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


# ---------------------------------------------------------------------------
# Added with the second wave of sources (Derrida, AOR bibliography, references)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def references():
    return _jsonl("references.jsonl")


@pytest.fixture(scope="module")
def edges():
    p = os.path.join(DATA, "edges.json")
    if not os.path.exists(p):
        pytest.skip("edges not built -- run python build_edges.py")
    return json.load(open(p))


def test_every_aor_book_has_an_author_from_their_own_bibliography(volumes):
    '''
        All 35 AOR directories resolve now, from Corpus-January-2019.xlsx.
        If this regresses to nulls, aor_resolve_books.py silently failed its
        join and 44,000 marks go back to being stranded.
    '''
    aor = [v for v in volumes if v["source_dataset"] == "aor"]
    if not aor:
        pytest.skip("aor not built")
    bad = [v for v in aor if not v["source_author"]]
    assert not bad, f'{len(bad)} AOR volumes lost their author, e.g. {bad[0]["volume_id"]}'
    allowed = {r["author"] for k, r in json.load(
        open(os.path.join(ROOT, "ingest", "aor_books.json"))).items()
        if not k.startswith("_")}
    got = {v["source_author_raw"] for v in aor if v["source_author_raw"]}
    assert got <= allowed, f"AOR invented author(s): {sorted(got - allowed)}"


def test_a_named_person_is_never_promoted_to_an_authorial_edge(references):
    """
        8,483 <person> tags name Hannibal, Socrates and Eutrapelus as often
        as Cicero. Giving a bare <person> a target_author would assert that
        Harvey cited Hannibal as a source.

        Note what this does NOT assert: that the two edge sets are disjoint.
        Cicero is legitimately in both -- named in notes AND the author of
        cited works. The guard is on the ROUTE, not on the name.
    """
    bad = [r for r in references if r["kind"] == "named_in_note" and r["target_author"]]
    assert not bad, str(len(bad)) + " bare <person> tags carry an author, e.g. " + str(bad[0] if bad else "")


def test_reference_kinds_are_declared(references):
    known = {"quotation", "footnote", "citation", "epigraph",
             "named_in_note", "work_cited_in_note"}
    seen = {r["kind"] for r in references}
    assert seen <= known, f"undeclared reference kind(s): {sorted(seen - known)}"


def test_a_reader_marking_their_own_book_is_not_an_edge(edges):
    '''Derrida annotated 5 of his own offprints. That is not influence.'''
    for e in edges["edges"]:
        assert e["reader"] != e["source_author"], f"self-edge survived: {e}"
    assert edges["n_self_edge_marks_excluded"], (
        "no self-edge marks were excluded at all -- Derrida's own offprints are in "
        "the library, so zero means the check stopped running"
    )


def test_own_hand_is_a_real_subset_somewhere(manifest):
    '''
        hand_is_reader must actually bite. Melville has 433 HMorESM marks
        and 177 unattributed; Derrida has 4 by Marguerite and 2 unattributed.
        If own-hand equals total everywhere, the flag defaulted True and the
        ~13% overstatement is back.
    '''
    biting = [k for k, v in manifest.items()
              if not k.startswith("_") and v["n_marks_in_readers_own_hand"] < v["n_marks"]]
    assert biting, "no source distinguishes the reader's own hand -- flag is inert"
    for k, v in manifest.items():
        if k.startswith("_"):
            continue
        assert v["n_marks_in_readers_own_hand"] <= v["n_marks"], f"{k}: own-hand > total"


def test_names_canonical_does_not_chain(volumes):
    '''
        An alias whose VALUE is also another alias's KEY would resolve
        differently depending on call order. canonical() applies once, so
        such a pair is a latent bug -- catch it in the table, not in the data.
    '''
    sys.path.insert(0, ROOT)
    import names
    chained = [k for v in names.ALIASES.values() for k in (v,) if k in names.ALIASES]
    assert not chained, f"alias values that are themselves alias keys: {chained}"
    for v in volumes:
        if v["source_author"]:
            assert names.canonical(v["source_author"]) == v["source_author"], (
                f'{v["source_author"]!r} is not stable under canonical()'
            )


def test_derrida_text_ships_because_it_is_cc_by(manifest, marks, volumes):
    d = manifest.get("derrida")
    if not d:
        pytest.skip("derrida not built")
    assert d["text_emitted"], "Derrida is CC BY -- text must ship"
    ids = {v["volume_id"] for v in volumes if v["source_dataset"] == "derrida"}
    dm = [m for m in marks if m["volume_id"] in ids]
    assert any(m["reader_text"] for m in dm), "no Derrida reader_text emitted"
    assert any(m["marked_text"] for m in dm), "no Derrida marked_text emitted"
