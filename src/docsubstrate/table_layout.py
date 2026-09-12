"""Column widths the way a browser computes them, from content.

Column widths are derived from content rather than a fixed column-weight
table. The algorithm measures what each column needs at its narrowest and at
its widest, then places the available space between those two bounds.

Kept as pure functions over measurements rather than inside the planner,
because the interesting part is arithmetic on numbers a caller supplies, and
because that makes the cases below testable without rendering anything.
"""

from __future__ import annotations

import math
import unicodedata
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from docsubstrate.ir import (
    Container,
    Grid,
    Horizontal,
    Image,
    LineBreak,
    Paragraph,
    Table,
    TableCell,
    Text,
)


@dataclass(frozen=True, slots=True)
class ColumnDemand:
    """What one column needs, at its narrowest and at its widest.

    ``minimum_mm`` is the widest piece that cannot be broken, so the column
    cannot be narrower without overflowing. ``maximum_mm`` is the content set
    on one line, past which extra width buys nothing.
    """

    minimum_mm: float
    maximum_mm: float

    def __post_init__(self) -> None:
        if self.maximum_mm < self.minimum_mm:
            raise ValueError(
                f"a column cannot want less at its widest ({self.maximum_mm}) "
                f"than at its narrowest ({self.minimum_mm})"
            )


@dataclass(frozen=True, slots=True)
class SpanningDemand:
    """A cell's demand on the sum of the columns it spans.

    A colspan does not belong to its first column.  It constrains the width
    of a consecutive range, and the table algorithm apportions only a
    shortfall across that range.  Keeping that distinction is what lets a
    20-column table with authored 3/3/2/4/1/1/1/1/4 spans retain all twenty
    columns instead of giving twelve of them zero width.
    """

    start: int
    span: int
    demand: ColumnDemand


def table_column_placements(rows):
    """Return each cell's start column after applying row spans.

    Raw cells-per-row is not the table grid width: a cell spanning from a
    preceding row still occupies columns that the following row omits.
    This is the HTML table-forming algorithm's structural input to both
    column sizing and drawing, so those two stages cannot disagree about
    where a cell lives.
    """
    occupied: list[int] = []
    placements = []
    column_count = 0
    for row in rows:
        starts = []
        cursor = 0
        for cell in row.cells:
            span = max(1, int(cell.colspan))
            while True:
                stop = cursor + span
                if stop > len(occupied):
                    occupied.extend(0 for _ in range(stop - len(occupied)))
                if not any(occupied[cursor:stop]):
                    break
                cursor += 1
            starts.append(cursor)
            for column in range(cursor, stop):
                occupied[column] = max(occupied[column], int(cell.rowspan))
            cursor = stop
            column_count = max(column_count, stop)
        placements.append(tuple(starts))
        occupied = [max(0, remaining - 1) for remaining in occupied]
    return tuple(placements), column_count


def apply_spanning_demands(
    columns: Sequence[ColumnDemand], spans: Iterable[SpanningDemand]
) -> tuple[ColumnDemand, ...]:
    """Apply colspan constraints to the sum of their underlying columns.

    Single-column cells establish the initial per-column minima and maxima.
    A spanning cell then contributes only when their sum cannot satisfy it;
    the shortfall is shared across the covered columns.  Processing narrow
    spans first preserves the more local constraint before a wider span is
    considered.

    A wider span grows columns which a narrower cell has already established,
    in proportion to their max-content demand.  It does not manufacture width
    for otherwise absent trailing grid columns.  This distinction is visible
    in a wide spanning cell, only participating columns receive the shared
    shortfall.

    This is deliberately a constraint operation, not ``demand / colspan``
    assigned unconditionally.  A wide heading spanning already-sized body
    columns must not erase the information those body cells supplied.
    """
    minima = [column.minimum_mm for column in columns]
    maxima = [column.maximum_mm for column in columns]
    count = len(columns)

    def add_shortfall(values, *, start, stop, shortfall, weights):
        active = [index for index in range(start, stop) if weights[index] > 0.0]
        recipients = active or list(range(start, stop))
        total_weight = sum(weights[index] for index in recipients)
        if total_weight > 0.0:
            for index in recipients:
                values[index] += shortfall * weights[index] / total_weight
        else:
            share = shortfall / len(recipients)
            for index in recipients:
                values[index] += share

    for item in sorted(spans, key=lambda value: (value.span, value.start)):
        start = max(0, item.start)
        stop = min(count, start + max(1, item.span))
        if start >= stop:
            continue
        minimum_shortfall = item.demand.minimum_mm - sum(minima[start:stop])
        if minimum_shortfall > 0:
            add_shortfall(
                minima,
                start=start,
                stop=stop,
                shortfall=minimum_shortfall,
                weights=maxima,
            )
            for index in range(start, stop):
                maxima[index] = max(maxima[index], minima[index])

        maximum_shortfall = item.demand.maximum_mm - sum(maxima[start:stop])
        if maximum_shortfall > 0:
            add_shortfall(
                maxima,
                start=start,
                stop=stop,
                shortfall=maximum_shortfall,
                weights=maxima,
            )

    return tuple(
        ColumnDemand(minimum, maximum)
        for minimum, maximum in zip(minima, maxima)
    )


