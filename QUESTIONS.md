# Questions people bring, and the tool that answers each

Per `~/.claude/CLAUDE.md`, *Every question theme gets a tool* (2026-11-22). Counts are PostHog
`mcp_tool_call`, `site = marginalia-corpus`, all time to 2026-11-22. The volume is small (40 calls)
and includes the directory filing's own test runs, so it ranks themes rather than proving demand.
Themes with no call on record are marked **inferred**: they come from what a reader asks a chatbot
about famous readers and their books, not from our logs.

## From the logs

| theme | user's words | calls | tool |
|---|---|---|---|
| what a reader marked | "what did Melville mark in Shakespeare" | 9 | `reader_marks` |
| search the margins | "who wrote 'nothing can come of nothing' in a margin" | 8 | `search_marginalia` |
| one reader's library | "what did John Dee read" | 7 | `reader_profile` |
| authors many readers reached | "which authors did the most readers mark" | 7 | `authors_read_by_many` |
| who read an author | "who read Homer" | 7 | `who_read_author` |
| what is in here | "what sources does this use" | 2 | `about_the_corpus` |

Unknown tool names were logged only as `unknown` until 2026-11-22. **Now logged:** `attempted`, the
tool name a caller reached for (letters, digits, `_.-` only, 60 characters). Read it before the next
pass.

## Inferred themes, each with a door (shipped 2026-11-22)

| theme | user's words | tool | engine |
|---|---|---|---|
| did X read Y | "did Melville read Shakespeare", "did Beckett read Proust" | `did_reader_read_author` | the reader's edges for one author, yes/no first, kinds kept apart |
| their own notes | "what did Melville write in the margins of his Milton" | `what_reader_wrote_in_margins` | reader_marks, own words only |
| what they thought of a subject | "what did Nietzsche write about Wagner" | `what_reader_said_about` | search_marginalia, reader's words only |
| reading in common | "what did Dee and Harvey both read" | `what_readers_both_read` | authors_read_by_many with readers |
| Shakespeare and Company | "what did Hemingway borrow from Sylvia Beach", "who borrowed Joyce" | `shakespeare_and_company_borrowing` | lending-card edges, by author or by member |

## Gaps left, and why

| theme | user's words | why not yet |
|---|---|---|
| a reader outside the corpus | "what did Jefferson annotate" | 555 readers from eight archives; the tools say so and name the closest |
| withheld text | "show me Whitman's notes" | Whitman Archive, Archaeology of Reading and Beckett Digital Library withhold text by their terms; counts only |
| images of the pages | "show me the page Melville marked" | IIIF images belong to the holding libraries; we link the source page, never the image |
| a book's whole marginal history | "everyone who marked this copy of Montaigne" | volumes are keyed by reader; a by-title door across readers is the next one to build if `attempted` shows it |
