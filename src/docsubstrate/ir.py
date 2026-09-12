"""Minimal backend-neutral document IR.

The bounded model carries only the semantics exercised by its synthetic
contracts; it is not an attempt to clone HTML/CSS.

A block carries its own outer spacing (``space_before_mm`` / ``space_after_mm``,
``None`` meaning "unspecified, use the engine default"). That is not a CSS
concession: every target expresses it natively -- Typst ``block(above:, below:)``,
ReportLab ``spaceBefore``/``spaceAfter``, HTML margins -- which is the test for
whether something belongs in the IR at all. Paint that only one backend can
express (borders, tints, text transforms) stays out.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True, slots=True)
class Text:
    """A run of text plus the display function declared over it.

    ``transform`` is a presentation function (``text-uppercase`` and friends),
    kept beside the value rather than applied to it: the untransformed value
    is what compares against the record, and the function is what compares
    against what the source engine drew.
    """

    value: str
    bold: bool = False
    italic: bool = False
    transform: str | None = None
    #: The `font-family` in force over this run, under its own CSS name. The
    #: renderer picks a face by script when this is absent, which is right
    #: for text and wrong for a glyph at a private-use codepoint: no script
    #: test calls it CJK, so it would go to the one face guaranteed not to
    #: have it.
    font_family: str | None = None
    #: A colour declared on this inline run. Paragraph.fill_rgb remains the
    #: inherited/default paint; this field is for spans such as text-muted
    #: that change only part of a line.
    fill_rgb: tuple[float, float, float] | None = None
    #: A company-scoped selector that paints this run. Kept semantic because
    #: the parser proves selector scope before the render request supplies the
    #: company's actual colours.
    colour_role: str | None = None
    #: True for text inside an `<a href>`. The stylesheet colours only those:
    #: `a:not([href]):not([class])` resets a bare anchor to `inherit`, and
    #: that rule outranks the plain `a` one.
    link: bool = False

    @property
    def displayed(self) -> str:
        """The value as a renderer must draw it."""
        if self.transform == "upper":
            return self.value.upper()
        if self.transform == "lower":
            return self.value.lower()
        if self.transform == "capitalize":
            return self.value.title()
        return self.value


@dataclass(frozen=True, slots=True)
class PageNumber:
    fill_rgb: tuple[float, float, float] | None = None


@dataclass(frozen=True, slots=True)
class TotalPages:
    fill_rgb: tuple[float, float, float] | None = None


@dataclass(frozen=True, slots=True)
class LineBreak:
    pass


Inline = Text | PageNumber | TotalPages | LineBreak


@dataclass(frozen=True, slots=True)
class Paragraph:
    children: Sequence[Inline] = field(default_factory=tuple)
    align: str | None = None
    role: str | None = None
    #: A unitless CSS ``line-height``, as a multiple of the font size.  It
    #: remains a ratio through inheritance, so a descendant with a different
    #: font size computes a different line box. ``None`` means the body
    #: default unless ``line_height_mm`` carries an absolute authored length.
    line_height_ratio: float | None = None
    #: A CSS ``line-height`` authored as a length. CSS inherits its computed
    #: absolute value rather than recomputing it from a descendant font size;
    #: retaining millimetres also keeps the planner from mistaking ``0.6cm``
    #: for a unitless line box that wkhtmltopdf advances on its pixel grid.
    line_height_mm: float | None = None
    #: Literal element typography.  These stay optional so the ordinary Odoo
    #: report path keeps the compiled body/heading defaults; label and thermal
    #: templates that state their type inline carry the winning values here.
    font_size_pt: float | None = None
    fill_rgb: tuple[float, float, float] | None = None
    #: A company-scoped cascade colour the parser proved applies here.
    #: ``None`` means the cascade was silent; the planner must not guess.
    colour_role: str | None = None
    letter_spacing_mm: float = 0.0
    #: A `border-top` on the block this text came from, in points. Odoo rules
    #: off its footer that way, and the engine had no notion of a border on
    #: anything but a table.
    rule_above_pt: float = 0.0
    space_before_mm: float | None = None
    space_after_mm: float | None = None
    #: Whether this paragraph's collapsible whitespace is content rather than
    #: a line boundary. A line strips its own leading and trailing whitespace
    #: and so does this planner; a space that is itself
    #: an inline item between two others is at neither boundary and is drawn.
    #: The difference is positional, so it is decided where the siblings are
    #: known and carried here, rather than guessed where runs are wrapped.
    preserves_collapsed_space: bool = False
    #: Where this paragraph's text came from in the parsed tree, as a
    #: a stable DOM path. Provenance only: nothing downstream may read it
    #: to decide geometry, and two paragraphs that lay out identically must
    #: still carry different values. ``None`` means the block was synthesised
    #: rather than parsed -- page chrome, for instance -- and a consumer must
    #: report that as unknown rather than attributing it to a neighbour.
    source_block_id: str | None = None
    #: CSS `white-space: nowrap`, resolved off the same cascade
    #: `TableCell.nowrap`/`Cell.nowrap` already read for a table cell.
    #: `True` means this paragraph's text does not wrap, full stop -- the
    #: planner lays out one line however wide it runs, the way a browser
    #: keeps `.text-truncate` (which implies `nowrap`) on one line rather
    #: than breaking it across several.
    nowrap: bool = False


@dataclass(frozen=True, slots=True)
class Image:
    src: str
    alt: str | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    #: A percentage width cannot become millimetres until the planner knows
    #: the containing block.  Keep the declaration as a ratio, just as Table
    #: does, instead of baking one report's column width into the parser.
    width_fraction: float | None = None
    #: CSS max constraints are especially important inside table cells: the
    #: employee badge gives its logo only a full-width maximum and
    #: a forty-point height limit and lets intrinsic dimensions choose the result.
    max_width_mm: float | None = None
    max_width_fraction: float | None = None
    max_height_mm: float | None = None
    #: Intrinsic dimensions read from the evaluated payload's PNG/JPEG
    #: header.  They preserve ``height:auto`` without asking a backend image
    #: decoder to rediscover information the QWeb adapter already has.
    natural_size_px: tuple[int, int] | None = None
    #: Whether ``natural_size_px`` is the compatibility profile's fixed
    #: failed-resource size rather than decoded intrinsic dimensions.  The
    #: planner uses the flag to select the failed-resource sizing contract.
    natural_size_is_failed_replaced_element: bool = False
    #: CSS Images defines ``object-fit: fill`` as the initial value.  Carry
    #: the computed declaration because Canvas otherwise defaults to keeping
    #: the intrinsic ratio and silently paints a smaller image inside a box
    #: whose dimensions were already resolved correctly.
    object_fit: str = "fill"
    #: A replaced element floats like any other box after its used width has
    #: been resolved from declarations and intrinsic dimensions.
    float_side: str | None = None
    clear: str | None = None
    space_before_mm: float | None = None
    space_after_mm: float | None = None


@dataclass(frozen=True, slots=True)
class TableCell:
    blocks: Sequence["Block"] = field(default_factory=tuple)
    colspan: int = 1
    rowspan: int = 1
    header: bool = False
    align: str | None = None
    bold: bool = False
    nowrap: bool = False
    role: str | None = None
    valign: str | None = None
    #: Width constraints the stylesheet puts on this cell, in millimetres.
    #: A column takes the widest constraint of its cells.
    min_width_mm: float | None = None
    max_width_mm: float | None = None
    #: The cell's own CSS ``width`` declaration.  Unlike min/max constraints,
    #: this is consulted only by ``table-layout: fixed`` and only from the
    #: first row; carrying the declaration keeps that algorithm out of the
    #: parser.
    width_mm: float | None = None
    width_fraction: float | None = None
    #: Per-cell inline padding, clockwise from top. ``None`` keeps the table
    #: skin's normal cell padding rather than silently zeroing it.
    padding_mm: tuple[float, float, float, float] | None = None
    #: The cell's own borders, clockwise from top -- the same representation
    #: `Container.border` uses, because it is the same authored property.
    #:
    #: A table's edges are divided between its boxes by the stylesheet, not
    #: by orientation: `.table-bordered` declares `border-width: 1px 0` on
    #: rows and `0 1px` on cells, so the horizontal edges belong to the row
    #: and the vertical ones to the cell. Keeping this as `border` rather
    #: than as a rule or a line keeps that division sayable; a renderer's
    #: line is how an edge gets painted, not what it is.
    border: tuple[Border, Border, Border, Border] = field(
        default_factory=lambda: (Border(), Border(), Border(), Border())
    )
    #: Selector-matched presentation from the offline compiled CSS profile.
    #: Property names and values deliberately stay in CSS's vocabulary so a
    #: backend resolves them against its active px bridge; flattening this to
    #: a theme-specific field would discard the predicate again.
    css: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    font_size_pt: float | None = None
    line_height_ratio: float | None = None
    line_height_mm: float | None = None
    #: Inherited paint selected by a scoped company rule on the cell itself.
    #: Kept separate from ``role`` because the semantic class exists even
    #: when its required ``o_company_N_layout`` ancestor does not.
    colour_role: str | None = None
    #: CSS ``visibility:hidden`` retains the cell's box, intrinsic sizing,
    #: and participation in table layout while suppressing the cell and all
    #: descendant paint.  Product and lot label sheets use exactly that
    #: authored contract for the unused slots on their final page; treating
    #: it as ``display:none`` collapses the grid, while ignoring it paints
    #: the placeholder record repeatedly.
    visible: bool = True


@dataclass(frozen=True, slots=True)
class TableRow:
    cells: Sequence[TableCell] = field(default_factory=tuple)
    #: Selector-matched row chrome. Rows and cells are separate CSS boxes:
    #: Bootstrap's bordered table puts horizontal rules on ``tr`` and
    #: vertical rules on ``td``/``th``. Collapsing both into a table theme is
    #: the predicate loss this field prevents.
    css: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    #: The row group's element and this row's 1-based child position in it.
    #: CSS ``nth-child`` counts within the parent group, never across the
    #: whole table. Native IR may leave these unset; evaluated HTML records
    #: the actual thead/tbody/tfoot structure.
    group: str | None = None
    group_index: int | None = None
    #: CSS row height is a minimum. Percentages stay unresolved until the
    #: planner knows the table's used height, just like percentage cell/table
    #: widths stay structural until their containing box is known.
    height_mm: float | None = None
    height_fraction: float | None = None
    #: `"total"` for the `o_total` row of a totals band. Every stock layout
    #: singles that row out -- a rule above it, and under the shaped layouts
    #: the company colour behind it -- so it is not just the last body row.
    role: str | None = None


@dataclass(frozen=True, slots=True)
class Table:
    rows: Sequence[TableRow] = field(default_factory=tuple)
    repeat_header_rows: int = 0
    borderless: bool = False
    compact: bool = False
    column_weights: Sequence[float] = field(default_factory=tuple)
    align: str | None = None
    width_fraction: float | None = None
    width_mm: float | None = None
    height_fraction: float | None = None
    height_mm: float | None = None
    #: CSS chooses the column algorithm explicitly.  ``auto`` preserves the
    #: content-sized path; ``fixed`` uses only first-row/col declarations.
    layout_mode: str = "auto"
    border_collapse: str = "collapse"
    #: Horizontal and vertical ``border-spacing``.  The report reset states
    #: zero; inline declarations such as the employee badge's 4pt override it.
    border_spacing_mm: tuple[float, float] = (0.0, 0.0)
    #: Legacy HTML ``border=\"1\"`` is one CSS pixel.  It participates in the
    #: table border box even when no report-theme skin is applied.
    border_width_mm: float = 0.0
    kind: str = "plain"
    attach: bool = False
    theme: str | None = None
    space_before_mm: float | None = None
    space_after_mm: float | None = None


@dataclass(frozen=True, slots=True)
class GridCell:
    blocks: Sequence["Block"] = field(default_factory=tuple)
    span: int = 1
    offset: int = 0
    align: str | None = None


@dataclass(frozen=True, slots=True)
class Grid:
    cells: Sequence[GridCell] = field(default_factory=tuple)
    columns: int = 12
    gutter_mm: float = 4.0
    kind: str = "plain"
    space_before_mm: float | None = None
    space_after_mm: float | None = None
    #: The row's own padding, clockwise from top. A `.row` is a box in CSS
    #: and its padding insets what is inside it while its background paints
    #: to the border box -- which is why this is a field here rather than a
    #: container wrapped around the grid: a themed panel is drawn at the
    #: grid's outer edge and would move with the wrapper.
    padding_mm: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)



@dataclass(frozen=True, slots=True)
class HorizontalCell:
    blocks: Sequence["Block"] = field(default_factory=tuple)
    align: str | None = None
    #: Inline-block rows state their cell widths on the spans themselves.
    width_mm: float | None = None
    width_fraction: float | None = None
    #: CSS flex growth stays relative until the planner knows the row width.
    flex_grow: float = 0.0
    #: A `min-width` on the item. The box algorithm clamps the item's
    #: pass-one width to it before distributing growth, so an item can be
    #: wider than its content before anything flexes.
    min_width_mm: float | None = None
    #: The item's own horizontal margins. An inline-level item is separated
    #: from its neighbour by its own `margin-right` -- `.list-inline-item`
    #: states 0.5rem -- and that is a property of the item, not a uniform gap
    #: on the row: two items may state different margins, and borrowing
    #: `Paragraph.space_after` would put a vertical name on a horizontal fact.
    margin_left_mm: float = 0.0
    margin_right_mm: float = 0.0


@dataclass(frozen=True, slots=True)
class Horizontal:
    cells: Sequence[HorizontalCell] = field(default_factory=tuple)
    gap_mm: float = 4.0
    #: ``flex-wrap: wrap``. A wrapping row can put every item on a line of
    #: its own, so its minimum width is its widest item rather than the sum
    #: of them -- which is what CSS says and what decides whether a document
    #: overflows its paper. Bootstrap's `.row` wraps; a bare `display:flex`
    #: does not.
    wraps: bool = False
    #: The row's cross-axis alignment. `center` is authored on the standard
    #: header, where a one-line tagline sits beside a much taller logo.
    align_items: str | None = None
    #: `-webkit-box-pack`: how a legacy box distributes the space its
    #: children do not fill. `justify` is Bootstrap's `space-between`,
    #: reached through the legacy property accepted by the bounded Odoo 19
    #: compatibility profile. The accepted vocabulary is generated and
    #: checked by `tools/derive_layout_rules.py`.
    pack: str | None = None
    #: Whether this row is an inline formatting context rather than a flex
    #: row. The parser knows which it built -- a run of inline-level siblings
    #: coalesced onto a line box, against a `display: -webkit-box` row -- and
    #: the distinction decides whether `text-align` may move it. It moves a
    #: line box and it does not move a box child, so conflating the two would
    #: shift every flex row that happens to sit in a `.text-end`.
    inline_run: bool = False
    #: The inherited `text-align` in force on this row, when it is a line box.
    #: `None` on a flex row, and the planner never reads it there.
    align: str | None = None
    space_before_mm: float | None = None
    space_after_mm: float | None = None
    rule_above_pt: float = 0.0


@dataclass(frozen=True, slots=True)
class Border:
    """One explicitly declared edge of a normal-flow element."""

    width_pt: float = 0.0
    colour: tuple[float, float, float] | None = None
    style: str = "none"


@dataclass(frozen=True, slots=True)
class Container:
    children: Sequence["Block"] = field(default_factory=tuple)
    #: The evaluated HTML body's box is also the root of a page fragment.
    #: It may carry horizontal padding while the first child's positive top
    #: margin still adjoins the fragment edge. Ordinary nested containers do
    #: not inherit that page-edge behavior.
    fragment_root: bool = False
    #: An inline-block establishes its own formatting context, so its outer
    #: margin does not adjoin (and disappear at) a page-fragment root. Keep
    #: this structural display fact instead of naming the badge that exposed
    #: the difference.
    preserve_fragment_leading_margin: bool = False
    #: Whether this box is inline-level in its parent. Consecutive
    #: inline-level siblings share one line box; a lone one is placed as the
    #: ordinary container it already was.
    inline_level: bool = False
    #: A generated trailing clearance belongs to this formatting structure
    #: even though it has no visible paint of its own.  Bootstrap's
    #: ``.clearfix::after`` emits ``display:block; clear:both``; consequently
    #: the last real child's bottom margin cannot collapse through this box.
    #: Keep that source fact in IR rather than guessing from the final box
    #: height in the planner.
    contains_trailing_clearance: bool = False
    #: This box was a direct child of a flex formatting context
    #: (`-webkit-box`/`-webkit-inline-box`) that vanished as a transparent
    #: wrapper -- Bootstrap's `.row` has no width, height, padding or border
    #: of its own, so it never becomes a `Container`; this child was inserted
    #: straight into the flex row's own parent instead.
    #:
    #: A trailing descendant margin can collapse through this box. Legacy
    #: flex placement does not spend that escaped value, while normal block
    #: placement does; the parser records which contract applies.
    discard_escaping_trailing_margin: bool = False
    #: `opacity: 0` resolved to exactly zero on this element. CSS makes
    #: opacity a paint/compositing property, not a layout one: unlike
    #: `display: none`, the element keeps its whole box -- width, height,
    #: padding, border, margin, and everything a descendant would otherwise
    #: paint -- in the flow. Only paint is gone: text, images, rules and
    #: fills, generated content, page markers, all of it, from this element
    #: and everything under it, however deep, regardless of a descendant's
    #: own opacity (compositing is not escapable from inside: CSS renders
    #: the whole subtree to one buffer and then multiplies it by this
    #: element's own alpha).
    #:
    #: `opacity-0` used to mean `self._vanish_depth = 1` in the parser --
    #: the same subtree-removal `display: none` uses -- which is a different
    #: CSS mechanism entirely, and dropped the element's own margin along
    #: with its (correctly invisible) content. Odoo's Folder layout repeats
    #: the document title as exactly this: a hidden `<h3 class="opacity-0"
    #: style="height: 0px">`, whose own `margin-bottom: 0.75rem` still
    #: separates it from what follows it in the real render. Not partial
    #: opacity: this engine does not implement alpha compositing, and a
    #: value strictly between 0 and 1 is recorded as a capability gap
    #: rather than approximated as either 0 or 1.
    paint_suppressed: bool = False
    #: CSS border-box dimensions. Percentages stay relative until planning.
    width_mm: float | None = None
    width_fraction: float | None = None
    height_mm: float | None = None
    height_fraction: float | None = None
    #: Clockwise from top, matching CSS shorthand expansion.
    padding_mm: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    border: tuple[Border, Border, Border, Border] = field(
        default_factory=lambda: (Border(), Border(), Border(), Border())
    )
    fill_rgb: tuple[float, float, float] | None = None
    #: A CSS background belongs to the box rather than to normal flow.  Keep
    #: its source declarations unresolved until planning, when both the
    #: container's final height and the image's intrinsic dimensions exist.
    background_image_src: str | None = None
    background_size: str = "auto"
    background_position: str = "0% 0%"
    background_repeat: str = "repeat"
    radius_mm: float = 0.0
    margin_start_mm: float = 0.0
    margin_end_mm: float = 0.0
    margin_start_auto: bool = False
    margin_end_auto: bool = False
    #: `float`, under its own CSS name and carrying its own CSS values,
    #: `left` and `right`. The side belongs on the box rather than on its
    #: children.
    float_side: str | None = None
    #: `clear`, likewise: `left`, `right` or `both`. The box's top edge is
    #: pushed down to the lowest margin-box bottom of the floats on those
    #: sides. Synthetic left/right/both controls live in
    #: `tests/test_float_clear.py`.
    clear: str | None = None
    #: Whether this box establishes a block formatting context, and so
    #: contains its own floats instead of letting them overhang.
    establishes_bfc: bool = False
    space_before_mm: float | None = None
    space_after_mm: float | None = None


@dataclass(frozen=True, slots=True)
class PageBreak:
    pass


Block = Paragraph | Image | Table | Grid | Horizontal | Container | PageBreak


@dataclass(frozen=True, slots=True)
class PageArtRow:
    """One fixed-height, nowrap row inside positioned page decoration.

    Folder's tab is the bounded case this IR exists for: one SVG grows into
    the space left by an intrinsic-width SVG and one intrinsic-width heading.
    Keeping the heading here is structural, not cosmetic -- the whole row is
    out of normal flow, so returning it to ``Document.header`` moves both the
    heading and every following header block.
    """

    #: Row top and height in CSS pixels, before the host's paper scale.
    top_px: float
    height_px: float
    #: The final flex item and its two source margins. A layout may leave the
    #: item's text out while still reserving its width --
    #: `web.external_layout_folder` writes its heading as `w-25` when the
    #: report authors no `document_title` -- so the paragraph is optional and
    #: the width it reserves is carried separately.
    trailing: Paragraph | None
    trailing_margin_top_mm: float = 0.0
    trailing_margin_end_mm: float = 0.0
    #: The trailing item's declared width as a fraction of the row, when it
    #: states one. `.w-25{width: 25% !important}`; without it the item is as
    #: wide as its text.
    trailing_width_fraction: float | None = None


@dataclass(frozen=True, slots=True)
class PageArt:
    """An out-of-flow SVG from a layout's header or footer.

    Some layouts spell a dimension through a QWeb variable such as
    ``header_shape_height``.  That is source structure, not runtime-only
    geometry: the QWeb host reads its resolved value from evaluated HTML,
    while the record host reads the same authored layout branch.  This keeps
    either result in the SVG's own user units until the paper is known.
    """

    #: `("m"|"l"|"c"|"z", *coords)` in the SVG's user units.
    segments: tuple = ()
    #: `viewBox` extent; the user-unit space `segments` live in.
    view_w: float = 0.0
    view_h: float = 0.0
    #: The rendered box, in CSS pixels. Width is the page when `w-100`.
    height_px: float = 0.0
    full_width: bool = True
    #: Intrinsic width for an item in :class:`PageArtRow`; ``None`` is the
    #: width left for a flex-grow item. Ordinary full-page art uses neither.
    box_width_px: float | None = None
    flex_grow: float = 0.0
    row: PageArtRow | None = None
    #: Which edge the box is pinned to: the page top, or the footer band.
    anchor: str = "top"
    #: Insets of the positioned SVG box, in CSS pixels.  They come from the
    #: computed CSS of the SVG itself; ``right`` is kept relative until the
    #: planner knows the paper width.
    top_px: float | None = None
    left_px: float | None = None
    right_px: float | None = None
    fill: str | None = None
    fill_opacity: float = 1.0


@dataclass(frozen=True, slots=True)
class Document:
    body: Sequence[Block] = field(default_factory=tuple)
    header: Sequence[Block] = field(default_factory=tuple)
    footer: Sequence[Block] = field(default_factory=tuple)
    layout: str | None = None
    #: The external layout this document *declares*, as opposed to the one it
    #: was rendered under. Odoo writes `o_report_layout_<name>` on the article
    #: when an external layout applies, and writes nothing when none does --
    #: `layout_applicability` in a run's evidence is the same fact seen from
    #: the host's side. `None` therefore means "no external layout applies to
    #: this document", which is not the same as "the caller did not say which
    #: one to use".
    layout_class: str | None = None
    table_theme: str | None = None
    #: The `o_company_N_layout` class Odoo stamps on the report body. Odoo
    #: generates a stylesheet per company keyed on exactly that selector, so
    #: dropping it loses every colour the company set.
    company_class: str | None = None
    #: Each prepared wkhtmltopdf region is an independent HTML document and
    #: can load a different stylesheet carrier.  Keep its inherited root
    #: paint per region rather than promoting one body's cascade to all three.
    body_text_rgb: tuple[float, float, float] | None = None
    header_text_rgb: tuple[float, float, float] | None = None
    footer_text_rgb: tuple[float, float, float] | None = None
    #: `position-fixed` SVG art found in the header or footer regions.
    page_art: Sequence[PageArt] = field(default_factory=tuple)
