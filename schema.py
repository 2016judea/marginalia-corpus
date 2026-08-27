'''
    Author: Aidan Jude

    The record types, and the evidence ladder that is this repo's whole
    reason to exist.

    A mark in a book is not an opinion about influence. It is a physical
    fact: this reader held this edition of this author and attended to
    this passage. Scholarly attribution -- which is what an influence
    graph normally gets validated against -- is an interpretation of that
    kind of fact, made by someone who was not there.

    So every record here carries a TIER, and tiers are never merged into
    one "influence score". The point of the corpus is that the tiers are
    different KINDS of evidence, and a consumer must be able to ask for
    only the direct ones.

      T1  autograph   the reader's own words, written in the margin,
                      beside a locatable passage. The strongest thing on
                      record: first person, at the point of contact.
      T2  mark        a non-verbal mark -- score, underline, checkmark,
                      X -- locating a passage the reader attended to.
                      Direct, and it carries a passage, but says nothing
                      about what the reader thought.
      T3  copy        the reader demonstrably owned or borrowed the
                      volume; no surviving marks. Direct contact, no
                      passage.
      T4  documented  a scholar (or a model, or Wikidata) asserts the
                      influence. Interpretive. This repo does NOT emit
                      T4 -- literature-mutations already has two such
                      sources (known_influences.json, 377 LLM-enumerated;
                      wikidata_influences.json, 350 P737 claims) and the
                      whole reason for this corpus is that they are the
                      weaker evidence class.

    A tier is a fact about the page, never about our licence. Where
    rights.py bars redistributing a note's text, the mark stays T1 with
    `text_withheld=True` and an empty reader_text -- demoting it to T2
    instead would let a permissions decision quietly rewrite the evidence.
    Caught 2026-08-27: the AOR slice reported 0 autographs on 20,000 notes
    in Harvey's and Dee's own hands, purely because emit_text is False.

    Rule that fails silently if broken, so it is structural here:
    MARKED TEXT AND READER TEXT ARE DIFFERENT FIELDS.

      marked_text  = the SOURCE AUTHOR's printed words that the mark sits
                     on. Melville scoring a Lear line yields Shakespeare's
                     words, not Melville's.
      reader_text  = the READER's own inscribed words. Only present on T1.

    Collapsing them produces a corpus that looks perfect and asserts that
    Melville wrote "Nothing can come of nothing". The shakespeare-marginalia
    project learned this by hand ("only a reader's own written words get
    quoted", corrected 2026-08-03); here it is a schema constraint with a
    test behind it.
'''

from dataclasses import dataclass, field, asdict
from typing import Optional

TIER_AUTOGRAPH = "T1_autograph"
TIER_MARK = "T2_mark"
TIER_COPY = "T3_copy"

TIERS = (TIER_AUTOGRAPH, TIER_MARK, TIER_COPY)

# Mark types that carry the reader's own words. Anything not listed is a
# non-verbal mark and must NOT be given a reader_text.
VERBAL_MARK_TYPES = {
    "annotation", "notation", "autograph", "emendation", "annotated",
    "emended", "text", "insert", "presentation", "marginalia",
}


@dataclass
class Reader:
    '''An author who annotated. The node this corpus is about.'''
    reader_id: str
    name: str
    birth: Optional[int] = None
    death: Optional[int] = None
    wikidata: Optional[str] = None
    note: str = ""


@dataclass
class Volume:
    '''One physical annotated volume, held somewhere, by someone.'''
    volume_id: str
    source_dataset: str
    reader_id: str
    source_author: str             # canonical, via names.canonical()
    source_title: str
    source_date: str = ""          # imprint date of the EDITION the reader held
    repository: str = ""
    shelfmark: str = ""
    url: str = ""
    n_marks: int = 0
    source_author_raw: str = ""    # exactly as the source emitted it
    co_bound_authors: tuple = ()   # other works bound in the same volume; a mark
                                   # cannot be attributed between them, so these
                                   # get NO edge -- see aor_resolve_books.py
    read_from: str = ""            # when the reader read it, where attested
    read_to: str = ""
    evidence_source: str = ""      # WHO attests it, for a T3 record. A T3 with
                                   # no evidence_source is an unsourced claim,
                                   # i.e. the thing this corpus exists to beat.