def _breaks_anywhere(character: str) -> bool:
    """Whether a line may break after this character with no space present.

    CJK is the reason this function exists. `屬性` has no space in it and
    breaks between the two glyphs quite legally, so a column one glyph wide
    does not overflow -- it wraps, and the defect is silent. Latin words do
    not break, which is why a Latin table degrades visibly and a CJK one does
    not.
    """
    if character.isspace():
        return True
    # Wide and fullwidth East Asian forms used by supported report inputs.
    return unicodedata.east_asian_width(character) in {"W", "F"}


def unbreakable_runs(text: str) -> list[str]:
    """The pieces of `text` that must stay on one line."""
    runs: list[str] = []
    current: list[str] = []
    for character in text:
        if _breaks_anywhere(character):
            if current:
                runs.append("".join(current))
                current = []
            if not character.isspace():
                runs.append(character)
            continue
        current.append(character)
    if current:
        runs.append("".join(current))
    return runs


def demand_for(
    texts: Iterable[str], measure: Callable[[str], float], *, padding_mm: float = 0.0
) -> ColumnDemand:
    """What a column needs, given every string that appears in it.

    A forced line break bounds both answers. Max-content is the width the
    content takes when *nothing* wraps, and a `<br>` is not wrapping -- it
    breaks at every width, so it is a segment boundary rather than something
    to measure through. CSS Sizing says as much: the max-content size is the
    size the box takes "if none of its content wrapped", with forced breaks
    still taken.

    Measuring each segment independently keeps the column demand at the
    widest segment rather than joining text across a forced break.

    `\n` is the only forced break that reaches here: `_paragraph_text` emits
    one per `LineBreak` and nothing else produces one.
    """
    minimum = maximum = 0.0
    for text in texts:
        for segment in (text or "").split("\n"):
            stripped = segment.strip()
            if not stripped:
                continue
            maximum = max(maximum, measure(stripped))
            for run in unbreakable_runs(stripped):
                minimum = max(minimum, measure(run))
    return ColumnDemand(minimum + padding_mm, max(minimum, maximum) + padding_mm)


def distribute(demands: Sequence[ColumnDemand], available_mm: float) -> tuple[float, ...]:
    """Place `available_mm` across columns, between their two bounds.

    Three cases, which is what the specification says and what browsers do:

    * everything fits at its widest -- give each its maximum and share the
      surplus in proportion to those maxima, so a wide column stays wide;
    * everything fits at its narrowest but not at its widest -- give each its
      minimum and share what is left in proportion to how much more each
      column could still use;
    * not even the minima fit -- scale them down together and accept the
      overflow, because there is no width that avoids it.

    The third case is a real outcome rather than an error. A twenty-column
    matrix on A4 can genuinely have no non-overflowing solution, and the
    browser overflows too.
    """
    if not demands:
        return ()
    if available_mm <= 0:
        return tuple(0.0 for _ in demands)

    minima = [d.minimum_mm for d in demands]
    maxima = [d.maximum_mm for d in demands]
    total_min, total_max = sum(minima), sum(maxima)

    if total_max <= available_mm:
        surplus = available_mm - total_max
        if total_max <= 0:
            share = available_mm / len(demands)
            return tuple(share for _ in demands)
        return tuple(m + surplus * m / total_max for m in maxima)

    if total_min <= available_mm:
        slack = available_mm - total_min
        room = total_max - total_min
        if room <= 0:
            return tuple(minima)
        return tuple(
            lo + slack * (hi - lo) / room for lo, hi in zip(minima, maxima)
        )

    if total_min <= 0:
        share = available_mm / len(demands)
        return tuple(share for _ in demands)
    scale = available_mm / total_min
    return tuple(m * scale for m in minima)


