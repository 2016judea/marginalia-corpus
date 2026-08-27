'''
    Author: Aidan Jude

    The Beckett Digital Library -> Volume/Mark records.

    Samuel Beckett's personal library, digitally reconstructed from the
    volumes surviving in his Paris apartment, the Beckett International
    Foundation, and private collections. Editors Dirk Van Hulle, Mark Nixon
    and Vincent Neyt.

    ---- it was written off as subscription-only, and that was wrong ----

    The BDMP sells a subscription and a first pass concluded the library was
    behind it (the browse index returns a 2.3 KB shell to a bare curl). What
    the subscription actually buys is the **facsimile images**. The
    bibliography, the reading-trace page lists, the dated student-library
    reading notes, AND the marginalia transcriptions are all public.

    Three public routes, all server-rendered:

        library/Author/{A..Z}       872 items, sorted by author, with place,
                                   publisher, date, edition, inscriptions,
                                   current location and reading-trace pages
        library/Marginalia/{A..Z}   the subset with margin annotations
        library/search/index.html?q=marginalia&index=library
              &doc=library-readingtraces&start=N
                                   **2,685 marginalia entries**, 10 per page

    That last one is the find. `doc=library-readingtraces` with NO book id
    is the whole-library reading-traces document; appending `-<BOOKID>`
    scopes it to one book. Each hit gives exactly the two fields this
    corpus is built on, already separated at the source:

        Reading Trace:   what BECKETT wrote or drew   -> reader_text
        Marked Passage:  the SOURCE AUTHOR's printed words -> marked_text

        Shakespeare, Macbeth, p. tp1, Zone 1
          Reading Trace: "Skeleton of Macbeth."
        Proust, Du Côté de chez Swann, p. 73, Zone 1
          Reading Trace: "Base senses (Kant)"

    Note that second one: Beckett writing *Kant* in the margin of *Proust*.
    A reader connecting two authors in his own hand.

    ---- RIGHTS: the strictest source in the corpus, and correctly so ----

    Beckett died in 1989. His marginalia are **unpublished work still in
    copyright**, controlled by the Estate, and the BDMP is a subscription
    publication. So emit_text is FALSE: this slice ships tiers, mark types,
    page numbers, zones, source authors and counts -- and no text at all,
    not even the marked passage. Nothing analytical is lost for the
    influence graph, which needs to know *which author* and *which page*,
    not the words.

    A T1 here therefore always carries text_withheld=True. Note the reason
    differs from AOR and Whitman: there the licence is merely unstated, here
    the underlying work is in copyright for another thirty-odd years.

    ---- what the free layer contains ----

    * 872 volumes he owned, by author, with edition and inscriptions
    * 2,685 marginalia entries at page and zone grain
    * per-book reading-trace page lists (a page with a trace but no
      transcribed marginalia is a T2)
    * "Student library" reading DATES with their scholarly sources, e.g.
      Proust vol. I: "Read: by October 1927, Summer 1929, Summer 1930",
      cited to Letters of Samuel Beckett vol. I p. 11 and Pilling 2006 p. 26
'''

import html
import os
import re
import time
import urllib.request

import names
import rights
from schema import Mark, Volume, TIER_AUTOGRAPH, TIER_MARK, TIER_COPY

SOURCE = "beckett"
READER = "beckett"
BASE = "https://www.beckettarchive.org/library"
SEARCH = (BASE + "/search/index.html?q=marginalia&index=library"
                 "&doc=library-readingtraces&start={}")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache", SOURCE)
UA = {"User-Agent": "marginalia-corpus/1.0 (personal research; aidanjude2016@gmail.com)"}
LETTERS = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
PER_PAGE = 10
PAUSE = 0.35          # a small academic host; 300-odd requests, be polite


def _get(url, name):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, name)
    if os.path.exists(p) and os.path.getsize(p) > 3000:
        return open(p, encoding="utf-8", errors="replace").read()
    time.sleep(PAUSE)
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
    text = raw.decode("utf-8", errors="replace")
    if len(text) < 3000:
        raise RuntimeError(f"{url} returned {len(text)} bytes -- the browse index serves "
                           f"a 2.3 KB shell to some clients; check before trusting a "
                           f"short page as 'no results'.")
    open(p, "w", encoding="utf-8").write(text)
    return text


