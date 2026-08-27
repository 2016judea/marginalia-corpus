# Sources: what's in, what's gated, what's ruled out

Surveyed 2026-08-27. **A count marked *measured* was produced by fetching the
data and counting it in this session. A count marked *stated* is the project's
own published figure, unverified.** The distinction matters: three of the
measured figures came out materially different from the stated ones.

---

## In (six sources, ingested and building)

### 1. Melville's Marginalia Online — `ingest/melville_monline.py`

*Measured:* 52 volumes, 4,864 marks, 168,299 transcribed marked words,
20 distinct source authors, 62 distinct mark types, hand-attributed.

One HTTP request per volume: `XmlDownload.ashx?DocId=N&Stage=False`. DocIds are
not contiguous and are published nowhere — 52 of a 1..140 sweep responded.

- **Do not use the GitHub mirror.** `github.com/monline/xml` holds **5** of the
  52 volumes (130-Channing, 277/278-Homer, 385b-Milton, 460-Shakespeare). A
  session that finds the repo first builds a corpus 10% the real size and
  believes it is complete.
- *Stated:* Melville owned ~1,000 volumes; ~500 titles identified. So the
  transcribed 52 is ~10% of what is identified and ~5% of the library. The
  ceiling on this source is set by their transcription workflow, not by us.
- **433 of 4,864 marks are attributed `HMorESM`** — Herman *or* his wife
  Elizabeth. Crediting those to Herman overstates him by ~9%.

### 2. The Archaeology of Reading in Early Modern Europe — `ingest/aor.py`

*Measured:* 35 book directories, 7,594 page files, **28,324 marginal notes**,
107,856 underlines, ~190,000 marks total. Readers: Gabriel Harvey, John Dee,
plus three pages of John Winthrop.

*Stated:* "thirty-six fully digitized books… tens of thousands of handwritten
notes."

- **1,555 of 7,594 files (20%) do not parse as XML.** They use HTML named
  entities the schema never declares — `&egrave;` 496×, `&agrave;` 250×,
  `&ograve;` 102×, `&AElig;` 97×, plus a project-specific `&sharp-S;` 71×. A
  bare `ElementTree.parse` drops them, and because the failures cluster in the
  Latin books (Cicero II worst) **that silently loses 43% of the notes** —
  16,118 instead of 28,324. Fixed by entity substitution before parsing; the
  ingest raises if a new undeclared entity appears.
