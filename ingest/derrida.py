'''
    Author: Aidan Jude

    Derrida's Margins -> Volume/Mark/Reference records.

    THE ONLY OPENLY LICENSED SOURCE IN THE CORPUS. Rights field reads
    "CC BY -- Creative Commons Attribution 4.0 International", so this is
    the one slice whose note text ships in full.

    Getting the data was the whole trick, so record the route:

      * derridas-margins.princeton.edu is now a READ-ONLY web archive.
        Its "Download data for all interventions" link points at
        doi.org/10.34770/2ezk-1104.
      * That DOI resolves to datacommons.princeton.edu, which sits behind a
        JS challenge and returns 401 to every scripted fetch, browser
        headers or not.
      * The Blacklight JSON view is NOT challenged:
            /discovery/catalog/doi-10-34770-2ezk-1104.json
        and it hands back direct Globus download URLs plus the rights field.
        That is the route this module uses.
      * Figshare collection 4256927 also holds this data as CC0 -- but it is
        **v1 (2018) and superseded**; the article descriptions say so
        themselves. v1.1.1 has different filenames (annotations.csv, not
        interventions.csv) and different row counts. Do not take the easy
        Figshare download.

    Scope, and it is narrow: Derrida's library at Princeton runs to ~13,800
    volumes. This dataset is phase 1 only -- the books behind *De la
    grammatologie* (1967). 222 library records, 83 flagged annotated, 50
    actually carrying annotation rows.

    What it adds that nothing else in the corpus does:
      * a 20th-century reader, against Melville's 19th and Harvey's 16th
      * 120 distinct source authors -- 6x Melville's 20 -- Rousseau (37
        volumes), Levi-Strauss, Heidegger, Plato, Husserl, Hegel, Freud
      * `annotation_region`, a IIIF URL cropped to the mark itself, so a
        passage anchor comes with its image
      * references.csv: 1,052 references in Derrida's OWN book, typed
        Quotation (632) / Footnote (325) / Citation (78) / Epigraph (17),
        each with the sentence of his that makes the reference and a link to
        the annotated copy. A self-declared influence edge, in the author's
        published voice rather than his margin.

    Hand attribution: `annotator` is "Derrida, Jacques" on 1,413 rows,
    "Derrida, Marguerite" on 4, empty on 2. All stay under reader_id
    `derrida` (the library is his) with hand_is_reader False on the six that
    are not his -- same convention as Melville's 433 HMorESM marks.
'''

import csv
import io
import json
import os
import urllib.request

import names
import rights
from schema import Mark, Reference, Volume, TIER_AUTOGRAPH, TIER_MARK, TIER_COPY

SOURCE = "derrida"
READER = "derrida"
CATALOG = "https://datacommons.princeton.edu/discovery/catalog/doi-10-34770-2ezk-1104.json"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache", SOURCE)
UA = {"User-Agent": "marginalia-corpus/1.0 (personal research; aidanjude2016@gmail.com)"}
WANT = ("annotations.csv", "insertions.csv", "library.csv", "references.csv",
        "DerridasMargins_v1.1.1_README.txt")

REF_KINDS = {"quotation": "quotation", "footnote": "footnote",
             "citation": "citation", "epigraph": "epigraph"}


def fetch():
    os.makedirs(CACHE, exist_ok=True)
    if all(os.path.exists(os.path.join(CACHE, f)) for f in WANT):
        return CACHE
    meta = json.load(urllib.request.urlopen(
        urllib.request.Request(CATALOG, headers=UA), timeout=60))
    got = {f["name"]: f["download_url"] for f in meta.get("files", [])}
    licence = [r.get("identifier") for r in (meta.get("rights") or [])]
    if "CC BY" not in licence:
        raise RuntimeError(
            f"Derrida dataset rights changed: {licence!r}. rights.py says CC BY and "
            f"emit_text is True on that basis -- re-read the terms before building."
        )
    for f in WANT:
        if f not in got:
            raise RuntimeError(f"{f} missing from the v1.1.1 release; filenames changed.")
        open(os.path.join(CACHE, f), "wb").write(
            urllib.request.urlopen(urllib.request.Request(got[f], headers=UA), timeout=120).read())
    return CACHE


