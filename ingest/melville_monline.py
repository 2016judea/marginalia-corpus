'''
    Author: Aidan Jude

    Melville's Marginalia Online -> normalized Volume/Mark records.

    One HTTP request per volume:
        https://melvillesmarginalia.org/XmlDownload.ashx?DocId=N&Stage=False

    DocIds are not contiguous and are not published anywhere. Sweeping
    1..N and keeping what parses is the only enumeration available; 52 of
    140 responded on 2026-08-27. Re-sweep rather than hardcoding the list,
    because the project adds digital copies as transcription permits (its
    Search page says so outright) -- but DO cache, because a full sweep is
    140 requests against a small academic host.

    NOT the GitHub mirror. github.com/monline/xml exists and holds only 5
    of the 52 volumes (130-Channing, 277-Homer, 278-Homer, 385b-Milton,
    460-Shakespeare) and was last touched years before the live endpoint.
    A session that finds the repo first will build a corpus 10% the real
    size and believe it is complete. Verified 2026-08-27.

    Mark structure (verified against DocId 31, King Lear Vol. 7):
        <div page="460_7_7.012" type="score" type2="xmark" attribution="HM"
             sealts="460_7" x=".." y=".." play="7c">
          <line n="1"><w>Nothing</w><w>can</w>...</line>
        </div>

      type         the mark. 62 distinct values across the corpus, from
                   `score` (1,846) down to `fist` (1). Kept RAW -- do not
                   normalize a vocabulary this considered.
      type2        a decoration on a verbal note (annotation + xmark).
      attribution  WHOSE HAND. 'HM' Herman, 'ESM' Elizabeth Shaw Melville,
                   'HMorESM' ambiguous, 'Unattributed', 'Other'. 433 of
                   4,864 marks are HM-or-ESM ambiguous; a corpus that
                   silently credits those to Herman overstates him by ~9%.
      <w> content  IS THE READER'S WORDS on a verbal type, and the SOURCE
                   AUTHOR'S PRINTED WORDS on every other type. See
                   schema.py.
'''

import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

import names
import rights
from schema import Mark, Volume, tier_for, TIER_AUTOGRAPH

SOURCE = "monline"
BASE = "https://melvillesmarginalia.org"
UA = {"User-Agent": "marginalia-corpus/1.0 (personal research; aidanjude2016@gmail.com)"}
DID_RANGE = range(1, 141)
CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache", SOURCE)

READER = "melville"
HANDS = {"HM": "Herman Melville", "ESM": "Elizabeth Shaw Melville",
         "HMorESM": "Herman Melville or Elizabeth Shaw Melville",
         "Unattributed": "unattributed", "Other": "other"}


def _fetch(did):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"doc{did}.xml")
    if os.path.exists(path) and os.path.getsize(path) > 400:
        return open(path, "rb").read()
    url = f"{BASE}/XmlDownload.ashx?DocId={did}&Stage=False"
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
    except Exception:
        return None
    if len(raw) < 400:
        return None
    open(path, "wb").write(raw)
    return raw


def _words(div):
    '''
        Flatten <w> to a string, in page order. <choice><orig>/<reg> is the project's
        normalization of 19c orthography and contractions -- keep `orig`,
        which is what is physically on the page. Taking `reg` would silently
        modernize a transcription whose whole value is fidelity, and a <w>
        can carry SEVERAL <reg> children for one <orig> ("Here's" -> "Here
        is" + "Here" + "is"), so a naive itertext() triples words.

        Two shapes that read as nothing with a direct-children walk (2026-10-18):
          - a <line> nested INSIDE a <line>, where a mark runs into the margin
            (doc101 p.247_2_136: "Perugino" sat in the inner line); 235 marks
            lost words that way. iter("w") takes every word in document order.
          - a word broken over a line: <choice><hyph>mas-</hyph><reg>massiveness,</reg>
            </choice> with NO <orig>; 1,618 of those read as "" and the next
            line's "siveness," stood alone. The <hyph> half IS what the page
            shows; <missp> likewise; a bare <choice> carries its own text.
    '''
    out = []
    for w in div.iter("w"):
        ch = w.find("choice")
        if ch is not None:
            for tag in ("orig", "hyph", "missp"):
                e = ch.find(tag)
                if e is not None:
                    out.append((e.text or "").strip())
                    break
            else:
                out.append((ch.text or "").strip())
        else:
            out.append("".join(w.itertext()).strip())
    return re.sub(r"\s+", " ", " ".join(x for x in out if x)).strip()