- Best schema of the three, and the reason it's worth including even though
  Dee is not a literary author: it separates `anchor_text` (the printed words
  the note answers) from `marginalia_text` (the reader's words) at the source,
  and adds an editorial English `<translation>`.
- **All 35 books now carry AOR's own author** — 31 distinct. The first pass left
  15 as `null` because the per-page XML has no book-level bibliography, only the
  project's short directory label, and guessing an author from "De navigatione"
  or "Voarchadumia" would have put a fabricated citation into an influence
  graph. Then the bibliography turned up on their own downloads page:
  **Corpus-January-2019.xlsx**, 37 rows with Author, Title, Short Title,
  Location and Shelfmark. `ingest/aor_resolve_books.py` joins on Short Title;
  the only hand-made part is a directory→label alignment, checkable against the
  shelfmark. That unstranded **44,279 marks**.
- **Two Sammelbände set a real limit.** Folger H.a.2 holds Domenichi's *Facetie*
  **and** Guicciardini's *Detti et Fatti*; RCP 10552-2 holds two Walsinghams.
  A mark in a bound-together volume cannot be attributed to one of its works
  without page ranges, which the page XML does not carry. First work is primary,
  the rest go in `co_bound_authors` and get **no edge** — so Guicciardini is a
  reader-contact we can see and cannot count.
- **Both authority tables are now ingested** (`ingest/aor_authorities.py`),
  turning the `<person>` and `<book>` tags inside notes into **9,641 references**
  — 8,483 people named, 1,158 works cited, **6,359 resolved to an ISNI or USTC
  id**. That is the second edge class: not "Harvey read Livy" but "Harvey,
  reading Livy, reached for Machiavelli", a link the reader drew himself.
  Top targets: Dee→Cicero 208 works cited, Harvey→Cicero 31, Harvey→Aristotle 24.
  - `<book title="..."/>` matches the Books sheet's **"Standard ID"** short
    label, not the full title.
  - **Both sheets are RAGGED** — empty cells are omitted rather than emitted
    blank, and the author column in Books sits at index 6 behind five empties.
    A hand-rolled XLSX reader that concatenates `<c>` elements shifts every
    value left and reads the author as the title. Use openpyxl, or place cells
    by their `r` reference.
- **Repo last pushed 2020-06-01.** Static; no licence file.

### 3. The Walt Whitman Archive — `ingest/whitman.py`

*Measured:* 148 marginalia TEI items → 1,384 `<add>` insertions in Whitman's
hand, 708 marks (`underline` 667, `circled` 35, `doubleUnderline` 3). Plus one
authority file, `anc.02129`, holding **214 records of works he is documented to
have read**, each with a normalized author key, an edition, a reaction note and
the scholarly source of the claim.

*Stated:* "over 100 documents" transcribed, plus a ~1,200-page scrapboook.

- **The public site 403s every scripted fetch** — Cloudflare JS challenge,
  browser User-Agent or not. `github.com/whitmanarchive/whitman-marginalia`
  (branch `dev`, pushed 2025-08-13) is the only scriptable route in, and it is
  live rather than abandoned.
- **`<date type="readingDate">` is present on all 214 handlist records and
  populated on 28.** `grep -c` returns 214; the real payload is 28. Same shape
  on the sibling notes: `reaction`/`comments`/`source` all 214, `details` 24.
- **Whitman's annotations are mostly not marks in books.** They are reading
  notes on loose sheets, clipped articles, and a scrapbook. The source work is
  named in *prose* inside `<notesStmt>`; `<sourceDesc><bibl>` describes the
  manuscript's shelfmark, never the book being read. So `source_author` is left
  **empty** on the 148-item slice — 2,118 marks stranded — and that is a refusal,
  not an oversight. Resolving it means reading 148 editorial notes by hand.
- **Rights are explicit and restrictive:** *"Copyright © 2014 by Ed Folsom and
  Kenneth M. Price, all rights reserved… Redistribution or republication on
  other terms, in any medium, requires express written consent from the
  editors."* Counts and metadata only.

---

### 4. Derrida's Margins — `ingest/derrida.py`

*Measured:* 222 library records (83 flagged annotated, 50 carrying rows),
**1,419 annotations** + 251 insertions, **1,052 typed references** in *De la
grammatologie* (Quotation 632, Footnote 325, Citation 78, Epigraph 17), **107
distinct source authors** — Rousseau 37 volumes, Lévi-Strauss 13, Heidegger 10,
Plato, Husserl, Leibniz, Descartes, Hegel, Freud, Peirce, Saussure.

**The only openly licensed source in the corpus** — CC BY 4.0, stated in the
release's own rights field — so it is the one slice whose note text ships in
full. `ingest/derrida.py` re-checks that field on every fetch and refuses to
build if it changes.

Getting it was the whole trick, so the route is worth recording:

1. `derridas-margins.princeton.edu` is now a **read-only web archive**. Its
   "Download data for all interventions" link points at `doi.org/10.34770/2ezk-1104`.
2. That DOI resolves to `datacommons.princeton.edu`, which sits behind a JS
   challenge and **401s every scripted fetch**, browser headers or not.
3. The Blacklight JSON view is **not** challenged —
   `/discovery/catalog/doi-10-34770-2ezk-1104.json` — and hands back direct
   Globus download URLs *plus* the rights field. That is the route used.
4. **Figshare collection 4256927 is a trap.** It holds this data as CC0, which
   is more permissive and one API call away — but it is **v1 (2018) and
   superseded**, as its own article descriptions say. v1.1.1 has different
   filenames (`annotations.csv`, not `interventions.csv`) and different row
   counts. The easy download is the wrong one.

Scope is narrow and deliberately so: Derrida's library at PUL runs to ~13,800
volumes; this dataset is phase 1, the books behind *De la grammatologie* (1967).

Two things it adds that nothing else here has: `annotation_region`, a IIIF URL
cropped to the mark itself, so a passage anchor arrives with its image; and a
reference set in the reader's **published** voice rather than his margin, with
the annotated copy linked from each row.

---

### 5. Nietzsche — `ingest/nietzsche.py` — NO MARKS, and that is the finding

*Measured:* 1,081 references over **60 authors named**, across seven German
public-domain works from Project Gutenberg. **Zero volumes, zero marks.**

He is the best-documented annotator in the whole survey and the least
reachable. Each of these was established by fetching, 2026-08-27:

| what | result |
|---|---|
| Nietzsche Source module list | **exactly three** — eKGWB (Colli-Montinari text), DFGA (facsimiles of the *archive*), Studia Nietzscheana. The announced digital edition of the **library is not published**. Confirmed by rendering the AngularJS nav; the served HTML is a 1.3 KB shell, so a curl-and-read survey concludes wrongly either way. |
| DFGA scope | **manuscripts, not books.** Its search table columns are `td-mette`, `td-kwg`, `td-kwg-ix`, `td-writer` — Mette catalogue numbers and KGW sigla. |
| the 18,000 annotated pages | **facsimile only.** No transcription layer exists to ingest. |
| Weimar (`haab-digital.klassik-stiftung.de`) | **blocks automated access outright** — Anubis proof-of-work — and it gates `/viewer/oai?verb=Identify` too, which is the *sanctioned* harvesting route. A deliberate operator decision; respected. Do not solve the PoW with a headless browser. |
| K10plus provenance search | `pica.vbs`, `pica.prv`, `pica.vor` all return no such index. A former-owner route may exist under a different index name; unfinished. |
| Studia Nietzscheana | 2014–2018 volumes exist and the article lists are Solr-driven JS. Its per-book commentaries do carry "une documentation détaillée des traces de lecture et des annotations" — **real transcribed Lesespuren, small n**, and the one gated route worth finishing. POST to `/SN/search`. |
| the transcriptions themselves | Campioni, D'Iorio, Fornari, Fronterotta & Orsucci, *Nietzsches persönliche Bibliothek* (de Gruyter, 2003): **~2,200 titles with a complete index of reading traces.** In copyright, in print, purchasable. The Coleridge problem, and the only gate that matters. |

So he enters through the one class that is free, complete and redistributable:
naming another author in his own prose. Seven works — *Geburt der Tragödie*
(1872), *Menschliches* (1878), *Zarathustra* (1885), *Jenseits* (1886),
*Götzen-Dämmerung* (1888), *Ecce homo* (1888), and the posthumous *Wille zur
Macht* compilation, flagged as such because its selection and title are
Elisabeth Förster-Nietzsche's, not his.

**Closed gazetteer, never open-ended NER.** 66 declared authors in
`ingest/nietzsche_gazetteer.json`; every hit's sentence is written to
`_data/nietzsche_audit.json`. Three deliberate consequences:

1. **Zero is a real answer**, so three impossible controls are in the list
   (Melville, Whitman, Derrida). A hit fails the build.
2. **Recall is bounded by the list** — this is not a claim to have found
   everyone he cites.
3. **Ambiguous surnames are gated.** Every raw match on "Lange" across the seven
   texts is the German adjective (*Lange schlief Zarathustra*, *Langes Leben*,
   *alles Lange*); ungated, Friedrich Albert Lange ranks 28th on twelve false
   hits. "Strauss" catches a bouquet and an ostrich. Those need a first name
   within 60 characters.

The output validates against the books: *Geburt der Tragödie* → Euripides 59,
Socrates 58, Aeschylus 17. *Ecce homo* → Wagner 64. **Zarathustra names nobody
at all** — it is written as scripture, not argument — and is recorded as
`works_naming_nobody` rather than dropped, because an absent row reads as "not
processed".

Rights: public domain (d. 1900); Gutenberg's licence attaches to their marked-up
files, which are stripped. **This is NOT the Colli-Montinari eKGWB**, which is de
Gruyter copyright published online by permission and must never be redistributed
from here.

---

### 6. The Shakespeare and Company Project — `ingest/shakeco.py`

*Measured:* 5,235 members, 6,020 books, 35,523 events of which **21,059 are
borrows**. Restricted to authors of record: **520 readers on the roster, 253 with
events, 7,741 reader-book records, 8,432 attested-contact events, 1,420 distinct
source authors, 7,739 of 7,741 dated.**

**CC BY 4.0**, v1.2 (2022-01), fourteen datasets on Princeton Data Commons —
same host and same Blacklight JSON route as Derrida (section 4). The ingest
re-checks the rights field and refuses to build if it stops saying CC BY.

Sylvia Beach's Paris lending library, 1919–1941, from her surviving cards. Same
evidence class as Whitman's handlist — attested contact, no mark — but **dated to
the day, sourced to a named card, and 98.8% of events link a IIIF image of it**.
Nothing else in the corpus documents contact this precisely. Joyce 149 borrows,
Hemingway 123, Stein 60, Porter 49, Sarraute 41; Beckett, Pound, Benjamin, Djuna
Barnes, Bryher all hold cards.

This is what took the corpus from 7 readers to 527 and from 313 source authors to
1,705, and it is why **836 authors are now reached by more than one reader** —
Joyce by 55, Woolf by 50, Lawrence by 48.

Three things to get right, all guarded:

- **Reader selection is mechanical.** 5,235 members is too many for a corpus
  about authors and choosing the famous novelists would be cherry-picking, so the
  criterion is *has a VIAF url* — an entry in library authority files. 520 of
  5,235. `wikipedia` is carried too (345 have both) so a consumer can tighten.
  The roster is generated into `ingest/shakeco_readers.json` and **committed**,
  so `build_corpus.py`'s "no adapter invents a reader" guard still holds.
- **Every record is T3.** A card records a transaction. If this slice ever
  reported a T1 or T2 it would have invented a passage anchor, and its 8,432
  records would swamp Melville's 4,864 physical marks in any consumer filtering
  on `passage_anchored`. `test_shakeco_is_t3_only` enforces it.
- **A shared card double-counts across its members** — Archibald and Ada MacLeish
  show 236 events each, the same transactions. `member_uris` is multi-valued
  precisely so the project need not guess who borrowed. Summing across readers
  over-counts; per reader does not. Carried, not "fixed".

Excluded and counted, never silently dropped: 2,764 member uris and 127 book uris
listed in the `*_removed.csv` files (identities the project merged or withdrew
between versions), plus 789 marks whose book has no author of record.

---

## Gated (measured or read, not ingested — ranked by what they'd add)

| Source | Reader | Scale *(stated)* | What blocks it |
|---|---|---|---|
| **Beckett Digital Library** | Samuel Beckett | **815 extant volumes** with reading traces + transcriptions, 247 virtual entries | Subscription for the full module; the browse index renders only inside a JS/session app — a scripted fetch returns a 2.3 KB shell. Needs a real browser, then probably a login. **The single biggest literary addition available.** |
| **Charles Darwin's Library** (BHL + Cambridge) | Darwin | **730 annotated books** of 1,480, fully-indexed transcriptions (Di Gregorio & Gill) | **One free API key away, and the keyless routes are exhausted:** `api3` returns an empty body without a key; OAI-PMH (`/oai?verb=Identify`) works but serves bibliographic metadata only; the open `/data/TSV/` directory carries title/item/part/page/creator/subject and **no marginalia table** (checked 2026-08-27, dump dated 2026-08-01). Science rather than prose — but ~4× everything currently here. |
| **Corpus des notes marginales de Voltaire** | Voltaire | 9 printed volumes, TEI digitisation under way at Oxford | Openness unstated. Ask the Voltaire Foundation. |
| **Reading Experience Database (UK RED)** | ~many | ~30,000 recorded reading experiences, 1450–1945, graded by evidence type | Open University site 403s a plain fetch. Not marginalia — but it is the only source that would populate **T3 at scale**, across hundreds of readers instead of one. |
| **Nietzsche's *Lesespuren*** — the transcriptions | Nietzsche | **~2,200 titles, complete index of reading traces** | A **book**, not a website: *Nietzsches persönliche Bibliothek* (de Gruyter 2003). Purchasable. See section 5 — everything else about Nietzsche is settled and this is the only thing left. |
| **Studia Nietzscheana** per-book commentaries | Nietzsche | 2014–2018, small n | Real transcribed Lesespuren inside journal articles. Article lists are Solr-driven JS; POST to `/SN/search`. Unfinished, and the cheapest remaining Nietzsche win. |
| **Annotated Books Online** | ~100 early modern owners | **100+ annotated copies**, transcriptions and translations, **CC BY-NC** — so note text could ship | An ExtJS app with a gated backend: `/backend` exists and returns **403** to a bare request, `/backend/BookController` 404s, and no endpoint appears in the frontend JS. Next step is capturing the app's own request format in a browser. Readers are early modern owners, not literary authors — same profile as AOR. |
| **Newton Project** | Newton | Annotated books alongside the manuscripts | Site responds 200; `/his-library` is 404. Annotated-book coverage vs manuscript coverage unmeasured. |
| **Whitman's sibling data repos** | Whitman | `whitman-notebooks` 700 KB, `whitman-correspondence` **66 MB**, `whitman-other_books`, `whitman-reviews` | Same GitHub org, same TEI, already cloneable. His notebooks and 66 MB of letters are full of statements about what he was reading — a T3-with-a-date layer sitting one clone away, in a source whose marginalia slice is already wired. **Cheapest unclaimed win in the survey.** |
| **CERL / MEI** (Material Evidence in Incunabula) | many | copy-level provenance and annotation flags at scale | `data.cerl.org/mei/_search` responds. Flags annotation as a feature; carries no transcriptions. T3 at scale for incunabula, no passages. |
| **OPenn** (Penn) | many | openly licensed TEI + IIIF, no rights encumbrance at all | Responds 200. Manuscript descriptions; how much is annotated *printed* books is unmeasured. |
| **LibraryThing Legacy Libraries** | ~500 historical figures | personal library catalogues — Jefferson, Poe, Hemingway, Plath, Sontag | **403s automated access.** T3 ownership at real breadth if a sanctioned route exists. |
| **John Adams Library** (Boston Public Library) | Adams | ~3,500 volumes, heavily annotated, digitised on archive.org | BPL's own landing page is 404 as of 2026-08-27. Transcriptions likely absent — facsimile only. |

## Ruled out — don't re-research these

Carried over from the [shakespeare-marginalia](https://github.com/2016judea/shakespeare-marginalia)
survey, which reached the same wall:

- **Coleridge** — real marginalia, and prolific, but they exist only inside a
  modern in-copyright critical edition (Bollingen, 6 vols).
- **Keats** — his own 7-volume *Dramatic Works* at Harvard **is** IIIF-digitised
  and all 104 *Lear* pages were swept: **zero visible marks**. His real *Lear*
  marks are in a First Folio facsimile at Keats House London that isn't freely
  available. Text-only via the scholarship (Spurgeon 1928) was Aidan's explicit
  call for that project — don't assume it generalises.
- **Milton's First Folio** — five *Lear* marks located by hand off the Free
  Library of Philadelphia's facsimile (`archive.org/details/shk00001`, image
  index = printed page + 511). Real, but hand-located: ~1 mark per 5 pages of
  eyeballing. That rate is the honest cost of the general case.
- **Actor promptbooks** — Folger and the Shakespeare Birthplace Trust hold real
  ones; nothing freely digitised enough.
- **Tolstoy on Shakespeare** — a standalone essay, not annotations. T4, and out
  of scope by construction.

## The shape of the ceiling

Structured, transcribed, machine-readable marginalia exists for **a handful of
readers, deeply** — not for many readers, thinly. 527 readers, four centuries,
1,705 source authors, and 836 authors reached by more than one of them.

But note where that breadth came from: **one lending library supplied 520 of the
527 readers and every one of them at T3.** The deep, passage-anchored evidence is
still six readers — Melville, Harvey, Dee, Winthrop, Whitman, Derrida — and
breadth at T3 does not substitute for it. Nobody else in American literature has what Melville has.
That is a fact about the field's funding, not about the evidence: the marks
exist in the world — Nietzsche's 18,000 annotated pages are photographed and
sitting there — they just haven't been transcribed.

The licensing skews the same way and inversely to the size: the biggest slice
(AOR, 190,000 marks) is unlicensed, and the only CC BY one (Derrida) is the
second smallest. Openness is not correlated with scale here, so plan the rights
gate per source and never once for the corpus.

Which sets the strategy. **Do not wait for breadth.** The measurement this data
uniquely permits — do marked passages predict the reader's own later prose? —
needs *one* reader with enough marks and enough of his own prose to test
against. Melville is that reader, twice over: 4,864 marks, and a known-positive
control in Beale. Prove the method on him before spending a week on Darwin.

## Adjacent evidence classes

Two of these are now BUILT, arriving for free with AOR's authority tables and
Derrida's references — 10,693 records in `_data/references.jsonl`:

- ✅ **Epigraphs** — 17, in Derrida.
- ✅ **In-text quotation** — 632 quotations and 325 footnotes in *De la
  grammatologie*, each located in Derrida's own annotated copy. Plus 1,158 works
  cited inside Harvey's and Dee's marginal notes.

Still not built. Each is direct, first-person and machine-extractable, and each
is a different repo-sized decision. Listed so they aren't rediscovered as novel:

1. **Epigraphs at scale** — an author naming a source at the top of their own
   book, extracted from front matter across a whole corpus rather than one
   dataset. `literature-mutations` already holds 345 full texts and 60 MB of
   `bibliography_books.json`; this is in-house and cheap.
2. **In-text quotation at scale** — Melville quoting Shakespeare *inside*
   Moby-Dick, found by string search rather than by an editor. The natural
   companion to the marked-passage test.
3. **Letters** — Melville to Hawthorne, 1851, on discovering Shakespeare. Dated,
   first-person, and the Darwin Correspondence Project shows the form scales.
4. **Reading notebooks and commonplace books** — Hardy's *Literary Notebooks*,
   Woolf's reading notebooks. Same evidence class as Whitman's loose sheets:
   T1 without a passage anchor.
