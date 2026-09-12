"""Resolve constrained document structure into immutable physical pages.

The planner owns pagination.  Canvas never receives flow objects and never
makes a page-break decision.  This first native planner intentionally focuses
on the primitives needed by transactional business documents: paragraphs,
tables, explicit page breaks, and repeated table headers.
"""

from __future__ import annotations

import dataclasses
import logging
import math
import re
import unicodedata
from dataclasses import dataclass, replace

from docsubstrate.horizontal_geometry import (
    allocate_horizontal_widths,
    inline_alignment_offset,
    packed_offsets,
)
from docsubstrate.ir import (
    Container,
    Document,
    Grid,
    Horizontal,
    HorizontalCell,
    Image,
    LineBreak,
    PageBreak,
    PageNumber,
    Paragraph,
    Table,
    Text,
    TotalPages,
)
from docsubstrate.odoo_report_profile import (
    BLOCK_RULE_OPACITY,
    BLOCK_RULE_PT,
    BLOCK_RULE_RGB,
    BODY_TEXT_RGB,
    BORDER_DASH_MULTIPLIERS,
    DOCUMENT_TITLE_REM,
    FONT_SIZE_PT,
    HEADING_LINE_HEIGHT_RATIO,
    HEADING_SIZES_REM,
    LEGACY_TABLE_INNER_RGB,
    LEGACY_TABLE_OUTER_RGB,
    LINE_HEIGHT_MM,
    LINE_HEIGHT_RATIO,
    LINK_COLOUR,
    PX_PER_INCH,
    TABLE_CELL_PAD_MM,
    TABLE_SM_PAD_RATIO,
)
from docsubstrate.odoo_report_theme import Fill, ReportTheme, TableSkin, rgb
from docsubstrate.pageplan import ImageRef, Line, PagePlan, Rect, ResolvedDocument, TextRun
from docsubstrate.render_baseline import collapse_margins, matches_oracle
from docsubstrate.renderers.base import UnsupportedDocumentFeature
from docsubstrate.renderers.reportlab_canvas import registered_font_set, registered_text_font
from docsubstrate.table_layout import (
    ColumnDemand,
    SpanningDemand,
    apply_spanning_demands,
    demand_for,
    distribute,
    table_column_placements,
)

_logger = logging.getLogger(__name__)


def _fill_parts(fill):
    """Return renderer RGB/alpha for a generated or authored table fill."""
    if isinstance(fill, Fill):
        return fill.rgb, fill.alpha
    return fill, 1.0

_CSS_LENGTH = re.compile(
    r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))(px|rem|em|mm|cm|in|pt|pc|q)?$",
    re.IGNORECASE,
)
_CSS_VAR = re.compile(r"var\(\s*(--[\w-]+)(?:\s*,\s*([^()]+))?\s*\)", re.IGNORECASE)


def _resolved_css_value(value: str, properties: dict[str, str]) -> str | None:
    """Resolve a bounded custom-property chain or report it as unavailable."""
    current = value.strip()
    for _ in range(16):
        match = _CSS_VAR.search(current)
        if match is None:
            return current
        replacement = properties.get(match.group(1))
        if replacement is None:
            replacement = match.group(2)
        if replacement is None:
            return None
        current = current[: match.start()] + replacement.strip() + current[match.end() :]
    return None


def _css_length_px(value: str | None, properties: dict[str, str] | None = None) -> float | None:
    """Read one absolute or font-relative CSS length as reference pixels."""
    if value is None:
        return None
    resolved = _resolved_css_value(value, properties or {})
    if resolved is None or "calc(" in resolved.lower() or resolved.endswith("%"):
        return None
    match = _CSS_LENGTH.fullmatch(resolved.strip())
    if match is None:
        return None
    number = float(match.group(1))
    unit = (match.group(2) or "px").lower()
    scale = {
        "px": 1.0,
        "rem": 16.0,
        "em": 16.0,
        "mm": 96.0 / 25.4,
        "cm": 96.0 / 2.54,
        "in": 96.0,
        "pt": 96.0 / 72.0,
        "pc": 16.0,
        "q": 96.0 / 101.6,
    }[unit]
    result = number * scale
    return result if math.isfinite(result) else None


def _css_colour_alpha(
    value: str | None,
) -> tuple[tuple[float, float, float], float] | None:
    """Read the numeric colour forms used by compiled table paint."""
    text = (value or "").strip().lower()
    if text == "transparent":
        return (0.0, 0.0, 0.0), 0.0
    if text.startswith("#"):
        digits = text[1:]
        if len(digits) == 3:
            digits = "".join(char * 2 for char in digits)
        if len(digits) in {6, 8}:
            try:
                colour = tuple(
                    int(digits[index : index + 2], 16) / 255.0 for index in (0, 2, 4)
                )
                alpha = int(digits[6:8], 16) / 255.0 if len(digits) == 8 else 1.0
                return colour, alpha
            except ValueError:
                return None
    match = re.fullmatch(
        r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)"
        r"(?:\s*,\s*([\d.]+))?\s*\)",
        text,
    )
    if match:
        channels = tuple(float(match.group(index)) for index in (1, 2, 3))
        alpha = float(match.group(4)) if match.group(4) is not None else 1.0
        if all(0.0 <= channel <= 255.0 for channel in channels) and 0.0 <= alpha <= 1.0:
            return tuple(channel / 255.0 for channel in channels), alpha
    return None


def _css_rgb(value: str | None) -> tuple[float, float, float] | None:
    parsed = _css_colour_alpha(value)
    return parsed[0] if parsed else None


def _compiled_inset_fill(
    declarations,
) -> tuple[tuple[float, float, float], float] | None:
    properties = dict(declarations)
    value = _resolved_css_value(properties.get("box-shadow", ""), properties)
    prefix = "inset 0 0 0 9999px "
    if value is None or not value.lower().startswith(prefix):
        return None
    return _css_colour_alpha(value[len(prefix) :])


def _compiled_css_edge(
    declarations, side: str, *, px_per_inch: float
) -> tuple[float, tuple[float, float, float]] | None:
    """Return the visible width and colour of one compiled table edge."""
    properties = dict(declarations)
    style_value = _resolved_css_value(
        properties.get(f"border-{side}-style", "none"), properties
    )
    if style_value is None or style_value.lower() in {"none", "hidden"}:
        return None
    width_value = properties.get(f"border-{side}-width")
    width = 3.0 if width_value is None else _css_length_px(width_value, properties)
    if width is None or width <= 0.0:
        return None
    colour_value = _resolved_css_value(
        properties.get(f"border-{side}-color", ""), properties
    )
    if colour_value is not None and colour_value.lower() == "currentcolor":
        colour_value = _resolved_css_value(properties.get("color", ""), properties)
    colour = _css_rgb(colour_value) or _css_rgb(properties.get("color")) or (0.0, 0.0, 0.0)
    return width * 72.0 / px_per_inch, colour


#: Headings that carry the document's identity, and so its colour.
_TITLE_ROLES = frozenset({"document-title", "document-number", "h1", "h2", "h3", "h4"})
_SEMANTIC_TITLE_ROLES = frozenset({"document-title", "document-number"})

#: Heading sizes are multiples of the document root, so shrink-to-fit scales
#: the root and every heading together.
_HEADING_SIZES_REM = dict(HEADING_SIZES_REM)
_HEADING_SIZES_REM["document-title"] = DOCUMENT_TITLE_REM
_HEADING_SIZES_REM["document-number"] = DOCUMENT_TITLE_REM


@dataclass(frozen=True, slots=True)
class PagePolicy:
    width_mm: float = 210.0
    height_mm: float = 297.0
    margin_left_mm: float = 15.0
    margin_right_mm: float = 15.0
    margin_top_mm: float = 15.0
    margin_bottom_mm: float = 15.0
    #: Header/footer inset from the page edge. ``None`` uses the default band
    #: placement contract.
    band_inset_mm: float | None = None
    font_name: str | None = None
    #: Path to a Latin text face. Odoo renders reports in Lato and ships it
    #: with its web addon; matching it is most of the width fidelity, because
    #: Han advances already agree across CJK faces and Latin ones do not.
    latin_font_path: str | None = None
    #: The host's answer to "what font files can you serve from where this
    #: URL points". Absent for every caller that has no host, and then a
    #: declared family simply does not resolve and the script rule stands.
    font_assets: object | None = None
    font_size_pt: float = FONT_SIZE_PT
    line_height_mm: float = LINE_HEIGHT_MM
    block_gap_mm: float = 2.0
    table_cell_pad_mm: float = TABLE_CELL_PAD_MM
    #: Effective CSS pixel density selected by the print profile.
    css_px_per_inch: float = PX_PER_INCH
    #: Host-supplied access origin for relative Odoo report image routes.
    #: The adapter obtains it from ``ir.actions.report._get_report_url()``;
    #: the engine never guesses from a browser-facing hostname.
    image_base_url: str | None = None
    #: Odoo sends named paper and custom dimensions as distinct paperformat
    #: inputs. Preserve both until the page box is written.
    paper_format: str = "A4"
    dpi: int = 90


def _inherit_align(blocks, align):
    """Push a container's `text-align` down onto the blocks that don't set one.

    `text-align` inherits in CSS, but the IR records it per block, so a
    `<div class="w-50 text-end">` that becomes a `HorizontalCell` keeps the
    alignment on the cell while the paragraphs inside it still say `None`.
    The planner drew those at the cell's left edge -- which is why the header
    company address came out left-aligned inside a right-aligned box, up to
    71mm from where wkhtmltopdf puts it.

    Only `None` is filled in: a block that states its own alignment has
    overridden the inherited one, exactly as the cascade would.

    A line box takes it too. `text-align` aligns a run of inline-level
    siblings. A flex row is not a line box and is left alone.
    """
    if not align:
        return blocks
    out = []
    for block in blocks:
        if isinstance(block, Paragraph) and block.align is None:
            out.append(replace(block, align=align))
        elif isinstance(block, Container):
            out.append(replace(block, children=_inherit_align(block.children, align)))
        elif isinstance(block, Horizontal) and block.inline_run and block.align is None:
            out.append(replace(block, align=align))
        else:
            out.append(block)
    return tuple(out)


def _inherit_cell_style(blocks, cell):
    """Carry inherited cell text properties into its child block flow.

    A table cell is a containing block, not a string join.  Once it contains
    more than one block, each Paragraph is flowed independently; inherited
    CSS still comes from the cell.  Literal declarations on the Paragraph
    remain more specific.  Containers recurse because inheritance crosses a
    transparent wrapper, while nested tables keep the styles already parsed
    on their own cells.
    """
    colour_role = cell.colour_role
    styled = []
    for block in blocks:
        if isinstance(block, Paragraph):
            block_owns_line_height = (
                block.line_height_ratio is not None
                or block.line_height_mm is not None
            )
            styled.append(replace(
                block,
                align=block.align or cell.align,
                role=block.role or cell.role,
                colour_role=block.colour_role or colour_role,
                font_size_pt=block.font_size_pt or cell.font_size_pt,
                line_height_ratio=(
                    block.line_height_ratio
                    if block_owns_line_height else cell.line_height_ratio
                ),
                line_height_mm=(
                    block.line_height_mm if block_owns_line_height
                    else cell.line_height_mm
                ),
            ))
        elif isinstance(block, Container):
            styled.append(replace(
                block, children=_inherit_cell_style(block.children, cell)
            ))
        elif isinstance(block, Image) and block.space_after_mm is None:
            # Images have no UA bottom margin. The old cell image path placed
            # the following text directly after the image; entering the block
            # flow must not invent PagePolicy.block_gap_mm merely because the
            # IR left that zero implicit.
            styled.append(replace(block, space_after_mm=0.0))
        else:
            styled.append(block)
    return tuple(styled)


def _is_self_collapsing(block) -> bool:
    """Whether this box contributes no height of its own.

    The bounded synthetic contract in `tests/test_float_clear.py` requires:
    not a table, no border or padding in the block direction, no stated height, and
    every in-flow child self-collapsing too -- which is vacuously true of a
    box with no children, and that is the shape a generated `content: ""`
    takes.

    A fill or a background is deliberately not consulted. Paint does not give
    a box height, and asking about it here would make a coloured empty div
    behave differently from a transparent one for no reason CSS states.
    """
    if not isinstance(block, Container):
        return False
    if block.height_mm is not None or block.height_fraction is not None:
        return False
    if any(block.padding_mm):
        return False
    if any(edge.width_pt for edge in block.border):
        return False
    return all(_is_self_collapsing(child) for child in block.children)


#: A box's four paddings, and the single rule that consumes them.
#:
#: It exists because the grid had two readers of the same four numbers and
#: they disagreed. The advance took `pad_top` and dropped `pad_bottom` -- it
#: was unpacked into `_pad_bottom` and thrown away -- so a row that gained a
#: padding got *shorter*, and the panel painted behind it started below its
#: own top edge. One object with `open`, `close` and `inset` leaves nowhere
#: for a second answer to grow.
@dataclass(frozen=True, slots=True)
class _PaddingBox:
    top: float
    right: float
    bottom: float
    left: float

    @classmethod
    def of(cls, padding) -> "_PaddingBox":
        """Clockwise from the top, matching CSS shorthand expansion."""
        top, right, bottom, left = padding
        return cls(top, right, bottom, left)

    def __bool__(self) -> bool:
        return bool(self.top or self.right or self.bottom or self.left)

    def inset(self, x: float, width: float) -> tuple[float, float]:
        """Content origin and width inside the border box."""
        if not (self.left or self.right):
            return x, width
        return x + self.left, max(1.0, width - self.left - self.right)

    def open(self, y: float) -> float:
        """Where this box's content begins, below its top padding."""
        return y - self.top

    def close(self, y: float) -> float:
        """Where this box's border box ends, below its bottom padding.

        Applied after the flow and exactly once, whatever the flow did in
        between. A box that paginates carries its bottom padding on its last
        fragment, and one that is empty is still `top + bottom` tall.
        """
        return y - self.bottom


#: Which float sides each `clear` value waits for. Synthetic left/right/both
#: cases in `tests/test_float_clear.py` fix this table; `none` is absent
#: because it clears nothing.
_CLEAR_SIDES = {
    "left": ("left",),
    "right": ("right",),
    "both": ("left", "right"),
}


#: A float, as one block formatting context sees it: a margin box in page
#: millimetres, where a larger number is higher up the page.
@dataclass(frozen=True, slots=True)
class _FloatBox:
    side: str
    top_mm: float
    bottom_mm: float
    left_mm: float
    right_mm: float


class _FloatContext:
    """The floats of one block formatting context.

    A float context is shared by boxes in one formatting context: a float is
    added where it is placed, and every box in the same
    context -- however deeply nested -- sees it. Nothing here is scoped by
    element, class or report.
    """

    __slots__ = ("boxes",)

    def __init__(self):
        self.boxes: list[_FloatBox] = []

    #: The maximum of the placed floats' *margin* box bottoms, so a float's
    #: own `margin-bottom` is inside what a `clear` clears to.
    def lowest_bottom(self, sides) -> float | None:
        bottoms = [b.bottom_mm for b in self.boxes if b.side in sides]
        return min(bottoms) if bottoms else None

    def insets(self, y: float, box_x: float, width: float) -> tuple[float, float]:
        """How far the left and right edges are pushed in at height `y`.

        Active floats contribute their innermost edge. In CSS coordinates a float
        spans `[y, maxY)`; these run upward, so the same half-open interval
        is `bottom < y <= top`.
        """
        left, right = box_x, box_x + width
        for box in self.boxes:
            if not (box.bottom_mm < y <= box.top_mm):
                continue
            if box.side == "left":
                left = max(left, box.right_mm)
            else:
                right = min(right, box.left_mm)
        return max(0.0, left - box_x), max(0.0, box_x + width - right)

    def next_bottom_below(self, y: float) -> float | None:
        """The highest float bottom that lies below `y`, or None.

        The step `positionNewFloats` takes when a float does not fit on the
        current line: `logicalTop += min(heightRemainingLeft,
        heightRemainingRight)`, which is the nearest float bottom.
        """
        below = [b.bottom_mm for b in self.boxes if b.bottom_mm < y]
        return max(below) if below else None


