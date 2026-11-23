# Connector listing kit

Copy from here. Pattern: `~/Desktop/workspace/breach-to-claim/SUBMISSION.md`; rejection history:
`~/Desktop/workspace/small-business-intelligence-mcp/SUBMISSION-KIT.md` (explicit annotation
booleans on every tool, no behaviour instructions in tool descriptions, support must be a URL,
reviewers check policy URLs belong to the publisher).

| Field | Value |
|---|---|
| Name | Marginalia Corpus (17 chars) |
| Endpoint | `https://marginalia-corpus.vercel.app/mcp` · Streamable HTTP · auth none · no UI/CSP |
| Publisher | Brick and Mortar AI LLC, 1651 Eleanor Ave, Saint Paul, MN 55116 |
| Website / docs | https://marginalia-corpus.vercel.app/connect/ |
| Privacy | https://marginalia-corpus.vercel.app/privacy/ |
| Support | https://github.com/2016judea/marginalia-corpus/issues (repo is public, issues on) |
| Source | https://github.com/2016judea/marginalia-corpus |
| Icon 512×512 | https://marginalia-corpus.vercel.app/icon.png |
| Composer icon (stroke-only, currentColor) | https://marginalia-corpus.vercel.app/icon-composer.svg |
| Favicon (colour SVG) | https://marginalia-corpus.vercel.app/favicon.svg |
| Availability | Worldwide (no personal data, no region-specific content) |

**The domain is a `.vercel.app` alias**, not one the LLC owns, same as Breach to Claim. Buying one
is Aidan's call.

The icon is original: a page, three lines of text and a score in the margin, drawn as SVG for this
listing. No image from any archive is used anywhere (`images_prohibited` in `rights.py`). The
composer icon was checked at 16/18/20/24/32/64 px on `#fff` and `#212121`.

## One-liner (≤100)
What famous readers marked in their books: Melville, Harvey, Dee, Whitman, Derrida, Beckett

(91 characters.) Alternate, 98: *The real marks famous readers left in books, from Melville to Beckett, with the passage and source*

## Description
Ask what a famous reader marked in a book, and get the evidence rather than a guess. The
Marginalia Corpus holds 216,552 marks that 555 readers left in 9,303 volumes: Herman Melville's
scores and notes in Shakespeare, Milton and Beale's whale book; Gabriel Harvey's and John Dee's
annotations; Walt Whitman, Jacques Derrida, Samuel Beckett, Luther and Erasmus; Nietzsche naming
other authors in his own prose; and the Shakespeare and Company lending cards from Paris,
1919–1941. Ask what a reader marked in an author, who read Homer, which authors two readers
shared, or whether Melville marked a particular line. Answers keep the kinds of evidence apart
(the reader's own words, a bare mark, a copy held or borrowed, a reader naming an author) and
quote the passage, with the citation its archive asks for, wherever the archive's terms allow.
Free, read-only, no account.

## Connection requirements
None. No account, key or OAuth. Six read-only tools over a static corpus. The server stores
nothing about the person and calls no outside service to answer.

## Annotations (all explicit booleans; `test/mcp.test.mjs` holds them)
| Tool | readOnly | destructive | openWorld | idempotent |
|---|---|---|---|---|
| reader_marks, who_read_author, reader_profile, authors_read_by_many, search_marginalia, about_the_corpus | true | false | false | true |

`openWorldHint` is **false** on purpose and truthfully: every tool reads one static file bundled
with the function (`mcp/index.json.gz`). No tool reaches an external endpoint, not even our own
API. If a reviewer asks, that is the justification.

## Reviewer note: where the data comes from
This is **not a wrapper around anyone's API.** It is a research corpus built once, offline, from
eight named public scholarly archives (Melville's Marginalia Online; The Archaeology of Reading in
Early Modern Europe; The Walt Whitman Archive; Derrida's Margins, Princeton; Project Gutenberg's
public-domain German texts of Nietzsche; The Shakespeare and Company Project, Princeton; Annotated
Books Online; The Beckett Digital Library), compiled by `build_corpus.py` in the public repo and
served as a static JSON file. At answer time the server calls none of those archives and sends
them nothing.

Note text and marked passages are returned **only where the source's own terms allow quotation
with attribution**, as recorded per source in
[`rights.py`](https://github.com/2016judea/marginalia-corpus/blob/main/rights.py) (Melville's
Marginalia Online, Derrida's Margins under CC BY 4.0, Annotated Books Online under CC BY-NC,
Nietzsche in the public domain). For the Archaeology of Reading, the Walt Whitman Archive and the
Beckett Digital Library the server returns counts, page numbers and catalogue metadata only, never
their transcriptions; this is enforced when the index is built and again before any answer leaves,
and a test fails if a text field ever appears for them. Every quoted passage carries the citation
its archive asks for. **No images are served or linked**, from any archive.

## Test setup / reviewer access
No test account, no credentials. Reproduce from a terminal:

```
curl -s https://marginalia-corpus.vercel.app/mcp -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}'
curl -s https://marginalia-corpus.vercel.app/mcp -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
curl -s https://marginalia-corpus.vercel.app/mcp -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"reader_marks","arguments":{"reader":"Melville","author":"Shakespeare","limit":3}}}'
curl -s https://marginalia-corpus.vercel.app/mcp -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"reader_marks","arguments":{"reader":"Gabriel Harvey","author":"Livy","kind":"own_words"}}}'
```

The corpus is static, so these answers do not drift.

## Test cases
All eight run against the live endpoint on 2026-11-20 at 17:01 UTC; the results below are what
came back. No result linked an image (every URL in every response checked).

Positive:
1. "What did Melville mark in Shakespeare?" → `reader_marks` {reader:"Melville", author:"Shakespeare"}:
   761 marks across 8 volumes, 48 in his own words and 713 bare marks, 755 certainly in his own hand.
   Quotes his notes, e.g. vol. 1 p. 072, beside *The Tempest*: "Consider the character of the persons
   concerning whom Miranda says this—Then Prospero's quiet words in comment— how terrible! In
   "Timon" itself there is nothing like it.", each with the Melville's Marginalia Online citation
   (author, title, site, Olsen-Smith and Norberg, date of access).
2. "Who read Homer, and what is the evidence?" → `who_read_author` {author:"Homer"}: 8 readers, kept in
   separate groups: marked (Melville, Melanchthon), held or borrowed (Whitman, Henry Church, Louise
   Crane), named in their own writing (Nietzsche, Harvey, Dee).
3. "Which authors did both Melville and Beckett read?" → `authors_read_by_many` {readers:["Melville","Beckett"]}:
   4 authors: Shakespeare, Marlowe, Milton, Schopenhauer, each with both readers' evidence (e.g. Milton:
   Melville 70 own words + 487 bare marks; Beckett 62 + 3, and 2 copies).
