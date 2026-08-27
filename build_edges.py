'''
    Author: Aidan Jude

    The corpus -> a directed influence edge set, for import into
    literature-mutations.

    Edge = (reader_author -> source_author), one per pair, carrying
    SEPARATE per-tier weights. Tiers are never summed into one
    "influence score", for the same reason literature-mutations keeps its
    stylistic and conceptual similarities in separate fields: they are
    different measurements and the consumer must choose.

        n_T1  marks in the reader's own words, at a passage
        n_T2  non-verbal marks locating a passage
        n_T3  attested reading with no surviving mark

    What this edge set is FOR. literature-mutations' Phase 2 validates its
    author-similarity graph against two held-out sources, and both are
    interpretations:

        known_influences.json     377 relationships, LLM-enumerated
        wikidata_influences.json  350 P737 claims, 44 of 77 authors

    Both answer "who does the record say influenced whom". This answers a
    different question -- "who demonstrably read whom, and which passages
    did they stop on" -- and it is the only one of the three that carries a
    PASSAGE. Keep it in its own key, as Phase 2 already keeps its two.

    The measurement this data uniquely permits, and the reason it is worth
    building: do the passages a reader MARKED predict that reader's own
    later prose better than unmarked passages from the same volume? The
    known-positive control is on the shelf already -- Melville left 212
    marks in Beale's Natural History of the Sperm Whale, from which he
    demonstrably lifted into Moby-Dick. If the method cannot recover Beale,
    it cannot be trusted on Shakespeare.

    Out:  _data/edges.json
'''

import gzip
import json
import os
from collections import defaultdict

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_data")
TIER_KEY = {"T1_autograph": "n_T1", "T2_mark": "n_T2", "T3_copy": "n_T3"}


def load(name):
    path = os.path.join(OUT, name)
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    readers = {r["reader_id"]: r for r in json.load(open(os.path.join(OUT, "readers.json")))}
    volumes = {v["volume_id"]: v for v in load("volumes.jsonl")}
    marks = load("marks.jsonl.gz")

    edges = defaultdict(lambda: dict(n_T1=0, n_T2=0, n_T3=0, volumes=set(),
                                     datasets=set(), mark_types=set(),
                                     source_dates=set(), read_windows=set()))
    stranded = defaultdict(int)

    for m in marks:
        v = volumes.get(m["volume_id"])
        if v is None:
            continue
        src = (v["source_author"] or "").strip()
        if not src:
            # A mark whose source author is unresolved is real evidence that
            # cannot yet be an edge. Counted, never dropped silently, never
            # guessed -- see ingest/whitman.py and ingest/aor_books.json.
            stranded[v["source_dataset"]] += 1
            continue
        e = edges[(m["reader_id"], src)]
        e[TIER_KEY[m["tier"]]] += 1
        e["volumes"].add(m["volume_id"])
        e["datasets"].add(v["source_dataset"])
        e["mark_types"].add(m["mark_type"].split("+")[0].split(":")[0])
        if v.get("source_date"):
            e["source_dates"].add(v["source_date"])
        if v.get("read_from"):
            e["read_windows"].add(f'{v["read_from"]}-{v.get("read_to") or ""}'.rstrip("-"))

    rows = []
    for (rid, src), e in sorted(edges.items(), key=lambda kv: -(kv[1]["n_T1"] * 1000 + kv[1]["n_T2"])):
        rows.append(dict(
            reader_id=rid, reader=readers[rid]["name"], source_author=src,
            n_volumes=len(e["volumes"]),
            n_T1=e["n_T1"], n_T2=e["n_T2"], n_T3=e["n_T3"],
            n_marks=e["n_T1"] + e["n_T2"] + e["n_T3"],
            passage_anchored=bool(e["n_T1"] or e["n_T2"]),
            datasets=sorted(e["datasets"]),
            edition_dates=sorted(e["source_dates"]),
            reading_windows=sorted(e["read_windows"]),
            mark_types=sorted(e["mark_types"])[:12],
        ))

    payload = dict(
        note=("Directed edges from PHYSICAL evidence of reading. Tiers are "
              "separate measurements; do not sum them. See build_edges.py."),
        n_edges=len(rows),
        n_marks_stranded_no_source_author=dict(stranded),
        edges=rows,
    )
    with open(os.path.join(OUT, "edges.json"), "w") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)

    print(f"{len(rows)} edges over {len({r['reader_id'] for r in rows})} readers")
    print(f"stranded marks (source author unresolved): {dict(stranded)}\n")
    print(f'{"reader":<16} {"source author":<26} {"vols":>4} {"T1":>6} {"T2":>7} {"T3":>4}')
    for r in rows[:26]:
        print(f'{r["reader"]:<16} {r["source_author"][:26]:<26} {r["n_volumes"]:>4} '
              f'{r["n_T1"]:>6} {r["n_T2"]:>7} {r["n_T3"]:>4}')


if __name__ == "__main__":
    main()
