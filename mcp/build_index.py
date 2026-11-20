'''
    Author: Aidan Jude

    Builds mcp/index.json.gz, the one file the MCP server (api/mcp.js) loads.

        python mcp/build_index.py

    Run it after build_corpus.py / build_edges.py. Never hand-edit the output.

    The rights gate lives HERE, at build time, and is read from rights.py rather
    than retyped: a passage or reference row is only written when its source has
    emit_text=True. AOR, Whitman and Beckett therefore reach the server as counts,
    metadata and edges, with no transcription anywhere in the file, so no bug in
    the server can leak one. No image URL is written either (images_prohibited):
    Derrida's and Shakespeare and Company's per-mark links are IIIF image files and
    are dropped for the page they sit on.
'''
import collections
import gzip
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import rights  # noqa: E402

DATA = os.path.join(ROOT, "_data")
OUT = os.path.join(ROOT, "mcp", "index.json.gz")

TIER = {"T1_autograph": 1, "T2_mark": 2, "T3_copy": 3}
IMAGE_URL = re.compile(r"iiif|/loris/|figgy|\.(jpe?g|jp2|png|gif|tiff?|webp)(\?|$)|/full/\d|default\.jpg", re.I)
MAX_TEXT = 1500   # a passage longer than this is cut and flagged, never silently


def safe_url(u):
    u = (u or "").strip()
    if not u or IMAGE_URL.search(u):
        return ""
    return u


def cut(s):
    s = (s or "").strip()
    return (s[:MAX_TEXT].rstrip() + " …", 1) if len(s) > MAX_TEXT else (s, 0)


def source_of_volume(v):
    return v["source_dataset"]


def main():
    readers = json.load(open(os.path.join(DATA, "readers.json")))
    rix = {r["reader_id"]: i for i, r in enumerate(readers)}

    volumes = [json.loads(l) for l in open(os.path.join(DATA, "volumes.jsonl"))]
    vix = {v["volume_id"]: i for i, v in enumerate(volumes)}
    for v in volumes:
        rights.check(source_of_volume(v))

    # Per-volume counts: tier x own-hand, and the mark-type vocabulary.
    counts = [[0] * 7 for _ in volumes]   # n1 n2 n3 own1 own2 own3 withheld
    mtypes = [collections.Counter() for _ in volumes]
    passages = []
    n_marks = 0
    for line in gzip.open(os.path.join(DATA, "marks.jsonl.gz"), "rt"):
        m = json.loads(line)
        n_marks += 1
        i = vix[m["volume_id"]]
        v = volumes[i]
        src = source_of_volume(v)
        t = TIER[m["tier"]]
        c = counts[i]
        c[t - 1] += 1
        if m["hand_is_reader"]:
            c[t + 2] += 1
        if m["text_withheld"]:
            c[6] += 1
        mtypes[i][m["mark_type"]] += 1
        if not rights.may_emit_text(src):
            continue                                   # THE GATE
        marked, c1 = cut(m["marked_text"])
        said, c2 = cut(m["reader_text"])
        trans, c3 = cut(m["translation"])
        if not (marked or said):
            continue
        url = m["url"]
        if src == "derrida" and str(m["mark_id"]).startswith("https://derridas-margins.princeton.edu/interventions/"):
            url = m["mark_id"]                         # the intervention's page, not its image crop
        passages.append([i, t, m["mark_type"], m["page"], marked, said, trans,
                         m["hand"], 1 if m["hand_is_reader"] else 0, m["lang"],
                         safe_url(url) or safe_url(v["url"]), 1 if (c1 or c2 or c3) else 0])

    vol_rows = []
    for i, v in enumerate(volumes):
        top = "|".join(f"{k}:{n}" for k, n in mtypes[i].most_common(6))
        vol_rows.append([rix[v["reader_id"]], source_of_volume(v), v["source_author"], v["source_title"],
                         v["source_date"], v["repository"], v["shelfmark"], safe_url(v["url"]),
                         v["read_from"], v["read_to"], v.get("evidence_source", ""), *counts[i], top])

    refs = []
    for line in open(os.path.join(DATA, "references.jsonl")):
        r = json.loads(line)
        src = r["source_dataset"]
        if not rights.may_emit_text(src):
            continue                                   # THE GATE (AOR: names only, via ref_edges)
        anchor, c1 = cut(r["anchor_text"])
        in_vol = vix.get(r["in_volume"], -1)
        refs.append([rix[r["reader_id"]], src, r["kind"], r["in_work"], in_vol, r["target_name"],
                     r["target_author"], anchor, r["page"], safe_url(r["url"]), c1])

    e = json.load(open(os.path.join(DATA, "edges.json")))
    edges = [[rix[x["reader_id"]], x["source_author"], x["n_volumes"], x["n_T1"], x["n_T2"], x["n_T3"],
              x["n_own_hand"], 1 if x["passage_anchored"] else 0, x["datasets"]] for x in e["edges"]]
    ref_edges = [[rix[x["reader_id"]], x["target_author"], x["n_references"], x["kinds"],
                  x["works_named"][:8], x["in_works"][:8], x["datasets"]] for x in e["reference_edges"]]
    person_edges = [[rix[x["reader_id"]], x["person"], x["n_mentions"], x["n_volumes"], x["datasets"]]
                    for x in e["named_person_edges"]]

    manifest = json.load(open(os.path.join(DATA, "manifest.json")))
    sources = {}
    for k, s in rights.SOURCES.items():
        sources[k] = dict(name=s["name"], url=s["url"], editors=s["editors"], terms=s["terms"],
                          emit_text=bool(s["emit_text"]), images_prohibited=bool(s["images_prohibited"]),
                          attribution_required=bool(s["attribution_required"]),
                          citation=rights.citation(k),
                          counts={kk: manifest.get(k, {}).get(kk) for kk in
                                  ("n_volumes", "n_marks", "n_autograph", "n_mark", "n_copy",
                                   "n_text_withheld", "n_references", "n_source_authors")})

    out = dict(
        data_built=time.strftime('%Y-%m-%d', time.gmtime(os.path.getmtime(os.path.join(DATA, 'edges.json')))),
        totals=dict(readers=len(readers), volumes=len(volumes), marks=n_marks,
                    references=sum(1 for _ in open(os.path.join(DATA, "references.jsonl"))),
                    mark_edges=e["n_edges"], reference_edges=e["n_reference_edges"],
                    named_person_edges=e["n_named_person_edges"],
                    authors_reached_by_multiple_readers=e["n_authors_reached_by_multiple_readers"]),
        notes=dict(edges=e["note"], reference_edges=e["reference_note"],
                   named_person_edges=e["named_person_note"], shared=e["shared_note"]),
        sources=sources,
        readers=[[r["reader_id"], r["name"], r["birth"], r["death"], r["note"]] for r in readers],
        volumes=vol_rows, passages=passages, refs=refs,
        edges=edges, ref_edges=ref_edges, person_edges=person_edges,
    )
    raw = json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with gzip.GzipFile(OUT, "wb", mtime=0) as f:      # mtime=0: same input, same bytes
        f.write(raw)
    print(f"{OUT}: {len(raw)/1e6:.1f} MB raw, {os.path.getsize(OUT)/1e6:.1f} MB gz; "
          f"{len(readers)} readers, {len(volumes)} volumes, {n_marks} marks, "
          f"{len(passages)} quotable passages, {len(refs)} quotable references")


if __name__ == "__main__":
    main()
