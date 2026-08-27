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

    plus `n_own_hand`, the subset of n_T1+n_T2 the source attributes
    confidently to the named reader rather than ambiguously. 433 of
    Melville's marks are "Herman or his wife Elizabeth"; 6 of Derrida's are
    Marguerite's or unattributed. Claiming those overstates the reader.

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

    A SECOND, separate edge set is emitted alongside: reference edges, from
    _data/references.jsonl. Those are not marks -- they are the reader
    NAMING another author, in a marginal note (AOR: 8,483 people, 1,158
    works) or in their own published book (Derrida: 1,052 in De la
    grammatologie). Different measurement, own key, never summed with the
    mark tiers. See schema.Reference.

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

    edges = defaultdict(lambda: dict(n_T1=0, n_T2=0, n_T3=0, n_own_hand=0,
                                     volumes=set(), datasets=set(), mark_types=set(),
                                     source_dates=set(), read_windows=set()))
    stranded = defaultdict(int)
    self_edges = defaultdict(int)

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
        if src == readers[m["reader_id"]]["name"]:
            # Derrida owned and annotated 5 of his own offprints. A reader
            # marking their own book is not influence; counted, not emitted.
            self_edges[m["reader_id"]] += 1
            continue
        e = edges[(m["reader_id"], src)]
        e[TIER_KEY[m["tier"]]] += 1
        if m.get("hand_is_reader", True) and m["tier"] != "T3_copy":
            e["n_own_hand"] += 1
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
            n_own_hand=e["n_own_hand"],
            n_marks=e["n_T1"] + e["n_T2"] + e["n_T3"],
            passage_anchored=bool(e["n_T1"] or e["n_T2"]),
            datasets=sorted(e["datasets"]),
            edition_dates=sorted(e["source_dates"]),
            reading_windows=sorted(e["read_windows"]),
            mark_types=sorted(e["mark_types"])[:12],
        ))

    # ---- reference edges: the reader naming an author, in their own words ----
    refs = load("references.jsonl")
    redges = defaultdict(lambda: dict(kinds=defaultdict(int), targets=set(),
                                      ids=set(), works=set(), datasets=set()))
    unresolved = defaultdict(int)
    for r in refs:
        # A reference resolves to an AUTHOR when the source supplies one
        # (a cited work). A <person> tag names a person who may or may not be
        # an author -- Hannibal and Socrates are named as often as Cicero -- so
        # those are kept on target_name and counted, never promoted to an
        # authorial edge.
        tgt = (r.get("target_author") or "").strip()
        if not tgt:
            unresolved[f'{r["source_dataset"]}:{r["kind"]}'] += 1
            continue
        e = redges[(r["reader_id"], tgt)]
        e["kinds"][r["kind"]] += 1
        e["targets"].add(r.get("target_name") or "")
        e["datasets"].add(r["source_dataset"])
        if r.get("target_id"):
            e["ids"].add(r["target_id"])
        if r.get("in_work"):
            e["works"].add(r["in_work"])
    # ---- persons named in a note who are not attached to a work ----
    # 8,483 <person> tags. Hannibal, Socrates and Eutrapelus are named as
    # often as Cicero, so these are PEOPLE the reader reached for, not
    # necessarily authors. Kept keyed on the name with AOR's ISNI, and
    # deliberately NOT promoted into the authorial edge set.
    named = defaultdict(lambda: dict(n=0, ids=set(), volumes=set(), datasets=set()))
    for r in refs:
        if (r.get("target_author") or "").strip() or r["kind"] != "named_in_note":
            continue
        k = (r["reader_id"], r.get("target_name") or "")
        named[k]["n"] += 1
        named[k]["volumes"].add(r.get("in_volume") or "")
        named[k]["datasets"].add(r["source_dataset"])
        if r.get("target_id"):
            named[k]["ids"].add(r["target_id"])
    nrows = [dict(reader_id=rid, reader=readers[rid]["name"], person=nm,
                  n_mentions=v["n"], isni=sorted(v["ids"])[:1],
                  n_volumes=len({x for x in v["volumes"] if x}),
                  datasets=sorted(v["datasets"]))
             for (rid, nm), v in sorted(named.items(), key=lambda kv: -kv[1]["n"]) if nm]

    rrows = [dict(
        reader_id=rid, reader=readers[rid]["name"], target_author=tgt,
        n_references=sum(e["kinds"].values()), kinds=dict(e["kinds"]),
        works_named=sorted(x for x in e["targets"] if x)[:10],
        in_works=sorted(e["works"]), identifiers=sorted(e["ids"])[:4],
        datasets=sorted(e["datasets"]),
    ) for (rid, tgt), e in sorted(redges.items(), key=lambda kv: -sum(kv[1]["kinds"].values()))]

    payload = dict(
        note=("Directed edges from PHYSICAL evidence of reading. Tiers are "
              "separate measurements; do not sum them. See build_edges.py."),
        n_edges=len(rows),
        n_marks_stranded_no_source_author=dict(stranded),
        n_self_edge_marks_excluded=dict(self_edges),
        edges=rows,
        reference_note=("The reader NAMING an author, in a marginal note or in their "
                        "own published work. A separate measurement from the mark "
                        "tiers -- never sum the two."),
        n_reference_edges=len(rrows),
        n_references_without_an_author=dict(unresolved),
        reference_edges=rrows,
        named_person_note=("People named inside a marginal note who are not attached "
                           "to a cited work. NOT authors -- Hannibal and Socrates are "
                           "here too. Never merge into reference_edges."),
        n_named_person_edges=len(nrows),
        named_person_edges=nrows,
    )
    with open(os.path.join(OUT, "edges.json"), "w") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)

    print(f"{len(rows)} edges over {len({r['reader_id'] for r in rows})} readers")
    print(f"stranded marks (source author unresolved): {dict(stranded)}\n")
    print(f'{"reader":<16} {"source author":<26} {"vols":>4} {"T1":>6} {"T2":>7} {"T3":>4} {"own":>6}')
    for r in rows[:24]:
        print(f'{r["reader"]:<16} {r["source_author"][:26]:<26} {r["n_volumes"]:>4} '
              f'{r["n_T1"]:>6} {r["n_T2"]:>7} {r["n_T3"]:>4} {r["n_own_hand"]:>6}')
    print(f'\nself-edge marks excluded (a reader in their own book): {dict(self_edges)}')
    print(f'{len(nrows)} NAMED-PERSON edges (persons, not authors) -- top: '
          f'{[(r["reader"].split()[-1], r["person"], r["n_mentions"]) for r in nrows[:6]]}')
    print(f'\n{len(rrows)} REFERENCE edges (the reader naming an author)')
    print(f'references with no author attached: {dict(unresolved)}')
    for r in rrows[:14]:
        print(f'{r["reader"]:<16} {r["target_author"][:30]:<30} {r["n_references"]:>4}  {r["kinds"]}')


if __name__ == "__main__":
    main()