@dataclass
class Mark:
    '''
        One intervention by a reader on one page. The atom of the corpus.
    '''
    mark_id: str
    volume_id: str
    reader_id: str
    tier: str
    mark_type: str                 # the source dataset's own vocabulary, kept raw
    page: str = ""
    marked_text: str = ""          # the SOURCE AUTHOR's printed words
    reader_text: str = ""          # the READER's own inscribed words (T1 only)
    hand: str = ""                 # which hand, where the dataset attributes it
    hand_is_reader: bool = True     # False when the dataset attributes the mark to
                                   # someone OTHER than, or ambiguously with, the
                                   # volume's reader. 433 of Melville's 4,864 marks
                                   # are "HMorESM" -- Herman or his wife Elizabeth --
                                   # and counting those as his overstates him ~9%.
                                   # Filter on this before making a claim about a
                                   # named reader.
    lang: str = ""
    translation: str = ""          # where the dataset supplies one (AOR does)
    refs_people: tuple = ()        # people named INSIDE the note
    url: str = ""
    text_withheld: bool = False    # the reader DID write words; rights.py bars
                                   # us from redistributing them. The tier is a
                                   # fact about the page, not about our licence.

    def validate(self):
        if self.tier not in TIERS:
            raise ValueError(f"{self.mark_id}: unknown tier {self.tier!r}")
        if self.tier == TIER_MARK and self.reader_text:
            raise ValueError(
                f"{self.mark_id}: a non-verbal mark ({self.mark_type}) carries "
                f"reader_text {self.reader_text[:40]!r}. See schema.py -- this is "
                f"the failure that makes the corpus assert the source author's "
                f"words are the reader's."
            )
        if self.tier == TIER_AUTOGRAPH and not self.reader_text and not self.text_withheld:
            raise ValueError(
                f"{self.mark_id}: T1 with no reader_text and text_withheld unset. "
                f"Either the reader wrote words (set text_withheld when rights.py "
                f"bars emitting them) or this is not an autograph."
            )
        return self


def tier_for(mark_type: str, has_reader_text: bool) -> str:
    '''
        The dataset's mark_type vocabulary -> our tier. A type in
        VERBAL_MARK_TYPES only earns T1 if words actually came through;
        Melville's XML carries e.g. type="annotation" type2="xmark" where
        the words are the annotation and the xmark is decoration.
    '''
    if mark_type.lower() in VERBAL_MARK_TYPES and has_reader_text:
        return TIER_AUTOGRAPH
    return TIER_MARK


@dataclass
class Reference:
    '''
        The SECOND evidence class, and it is not a mark.

        A reference is the reader naming another author or work -- inside a
        marginal note, or inside their own published book. Where a mark says
        "this reader attended to this passage", a reference says "this reader
        connected this passage to that author", and the reader drew the link
        themselves.

        Two shapes, both direct:
          in a NOTE     Harvey, reading Livy, writes a note that names
                        Machiavelli. AOR tags 3,687 <person> and 468 <book>
                        elements inside the notes for exactly this.
          in a WORK     Derrida quotes Rousseau in De la grammatologie, and
                        the project located the quoted passage in Derrida's
                        own annotated copy. 1,052 references, typed
                        Quotation / Footnote / Citation / Epigraph.

        Kept out of Mark and out of the tier ladder on purpose: a reference
        is a different measurement, and merging the two would produce a
        weight that means nothing.
    '''
    ref_id: str
    reader_id: str
    kind: str                      # quotation | footnote | citation | epigraph
                                   # | named_in_note | work_cited_in_note
    source_dataset: str
    in_volume: str = ""            # the annotated volume the note sits in
    in_work: str = ""              # the reader's OWN work making the reference
    target_name: str = ""          # person or work named
    target_author: str = ""
    target_id: str = ""            # ISNI / USTC / project URI, where given
    anchor_text: str = ""          # the reader's own words making the reference
    page: str = ""
    url: str = ""


def rows(objs):
    return [asdict(o) for o in objs]