def _txt(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


ENTRY = re.compile(r'<a name="([A-Z0-9\-]+)"></a>', re.I)


def _books():
    '''library/Author/{A..Z} -> one record per volume Beckett owned.'''
    out = {}
    for L in LETTERS:
        h = _get(f"{BASE}/Author/{L}", f"author_{L}.html")
        for block in h.split('<div class="entryEL">')[1:]:
            m = ENTRY.search(block)
            if not m:
                continue
            bid = m.group(1)
            g = lambda cls: _txt((re.search(r'<span class="%s">(.*?)</span>' % cls,
                                            block, re.S) or [None, ""])[1])
            author = g("library-authorcurrent").rstrip(":").strip()
            # "Abrahams, Gerald" -> canonical; the surname sits outside the
            # inner span, so the flip in names.py does the work.
            traces = re.search(r'<span class="library-rt-pagenumbers">(.*?)</span>', block, re.S)
            pages = [p.strip().rstrip("*") for p in _txt(traces.group(1)).split(",")] if traces else []
            out[bid] = dict(
                book_id=bid, author=author, title=g("library-title"),
                place=g("library-place").rstrip(": ").strip(),
                publisher=g("library-publisher").rstrip(", ").strip(),
                date=g("library-date"),
                inscription=g("library-dedication"),
                trace_pages=[p for p in pages if p],
            )
    return out


def _marginalia_books():
    '''library/Marginalia/{A..Z} -> the subset with margin annotations.'''
    ids = set()
    for L in LETTERS:
        h = _get(f"{BASE}/Marginalia/{L}", f"marg_{L}.html")
        ids |= set(ENTRY.findall(h))
    return ids


ROW = re.compile(
    r'href="\.\./\.\./library/([A-Z0-9\-]+)\.html\?page=([^&"]*)&amp;zone=(\d+)"'
    r'(.*?)<b>Reading Trace:</b>(.*?)<b>Marked Passage:</b>(.*?)</span>', re.S)


def _marginalia():
    '''
        The whole-library reading-traces search, paged 10 at a time.
        `Found N hits` is read from page 0 and drives the sweep -- do not
        hardcode 2,685; the project is still adding volumes.
    '''
    first = _get(SEARCH.format(0), "search_0.html")
    m = re.search(r"Found\s*([\d,]+)\s*hits", _txt(first))
    if not m:
        raise RuntimeError("search page carries no hit count -- the results template "
                           "changed; re-read it before sweeping 270 pages.")
    total = int(m.group(1).replace(",", ""))
    out = []
    for start in range(0, total, PER_PAGE):
        h = first if start == 0 else _get(SEARCH.format(start), f"search_{start}.html")
        for bid, page, zone, head, trace, marked in ROW.findall(h):
            t = re.search(r"<Transcription>(.*?)</Transcription>", trace, re.S)
            out.append(dict(book_id=bid, page=html.unescape(page), zone=int(zone),
                            reader_text=_txt(t.group(1)) if t else _txt(trace),
                            marked_text=_txt(marked)))
    if len(out) < total * 0.9:
        raise RuntimeError(f"parsed {len(out)} of {total} marginalia rows -- the result "
                           f"row template changed; fix ROW rather than shipping a "
                           f"silently truncated slice.")
    return out, total


def ingest():
    emit_text = rights.may_emit_text(SOURCE)
    books = _books()
    marg_books = _marginalia_books()
    rows, total = _marginalia()

    vols, marks = {}, []
    unknown_book = 0

    def volume(bid):
        b = books.get(bid)
        if b is None:
            return None
        v = vols.get(bid)
        if v is None:
            v = vols[bid] = Volume(
                volume_id=f"{SOURCE}:{bid}", source_dataset=SOURCE, reader_id=READER,
                source_author=names.canonical(b["author"]),
                source_author_raw=b["author"],
                source_title=b["title"], source_date=b["date"],
                repository=b["place"] or "", shelfmark="",
                url=f"{BASE}/{bid}.html", n_marks=0,
                evidence_source=(b["inscription"] or "")[:200],
            )
        return v

    seen_pages = set()
    for i, r in enumerate(rows):
        v = volume(r["book_id"])
        if v is None:
            unknown_book += 1
            continue
        v.n_marks += 1
        seen_pages.add((r["book_id"], r["page"]))
        marks.append(Mark(
            mark_id=f'{SOURCE}:{r["book_id"]}:{r["page"]}:{r["zone"]}:{i}',
            volume_id=v.volume_id, reader_id=READER,
            tier=TIER_AUTOGRAPH if r["reader_text"] else TIER_MARK,
            mark_type=f'marginalia:zone{r["zone"]}',
            page=r["page"],
            reader_text=(r["reader_text"] if emit_text else ""),
            marked_text=(r["marked_text"] if emit_text else ""),
            text_withheld=bool(r["reader_text"] and not emit_text),
            hand="Samuel Beckett", hand_is_reader=True,
            url=f'{BASE}/{r["book_id"]}.html?page={r["page"]}&zone={r["zone"]}',
        ).validate())

    # A page listed as carrying a reading trace but with no transcribed
    # marginalia is a mark without words: T2. Underlinings, dog-ears, marks.
    for bid, b in books.items():
        v = None
        for pg in b["trace_pages"]:
            if (bid, pg) in seen_pages:
                continue
            v = v or volume(bid)
            if v is None:
                continue
            v.n_marks += 1
            marks.append(Mark(
                mark_id=f"{SOURCE}:{bid}:{pg}:trace",
                volume_id=v.volume_id, reader_id=READER, tier=TIER_MARK,
                mark_type="reading_trace", page=pg,
                hand="Samuel Beckett", hand_is_reader=True,
                url=f"{BASE}/{bid}.html?page={pg}",
            ).validate())

    # Every remaining volume is attested ownership with no surviving trace: T3.
    for bid, b in books.items():
        if bid in vols:
            continue
        v = volume(bid)
        if v is None:
            continue
        v.n_marks = 0
        marks.append(Mark(
            mark_id=f"{SOURCE}:{bid}:owned", volume_id=v.volume_id, reader_id=READER,
            tier=TIER_COPY, mark_type="attested_ownership",
            hand="", hand_is_reader=True, url=f"{BASE}/{bid}.html",
        ).validate())

    stats = dict(library_items=len(books), books_with_marginalia=len(marg_books),
                 marginalia_rows_reported=total, marginalia_rows_parsed=len(rows),
                 marginalia_rows_unknown_book=unknown_book)
    return list(vols.values()), marks, [], stats


if __name__ == "__main__":
    v, m, _, s = ingest()
    from collections import Counter
    c = Counter(x.tier for x in m)
    print(f"{len(v)} volumes, {len(m)} marks {dict(c)}")
    print("stats:", s)
    print(f"distinct source authors: {len({x.source_author for x in v if x.source_author})}")
    top = Counter()
    for x in v:
        top[x.source_author] += x.n_marks
    for a, n in top.most_common(14):
        print(f"  {n:>4}  {a}")
