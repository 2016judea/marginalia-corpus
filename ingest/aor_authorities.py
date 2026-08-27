'''
    Author: Aidan Jude

    AOR's two authority tables, which turn the <person> and <book> tags
    inside the notes into resolvable identifiers.

    From archaeologyofreading.org/downloads/ (same page as the corpus
    bibliography, fetched by aor_resolve_books.py):

      People-January-2019.xlsx   2,485 people named in the notes, each with
                                 up to four alternative name forms and an
                                 ISNI. `-` means "no ISNI exists" (a
                                 biblical or mythological figure, mostly),
                                 which is a real answer, not a gap.
      Books-January-2019.xlsx     530 books cited in the notes, with the
                                 bibliographic author and a USTC / EEBO /
                                 Digitale Sammlungen / Perseus link.

    THE RAGGED-CELL TRAP. Both sheets omit empty cells from the XLSX rather
    than emitting them blank, and the author column in Books sits at index 6
    with five empty columns before it. A minimal reader that concatenates
    <c> elements shifts every value left and reads the author as the title.
    openpyxl places cells by their `r` reference and gets it right; anything
    hand-rolled must too.

    The Books sheet's key column is headed "Standard ID" -- a short label
    like "A brief discourse" -- and that is what the XML's
    <book title="..."/> matches on, NOT the full title.
'''

import os

from ingest.aor_resolve_books import CACHE, fetch_sheets, sheet_rows

_PEOPLE = None
_BOOKS = None


def _load():
    global _PEOPLE, _BOOKS
    if _PEOPLE is not None:
        return
    fetch_sheets()
    people = {}
    rows = sheet_rows(os.path.join(CACHE, "People-January-2019.xlsx"))
    hdr = rows[0]
    isni_col = hdr.index("ISNI") if "ISNI" in hdr else 6
    for r in rows[1:]:
        std = r[0].strip()
        if not std:
            continue
        isni = (r[isni_col].strip() if len(r) > isni_col else "")
        rec = dict(isni="" if isni in ("", "-") else isni,
                   alt=[x.strip() for x in r[1:5] if x.strip()])
        people[std] = rec
        for a in rec["alt"]:
            people.setdefault(a, rec)
    books = {}
    rows = sheet_rows(os.path.join(CACHE, "Books-January-2019.xlsx"))
    hdr = rows[0]
    a_col = hdr.index("Bibl.information: author") if "Bibl.information: author" in hdr else 6
    t_col = hdr.index("Bibl.information: full title") if "Bibl.information: full title" in hdr else 7
    u_col = hdr.index("USTC") if "USTC" in hdr else 8
    for r in rows[1:]:
        std = r[0].strip()
        if not std:
            continue
        get = lambda i: (r[i].strip() if len(r) > i else "")
        books[std] = dict(author=get(a_col), title=get(t_col), ustc=get(u_col))
    _PEOPLE, _BOOKS = people, books


def person(name):
    _load()
    return _PEOPLE.get((name or "").strip(), {})


def book(std_id):
    _load()
    return _BOOKS.get((std_id or "").strip(), {})


def counts():
    _load()
    return dict(people=len({id(v) for v in _PEOPLE.values()}), books=len(_BOOKS))


if __name__ == "__main__":
    print(counts())
    print("Cicero ->", person("Cicero"))
    print("A brief discourse ->", book("A brief discourse"))
