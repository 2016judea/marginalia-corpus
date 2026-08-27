'''
    Author: Aidan Jude

    Cross-source author-name reconciliation, kept as small and as
    mechanical as possible.

    Three sources, three conventions for the same person:
        Melville's Marginalia Online   "William Shakespeare"
        Archaeology of Reading         "Patavinus, Titus Livius"
        Derrida's Margins              "Rousseau, Jean-Jacques"

    Without reconciliation the edge set cannot compare readers at all --
    Melville->Homer and Dee->Ovid would be in different namespaces, and the
    whole point is a graph across readers.

    Two operations, deliberately separated:

    1. `flip` -- mechanical. "Rousseau, Jean-Jacques" -> "Jean-Jacques
       Rousseau". No knowledge, no claim, reversible.
    2. `ALIASES` -- a claim, so it is tiny, explicit, and each entry says
       why. Adding a name here asserts that two strings are one person, and
       a wrong entry merges two authors into one node without erroring.
       Do not grow this by pattern-matching; add only what a source
       actually emits.

    `source_author_raw` is always preserved on the record. This never
    overwrites, only adds a `source_author` for joining.
'''

import re

# Each entry: a raw string a source actually emits -> the canonical form,
# with the reason. Verified against the emitting source, 2026-08-27.
ALIASES = {
    # AOR's bibliography catalogues Livy under the Latin habitational form
    # ("of Padua"); every other source and literature-mutations use "Livy".
    "Patavinus, Titus Livius": "Livy",
    # AOR spells Columbus's son in Spanish; he is normally Ferdinand Columbus.
    "Colòn, Fernando": "Ferdinand Columbus",
    # AOR: "Pliny, Caius" is Pliny the Elder (Gaius Plinius Secundus). His
    # nephew, Pliny the Younger, is NOT in the corpus -- checked, because
    # collapsing the two would be exactly the silent merge this table risks.
    "Pliny, Caius": "Pliny the Elder",
    # AOR: the Voarchadumia's author, Latinized. Also seen as Giovanni
    # Agostino Panteo.
    "Panteus, Joannes": "Joannes Pantheus",
    # AOR: Olaus Magnus, catalogued surname-first as "Magnus, Olaus".
    "Magnus, Olaus": "Olaus Magnus",
    # Melville's Marginalia gives the translator's name form for Chapman's
    # Homer as plain "Homer"; AOR gives "Homer". Nothing to do -- noted so a
    # later session does not "fix" a non-problem.
}

_SUFFIX = re.compile(r"\b(Sir|Saint|St\.?|Dr\.?)\b", re.I)


def flip(name: str) -> str:
    '''
        "Last, First" -> "First Last". Mechanical and conservative:
        untouched if there is no comma, if there are two or more commas
        (a compound catalogue heading, e.g. dates or an epithet), or if
        either side is empty.
    '''
    n = " ".join((name or "").split())
    if n.count(",") != 1:
        return n
    last, first = (p.strip() for p in n.split(","))
    if not last or not first:
        return n
    return f"{first} {last}"


def canonical(name: str) -> str:
    '''The one function callers use. Alias first, then the flip.'''
    n = " ".join((name or "").split())
    if not n:
        return ""
    if n in ALIASES:
        return ALIASES[n]
    flipped = flip(n)
    return ALIASES.get(flipped, flipped)
