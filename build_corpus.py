'''
    Author: Aidan Jude

    Run every ingest adapter, validate, and write the normalized corpus.

    Out:  _data/readers.json     one row per annotating author
          _data/volumes.jsonl    one row per annotated volume (per reader)
          _data/marks.jsonl      one row per mark -- SHIPPED ONLY where
                                 rights.py permits the text; otherwise
                                 tiers, types, pages and counts, no text
          _data/manifest.json    what ran, how much, and the citation for
                                 every source, so a downstream consumer can
                                 attribute without reading this code

    Run:  python build_corpus.py
'''

import gzip
import json
import os
from collections import Counter
from dataclasses import asdict

import rights
from schema import Reader, TIER_AUTOGRAPH, TIER_MARK, TIER_COPY
from ingest import aor, derrida, melville_monline, nietzsche, whitman

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_data")

# Readers are declared here, not derived, because a reader is the unit of
# the whole corpus and a typo in an adapter must not invent one.
READERS = [
    Reader("melville", "Herman Melville", 1819, 1891, "Q4162",
           "Library of ~1,000 volumes at his death; 52 digitally transcribed."),
    Reader("whitman", "Walt Whitman", 1819, 1892, "Q81438",
           "Annotations mostly on loose sheets and clippings, not bound volumes."),
    Reader("harvey", "Gabriel Harvey", 1552, 1631, "Q1489443",
           "Spenser's correspondent; the most prolific annotator in AOR."),
    Reader("dee", "John Dee", 1527, 1609, "Q117783",
           "Not a literary author -- included because AOR is the reference "
           "implementation of a marginalia data model, and Dee is half of it."),
    Reader("winthrop", "John Winthrop", 1606, 1676, "Q1701206",
           "Three pages in AOR's Paracelsus_Meteorum only."),
    Reader("nietzsche", "Friedrich Nietzsche", 1844, 1900, "Q9358",
           "NO annotated volumes reachable: his ~1,100 surviving library books are "
           "digitised as facsimile only, Weimar blocks automated access, and the "
           "transcribed Lesespuren exist solely in the 2003 de Gruyter print "
           "catalogue. Present here through references in his own published prose."),
    Reader("derrida", "Jacques Derrida", 1930, 2004, "Q9364",
           "Library of ~13,800 volumes at PUL; this dataset is phase 1 only, "
           "the books behind De la grammatologie (1967)."),
]

ADAPTERS = [
    ("monline", melville_monline.ingest),
    ("aor", aor.ingest),
    ("whitman", whitman.ingest),
    ("derrida", derrida.ingest),
    ("nietzsche", nietzsche.ingest),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    known = {r.reader_id for r in READERS}
    all_vols, all_marks, all_refs, manifest = [], [], [], {}

    for key, fn in ADAPTERS:
        meta = rights.check(key)              # gate: no entry, no ingest
        vols, marks, refs = fn()
        stray = {v.reader_id for v in vols} - known
        if stray:
            raise RuntimeError(
                f"{key} emitted unknown reader(s) {sorted(stray)}. Add them to "
                f"READERS deliberately -- an adapter must not invent a reader."
            )
        for m in marks:
            m.validate()
        tiers = Counter(m.tier for m in marks)
        manifest[key] = dict(
            name=meta["name"], citation=rights.citation(key),
            text_emitted=meta["emit_text"], terms=meta["terms"],
            readers=sorted({v.reader_id for v in vols}),
            n_volumes=len(vols), n_marks=len(marks),
            n_autograph=tiers[TIER_AUTOGRAPH], n_mark=tiers[TIER_MARK],
            n_copy=tiers[TIER_COPY],
            n_text_withheld=sum(1 for m in marks if m.text_withheld),
            n_marks_in_readers_own_hand=sum(1 for m in marks if m.hand_is_reader),
            n_references=len(refs),
            n_source_authors=len({v.source_author for v in vols if v.source_author}),
        )
        all_vols += vols
        all_marks += marks
        all_refs += refs

    with open(os.path.join(OUT, "readers.json"), "w") as f:
        json.dump([asdict(r) for r in READERS], f, indent=1)
    def write(name, rowset, gz=False):
        path = os.path.join(OUT, f"{name}.jsonl" + (".gz" if gz else ""))
        opener = (lambda: gzip.open(path, "wt", encoding="utf-8")) if gz else (lambda: open(path, "w"))
        with opener() as f:
            for o in rowset:
                d = asdict(o)
                d = {k: (list(v) if isinstance(v, tuple) else v) for k, v in d.items()}
                f.write(json.dumps(d, ensure_ascii=False) + "\n")

    write("volumes", all_vols)
    write("references", all_refs)
    # 197k rows, 63 MB raw. Gzipped, matching literature-mutations'
    # reception_entries.jsonl.gz -- a submodule should not carry 63 MB.
    write("marks", all_marks, gz=True)
    stale = os.path.join(OUT, "marks.jsonl")
    if os.path.exists(stale):
        os.remove(stale)

    totals = Counter(m.tier for m in all_marks)
    manifest["_totals"] = dict(
        readers=len(READERS), volumes=len(all_vols), marks=len(all_marks),
        T1_autograph=totals[TIER_AUTOGRAPH], T2_mark=totals[TIER_MARK],
        T3_copy=totals[TIER_COPY], references=len(all_refs),
        source_authors=len({v.source_author for v in all_vols if v.source_author}),
    )
    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)

    for k, v in manifest.items():
        if k.startswith("_"):
            continue
        print(f'{k:<10} {v["n_volumes"]:>4} vols  {v["n_marks"]:>7} marks  '
              f'T1 {v["n_autograph"]:>6}  T2 {v["n_mark"]:>6}  T3 {v["n_copy"]:>4}  '
              f'{v["n_references"]:>5} refs  {v["n_source_authors"]:>3} authors  '
              f'text={"yes" if v["text_emitted"] else "WITHHELD"}')
    t = manifest["_totals"]
    print(f'\nTOTAL      {t["volumes"]:>4} vols  {t["marks"]:>7} marks   '
          f'T1 {t["T1_autograph"]}  T2 {t["T2_mark"]}  T3 {t["T3_copy"]}   '
          f'{t["references"]} refs   {t["source_authors"]} source authors   '
          f'{t["readers"]} readers')


if __name__ == "__main__":
    main()
