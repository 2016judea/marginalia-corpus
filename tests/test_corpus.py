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
             "named_in_note", "work_cited_in_note", "named_in_work"}
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


def test_nietzsche_controls_stay_at_zero():
    """
        The Nietzsche slice matches a CLOSED gazetteer of 66 declared
        authors, three of which cannot possibly appear -- Melville and
        Whitman he never names, Derrida was born thirty years after he died.
        A hit on any of them means the matcher produces false positives, and
        every other count is then suspect.
    """
    p = os.path.join(DATA, "nietzsche_audit.json")
    if not os.path.exists(p):
        pytest.skip("nietzsche not built")
    a = json.load(open(p))
    hits = a["counts"]
    for c in a["controls_at_zero"]:
        assert hits.get(c, 0) == 0, f"control author {c!r} matched {hits[c]} times"


def test_nietzsche_ambiguous_surnames_stay_gated():
    """
        Every raw match on "Lange" in these seven texts is the German
        adjective. If the gate is removed, Friedrich Albert Lange appears on
        twelve false hits and outranks Darwin. Guarded as a shape: a gated
        entry must be rarer than the ungated ones it would otherwise beat.
    """
    p = os.path.join(DATA, "nietzsche_audit.json")
    if not os.path.exists(p):
        pytest.skip("nietzsche not built")
    counts = json.load(open(p))["counts"]
    assert counts.get("Friedrich Albert Lange", 0) == 0, (
        "Lange matched -- the first-name gate regressed and the German adjective "
        "is being counted as a philosopher"
    )
    assert counts.get("David Strauss", 0) < 10, (
        "David Strauss over-matched -- 'Der Vogel Strauss' (the ostrich) and "
        "'ein Strauss' (a bouquet) are back in"
    )


def test_a_reader_naming_themselves_is_not_an_edge(edges):
    """Dee cites his own printed books in his own margins; Derrida quotes himself."""
    for e in edges["reference_edges"]:
        assert e["reader"] != e["target_author"], f"self-reference survived: {e}"
    assert edges["n_self_references_excluded"], "no self-references excluded at all"


def test_the_corpus_has_cross_reader_reach(edges):
    """
        A single-reader corpus cannot say anything comparative. The point is
        authors reached by more than one reader -- Homer by five, Shakespeare
        by Melville and Nietzsche four centuries apart. Marks and references
        are reported per reader and must never be summed into one number.
    """
    shared = edges["shared_authors"]
    assert len(shared) > 20, f"only {len(shared)} authors reached by 2+ readers"
    for x in shared:
        assert len(x["readers"]) == x["n_readers"]
        for r, m in x["readers"].items():
            assert set(m) <= {"marks", "references"}, f"unexpected measure on {x['author']}: {m}"


def test_shakeco_is_t3_only(manifest):
    '''
        A lending card records a transaction, not a mark. If this slice ever
        reports a T1 or T2 it has invented a passage anchor, and its 8,432
        records would then outweigh Melville's 4,864 physical marks in any
        consumer that filters on "passage_anchored".
    '''
    s = manifest.get("shakeco")
    if not s:
        pytest.skip("shakeco not built")
    assert s["n_autograph"] == 0 and s["n_mark"] == 0, (
        f'shakeco reported {s["n_autograph"]} T1 and {s["n_mark"]} T2 -- a borrow is '
        f'attested contact, never a mark'
    )
    assert s["n_copy"] > 5000


def test_shakeco_readers_come_from_the_committed_roster(volumes):
    '''
        520 readers is too many to hand-type, so they are generated into
        ingest/shakeco_readers.json and committed. The point of the file is
        that the adapter cannot invent a reader at build time -- if a reader
        appears in the data who is not in the file, that guarantee is gone.
    '''
    sc = [v for v in volumes if v["source_dataset"] == "shakeco"]
    if not sc:
        pytest.skip("shakeco not built")
    roster = json.load(open(os.path.join(ROOT, "ingest", "shakeco_readers.json"),
                            encoding="utf-8"))["readers"]
    stray = {v["reader_id"] for v in sc} - set(roster)
    assert not stray, f"readers absent from the committed roster: {sorted(stray)[:5]}"


