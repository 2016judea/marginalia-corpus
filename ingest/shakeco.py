'''
    Author: Aidan Jude

    The Shakespeare and Company Project -> Volume/Mark(T3) records.

    Sylvia Beach's Paris lending library, 1919-1941, reconstructed from her
    surviving lending cards and logbooks. **CC BY 4.0**, v1.2 (2022-01),
    doi:10.34770 series on Princeton Data Commons -- the same host and the
    same JSON route as Derrida's Margins (see ingest/derrida.py for why the
    Blacklight view is the only way in).

    Why a lending library belongs in a marginalia corpus: it is the same
    evidence class as Whitman's Bibliographical Handlist -- attested contact
    with a specific copy, no surviving mark -- except it is **dated to the
    day, sourced to a physical card, and 98.8% of events link an image of
    that card**. Nothing else in the corpus documents contact this precisely.

        Borrow, 1922 -> 1922-08-23, Mr. Rhys, Conrad's *Typhoon* (1902)
        source: Sylvia Beach, Rhys Lending Library Card, Box 43
        image:  iiif.princeton.edu/loris/figgy_prod/...

    Scale, measured 2026-08-27: 5,235 members, 6,020 books, 35,523 events of
    which 21,059 are borrows. Restricted to members who are authors of
    record (below): **520 readers, 8,422 borrow/purchase/request events,
    7,731 reader-book pairs, 1,510 distinct source authors.** Joyce borrowed
    149 times, Hemingway 123, Gertrude Stein 60, Katherine Anne Porter 49,
    Nathalie Sarraute 41; Beckett, Pound, Walter Benjamin, Djuna Barnes and
    Bryher all hold cards.

    ---- who counts as a reader here, and why it is mechanical ----

    5,235 members is too many for a corpus about authors; picking the famous
    novelists would be cherry-picking. The criterion is therefore **the
    member has a VIAF url** -- they appear in library authority files, i.e.
    they are an author of record -- which the project supplies per member and
    which involves no judgement of ours. 520 of 5,235 qualify.

    `wikipedia` is carried per reader as well, so a consumer can tighten to
    the 345 who have both. Members without a VIAF are not emitted, and the
    count of what that drops is reported in the manifest.

    ---- what this slice is NOT ----

    A borrow is attested CONTACT, not proof of reading, and certainly not a
    passage. Every record here is T3. There are no marks, no anchors and no
    reader's words -- the cards record transactions. Anyone weighting these
    against Melville's 4,864 physical marks has merged two different
    measurements; that is what the tier is for.

    One artefact of the source to carry, not to fix: a SHARED CARD credits
    one event to every member on it, so a couple appear with identical
    counts (Archibald and Ada MacLeish, 236 each). Those are the same
    physical transactions, and `member_uris` is multi-valued precisely so
    the project does not have to guess who did the borrowing. Summing across
    readers therefore over-counts events; summing per reader does not.

    Also note 2,764 member uris and 127 book uris appear in
    `*_removed.csv`: identities the project merged or withdrew between
    versions. They are excluded, not silently dropped -- see the counts.
'''

import csv
import json
import os
import urllib.request

import names
import rights
from schema import Mark, Volume, TIER_COPY

SOURCE = "shakeco"
CATALOG = "https://datacommons.princeton.edu/discovery/catalog.json?q=shakespeare+and+company"
ITEM = "https://datacommons.princeton.edu/discovery/catalog/{}.json"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache", SOURCE)
UA = {"User-Agent": "marginalia-corpus/1.0 (personal research; aidanjude2016@gmail.com)"}
VERSION = "v1.2"
WANT = ("SCoData_members_v1.2_2022-01.csv", "SCoData_books_v1.2_2022-01.csv",
        "SCoData_events_v1.2_2022-01.csv", "SCoData_members_v1.2_removed.csv",
        "SCoData_books_v1.2_removed.csv")
# Event types that put a specific copy in the reader's hands. Subscription,
# Renewal, Reimbursement and Separate Payment are money, not books.
CONTACT = {"Borrow", "Purchase", "Request", "Gift"}
READERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shakeco_readers.json")


def fetch():
    os.makedirs(CACHE, exist_ok=True)
    if all(os.path.exists(os.path.join(CACHE, f)) for f in WANT):
        return CACHE
    ids = []
    for page in (1, 2):
        url = CATALOG + (f"&page={page}" if page > 1 else "")
        try:
            ids += [x["id"] for x in json.load(urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=60))["data"]]
        except Exception:
            break
    urls, licences = {}, set()
    for i in ids:
        d = json.load(urllib.request.urlopen(urllib.request.Request(ITEM.format(i), headers=UA), timeout=60))
        licences |= {r.get("identifier") for r in (d.get("rights") or [])}
        for f in d.get("files", []):
            urls.setdefault(f["name"], f["download_url"])
    if licences and "CC BY" not in licences:
        raise RuntimeError(f"Shakespeare and Co rights changed: {licences!r}. rights.py "
                           f"sets emit_text on CC BY -- re-read the terms.")
    for f in WANT:
        if f not in urls:
            raise RuntimeError(f"{f} absent; a newer version than {VERSION} may have "
                               f"replaced the filenames. Check the catalog before bumping.")
        open(os.path.join(CACHE, f), "wb").write(
            urllib.request.urlopen(urllib.request.Request(urls[f], headers=UA), timeout=300).read())
    return CACHE


