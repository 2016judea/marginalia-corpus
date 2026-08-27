'''
    Author: Aidan Jude

    The Walt Whitman Archive -> Volume/Mark records. Two slices, and the
    SECOND one is the reason to bother.

    Source: github.com/whitmanarchive/whitman-marginalia (branch `dev`,
    pushed 2025-08-13 -- live, unlike the other two). 214 XML files, 14 MB.
    The public site is behind a Cloudflare JS challenge and 403s every
    scripted fetch, browser User-Agent or not; the GitHub data repo is the
    only scriptable route in. Verified 2026-08-27.

    ---- slice 1: the marginalia items (148 TEI files) ----

    Whitman's annotations are mostly NOT marks in a printed book. They are
    reading notes on loose sheets, clipped articles, and a 1,200-page
    cultural-geography scrapbook. So the source work he is responding to is
    named in PROSE inside <notesStmt> ("based partly on Volney's Ruins; or
    Meditations on the Revolution of Empires") and not in any structured
    field: <sourceDesc><bibl> describes the MANUSCRIPT (its shelfmark and
    holding library), never the book being read.

    Therefore source_author is left EMPTY on this slice, and that is a
    deliberate refusal, not an oversight. Regexing an author out of an
    editor's prose note would put a guessed citation into an influence
    graph whose entire claim is that its edges are physical facts. The
    resolution route exists and is slice 2's authority file plus the
    per-item notesStmt read by hand.

    ---- slice 2: the Bibliographical Handlist (anc.02129) ----

    One authority file, 214 <bibl> records: everything Whitman is
    documented to have read, each with a normalized @key author, a title,
    the edition, the SCHOLARLY SOURCE of the claim, and:

        <date type="readingDate">1881-1892</date>
        <note type="reaction">Several reactions over at least four
          readings. Extensive markings, with narrative of his readings in
          endpapers. One of WW's favorites.</note>

    A reading DATE is the thing no attribution source has. literature-
    mutations' Phase 2 permits an edge A->B only when A's earliest work
    predates B's -- "real literary chronology, not personal reading order",
    because personal reading order was not available. Here it is.

    BUT COUNT IT, DON'T GREP IT. `grep -c 'type="readingDate"'` returns 214
    and every one of those elements is real. **186 of them are EMPTY** --
    `<date type="readingDate"/>`, no text, no notBefore/notAfter. The field
    is in the schema and mostly unpopulated. The actual reading-date payload
    is **28 works**, and a session that trusts the grep will report an
    8x-inflated figure. Same trap on the reaction/comments/source notes:
    all 214 present, and `details` only 24. Measured 2026-08-27.

    The reaction note also grades the evidence: records whose reaction
    mentions markings/annotation are T2-or-better, the rest are T3.

    RIGHTS: the Archive's own <availability> says "Copyright (c) 2014 by Ed
    Folsom and Kenneth M. Price, all rights reserved... Redistribution or
    republication on other terms, in any medium, requires express written
    consent from the editors." So emit_text is False for this source and
    the text stays in cache/. Counts, dates and edges are facts about the
    record, not the record.
'''

import os
import re
import subprocess
import xml.etree.ElementTree as ET

import names
import rights
from schema import Mark, Volume, TIER_AUTOGRAPH, TIER_MARK, TIER_COPY

SOURCE = "whitman"
REPO = "https://github.com/whitmanarchive/whitman-marginalia.git"
BRANCH = "dev"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache", SOURCE)
NS = "{http://www.tei-c.org/ns/1.0}"
READER = "whitman"
HANDLIST = "anc.02129"

# <hi rend="..."> values that are a reader's mark on the page rather than
# typographic rendering of printed text. `italic` and `smallcaps` are the
# printed source's own styling and are NOT marks -- counting them would
# inflate Whitman's 705 real marks to 2,020.
MARK_RENDS = {"underline", "doubleUnderline", "circled"}


def fetch():
    if os.path.isdir(os.path.join(CACHE, ".git")):
        return CACHE
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    subprocess.run(["git", "clone", "-q", "--depth", "1", "-b", BRANCH, REPO, CACHE], check=True)
    return CACHE


def _txt(e):
    return re.sub(r"\s+", " ", "".join(e.itertext())).strip() if e is not None else ""