# --- the document's own minimum, which is what the page is scaled to fit ---
#
# Everything above sizes columns inside a table whose width is already known.
# What follows asks the opposite question, one level up: how narrow can the
# *document* be made before something in it stops fitting? That is CSS's
# min-content width of the root box, and it is the number wkhtmltopdf's smart
# shrinking needs -- WebKit lays a printed page out at 1.25 papers, relays it
# out wider when the document does not fit, and paints the result back onto
# the paper. The scale it paints at is the paper over that laid-out width, so
# without this walk the engine has the first term and not the second.
#
# The three things that cannot shrink are the three the doc names: a
# `table-layout: fixed` table, an absolute stated width, and an image's
# intrinsic width. Text is the fourth and it was already here -- a paragraph
# cannot be narrower than its longest unbreakable run, which is what
# `unbreakable_runs` decides and `demand_for` measures.
#
# Percentages are the mirror image: a `width: 50%` box does not resist
# shrinking at all, so it contributes only whatever its contents do. CSS
# Sizing says as much -- a percentage is treated as `auto` when computing an
# intrinsic contribution -- and it is also the only safe reading here. The
# tempting alternative, that a `width: 25%` box needing 30mm forces its
# parent to 120mm, turns one long word in a `col-1` into a twelvefold demand
# and shrinks a page that otherwise fits. A false clamp is worse than a
# missed one, because it moves every document.
#
# What that costs is genuine multi-column overflow, where two side-by-side
# halves each hold something too wide. WebKit does not use min-content there
# either: it lays the page out at the paper and takes `documentRect`, which
# is offset-based and so catches exactly that case. Recorded in
# `docs/capability-gaps.md` rather than approximated here.


@dataclass(frozen=True, slots=True)
class MinContentWidth:
    """The narrowest a box can be, and what decided that.

    ``source`` exists because this number changes every page of a document
    that overflows, so "why 181mm" has to be answerable without a debugger.
    It names the mechanism, not the element: an unexplained page scale is the
    same defect as an unexplained constant.
    """

    width_mm: float = 0.0
    source: str = "empty"

    def widest(self, other: MinContentWidth) -> MinContentWidth:
        return other if other.width_mm > self.width_mm else self


@dataclass(frozen=True, slots=True)
class ContentMetrics:
    """What the walk needs from whoever owns the fonts and the px bridge.

    Passed in rather than imported so this module stays arithmetic over
    measurements a caller supplies, the way the column functions above do.
    """

    #: ``(text, font_size_pt) -> mm``.
    text_width_mm: Callable[[str, float], float]
    #: The size text takes when no box in the chain states one.
    body_font_size_pt: float
    #: Millimetres per CSS pixel, for an image's intrinsic width.
    mm_per_px: float
    #: Normal horizontal padding of a table cell, both edges together.
    cell_padding_mm: float = 0.0
    #: The width a percentage resolves against, when the caller knows it.
    #: Zero means "unknown", and a percentage then contributes nothing
    #: intrinsic, which is what CSS Sizing says and what this walk did
    #: before the extent below was added.
    available_mm: float = 0.0


def _inline_text(children) -> str:
    """The paragraph's text, with its forced breaks kept as `\n`.

    Dropping a `LineBreak` here would join the runs on either side of it into
    one, so `demand_for` would read a break as the absence of one -- exactly
    backwards, and the same defect in the min-content walk that the column
    demands had in their maxima.
    """
    parts = []
    for child in children:
        if isinstance(child, Text):
            parts.append(child.displayed)
        elif isinstance(child, LineBreak):
            parts.append("\n")
    return "".join(parts)