class PagePlanner:
    """Global pagination followed by page-local execution plans."""

    #: Fallback box for an image the document did not size.
    DEFAULT_IMAGE_WIDTH_MM = 40.0

    def __init__(self, policy: PagePolicy | None = None, theme: ReportTheme | None = None):
        self.policy = policy or PagePolicy()
        #: The layout the company picked; tables inherit their chrome from it.
        self.theme = theme or ReportTheme()
        self.font_name = self.policy.font_name or registered_text_font()
        #: One face per script. ReportLab has no fallback, so text is split
        #: before measurement and drawing.
        self.fonts = registered_font_set(
            self.policy.latin_font_path, self.policy.font_assets)
        if self.policy.font_name:
            # Replace, not rebuild: constructing a fresh one from two of its
            # three fields silently drops the declared faces, and a glyph at
            # a private-use codepoint then goes to the text face.
            self.fonts = dataclasses.replace(self.fonts, cjk=self.font_name)
        self._page_ctx = (1, 1)
        self._top_y = self.policy.height_mm - self.policy.margin_top_mm
        self._bottom_limit = self.policy.margin_bottom_mm
        #: True while flowing a header/footer band, which must never paginate.
        self._in_band = False
        self.warnings: list[str] = []
        self._image_validity: dict[str, bool] = {}
        self._resolved_images: dict[str, str] = {}
        self._image_fallback_warned: set[str] = set()
        self._measuring_intrinsic = False
        #: The margin the most recent `_flow` collapsed out of its scope.
        self._flow_trailing_mm = 0.0
        self._text_rgb = BODY_TEXT_RGB

    def _warn_once(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def _role_size_pt(self, role: str | None, default: float | None = None) -> float:
        """The size a semantic role is set at, off this page's root size.

        A role the stylesheet says nothing about falls back to `default`, and
        then to the body size -- which is the same answer as before, only now
        it is one place instead of five call sites repeating the lookup.
        """
        body = self.policy.font_size_pt
        rem = _HEADING_SIZES_REM.get(role or "")
        if rem is None:
            return default if default is not None else body
        return rem * body

    def _line_advance_mm(self, size_pt: float, ratio: float) -> float:
        """Resolve a CSS line box without changing the glyph size.

        wkhtmltopdf preserves a fractional point size (10pt is painted at
        10.2462pt under smart shrinking) but advances that line box by a
        whole CSS pixel.  Quantising the font would regress text_size; rounding
        the final y coordinate would also corrupt content-driven table rows.
        This boundary applies only to the line-height component.
        """
        advance = size_pt * ratio * 25.4 / 72.0
        if not matches_oracle("layout_advances_in_whole_pixels"):
            return advance
        pixels = advance * self.policy.css_px_per_inch / 25.4
        return math.floor(pixels + 0.5) * 25.4 / self.policy.css_px_per_inch

    def plan(self, document: Document) -> ResolvedDocument:
        self.warnings = []
        self._image_validity = {}
        self._resolved_images = {}
        self._image_fallback_warned = set()
        self._measuring_intrinsic = False
        self._text_rgb = document.body_text_rgb or BODY_TEXT_RGB
        p = self.policy
        width = p.width_mm - p.margin_left_mm - p.margin_right_mm

        # Odoo's paperformat margins are not blank space above the content --
        # they are the strips the header and footer are drawn into, which is
        # why an A4 report asks for 52mm at the top. So the body starts at the
        # page margin; reserving the band again would subtract it twice.
        self._top_y = p.height_mm - p.margin_top_mm
        self._bottom_limit = p.margin_bottom_mm
        self._warn_if_band_overflows(
            document.header, width, top=True, text_rgb=document.header_text_rgb,
        )
        self._warn_if_band_overflows(
            document.footer, width, top=False, text_rgb=document.footer_text_rgb,
        )

        pages: list[list] = [[]]
        y = self._top_y

        def new_page() -> None:
            nonlocal y
            pages.append([])
            y = self._top_y

        y = self._flow(
            document.body, p.margin_left_mm, y, width, pages, new_page,
            discard_positive_leading_margin=True,
            containing_height_mm=self._top_y - self._bottom_limit,
        )

        page_count = len(pages)
        resolved = []
        for index, commands in enumerate(pages, start=1):
            # Header/footer are structural projections repeated on every page.
            # Odoo builds them from the same layout vocabulary as the body --
            # the company block is a Grid and the logo an Image -- so they get
            # the same flow, only pinned to a band instead of paginated.
            decorated = []
            # Page art first, so everything else lands on top of it. The
            # template marks these `position-fixed`, which is why they repeat
            # on every page rather than flowing with the content.
            # Three states, and the document says which one it is in.
            #
            # Odoo writes `o_report_layout_<name>` on the article exactly when
            # an external layout applies, so `document.layout_class` is that
            # fact: it names the layout the document declares.
            #
            #   art present            -- draw it, whatever the caller said
            #   layout declared, no art -- an older host that captured no
            #                              structure; the compiled theme table
            #                              is the compatibility fallback
            #   no layout, or another   -- no external layout applies, so
            #                              there is nothing to decorate with
            #
            # The last case used to reach the fallback too, and painted a
            # layout's shapes onto documents that had never asked for them.
            if document.page_art:
                decorated.extend(self._page_art(document.page_art))
            elif document.layout_class == self.theme.layout:
                decorated.extend(
                    self.theme.page_shapes(p.width_mm, p.height_mm, p.margin_bottom_mm)
                )
            # Folder used a theme-derived rectangular approximation while
            # its actual out-of-flow SVG was unread. Once the document has
            # supplied page art, painting that approximation afterwards
            # would cover the vector geometry we just recovered.
            # The same three states. A band is decoration like any other.
            band = (
                self.theme.band_fill
                if not document.page_art
                and document.layout_class == self.theme.layout
                else None
            )
            header_commands = self._band(
                document.header, width, index, page_count, top=True,
                text_rgb=document.header_text_rgb,
            )
            if band and header_commands:
                # Folder/Wave/Bubble tint the whole strip behind the header.
                # The shape Odoo draws there is SVG art; this is the colour.
                lowest = min(getattr(cmd, "y_mm", p.height_mm) for cmd in header_commands)
                depth = max(0.0, p.height_mm - lowest + p.block_gap_mm)
                decorated.append(Rect(
                    0.0, p.height_mm - depth, p.width_mm, depth,
                    stroke=False, fill=True, fill_rgb=band,
                ))
            decorated.extend(header_commands)
            decorated.extend(commands)
            decorated.extend(self._band(
                document.footer, width, index, page_count, top=False,
                text_rgb=document.footer_text_rgb,
            ))
            resolved.append(PagePlan(
                p.width_mm,
                p.height_mm,
                tuple(decorated),
                paper_format=p.paper_format,
                dpi=p.dpi,
            ))

        return ResolvedDocument(tuple(resolved))

    def _page_art(self, arts) -> list:
        """Resolve `position-fixed` SVG art from the template onto the sheet.

        `preserveAspectRatio="none"` on every one of these, so the viewBox
        stretches to the rendered box independently in x and y -- which is
        the point: the art is a full-width band whose height the template
        chooses. Anything else would letterbox it.
        """
        from docsubstrate.pageplan import Path
        from docsubstrate.svg_path import transform_path

        p = self.policy
        drawn = []
        completed_rows = set()
        for art in arts:
            if art.row is not None:
                identity = id(art.row)
                if identity in completed_rows:
                    continue
                completed_rows.add(identity)
                members = [candidate for candidate in arts if candidate.row is art.row]
                drawn.extend(self._page_art_row(art.row, members))
                continue
            if not art.segments or not art.view_w or not art.view_h:
                continue
            box_w = (
                p.width_mm if art.full_width
                else art.view_w * 25.4 / p.css_px_per_inch
            )
            box_h = art.height_px * 25.4 / p.css_px_per_inch
            mm_per_px = 25.4 / p.css_px_per_inch
            if art.left_px is not None:
                offset_x = art.left_px * mm_per_px
            elif art.right_px is not None:
                offset_x = p.width_mm - art.right_px * mm_per_px - box_w
            else:
                offset_x = 0.0
            # `top-0` pins the box to the page. The footer's art states no
            # edge, so it comes to rest at its static position: the top of
            # the band the paperformat reserved, which is where wkhtmltopdf
            # starts the footer document.
            offset_y = (
                art.top_px * mm_per_px
                if art.top_px is not None
                else (0.0 if art.anchor == "top" else p.height_mm - p.margin_bottom_mm)
            )
            segments = transform_path(
                art.segments,
                scale_x=box_w / art.view_w,
                scale_y=box_h / art.view_h,
                offset_x=offset_x,
                offset_y=offset_y,
                height_mm=p.height_mm,
            )
            art_rgb, art_alpha = self._art_fill(art)
            drawn.append(Path(tuple(segments), fill_rgb=art_rgb, fill_alpha=art_alpha))
        return drawn

    def _page_art_row(self, row, arts) -> list:
        """Resolve one bounded out-of-flow flex row from source dimensions.

        one or more intrinsic-width SVGs, exactly one grow SVG, and one nowrap
        Paragraph.  Their source order is preserved; the grow item receives
        the width left after the planner measures the real title font.
        """
        from docsubstrate.pageplan import Path
        from docsubstrate.svg_path import transform_path

        p = self.policy
        mm_per_px = 25.4 / p.css_px_per_inch
        if row.trailing_width_fraction is not None:
            # The trailing item states its width, so the shapes divide what
            # is left of the row rather than what is left of its text.
            # The Folder template writes a quarter-width heading when
            # the report authors no title, and the matching utility
            # reserves that quarter whether or not anything is written in it.
            title_width = p.width_mm * row.trailing_width_fraction
        elif row.trailing is None:
            title_width = 0.0
        else:
            runs = self._paragraph_runs(row.trailing)
            if any(text == "\n" for text, *_rest in runs):
                self._warn_once("page art row heading is not nowrap; row not drawn")
                return []
            size_pt = row.trailing.font_size_pt or self._role_size_pt(row.trailing.role)
            title_width = self._line_width_mm(
                runs, size_pt,
                letter_spacing_mm=row.trailing.letter_spacing_mm,
            )
        fixed_width = sum(
            (art.box_width_px or 0.0) * mm_per_px
            for art in arts if art.flex_grow <= 0
        )
        grow_total = sum(max(0.0, art.flex_grow) for art in arts)
        available = (
            p.width_mm - fixed_width - title_width
            - row.trailing_margin_end_mm
        )
        if grow_total <= 0 or available < 0:
            self._warn_once(
                "page art row does not fit its positioned containing block; row not drawn"
            )
            return []

        row_top = row.top_px * mm_per_px
        row_height = row.height_px * mm_per_px
        cursor = 0.0
        drawn = []
        for art in arts:
            if not art.segments or not art.view_w or not art.view_h:
                continue
            box_w = (
                available * art.flex_grow / grow_total
                if art.flex_grow > 0
                else float(art.box_width_px) * mm_per_px
            )
            segments = transform_path(
                art.segments,
                scale_x=box_w / art.view_w,
                scale_y=row_height / art.view_h,
                offset_x=cursor,
                offset_y=row_top,
                height_mm=p.height_mm,
            )
            art_rgb, art_alpha = self._art_fill(art)
            drawn.append(Path(tuple(segments), fill_rgb=art_rgb, fill_alpha=art_alpha))
            cursor += box_w

        # The heading is the last flex item, not ordinary header flow. Reuse
        # the paragraph painter so its script-specific font metrics, baseline,
        # company colour and run styling cannot diverge from normal headings.
        if row.trailing is None:
            return drawn
        was_in_band = self._in_band
        self._in_band = True
        try:
            self._place_paragraph(
                row.trailing,
                cursor,
                p.height_mm - row_top - row.trailing_margin_top_mm,
                max(0.1, title_width),
                [drawn],
                lambda: None,
            )
        finally:
            self._in_band = was_in_band
        return drawn

    def _art_fill(self, art):
        """The path's colour and true alpha.

        Wave, Bubble and the like draw these at `fill-opacity=".1"`. A
        pre-flattened opaque colour happens to paint identically for a shape
        sitting alone on white paper, but stops being correct the moment
        anything else -- an overlapping shape, a raster background -- shares
        its backdrop; carrying real alpha through to the renderer costs
        nothing when the backdrop really is blank paper and is required when
        it is not.
        """
        if not art.fill:
            # Folder's generated company stylesheet supplies the rect/path
            # fill through `.o_folder_header_container`; it is not repeated
            # as an SVG attribute in the evaluated HTML. ReportTheme already
            # resolves that authoritative rule to the 92%-white primary tint.
            # Outside that rule, SVG's default fill is black.
            return self.theme.band_fill or (0.0, 0.0, 0.0), 1.0
        base = rgb(art.fill, "#000000")
        return base, max(0.0, min(1.0, art.fill_opacity))

    @staticmethod
    def _flatten_on_white(colour, opacity):
        """Resolve alpha against the white paper both kinds of art sit on."""
        alpha = max(0.0, min(1.0, opacity))
        return tuple(1.0 - (1.0 - channel) * alpha for channel in colour)

    def _band_content(self, blocks, *, top: bool):
        """Drop the page art from a header or footer band.

        Odoo draws each layout's shape as an SVG inside the header or footer,
        and some layouts give it no class at all -- Bubble's is a bare
        500x228px `<svg>` -- so it cannot be recognised by name. What does
        distinguish it is size: a graphic taller than the strip the
        paperformat reserved for that band is not content in the band, it is
        the band's background. Laying it out as content pushes the real
        footer, and its page number, up into the document body.
        """
        p = self.policy
        allowed = p.margin_top_mm if top else p.margin_bottom_mm
        kept = []
        for block in blocks:
            height = getattr(block, "height_mm", None)
            if isinstance(block, Image) and height and height > allowed:
                _logger.debug(
                    "dropping %.0fmm band graphic; the %s strip is %.0fmm",
                    height, "header" if top else "footer", allowed,
                )
                continue
            kept.append(block)
        return kept

    def _warn_if_band_overflows(
        self, blocks, width: float, *, top: bool,
        text_rgb: tuple[float, float, float] | None = None,
    ) -> None:
        """Say so when a band does not fit the strip the paperformat gave it.

        Growing the reservation instead would hide a header that is too tall
        by eating the body's page, so this reports and carries on.
        """
        claimed = self._band_height(
            self._band_content(blocks, top=top), width, top=top,
            text_rgb=text_rgb,
        )
        p = self.policy
        allowed = p.margin_top_mm if top else p.margin_bottom_mm
        if claimed > allowed:
            _logger.warning(
                "%s band needs %.1fmm but the paperformat reserves %.1fmm; it will "
                "overlap the body",
                "header" if top else "footer", claimed, allowed,
            )

    def _band_height(
        self, blocks, width: float, *, top: bool,
        text_rgb: tuple[float, float, float] | None = None,
    ) -> float:
        """Vertical space a repeated band claims, plus a gap off the content."""
        if not blocks:
            return 0.0
        p = self.policy
        commands = self._band(
            blocks, width, 1, 1, top=top, text_rgb=text_rgb,
        )
        if not commands:
            return 0.0
        lowest = min(getattr(cmd, "y_mm", p.height_mm) for cmd in commands)
        highest = max(getattr(cmd, "y_mm", 0.0) for cmd in commands)
        if top:
            claimed = (p.height_mm - p.margin_top_mm) - lowest
        else:
            claimed = highest - p.margin_bottom_mm
        return max(0.0, claimed) + p.block_gap_mm

    def _band(
        self, blocks, width: float, page: int, total: int, *, top: bool,
        text_rgb: tuple[float, float, float] | None = None,
    ) -> list:
        """Lay out a header or footer as a band that never paginates.

        the bottom margin: its height is only known once its blocks are flowed.
        """
        if not blocks:
            return []
        p = self.policy
        blocks = self._band_content(blocks, top=top)
        if not blocks:
            return []
        previous = self._page_ctx
        was_in_band = self._in_band
        previous_text_rgb = self._text_rgb
        self._page_ctx = (page, total)
        self._in_band = True
        self._text_rgb = text_rgb or BODY_TEXT_RGB
        try:
            def measure(start_y):
                scratch: list[list] = [[]]
                # A band is already the projected header/footer document,
                # not a paginated body fragment.  Its first spacing can be
                # real padding: every Odoo footer starts with
                # `.o_footer_content.pt-5` (3rem).  Discarding that value as
                # though it were a fragment-adjoining margin lifts the whole
                # footer by exactly 10.837mm.
                end = self._flow(
                    blocks, p.margin_left_mm, start_y, width, scratch, lambda: None,
                )
                return [cmd for page_commands in scratch for cmd in page_commands], end

            if top:
                inset = p.band_inset_mm if p.band_inset_mm is not None else max(3.0, p.margin_top_mm / 2)
                commands, _ = measure(p.height_mm - inset)
                return commands
            # wkhtmltopdf renders the footer document into the bottom margin
            # strip starting at the *top* of that strip; the footer's own
            # `pt-5` -- 3rem, 10.84mm -- is what pushes its text down inside
            # it. Bottom-anchoring the band was an invented rule, and it also
            # made that padding inert: pushing from the top moves nothing when
            # the bottom is pinned. `band_inset_mm` still governs the header,
            # whose markup carries no padding of its own.
            return measure(p.margin_bottom_mm)[0]
        finally:
            self._page_ctx = previous
            self._in_band = was_in_band
            self._text_rgb = previous_text_rgb

    def _flow(
        self, blocks, box_x: float, y: float, width: float,
        pages: list[list], new_page, *,
        discard_positive_leading_margin: bool = False,
        containing_height_mm: float | None = None,
        inherited_align: str | None = None,
        floats: "_FloatContext | None" = None,
    ) -> float:
        p = self.policy
        #: The trailing margin of the previous block, held so it can collapse
        #: against the next one's leading margin instead of adding to it.
        pending_gap = 0.0
        # A formatting context is inherited when the caller has one, and made
        # here when it does not. Owning it is the same question as enclosing
        # the floats in it. The bounded contract is true for a table cell, an
        # inline-block, an overflow clip, a float and the root -- the boxes
        # that establish a context -- and false for an ordinary `div`, which
        owns_context = floats is None
        if floats is None:
            floats = _FloatContext()
        at_fragment_top = discard_positive_leading_margin
        remaining = list(blocks)
        for index, block in enumerate(remaining):
            if isinstance(block, PageBreak):
                new_page()
                y = p.height_mm - p.margin_top_mm
                at_fragment_top = discard_positive_leading_margin
                continue

            # Adjacent margins collapse: the gap between two blocks is the
            # larger of the facing margins, not their sum, and a negative one
            # is added to it. Summing them opened a 3.6mm gap between the
            # line table and the totals band that closes to zero in the
            # source document, where `.table`'s 1rem meets `.row.mt-n3`.
            side = getattr(block, "float_side", None)
            if side:
                leading = block.space_before_mm or 0.0
                if at_fragment_top and leading > 0:
                    leading = 0.0
                self._place_float(
                    block, side, box_x, y - collapse_margins(pending_gap, leading),
                    width, pages, new_page, floats,
                )
                # A float is removed from normal flow.  In particular it does
                # not consume the line table's pending bottom margin; the
                # following payment terms still collapse against that margin.
                at_fragment_top = False
                continue

            fragment_top_for_block = at_fragment_top
            leading = block.space_before_mm
            # CSS Fragmentation discards a positive margin adjoining the top
            # of a page fragment.  wkhtmltopdf demonstrates the distinction
            # directly on the return document: +8px and +32px both move
            # nothing, -32px still pulls content up, and 32px padding moves it
            # down.  Nested cell/container flow does not opt into this rule.
            if (
                at_fragment_top and leading is not None and leading > 0
                and not (
                    isinstance(block, Container)
                    and block.preserve_fragment_leading_margin
                )
            ):
                leading = 0.0
            # Clearance applies after the margin, not instead of it: the
            # margin positions the box and the clearance then pushes that
            # position down to the lowest float bottom, or does nothing if it
            # is already below it.
            sides = _CLEAR_SIDES.get(getattr(block, "clear", None) or "none")
            cleared_to = floats.lowest_bottom(sides) if sides else None
            settled = y - collapse_margins(pending_gap, leading)

            if sides and _is_self_collapsing(block):
                at_bottom = all(
                    getattr(later, "float_side", None)
                    for later in remaining[index + 1:]
                )
                # contributes no height of its own is not a boundary in the
                # flow; what it does is hold clearance, and only when there is
                # clearance to hold.
                if cleared_to is None or cleared_to >= settled:
                    # `if (!heightIncrease) return yPos;` -- `:1703-1704`. No
                    # clearance, no height increase, and no boundary: the
                    # margin on either side of it goes on collapsing as
                    # though the box were not there. Treating it as a
                    # boundary anyway is what left a 24px margin inside the
                    # invoice article that CSS collapses out of it.
                    pending_gap = collapse_margins(
                        pending_gap, leading, block.space_after_mm
                    )
                    continue
                # Clearance applies. `setLogicalHeight(child->y() - max(0,
                # marginInfo.margin()))` -- `:1731`: the parent's height ends
                # at the cleared position less the margin that collapsed into
                # it, because that margin collapses on through this box
                # rather than being trapped above it.
                collapsed = max(0.0, collapse_margins(pending_gap, leading))
                y = cleared_to + collapsed
                # `:1720-1727`: what carries on collapsing is the box's *own*
                # margin, not the one that was consumed positioning it. At
                # the bottom of the block that is its after-margin alone; with
                # in-flow siblings still to come it is the larger of its two.
                own_after = block.space_after_mm or 0.0
                own_before = block.space_before_mm or 0.0
                pending_gap = own_after if at_bottom else max(own_before, own_after)
                at_fragment_top = False
                continue

            y = settled
            pending_gap = 0.0
            at_fragment_top = False
            if cleared_to is not None:
                y = min(y, cleared_to)

            # A float shortens the line boxes beside it. This engine narrows
            # the whole block rather than its lines, which is the behaviour
            # that shipped for the invoice's end float; what changes here is
            # that a left float now shifts the content origin as well, which
            # it could not before because `left` had no spelling.
            left_inset, right_inset = floats.insets(y, box_x, width)
            flow_x = box_x + left_inset
            flow_width = max(0.1, width - left_inset - right_inset)

            if isinstance(block, Paragraph):
                y = self._place_paragraph(block, flow_x, y, flow_width, pages, new_page)
            elif isinstance(block, Image):
                y = self._place_image(
                    block, flow_x, y, flow_width, pages, new_page,
                    align=inherited_align,
                )
            elif isinstance(block, Table):
                y = self._place_table(
                    block, pages, y, flow_width, new_page, box_x=flow_x,
                    containing_height_mm=containing_height_mm,
                )
            elif isinstance(block, Grid):
                y = self._place_grid(block, pages, y, flow_width, new_page, flow_x)
            elif isinstance(block, Horizontal):
                y = self._place_horizontal(block, pages, y, flow_width, new_page, flow_x)
            elif isinstance(block, Container):
                y = self._place_container(
                    block, flow_x, y, flow_width, pages, new_page,
                    discard_positive_leading_margin=(
                        fragment_top_for_block and block.fragment_root
                    ),
                    containing_height_mm=containing_height_mm,
                    floats=None if block.establishes_bfc else floats,
                )
                if block.discard_escaping_trailing_margin:
                    # This box was a flex item of a `.row` that vanished as
                    # a transparent wrapper. `_place_container` just baked
                    # its own descendant's collapsed-through trailing margin
                    # into `y`, the way an ordinary block would let it keep
                    # collapsing outward -- but `RenderFlexibleBox` never
                    # reads a flex item's `collapsedMarginAfter()`, only its
                    # plain declared margin, so that escape never happens in
                    # the source at all. Undo exactly the amount this box's
                    # own flow just subtracted; `block.space_after_mm` below
                    # still carries this box's *own* declared margin, which
                    # a flex container's sizing does still add.
                    y += self._flow_trailing_mm
            else:
                raise UnsupportedDocumentFeature(
                    f"paginated planner does not support {type(block).__name__} yet"
                )

            trailing = block.space_after_mm
            pending_gap = p.block_gap_mm if trailing is None else trailing
        # What this scope's last margin collapsed out to. `_place_container`
        # paints to the border box, which excludes it (CSS 2.2 section 8.3.1),
        # and it used to re-derive the value from `children[-1]`. That reads
        # the IR where the flow knows the answer: a self-collapsing generated
        # box at the end states a zero margin of its own and hid the real one
        # behind it, which is how a background box grew by 24px without any
        # text moving.
        self._flow_trailing_mm = collapse_margins(pending_gap)
        y -= self._flow_trailing_mm
        if owns_context:
            # A box that establishes a context grows to the lowest float
            # bottom. A box that does not is left
            # exactly where its own flow ended, and the floats hang out of it
            # from its `.clearfix::after`.
            lowest = floats.lowest_bottom(("left", "right"))
            if lowest is not None:
                y = min(y, lowest)
        return y

    def _place_float(
        self, block, side: str, box_x: float, top: float, width: float,
        pages, new_page, floats: "_FloatContext",
    ) -> None:
        """Place one float and add it to the formatting context.

        The synthetic contract makes the float take its own margin-box width,
        cap it to the available
        content width, and is then pushed down a line at a time until that
        width fits between the floats already placed. Which is the whole of
        "two floats sit side by side unless the second does not fit".
        """
        start = getattr(block, "margin_start_mm", 0.0)
        end = getattr(block, "margin_end_mm", 0.0)
        available = max(0.1, width - start - end)

        if isinstance(block, Image):
            # A replaced element already has a used width
            # shrink-to-fit path a `width: auto` block float would need is
            # not reached by this one.
            outer = self._image_dimensions(block, available)[0]
        elif block.width_mm is not None:
            outer = block.width_mm
        elif block.width_fraction is not None:
            outer = width * block.width_fraction
        else:
            # `width: auto` on a block float is shrink-to-fit, which needs the intrinsic
            # preferred widths this planner does not compute. Say so rather
            self._warn_once(
                "float has no stated width; shrink-to-fit is not implemented"
            )
            outer = available
        outer = max(0.0, min(outer, available))

        # A float clears before it is placed, exactly as a block does.
        sides = _CLEAR_SIDES.get(getattr(block, "clear", None) or "none")
        if sides:
            cleared = floats.lowest_bottom(sides)
            if cleared is not None:
                top = min(top, cleared)

        span = outer + start + end
        while True:
            left_inset, right_inset = floats.insets(top, box_x, width)
            if width - left_inset - right_inset >= span:
                break
            below = floats.next_bottom_below(top)
            if below is None:
                break
            top = below
        if side == "left":
            outer_x = box_x + left_inset + start
        else:
            outer_x = box_x + width - right_inset - end - outer

        if isinstance(block, Image):
            bottom = self._place_image(
                replace(block, width_mm=outer, width_fraction=None),
                outer_x, top, outer, pages, new_page,
            )
        else:
            bottom = self._place_container(
                replace(block, width_mm=outer, width_fraction=None),
                outer_x - start, top, span, pages, new_page,
            )
        trailing = block.space_after_mm or 0.0
        floats.boxes.append(_FloatBox(
            side=side,
            top_mm=top,
            # The context stores *margin* box bottoms, because that is what
            # `lowestFloatLogicalBottom` returns and therefore what a `clear`
            # clears to.
            bottom_mm=bottom - max(0.0, trailing),
            left_mm=outer_x - start,
            right_mm=outer_x + outer + end,
        ))

    def _place_paragraph(self, block: Paragraph, box_x: float, y: float, width: float, pages, new_page) -> float:
        p = self.policy
        page, total = self._page_ctx
        runs = self._paragraph_runs(block, page=page, total=total)
        height_size = block.font_size_pt or self._role_size_pt(block.role)
        if not runs and block.rule_above_pt:
            pages[-1].append(Line(
                box_x, y, box_x + width, y,
                width_pt=block.rule_above_pt,
                stroke_rgb=self._flatten_on_white(
                    rgb(BLOCK_RULE_RGB, BLOCK_RULE_RGB), BLOCK_RULE_OPACITY
                ),
            ))
            # A bare `hr` is a one-pixel-high box. Its margins live on the
            # Paragraph; the box itself still consumes its rule thickness.
            return y - block.rule_above_pt * 25.4 / 72.0
        # `white-space: nowrap` removes soft wrap opportunities --
        # the same rule `TableCell.nowrap` already applies to a cell (see
        # `draw_row`'s `cell.nowrap` branch). `.text-truncate` implies this;
        # ignoring it here is why an over-long identifier under a
        # `.text-truncate` title split across lines instead of staying put.
        # A forced break is not a soft opportunity: `<br>` still ends the
        # line, including under nowrap.
        lines = self._nowrap_lines(
            runs, preserve_collapsed_space=block.preserves_collapsed_space,
        ) if (runs and block.nowrap) else (
            self._wrap_runs(
                runs, width, height_size,
                letter_spacing_mm=block.letter_spacing_mm,
                preserve_collapsed_space=block.preserves_collapsed_space,
            )
        )
        size = block.font_size_pt or self._role_size_pt(block.role)
        # A block's own `lh-*` wins; otherwise a heading takes the tighter
        # heading ratio and body text the body one. `p.line_height_mm` is
        # deliberately not used here: it is a table *row* metric that carries
        # the cell's border as well, and reusing it for a block paragraph set
        # every body line 0.24mm too far apart.
        if block.line_height_mm is not None:
            step = block.line_height_mm
        elif block.line_height_ratio is not None:
            step = self._line_advance_mm(size, block.line_height_ratio)
        elif size == p.font_size_pt:
            step = self._line_advance_mm(size, LINE_HEIGHT_RATIO)
        else:
            step = self._line_advance_mm(size, HEADING_LINE_HEIGHT_RATIO)
        height = len(lines) * step
        if not self._in_band and y - height < self._bottom_limit and pages[-1]:
            new_page()
            y = p.height_mm - p.margin_top_mm
        # CSS colour inherits. The report bundle gives body #111827, while
        # headings explicitly override that inherited value with #000. A
        # company selector or literal declaration remains more specific.
        fill = block.fill_rgb
        if fill is None and (
            block.colour_role == "title" or block.role in _SEMANTIC_TITLE_ROLES
        ):
            fill = self.theme.title_rgb
        elif fill is None and block.colour_role == "tagline":
            fill = self.theme.tagline_rgb
        elif fill is None:
            # A heading gets no colour of its own here. The bundle's only
            # heading rule is `h1--h6 { color: var(--heading-color) }`, and
            # declaration and the heading inherits the body. The company rule
            # that does apply -- `.o_company_1_layout h2 { color: #5e4766 }`
            # -- is literal, and arrives as a scoped `colour_role` above.
            fill = self._text_rgb
        if block.rule_above_pt:
            # `.border-top` on the wrapper. Drawn at the block's top edge,
            # before the first baseline drops below it.
            pages[-1].append(Line(
                box_x, y, box_x + width, y,
                width_pt=block.rule_above_pt, stroke_rgb=rgb(BLOCK_RULE_RGB, BLOCK_RULE_RGB),
            ))
        # No paragraph-level bold override: `_inline_children` already
        # stamps the paragraph's own bold onto every run it builds, so
        # forcing it again here would make one `<strong>` bold the sentence
        # around it -- which is what it used to do.
        first = True
        for line in lines:
            y -= self._first_baseline_mm(size, step) if first else step
            first = False
            start = box_x
            if block.align in {"right", "center"}:
                spare = width - self._line_width_mm(
                    line, size, letter_spacing_mm=block.letter_spacing_mm
                )
                start = box_x + (spare if block.align == "right" else spare / 2.0)
            pages[-1].extend(self._draw_runs(
                line, start, y, size, fill=fill,
                letter_spacing_mm=block.letter_spacing_mm,
            ))
        # The block still occupies whole line boxes; only the baseline inside
        # the first one moves.
        return y - (step - self._first_baseline_mm(size, step))

    def _cell_images(self, cell, available_mm: float):
        """Images a table cell carries, sized the way a block-level one is."""
        placed = []
        for block in cell.blocks:
            if not isinstance(block, Image):
                continue
            width, height = self._image_dimensions(block, available_mm)
            if width > available_mm > 0:
                height *= available_mm / width
                width = available_mm
            placed.append((block, width, height))
        return placed

    def _image_dimensions(self, block: Image, available_mm: float):
        """Resolve declared image dimensions against its containing block."""
        natural_size = block.natural_size_px
        source = None
        constrained_intrinsic = (
            block.max_width_mm is not None
            or block.max_width_fraction is not None
            or block.max_height_mm is not None
        )
        if natural_size is None and constrained_intrinsic:
            try:
                source = self._resolved_image_source(block.src)
                from docsubstrate.image_assets import image_natural_size_px

                natural_size = image_natural_size_px(source)
            except Exception:
                source = block.src
        ratio = None
        if natural_size:
            natural_width, natural_height = natural_size
            if natural_height:
                ratio = natural_width / natural_height
        if not ratio:
            try:
                source = source or self._resolved_image_source(block.src)
            except Exception:
                source = block.src
            ratio = self._aspect_ratio(source, default=1.0)

        width = block.width_mm
        height = block.height_mm
        if block.width_fraction is not None:
            width = max(0.0, available_mm * block.width_fraction)
        if width is None and height is None and natural_size:
            width = natural_size[0] * 25.4 / self.policy.css_px_per_inch
            height = natural_size[1] * 25.4 / self.policy.css_px_per_inch
        if width is None and height is not None:
            width = height * ratio
        if width is None:
            # Preserve the existing fallback for a payload with neither a
            # usable natural size nor a width declaration.
            if height is None and block.src not in self._image_fallback_warned:
                warning = (
                    "image has no resolved CSS width or height; using "
                    f"{self.DEFAULT_IMAGE_WIDTH_MM:.2f}mm fallback box"
                )
                self.warnings.append(warning)
                _logger.warning(warning)
                self._image_fallback_warned.add(block.src)
            width = min(max(1.0, available_mm), self.DEFAULT_IMAGE_WIDTH_MM)
        if height is None:
            if block.natural_size_is_failed_replaced_element and natural_size:
                # bother scaling" when `errorOccurred()`: a failed
                # replaced element's used height is its fixed intrinsic
                # value directly, never a stated width divided by a
                # ratio -- which for this engine's own 20x20 fixed size
                # would silently reproduce the real image's answer
                # whenever the real ratio also happens to be 1:1 (as it
                # is here), since 100/1.0 and 100/1.0 are the same
                # number. The flag exists so this branch is reached on
                # its own evidence, not on the numbers coinciding.
                height = natural_size[1] * 25.4 / self.policy.css_px_per_inch
            else:
                height = width / ratio if ratio > 0 else width
        max_width = block.max_width_mm
        if block.max_width_fraction is not None:
            relative_max = max(0.0, available_mm * block.max_width_fraction)
            max_width = min(max_width, relative_max) if max_width is not None else relative_max
        scales = [1.0]
        if max_width is not None and width > max_width:
            scales.append(max_width / width)
        if block.max_height_mm is not None and height > block.max_height_mm:
            scales.append(block.max_height_mm / height)
        scale = min(scales)
        width *= scale
        height *= scale
        return width, height

    def _place_image(
        self, block: Image, box_x: float, y: float, width: float, pages, new_page,
        *, align: str | None = None,
    ) -> float:
        """Place an image, breaking the page when it does not fit below.

        An image without a stated width keeps the existing capped fallback;
        when its payload supplies a natural ratio, ``height:auto`` follows it.
        """
        p = self.policy
        image_width, image_height = self._image_dimensions(block, width)
        if not self._in_band and y - image_height < self._bottom_limit and pages[-1]:
            new_page()
            y = p.height_mm - p.margin_top_mm
        y -= image_height
        image_x = box_x
        if align == "right":
            image_x += max(0.0, width - image_width)
        elif align == "center":
            image_x += max(0.0, width - image_width) / 2.0
        pages[-1].extend(self._draw_image(
            block.src, image_x, y, image_width, image_height,
            preserve_aspect_ratio=block.object_fit != "fill",
        ))
        return y

    def _draw_image(self, src, x, y, width, height, *, preserve_aspect_ratio=False):
        """Every command needed to put this image on the page.

        One entry point because three places draw an image -- a block, a
        container background and a table cell -- and wiring the vector path
        into only the first is how the other two keep photographing SVGs
        while the tests stay green. That is exactly what happened: the
        employee badge's avatar went on drawing itself as a bitmap because
        its image is placed by a different branch.

        Returns a list, so a drawn SVG can be several shapes and an
        undrawable image can be none.
        """
        drawn = self._vector_commands(src, x, y, width, height)
        if drawn is not None:
            return drawn
        command = self._image_ref(
            src, x, y, width, height,
            preserve_aspect_ratio=preserve_aspect_ratio,
        )
        return [] if command is None else [command]

    def _vector_commands(self, src, x, y, width, height):
        """Draw an SVG into the box it was given, or None to photograph it.

        wkhtmltopdf renders SVG as vector, so a barcode reaches its PDF as
        rectangles and Odoo's letter avatar as a `<text>` object. Rasterising
        instead costs three things at once: those marks go missing from
        emitted, and the letter stops being text.

        That last one is why this is worth doing past fidelity. A glyph baked
        into a bitmap is gone for every consumer that is not a page.

        Returning None means fall back and rasterise. Every such fall back is
        warned rather than silent, because a quiet one rebuilds the situation
        this replaces and leaves nothing to find it by.
        """
        from docsubstrate.image_assets import (
            SvgRect,
            UnvectorisableSvg,
            svg_payload,
            vectorize_svg,
        )

        try:
            payload = svg_payload(src, self.policy.image_base_url)
        # An unreadable source is the raster path's problem to report, and it
        # will, so this one stays quiet rather than warning twice.
        except Exception:  # noqa: BLE001
            return None
        if payload is None:
            return None
        try:
            (intrinsic_width, intrinsic_height), shapes = vectorize_svg(payload)
        except UnvectorisableSvg as exc:
            self._warn_once(f"SVG rasterised rather than drawn: {exc}")
            return None
        except ValueError:
            # Malformed or sizeless: unusable by either path, and the raster
            # fallback names it precisely. Not a vectorisation gap.
            return None
        if not intrinsic_width or not intrinsic_height:
            return None

        scale_x = width / intrinsic_width
        scale_y = height / intrinsic_height
        # SVG counts y downward from the box's top; a plan counts it upward
        # from the page's bottom, and the box's bottom edge is `y`.
        top = y + height
        commands = []
        for shape in shapes:
            if isinstance(shape, SvgRect):
                commands.append(Rect(
                    x + shape.x * scale_x,
                    top - (shape.y + shape.height) * scale_y,
                    shape.width * scale_x,
                    shape.height * scale_y,
                    stroke=False, fill=True, fill_rgb=shape.fill_rgb,
                ))
                continue
            size_pt = shape.font_size * scale_y * 72.0 / 25.4
            text_x = x + shape.x * scale_x
            if shape.anchor == "middle":
                from reportlab.pdfbase.pdfmetrics import stringWidth

                # `text-anchor` is resolved here and not in `vectorize_svg`
                # because it needs the width of this string in the font that
                # will actually draw it, which is known here and nowhere
                # earlier.
                text_x -= stringWidth(
                    shape.text, self.font_name, size_pt
                ) * 25.4 / 72.0 / 2.0
            commands.append(TextRun(
                text_x, top - shape.y * scale_y, shape.text,
                font_name=self.font_name, font_size_pt=size_pt,
                fill_rgb=shape.fill_rgb,
            ))
        return commands

    def _image_ref(
        self, src: str, x: float, y: float, width: float, height: float,
        *, preserve_aspect_ratio: bool = False,
    ):
        """An executable image command, or a warned gap of the same size.

        Planning has already claimed the image's box when this runs.  If the
        Canvas cannot decode the payload, omitting only the command preserves
        that geometry instead of aborting the whole document or closing the
        surrounding content over the missing asset.
        """
        valid = self._image_validity.get(src)
        if valid is False:
            return None
        if valid is None:
            try:
                resolved = self._resolved_image_source(src)
                from docsubstrate.renderers.reportlab_canvas import _image_source

                source = _image_source(resolved)
                if isinstance(source, str):
                    from reportlab.lib.utils import ImageReader

                    source = ImageReader(source)
                source.getSize()  # ImageReader is lazy; force the decode here.
            except Exception as exc:
                self._image_validity[src] = False
                media_type = "external image"
                if src.startswith("data:image/"):
                    media_type = src.partition(",")[0].removeprefix("data:").split(";", 1)[0]
                warning = (
                    f"image not drawn; layout gap preserved: {media_type} "
                    f"could not be decoded ({type(exc).__name__}: {exc})"
                )
                self.warnings.append(warning)
                _logger.warning(warning)
                return None
            self._image_validity[src] = True
        return ImageRef(
            self._resolved_images[src], x, y, width, height,
            preserve_aspect_ratio=preserve_aspect_ratio,
        )

    def _resolved_image_source(self, src: str) -> str:
        resolved = self._resolved_images.get(src)
        if resolved is None:
            from docsubstrate.image_assets import resolve_image_source

            resolved = resolve_image_source(src, self.policy.image_base_url)
            self._resolved_images[src] = resolved
        return resolved

    @staticmethod
    def _aspect_ratio(src: str, *, default: float) -> float:
        """Width over height of an embedded image, or `default` if unreadable."""
        try:
            from docsubstrate.renderers.reportlab_canvas import _image_source

            reader = _image_source(src)
            image_width, image_height = reader.getSize()
            if image_height:
                return image_width / image_height
        except Exception:
            _logger.debug("could not read image proportions from %s", src[:40], exc_info=True)
        return default

    def _place_grid(self, grid: Grid, pages, y: float, width: float, new_page, box_x: float) -> float:
        # Bubble and Wave frame the informations row, and they do it by
        # overriding the row's negative margin to zero -- so the panel spans
        # the container exactly and its padding insets what is inside it.
        # panel and the table below it disagree about where the page edge is.
        box = self.theme.informations_box if grid.kind == "info" else None
        outer_x, outer_width = box_x, width
        if box is not None:
            box_x += box.padding_mm
            width = max(1.0, width - 2 * box.padding_mm)
        # The row's own padding does the same thing and for the same reason:
        # a background paints to the border box and the padding insets what
        # is inside it. Applied once -- the themed box's own padding is 0
        # now that the cascade states this one.
        padding = _PaddingBox.of(grid.padding_mm)
        box_x, width = padding.inset(box_x, width)
        # The border box top, kept before the padding opens. The panel and
        # any background paint to *this*, not to where the content starts.
        outer_top = y
        y = padding.open(y)

        # Bootstrap pulls the row out by half a gutter and pads each column
        # back in by the same, so column *content* starts flush with the
        # container and the gutter is taken out of the width, never added
        # gutter) / columns.
        col_w = (width + grid.gutter_mm) / max(1, grid.columns)
        cursor = 0
        row: list[tuple[float, float, tuple]] = []
        rows: list[list[tuple[float, float, tuple]]] = []
        for cell in grid.cells:
            span = max(1, cell.span)
            if cell.offset == -1:
                cursor = max(cursor, grid.columns - span)
            else:
                cursor += max(0, cell.offset)
            if cursor + span > grid.columns and row:
                rows.append(row)
                row = []
                cursor = 0 if cell.offset < 0 else max(0, cell.offset)
            cell_x = box_x + cursor * col_w
            cell_w = max(1.0, span * col_w - grid.gutter_mm)
            # The cell's `text-align` reaches its blocks here, the same way a
            # `HorizontalCell`'s does in `_place_horizontal`. A Paragraph
            # usually already carries it from the cascade; a line box did not
            # carry it at all until it had somewhere to put it.
            row.append((cell_x, cell_w, _inherit_align(cell.blocks, cell.align)))
            cursor += span
        if row:
            rows.append(row)

        # The frame needs the height of what it frames, so it is drawn after
        # the flow and inserted underneath it -- and only when the flow
        # stayed on one page, because a box around content that paginated is
        # a box around the wrong thing.
        page_before = len(pages)
        mark = len(pages[-1])
        top = outer_top
        if box is not None:
            y -= box.padding_mm

        for row_cells in rows:
            y_start = y
            y_end = y
            for cell_x, cell_w, blocks in row_cells:
                y_cell = self._flow(blocks, cell_x, y_start, cell_w, pages, new_page)
                y_end = min(y_end, y_cell)
            y = y_end

        # The bottom padding closes the border box, and it does so whether or
        # not this grid drew anything: an empty row is still as tall as its
        # own two paddings.
        y = padding.close(y)

        if box is not None:
            y -= box.padding_mm
            if len(pages) == page_before and (box.fill or box.border_rgb):
                pages[-1].insert(mark, Rect(
                    outer_x, y, outer_width, top - y,
                    stroke=box.border_rgb is not None,
                    fill=box.fill is not None,
                    line_width_pt=box.border_pt,
                    fill_rgb=box.fill,
                    stroke_rgb=box.border_rgb,
                    radius_mm=box.radius_mm,
                ))
        return y

    @staticmethod
    def _cell_trailing_margin_mm(cell) -> float:
        """The bottom margin a cell keeps inside itself.

        The signed and last-child cases in
        `tests/test_table_cell_trailing_margin.py` require that a cell never
        collapse with its
        children and `handleAfterSideOfBlock` (`:1835-1838`) adds the held
        margin to its height. The quirks branch of that condition needs
        `document()->inQuirksMode()`, and these documents carry a
        `<!DOCTYPE html>`.

        The **last** child's, and only its own. `marginInfo.margin()` at the
        after side of a block is what the final child left pending, not the
        largest margin anywhere in the box: an earlier child's bottom margin
        has already collapsed against the next child's top and been spent
        inside the flow. Taking a maximum would let a big margin in the
        middle of a cell push the cell's floor down.

        **Signed.** `marginInfo.margin()` is a signed quantity and
        `handleAfterSideOfBlock` adds it as one, so a negative bottom margin
        makes the box shorter. Clamping it at zero would keep a cell that CSS
        shrinks at its full height; the minimum the renderer does impose is
        on the total (`:1844`, `max(logicalHeight(), beforeSide + afterSide)`),
        not on this term.

        One function because three places need the same number: the cell's
        height, and where a bottom- or middle-aligned cell puts its text.
        The same table-cell contract positions the whole content box --
        `logicalHeightWithoutIntrinsicPadding`, which includes this margin --
        and the text sits at the top of that box, so the margin is below the
        text in every one of the three.
        """
        if not cell.blocks:
            return 0.0
        return cell.blocks[-1].space_after_mm or 0.0

    @staticmethod
    def _edge_dash(edge):
        multipliers = BORDER_DASH_MULTIPLIERS.get(edge.style, ())
        return tuple(edge.width_pt * value for value in multipliers)

    def _place_container(
        self, block: Container, box_x: float, y: float, width: float, pages, new_page,
        *, discard_positive_leading_margin: bool = False,
        containing_height_mm: float | None = None,
        floats: "_FloatContext | None" = None,
    ) -> float:
        """Flow a normal element's children inside its declared border box."""
        outer_width = (
            block.width_mm if block.width_mm is not None
            else width * block.width_fraction if block.width_fraction is not None
            else max(0.0, width - block.margin_start_mm - block.margin_end_mm)
        )
        spare = max(0.0, width - outer_width - block.margin_start_mm - block.margin_end_mm)
        if block.margin_start_auto and block.margin_end_auto:
            offset = block.margin_start_mm + spare / 2.0
        elif block.margin_start_auto:
            offset = block.margin_start_mm + spare
        else:
            offset = block.margin_start_mm
        outer_x = box_x + offset
        top = y
        edge_mm = tuple(edge.width_pt * 25.4 / 72.0 for edge in block.border)
        pad_top, pad_right, pad_bottom, pad_left = block.padding_mm
        content_x = outer_x + edge_mm[3] + pad_left
        content_width = max(
            0.1, outer_width - edge_mm[1] - edge_mm[3] - pad_left - pad_right
        )
        content_y = y - edge_mm[0] - pad_top
        declared_height = block.height_mm
        if declared_height is None and block.height_fraction is not None:
            if containing_height_mm is None:
                if not self._measuring_intrinsic:
                    self._warn_once(
                        "percentage container height is unresolved; using natural height"
                    )
            else:
                declared_height = containing_height_mm * block.height_fraction
        content_height = None
        if declared_height is not None:
            content_height = max(
                0.0,
                declared_height - edge_mm[0] - edge_mm[2] - pad_top - pad_bottom,
            )
        mark = len(pages[-1])
        page_before = len(pages)
        bottom = self._flow(
            block.children, content_x, content_y, content_width, pages, new_page,
            discard_positive_leading_margin=discard_positive_leading_margin,
            containing_height_mm=content_height,
            floats=floats,
        )
        trailing_mm = self._flow_trailing_mm
        bottom -= pad_bottom + edge_mm[2]
        if declared_height is not None:
            # CSS `height` is a used box size, not `min-height`. Descendants
            # may overflow that box, but they do not enlarge it or move the
            # following flow. This is load-bearing on Odoo's 4x12 sheets:
            # 12 authored 19mm labels plus 40mm page padding occupy 268mm;
            # treating each height as a minimum lets label contents enlarge
            # the rows and invents a second page that wkhtmltopdf never has.
            bottom = top - declared_height

        if block.paint_suppressed:
            # `opacity: 0`. Geometry above this point is unchanged --
            # `bottom` already accounts for this box's own padding/border
            # and any declared height, exactly as an ordinary container's
            # would -- only paint is gone. `_flow` already appended
            # everything this subtree draws (text, images, rules and
            # fills, generated content, page markers, this container's own
            # border/fill/background included) to `pages[-1]` at and after
            # `mark`; discarding from there covers all of it in the one
            # place they all pass through, the same way CSS itself cannot
            # be escaped from inside -- a descendant's own opacity of 1
            # does not un-suppress a subtree its ancestor already zeroed.
            # A page break inside a suppressed box is one this box's own
            # (invisible) content forced; nothing on the pages it forced
            # open belongs to anything else yet, so they are cleared
            # outright rather than warned about.
            del pages[page_before - 1][mark:]
            for page in pages[page_before:]:
                del page[:]
            return bottom

        visible = [edge for edge in block.border if edge.width_pt and edge.style != "none"]
        if len(pages) != page_before:
            # A sizing-only wrapper has no paint to lose when its children
            # paginate.  Odoo's evaluated PDF body is rooted at
            # `<html style="height: 0">`, so warning for every multi-page
            # report would claim that an invisible frame was omitted.
            if block.fill_rgb is not None or block.background_image_src or visible:
                self.warnings.append("styled container split across pages; frame not drawn")
            return bottom

        height = max(0.0, top - bottom)
        paint_bottom = bottom
        # CSS 2.2 section 8.3.1: the bottom margin of an in-flow last child
        # collapses through a parent with no bottom border, padding or stated
        # height. A background does not establish a new formatting context,
        # so the collapsed margin lies outside the painted box. The report
        # article ends in ``mb-3`` (3.61244mm); including it made its centred
        # contain image 1.80622mm lower even though all content anchors stayed
        # put. Keep returning ``bottom`` so the collapsed margin still
        # separates the following flow, but exclude it from box paint.
        if (
            block.children
            and not block.contains_trailing_clearance
            and declared_height is None
            and not block.float_side
            and pad_bottom == 0.0
            and edge_mm[2] == 0.0
        ):
            if trailing_mm > 0.0:
                paint_bottom = min(top, bottom + trailing_mm)
        paint_height = max(0.0, top - paint_bottom)
        if block.background_image_src:
            self._insert_container_background_image(
                block, pages[-1], mark, outer_x, paint_bottom, outer_width, paint_height
            )
        uniform = bool(visible) and all(edge == block.border[0] for edge in block.border)
        if uniform:
            edge = block.border[0]
            inset = edge.width_pt * 25.4 / 72.0 / 2.0
            pages[-1].insert(mark, Rect(
                outer_x + inset,
                paint_bottom + inset,
                max(0.0, outer_width - 2 * inset),
                max(0.0, paint_height - 2 * inset),
                stroke=True,
                fill=block.fill_rgb is not None,
                line_width_pt=edge.width_pt,
                fill_rgb=block.fill_rgb,
                stroke_rgb=edge.colour,
                radius_mm=block.radius_mm,
                dash_array_pt=self._edge_dash(edge),
            ))
        else:
            if block.fill_rgb is not None:
                pages[-1].insert(mark, Rect(
                    outer_x, paint_bottom, outer_width, paint_height,
                    stroke=False, fill=True, fill_rgb=block.fill_rgb,
                    radius_mm=block.radius_mm,
                ))
                mark += 1
            coordinates = (
                (outer_x, top, outer_x + outer_width, top),
                (outer_x + outer_width, top, outer_x + outer_width, paint_bottom),
                (outer_x, paint_bottom, outer_x + outer_width, paint_bottom),
                (outer_x, top, outer_x, paint_bottom),
            )
            for edge, coords in reversed(list(zip(block.border, coordinates))):
                if not edge.width_pt or edge.style == "none":
                    continue
                pages[-1].insert(mark, Line(
                    *coords,
                    width_pt=edge.width_pt,
                    stroke_rgb=edge.colour,
                    dash_array_pt=self._edge_dash(edge),
                ))
        return bottom

    def _insert_container_background_image(
        self, block, commands, mark, box_x, box_y, box_width, box_height
    ):
        """Paint one source-derived CSS background below container content.

        ``background-size:contain; background-position:center;
        background-repeat:no-repeat``.  Unsupported CSS values warn instead
        of degrading to an invented box, because a wrong background can look
        like a successful render while covering most of the page.
        """
        if block.background_repeat != "no-repeat":
            self._warn_once(
                "container background image not drawn: only no-repeat is supported"
            )
            return
        if block.background_size != "contain":
            self._warn_once(
                "container background image not drawn: only contain is supported"
            )
            return
        if block.background_position != "center":
            self._warn_once(
                "container background image not drawn: only center is supported"
            )
            return
        try:
            source = self._resolved_image_source(block.background_image_src)
            from docsubstrate.image_assets import image_natural_size_px

            natural = image_natural_size_px(source)
            if not natural or natural[0] <= 0 or natural[1] <= 0:
                raise ValueError("image has no natural dimensions")
        except Exception as exc:
            self._warn_once(
                "container background image not drawn: natural size could not be "
                f"resolved ({type(exc).__name__}: {exc})"
            )
            return
        scale = min(box_width / natural[0], box_height / natural[1])
        image_width = natural[0] * scale
        image_height = natural[1] * scale
        image_x = box_x + (box_width - image_width) / 2.0
        image_y = box_y + (box_height - image_height) / 2.0
        # Insert rather than append: a background belongs behind the content
        # already planned above it, and several shapes keep their order.
        for offset, command in enumerate(self._draw_image(
            block.background_image_src,
            image_x,
            image_y,
            image_width,
            image_height,
        )):
            commands.insert(mark + offset, command)

    @staticmethod
    def _cell_cursor(cells, widths, gap, box_x):
        """Where each item starts, walking the row once.

        One walk, two readers: the pass that measures the row and the pass
        that draws it. They had drifted -- the first advanced by each item's
        own horizontal margins and the second did not -- so a margin was
        drawn. Two loops cannot answer this separately without doing that
        again.
        """
        cursor = box_x
        for cell, width in zip(cells, widths):
            cursor += cell.margin_left_mm
            yield cell, width, cursor
            cursor += width + cell.margin_right_mm + gap

    def _place_horizontal(self, block: Horizontal, pages, y: float, width: float, new_page, box_x: float) -> float:
        if not block.cells:
            return y
        gap = block.gap_mm
        cell_widths = self._horizontal_cell_widths(block, width)
        # `text-align` moves the line box's content inside the box, and this
        # row is that content when it is an inline run. Its extent is read
        # from the same walk that places the items, so the offset cannot
        # disagree with where they land.
        box_x += self._inline_run_offset(block, cell_widths, gap, width)
        # A flex row packs instead. The two are exclusive by construction:
        # `_inline_run_offset` returns zero unless the row is a line box and
        # `_pack_offsets` unless it is a flex row.
        pack = self._pack_offsets(block, cell_widths, gap, width)
        y_start = y
        measured_end = y_start
        was_in_band = self._in_band
        self._in_band = True
        try:
            scratch = [[]]
            cell_ends = []
            for index, (cell, cell_w, cell_x) in enumerate(self._cell_cursor(
                block.cells, cell_widths, gap, box_x
            )):
                blocks = _inherit_align(cell.blocks, cell.align)
                cell_end = self._flow(
                    blocks, cell_x + pack[index], y_start, cell_w,
                    scratch, lambda: None
                )
                cell_ends.append(cell_end)
                measured_end = min(measured_end, cell_end)
        finally:
            self._in_band = was_in_band
        if (
            not self._in_band
            and measured_end < self._bottom_limit
            and (pages[-1] or y_start < self._top_y)
        ):
            new_page()
            y_start = self.policy.height_mm - self.policy.margin_top_mm
        if block.rule_above_pt:
            pages[-1].append(Line(
                box_x,
                y_start,
                box_x + width,
                y_start,
                width_pt=block.rule_above_pt,
                stroke_rgb=rgb(BLOCK_RULE_RGB, BLOCK_RULE_RGB),
            ))
        # `align-items: center` centres each item on the row's cross axis. The
        # standard header states it on the row holding the logo and the
        # tagline, and without it a one-line tagline sits at the top of a much
        # against the logo's 40.5, while this engine top-aligned it at 28.4
        # against a logo top of 26.6.
        row_height = max(0.0, y_start - measured_end)
        offsets = [0.0] * len(block.cells)
        if block.align_items == "center":
            offsets = [
                max(0.0, (row_height - max(0.0, y_start - end)) / 2.0)
                for end in cell_ends
            ]

        y_end = y_start
        for index, (cell, cell_w, cell_x) in enumerate(self._cell_cursor(
            block.cells, cell_widths, gap, box_x
        )):
            blocks = _inherit_align(cell.blocks, cell.align)
            y_cell = self._flow(
                blocks, cell_x + pack[index], y_start - offsets[index], cell_w,
                pages, new_page
            )
            y_end = min(y_end, y_cell)
        return y_end

    def _pack_offsets(self, block: Horizontal, widths, gap: float, width: float):
        """Place box children from the row's project-owned packing contract."""
        if block.inline_run:
            return [0.0] * len(block.cells)
        return list(
            packed_offsets(
                cells=block.cells,
                widths=widths,
                gap_mm=gap,
                row_width_mm=width,
                css_px_per_inch=self.policy.css_px_per_inch,
                pack=(block.pack or "").strip().lower(),
            )
        )

    def _inline_run_offset(
        self, block: Horizontal, widths, gap: float, width: float
    ) -> float:
        """Shift one inline run within its finite containing width."""
        return inline_alignment_offset(
            cells=block.cells,
            widths=widths,
            gap_mm=gap,
            row_width_mm=width,
            inline_run=block.inline_run,
            align=block.align,
        )

    def _horizontal_cell_widths(
        self, block: Horizontal, width: float
    ) -> tuple[float, ...]:
        """Resolve row widths from authored IR and project allocation rules."""
        return allocate_horizontal_widths(
            block.cells,
            width,
            block.gap_mm,
            self.policy.css_px_per_inch,
            self._horizontal_cell_intrinsic_width,
            self._warn_unknown_flex_item,
        )

    def _warn_unknown_flex_item(self, cell) -> None:
        """A flex item whose max-content width this planner cannot state.

        The engine always has one, so this is our gap rather than the
        document's. It is reported instead of being silently sized, because
        the alternative -- reading `None` as zero -- put every character of a
        company tagline on its own line across three layouts.
        """
        kinds = ",".join(sorted({type(b).__name__ for b in cell.blocks}))
        warning = f"flex item has no measurable max-content width: {kinds}"
        if warning not in self.warnings:
            self.warnings.append(warning)

    def _cell_demand_texts(self, blocks):
        """Every string a cell's content holds, however deeply it sits.

        This read only the cell's top-level `Paragraph`s. A cell whose
        content is wrapped in anything else therefore demanded **nothing**,
        and when every column of a table demands nothing `distribute` has no
        proportion to work with and falls to its equal-share branch.

        That is what a `.row` inside a `<td>` walked straight into. The
        delivery slip's address table carries an authored `colspan="2"` on
        its second row, so the table really is two columns wide; once the
        first row's cell held a `Grid` rather than paragraphs its demand
        went to zero, both columns split the width evenly, and the address
        was placed correctly inside half a cell.

        This is text demand, not general preferred width: a block whose
        preferred width is not a function of the text it holds -- an `Image`
        chief among them -- still contributes nothing here, the same way a
        computePreferredLogicalWidths` would add a replaced element's own
        intrinsic width; recorded as an open gap in `docs/capability-gaps.md`
        rather than folded in here, since closing it needs min/max semantics
        exercises it (reach zero -- no table cell in any of the 175
        documents holds an `Image` at any depth).
        """
        for block in blocks:
            if isinstance(block, Paragraph):
                yield self._paragraph_text(block)
                continue
            for name in ("children", "blocks"):
                yield from self._cell_demand_texts(getattr(block, name, ()) or ())
            for inner in (getattr(block, "cells", ()) or ()):
                yield from self._cell_demand_texts(getattr(inner, "blocks", ()) or ())
            for row in (getattr(block, "rows", ()) or ()):
                for inner in row.cells:
                    yield from self._cell_demand_texts(inner.blocks)

    def _horizontal_cell_intrinsic_width(
        self, cell: HorizontalCell, available_mm: float | None = None,
    ) -> float | None:
        """A flex item's max-content width: the widest thing it contains.

        Every block contributes, not only the paragraphs. The engine has no
        Widths` walks all of them, and a replaced child such as an `img`
        contributes its own width -- so a cell holding a logo beside a
        tagline is as wide as the wider of the two.

        Returning `None` here means *not knowable*, and a caller must not
        read it as *needs nothing*. Those are different claims, and reading
        the first as the second collapsed the company block in Folder,
        Striped and Wave to zero width and put each character of the tagline
        on its own line.
        """
        widths = []
        for block in cell.blocks:
            width = self._block_intrinsic_width(block, available_mm)
            if width is None:
                return None
            widths.append(width)
        return max(widths, default=0.0)

    def _block_intrinsic_width(
        self, block, available_mm: float | None = None,
    ) -> float | None:
        """One block's max-content width, or `None` when we cannot say."""
        if isinstance(block, Image):
            width, _height = self._image_dimensions(
                block, available_mm if available_mm is not None else 0.0
            )
            return width
        if isinstance(block, Container):
            widths = [
                self._block_intrinsic_width(child, available_mm)
                for child in block.children
            ]
            if any(value is None for value in widths):
                return None
            return max(widths, default=0.0)
        if isinstance(block, Horizontal):
            widths = [
                self._horizontal_cell_intrinsic_width(inner, available_mm)
                for inner in block.cells
            ]
            if any(value is None for value in widths):
                return None
            gaps = block.gap_mm * max(0, len(block.cells) - 1)
            return sum(widths) + gaps
        if not isinstance(block, Paragraph):
            return None
        return self._paragraph_intrinsic_width(block)

    def _paragraph_intrinsic_width(self, block: Paragraph) -> float:
        """One paragraph's widest line, forced breaks respected."""
        size = block.font_size_pt or self._role_size_pt(block.role)
        runs = self._paragraph_runs(
            block, page=self._page_ctx[0], total=self._page_ctx[1]
        )
        lines: list[list[tuple]] = [[]]
        for run in runs:
            if run[0] == "\n":
                lines.append([])
            else:
                lines[-1].append(run)
        return max((
            self._line_width_mm(
                line, size, letter_spacing_mm=block.letter_spacing_mm
            )
            for line in lines
        ), default=0.0)

    def _font(self, bold: bool) -> str:
        if bold and self.font_name == "Helvetica":
            return "Helvetica-Bold"
        return self.font_name

    def _runs(
        self, text: str, x_mm: float, y_mm: float, size_pt: float, *,
        bold=False, fill=None, letter_spacing_mm=0.0, source_block_id=None,
        font_family=None,
    ):
        """One TextRun per script, laid end to end from `x_mm`."""
        runs = []
        cursor = x_mm
        segments = list(self.fonts.segments(text, font_family))
        for index, (segment, face) in enumerate(segments):
            if bold:
                face = self.fonts.bold(face)
            runs.append(TextRun(
                cursor, y_mm, segment, font_name=face, font_size_pt=size_pt,
                fill_rgb=fill,
                char_space_pt=letter_spacing_mm * 72.0 / 25.4,
                source_block_id=source_block_id,
            ))
            from reportlab.pdfbase.pdfmetrics import stringWidth

            cursor += stringWidth(segment, face, size_pt) * 25.4 / 72.0
            cursor += max(0, len(segment) - 1) * letter_spacing_mm
            if index < len(segments) - 1 and segment:
                cursor += letter_spacing_mm
        return runs

    def _column_widths(self, table, count, table_width, pad, weights):
        """Size the columns from their content, the way an HTML table does.

        Fixed weights per report is the same mistake as one template per
        report. What the stylesheet actually says is `white-space: nowrap` on
        four of the five line-table columns and a min/max width on the
        quantity one; everything else follows from how wide the text is.

        A `nowrap` column is never narrower than its widest cell -- that is
        what nowrap means, and giving the tax column less is what broke "5%"
        across two lines and made every row half again as tall as the source
        engine draws it.
        """
        if table.layout_mode == "fixed":
            return self._fixed_column_widths(table, count, table_width)

        demands = [ColumnDemand(0.0, 0.0) for _ in range(count)]
        spanning_demands = []
        placements, _grid_count = table_column_placements(table.rows)
        for row, starts in zip(table.rows, placements):
            for cell, index in zip(row.cells, starts):
                span = max(1, min(cell.colspan, count - index))
                if index >= count or span <= 0:
                    continue
                texts = tuple(self._cell_demand_texts(cell.blocks))
                size, _fill = self._cell_type(cell, header=False, skin=None)
                horizontal_padding = 2 * pad
                if cell.padding_mm is not None:
                    horizontal_padding = cell.padding_mm[1] + cell.padding_mm[3]
                elif cell.css:
                    properties = dict(cell.css)
                    right = _css_length_px(properties.get("padding-right"), properties)
                    left = _css_length_px(properties.get("padding-left"), properties)
                    if right is not None and left is not None:
                        horizontal_padding = (
                            (right + left) * 25.4 / self.policy.css_px_per_inch
                        )
                demand = demand_for(
                    texts,
                    lambda text: self.fonts.width_pt(text, size) * 25.4 / 72.0,
                    padding_mm=horizontal_padding,
                )
                minimum = demand.maximum_mm if cell.nowrap else demand.minimum_mm
                declared = cell.width_mm
                if declared is None and cell.width_fraction is not None:
                    declared = table_width * cell.width_fraction
                minimum = max(minimum, cell.min_width_mm or 0.0, declared or 0.0)
                maximum = max(minimum, demand.maximum_mm, declared or 0.0)
                if cell.max_width_mm is not None:
                    maximum = max(minimum, min(maximum, cell.max_width_mm))
                demand = ColumnDemand(minimum, maximum)
                if span == 1:
                    current = demands[index]
                    demands[index] = ColumnDemand(
                        max(current.minimum_mm, demand.minimum_mm),
                        max(current.maximum_mm, demand.maximum_mm),
                    )
                else:
                    spanning_demands.append(SpanningDemand(index, span, demand))

        demands = apply_spanning_demands(demands, spanning_demands)
        return distribute(demands, table_width)

    @staticmethod
    def _fixed_column_widths(table, count: int, table_width: float):
        """CSS fixed table layout from the first row, never from content.

        The allocation model was proposed from recalled WebKit behaviour:
        first-row fixed/percentage widths establish columns, auto columns
        split what remains, and an all-specified row scales up to fill a
        Shape-A fixture below -- 135.152mm predicted against wkhtmltopdf's
        Keeping this separate from :meth:`_column_widths` is the regression
        boundary: an auto table never enters this branch.
        """
        if count <= 0:
            return ()
        declared: list[float | None] = [None] * count
        first = table.rows[0] if table.rows else None
        column = 0
        for cell in first.cells if first else ():
            span = max(1, min(cell.colspan, count - column))
            value = cell.width_mm
            if value is None and cell.width_fraction is not None:
                value = max(0.0, cell.width_fraction) * table_width
            if value is not None:
                each = max(0.0, value) / span
                for index in range(column, column + span):
                    declared[index] = each
            column += span
            if column >= count:
                break

        widths = [value or 0.0 for value in declared]
        automatic = [index for index, value in enumerate(declared) if value is None]
        used = sum(widths)
        if automatic:
            remaining = max(0.0, table_width - used)
            share = remaining / len(automatic)
            for index in automatic:
                widths[index] = share
        elif used > 0.0 and used < table_width:
            scale = table_width / used
            widths = [value * scale for value in widths]
        elif used == 0.0:
            widths = [table_width / count] * count
        return tuple(widths)

    def _first_baseline_mm(self, size_pt: float, step_mm: float) -> float:
        """How far below a block's top edge its first baseline sits.

        CSS stacks a line box of `line-height` around the text and centres
        the font's own height inside it, so the baseline lands at
        half-leading plus the ascent -- not a whole line-height down, which
        is what the planner did and is worth about 2mm on every block that
        begins with text.
        """
        ascent, descent = self.fonts.vertical_metrics()
        em = size_pt * 25.4 / 72.0
        half_leading = (step_mm - (ascent + descent) * em) / 2.0
        return half_leading + ascent * em

    def _cell_type(
        self, cell, *, header: bool, skin, total: bool = False
    ) -> tuple[float, tuple | None]:
        """The size and colour a table cell's text takes.

        Odoo puts the document title in a table cell, not in a block, so a
        planner that styles headings only on the block path prints an h2 at
        body size -- and, because that cell is right-aligned, 25mm from where
        it belongs. The role the parser recorded is the same one either way;
        this is where the cell path reads it.
        """
        p = self.policy
        roles = {
            block.role for block in cell.blocks
            if isinstance(block, Paragraph) and block.role
        }
        colour_roles = {
            block.colour_role for block in cell.blocks
            if isinstance(block, Paragraph) and block.colour_role
        }
        if cell.colour_role:
            colour_roles.add(cell.colour_role)
        size = max(
            (self._role_size_pt(role) for role in roles if role in _HEADING_SIZES_REM),
            default=cell.font_size_pt or p.font_size_pt,
        )
        fill = None
        if "title" in colour_roles or roles & _SEMANTIC_TITLE_ROLES:
            fill = self.theme.title_rgb
        elif "tagline" in colour_roles:
            fill = self.theme.tagline_rgb
        elif header and skin is not None and skin.header_text_rgb:
            fill = skin.header_text_rgb
        elif total and skin is not None and skin.total_row_text_rgb:
            fill = skin.total_row_text_rgb
        else:
            fill = self._text_rgb
        return (size, fill)

    @staticmethod
    def _rowspan_row_heights(
        rows, natural_heights, spanning_minimums, *, vertical_spacing_mm: float,
    ) -> tuple[float, ...]:
        """Apply spanning-cell minimums to the rows they actually span.

        CSS Tables 3 section 3.10 treats a rowspan cell's minimum height as a
        constraint on the combined height of the covered rows, not as the
        height of the row where the cell starts.  The latter made the
        e-invoice seller block add its four lines once *and* retain the two
        following rows, growing the A5 table enough to force its final nested
        row onto a second page.

        A deficit is shared by auto rows in the span (or the whole span when
        that deficit path; the e-invoice's three natural rows already exceed
        the spanning cell minimum.  Keeping it structural avoids turning
        that fact into a report-specific exception.
        """
        heights = [float(height) for height in natural_heights]
        for start, minimums in enumerate(spanning_minimums):
            for rowspan, minimum in minimums:
                stop = min(len(rows), start + max(1, int(rowspan)))
                if stop <= start:
                    continue
                spacing = vertical_spacing_mm * max(0, stop - start - 1)
                actual = sum(heights[start:stop]) + spacing
                deficit = max(0.0, float(minimum) - actual)
                if deficit == 0.0:
                    continue
                recipients = [
                    index for index in range(start, stop)
                    if rows[index].height_mm is None
                    and rows[index].height_fraction is None
                ] or list(range(start, stop))
                share = deficit / len(recipients)
                for index in recipients:
                    heights[index] += share
        return tuple(heights)

    @staticmethod
    def _table_row_heights(
        rows, natural_heights, *, table_grid_height_mm: float | None,
    ) -> tuple[float, ...]:
        """Resolve CSS row minimums against a table's used grid height.

        CSS Tables 3 section 3.10 defines two passes. Percentage-dependent
        descendants are natural/auto in the first pass; once the table has a
        used height, percentage row minimums form the reference sizes. Space
        beyond those references goes to auto rows first. This is why the
        badge's 30%/70% rows are derivable from its 153pt outer box without a
        special notion of a "layout table".
        """
        base = [
            max(float(natural), row.height_mm or 0.0)
            for row, natural in zip(rows, natural_heights)
        ]
        if table_grid_height_mm is None:
            return tuple(base)

        target = max(float(table_grid_height_mm), sum(base))
        reference = [
            max(
                base_height,
                target * row.height_fraction
                if row.height_fraction is not None else 0.0,
            )
            for row, base_height in zip(rows, base)
        ]
        base_sum = sum(base)
        reference_sum = sum(reference)
        if target <= reference_sum and reference_sum > base_sum:
            fraction = (target - base_sum) / (reference_sum - base_sum)
            return tuple(
                base_height + (reference_height - base_height) * fraction
                for base_height, reference_height in zip(base, reference)
            )

        heights = list(reference)
        extra = max(0.0, target - reference_sum)
        automatic = [
            index for index, row in enumerate(rows)
            if row.height_mm is None and row.height_fraction is None
        ]
        recipients = automatic or list(range(len(rows)))
        if recipients:
            share = extra / len(recipients)
            for index in recipients:
                heights[index] += share
        return tuple(heights)

    def _paragraph_runs(
        self, paragraph: Paragraph, *, page: int = 1, total: int = 1,
        total_strong_rgb=None,
    ):
        """A paragraph as styled runs, not one flattened string.

        `<a href>` and `<strong>` start partway through a line, so a planner
        that joins the children and draws one string per line can only style
        whole paragraphs. That is why the terms line printed entirely in body
        black when the stylesheet colours only the URL inside it.

        Each run is
        ``(text, bold, italic, link, fill, source_block_id, font_family)``; a
        line break arrives as a run whose text is ``"\n"``. The last field is
        provenance and never geometry: it rides along so a drawn TextRun can
        name the paragraph it came from, and it also keeps `_coalesce_runs`
        from merging two identically styled runs that came from different
        blocks.
        """
        runs = []
        for child in paragraph.children:
            if isinstance(child, Text):
                run_fill = child.fill_rgb
                if run_fill is None and child.colour_role == "total-strong":
                    # The compiled skin carries the selector result.  Testing
                    # the layout name here lost Boxed's equally specific
                    # white-on-primary total rule.
                    run_fill = (
                        total_strong_rgb
                        if total_strong_rgb is not None else self.theme.primary
                    )
                elif (
                    run_fill is None
                    and child.colour_role == "information-strong"
                ):
                    run_fill = self.theme.secondary
                elif run_fill is None and child.colour_role == "tagline":
                    # Inline taglines (notably Boxed/Bold footer `<strong>`)
                    # carry the same scoped company selector as a block-level
                    # tagline.  The run path must consume that role too.
                    run_fill = self.theme.tagline_rgb
                runs.append((
                    child.displayed, child.bold, child.italic, child.link,
                    run_fill, paragraph.source_block_id, child.font_family,
                ))
            elif isinstance(child, LineBreak):
                runs.append((
                    "\n", False, False, False, None, paragraph.source_block_id,
                    None,
                ))
            elif isinstance(child, PageNumber):
                runs.append((
                    str(page), False, False, False, child.fill_rgb,
                    paragraph.source_block_id, None,
                ))
            elif isinstance(child, TotalPages):
                runs.append((
                    str(total), False, False, False, child.fill_rgb,
                    paragraph.source_block_id, None,
                ))
        return runs

    def _wrap_runs(
        self, runs, width_mm: float, size_pt: float, *, letter_spacing_mm=0.0,
        preserve_collapsed_space=False,
    ):
        """Break styled runs into lines, keeping each run's styling.

        Wrapping happens between words across run boundaries, the way an
        inline formatting context does -- so a bold word at the end of a line
        wraps with the sentence rather than pulling its whole run down.
        """
        limit = width_mm * 72.0 / 25.4
        lines, current, used = [], [], 0.0
        for text, bold, italic, link, run_fill, block_id, family in runs:
            if text == "\n":
                lines.append(current)
                current, used = [], 0.0
                continue
            for word in self._wrap_tokens(text):
                if not word:
                    continue
                if word.isspace():
                    if current or preserve_collapsed_space:
                        current.append(
                            (" ", bold, italic, link, run_fill, block_id,
                             family)
                        )
                        used += self.fonts.width_pt(" ", size_pt)
                    continue
                word_pt = self.fonts.width_pt(word, size_pt)
                word_pt += max(0, len(word) - 1) * letter_spacing_mm * 72.0 / 25.4
                if current and used + word_pt > limit:
                    while current and current[-1][0] == " ":
                        current.pop()
                    lines.append(current)
                    current, used = [], 0.0
                current.append(
                    (word, bold, italic, link, run_fill, block_id, family))
                used += word_pt
        lines.append(current)
        return [
            self._coalesce_runs(line, preserve_collapsed_space)
            for line in lines
        ] or [[]]

    def _nowrap_lines(self, runs, *, preserve_collapsed_space=False):
        """Suppress soft wrapping while retaining authored line breaks."""
        lines, current = [], []
        for run in runs:
            if run[0] == "\n":
                lines.append(
                    self._coalesce_runs(current, preserve_collapsed_space)
                )
                current = []
            else:
                current.append(run)
        lines.append(self._coalesce_runs(current, preserve_collapsed_space))
        return lines

    @staticmethod
    def _wrap_tokens(text):
        """Yield soft-wrap units without treating a CJK phrase as one word.

        Unicode East Asian wide/fullwidth characters carry an ordinary
        browser line-break opportunity between characters. Python's
        whitespace split does not, which made Chinese text escape a box whose
        width otherwise matched the source.
        """
        token = []
        for char in text:
            if char.isspace() or unicodedata.east_asian_width(char) in {"W", "F"}:
                if token:
                    yield "".join(token)
                    token = []
                yield char
            else:
                token.append(char)
        if token:
            yield "".join(token)

    @staticmethod
    def _coalesce_runs(line, preserve_collapsed_space=False):
        """Rejoin neighbouring runs that share their styling.

        Wrapping works word by word, but drawing should not: a line of body
        text is one run again once the words are placed, so the output stays
        one TextRun per styled segment rather than one per word.
        """
        merged = []
        for text, bold, italic, link, run_fill, block_id, family in line:
            if merged and merged[-1][1:] == (
                bold, italic, link, run_fill, block_id, family,
            ):
                merged[-1] = (
                    merged[-1][0] + text, bold, italic, link, run_fill,
                    block_id, family,
                )
            else:
                merged.append(
                    (text, bold, italic, link, run_fill, block_id, family))
        if not preserve_collapsed_space:
            while merged and not merged[-1][0].strip():
                merged.pop()
            return [(text.rstrip() if index == len(merged) - 1 else text, *rest)
                    for index, (text, *rest) in enumerate(merged)]
        # An inline item that is itself a collapsed space sits at no line
        # boundary, so neither the pop nor the rstrip applies to it. The
        # planner strips a line's own leading and trailing whitespace; this
        # is not that. `tests/test_ignorable_whitespace.py` fixes the boundary.
        return merged

    def _line_width_mm(self, line, size_pt: float, *, letter_spacing_mm=0.0) -> float:
        text_width = sum(
            self.fonts.width_pt(text, size_pt, run[-1]) for text, *run in line
        ) * 25.4 / 72.0
        characters = sum(len(text) for text, *_ in line)
        return text_width + max(0, characters - 1) * letter_spacing_mm

    def _draw_runs(
        self, line, x_mm: float, y_mm: float, size_pt: float, *, fill=None,
        letter_spacing_mm=0.0,
    ):
        """Draw one line of styled runs, advancing across it."""
        out = []
        cursor = x_mm
        for index, (
            text, bold, _italic, link, declared_fill, block_id, family,
        ) in enumerate(line):
            run_fill = (
                declared_fill
                or (rgb(LINK_COLOUR, LINK_COLOUR) if link else fill)
            )
            drawn = self._runs(
                text, cursor, y_mm, size_pt, bold=bold, fill=run_fill,
                letter_spacing_mm=letter_spacing_mm,
                source_block_id=block_id, font_family=family,
            )
            out.extend(drawn)
            cursor += self.fonts.width_pt(text, size_pt, family) * 25.4 / 72.0
            cursor += max(0, len(text) - 1) * letter_spacing_mm
            if index < len(line) - 1 and text:
                cursor += letter_spacing_mm
        return out

    @staticmethod
    def _paragraph_bold(paragraph: Paragraph) -> bool:
        return any(isinstance(child, Text) and child.bold for child in paragraph.children)

    def _place_table(
        self, table: Table, pages: list[list], y: float, width: float,
        new_page, box_x: float | None = None, *,
        containing_height_mm: float | None = None,
    ) -> float:
        p = self.policy
        if not table.rows:
            return y

        rows = list(table.rows)
        cell_columns, column_count = table_column_placements(rows)
        origin = p.margin_left_mm if box_x is None else box_x
        pad = 0.0 if table.theme == "bare" else (
            p.table_cell_pad_mm * PX_PER_INCH / p.css_px_per_inch
            * (TABLE_SM_PAD_RATIO if table.compact else 1.0)
        )
        table_width = (
            table.width_mm if table.width_mm is not None
            else width * float(table.width_fraction) if table.width_fraction is not None
            else width
        )
        table_x = origin
        if table.align == "right":
            table_x = origin + (width - table_width)
        elif table.align == "center":
            table_x = origin + (width - table_width) / 2.0

        separate = table.border_collapse == "separate"
        horizontal_spacing, vertical_spacing = table.border_spacing_mm if separate else (0.0, 0.0)
        edge = max(0.0, table.border_width_mm)
        column_space = max(
            0.0,
            table_width - 2 * edge - horizontal_spacing * (column_count + 1),
        )
        weights = tuple(table.column_weights)
        if len(weights) != column_count:
            weights = tuple(1.0 for _ in range(column_count))
        col_widths = self._column_widths(table, column_count, column_space, pad, weights)
        grid_x = table_x + edge + horizontal_spacing
        # Needed by row_measure, which reads the header's text colour from it.
        #
        # `o_ignore_layout_styling` is how Odoo opts a table out of layout
        # chrome, and every rule in `report_tables.scss` is written
        # `:not(.o_ignore_layout_styling)` to honour it. The parser records
        # those as `meta`; they get no skin at all.
        table_theme = (
            replace(self.theme, table=table.theme)
            if table.theme is not None else self.theme
        )
        has_compiled_css = any(
            row.css or any(cell.css for cell in row.cells)
            for row in rows
        )
        if table.kind == "meta" or table.theme == "bare" or (
            table.borderless and table.theme == "unstyled"
        ):
            skin = TableSkin()
        elif table.theme == "unstyled" and has_compiled_css:
            # Generic Bootstrap tables carry their own selector-matched row
            # and cell edges.  Mapping `table-bordered` to Odoo's Boxed skin
            # is the defect this path replaces: the class asks for a grid in
            # inherited body colour, not Boxed's grey document-theme frame.
            skin = TableSkin()
        elif table.theme == "unstyled":
            # Native IR may deliberately request the generic table contract
            # without originating in an evaluated DOM.  Until its host can
            # supply compiled declarations, retain the source-derived legacy
            # fallback rather than silently erasing its rules.
            skin = TableSkin(
                header_rule=True,
                header_rule_pt=BLOCK_RULE_PT,
                row_rules=True,
                row_rule_pt=BLOCK_RULE_PT,
                rule_rgb=rgb(BLOCK_RULE_RGB, BLOCK_RULE_RGB),
            )
        else:
            skin = table_theme.table_skin(
                "totals" if table.kind == "totals" else "lines"
            )
        # How many leading rows are the header. This gives them the company
        # fill and their own text colour; it no longer makes them repeat,
        header_count = min(max(0, table.repeat_header_rows), len(table.rows))
        has_rowspans = any(
            cell.rowspan > 1 for row in rows for cell in row.cells
        )
        rowspan_grid = has_rowspans and edge > 0.0

        def css_edge(declarations, side):
            if not declarations:
                return None
            return _compiled_css_edge(
                declarations, side, px_per_inch=p.css_px_per_inch
            )

        direct_css_chrome = (
            table.theme in {"unstyled", "bare"} and has_compiled_css
        )

        def row_measure(row, *, row_index, header=False):
            height = 0.0
            wrapped_cells = []
            spanning_minimums = []
            row_bottom_edge = (
                css_edge(row.css, "bottom") if direct_css_chrome else None
            )
            for cell, column_index in zip(row.cells, cell_columns[row_index]):
                span_width = (
                    sum(col_widths[column_index : column_index + cell.colspan])
                    + horizontal_spacing * max(0, cell.colspan - 1)
                )
                # A cell's text is styled runs, like a block's: `<strong>`
                # inside one used to bold the whole cell, because the cell
                # path joined the children and drew one string per line.
                cell_runs = []
                for child in cell.blocks:
                    if not isinstance(child, Paragraph):
                        continue
                    if cell_runs:
                        # Same run contract as `_paragraph_runs`: text, bold,
                        # italic, link, declared fill, source block.  The
                        # separator owns no paint and no block of its own, so
                        # it cannot merge either neighbour into the other.
                        cell_runs.append(
                            (" ", False, False, False, None, None)
                        )
                    cell_runs.extend(self._paragraph_runs(
                        child,
                        total_strong_rgb=(
                            skin.total_row_text_rgb
                            if skin.total_row_text_rgb not in {
                                None, self._text_rgb,
                            }
                            else self.theme.primary
                        ),
                    ))
                size, fill = self._cell_type(
                    cell, header=header, skin=skin, total=row.role == "total"
                )
                css_padding = None
                if cell.css:
                    properties = dict(cell.css)
                    resolved = []
                    for side in ("top", "right", "bottom", "left"):
                        value = properties.get(f"padding-{side}")
                        pixels = _css_length_px(value, properties)
                        if pixels is None:
                            resolved = []
                            break
                        resolved.append(pixels * 25.4 / p.css_px_per_inch)
                    if resolved:
                        css_padding = tuple(resolved)
                padding = cell.padding_mm or css_padding or (pad, pad, pad, pad)
                pad_top, pad_right, pad_bottom, pad_left = padding
                content_width = max(0.1, span_width - pad_left - pad_right)
                # One Paragraph/Image keeps the established table fast path:
                # tables. Multiple siblings are a CSS block flow, not one
                # text stream separated by invented spaces. Sending them
                # through `_flow` preserves their boundaries, facing margins,
                # line-height and semantic paint while the scratch page keeps
                # the row atomic.
                flowed = len(cell.blocks) > 1 or any(
                    not isinstance(child, (Paragraph, Image))
                    for child in cell.blocks
                )
                flow_blocks = (
                    _inherit_cell_style(cell.blocks, cell)
                    if flowed else cell.blocks
                )
                flow_height = 0.0
                cell_height = 0.0
                own_height = 0.0
                if flowed:
                    # A cell is a bounded flow region, not merely a text
                    # string.  Measure its child blocks through the same
                    # planner used by body/grid/horizontal regions, with
                    # pagination disabled so the containing row stays atomic.
                    was_in_band = self._in_band
                    was_measuring_intrinsic = self._measuring_intrinsic
                    self._in_band = True
                    self._measuring_intrinsic = True
                    try:
                        flow_bottom = self._flow(
                            flow_blocks, 0.0, 0.0, content_width,
                            [[]], lambda: None, inherited_align=cell.align,
                        )
                    finally:
                        self._in_band = was_in_band
                        self._measuring_intrinsic = was_measuring_intrinsic
                    flow_height = max(0.0, -flow_bottom)
                    cell_height = max(
                        cell_height, flow_height + pad_top + pad_bottom
                    )
                if cell.line_height_mm is not None:
                    step = cell.line_height_mm
                elif cell.line_height_ratio is not None:
                    step = self._line_advance_mm(size, cell.line_height_ratio)
                else:
                    roles = {
                        child.role
                        for child in cell.blocks
                        if isinstance(child, Paragraph) and child.role
                    }
                    if roles & _TITLE_ROLES:
                        step = self._line_advance_mm(size, HEADING_LINE_HEIGHT_RATIO)
                    elif cell.font_size_pt is not None:
                        step = self._line_advance_mm(size, LINE_HEIGHT_RATIO)
                    elif table.theme == "unstyled":
                        # A generic Bootstrap table owns an ordinary 1.5
                        # also carries its cell border; reusing it for the
                        # unthemed `.table-sm` in base module references adds
                        # 0.235mm to every row.
                        step = self._line_advance_mm(size, LINE_HEIGHT_RATIO)
                    elif skin.cell_borders or skin.row_rules or table.kind == "totals":
                        # The source-derived bordered line box includes the
                        # report bundle's 1px row rule, so it is right only
                        # where that rule is actually drawn. `row_rules` is a
                        # real edge too; limiting this branch to a full cell
                        # advances at 41px.
                        #
                        # The totals table keeps it regardless. `LINE_HEIGHT_MM`
                        # rows are not on a single pitch at all -- 24.63pt then
                        # 27.21pt on the same invoice, because those rows carry
                        # bold and differently sized runs. Nothing here has been
                        # doing it anyway moved the invoice's totals from -2px
                        # to -13px.
                        step = p.line_height_mm
                    else:
                        # A table that draws no cell border must not be
                        # difference is exactly the authored border, and over
                        # 28 rows it accumulates to 6.2mm -- enough to push a
                        # row off and displace every later row by one whole
                        # row.
                        step = self._line_advance_mm(size, LINE_HEIGHT_RATIO)
                # `white-space: nowrap` means the text does not wrap, full
                # stop. Sizing the column to fit it and then wrapping anyway
                # leaves the result at the mercy of a rounding error in the
                # font metrics -- which is exactly how "5%" still broke in
                # two on the deployment after the column was made wide
                # enough for it locally.
                wrapped = [] if flowed or not cell_runs else (
                    [self._coalesce_runs(cell_runs)] if cell.nowrap
                    else self._wrap_runs(cell_runs, content_width, size)
                )
                if not flowed:
                    cell_bottom_edge = (
                        css_edge(cell.css, "bottom")
                        if direct_css_chrome else None
                    )
                    border_height = max(
                        row_bottom_edge[0] if row_bottom_edge else 0.0,
                        cell_bottom_edge[0] if cell_bottom_edge else 0.0,
                    ) * 25.4 / 72.0
                    # The block's own bottom margin, which has nowhere to
                    # escape to. The table-cell contract says a cell never
                    # collapses with its children, and
                    # `handleAfterSideOfBlock` (`:1835-1838`) then adds the
                    # held margin to the box's height. The quirks branch of
                    # that condition needs `document()->inQuirksMode()`, and
                    # these documents carry a `<!DOCTYPE html>`.
                    #
                    # `_flow` already keeps it for a cell with several
                    # blocks; this is the same fact on the single-block fast
                    # zero for an ordinary line-table cell, whose paragraph
                    # states no bottom margin -- what it recovers is
                    # bubble's informations cell, one `Paragraph` carrying
                    # the `mb-4` of the `<div class="address row mb-4">` it
                    # was flattened from.
                    trailing_margin = self._cell_trailing_margin_mm(cell)
                    # `logicalHeightWithoutIntrinsicPadding`
                    # in the table-cell contract: the cell's own laid-out
                    # height -- authored padding and content, before the row
                    # stretches it. Computed here, where its terms exist, and
                    # carried rather than rebuilt in the draw pass.
                    own_height = (
                        len(wrapped) * step + pad_top + pad_bottom
                        + border_height + trailing_margin
                    )
                    cell_height = max(cell_height, own_height)
                # Odoo puts the company logo in a header cell in several
                # layouts, so a cell that only measures its text loses it.
                images = [] if flowed else self._cell_images(cell, content_width)
                for _image, _width, image_height in images:
                    cell_height = max(
                        cell_height, image_height + pad_top + pad_bottom
                    )
                if cell.rowspan > 1:
                    spanning_minimums.append((cell.rowspan, cell_height))
                else:
                    height = max(height, cell_height)
                wrapped_cells.append(
                    (
                        cell, column_index, span_width, wrapped, images, size, fill, step,
                        padding, flowed, flow_height, flow_blocks, own_height,
                    )
                )
            return height, wrapped_cells, spanning_minimums

        # The skin already knows about `table-borderless`: it is compiled
        # from probes that carry the class, and the cascade decided there
        # that `.o_table_boxed … td` outranks `.table-borderless td`.
        # Re-applying it here overrode that -- and the parser had grown a
        # hack forcing `borderless = False` on line tables to compensate.
        borders = skin.cell_borders

        def draw_row(row, row_height, cells, current_y, *, index=0, header=False):
            current_y -= row_height
            # Fills go down first so text and rules land on top of them.
            total_row = row.role == "total"
            fill = skin.header_fill if header else None
            if fill is None and total_row:
                fill = skin.total_row_fill
            if fill is None and row.role == "taxes":
                fill = skin.taxes_row_fill
            row_group = row.group or ("thead" if header else "tbody")
            group_index = row.group_index
            if group_index is None and not header:
                # Native IR has one implicit tbody after its repeated header.
                # Evaluated HTML carries the exact group-local child index.
                group_index = index - header_count + 1
            if (
                fill is None
                and skin.stripe_fill
                and row_group == "tbody"
                and group_index is not None
                and group_index % 2 == 1
            ):
                fill = skin.stripe_fill
            if fill:
                fill_rgb, fill_alpha = _fill_parts(fill)
                pages[-1].append(Rect(
                    table_x, current_y, table_width, row_height,
                    stroke=False, fill=True, fill_rgb=fill_rgb,
                    fill_alpha=fill_alpha,
                    # The header's fill follows the frame's top corners, or
                    # it squares off outside a rounded edge.
                    corner_radii_mm=skin.header_corners_mm if header else None,
                ))
            if direct_css_chrome:
                # Bootstrap stripes are a full-cell inset shadow rather than
                # a row background. Preserve that scope: colspan cells and
                # mixed overrides may legitimately resolve differently.
                for cell_data in cells:
                    cell, column_index, span_width = cell_data[:3]
                    cell_fill = _compiled_inset_fill(cell.css)
                    if cell_fill is None:
                        continue
                    fill_rgb, fill_alpha = cell_fill
                    cursor_x = (
                        grid_x
                        + sum(col_widths[:column_index])
                        + horizontal_spacing * column_index
                    )
                    pages[-1].append(Rect(
                        cursor_x, current_y, span_width, row_height,
                        stroke=False, fill=True, fill_rgb=fill_rgb,
                        fill_alpha=fill_alpha,
                    ))
            if edge > 0.0 and not rowspan_grid:
                # HTML's legacy `border` attribute is a two-scope
                # presentational hint in WebKit: the outer bevel is dark,
                # while boundaries between cells are mid-grey.  Draw only
                # the internal horizontal boundary here; close_frame() owns
                # the outer edge so the two cannot be flattened together.
                if index + 1 < len(rows):
                    pages[-1].append(Line(
                        table_x, current_y, table_x + table_width, current_y,
                        width_pt=edge * 72.0 / 25.4,
                        stroke_rgb=LEGACY_TABLE_INNER_RGB,
                    ))
            elif skin.row_rules and not header:
                pages[-1].append(Line(
                    table_x, current_y, table_x + table_width, current_y,
                    width_pt=skin.row_rule_pt,
                    stroke_rgb=skin.row_rule_rgb or skin.rule_rgb,
                ))
            elif (
                not borders and not header and skin.bottom_rule
                and skin.bottom_rule_pt
                and (
                    index + 1 == len(rows)
                    or (rows[index + 1].group or "tbody") != row_group
                )
            ):
                pages[-1].append(Line(
                    table_x, current_y, table_x + table_width, current_y,
                    width_pt=skin.bottom_rule_pt, stroke_rgb=skin.rule_rgb,
                ))
            elif borders and not header:
                # Boxed themes state a bottom border on each body cell except
                # those in the last row of their row group.  A stroked row
                # rectangle looks close, but it colours every edge alike and
                # swallows the independently coloured vertical rules when
                # visible regions are canonicalised.
                next_row = rows[index + 1] if index + 1 < len(rows) else None
                next_group = (
                    next_row.group or "tbody" if next_row is not None else None
                )
                if next_group == row_group and skin.row_rule_pt:
                    pages[-1].append(Line(
                        table_x, current_y, table_x + table_width, current_y,
                        width_pt=skin.row_rule_pt,
                        stroke_rgb=skin.row_rule_rgb or skin.rule_rgb,
                    ))
                elif (
                    skin.bottom_rule and skin.bottom_rule_pt
                    and not skin.frame_rule
                ):
                    pages[-1].append(Line(
                        table_x, current_y, table_x + table_width, current_y,
                        width_pt=skin.bottom_rule_pt,
                        stroke_rgb=skin.row_rule_rgb or skin.rule_rgb,
                    ))
            if total_row and skin.total_row_rule_pt:
                # Every layout rules off the total from the subtotals above it.
                pages[-1].append(Line(
                    table_x, current_y + row_height,
                    table_x + table_width, current_y + row_height,
                    width_pt=skin.total_row_rule_pt, stroke_rgb=skin.rule_rgb,
                ))
            if header and skin.header_rule:
                pages[-1].append(Line(
                    table_x, current_y, table_x + table_width, current_y,
                    width_pt=skin.header_rule_pt,
                    stroke_rgb=skin.header_rule_rgb or skin.rule_rgb,
                ))
            if header:
                # A rule *above* the header is its own declaration, not a
                # side effect of a thick one below: `bold` rules only the top
                # edge, so inferring the top from the bottom's weight drew it
                # in the one layout that has no bottom rule at all.
                top_pt = skin.header_top_rule_pt or (
                    skin.header_rule_pt if skin.header_rule and skin.header_rule_pt > 1.5 else 0.0
                )
                if top_pt:
                    pages[-1].append(Line(
                        table_x, current_y + row_height,
                        table_x + table_width, current_y + row_height,
                        width_pt=top_pt, stroke_rgb=skin.rule_rgb,
                    ))
            if direct_css_chrome:
                row_top = css_edge(row.css, "top")
                row_bottom = css_edge(row.css, "bottom")
                if index == 0 and row_top:
                    pages[-1].append(Line(
                        table_x, current_y + row_height,
                        table_x + table_width, current_y + row_height,
                        width_pt=row_top[0], stroke_rgb=row_top[1],
                    ))
                if row_bottom:
                    pages[-1].append(Line(
                        table_x, current_y, table_x + table_width, current_y,
                        width_pt=row_bottom[0], stroke_rgb=row_bottom[1],
                    ))
            cell_borders = borders or edge > 0.0
            for (
                cell, column_index, span_width, wrapped, images, size, fill, step, padding,
                flowed, flow_height, flow_blocks, own_height,
            ) in cells:
                # CSS visibility suppresses the cell and every descendant,
                # but row_measure deliberately saw the same blocks above so
                # intrinsic widths, row height, and pagination remain intact.
                if not cell.visible:
                    continue
                cursor_x = (
                    grid_x
                    + sum(col_widths[:column_index])
                    + horizontal_spacing * column_index
                )
                pad_top, pad_right, pad_bottom, pad_left = padding
                span_rows = min(cell.rowspan, len(row_heights) - index)
                cell_height = (
                    sum(row_heights[index:index + span_rows])
                    + vertical_spacing * max(0, span_rows - 1)
                )
                cell_bottom = current_y - max(0.0, cell_height - row_height)
                if cell.role == "price-total" and skin.price_total_fill:
                    fill_rgb, fill_alpha = _fill_parts(skin.price_total_fill)
                    pages[-1].append(Rect(
                        cursor_x, cell_bottom, span_width, cell_height,
                        stroke=False, fill=True, fill_rgb=fill_rgb,
                        fill_alpha=fill_alpha,
                    ))
                direct_vertical_chrome = False
                if direct_css_chrome:
                    # Collapsed borders are emitted once: the first cell owns
                    # the outer left edge, every cell owns its right and
                    # bottom edges. Horizontal row edges above take priority
                    # for `.table-bordered`, whose cells explicitly zero
                    # their own top/bottom widths.
                    left_edge = css_edge(cell.css, "left")
                    right_edge = css_edge(cell.css, "right")
                    bottom_edge = css_edge(cell.css, "bottom")
                    direct_vertical_chrome = bool(left_edge or right_edge)
                    if column_index == 0 and left_edge:
                        pages[-1].append(Line(
                            cursor_x, cell_bottom,
                            cursor_x, cell_bottom + cell_height,
                            width_pt=left_edge[0], stroke_rgb=left_edge[1],
                        ))
                    if right_edge:
                        right_x = cursor_x + span_width
                        pages[-1].append(Line(
                            right_x, cell_bottom,
                            right_x, cell_bottom + cell_height,
                            width_pt=right_edge[0], stroke_rgb=right_edge[1],
                        ))
                    if bottom_edge:
                        pages[-1].append(Line(
                            cursor_x, cell_bottom,
                            cursor_x + span_width, cell_bottom,
                            width_pt=bottom_edge[0], stroke_rgb=bottom_edge[1],
                        ))
                if edge > 0.0:
                    cell_rule_pt = edge * 72.0 / 25.4
                    cell_rule_rgb = LEGACY_TABLE_INNER_RGB
                elif header:
                    cell_rule_pt = skin.header_vertical_rule_pt
                    cell_rule_rgb = skin.header_vertical_rule_rgb or skin.rule_rgb
                else:
                    cell_rule_pt = skin.vertical_rule_pt
                    cell_rule_rgb = skin.vertical_rule_rgb or skin.rule_rgb
                if rowspan_grid:
                    # A full-width row rectangle draws a horizontal rule
                    # through cells that continue into following rows. Draw
                    # the actual *internal* cell edges instead; the dark
                    # legacy outer frame is added once after the grid closes.
                    # Painting the top/right/bottom perimeter here as the
                    # inner grey as well leaves two different colours on the
                    # same physical edge -- three spurious paint marks in the
                    right_x = cursor_x + span_width
                    if index + cell.rowspan < len(rows):
                        pages[-1].append(Line(
                            cursor_x, cell_bottom, right_x, cell_bottom,
                            width_pt=cell_rule_pt, stroke_rgb=cell_rule_rgb,
                        ))
                    if column_index + cell.colspan < column_count:
                        pages[-1].append(Line(
                            right_x, cell_bottom,
                            right_x, cell_bottom + cell_height,
                            width_pt=cell_rule_pt, stroke_rgb=cell_rule_rgb,
                        ))
                elif not direct_vertical_chrome and (authored_edges := [
                    (side, side_offset)
                    for side, side_offset in (
                        (cell.border[3], 0.0),
                        (cell.border[1], span_width),
                    )
                    if side.width_pt and side.style != "none"
                ]):
                    # The cell's own borders, as the stylesheet divided them
                    # between the table's boxes: `.table-bordered` puts
                    # `border-width: 1px 0` on the row and `0 1px` on the
                    # cell, so these are the cell's edges and the row keeps
                    # the ones above and below it.
                    #
                    # `border-collapse: collapse` merges a cell's right edge
                    # with the next cell's left, so an internal boundary is
                    # painted once -- by the cell to its right -- and a
                    # cell's own right edge is painted only where the table
                    # ends. Painting both would put two marks on one edge.
                    #
                    # A border with no declared colour is `currentColor`,
                    # which is this cell's text colour: the report bundle
                    # states these colours as `var(--table-border-color)`,
                    # the renderer drops what it cannot resolve, and the
                    # paints this grid in the body colour.
                    last_column = column_index + cell.colspan >= column_count
                    for side, side_offset in authored_edges:
                        if side_offset and not last_column:
                            continue
                        side_x = cursor_x + side_offset
                        pages[-1].append(Line(
                            side_x, cell_bottom, side_x, cell_bottom + cell_height,
                            width_pt=side.width_pt,
                            stroke_rgb=side.colour or fill or self._text_rgb,
                        ))
                elif (
                    not direct_vertical_chrome
                    and cell_borders
                    and cursor_x > grid_x
                    and cell_rule_pt
                ):
                    pages[-1].append(Line(
                        cursor_x, cell_bottom, cursor_x, cell_bottom + cell_height,
                        width_pt=cell_rule_pt, stroke_rgb=cell_rule_rgb,
                    ))
                image_y = cell_bottom + cell_height - pad_top
                if flowed:
                    flow_top = image_y
                    align = cell.valign or ("middle" if header else "top")
                    if align == "bottom":
                        flow_top = cell_bottom + pad_bottom + flow_height
                    elif align == "middle":
                        flow_top = cell_bottom + (cell_height + flow_height) / 2.0
                    was_in_band = self._in_band
                    self._in_band = True
                    try:
                        self._flow(
                            flow_blocks, cursor_x + pad_left, flow_top,
                            max(0.1, span_width - pad_left - pad_right),
                            pages, lambda: None,
                            containing_height_mm=max(
                                0.0, cell_height - pad_top - pad_bottom
                            ),
                            inherited_align=cell.align,
                        )
                    finally:
                        self._in_band = was_in_band
                for image, image_width, image_height in images:
                    image_y -= image_height
                    image_x = cursor_x + pad_left
                    if cell.align == "right":
                        image_x = cursor_x + span_width - pad_right - image_width
                    elif cell.align == "center":
                        image_x = cursor_x + (span_width - image_width) / 2.0
                    pages[-1].extend(self._draw_image(
                        image.src, image_x, image_y, image_width, image_height,
                        preserve_aspect_ratio=image.object_fit != "fill",
                    ))
                # Vertical alignment. `table.table td` is `top` and `th` is
                # `middle` in the report stylesheet, and the `.align-*`
                # utilities override both. It is load-bearing rather than
                # cosmetic: Odoo puts the document title in an `align-bottom`
                # cell beside the customer address, so a planner that draws
                # every cell from the top prints the title through the
                # address instead of under it.
                text_top = image_y if images else cell_bottom + cell_height - pad_top
                if not images:
                    block_height = len(wrapped) * step
                    align = cell.valign or ("middle" if header else "top")
                    # The table-cell geometry contract stretches a cell by
                    # adding *intrinsic* padding around the height the
                    # cell laid itself out at, and `vertical-align` only says
                    # how that spare is split:
                    #
                    #     logicalHeightWithoutIntrinsicPadding             :632
                    #     TOP     intrinsicPaddingBefore = 0               :646
                    #     MIDDLE  = (rHeight - height) / 2                 :649
                    #     BOTTOM  = rHeight - height                       :652
                    #     intrinsicPaddingAfter = rHeight - height - before :658
                    #
                    # So the spare is taken against the cell's *own* height,
                    # not against its content: authored padding is inside
                    # that height and is never what is split. Halving
                    # `cell_height + content_height` only agreed with this
                    # when `pad_top` happened to equal `pad_bottom`.
                    content_height = (
                        block_height + self._cell_trailing_margin_mm(cell)
                    )
                    # Two separable things, as in `_pack_offsets`.
                    #
                    # *How* the spare becomes a whole pixel is the canonical
                    # boundary: `rHeight` and
                    # `logicalHeightWithoutIntrinsicPadding` are `int` used
                    # values out of `RenderBox`, and this planner has
                    # millimetre estimates of them. The snap below is that
                    # estimator, not the renderer's arithmetic -- see the
                    # integer-used-values entry in `docs/capability-gaps.md`.
                    #
                    # *What happens once it is a whole pixel* is not a
                    # boundary at all, and is implemented: `:649` is C
                    # integer division, so `intrinsicPaddingBefore`
                    # truncates and `:658` gives the remainder to
                    # `intrinsicPaddingAfter`. A 51px spare is 25 before and
                    # **26** after -- and after is the one this reads,
                    # because it places the text up from the cell's floor.
                    #
                    # `own_height` carries `border_height`, this engine's
                    # one-sided read of a collapsed bottom edge rather than
                    # the renderer's `borderBefore() + borderAfter()`. It
                    # sits on both sides of the subtraction, so it cancels
                    # and invents no spare.
                    per_px = 25.4 / self.policy.css_px_per_inch
                    spare = max(
                        0, math.floor((cell_height - own_height) / per_px + 0.5)
                    )
                    intrinsic_after = (spare - spare // 2) * per_px
                    if align == "bottom":
                        text_top = cell_bottom + pad_bottom + content_height
                    elif align == "middle":
                        text_top = (
                            cell_bottom + intrinsic_after
                            + pad_bottom + content_height
                        )
                text_y = text_top - self._first_baseline_mm(size, step)
                for line in wrapped:
                    if cell.align in {"right", "center"}:
                        text_w = self._line_width_mm(line, size)
                        spare = span_width - pad_right - text_w
                        text_x = cursor_x + (spare if cell.align == "right"
                                             else (span_width - text_w) / 2.0)
                    else:
                        text_x = cursor_x + pad_left
                    pages[-1].extend(self._draw_runs(line, text_x, text_y, size, fill=fill))
                    text_y -= step
            return current_y

        measured_rows = [
            (row, *row_measure(
                row,
                row_index=index,
                header=(row.group == "thead" or index < header_count),
            ))
            for index, row in enumerate(rows)
        ]
        declared_table_height = table.height_mm
        if declared_table_height is None and table.height_fraction is not None:
            if containing_height_mm is None:
                if not self._measuring_intrinsic:
                    self._warn_once(
                        "percentage table height is unresolved; using natural height"
                    )
            else:
                declared_table_height = containing_height_mm * table.height_fraction
        non_row_height = 2 * edge + vertical_spacing * (len(rows) + 1)
        natural_row_heights = self._rowspan_row_heights(
            rows,
            [row_data[1] for row_data in measured_rows],
            [row_data[3] for row_data in measured_rows],
            vertical_spacing_mm=vertical_spacing,
        )
        natural_table_height = non_row_height + sum(
            natural_row_heights
        )
        used_table_height = (
            max(natural_table_height, declared_table_height)
            if declared_table_height is not None else natural_table_height
        )
        row_heights = self._table_row_heights(
            rows,
            natural_row_heights,
            table_grid_height_mm=max(0.0, used_table_height - non_row_height),
        )
        # `boxed` and `boxed-rounded` draw an outer frame in a generated
        # `::before` that is inset to the table's edges. It is a separate
        # thing from the cell grid -- it survives `table-borderless` and it
        # is what rounds the corners -- and nothing was drawing it.
        frame_top = y
        frame_page = len(pages)

        def close_frame(bottom: float) -> None:
            if len(pages) != frame_page:
                return
            if skin.frame_rule:
                pages[-1].append(Rect(
                    table_x, bottom, table_width, frame_top - bottom,
                    stroke=True, fill=False,
                    line_width_pt=skin.frame_rule_pt,
                    stroke_rgb=skin.frame_rgb,
                    corner_radii_mm=skin.frame_corners_mm,
                ))
            if edge > 0.0:
                pages[-1].append(Rect(
                    table_x, bottom, table_width, frame_top - bottom,
                    stroke=True, fill=False,
                    line_width_pt=edge * 72.0 / 25.4,
                    stroke_rgb=LEGACY_TABLE_OUTER_RGB,
                ))

        if vertical_spacing:
            y -= vertical_spacing
        for row_index, (row, _natural_height, cells, _spans) in enumerate(measured_rows):
            if row_index and vertical_spacing:
                y -= vertical_spacing
            # `header=` decides the cell's text colour, and the measure pass
            # is where that is computed -- so leaving it off here drew the
            # header row's text in body black on the company's fill, while
            # the repeated-header pass (which does pass it) was white.
            row_height = row_heights[row_index]
            if row_height > self._top_y - self._bottom_limit:
                self._warn_once(
                    "atomic table row is taller than one physical page; drawing without splitting"
                )

            if not self._in_band and y - row_height < self._bottom_limit:
                new_page()
                y = p.height_mm - p.margin_top_mm
                # A continuation page does not get the column header again.
                # CSS repeats `<thead>` across page breaks and modern browsers
                # do it, but wkhtmltopdf's WebKit does not, and it is the
                # opens on the next line item where this engine drew the header
                # a second time. Each repeat cost about 42px, and two of them
                # pushed the totals 85px down and spilled the terms line onto a
                #
                # `repeat_header_rows` keeps its other meaning: how many
                # leading rows are the header, which is what gives them the
                # company fill and their own text colour.
                if not matches_oracle("thead_never_repeats"):
                    for h in range(header_count):
                        h_row, _h_natural, h_cells, _h_spans = measured_rows[h]
                        y = draw_row(
                            h_row, row_heights[h], h_cells, y, index=h, header=True
                        )

            y = draw_row(
                row, row_height, cells, y, index=row_index,
                header=(row.group == "thead" or row_index < header_count),
            )

        if vertical_spacing:
            y -= vertical_spacing

        close_frame(y)
        return y

    @staticmethod
    def _paragraph_text(paragraph: Paragraph, *, page: int = 1, total: int = 1) -> str:
        parts = []
        for child in paragraph.children:
            if isinstance(child, Text):
                parts.append(child.displayed)
            elif isinstance(child, LineBreak):
                parts.append("\n")
            elif isinstance(child, PageNumber):
                parts.append(str(page))
            elif isinstance(child, TotalPages):
                parts.append(str(total))
        return "".join(parts).strip()

    def _wrap_text(self, text: str, width_mm: float, size_pt: float | None = None) -> tuple[str, ...]:
        if not text:
            return ("",)
        size_pt = self.policy.font_size_pt if size_pt is None else size_pt
        max_pt = width_mm * 72.0 / 25.4
        output = []
        for source_line in text.splitlines() or [text]:
            words = source_line.split()
            if not words:
                output.append("")
                continue
            current = ""
            for word in words:
                candidate = word if not current else f"{current} {word}"
                if not current or self.fonts.width_pt(candidate, size_pt) <= max_pt:
                    current = candidate
                else:
                    output.extend(self._break_token(current, max_pt))
                    current = word
            output.extend(self._break_token(current, max_pt))
        return tuple(output)

    def _break_token(self, token: str, max_pt: float) -> list[str]:
        from reportlab.pdfbase.pdfmetrics import stringWidth

        if stringWidth(token, self.font_name, self.policy.font_size_pt) <= max_pt:
            return [token]
        output = []
        current = ""
        for char in token:
            candidate = current + char
            if current and stringWidth(candidate, self.font_name, self.policy.font_size_pt) > max_pt:
                output.append(current)
                current = char
            else:
                current = candidate
        if current:
            output.append(current)
        return output