def _rows(path, name):
    with open(os.path.join(path, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _authors(field):
    return [x.strip() for x in (field or "").split(";") if x.strip()]


def ingest():
    emit_text = rights.may_emit_text(SOURCE)
    path = fetch()
    lib = _rows(path, "library.csv")
    anns = _rows(path, "annotations.csv")
    ins = _rows(path, "insertions.csv")
    refs = _rows(path, "references.csv")

    ann_count = {}
    for a in anns:
        ann_count[a["book_id"]] = ann_count.get(a["book_id"], 0) + 1
    for i in ins:
        ann_count[i["book_id"]] = ann_count.get(i["book_id"], 0) + 1

    volumes, marks, references = [], [], []
    for l in lib:
        au = _authors(l["authors"])
        volumes.append(Volume(
            volume_id=l["id"], source_dataset=SOURCE, reader_id=READER,
            source_author=names.canonical(au[0]) if au else "",
            source_author_raw=au[0] if au else "",
            co_bound_authors=tuple(names.canonical(x) for x in au[1:]),
            source_title=l["title"], source_date=l["print_date"] or l["copyright_year"] or l["work_year"],
            repository="Princeton University Library",
            shelfmark=l.get("copy") or "",
            url=l["id"], n_marks=ann_count.get(l["id"], 0),
        ))

    for a in anns:
        who = (a.get("annotator") or "").strip()
        note = (a.get("text_content") or "").strip()
        quote = (a.get("quote_content") or "").strip()
        tier = TIER_AUTOGRAPH if note else TIER_MARK
        marks.append(Mark(
            mark_id=a["id"], volume_id=a["book_id"], reader_id=READER, tier=tier,
            mark_type=";".join(sorted(x.strip() for x in (a.get("tags") or "").split(";") if x.strip())) or "unknown",
            page=a.get("page") or "",
            marked_text=quote if emit_text else "",
            reader_text=note if emit_text else "",
            text_withheld=bool(note and not emit_text),
            hand=who or "unattributed",
            hand_is_reader=(who == "Derrida, Jacques"),
            lang=a.get("text_language_code") or a.get("quote_language_code") or "",
            translation=(a.get("text_translation") or "") if emit_text else "",
            url=a.get("annotation_region") or a["id"],
        ).validate())

    for i in ins:
        # A physical object left in the book -- a slip, a card, a page tipped
        # in. Attention without words: T2, never T1.
        marks.append(Mark(
            mark_id=i["id"], volume_id=i["book_id"], reader_id=READER, tier=TIER_MARK,
            mark_type=f'insertion:{(i.get("label") or "").strip() or "unlabelled"}',
            page=i.get("page") or "", hand="unattributed", hand_is_reader=False,
            url=i.get("image_iiif") or i["id"],
        ).validate())

    by_id = {l["id"]: l for l in lib}
    for n, r in enumerate(refs):
        tgt = by_id.get(r["book_id"]) or {}
        au = _authors(tgt.get("authors", ""))
        references.append(Reference(
            ref_id=f'{SOURCE}:ref:{n}', reader_id=READER,
            kind=REF_KINDS.get((r.get("type") or "").strip().lower(), "citation"),
            source_dataset=SOURCE,
            in_volume=r["book_id"],
            # Every row in this file is a reference made inside De la
            # grammatologie -- that is the dataset's scope, not an inference.
            in_work="De la grammatologie",
            target_name=r.get("book_title") or "",
            target_author=names.canonical(au[0]) if au else "",
            target_id=r.get("book_id") or "",
            anchor_text=(r.get("anchor_text") or "") if emit_text else "",
            page=r.get("page") or "",
            url=r.get("id") or "",
        ))

    return volumes, marks, references


if __name__ == "__main__":
    v, m, r = ingest()
    from collections import Counter
    print(f"{len(v)} volumes, {len(m)} marks {dict(Counter(x.tier for x in m))}, "
          f"{len(r)} references {dict(Counter(x.kind for x in r))}")
    print(f"marks confidently in Derrida's own hand: {sum(1 for x in m if x.hand_is_reader)}")
    print(f"distinct source authors: {len({x.source_author for x in v if x.source_author})}")