def _paragraph_min_content(block: Paragraph, metrics: ContentMetrics) -> MinContentWidth:
    text = _inline_text(block.children)
    if not text.strip():
        return MinContentWidth()
    size = block.font_size_pt or metrics.body_font_size_pt
    demand = demand_for([text], lambda value: metrics.text_width_mm(value, size))
    return MinContentWidth(demand.minimum_mm, "unbreakable-text")


def _image_min_content(block: Image, metrics: ContentMetrics) -> MinContentWidth:
    if block.width_mm is not None:
        return MinContentWidth(block.width_mm, "image-stated-width")
    if block.width_fraction is not None:
        # A percentage-width replaced element shrinks with its container.
        return MinContentWidth()
    if block.max_width_fraction is not None:
        # `max-width: 100%` is exactly the licence to shrink, and it is what
        # the badge logo states. An intrinsic width read through it would
        # make every logo a reason to scale the page down.
        return MinContentWidth()
    if not block.natural_size_px:
        return MinContentWidth()
    width = block.natural_size_px[0] * metrics.mm_per_px
    if block.max_width_mm is not None:
        width = min(width, block.max_width_mm)
    return MinContentWidth(width, "image-intrinsic")


def _cell_min_content(cell: TableCell, metrics: ContentMetrics) -> MinContentWidth:
    """One cell's minimum: its text, its contents, and its own declarations."""
    inner = MinContentWidth()
    texts = []
    for block in cell.blocks:
        if isinstance(block, Paragraph):
            texts.append(_inline_text(block.children))
        else:
            inner = inner.widest(block_min_content(block, metrics))
    size = cell.font_size_pt or metrics.body_font_size_pt
    demand = demand_for(texts, lambda value: metrics.text_width_mm(value, size))
    # `nowrap` is a licence to overflow, not to wrap: the whole line is the
    # minimum. That is the same reading `_column_widths` applies.
    text_min = demand.maximum_mm if cell.nowrap else demand.minimum_mm
    inner = inner.widest(MinContentWidth(
        text_min, "cell-nowrap" if cell.nowrap else "unbreakable-text"
    ))
    if cell.min_width_mm:
        inner = inner.widest(MinContentWidth(cell.min_width_mm, "cell-min-width"))
    if cell.width_mm:
        inner = inner.widest(MinContentWidth(cell.width_mm, "cell-stated-width"))
    padding = (
        cell.padding_mm[1] + cell.padding_mm[3]
        if cell.padding_mm is not None else metrics.cell_padding_mm
    )
    return MinContentWidth(inner.width_mm + padding, inner.source)


def _table_min_content(
    table: Table, metrics: ContentMetrics
) -> MinContentWidth:
    """A table's minimum: its columns' minima, or its fixed declarations.

    ``table-layout: fixed`` takes widths from the first row only, so a fixed
    table's minimum is the sum of those declarations -- content cannot make it
    narrower and cannot make it wider. An auto table is the sum of its
    columns' min-content demands, apportioned through the same colspan
    constraint solver the planner uses, so a spanning heading cannot inflate
    columns that no body cell occupies.
    """
    placements, count = table_column_placements(table.rows)
    if count <= 0:
        return MinContentWidth()
    spacing = table.border_spacing_mm[0] * (count + 1)
    frame = 2 * table.border_width_mm

    if table.layout_mode == "fixed":
        stated = 0.0
        first = table.rows[0] if table.rows else None
        for cell in (first.cells if first is not None else ()):
            if cell.width_mm:
                stated += cell.width_mm
        if stated > 0.0:
            return MinContentWidth(stated + spacing + frame, "fixed-table")

    demands = [ColumnDemand(0.0, 0.0) for _ in range(count)]
    #: What made each column as wide as it is, so the table can pass on the
    #: reason its widest column gives rather than a label of its own. A sum
    #: has no single cause, but the column that dominates it does.
    reasons = ["table-columns"] * count
    spans = []
    for row, starts in zip(table.rows, placements):
        for cell, index in zip(row.cells, starts):
            if index >= count:
                continue
            span = max(1, min(int(cell.colspan), count - index))
            demand = _cell_min_content(cell, metrics)
            entry = ColumnDemand(demand.width_mm, demand.width_mm)
            if span == 1:
                current = demands[index]
                if entry.minimum_mm > current.minimum_mm:
                    reasons[index] = demand.source
                demands[index] = ColumnDemand(
                    max(current.minimum_mm, entry.minimum_mm),
                    max(current.maximum_mm, entry.maximum_mm),
                )
            else:
                spans.append(SpanningDemand(index, span, entry))
    demands = apply_spanning_demands(demands, spans)
    total = sum(demand.minimum_mm for demand in demands) + spacing + frame
    widest = max(range(count), key=lambda index: demands[index].minimum_mm)
    return MinContentWidth(total, reasons[widest])


