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
| [Nietzsche, works](https://www.gutenberg.org) (Gutenberg, German) | Friedrich Nietzsche | — | — | — | — | — | 1,081 | 60 |
| [Shakespeare and Company Project](https://shakespeareandco.princeton.edu) | 253 writers with a Paris library card | 7,741 | 8,432 | — | — | 8,432 | — | 1,420 |
| [Annotated Books Online](https://annotatedbooksonline.com) | Dee, Luther, Melanchthon, Erasmus, Newton, Scaliger + 11 | 21 | 3,527 | 3,506 | 21 | — | — | 17 |
| **Total** | **554 readers** | **8,434** | **210,776** | **33,743** | **168,390** | **8,643** | **11,774** | **1,719** |

**30,237 utterances by an author, written in another author's book, beside the
line that provoked them.** Plus 168,369 marks that locate a passage without
saying anything, and 10,693 references where the reader names another author in
their own words. Four centuries of readers: Harvey and Dee in the 1570s,
Melville and Whitman in the 1850s, Derrida in the 1960s.

Three edge sets in `_data/edges.json`, never merged:

- **5,157 mark-and-contact edges** — the reader marked this author's book, or
  demonstrably held a copy of it. 84 are passage-anchored.
- **446 reference edges** — the reader *named* this author, in a marginal note
  or in their own published work.
- **2,572 named-person edges** — people named inside notes who are not attached
  to a cited work. Not authors: Hannibal and Socrates are here too.

And the thing a multi-reader corpus is *for*: **836 authors reached by more than
one reader, 228 of them by six or more.**

| author | documented readers |
|---|---:|
| James Joyce | 55 |
| Virginia Woolf | 50 |
| D. H. Lawrence | 48 |
| Ernest Hemingway | 45 |
| T. S. Eliot | 37 |
| William Faulkner | 35 |

Joyce is simultaneously the most-read author in the corpus and one of its
readers — 149 borrows on his own card. Homer is reached by five readers across
four centuries; Shakespeare by Melville and Nietzsche. Marks, contacts and
references are reported per reader inside `shared_authors` and never added
together.

## The evidence ladder

Tiers are never summed. They are different **kinds** of evidence, and a
consumer has to be able to ask for only the direct ones. Full definitions in
[`schema.py`](schema.py).

| | | Has a passage | Has the reader's words |
|---|---|---|---|
| **T1** | autograph — the reader's own words in the margin | yes | yes |
| **T2** | mark — score, underline, checkmark, bracket, X | yes | no |
| **T3** | contact — the reader demonstrably held this copy; no surviving mark | no | no |
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

## Two projects transcribed the same books — catching that mattered most

Annotated Books Online is **CC BY-NC**, and its API turns out to be wide open
once you find the shape: `POST /?controller=Book&action=search` — the route is in
`frontend/logic/requestmanager.js`, `/backend` itself 403s and no endpoint
appears anywhere else. Three calls return the whole archive: 110 books, 50,776
scans, **4,803 annotations, 4,752 with an original transcription and 1,785 with
an English translation.**

Then the check that changed the number. **10 of ABO's 11 books with Dee or Harvey
provenance are the same physical copies AOR already transcribed** — the Folger
H.a.2 Sammelband, Princeton's *Arte of Warre*, the Livy, both Buchanans.
Ingesting both naively counts the same marks twice as independent evidence.

| | annotations |
|---|---:|
| on copies AOR already covers — **excluded** | 1,190 |
| on copies AOR does not — **ingested** | 3,611 |

What survives is worth having: **John Dee's Strabo, *De situ orbis*, at the Royal
Library of Belgium — 2,826 annotations**, his most heavily annotated book
anywhere and absent from AOR. Plus new readers: Luther (224, in an Erasmus New
Testament), Luther and Melanchthon's shared Odyssey (70), Erasmus himself (55),
Joseph Scaliger, Jan van Hout, Adriaen Verwer's copy of Newton's *Principia*
(65 — Verwer the reader, Newton the source author), and Newton's own Principia (1).

Montaigne's Lucretius is in ABO's book list with **zero** annotations
transcribed. Listed, not transcribed — he is not in this corpus.

Two joins that fail silently, both now guarded: `bindingId` is an **int** on
scans and a **string** on books, so a dict lookup across them matches nothing and
reports every annotation unmapped; and **a binding can hold several works** (12
of 95 do), so the book is the one with the greatest `firstPage` at or below the
scan's page — without that, every Sammelband annotation lands on the first work.

## A lending library, and why it belongs here

Sylvia Beach's Shakespeare and Company, Paris, 1919–1941, reconstructed from her
surviving lending cards. **21,059 borrow events**; restricted to members who are
authors of record, **8,432 events over 253 writers and 1,420 source authors**.

It is the same evidence class as Whitman's handlist — attested contact with a
specific copy, no surviving mark — except **dated to the day, sourced to a
physical card, and 98.8% of events link an image of that card**:

> `Borrow, 1922 → 1922-08-23 · Mr. Rhys · Conrad, *Typhoon* (1902)`
> `source: Sylvia Beach, Rhys Lending Library Card, Box 43`

Nothing else in the corpus documents contact this precisely. Joyce borrowed 149
times, Hemingway 123, Gertrude Stein 60, Katherine Anne Porter 49, Nathalie
Sarraute 41; Beckett, Pound, Walter Benjamin, Djuna Barnes and Bryher all held
cards.

**Who counts as a reader is mechanical, not a fame judgment.** 5,235 members is
too many for a corpus about authors, and picking the famous novelists would be
cherry-picking — so the criterion is *the member has a VIAF url*, i.e. an entry
in library authority files. 520 of 5,235 qualify, 253 of those have at least one
event, and `wikipedia` is carried per reader so a consumer can tighten to the 345
who have both. The roster is generated into `ingest/shakeco_readers.json` and
**committed**, so the "no adapter invents a reader" guard still holds.

**Every record is T3**, and the guard
`test_shakeco_is_t3_only` enforces it. A borrow is attested contact, not proof of
reading, and never a passage. Anyone weighting these 8,432 against Melville's
4,864 physical marks has merged two different measurements.

One source artefact carried rather than fixed: a **shared card** credits one
event to every member on it, so Archibald and Ada MacLeish show 236 each — the
same transactions. `member_uris` is multi-valued precisely so the project need
not guess who did the borrowing. Summing across readers over-counts; per reader
does not.

## Nietzsche has no marks here, and that is the finding

He is the best-documented annotator in the survey and the least reachable.
Established by fetching, not by reading about it:

- **430,000 pages of his library are digitised, ~18,000 carrying annotations —
  and they are facsimile only.** There is no transcription layer to ingest.
- **Nietzsche Source publishes exactly three modules** — the Colli-Montinari
  text, facsimiles of the *archive* (manuscripts: its search columns are Mette
  numbers and KGW sigla, not books), and a journal. The announced digital
  edition of the **library is not published**. Confirmed by rendering the
  JavaScript nav, since the served HTML is an empty shell.
- **Weimar blocks automated access outright** — Anubis proof-of-work, and it
  gates the OAI-PMH endpoint too, which is the sanctioned harvesting route.
  That is a deliberate operator decision and this repo respects it.
- The transcribed *Lesespuren* exist in one place: **Campioni, D'Iorio, Fornari,
  Fronterotta and Orsucci, *Nietzsches persönliche Bibliothek* (de Gruyter,
  2003)** — ~2,200 titles with a complete index of reading traces. In copyright,
  in print, purchasable. It is the Coleridge problem again, and the only gate
  that matters.

So he enters through the one class that is free, complete and redistributable:
**naming another author in his own published prose** — seven German works from
Project Gutenberg, public domain, header stripped. A reference, never a mark.

**The matching is a closed gazetteer of 66 declared authors, never open-ended
entity recognition**, and the audit is shipped in
`_data/nietzsche_audit.json` with every hit's surrounding sentence so the counts
can be checked instead of trusted. Three consequences, all deliberate:

1. **Zero is a real answer**, so three impossible controls are in the list —
   Melville, Whitman, Derrida. A hit on any of them fails the build.
2. **Recall is bounded by the list.** This finds who, among 66 candidates,
   Nietzsche invokes and how often. It is not a claim to have found everyone.
3. **Ambiguous surnames are gated**, because a bare German surname is often a
   common word. Every raw match on "Lange" is the adjective — *Lange schlief
   Zarathustra*, *Langes Leben*, *alles Lange* — so Friedrich Albert Lange would
   otherwise rank 28th on twelve false hits. "Strauss" catches a bouquet and, in
   Zarathustra, an ostrich. Those entries require a first name within 60 characters.

What comes out reads like the books themselves, which is the check that matters:

| work | most-named |
|---|---|
| *Die Geburt der Tragödie* (1872) | Euripides 59, Socrates 58, Aeschylus 17 |
| *Ecce homo* (1888) | Wagner 64, Schopenhauer 13 |
| *Götzen-Dämmerung* (1888) | Socrates 35, Plato 23, Goethe 17 |
| *Also sprach Zarathustra* (1885) | **nobody** |

Zarathustra names none of the 66. It is written as scripture, not as argument —
recorded in the audit as `works_naming_nobody` rather than dropped, because an
absent row reads as "not processed".

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
| **Nietzsche (Gutenberg, German)** | public domain — he died in 1900; Gutenberg's licence attaches to their marked-up files, which are stripped | **yes** |
| **Shakespeare and Company Project** | CC BY 4.0 on all fourteen deposited datasets; the card images are PUL's and are linked, not copied | **yes** |
| **Annotated Books Online** | **CC BY-NC** — the one source narrower than CC BY. Transcriptions ship with attribution; the NC clause constrains commercial reuse downstream | **yes** |
| **Archaeology of Reading** | no licence file, no reuse statement found | no — counts and metadata only |
| **Walt Whitman Archive** | its own `<availability>`: *"all rights reserved… Redistribution or republication on other terms, in any medium, requires express written consent"* | no — counts and metadata only |

**Not the Colli-Montinari text.** The eKGWB at nietzschesource.org is de Gruyter
copyright, published online by permission, and must never be redistributed from
here. The Gutenberg German editions are a different, public-domain text.

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
- **Charles Darwin's Library** — 730 annotated books. **Not the free win it looked
  like:** BHL is behind Cloudflare bot protection that a real headless browser
  does not pass either, its developer docs list no marginalia resource, and the
  transcriptions are Di Gregorio and Gill's copyrighted 1990 catalogue which BHL
  *displays* rather than serves. Same category as Nietzsche and Coleridge.
- **Nietzsche's *Lesespuren*** — ~2,200 titles, fully indexed, in a €-priced
  2003 de Gruyter volume. Not a technical problem.


## Citing the sources

Attribution is required by all four. `_data/manifest.json` carries a citation
string per source so a downstream consumer never has to read this code to
credit them properly.
