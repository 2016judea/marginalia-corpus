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
      person/location  named entities INSIDE the note, reconcilable against
                       AOR's own authority sheets (2,484 people with ISNI;
                       530 books with USTC ids) -- see aor_authorities.py

    1,555 of 7,594 files (20%) DO NOT PARSE as XML out of the box. They use
    HTML named entities (&egrave; 496x, &agrave; 250x, &ograve; 102x,
    &AElig; 97x) plus a project-specific &sharp-S; (71x), against a schema
    that declares none of them. A session that parses with a bare
    ElementTree and moves on silently loses a fifth of the corpus,
    concentrated in the Latin books (Cicero II worst). Fixed by substituting
    entities before parsing -- do not "clean up" that step.

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

import rights
from schema import Mark, Volume, TIER_AUTOGRAPH, TIER_MARK

SOURCE = "aor"
REPO = "https://github.com/livesandletters/aor.git"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache", SOURCE)
BOOK_AUTHORS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "aor_books.json")))

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
    volumes, marks = [], []
    unparsed = 0

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

        for rid, n in per_reader.items():
            volumes.append(Volume(
                volume_id=f"{SOURCE}:{book}:{rid}", source_dataset=SOURCE, reader_id=rid,
                source_author=BOOK_AUTHORS.get(book) or "",
                source_title=book.replace("_", ", "),
                url="https://archaeologyofreading.org/", n_marks=n,
            ))

    if unparsed:
        raise RuntimeError(
            f"{unparsed} AOR files still failed to parse after entity substitution. "
            f"An undeclared entity was added upstream -- add it to EXTRA_ENTITIES "
            f"rather than letting the files drop silently."
        )
    return volumes, marks


if __name__ == "__main__":
    v, m = ingest()
    print(f"{len(v)} volume-reader records, {len(m)} marks, "
          f"{sum(1 for x in m if x.tier == TIER_AUTOGRAPH)} autograph")
