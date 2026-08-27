'''
    Author: Aidan Jude

    Annotated Books Online -> Volume/Mark records.

    **CC BY-NC**, stated on annotatedbooksonline.com/conditions-of-use:
    "You are free to use the images of digitized books on ABO for
    non-commercial purposes... These works are licensed under a Creative
    Commons Attribution-Noncommercial license." So the transcriptions ship;
    the NC clause constrains downstream commercial reuse and is recorded in
    rights.py.

    ---- the API, which is open once you know the shape ----

    ABO is an ExtJS app and looks closed: `/backend` returns 403, there is
    no `/api`, and no endpoint appears in the frontend JS. The route is in
    `frontend/logic/requestmanager.js`:

        POST /?controller=<Controller>&action=<action>

    and `requestmanagerproxy.js` maps an ExtJS `read` operation to the
    action `load`. Three calls fetch the entire archive, and each one
    IGNORES filters and returns everything:

        Book/search      ->    110 books   (send {"limit":500}; default is 5)
        Scan/load        -> 50,776 scans
        Annotation/load  ->  4,803 annotations

    `Book/search` reports `total` separately from `records`, so a naive
    caller takes the first 5 of 110 and never notices.

    ---- the join, and the trap inside it ----

    annotation.scanId -> scan.bindingId -> book. **A binding can hold
    several works** -- 12 of 95 do -- so the book is the one with the
    greatest `firstPage` at or below the scan's page. Without that,
    Sammelband annotations all land on the binding's first work.

    Second trap: `bindingId` is an **int** on scans and a **string** on
    books. A dict lookup across the two silently matches nothing and every
    annotation reports unmapped. That is how this join failed on the first
    attempt.

    ---- THE OVERLAP, which is the important part ----

    ABO and AOR are different projects that transcribed **many of the same
    physical copies**. 10 of the 11 ABO books with Dee or Harvey provenance
    are copies AOR also covers -- the Folger H.a.2 Sammelband, Princeton's
    Arte of Warre, the Livy, both Buchanans. Ingesting both naively
    double-counts the same marks as independent evidence.

    So books whose copy AOR already covers are **excluded and counted**,
    matched on shelfmark then title against ingest/aor_corpus.csv:

        1,190 annotations on AOR-covered copies   -> EXCLUDED
        3,611 annotations on copies AOR does not  -> INGESTED

    What survives is worth having. **John Dee's Strabo, De situ orbis, at
    the Royal Library of Belgium: 2,826 annotations**, his most heavily
    annotated book anywhere and absent from AOR. Plus new readers -- Luther
    (224, on an Erasmus New Testament), Melanchthon and Luther's shared
    Odyssey (70), Erasmus himself (55), Joseph Scaliger, Jan van Hout,
    Adriaen Verwer's copy of Newton's *Principia* (65, where Verwer is the
    reader and Newton the source author), and Newton's own Principia (1).

    Montaigne's Lucretius is in the book list with **zero** annotations
    transcribed. Listed, not transcribed -- do not report him as present.

    ---- hands ----

    `provenance` is a free-text ownership CHAIN on the book, not a
    per-annotation hand, and ABO's `createdName`/`changedName` are the
    MODERN transcriber. So ingest/abo_readers.json maps each provenance
    string to one historical annotator and flags `sole`; every mark from a
    multi-name chain carries hand_is_reader=False.
'''

import json
import os
import re
import urllib.request

import names
import rights
from schema import Mark, Volume, TIER_AUTOGRAPH, TIER_MARK

SOURCE = "abo"
BASE = "https://abo2.annotatedbooksonline.com/"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, "cache", SOURCE)
UA = {"User-Agent": "marginalia-corpus/1.0 (personal research; aidanjude2016@gmail.com)",
      "Content-Type": "application/json"}
CALLS = {"books": ("Book", "search", {"limit": 500}),
         "scans": ("Scan", "load", {}),
         "annotations": ("Annotation", "load", {})}
READERS_MAP = json.load(open(os.path.join(HERE, "abo_readers.json"), encoding="utf-8"))
AOR_CORPUS = os.path.join(HERE, "aor_corpus.csv")


def fetch():
    os.makedirs(CACHE, exist_ok=True)
    out = {}
    for name, (ctrl, action, body) in CALLS.items():
        p = os.path.join(CACHE, f"{name}.json")
        if not (os.path.exists(p) and os.path.getsize(p) > 2000):
            req = urllib.request.Request(f"{BASE}?controller={ctrl}&action={action}",
                                         data=json.dumps(body).encode(), headers=UA, method="POST")
            open(p, "wb").write(urllib.request.urlopen(req, timeout=180).read())
        d = json.load(open(p, encoding="utf-8"))
        recs = d.get("records", [])
        # `total` comes back as a string on Book/search and an int on the
        # others -- comparing without int() raises rather than guarding.
        total = d.get("total")
        total = int(total) if str(total).isdigit() else None
        if total is not None and len(recs) < total:
            raise RuntimeError(
                f"{name}: got {len(recs)} of {total}. Book/search defaults to 5 records "
                f"and reports `total` separately -- raise the limit rather than "
                f"accepting the short list."
            )
        out[name] = recs
    return out