def _rows(path, name):
    with open(os.path.join(path, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def build_readers_file():
    '''
        Write the reader roster to a COMMITTED file rather than letting the
        adapter invent 520 readers at build time. build_corpus.py refuses
        readers it has not been shown, and that guard is worth keeping even
        for a source that legitimately has hundreds -- so the roster is
        generated, reviewed in git, and loaded.
    '''
    path = fetch()
    removed = {r["uri"] for r in _rows(path, "SCoData_members_v1.2_removed.csv")}
    out = {}
    for m in _rows(path, "SCoData_members_v1.2_2022-01.csv"):
        if m["uri"] in removed or not m["viaf_url"]:
            continue
        out[f'{SOURCE}:{m["uri"].rstrip("/").rsplit("/", 1)[-1]}'] = dict(
            name=m["name"], sort_name=m["sort_name"],
            birth=int(m["birth_year"]) if m["birth_year"].isdigit() else None,
            death=int(m["death_year"]) if m["death_year"].isdigit() else None,
            viaf=m["viaf_url"], wikipedia=m["wikipedia_url"],
            nationalities=m["nationalities"], uri=m["uri"],
        )
    json.dump({"_note": (
        "Generated by ingest/shakeco.py build_readers_file() from the CC BY v1.2 "
        "members dataset. Criterion: the member has a VIAF url, i.e. an entry in "
        "library authority files -- mechanical, not a judgement about who counts as "
        "a writer. 520 of 5,235 members qualify; 345 of those also have a Wikipedia "
        "page, carried here so a consumer can tighten. Members listed in "
        "SCoData_members_v1.2_removed.csv are excluded."),
        "readers": out}, open(READERS_FILE, "w"), indent=1, ensure_ascii=False)
    return out


def readers():
    if not os.path.exists(READERS_FILE):
        return build_readers_file()
    return json.load(open(READERS_FILE, encoding="utf-8"))["readers"]


def ingest():
    rights.check(SOURCE)
    path = fetch()
    roster = readers()
    by_uri = {v["uri"]: k for k, v in roster.items()}
    books = {b["uri"]: b for b in _rows(path, "SCoData_books_v1.2_2022-01.csv")}
    removed_books = {r["uri"] for r in _rows(path, "SCoData_books_v1.2_removed.csv")}
    events = _rows(path, "SCoData_events_v1.2_2022-01.csv")

    vol, marks = {}, []
    skipped_removed = skipped_no_author = 0

    for n, e in enumerate(events):
        if e["event_type"] not in CONTACT or not e["item_uri"]:
            continue
        if e["item_uri"] in removed_books:
            skipped_removed += 1
            continue
        book = books.get(e["item_uri"])
        if not book:
            skipped_removed += 1
            continue
        au = [x.strip() for x in (book["author"] or "").split(";") if x.strip()]
        if not au:
            # A book with no author of record cannot make an authorial edge.
            # Counted, never guessed from the title.
            skipped_no_author += 1
        for u in (e["member_uris"] or "").split(";"):
            rid = by_uri.get(u.strip())
            if not rid:
                continue
            slug = e["item_uri"].rstrip("/").rsplit("/", 1)[-1]
            vid = f"{SOURCE}:{rid.split(':', 1)[1]}:{slug}"
            v = vol.get(vid)
            if v is None:
                v = vol[vid] = Volume(
                    volume_id=vid, source_dataset=SOURCE, reader_id=rid,
                    source_author=names.canonical(au[0]) if au else "",
                    source_author_raw=au[0] if au else "",
                    co_bound_authors=tuple(names.canonical(x) for x in au[1:]),
                    source_title=book["title"], source_date=book["year"],
                    repository="Shakespeare and Company lending library, Paris",
                    url=e["item_uri"], n_marks=0,
                    evidence_source=e["source_citation"][:200],
                )
            v.n_marks += 1
            d = e["start_date"] or e["end_date"] or ""
            if d and (not v.read_from or d < v.read_from):
                v.read_from = d
            if d and d > v.read_to:
                v.read_to = d
            marks.append(Mark(
                mark_id=f"{SOURCE}:{n}:{rid.split(':', 1)[1]}",
                volume_id=vid, reader_id=rid, tier=TIER_COPY,
                mark_type=f'attested_{e["event_type"].lower()}',
                page=d,                     # the date IS the payload here
                hand="", hand_is_reader=True,
                url=e["source_image"] or e["source_manifest"] or e["item_uri"],
            ).validate())

    return list(vol.values()), marks, []


if __name__ == "__main__":
    build_readers_file()
    v, m, _ = ingest()
    import collections
    per = collections.Counter(x.reader_id for x in m)
    roster = readers()
    print(f"{len(roster)} readers on the roster, {len(per)} with at least one event")
    print(f"{len(v)} reader-book records, {len(m)} attested-contact events, "
          f"{len({x.source_author for x in v if x.source_author})} distinct source authors")
    print(f"records carrying a date: {sum(1 for x in v if x.read_from)}/{len(v)}")
    for rid, c in per.most_common(12):
        print(f"  {c:>4}  {roster[rid]['name']}")
