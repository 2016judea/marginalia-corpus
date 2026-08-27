# marginalia-corpus

**A mark in a book is not an opinion about influence. It is a physical fact.**

Every influence graph in digital humanities is validated against attribution —
a scholar, or a crowd, or a model asserting that A influenced B. That is an
*interpretation* of evidence, made by someone who was not there.

This corpus is the evidence. When Melville drew a vertical bar beside a line of
*King Lear*, that bar is not a reading of Melville; it is Melville, at a
particular passage, in a copy that still exists. When Gabriel Harvey wrote in
the margin of his Livy, the note is in his own hand and it names the page it
answers. When Derrida bracketed a word in his Rousseau, the project that
transcribed it also found the sentence of *De la grammatologie* it became.

It is the most direct record of authorial and prose influence we have — and
the only kind that carries a **passage**.

---

## What's in it

Built 2026-08-27. Every number below comes out of `build_corpus.py`, not typed.

| Source | Reader(s) | Volumes | Marks | T1 own words | T2 non-verbal | T3 attested | References | Source authors |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| [Melville's Marginalia Online](https://melvillesmarginalia.org) | Herman Melville (+ Elizabeth Shaw Melville) | 52 | 4,864 | 367 | 4,497 | — | — | 19 |
| [Archaeology of Reading](https://archaeologyofreading.org) | Gabriel Harvey, John Dee, John Winthrop | 36 | 189,980 | 28,275 | 161,705 | — | 9,641 | 31 |
| [Walt Whitman Archive](https://whitmanarchive.org) | Walt Whitman | 362 | 2,303 | 1,384 | 708 | 211 | — | 160 |
| [Derrida's Margins](https://derridas-margins.princeton.edu) | Jacques Derrida | 222 | 1,670 | 211 | 1,459 | — | 1,052 | 107 |
| **Total** | **6 readers** | **672** | **198,817** | **30,237** | **168,369** | **211** | **10,693** | **313** |

**30,237 utterances by an author, written in another author's book, beside the
line that provoked them.** Plus 168,369 marks that locate a passage without
saying anything, and 10,693 references where the reader names another author in
their own words. Four centuries of readers: Harvey and Dee in the 1570s,
Melville and Whitman in the 1850s, Derrida in the 1960s.

Three edge sets in `_data/edges.json`, never merged:

- **242 mark edges** — the reader physically marked this author's book. 84 are
  passage-anchored.
- **388 reference edges** — the reader *named* this author, in a marginal note
  or in their own published book.
- **2,572 named-person edges** — people named inside notes who are not attached
  to a cited work. Not authors: Hannibal and Socrates are here too.

## The evidence ladder

Tiers are never summed. They are different **kinds** of evidence, and a
consumer has to be able to ask for only the direct ones. Full definitions in
[`schema.py`](schema.py).

| | | Has a passage | Has the reader's words |
|---|---|---|---|
| **T1** | autograph — the reader's own words in the margin | yes | yes |
| **T2** | mark — score, underline, checkmark, bracket, X | yes | no |
| **T3** | copy — demonstrably read, no surviving mark | no | no |
| *T4* | *documented — a scholar/model/Wikidata asserts it* | *no* | *no* |

**This repo does not emit T4.** `literature-mutations` already has two T4
sources (`known_influences.json`, 377 LLM-enumerated; `wikidata_influences.json`,
350 Wikidata P737 claims) and the entire reason this corpus exists is that they
are the weaker evidence class.

A tier is a fact about the page, never about our licence. Where `rights.py`
bars redistributing a note's text, the mark stays T1 with `text_withheld=true`
and an empty `reader_text` — demoting it would let a permissions decision
quietly rewrite the evidence. *(Caught here for real: the AOR slice first
reported **zero** autographs over 28,275 notes in Harvey's and Dee's own hands.)*

## Whose hand? — the finding that came out of asking

Every mark carries `hand_is_reader`. It is False when the source attributes the
mark to someone other than, or ambiguously with, the reader whose library it is.
Filter on it before making any claim about a named reader.

It bites harder than expected. Melville's second-most-marked author looked like
**William E. Channing, 453 marks** — fourth behind Shakespeare, Homer and Milton.
Split by hand:

| hand | marks |
|---|---:|
| Herman *or* Elizabeth Shaw Melville | 433 |
| Elizabeth Shaw Melville | 16 |
| **Herman Melville** | **4** |

**All 433 of the corpus's ambiguous marks are in the Channing volumes**, and only
four are certainly Herman's. Channing is not Melville's fourth-favourite author;
Channing is very probably his wife's reading. By raw count he ranks 4th of 19; by
own-hand he ranks last. Shakespeare, by contrast, is 755 of 761 unambiguously
Herman.

## The one rule that fails silently

**Marked text and reader text are different fields.**

- `marked_text` — the **source author's** printed words the mark sits on.
  Melville scoring a Lear line yields *Shakespeare's* words.
- `reader_text` — the **reader's** own inscribed words. T1 only.

Collapse them and the corpus asserts that Melville wrote "Nothing can come of
nothing". Nothing about the output looks wrong.
`tests/test_corpus.py::test_no_reader_text_on_a_non_verbal_mark` is the guard.
The rule was learned by hand on the [King Lear
edition](https://github.com/2016judea/shakespeare-marginalia) before it was a
schema constraint.

## What this data uniquely permits

Attribution can tell you Shakespeare influenced Melville. It cannot tell you
**which lines**. This can, so it supports a measurement nothing else does:

> **Do the passages a reader marked predict that reader's own later prose
> better than unmarked passages from the same volume?**

The known-positive control is already on the shelf. Melville left **212 marks
in Thomas Beale's *Natural History of the Sperm Whale*** — a book he
demonstrably lifted into *Moby-Dick*. If the method cannot recover Beale, it
cannot be trusted on Shakespeare. Runners-up as controls: Hawthorne (365 marks,
*Mosses from an Old Manse*, the book behind "Hawthorne and His Mosses") and
Chapman's Homer (563).

Derrida gives the same test a second, independent form: 632 of his references
are **quotations**, each located in his own annotated copy, so the marked
passage and the published sentence it became are both on record. Rousseau alone
supplies 478 references across 37 volumes.

## Build it

```bash
pip install -r requirements.txt
python build_corpus.py      # ingest all sources  -> _data/
python build_edges.py       # derive edges        -> _data/edges.json
python -m pytest tests -q
```

First run fetches ~100 MB into `cache/` (gitignored): 140 HTTP requests to
Melville's Marginalia Online, shallow clones of two GitHub data repos, four
spreadsheets from AOR, and the Derrida release off Princeton Data Commons.
Subsequent runs are offline.

## Importing into literature-mutations

Designed as a submodule of
[`literature-mutations`](https://github.com/2016judea/literature-mutations),
whose Phase 2 builds a directed author-influence graph and validates it against
two independent held-out sources. This is a **third**, and the only
non-interpretive one.

```bash
git submodule add https://github.com/2016judea/marginalia-corpus vendor/marginalia
```

```python
import json
d = json.load(open("vendor/marginalia/_data/edges.json"))
direct = [e for e in d["edges"] if e["passage_anchored"]]       # T1/T2 only
certain = [e for e in d["edges"] if e["n_own_hand"] > 0]        # drop ambiguous hands
declared = d["reference_edges"]                                 # separate measurement
```

Keep each set in its own key, exactly as Phase 2 already keeps
`held_out_validation` and `held_out_validation_wikidata` apart. Do not merge the
tiers, and do not add mark counts to reference counts.

**Nothing in `literature-mutations` has been touched.** Its
`docs/RESEARCH-PROGRAM.md` records Phase 2 as parked under a standing decision
("do not re-ask these"), so this repo waits for that to un-park rather than
reopening it. The import above is one line when it does.

Four things it hands Phase 2 that it does not currently have:

1. **A weight.** An attribution edge is binary. `n_T1`/`n_T2` say *how much* —
   Melville left **761** marks in Shakespeare against **45** in Marlowe.
2. **A hand.** `n_own_hand` separates what the reader certainly did from what
   the archive is unsure about. See the Channing case above.
3. **A reading date.** Phase 2 permits an edge only when A's earliest work
   predates B's, explicitly because "personal reading order" was unavailable.
   28 Whitman records carry one — see the caveat in
   [`ingest/whitman.py`](ingest/whitman.py): 186 of the 214 `readingDate` fields
   are **empty**, and a grep-derived count overstates this by 8×.
4. **A self-declared edge.** 632 quotations, 325 footnotes, 78 citations and 17
   epigraphs in which a reader names a source in their own published voice.

## Rights

`rights.py` is a gate: **the build refuses to run on a source with no entry**,
and each entry records the terms as actually read, with the date.

| Source | Terms | Text ships |
|---|---|---|
| **Derrida's Margins** | CC BY 4.0, stated in the release's own rights field | **yes** |
| **Melville's Marginalia Online** | transcriptions quotable with attribution; the restriction is on *photographic images* | **yes** |
| **Archaeology of Reading** | no licence file, no reuse statement found | no — counts and metadata only |
| **Walt Whitman Archive** | its own `<availability>`: *"all rights reserved… Redistribution or republication on other terms, in any medium, requires express written consent"* | no — counts and metadata only |

`_data/marks.jsonl.gz` therefore carries full text for Melville and Derrida and
structure only for the other two. Passage-level text for all four builds locally
into `cache/`. Nothing analytical is lost for the influence-graph use.

The Derrida ingest re-checks the licence on every fetch and **refuses to build**
if the rights field stops saying CC BY, because `emit_text` is set on that basis.

## Where it goes next

[`docs/SOURCES.md`](docs/SOURCES.md) is the survey: four sources in, six
measured and gated, five ruled out with the reason. The two biggest unclaimed
bodies:

- **Beckett Digital Library** — 815 volumes with transcribed reading traces.
  Subscription, and a JS app a scripted fetch cannot read.
- **Charles Darwin's Library** — 730 annotated books with transcriptions. One
  free BHL API key away; the keyless routes (bulk TSVs, OAI-PMH) carry
  bibliography only, checked 2026-08-27.

## Citing the sources

Attribution is required by all four. `_data/manifest.json` carries a citation
string per source so a downstream consumer never has to read this code to
credit them properly.