def _aor_keys():
    '''Shelfmarks and titles of the copies AOR already transcribed.'''
    import csv
    sigs, titles = [], []
    with open(AOR_CORPUS, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            k = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
            if r["Shelfmark"]:
                sigs.append(k(r["Shelfmark"]))
            if r["Title"]:
                titles.append(k(r["Title"])[:18])
    return sigs, titles


def _covered_by_aor(book, sigs, titles):
    k = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
    s, t = k(book.get("signature")), k(book.get("title"))[:18]
    if s and any(a and (s[:10] in a or a[:10] in s) for a in sigs):
        return True
    return bool(t) and any(a and (t in a or a in t) for a in titles)


def _strip(html):
    '''ABO transcriptions carry light markup (<i>, <br>, editorial spans).'''
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def readers():
    return {v["reader"]: v for k, v in READERS_MAP.items()
            if not k.startswith("_") and v}


def ingest():
    emit_text = rights.may_emit_text(SOURCE)
    d = fetch()
    sigs, titles = _aor_keys()
    scans = {s["scanId"]: s for s in d["scans"]}

    by_binding = {}
    for b in d["books"]:
        by_binding.setdefault(int(b["bindingId"]), []).append(b)
    for k in by_binding:
        by_binding[k].sort(key=lambda x: int(x["firstPage"] or 1))

    def book_for(scan):
        cands = by_binding.get(scan["bindingId"])
        if not cands:
            return None
        page, pick = scan.get("page") or 1, None
        for b in cands:
            if int(b["firstPage"] or 1) <= page:
                pick = b
        return pick or cands[0]

    excluded_aor = excluded_unattributed = unmapped = 0
    vols, marks = {}, []

    for a in d["annotations"]:
        scan = scans.get(a["scanId"])
        book = book_for(scan) if scan else None
        if book is None:
            unmapped += 1
            continue
        if _covered_by_aor(book, sigs, titles):
            excluded_aor += 1
            continue
        who = READERS_MAP.get(book.get("provenance") or "")
        if not who:
            excluded_unattributed += 1
            continue

        vid = f'{SOURCE}:{book["id"]}:{who["reader"]}'
        v = vols.get(vid)
        if v is None:
            v = vols[vid] = Volume(
                volume_id=vid, source_dataset=SOURCE, reader_id=who["reader"],
                source_author=names.canonical(book.get("author") or ""),
                source_author_raw=book.get("author") or "",
                source_title=book.get("title") or "",
                source_date=book.get("year") or "",
                repository=book.get("library") or "",
                shelfmark=book.get("signature") or "",
                url=f'{BASE}#/binding/{book["bindingId"]}', n_marks=0,
            )
        v.n_marks += 1
        orig, eng = _strip(a.get("transcriptionOrig")), _strip(a.get("transcriptionEng"))
        marks.append(Mark(
            mark_id=f'{SOURCE}:{a["annotationId"]}',
            volume_id=vid, reader_id=who["reader"],
            tier=TIER_AUTOGRAPH if orig else TIER_MARK,
            mark_type="annotation",
            page=str(scan.get("page") or ""),
            reader_text=(orig if emit_text else ""),
            text_withheld=bool(orig and not emit_text),
            translation=(eng if emit_text else ""),
            hand=who["name"], hand_is_reader=bool(who.get("sole")),
            url=f'{BASE}#/binding/{book["bindingId"]}',
        ).validate())

    stats = dict(excluded_already_in_aor=excluded_aor,
                 excluded_provenance_not_one_person=excluded_unattributed,
                 unmapped_scan=unmapped)
    if excluded_aor == 0:
        raise RuntimeError(
            "zero annotations excluded as AOR duplicates -- 10 of ABO's 11 Dee/Harvey "
            "books are copies AOR also transcribed, so a count of zero means the "
            "overlap check stopped working and the corpus is double-counting."
        )
    return list(vols.values()), marks, [], stats


if __name__ == "__main__":
    v, m, _, stats = ingest()
    import collections
    per = collections.Counter(x.reader_id for x in m)
    print(f"{len(v)} volume-reader records, {len(m)} marks, "
          f"{sum(1 for x in m if x.tier == TIER_AUTOGRAPH)} autograph, "
          f"{len(per)} readers")
    print("excluded:", stats)
    for r, c in per.most_common(14):
        print(f"  {c:>5}  {r}")
