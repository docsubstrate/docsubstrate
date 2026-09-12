"""Which parsed block each drawn string came from.

A rendered PDF says where text landed and not what authored it. Comparing a
report against its reference output therefore cannot ask the question that matters when
positions disagree -- *which* block moved -- because both sides are anonymous
glyph runs by then. This module carries the answer out of band.

Two rules define it, and both exist because the obvious shortcuts are wrong:

* The identity is the parser's stable DOM path, never anything read back
  out of the PDF. A coordinate identity cannot survive the case
  it is needed for, and a text identity cannot tell two blocks that
  say the same thing apart -- which every invoice does, several times a page.
* The sidecar never travels inside the PDF. Attribution that changes the bytes
  being compared would be measuring itself.

The join back is deliberately narrow. A row records the baseline and pen
position the renderer drew at, an extracted anchor records the same baseline
flipped about the page height, and geometry is used only to *locate* a row
that already knows its own identity. Where the located rows disagree, or where
none is found, the answer is unknown -- never the neighbour's.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from docsubstrate.pageplan import ResolvedDocument, TextRun

#: Bumped when the row shape changes, so a reader can refuse a stale file
#: rather than silently mismatching fields.
SIDECAR_VERSION = 1

MM_PER_PT = 25.4 / 72.0

#: How far a located row may sit from the anchor that should contain it.
#: ReportLab serialises coordinates to a couple of decimals, so exact float
#: equality does not survive the round trip. This is a locating tolerance and
#: nothing else: widening it can only make an attribution *ambiguous*, which
#: is reported as unknown, never as a guess.
LOCATE_EPSILON_PT = 0.05


@dataclass(frozen=True, slots=True)
class TextProvenanceRow:
    """One drawn string, with the block that authored it."""

    page: int
    x_pt: float
    baseline_pt: float
    text: str
    font_size_pt: float
    source_block_id: str | None


def _pt(mm: float) -> float:
    return mm / MM_PER_PT


def sidecar_rows(document: ResolvedDocument) -> tuple[TextProvenanceRow, ...]:
    """Every text command in a resolved document, in page order."""
    rows: list[TextProvenanceRow] = []
    for index, page in enumerate(document.pages, start=1):
        for command in page.commands:
            if not isinstance(command, TextRun):
                continue
            if not command.text:
                continue
            rows.append(TextProvenanceRow(
                page=index,
                x_pt=_pt(command.x_mm),
                baseline_pt=_pt(command.y_mm),
                text=command.text,
                font_size_pt=command.font_size_pt,
                source_block_id=command.source_block_id,
            ))
    return tuple(rows)


def sidecar(document: ResolvedDocument) -> dict:
    """The serialisable form written beside a rendered PDF."""
    return {
        "version": SIDECAR_VERSION,
        "page_heights_pt": tuple(_pt(page.height_mm) for page in document.pages),
        "rows": tuple(
            {
                "page": row.page,
                "x_pt": round(row.x_pt, 4),
                "baseline_pt": round(row.baseline_pt, 4),
                "text": row.text,
                "font_size_pt": row.font_size_pt,
                "source_block_id": row.source_block_id,
            }
            for row in sidecar_rows(document)
        ),
    }


@dataclass(frozen=True, slots=True)
class Attribution:
    """What a sidecar can say about one extracted anchor.

    `blocks` is every distinct block id located inside the anchor, kept for
    diagnosis whatever the verdict. `known` means the anchor resolved to
    exactly one block and is the only state a caller may act on: an anchor
    covering two blocks has no single author, so reporting it as known would
    let one block's id stand for glyphs another block drew, and would count
    towards coverage as though the question had been answered.
    """

    blocks: tuple[str, ...]
    known: bool

    @property
    def block(self) -> str | None:
        return self.blocks[0] if self.known and len(self.blocks) == 1 else None


UNKNOWN = Attribution(blocks=(), known=False)


def _squeeze(value: str) -> str:
    """Text with every space removed, for comparing what was drawn."""
    return "".join(value.split())


def attribute(
    *,
    page: int,
    baseline_pt: float,
    x0_pt: float,
    x1_pt: float,
    sidecar_document: dict | None,
    text: str | None = None,
) -> Attribution:
    """Locate the rows an extracted anchor was drawn from.

    `baseline_pt` is in the PDF's own bottom-left frame, the same one the
    renderer drew in. A caller holding a top-down measurement converts it with
    the page height *the extractor reported*, not the one in this file: a
    plan's 297mm page serialises as 842pt, and inverting through the
    millimetre value puts every baseline 0.11pt out -- enough to lose the
    join, and exactly the kind of near-miss that would otherwise be papered
    over by widening the tolerance.
    """
    if not sidecar_document:
        return UNKNOWN
    if sidecar_document.get("version") != SIDECAR_VERSION:
        return UNKNOWN

    located: list[tuple[float, str, str | None]] = []
    for row in sidecar_document.get("rows") or ():
        if row.get("page") != page:
            continue
        if abs(row.get("baseline_pt", 0.0) - baseline_pt) > LOCATE_EPSILON_PT:
            continue
        x = row.get("x_pt", 0.0)
        if x < x0_pt - LOCATE_EPSILON_PT or x > x1_pt + LOCATE_EPSILON_PT:
            continue
        located.append((x, row.get("text", ""), row.get("source_block_id")))
    located.sort()
    found: list[str | None] = [block for _x, _text, block in located]
    if text is not None and found:
        # The rows must account for the glyphs. An extractor groups a line by
        # proximity, not by author, so two blocks whose baselines differ by
        # more than the locating tolerance can still arrive as one anchor --
        # and then exactly one row falls inside it and would otherwise be
        # reported as the whole line's author. Requiring the located text to
        # reconstruct the anchor catches that: a shortfall means a
        # contributor was not located, whatever its block.
        drawn = _squeeze("".join(item[1] for item in located))
        if drawn != _squeeze(text):
            return Attribution(
                blocks=tuple(sorted(
                    block for block in set(found) if block is not None
                )),
                known=False,
            )
    if not found:
        return UNKNOWN
    named = tuple(sorted({block for block in found if block is not None}))
    # Two ways an anchor fails to have one author, and both are unknown:
    # a synthesised run -- page chrome, or the separator between two
    # paragraphs in one cell -- contributed glyphs no block claims, or the
    # located rows name more than one block. Returning either as known would
    # put one block's id on glyphs it did not draw, and would count towards
    # coverage as though it had been resolved.
    if any(block is None for block in found) or len(named) != 1:
        return Attribution(blocks=named, known=False)
    return Attribution(blocks=named, known=True)


def attribute_anchors(
    anchors: Iterable,
    sidecar_document: dict | None,
    page_heights_pt: Sequence[float],
) -> tuple[Attribution, ...]:
    """`attribute` over `compare_pdf.TextAnchor`-shaped items.

    `page_heights_pt` must come from the extraction being attributed, so a
    top-down anchor inverts through the page height its own reader saw.
    """
    return tuple(
        attribute(
            page=anchor.page,
            baseline_pt=(
                page_heights_pt[anchor.page - 1] - anchor.y_top_pt
                if 1 <= anchor.page <= len(page_heights_pt)
                else float("nan")
            ),
            x0_pt=anchor.x0_pt,
            x1_pt=anchor.x1_pt,
            sidecar_document=sidecar_document,
        )
        for anchor in anchors
    )


def coverage(attributions: Sequence[Attribution]) -> tuple[int, int]:
    """`(attributed, total)` -- what a caller needs to decide UNCHECKED."""
    return sum(1 for item in attributions if item.known), len(attributions)
