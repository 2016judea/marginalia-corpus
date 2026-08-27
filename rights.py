'''
    Author: Aidan Jude

    Per-source rights. The build FAILS if a source has no entry here.

    Borrowed wholesale from the bricks platform's LAYER_RIGHTS gate, for
    the same reason: a corpus that quietly redistributes someone else's
    transcription is a corpus you have to withdraw later, and a withdrawal
    takes the whole slice with it.

    Three of the sources here are academic projects with no licence file at
    all. "No licence" is not "public domain" -- it is "ask". So the default
    is `emit_text=False`: the ingest still reads the text (it has to, to
    count and to tier), and the shipped `_data/` carries counts, metadata
    and edges only. Nothing is lost analytically for the influence-graph
    use; passage-level text builds locally into `cache/`, which is
    gitignored.

    `emit_text=True` is set only where the source's own stated terms permit
    quotation with attribution.
'''

SOURCES = {
    "monline": dict(
        name="Melville's Marginalia Online",
        url="https://melvillesmarginalia.org",
        editors="Steven Olsen-Smith and Peter Norberg, eds.",
        terms=(
            "Policies page: written/edited material may be quoted or cited with "
            "author + title + 'Melville's Marginalia Online' + the two main editors "
            "+ date of access. The stated restriction is on PHOTOGRAPHIC IMAGES "
            "(one-time display permission from holding institutions), not on the "
            "transcriptions. Read 2026-08-27."
        ),
        emit_text=True,
        attribution_required=True,
        images_prohibited=True,
    ),
    "aor": dict(
        name="The Archaeology of Reading in Early Modern Europe",
        url="https://archaeologyofreading.org",
        editors="Sheridan Libraries (JHU), CELL (UCL), CDH (Princeton); Mellon-funded",
        terms=(
            "GitHub repo livesandletters/aor carries NO licence file and the site "
            "publishes no reuse statement found as of 2026-08-27. Counts and "
            "metadata only until someone asks them. Contact CELL before any bulk "
            "republication of the note transcriptions or translations."
        ),
        emit_text=False,
        attribution_required=True,
        images_prohibited=True,
    ),
    "whitman": dict(
        name="The Walt Whitman Archive — Annotations and Marginalia",
        url="https://whitmanarchive.org/manuscripts/marginalia",
        editors="Kenneth M. Price and Ed Folsom, dirs.; Matt Cohen, marginalia project",
        terms=(
            "Data repo whitmanarchive/whitman-marginalia carries no licence file. "
            "The Archive's public terms are CC BY-NC-ND on site content; the TEI "
            "repos state no licence. Counts and metadata only pending a check. "
            "Read 2026-08-27."
        ),
        emit_text=False,
        attribution_required=True,
        images_prohibited=True,
    ),
    "derrida": dict(
        name="Derrida's Margins",
        url="https://derridas-margins.princeton.edu",
        editors=("Katie Chenoweth, Rebecca Sutton Koeser, Renee Altergott, Alexander "
                 "Baron-Raiffe, Jean Bauer, Chad Cordova, Austin Hancock, Benjamin "
                 "Hicks, Nick Budak, Kevin McElwee, Chloe Vettier; Center for Digital "
                 "Humanities, Princeton"),
        terms=(
            "Derrida's Margins Datasets v1.1.1, doi:10.34770/2ezk-1104, distributed by "
            "Princeton Data Commons. Rights field reads exactly: 'CC BY -- Creative "
            "Commons Attribution 4.0 International'. The only openly licensed source "
            "in the corpus, and therefore the only one whose note text ships in full. "
            "An earlier v1 on Figshare is CC0 but is SUPERSEDED -- use the DOI. "
            "Read 2026-08-27."
        ),
        emit_text=True,
        attribution_required=True,
        images_prohibited=True,   # the IIIF page images are PUL's, not CC BY
    ),
    "nietzsche": dict(
        name="Friedrich Nietzsche, works (Project Gutenberg German texts)",
        url="https://www.gutenberg.org",
        editors="Public domain; Nietzsche died 1900",
        terms=(
            "The underlying texts are public domain worldwide. Project Gutenberg's "
            "own licence attaches to their MARKED-UP FILES and to use of the "
            "trademark, not to the public-domain work, so the header and licence "
            "block are stripped and the text itself is emitted. Same treatment "
            "literature-mutations already applies to its 345 Gutenberg texts. "
            "NOTE this is NOT the Colli-Montinari critical text (eKGWB) -- that is "
            "de Gruyter copyright, published online by permission, and must never "
            "be redistributed from here. Read 2026-08-27."
        ),
        emit_text=True,
        attribution_required=False,
        images_prohibited=False,
    ),
    "shakeco": dict(
        name="The Shakespeare and Company Project",
        url="https://shakespeareandco.princeton.edu",
        editors=("Joshua Kotin, dir.; Center for Digital Humanities, Princeton. "
                 "Dataset v1.2 (2022-01), doi:10.34770 series"),
        terms=(
            "Princeton Data Commons rights field reads 'CC BY -- Creative Commons "
            "Attribution 4.0 International' on all fourteen deposited datasets "
            "(members, books, events, and the combined package, v1 / v1.1 / v1.2). "
            "Data derives from Sylvia Beach's own lending cards and logbooks; the "
            "card IMAGES are Princeton University Library's, served from IIIF, and "
            "are linked rather than copied. Read 2026-08-27."
        ),
        emit_text=True,
        attribution_required=True,
        images_prohibited=True,
    ),
}


class RightsError(RuntimeError):
    pass


def check(source_key: str) -> dict:
    '''Gate. Call before emitting anything from a source.'''
    if source_key not in SOURCES:
        raise RightsError(
            f"source {source_key!r} has no rights entry in rights.py. Add one "
            f"(with the terms you actually read, and the date you read them) "
            f"before ingesting it."
        )
    return SOURCES[source_key]


def may_emit_text(source_key: str) -> bool:
    return bool(check(source_key)["emit_text"])


def citation(source_key: str) -> str:
    s = check(source_key)
    return f'{s["name"]}. {s["editors"]} {s["url"]}. Accessed 2026-08-27.'
