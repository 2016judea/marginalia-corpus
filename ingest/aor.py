'''
    Author: Aidan Jude

    The Archaeology of Reading in Early Modern Europe -> Volume/Mark records.

    Source: github.com/livesandletters/aor (master, last pushed 2020-06-01).
    7,594 XML files, one per PAGE, grouped in 35 directories, one per book.
    33 MB. Cloned into cache/aor/ -- not vendored, see rights.py.

    Why this source is worth the entity mess below: AOR's schema separates
    the two things a marginalia corpus must never merge, at the source.

        <marginalia hand="Italian" anchor_text="Capuam Annibali Cannas fuisse">
          <marginalia_text>Capua, Annibali Canna[e]. s[upr]a, 331.</marginalia_text>
          <person name="Hannibal" /> <location name="Capua" />
          <translation>Capua, Hannibal's Cannae.</translation>
        </marginalia>
        <underline text="quos collaudatos Marcellus in subsidijs" />

      anchor_text      the SOURCE AUTHOR's printed words the note sits beside
      marginalia_text  the READER's own words
      translation      an editorial English translation of the note
      person/location  named entities INSIDE the note, resolved against
                       AOR's own authority sheets (2,479 people with ISNI
                       and alt-name forms; 526 books with author + USTC) --
                       see aor_authorities.py. These become References, not
                       Marks: Harvey, reading Livy, writes a note naming
                       Machiavelli. 3,687 <person> and 468 <book> tags.
                       <book title="..."/> matches the Books sheet's
                       "Standard ID" short label, NOT the full title.

    1,555 of 7,594 files (20%) DO NOT PARSE as XML out of the box. They use
    HTML named entities (&egrave; 496x, &agrave; 250x, &ograve; 102x,
    &AElig; 97x) plus a project-specific &sharp-S; (71x), against a schema
    that declares none of them. A session that parses with a bare
    ElementTree and moves on silently loses a fifth of the corpus,
    concentrated in the Latin books (Cicero II worst). Fixed by substituting
    entities before parsing -- do not "clean up" that step.

    Book-level bibliography is NOT in the page XML. It comes from AOR's own
    Corpus-January-2019.xlsx via ingest/aor_resolve_books.py -- all 35
    directories resolved, 31 distinct authors. Two directories are
    Sammelbände whose co-bound works get no edge; see that module.

    READER, not book, is the unit of interest. The reader is declared
    per-PAGE (`<page reader="Harvey">`), and a book can carry more than one
    hand: Castiglione has Harvey plus a Mary Young and an I. Young,
    Paracelsus_Meteorum has John Winthrop alongside Dee. Dee is spelled
    both "John Dee" (4,437 pages) and "Dee" (217) -- normalized here.
'''

import html.entities
import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET

import names
import rights
from ingest import aor_authorities
from schema import Mark, Reference, Volume, TIER_AUTOGRAPH, TIER_MARK

SOURCE = "aor"
REPO = "https://github.com/livesandletters/aor.git"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache", SOURCE)
BOOKS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "aor_books.json")))

READER_IDS = {
    "harvey": ("harvey", "Gabriel Harvey"),
    "john dee": ("dee", "John Dee"),
    "dee": ("dee", "John Dee"),
    "john winthrop": ("winthrop", "John Winthrop"),
}

# &sharp-S; is AOR's own; the rest resolve from html5. Mapped explicitly so a
# new undeclared entity shows up as a KeyError-free leftover rather than
# vanishing a file.
EXTRA_ENTITIES = {"sharp-S": "ß"}
_ENT = re.compile(r"&([A-Za-z][A-Za-z0-9._-]*);")