def block_min_content(block, metrics: ContentMetrics) -> MinContentWidth:
    """The narrowest this block can be laid out without overflowing.

    Anything not listed here -- a page break, a line break, a page number --
    puts no floor under the document width, which is why the fall-through is
    zero rather than an error.
    """
    if isinstance(block, Table):
        table = _table_min_content(block, metrics)
        if block.width_mm:
            table = table.widest(MinContentWidth(block.width_mm, "table-stated-width"))
        return table
    if isinstance(block, Paragraph):
        return _paragraph_min_content(block, metrics)
    if isinstance(block, Image):
        return _image_min_content(block, metrics)
    if isinstance(block, Grid):
        # Cells share the row rather than adding to it, so the row's
        # minimum is whichever cell needs the most. The span does not
        # multiply that demand: see the note above on percentages.
        widest = MinContentWidth()
        for cell in block.cells:
            inner = _blocks_min_content(cell.blocks, metrics)
            widest = widest.widest(inner)
        return widest
    if isinstance(block, Horizontal):
        # A flex row that cannot wrap lays its cells side by side, so their
        # minima add up. One that can wrap may put every item on a line of
        # its own, so its minimum is its widest item -- which is what CSS
        # Sizing says, and the difference decides whether a document
        # overflows. Bootstrap's `.row` wraps.
        widest = MinContentWidth()
        total = 0.0
        for cell in block.cells:
            inner = _blocks_min_content(cell.blocks, metrics)
            if cell.width_mm:
                inner = inner.widest(MinContentWidth(cell.width_mm, "flex-stated-width"))
            widest = widest.widest(inner)
            total += inner.width_mm
        if block.wraps or widest.width_mm <= 0.0:
            return widest
        total += block.gap_mm * max(0, len(block.cells) - 1)
        return MinContentWidth(total, "flex-row")
    if isinstance(block, Container):
        inner = _blocks_min_content(block.children, metrics)
        if block.width_mm:
            inner = inner.widest(MinContentWidth(block.width_mm, "stated-width"))
        insets = (
            block.padding_mm[1] + block.padding_mm[3]
            + block.margin_start_mm + block.margin_end_mm
            + sum(edge.width_pt * 25.4 / 72.0 for edge in (block.border[1], block.border[3]))
        )
        if inner.width_mm <= 0.0:
            return inner
        return MinContentWidth(inner.width_mm + insets, inner.source)
    return MinContentWidth()