def test_every_attested_contact_is_dated_and_sourced(volumes):
    '''
        The reason a lending library belongs here at all is that the contact
        is dated to the day and sourced to a physical card. Without those it
        is weaker than Whitman's handlist, not stronger.
    '''
    sc = [v for v in volumes if v["source_dataset"] == "shakeco"]
    if not sc:
        pytest.skip("shakeco not built")
    undated = [v for v in sc if not v["read_from"]]
    unsourced = [v for v in sc if not v["evidence_source"]]
    assert len(undated) < len(sc) * 0.01, f"{len(undated)}/{len(sc)} undated"
    assert not unsourced, f"{len(unsourced)} records name no source card"


def test_abo_excludes_the_copies_aor_already_transcribed(manifest):
    '''
        ABO and AOR are different projects that transcribed many of the SAME
        physical copies -- 10 of ABO's 11 Dee/Harvey books. If the overlap
        check stops working, ~1,190 annotations enter as independent evidence
        when they are duplicates, and every Dee and Harvey weight inflates.
    '''
    a = manifest.get("abo")
    if not a:
        pytest.skip("abo not built")
    assert a.get("excluded_already_in_aor", 0) > 1000, (
        f'only {a.get("excluded_already_in_aor")} annotations excluded as AOR '
        f'duplicates -- the overlap check regressed and the corpus is double-counting'
    )
    assert a["n_marks"] > 3000, f'abo fell to {a["n_marks"]} marks'


def test_abo_hands_are_flagged_on_shared_provenance(marks, volumes):
    '''
        ABO records provenance as a free-text ownership CHAIN on the book and
        gives no per-annotation hand. Where the chain names more than one
        person the mark must not claim to be the named reader's -- Luther's
        New Testament also passed through Praedinius and Manningha.
    '''
    ids = {v["volume_id"] for v in volumes if v["source_dataset"] == "abo"}
    am = [m for m in marks if m["volume_id"] in ids]
    if not am:
        pytest.skip("abo not built")
    assert any(not m["hand_is_reader"] for m in am), (
        "no ABO mark is flagged as a shared-provenance hand -- the `sole` flag in "
        "abo_readers.json stopped being applied"
    )
    assert any(m["hand_is_reader"] for m in am)


def test_beckett_ships_no_text_at_all(manifest, marks, volumes):
    '''
        The strictest source here. Beckett died in 1989, so his marginalia
        are unpublished work in copyright until roughly 2059 and controlled
        by his Estate. NOTHING may leak -- not the reading trace, not even
        the marked passage from a public-domain source author.
    '''
    b = manifest.get("beckett")
    if not b:
        pytest.skip("beckett not built")
    assert not b["text_emitted"], "beckett must not emit text"
    ids = {v["volume_id"] for v in volumes if v["source_dataset"] == "beckett"}
    leaks = [m for m in marks if m["volume_id"] in ids
             and (m["reader_text"] or m["marked_text"] or m["translation"])]
    assert not leaks, f'{len(leaks)} Beckett text fields leaked, e.g. {leaks[0]["mark_id"]}'
    assert b["n_text_withheld"] > 1000, (
        f'only {b["n_text_withheld"]} Beckett marks flag text_withheld -- the tier '
        f'is a fact about the page, so an autograph whose text we may not ship must '
        f'still say so'
    )


def test_beckett_sweep_is_complete(manifest):
    '''
        2,685 marginalia rows arrive 10 per page over ~269 requests. A
        truncated sweep still builds and still looks plausible, so the ingest
        compares parsed rows against the hit count the search itself reports
        and this pins the result.
    '''
    b = manifest.get("beckett")
    if not b:
        pytest.skip("beckett not built")
    reported, parsed = b["marginalia_rows_reported"], b["marginalia_rows_parsed"]
    assert parsed >= reported * 0.95, f"parsed {parsed} of {reported} marginalia rows"
    assert b["library_items"] > 800, f'only {b["library_items"]} library items swept'


