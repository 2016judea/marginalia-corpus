# Data model: the Marginalia MCP server

Written 2026-11-20, before the server, from the questions a Claude user asks about
famous readers. Each field names the question it answers. Then each was checked
against `_data/`.

## Entities

**Reader** (a person who read; one person can have several `reader_id`s, e.g.
Samuel Beckett is `beckett` in his own library and `shakeco:beckett` on a Paris
lending card, so readers are grouped by name)
- name, life dates: *who is this, and when did they read?*
- sources: *whose archive documents them, and may their words be quoted?*

**Author** (whose book was read, or who was named)
- canonical name: *did anyone read Homer?* Fuzzy-matched, because users type "Shakspeare".

**Volume** (one physical copy a reader held)
- title, author, edition date, repository, shelfmark, page link: *which copy, where is it now?*
- counts by tier, and by tier in the reader's own hand: *how much did they mark it, and was it really them?*
- reading dates where attested: *when did they read it?*

**Passage** (one mark, with text, where the source permits quoting)
- marked_text, the source author's printed words: *which lines did they mark?*
- reader_text, the reader's own words: *what did they write beside it?*
- translation, page, hand, hand_is_reader: *what does it say, where is it, whose hand?*

**Reference** (the reader naming an author in their own published prose or a note)
- anchor_text, kind, in_work: *where did Derrida quote Rousseau, and in what words?*

**Evidence sets** (kept apart, never summed)
- marked (T1 own words, T2 bare mark): *who left marks in Shakespeare?*
- held or borrowed (T3): *who owned or borrowed a copy?*
- named in their writing (reference edges): *who wrote about Schopenhauer?*
- named as a person in a note: *who mentions Socrates?*

## Reality check, field by field

| field | source | fillable? |
|---|---|---|
| reader, life dates | `readers.json` | yes, 555 |
| volume metadata, page link | `volumes.jsonl` | yes, 9,303 |
| counts by tier and own hand | `marks.jsonl.gz` aggregated per volume | yes, 216,552 marks |
| passage text | `marks.jsonl.gz` | **only where `rights.py` sets `emit_text`**: Melville, Derrida, ABO. AOR, Whitman and Beckett ship counts and metadata only. A rights limit, not a data gap. |
| reference text | `references.jsonl` | Derrida (CC BY) and Nietzsche (public domain); AOR names only |
| evidence sets | `edges.json`, the three sets as built | yes |
| images | — | never: `images_prohibited` on every source with images |

Nothing in the ideal model is unfillable by the data. The withheld text is withheld
by the sources' terms, and the server says so per source rather than shrinking the
model around it.