def _handlist(path, emit_text):
    '''slice 2 -> T3 volumes (+T2 where the reaction attests markings)'''
    f = os.path.join(path, "source", "authority", f"{HANDLIST}.xml")
    if not os.path.exists(f):
        raise RuntimeError(f"handlist {HANDLIST} missing from {path} -- the authority "
                           f"file moved; re-check the repo layout before trusting counts.")
    root = ET.parse(f).getroot()
    volumes, marks = [], []
    # Scope to <listBibl>: the file holds 220 <bibl>, of which 214 are handlist
    # records and 6 are citations in the editor's own introduction.
    bibls = [b for L in root.iter(f"{NS}listBibl") for b in L.findall(f"{NS}bibl")]
    for bib in bibls:
        bid = bib.get(f"{{http://www.w3.org/XML/1998/namespace}}id") or ""
        a = bib.find(f"{NS}author")
        # @key is the Archive's normalized form; the element text is the
        # catalogue form ("Bell, George Joseph"). Both need names.canonical()
        # or the handlist's 187 authors sit in their own namespace and never
        # join Melville's or Derrida's.
        author = (a.get("key") or _txt(a)) if a is not None else ""
        title = _txt(bib.find(f'{NS}title'))
        pub = read = ""
        for d in bib.findall(f"{NS}date"):
            # The date can be element text ("1881-1892") or only attributes
            # (notBefore/notAfter). Reading text alone found 28 of 214.
            v = _txt(d) or "/".join(x for x in (d.get("notBefore"), d.get("notAfter")) if x)
            if d.get("type") == "publicationDate":
                pub = v
            elif d.get("type") == "readingDate":
                read = v
        reaction = attests = ""
        for n in bib.findall(f"{NS}note"):
            if n.get("type") == "reaction":
                reaction = _txt(n)
            elif n.get("type") == "source":
                r = n.find(f"{NS}ref")
                attests = (r.get("target") or "").lstrip("#") if r is not None else _txt(n)
        marked = bool(re.search(r"mark|annotat|underlin|note[sd]? in", reaction, re.I))
        vol_id = f"{SOURCE}:handlist:{bid}"
        volumes.append(Volume(
            volume_id=vol_id, source_dataset=SOURCE, reader_id=READER,
            source_author=names.canonical(author), source_author_raw=author,
            source_title=title, source_date=pub,
            repository="", url="https://whitmanarchive.org/item/anc.02129",
            n_marks=1 if marked else 0,
            read_from=read.split("-")[0].split("/")[0] if read else "",
            read_to=(read.split("-")[-1].split("/")[-1] if read else ""),
            evidence_source=attests,
        ))
        marks.append(Mark(
            mark_id=f"{vol_id}:attested",
            volume_id=vol_id, reader_id=READER,
            tier=TIER_MARK if marked else TIER_COPY,
            mark_type="attested_markings" if marked else "attested_reading",
            marked_text="", reader_text="",
            # the reading window is the payload of this slice
            page=read,
            translation=reaction if emit_text else "",
            url="https://whitmanarchive.org/item/anc.02129",
        ).validate())
    return volumes, marks


def ingest():
    emit_text = rights.may_emit_text(SOURCE)
    path = fetch()
    volumes, marks = _handlist(path, emit_text)

    tei_dir = os.path.join(path, "source", "tei")
    for fn in sorted(os.listdir(tei_dir)):
        if not fn.endswith(".xml"):
            continue
        item = fn[:-4]
        root = ET.parse(os.path.join(tei_dir, fn)).getroot()
        body = root.find(f".//{NS}text")
        if body is None:
            continue
        t = root.find(f".//{NS}titleStmt/{NS}title")
        title = _txt(t)
        bibl = root.find(f".//{NS}sourceDesc//{NS}bibl")
        repo = ""
        if bibl is not None:
            # the holding library, i.e. where the MANUSCRIPT is -- not the book read
            for n in bibl.iter():
                if n.tag in (f"{NS}repository", f"{NS}institution"):
                    repo = _txt(n)
        vol_id = f"{SOURCE}:item:{item}"
        n = 0
        for i, add in enumerate(body.iter(f"{NS}add")):
            words = _txt(add)
            if not words:
                continue
            marks.append(Mark(
                mark_id=f"{vol_id}:add{i}", volume_id=vol_id, reader_id=READER,
                tier=TIER_AUTOGRAPH, mark_type="add",
                reader_text=words if emit_text else "",
                text_withheld=not emit_text,
                hand=add.get("hand") or "",
                url=f"https://whitmanarchive.org/item/{item}",
            ).validate())
            n += 1
        for i, hi in enumerate(body.iter(f"{NS}hi")):
            if hi.get("rend") not in MARK_RENDS:
                continue
            marks.append(Mark(
                mark_id=f"{vol_id}:hi{i}", volume_id=vol_id, reader_id=READER,
                tier=TIER_MARK, mark_type=f'hi:{hi.get("rend")}',
                marked_text=_txt(hi) if emit_text else "",
                url=f"https://whitmanarchive.org/item/{item}",
            ).validate())
            n += 1
        volumes.append(Volume(
            volume_id=vol_id, source_dataset=SOURCE, reader_id=READER,
            source_author="",              # deliberate: see module docstring
            source_title=title, repository=repo,
            url=f"https://whitmanarchive.org/item/{item}", n_marks=n,
        ))
    return volumes, marks, []


if __name__ == "__main__":
    v, m, _ = ingest()
    from collections import Counter
    c = Counter(x.tier for x in m)
    print(f"{len(v)} volumes, {len(m)} records  {dict(c)}")
    print(f"handlist works with a reading date: "
          f"{sum(1 for x in m if x.mark_type.startswith('attested') and x.page)}")