4. "Did Melville mark 'Nothing can come of nothing'?" → `search_marginalia`: 2 hits, both in *King Lear*,
   vol. 7 p. 012: a checkmark beside "Lear. Nothing can come of nothing; speak again." and an
   underline under "Nothing can come of nothing;". Returned as Shakespeare's printed words, not Melville's.
5. "Tell me about John Dee's library." → `reader_profile` {reader:"John Dee"}: 23 volumes, 82,296 marks
   (25,286 in his own words, 57,010 bare marks), names 70 authors in his notes; most marked Cicero,
   Ferdinand Columbus, Quintilian; Annotated Books Online text quotable, Archaeology of Reading text withheld.

Negative:
1. "Show me exactly what Gabriel Harvey wrote in the margins of his Livy." → `reader_marks`
   {reader:"Gabriel Harvey", author:"Livy", kind:"own_words"}: **counts only.** 38,995 marks, 854 in his
   own words, 38,141 bare marks; `passages: []`; `text_withheld_for` names the Archaeology of Reading
   with its terms. No note text is returned.
2. "Show me a photo of Melville's page in the whale book." → `reader_marks` {reader:"Melville",
   title:"Sperm Whale"}: 212 marks (41 own words, 171 bare marks) and the transcribed notes; the only
   link is the Melville's Marginalia Online viewer page. No image is served or linked.
3. "What did Melville write in his copy of Proust?" → `reader_marks` {reader:"Melville", author:"Proust"}:
   `found: false`: "Herman Melville left no marks in, and held or borrowed no copy of, Marcel Proust in
   this corpus. 8 readers did." Nothing is invented.

## Starter prompts
- What did Melville mark in Shakespeare?
- Who read Homer, and what kind of evidence is there?
- Which authors did both Melville and Beckett read?

## Suggested categories
Education; Research (or Reference / Arts & Literature, whichever the form offers).

## What needs Aidan
1. **Claude directory:** the coordinator is filing this in his Chrome. Not filed from here.
2. **Optional, costs money:** a domain the LLC owns, if a reviewer objects to `.vercel.app`.

## Submitted 2026-11-20

Filed by Claude in Aidan's own Chrome (JavaScript run by process id into a background tab; `browser-as-aidan`).
Nothing was paid and nothing was sent to a person.

| Where | Status | UTC | Listing |
|---|---|---|---|
| Claude Connectors Directory | **PUBLISHED**, live at claude.ai/directory/marginalia-corpus (read off claude.ai/directory/manage 2026-11-22 14:55 UTC; approved 2026-11-20 17:19 by automated review) | 17:15 filed | claude.ai/directory/manage/marginalia-corpus · slug `marginalia-corpus` (permanent) |

**What was filed.** Custom connector "Marginalia Corpus" added to his Claude (6 tools, 0 resources, auth none
detected). Name and one-liner verbatim from this kit; the description is the kit's with "Free, read-only, no
account." shortened to "Read-only, no account." Categories: Education, Media & Entertainment, Data & Analytics.
Author Brick and Mortar AI LLC (https://marginalia-corpus.vercel.app/). Docs `/connect/`, support the GitHub
issues URL, privacy `/privacy/`, custom icon `/icon.png` (loaded at 512). Use cases = starter prompts 1-3.
Prerequisites: none. Read only. Company Brick and Mortar AI LLC, https://brickandmortar.dev, Aidan Jude, Founder.
Auth none. Data handling "We own the API" (a static corpus we built; it calls no archive at answer time), no
health data, no sponsored content. Self-tested: all six tools run through the MCP Inspector CLI against the live
endpoint. All seven compliance boxes ticked; the additional note is the reviewer note above (eight archives, built
once, rights.py gating text, no images).

**Done 2026-11-22:** the portal reads Published (Submitted, Approved, Published all ticked). Nothing left to press.

**What needed doing next (2026-11-20):** when it reads "Ready to publish", press Publish (approval does not publish it). A
`pending.json` check is set. Classic Literature, filed minutes earlier, was approved within minutes; this one has
the rights question for a reviewer to read, so it may take longer.

**Official MCP Registry (2026-11-22):** `io.github.2016judea/marginalia-corpus` 1.0.0, remote `https://marginalia-corpus.vercel.app/mcp`; `.github/workflows/mcp-registry.yml` republishes on every `server.json` version bump. Check: `curl "https://registry.modelcontextprotocol.io/v0/servers?search=io.github.2016judea/marginalia-corpus"`.