def _defuse(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")

    def sub(m):
        name = m.group(1)
        if name in ("amp", "lt", "gt", "quot", "apos"):
            return m.group(0)
        if name in EXTRA_ENTITIES:
            return EXTRA_ENTITIES[name]
        ch = html.entities.html5.get(name + ";") or html.entities.html5.get(name)
        return ch if ch else ""

    return _ENT.sub(sub, text)


def fetch():
    if os.path.isdir(os.path.join(CACHE, ".git")):
        return CACHE
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    subprocess.run(["git", "clone", "-q", "--depth", "1", REPO, CACHE], check=True)
    return CACHE


def _txt(e):
    return re.sub(r"\s+", " ", "".join(e.itertext())).strip() if e is not None else ""


def ingest():
    emit_text = rights.may_emit_text(SOURCE)
    path = fetch()
    volumes, marks, references = [], [], []
    unparsed = 0
    nref = 0

    for book in sorted(os.listdir(path)):
        bdir = os.path.join(path, book)
        if not os.path.isdir(bdir) or book.startswith(".") or book == "XMLschema":
            continue
        per_reader = {}

        for fn in sorted(os.listdir(bdir)):
            if not fn.endswith(".xml"):
                continue
            try:
                root = ET.fromstring(_defuse(open(os.path.join(bdir, fn), "rb").read()))
            except ET.ParseError:
                unparsed += 1
                continue

            pg = root.find("page")
            raw_reader = (pg.get("reader") or "").strip() if pg is not None else ""
            rid, _ = READER_IDS.get(raw_reader.lower(), (None, None))
            if rid is None:
                continue          # 'Unknown', 'Other', modern readers: not an author
            page = (pg.get("pagination") or pg.get("signature") or fn).strip()
            vol_id = f"{SOURCE}:{book}:{rid}"
            per_reader.setdefault(rid, 0)

            for i, marg in enumerate(root.iter("marginalia")):
                # 30,438 <marginalia_text> against 28,324 <marginalia>: a note
                # split across positions (head/tail/left margin) or languages
                # carries several. find() would drop ~2,100 of them.
                note = " / ".join(x for x in (_txt(e) for e in marg.iter("marginalia_text")) if x)
                trans = _txt(marg.find("translation"))
                people = tuple(p.get("name") for p in marg.iter("person") if p.get("name"))
                vol_for_ref = vol_id
                for p_el in marg.iter("person"):
                    nm = (p_el.get("name") or "").strip()
                    if not nm:
                        continue
                    auth = aor_authorities.person(nm)
                    references.append(Reference(
                        ref_id=f"{SOURCE}:ref:{nref}", reader_id=rid,
                        kind="named_in_note", source_dataset=SOURCE,
                        in_volume=vol_for_ref, target_name=nm,
                        target_id=auth.get("isni", ""),
                        anchor_text=(note if emit_text else ""),
                        page=page, url="https://archaeologyofreading.org/",
                    ))
                    nref += 1
                for b_el in marg.iter("book"):
                    std = (b_el.get("title") or "").strip()
                    if not std:
                        continue
                    bk = aor_authorities.book(std)
                    references.append(Reference(
                        ref_id=f"{SOURCE}:ref:{nref}", reader_id=rid,
                        kind="work_cited_in_note", source_dataset=SOURCE,
                        in_volume=vol_for_ref, target_name=std,
                        target_author=names.canonical(bk.get("author", "")),
                        target_id=bk.get("ustc", ""),
                        anchor_text=(note if emit_text else ""),
                        page=page, url="https://archaeologyofreading.org/",
                    ))
                    nref += 1
                lang = marg.find(".//language")
                tier = TIER_AUTOGRAPH if note else TIER_MARK
                marks.append(Mark(
                    mark_id=f"{vol_id}:{page}:m{i}",
                    volume_id=vol_id, reader_id=rid, tier=tier,
                    mark_type="marginalia", page=page,
                    marked_text=(marg.get("anchor_text") or "") if emit_text else "",
                    reader_text=note if (tier == TIER_AUTOGRAPH and emit_text) else "",
                    text_withheld=bool(note and not emit_text),
                    hand=marg.get("hand") or "",
                    lang=(lang.get("ident") if lang is not None else ""),
                    translation=trans if emit_text else "",
                    refs_people=people,
                ).validate())
                per_reader[rid] += 1

            for tag in ("underline", "symbol", "mark", "numeral", "drawing", "emphasis"):
                for i, e in enumerate(root.iter(tag)):
                    marks.append(Mark(
                        mark_id=f"{vol_id}:{page}:{tag}{i}",
                        volume_id=vol_id, reader_id=rid, tier=TIER_MARK,
                        mark_type=f'{tag}:{e.get("type") or e.get("name") or ""}'.rstrip(":"),
                        page=page,
                        marked_text=(e.get("text") or "") if emit_text else "",
                        lang=e.get("language") or "",
                    ).validate())
                    per_reader[rid] += 1

        rec = BOOKS.get(book) or {}
        for rid, n in per_reader.items():
            volumes.append(Volume(
                volume_id=f"{SOURCE}:{book}:{rid}", source_dataset=SOURCE, reader_id=rid,
                source_author=names.canonical(rec.get("author") or ""),
                source_author_raw=rec.get("author") or "",
                source_title=rec.get("title") or book.replace("_", ", "),
                shelfmark=rec.get("shelfmark") or "",
                repository=rec.get("location") or "",
                co_bound_authors=tuple(names.canonical(c["author"])
                                       for c in rec.get("co_bound", [])),
                url="https://archaeologyofreading.org/", n_marks=n,
            ))

    if unparsed:
        raise RuntimeError(
            f"{unparsed} AOR files still failed to parse after entity substitution. "
            f"An undeclared entity was added upstream -- add it to EXTRA_ENTITIES "
            f"rather than letting the files drop silently."
        )
    return volumes, marks, references


if __name__ == "__main__":
    v, m, r = ingest()
    from collections import Counter
    print(f"{len(v)} volume-reader records, {len(m)} marks, "
          f"{sum(1 for x in m if x.tier == TIER_AUTOGRAPH)} autograph, "
          f"{len(r)} references {dict(Counter(x.kind for x in r))}")
    print(f"references resolved to an id: {sum(1 for x in r if x.target_id)}")