# ---------------------------------------------------------------------------
# Adapter-level guards (2026-10-18). These run the ingests on the committed
# cache only: every network call is stubbed to raise, so a missing cache file
# fails the test instead of fetching from a live site.
# ---------------------------------------------------------------------------

import xml.etree.ElementTree as ET  # noqa: E402
from collections import Counter  # noqa: E402


def _no_network(monkeypatch, *modules):
    def boom(*a, **k):
        raise AssertionError("test tried to reach the network")
    for m in modules:
        monkeypatch.setattr(m.urllib.request, "urlopen", boom, raising=True)


def _dupes(marks):
    return [k for k, n in Counter(m.mark_id for m in marks).items() if n > 1]


def test_melville_words_keep_nested_lines_and_hyphenated_words():
    '''
        MMO nests a <line> inside a <line> when a mark runs into the margin
        (doc101 p.247_2_136: "Perugino" sat in an inner line and was dropped,
        235 marks lost words that way), and a word broken over a line is a
        <choice><hyph>mas-</hyph><reg>massiveness,</reg></choice> with no
        <orig> at all -- 1,618 of those read as "" and vanished, leaving the
        next line's "siveness," orphaned. The marked passage is the point of
        the corpus; it must be the whole passage, in page order.
    '''
    from ingest.melville_monline import _words
    div = ET.fromstring('''
      <div page="x" type="xmark">
        <line n="1"><line n="21"><blank x="1"/><w>Perugino</w></line>
          <w>was</w><w>evidently</w><w>a</w><w>devout</w><w>man;</w></line>
        <line n="2"><w>its</w><w><choice><hyph>mas-</hyph><reg>massiveness,</reg></choice></w></line>
        <line n="3"><w endhyph="true">siveness,</w><w><choice><orig>neighbour</orig><reg>neighbor</reg></choice></w>
          <w><choice><missp>devel</missp><reg>devil</reg></choice></w><w><choice>burd'nous</choice></w></line>
      </div>''')
    assert _words(div) == ("Perugino was evidently a devout man; its mas- siveness, "
                           "neighbour devel burd'nous")


def test_melville_mark_ids_are_unique(monkeypatch):
    '''
        MMO's div @id restarts per page AND is reused within a page (doc32
        p.465_127 carries two id="2" divs in different groups), so
        volume:page:id named two different marks. The shipped 2026-08-27 data
        had 7 such collisions. Cached volumes only.
    '''
    from ingest import melville_monline as mm
    _no_network(monkeypatch, mm)
    _, marks, _ = mm.ingest(did_range=[32, 65, 67, 101, 114])
    assert marks, "no cached Melville volumes to test against"
    assert _dupes(marks) == []


def test_aor_mark_ids_are_unique(monkeypatch):
    '''
        AOR's @pagination/@signature is not unique per page file: 582 keys are
        shared by two files of the same book (Castiglione_Newberry
        [Ai[v]] is both _008.xml and _032.xml), so volume:page:m0 collided
        7,235 times in the shipped data. The file is the page's identity.
    '''
    from ingest import aor
    assert os.path.isdir(os.path.join(aor.CACHE, ".git")), "AOR cache not cloned"
    monkeypatch.setattr(aor.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("clone attempted")))
    _, marks, _ = aor.ingest()
    assert _dupes(marks) == []


def test_beckett_trace_pages_are_counted_once(monkeypatch):
    '''
        A reading-trace page listed twice for one volume (DAN-DIV-6 p.296)
        became two T2 marks with one id. One page, one trace.
    '''
    from ingest import beckett
    _no_network(monkeypatch, beckett)
    out = beckett.ingest()
    vols, marks = out[0], out[1]
    traces = [m for m in marks if m.mark_type == "reading_trace"]
    assert traces
    assert _dupes(marks) == []
    per_vol = Counter(m.volume_id for m in traces)
    n_marks = {v.volume_id: v.n_marks for v in vols}
    for vid, n in per_vol.items():
        assert n <= n_marks[vid]
