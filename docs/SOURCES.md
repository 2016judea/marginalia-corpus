# Sources: what's in, what's gated, what's ruled out

Surveyed 2026-08-27. **A count marked *measured* was produced by fetching the
data and counting it in this session. A count marked *stated* is the project's
own published figure, unverified.** The distinction matters: three of the
measured figures came out materially different from the stated ones.

---

## In (three sources, ingested and building)

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
- **15 of 35 books have no resolved source author** and are `null` in
  `ingest/aor_books.json` on purpose. AOR's per-page XML carries no book-level
  bibliography, only the project's short directory label. Guessing an author
  from "De navigatione" or "Voarchadumia" would put a fabricated citation into
  an influence graph whose entire claim is that its edges are physical facts.
  **Open task:** each book's record on archaeologyofreading.org carries a full
  bibliographic header — read those 15 and fill the map.
- Two authority tables the README links, **not yet ingested and both worth it**:
  - **530 books cited *inside* the notes**, with author, full title and USTC
    ids ([sheet](https://docs.google.com/spreadsheets/d/15Ny9EUVMd0OPExIL9XnGP1k-Z_DL7yUMGw3KB3CKEbI))
  - **2,484 people named inside the notes**, with ISNI identifiers
    ([sheet](https://docs.google.com/spreadsheets/d/1X8_iNd-C5D4wdg9DeLuED9fJsd0gO7q97sGRxXHI5Fs))

  Those make a *second* edge class: not "Harvey read Livy" but "Harvey, reading
  Livy, reached for Machiavelli" — a connection the reader drew himself, in his
  own hand, at a located passage. Nothing else in the survey offers that.
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

## Gated (measured or read, not ingested — ranked by what they'd add)

| Source | Reader | Scale *(stated)* | What blocks it |
|---|---|---|---|
| **Beckett Digital Library** | Samuel Beckett | **815 extant volumes** with reading traces + transcriptions, 247 virtual entries | Subscription for the full module; the browse index renders only inside a JS/session app — a scripted fetch returns a 2.3 KB shell. Needs a real browser, then probably a login. **The single biggest literary addition available.** |
| **Charles Darwin's Library** (BHL + Cambridge) | Darwin | **730 annotated books** of 1,480, fully-indexed transcriptions (Di Gregorio & Gill) | BHL 403s a plain fetch; its API v3 needs a free key. Science rather than prose — but ~4× everything currently here, and Darwin's marks on Malthus and Lyell are influence by any definition. |
| **Corpus des notes marginales de Voltaire** | Voltaire | 9 printed volumes, TEI digitisation under way at Oxford | Openness unstated. Ask the Voltaire Foundation. |
| **Reading Experience Database (UK RED)** | ~many | ~30,000 recorded reading experiences, 1450–1945, graded by evidence type | Open University site 403s a plain fetch. Not marginalia — but it is the only source that would populate **T3 at scale**, across hundreds of readers instead of one. |
| **Newton Project** | Newton | Annotated books alongside the manuscripts | Site responds 200; annotated-book coverage vs manuscript coverage unmeasured. |
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
readers, deeply** — not for many readers, thinly. Melville has 52 volumes;
nobody else in American literature has one. That is a fact about the field's
funding, not about the evidence: the marks exist in the world, they just haven't
been transcribed.

Which sets the strategy. **Do not wait for breadth.** The measurement this data
uniquely permits — do marked passages predict the reader's own later prose? —
needs *one* reader with enough marks and enough of his own prose to test
against. Melville is that reader, twice over: 4,864 marks, and a known-positive
control in Beale. Prove the method on him before spending a week on Darwin.

## Adjacent evidence classes, deliberately not built

Each is direct, first-person and machine-extractable, and each is a different
repo-sized decision. Listed so they aren't rediscovered as novel:

1. **Epigraphs** — an author naming a source at the top of their own book.
   Self-declared, verifiable in the text, and extractable at scale from front
   matter. `literature-mutations` already holds 345 full texts and 60 MB of
   `bibliography_books.json`; this is in-house and cheap.
2. **In-text quotation** — Melville quoting Shakespeare *inside* Moby-Dick.
   Direct, and it is the natural companion to the marked-passage test.
3. **Letters** — Melville to Hawthorne, 1851, on discovering Shakespeare. Dated,
   first-person, and the Darwin Correspondence Project shows the form scales.
4. **Reading notebooks and commonplace books** — Hardy's *Literary Notebooks*,
   Woolf's reading notebooks. Same evidence class as Whitman's loose sheets:
   T1 without a passage anchor.
