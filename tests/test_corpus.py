'''
    Author: Aidan Jude

    Guards on the corpus, not on the code. Each one exists because the
    failure it catches is SILENT -- the build succeeds, the numbers look
    plausible, and the corpus asserts something false.

    Run:  python -m pytest tests -q      (after python build_corpus.py)

    Deliberately thin, and each guard rests on a DIFFERENT assumption from
    its neighbours, so two cannot fail for one reason and leave a third
    reporting clean.
'''

import gzip
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
DATA = os.path.join(ROOT, "_data")

import rights  # noqa: E402


def _jsonl(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        pytest.skip(f"{name} not built -- run python build_corpus.py")
    opener = gzip.open if p.endswith(".gz") else open
    with opener(p, "rt", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


@pytest.fixture(scope="module")
def marks():
    return _jsonl("marks.jsonl.gz")


@pytest.fixture(scope="module")
def volumes():
    return _jsonl("volumes.jsonl")


@pytest.fixture(scope="module")
def manifest():
    p = os.path.join(DATA, "manifest.json")
    if not os.path.exists(p):
        pytest.skip("manifest not built")
    return json.load(open(p))


def test_no_reader_text_on_a_non_verbal_mark(marks):
    '''
        THE rule. A score in the margin of King Lear yields Shakespeare's
        words, not Melville's. Putting them in reader_text makes the corpus
        attribute "Nothing can come of nothing" to Melville, and nothing
        about the output looks wrong.
    '''
    bad = [m for m in marks if m["tier"] == "T2_mark" and m["reader_text"]]
    assert not bad, f'{len(bad)} non-verbal marks carry reader_text, e.g. {bad[0]["mark_id"]}'


def test_a_licence_decision_never_changes_a_tier(manifest):
    '''
        Caught for real 2026-08-27: AOR reported 0 autographs over ~28,000
        notes in Harvey's and Dee's own hands, purely because rights.py
        withholds the text. The tier is a fact about the page.
    '''
    for key, m in manifest.items():
        if key.startswith("_") or m["text_emitted"]:
            continue
        assert m["n_autograph"] > 0, (
            f"{key} withholds text and reports zero autographs -- a permissions "
            f"decision has rewritten the evidence ladder"
        )
        assert m["n_text_withheld"] > 0, f"{key} withholds text but flags none withheld"


def test_withheld_sources_emit_no_text(marks, volumes):
    '''The other direction: a withheld source must not leak text anyway.'''
    ds = {v["volume_id"]: v["source_dataset"] for v in volumes}
    leaks = [m for m in marks
             if not rights.may_emit_text(ds.get(m["volume_id"], "monline"))
             and (m["reader_text"] or m["marked_text"] or m["translation"])]
    assert not leaks, f'{len(leaks)} text fields leaked from a withheld source, e.g. {leaks[0]["mark_id"]}'


def test_every_source_has_a_rights_entry(volumes):
    for ds in {v["source_dataset"] for v in volumes}:
        rights.check(ds)          # raises RightsError if absent


def test_no_reader_is_invented(volumes, marks):
    declared = {r["reader_id"] for r in json.load(open(os.path.join(DATA, "readers.json")))}
    seen = {v["reader_id"] for v in volumes} | {m["reader_id"] for m in marks}
    assert seen <= declared, f"undeclared readers: {sorted(seen - declared)}"


def test_no_source_author_is_invented(volumes):
    '''
        Every AOR source author must come from the hand-checked map, never
        from a directory name coerced into a person. 15 of 35 AOR books are
        deliberately null there.
    '''
    allowed = set(json.load(open(os.path.join(ROOT, "ingest", "aor_books.json"))).values())
    got = {v["source_author"] for v in volumes if v["source_dataset"] == "aor" and v["source_author"]}
    assert got <= allowed, f"AOR invented author(s): {sorted(got - allowed)}"


def test_aor_entity_fix_still_covers_the_corpus(manifest):
    '''
        1,555 of 7,594 AOR files use HTML entities the schema never declares.
        A bare parse drops them -- 43% of the notes, concentrated in the
        Latin books. If a new undeclared entity lands upstream the ingest
        raises; this guards the shipped totals against a quiet regression
        that halves the corpus and still builds.
    '''
    a = manifest.get("aor")
    if not a:
        pytest.skip("aor not in manifest")
    assert a["n_volumes"] == 36, f'AOR volume-reader records {a["n_volumes"]}, expected 36'
    assert a["n_marks"] > 180000, f'AOR marks fell to {a["n_marks"]} -- entity fix regressed?'
    assert a["n_autograph"] > 27000, f'AOR autographs fell to {a["n_autograph"]}'


def test_whitman_reading_dates_are_mostly_empty(volumes):
    '''
        The trap, pinned as a shape rather than a number: <date
        type="readingDate"/> is present on all 214 handlist records and
        POPULATED on 28. A grep-derived count overstates by 8x. This guard
        fails if someone "fixes" the parser by filling the blanks.
    '''
    hl = [v for v in volumes if ":handlist:" in v["volume_id"]]
    if not hl:
        pytest.skip("whitman handlist not built")
    dated = [v for v in hl if v["read_from"]]
    assert 0 < len(dated) < len(hl) * 0.5, (
        f"{len(dated)}/{len(hl)} handlist records carry a reading date -- either "
        f"upstream populated them (good, update the docs) or the parser is "
        f"inventing dates (bad)"
    )


def test_every_t3_names_who_attests_it(volumes):
    '''
        A T3 is a claim that someone read something, with no mark to prove
        it. Unsourced, it is exactly the interpretive evidence this corpus
        exists to beat -- so it must carry its attestor.
    '''
    t3 = [v for v in volumes if ":handlist:" in v["volume_id"]]
    if not t3:
        pytest.skip("no T3 volumes built")
    bad = [v for v in t3 if not v["evidence_source"]]
    assert not bad, f'{len(bad)} attested-reading records name no source, e.g. {bad[0]["volume_id"]}'
