'''
    Author: Aidan Jude

    Nietzsche -> Reference records only. NO volumes, NO marks, and that
    absence is the honest headline.

    ---- why there is no marginalia slice here ----

    Nietzsche is the best-documented annotator in the survey and the least
    reachable. Established 2026-08-27, each by fetching:

      * **430,000 pages of his library are digitised, ~18,000 carrying
        annotations** -- and they are FACSIMILE ONLY. There is no
        transcription layer to ingest.
      * **Nietzsche Source publishes exactly three modules** -- eKGWB (the
        Colli-Montinari critical text), DFGA (facsimiles of the *archive*,
        i.e. manuscripts: its search columns are Mette numbers and KGW
        sigla, not books), and Studia Nietzscheana. The planned digital
        edition of the LIBRARY is announced and **not published**. Confirmed
        by rendering the JS nav, not by reading the homepage HTML.
      * **Weimar (haab-digital.klassik-stiftung.de) blocks automated access
        outright** -- Anubis proof-of-work, and it gates the OAI-PMH
        endpoint too, which is the sanctioned harvesting route. That is a
        deliberate operator decision and this repo respects it. Do not
        solve the PoW with a headless browser.
      * The transcribed reading traces exist in ONE place: *Nietzsches
        persönliche Bibliothek* (Campioni, D'Iorio, Fornari, Fronterotta,
        Orsucci; De Gruyter 2003), ~2,200 titles with a complete index of
        Lesespuren. In copyright, in print, purchasable. That is the
        Coleridge problem again and it is the only gate that matters.

    ---- what this module builds instead ----

    The one Nietzsche evidence class that is free, complete and
    redistributable: **Nietzsche naming another author in his own published
    prose.** Seven works, in German, from Project Gutenberg (public domain
    -- he died in 1900), header and licence block stripped.

    That is a Reference, never a Mark. He is not annotating; he is citing.
    It sits in the same class as Derrida's 1,052 references and Harvey's
    1,158 works-cited, and it is emitted with the same schema.

    ---- the gazetteer, and why it is honest ----

    Matching is a CLOSED lookup against ingest/nietzsche_gazetteer.json --
    62 declared authors -- never open-ended entity recognition. Three
    consequences, all deliberate:

      1. A count of zero is a real answer, so three impossible controls
         (Melville, Whitman, Derrida) are in the list. If they ever return
         a hit, the matcher is broken.
      2. Recall is bounded by the list. This finds who, among 62 named
         candidates, Nietzsche invokes and how often. It does not claim to
         find everyone he cites.
      3. Ambiguous surnames are GATED, because a bare German surname is
         frequently a common word. Every raw match on "Lange" in these
         seven texts is the adjective ("Lange schlief Zarathustra",
         "Langes Leben", "alles Lange") -- Friedrich Albert Lange would
         otherwise rank 28th on twelve false hits. "Strauss" catches a
         bouquet and, in Zarathustra, an ostrich. Those entries require a
         first name within 60 characters.

    Every hit's surrounding sentence is written to _data/nietzsche_audit.json
    so the claim can be checked against the text rather than trusted.

    Out (via build_corpus): References with kind="named_in_work".
'''

import json
import os
import re
import urllib.request

import names
import rights
from schema import Reference

SOURCE = "nietzsche"
READER = "nietzsche"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, "cache", SOURCE)
UA = {"User-Agent": "marginalia-corpus/1.0 (personal research; aidanjude2016@gmail.com)"}
GAZ_FILE = os.path.join(HERE, "nietzsche_gazetteer.json")

# Gutenberg id -> (title, siglum, year of Nietzsche's own publication).
# `year` is the WORK's date, which is what makes this a dated series; it is
# not the Gutenberg edition's date.
WORKS = {
    7206:  ("Die Geburt der Tragödie", "GT", 1872),
    7207:  ("Menschliches, Allzumenschliches", "MA", 1878),
    7205:  ("Also sprach Zarathustra", "Za", 1885),
    7204:  ("Jenseits von Gut und Böse", "JGB", 1886),
    7203:  ("Götzen-Dämmerung", "GD", 1888),
    7202:  ("Ecce homo", "EH", 1888),
    # Compiled posthumously by Elisabeth Förster-Nietzsche and Peter Gast
    # from the notebooks. The FRAGMENTS are his; the selection, ordering and
    # title are not, and the compilation is the one Colli-Montinari
    # dismantled. Kept because it is the only free route to notebook
    # material, and flagged so nobody treats it as an authored work.
    60360: ("Der Wille zur Macht (posthumous compilation)", "WzM", 1901),
}
POSTHUMOUS = {60360}
CONTEXT_WINDOW = 60          # chars either side, for a gated entry
SENTENCE = re.compile(r"[^.!?»«]*$")


def _gaz():
    d = json.load(open(GAZ_FILE, encoding="utf-8"))
    return {k: v for k, v in d.items() if not k.startswith("_")}