def _header(root):
    src = root.find(".//sourceDesc//monogr")
    author = title = date = ""
    if src is not None:
        a, t = src.find("author"), src.find("title")
        author = " ".join((a.text or "").split()) if a is not None else ""
        title = " ".join((t.text or "").split()) if t is not None else ""
        d = src.find(".//date")
        if d is not None:
            date = (d.get("when") or (d.text or "")).strip()
    ms = root.find(".//msIdentifier")
    repo = shelf = ""
    if ms is not None:
        for tag, dest in (("repository", "repo"), ("idno", "shelf")):
            e = ms.find(tag)
            if e is not None:
                v = " ".join((e.text or "").split())
                repo, shelf = (v, shelf) if dest == "repo" else (repo, v)
    return author, title, date, repo, shelf


def ingest(did_range=DID_RANGE, workers=6):
    emit_text = rights.may_emit_text(SOURCE)
    volumes, marks = [], []

    with ThreadPoolExecutor(workers) as ex:
        payloads = list(ex.map(_fetch, list(did_range)))

    for did, raw in zip(did_range, payloads):
        if raw is None:
            continue
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            continue
        author, title, date, repo, shelf = _header(root)
        vol_id = f"{SOURCE}:{did}"
        divs = [d for d in root.iter("div") if d.get("page")]

        seen_ids = {}
        for d in divs:
            mtype = (d.get("type") or "unknown").strip()
            text = _words(d)
            tier = tier_for(mtype, bool(text))
            page = d.get("page") or ""
            printed_page = page.rsplit(".", 1)[-1] if "." in page else ""
            # MMO's @id restarts per page and is reused within one (two id="2"
            # divs on doc32 p.465_127, in different groups); a repeat takes an
            # ordinal so two marks never share an id.
            base_id = f'{vol_id}:{page}:{d.get("id")}'
            seen_ids[base_id] = seen_ids.get(base_id, 0) + 1
            m = Mark(
                mark_id=base_id if seen_ids[base_id] == 1 else f"{base_id}#{seen_ids[base_id]}",
                volume_id=vol_id,
                reader_id=READER,
                tier=tier,
                mark_type=mtype if not d.get("type2") else f'{mtype}+{d.get("type2")}',
                page=printed_page or page,
                marked_text=(text if tier != TIER_AUTOGRAPH and emit_text else ""),
                reader_text=(text if tier == TIER_AUTOGRAPH and emit_text else ""),
                hand=HANDS.get(d.get("attribution") or "", d.get("attribution") or ""),
                # Only a bare 'HM' is confidently Herman. 433 marks are
                # 'HMorESM' and 177 'Unattributed'; counting those as his
                # overstates him by ~13%.
                hand_is_reader=(d.get("attribution") == "HM"),
                text_withheld=bool(tier == TIER_AUTOGRAPH and text and not emit_text),
                url=f"{BASE}/Viewer.aspx?did={did}",
            )
            marks.append(m.validate())

        volumes.append(Volume(
            volume_id=vol_id, source_dataset=SOURCE, reader_id=READER,
            source_author=names.canonical(author), source_author_raw=author,
            source_title=title, source_date=date,
            repository=repo, shelfmark=shelf,
            url=f"{BASE}/Viewer.aspx?did={did}", n_marks=len(divs),
        ))

    return volumes, marks, []


if __name__ == "__main__":
    v, m, _ = ingest()
    print(f"{len(v)} volumes, {len(m)} marks, "
          f"{sum(1 for x in m if x.tier == TIER_AUTOGRAPH)} autograph")