def _box_extent_mm(block, metrics: ContentMetrics, available_mm: float) -> float:
    """How far right this block's box reaches, in its parent's content space.

    The second operand of shrink-to-fit is not an intrinsic minimum. WebKit
    scales a printed page by comparing the paper with `documentRect`, which
    is where the laid-out boxes end -- and a box placed by an offset ends
    further right than anything intrinsic can express. `min-content` treats a
    percentage as `auto` and an offset as no width at all, which is right for
    "how narrow can this be" and blind to "how wide is this".

    Only two things push a box past its containing block: a leading offset
    and a definite width. Everything else fits by construction, so a block
    with neither contributes nothing and the recursion stays shallow.

    Percentages resolve against the containing block's *content* width, which
    is why an available width is threaded down rather than read from one
    constant.
    """
    if isinstance(block, Container):
        lead = (
            block.margin_start_mm + block.padding_mm[3]
            + block.border[3].width_pt * 25.4 / 72.0
        )
        trail = (
            block.margin_end_mm + block.padding_mm[1]
            + block.border[1].width_pt * 25.4 / 72.0
        )
        # A percentage resolves against the containing block, which is the
        # width passed in -- not against what is left of it after this box's
        # own offset. Getting that wrong gave the CV's sidebar half of
        # `192.775 - 112.889` instead of half of 192.775.
        if block.width_mm is not None:
            own = block.width_mm
        elif block.width_fraction is not None:
            own = block.width_fraction * available_mm
        else:
            own = 0.0
        edges = (
            block.padding_mm[1] + block.padding_mm[3]
            + (block.border[1].width_pt + block.border[3].width_pt) * 25.4 / 72.0
        )
        # What this box offers its own children: its content width when it has
        # a definite one, otherwise whatever is left of the containing block.
        inner_available = (
            max(0.0, own - edges) if own > 0.0
            else max(0.0, available_mm - lead - trail)
        )
        deepest = max(
            (_box_extent_mm(child, metrics, inner_available)
             for child in block.children),
            default=0.0,
        )
        return lead + max(own, deepest)
    if isinstance(block, (Grid, Horizontal)):
        # Cells share the row, so the row reaches as far as its furthest
        # cell rather than the sum -- the same reasoning the intrinsic walk
        # applies to a wrapping flex row.
        return max(
            (_box_extent_mm(inner, metrics, available_mm)
             for cell in block.cells for inner in cell.blocks),
            default=0.0,
        )
    return 0.0


def document_extent_mm(
    blocks, metrics: ContentMetrics, *, available_mm: float
) -> MinContentWidth:
    """The furthest right edge any box in the document reaches.

    Zero when nothing overflows, because a document whose boxes all fit puts
    no floor under the paper and must not be scaled for it.
    """
    if available_mm <= 0.0:
        return MinContentWidth()
    widest = max(
        (_box_extent_mm(block, metrics, available_mm) for block in blocks),
        default=0.0,
    )
    if widest <= available_mm:
        return MinContentWidth()
    return MinContentWidth(widest, "box-extent")


def _blocks_min_content(blocks, metrics: ContentMetrics) -> MinContentWidth:
    widest = MinContentWidth()
    for block in blocks or ():
        widest = widest.widest(block_min_content(block, metrics))
    return widest


def document_min_content_mm(
    blocks, metrics: ContentMetrics, *, insets_mm: float = 0.0
) -> MinContentWidth:
    """The narrowest the whole document can be laid out.

    ``insets_mm`` is the horizontal padding of the page box itself -- Odoo's
    ``.o_body_pdf.o_css_margins { padding: 0 11mm }`` -- which the adapter
    carries as page margins rather than as IR padding. It belongs here
    because WebKit measures the document against the paper, not against the
    paper less its own CSS padding.
    """
    widest = _blocks_min_content(blocks, metrics)
    if widest.width_mm <= 0.0:
        return widest
    return MinContentWidth(widest.width_mm + insets_mm, widest.source)


def shrink_to_fit_scale(
    available_mm: float, min_content_mm: float, *, floor: float
) -> float:
    """Choose a bounded print scale from available and demanded widths.

    Empty or non-positive geometry has no usable overflow signal and keeps
    the neutral scale.  Otherwise the width ratio is clipped to the closed
    interval from ``floor`` through one.  The lower bound must itself be a
    finite fraction in that interval so configuration errors fail loudly.
    """
    lower_bound = float(floor)
    if not math.isfinite(lower_bound) or not 0.0 < lower_bound <= 1.0:
        raise ValueError("floor must be a finite fraction in (0, 1]")
    available = float(available_mm)
    demand = float(min_content_mm)
    if not math.isfinite(available) or not math.isfinite(demand):
        raise ValueError("print widths must be finite")
    if available <= 0.0 or demand <= 0.0:
        return 1.0
    ratio = available / demand
    if ratio >= 1.0:
        return 1.0
    if ratio <= lower_bound:
        return lower_bound
    return ratio