def fetch():
    os.makedirs(CACHE, exist_ok=True)
    for gid in WORKS:
        p = os.path.join(CACHE, f"pg{gid}.txt")
        if os.path.exists(p) and os.path.getsize(p) > 50000:
            continue
        url = f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt"
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
        if len(raw) < 50000:
            raise RuntimeError(f"pg{gid} came back at {len(raw)} bytes -- Gutenberg "
                               f"serves an HTML error page as a 404 body; check the id.")
        open(p, "wb").write(raw)
    return CACHE


def _body(path):
    '''
        Strip Gutenberg's header and licence block. Everything between the
        START and END markers is the public-domain text; the markers
        themselves name authors ("Project Gutenberg"), so leaving them in
        would put boilerplate into the corpus.
    '''
    raw = open(path, encoding="utf-8", errors="replace").read()
    s, e = raw.find("*** START"), raw.find("*** END")
    if s < 0 or e < s:
        raise RuntimeError(f"{path}: Gutenberg markers missing; refusing to guess "
                           f"where the text begins.")
    return raw[raw.find("\n", s) + 1:e]


def ingest():
    emit_text = rights.may_emit_text(SOURCE)
    path = fetch()
    gaz = _gaz()
    references, audit = [], {}
    n = 0

    for gid, (title, siglum, year) in sorted(WORKS.items(), key=lambda kv: kv[1][2]):
        body = _body(os.path.join(path, f"pg{gid}.txt"))
        for canon, spec in gaz.items():
            requires = spec.get("requires")
            for form in spec["forms"]:
                # German genitive/inflected endings on a proper noun.
                pat = re.compile(r"\b" + re.escape(form) + r"(?:s|n|en|es|'s)?\b")
                for m in pat.finditer(body):
                    lo = max(0, m.start() - CONTEXT_WINDOW)
                    window = body[lo:m.end() + CONTEXT_WINDOW]
                    if requires and not any(q in window for q in requires):
                        continue
                    sent = re.sub(r"\s+", " ", body[max(0, m.start() - 160):m.end() + 160]).strip()
                    references.append(Reference(
                        ref_id=f"{SOURCE}:ref:{n}", reader_id=READER,
                        kind="named_in_work", source_dataset=SOURCE,
                        in_work=f"{title} ({year})",
                        target_name=form,
                        target_author=names.canonical(canon),
                        anchor_text=sent if emit_text else "",
                        page=siglum,
                        url=f"https://www.gutenberg.org/ebooks/{gid}",
                    ))
                    n += 1
                    audit.setdefault(canon, []).append(dict(work=siglum, context=sent[:220]))

    # Controls must stay at zero, or the matcher is wrong rather than the
    # finding surprising.
    controls = [k for k, v in gaz.items() if "CONTROL" in (v.get("note") or "")]
    hit = [c for c in controls if c in audit]
    if hit:
        raise RuntimeError(
            f"control author(s) matched: {hit}. These cannot appear in Nietzsche "
            f"(Melville and Whitman he never names; Derrida was born in 1930), so "
            f"the matcher is producing false positives -- fix it, do not widen the "
            f"control list."
        )

    # A work that names nobody is a FINDING, not an absent row. Zarathustra
    # cites none of the 62 -- it is written as scripture, not as argument --
    # and dropping it would read as "not processed".
    named_works = {r.page for r in references}
    silent = [f"{t} ({y})" for _, (t, sg, y) in sorted(WORKS.items(), key=lambda kv: kv[1][2])
              if sg not in named_works]

    os.makedirs(os.path.join(ROOT, "_data"), exist_ok=True)
    with open(os.path.join(ROOT, "_data", "nietzsche_audit.json"), "w") as f:
        json.dump({
            "_note": ("Every gazetteer hit with its surrounding sentence, so the counts "
                      "can be checked against the text instead of trusted. Gated "
                      "entries and zero-count controls are documented in "
                      "ingest/nietzsche_gazetteer.json."),
            "n_references": len(references),
            "controls_at_zero": controls,
            "posthumous_compilations": [WORKS[g][1] for g in POSTHUMOUS],
            "works_naming_nobody": silent,
            "hits": {k: v[:4] for k, v in sorted(audit.items(), key=lambda kv: -len(kv[1]))},
            "counts": {k: len(v) for k, v in sorted(audit.items(), key=lambda kv: -len(kv[1]))},
        }, f, indent=1, ensure_ascii=False)

    return [], [], references


if __name__ == "__main__":
    v, m, r = ingest()
    import collections
    per = collections.Counter(x.target_author for x in r)
    works = collections.Counter(x.in_work for x in r)
    print(f"{len(r)} references, {len(per)} authors named, {len(works)} works")
    for a, c in per.most_common(15):
        print(f"  {c:>4}  {a}")
    print()
    for w, c in sorted(works.items()):
        print(f"  {c:>4}  {w}")
