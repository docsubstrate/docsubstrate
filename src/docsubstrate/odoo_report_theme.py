"""Table and accent chrome for the stock Odoo report layouts.

The layout picker in Odoo (Settings, "Configure Document Layout") writes one
of ``web.external_layout_{standard,boxed,bold,striped,bubble,wave,folder}``
onto the company, and a separate setting picks the table style.  A renderer
that ignores either prints the right facts in the wrong document.

**Where these numbers come from.**  Odoo states all of this in CSS, in the
the public common report stylesheet used by the Odoo 19 input contract. That stylesheet has 3,004
rules, of which 269 are report chrome, and those flatten to the eleven
distinct answers in :data:`TABLE_SKINS`.  So the cascade that reads it --
the stylesheet compiler -- runs offline, in
``tools/derive_table_skins.py``, and what ships is its output.  Carrying a CSS
engine into every PDF to re-derive eleven constants would cost a 450 KB parse,
2.8 MB per worker and a runtime dependency, and buy nothing this table does
not already say.

That trade is only safe because the table is *checked*: running the tool
against a deployment's own bundle reports any skin that has drifted.  A table
nobody re-derives is folklore, which is the same standard
the profile metadata holds the geometry constants to.

Colours are not in the table.  They arrive from the company, and Odoo mixes
them in through a second generated stylesheet whose shape is fixed --
``web.styles_company_report``, a QWeb template with four inputs.
:func:`company_overlay` is that template, in Python.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

# Keep theme constants independent of the generated selector profile.  This
# lets the public profile generator import the cascade compiler from an
# archive where the generated profile is intentionally absent.
PX_PER_INCH = 112.5
MM_PER_PX = 25.4 / PX_PER_INCH
MM_PER_REM = 16.0 * MM_PER_PX
BUBBLE_CIRCLE_POSITION_PX = (-870.0, -450.0)

#: What ``web.styles_company_report`` falls back to when a company has set no
#: colour. Not Odoo's brand purple: ``res.company.primary_color`` is a plain
#: ``Char`` with no default, and the report template supplies its own.
DEFAULT_PRIMARY = "#212529"
DEFAULT_SECONDARY = "#212529"

LAYOUTS = ("standard", "boxed", "bold", "striped", "bubble", "wave", "folder")
#: The picker labels "standard" as Light.
LAYOUT_LABELS = {"standard": "Light"}

#: Table styles, which are a *separate* setting from the document layout.
#: ``boxed-rounded`` has no matching layout, which is the clearest sign the
#: two axes are independent.
TABLE_THEMES = (
    "standard", "boxed", "boxed-rounded", "bold", "striped",
    "bubble", "wave", "folder",
)
TABLE_KINDS = ("lines", "totals")

#: Which table style each layout template writes onto the document body.
#: Three of the seven do not use their own name -- Bubble is boxed-rounded,
#: Wave and Folder are striped -- which is why falling back to the layout
#: name drew the wrong table whenever the HTML did not say.
LAYOUT_TABLE_STYLE = {
    "standard": "standard",
    "boxed": "boxed",
    "bold": "bold",
    "striped": "striped",
    "bubble": "boxed-rounded",
    "wave": "striped",
    "folder": "striped",
}


def presentation_values(
    *,
    layout=None,
    table_theme=None,
    primary_color=None,
    secondary_color=None,
    company_class=None,
):
    """The presentation keys :meth:`ReportTheme.from_values` reads.

    One contract, so a host that builds a document from a record and a host
    that converts evaluated QWeb HTML describe their formatting the same
    way. They did not: the record path passed the layout under `odoo_layout`
    and no colours at all, so every document it produced came out on the
    default theme -- unstyled, and for a reason nothing reported.
    """
    values = {
        "layout": layout or "",
        "table_theme": table_theme or "",
        "primary_color": primary_color or "",
        "secondary_color": secondary_color or "",
        "company_class": company_class or "",
    }
    return {key: value for key, value in values.items() if value}


def rgb(value: str | None, fallback: str) -> tuple[float, float, float]:
    """`#rrggbb` (or `rrggbb`) to the 0..1 triple ReportLab wants."""
    text = (value or "").strip() or fallback
    if not text.startswith("#"):
        text = f"#{text}"
    text = text[1:]
    if len(text) == 3:
        text = "".join(char * 2 for char in text)
    if len(text) != 6:
        text = fallback[1:]
    return tuple(int(text[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def hex_rgb(text: str) -> tuple[float, float, float]:
    """`#111827` to a 0..1 triple.

    The table below is written in hex because that is how the stylesheet
    writes it, and a table nobody can read against its source is a table
    nobody will check.
    """
    value = text.lstrip("#")
    return tuple(int(value[index : index + 2], 16) / 255.0 for index in (0, 2, 4))


@dataclass(frozen=True, slots=True)
class Fill:
    """An uncomposited CSS fill, retaining authored alpha."""

    rgb: tuple[float, float, float]
    alpha: float = 1.0

    def __iter__(self):
        return iter(self.rgb)

    def __len__(self):
        return len(self.rgb)

    def __getitem__(self, index):
        return self.rgb[index]


def as_fill(value: Fill | tuple[float, float, float] | None) -> Fill | None:
    if value is None or isinstance(value, Fill):
        return value
    if isinstance(value, tuple) and len(value) == 3:
        return Fill(value)
    raise TypeError(f"expected Fill, rgb triple, or None; got {type(value)!r}")


_FILL_FIELDS = ("header_fill", "stripe_fill", "total_row_fill", "price_total_fill", "taxes_row_fill")


@dataclass(frozen=True, slots=True)
class TableSkin:
    """How one layout draws a table.

    ``cell_borders`` is the full grid; the stock layouts almost never want it,
    which is why an engine that draws it unconditionally looks wrong on every
    one of them.

    The fields below ``rule_rgb`` exist because the stylesheet distinguishes
    things the hand-carved skins could not: ``bold`` rules its header on the
    *top* edge rather than the bottom, ``boxed`` draws an outer frame in a
    generated ``::before`` box that is separate from its cell grid, and a
    company stylesheet can set the header's text colour along with its fill.
    """

    cell_borders: bool = False
    header_rule: bool = True
    header_rule_pt: float = 0.8
    #: Header bottom and inter-column rules are different declarations in
    #: boxed tables.  In particular boxed-rounded makes both #d8dadd while
    #: the body grid is #9a9ca5 and the generated outer frame is #374151.
    header_rule_rgb: tuple[float, float, float] | None = None
    header_vertical_rule_pt: float = 0.0
    header_vertical_rule_rgb: tuple[float, float, float] | None = None
    bottom_rule: bool = False
    bottom_rule_pt: float = 0.8
    row_rules: bool = False
    header_fill: Fill | tuple[float, float, float] | None = None
    stripe_fill: Fill | tuple[float, float, float] | None = None
    header_uppercase: bool = False
    rule_rgb: tuple[float, float, float] | None = None
    #: A rule above the header row. Zero means none; `bold` is the layout
    #: that uses it, and it is not the same thing as a thick bottom rule.
    header_top_rule_pt: float = 0.0
    row_rule_pt: float = 0.8
    row_rule_rgb: tuple[float, float, float] | None = None
    vertical_rule_pt: float = 0.0
    vertical_rule_rgb: tuple[float, float, float] | None = None
    header_text_rgb: tuple[float, float, float] | None = None
    #: The outer box `boxed` and `boxed-rounded` draw around the whole table,
    #: in a generated `::before` that sits over the cell grid. A border on
    #: the table element itself is the separate `table_top_rule_pt`, which is
    #: how `standard` rules off its totals band.
    frame_rule: bool = False
    frame_rule_pt: float = 0.0
    frame_rgb: tuple[float, float, float] | None = None
    #: `boxed-rounded` rounds the frame by 0.75rem, but not evenly: a line
    #: table with a totals band below squares off its bottom-right so the
    #: band tucks into it, and the band rounds only its own bottom two.
    #: Clockwise from the top left.
    frame_corners_mm: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    #: The header row's own corners, which follow the frame's top two so the
    #: fill does not square off outside a rounded edge.
    header_corners_mm: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    table_top_rule_pt: float = 0.0
    #: The `o_total` row, which every layout treats as its own thing rather
    #: than as the last body row.
    total_row_fill: Fill | tuple[float, float, float] | None = None
    total_row_text_rgb: tuple[float, float, float] | None = None
    total_row_rule_pt: float = 0.0
    #: Boxed table styles tint the authored ``o_price_total`` cell rather
    #: than its whole row.  Keeping that selector result separate prevents a
    #: row-level approximation from painting four unrelated columns.
    price_total_fill: Fill | tuple[float, float, float] | None = None
    #: Boxed styles also tint every cell in the explicitly authored
    #: ``o_taxes`` row.  This is a row role, distinct from nth-child stripes.
    taxes_row_fill: Fill | tuple[float, float, float] | None = None

    def __post_init__(self) -> None:
        for name in _FILL_FIELDS:
            object.__setattr__(self, name, as_fill(getattr(self, name)))


#: The company-independent chrome of every table style, compiled from the
#: report stylesheet. Regenerate with ``tools/derive_table_skins.py --emit``;
#: check a deployment against it by running the tool with no arguments.
#:
#: Eight styles times two kinds is sixteen entries and eleven distinct
#: answers -- ``boxed``/``boxed-rounded`` share their totals band, and
#: ``bubble``/``wave``/``folder`` state no table chrome at all, taking their
#: whole look from the company overlay.
TABLE_SKINS: dict[tuple[str, str], TableSkin] = {
    ("bold", "lines"): TableSkin(
        bottom_rule=True,
        bottom_rule_pt=1.92,
        header_rule=False,
        header_rule_pt=0.0,
        header_text_rgb=hex_rgb("#212529"),
        header_top_rule_pt=1.92,
        header_uppercase=True,
        row_rule_pt=0.0,
        rule_rgb=hex_rgb("#212529"),
    ),
    ("bold", "totals"): TableSkin(
        bottom_rule=True,
        bottom_rule_pt=1.92,
        header_rule=False,
        header_rule_pt=0.0,
        row_rule_pt=0.0,
        rule_rgb=hex_rgb("#212529"),
        total_row_rule_pt=0.64,
        total_row_text_rgb=hex_rgb("#212529"),
    ),
    ("boxed", "lines"): TableSkin(
        bottom_rule_pt=0.0,
        cell_borders=True,
        frame_rgb=hex_rgb("#495057"),
        frame_rule=True,
        frame_rule_pt=0.64,
        header_rule_pt=0.64,
        header_rule_rgb=hex_rgb("#212529"),
        header_text_rgb=hex_rgb("#212529"),
        header_uppercase=True,
        header_vertical_rule_pt=0.64,
        header_vertical_rule_rgb=hex_rgb("#495057"),
        price_total_fill=Fill(hex_rgb("#e9ecef"), 0.5),
        row_rule_pt=0.64,
        row_rule_rgb=hex_rgb("#ced4da"),
        rule_rgb=hex_rgb("#212529"),
        vertical_rule_pt=0.64,
        vertical_rule_rgb=hex_rgb("#ced4da"),
    ),
    ("boxed", "totals"): TableSkin(
        bottom_rule_pt=0.0,
        cell_borders=True,
        frame_rgb=hex_rgb("#495057"),
        frame_rule=True,
        frame_rule_pt=0.64,
        header_rule=False,
        header_rule_pt=0.0,
        row_rule_pt=0.64,
        row_rule_rgb=hex_rgb("#ced4da"),
        rule_rgb=hex_rgb("#ced4da"),
        taxes_row_fill=Fill(hex_rgb("#e9ecef"), 0.5),
        total_row_text_rgb=hex_rgb("#212529"),
        vertical_rule_pt=0.64,
        vertical_rule_rgb=hex_rgb("#ced4da"),
    ),
    ("boxed-rounded", "lines"): TableSkin(
        bottom_rule_pt=0.0,
        cell_borders=True,
        frame_corners_mm=(2.7093333333333334, 2.7093333333333334, 0.0, 2.7093333333333334),
        frame_rgb=hex_rgb("#495057"),
        frame_rule=True,
        frame_rule_pt=0.64,
        header_corners_mm=(2.7093333333333334, 2.7093333333333334, 0.0, 0.0),
        header_rule_pt=0.64,
        header_rule_rgb=hex_rgb("#dee2e6"),
        header_text_rgb=hex_rgb("#212529"),
        header_uppercase=True,
        header_vertical_rule_pt=0.64,
        header_vertical_rule_rgb=hex_rgb("#dee2e6"),
        price_total_fill=Fill(hex_rgb("#e9ecef"), 0.5),
        row_rule_pt=0.64,
        row_rule_rgb=hex_rgb("#ced4da"),
        rule_rgb=hex_rgb("#dee2e6"),
        vertical_rule_pt=0.64,
        vertical_rule_rgb=hex_rgb("#ced4da"),
    ),
    ("boxed-rounded", "totals"): TableSkin(
        bottom_rule_pt=0.0,
        cell_borders=True,
        frame_corners_mm=(0.0, 0.0, 2.7093333333333334, 2.7093333333333334),
        frame_rgb=hex_rgb("#495057"),
        frame_rule=True,
        frame_rule_pt=0.64,
        header_rule=False,
        header_rule_pt=0.0,
        row_rule_pt=0.64,
        row_rule_rgb=hex_rgb("#ced4da"),
        rule_rgb=hex_rgb("#ced4da"),
        taxes_row_fill=Fill(hex_rgb("#e9ecef"), 0.5),
        total_row_text_rgb=hex_rgb("#212529"),
        vertical_rule_pt=0.64,
        vertical_rule_rgb=hex_rgb("#ced4da"),
    ),
    ("bubble", "lines"): TableSkin(
        bottom_rule_pt=0.0,
        header_rule=False,
        header_rule_pt=0.0,
        header_text_rgb=hex_rgb("#212529"),
        row_rule_pt=0.0,
    ),
    ("bubble", "totals"): TableSkin(
        bottom_rule_pt=0.0,
        header_rule=False,
        header_rule_pt=0.0,
        row_rule_pt=0.0,
        total_row_text_rgb=hex_rgb("#212529"),
    ),
    ("folder", "lines"): TableSkin(
        bottom_rule_pt=0.0,
        header_rule=False,
        header_rule_pt=0.0,
        header_text_rgb=hex_rgb("#212529"),
        row_rule_pt=0.0,
    ),
    ("folder", "totals"): TableSkin(
        bottom_rule_pt=0.0,
        header_rule=False,
        header_rule_pt=0.0,
        row_rule_pt=0.0,
        total_row_text_rgb=hex_rgb("#212529"),
    ),
    ("standard", "lines"): TableSkin(
        bottom_rule_pt=0.0,
        header_rule_pt=0.64,
        header_rule_rgb=hex_rgb("#212529"),
        header_text_rgb=hex_rgb("#212529"),
        row_rule_pt=0.0,
        rule_rgb=hex_rgb("#212529"),
    ),
    ("standard", "totals"): TableSkin(
        bottom_rule_pt=0.0,
        header_rule=False,
        header_rule_pt=0.0,
        row_rule_pt=0.0,
        rule_rgb=hex_rgb("#212529"),
        table_top_rule_pt=0.64,
        total_row_rule_pt=0.64,
        total_row_text_rgb=hex_rgb("#212529"),
    ),
    ("striped", "lines"): TableSkin(
        bottom_rule=True,
        bottom_rule_pt=0.64,
        header_rule=False,
        header_rule_pt=0.0,
        header_text_rgb=hex_rgb("#212529"),
        row_rule_pt=0.64,
        row_rule_rgb=hex_rgb("#e9ecef"),
        row_rules=True,
        rule_rgb=hex_rgb("#e9ecef"),
        stripe_fill=Fill(hex_rgb("#e9ecef"), 0.5),
    ),
    ("striped", "totals"): TableSkin(
        bottom_rule=True,
        bottom_rule_pt=0.64,
        header_rule=False,
        header_rule_pt=0.0,
        row_rule_pt=0.64,
        row_rule_rgb=hex_rgb("#e9ecef"),
        row_rules=True,
        rule_rgb=hex_rgb("#e9ecef"),
        stripe_fill=Fill(hex_rgb("#e9ecef"), 0.5),
        total_row_fill=Fill(hex_rgb("#e9ecef"), 0.5),
        total_row_rule_pt=0.64,
        total_row_text_rgb=hex_rgb("#212529"),
    ),
    ("wave", "lines"): TableSkin(
        bottom_rule_pt=0.0,
        header_rule=False,
        header_rule_pt=0.0,
        header_text_rgb=hex_rgb("#212529"),
        row_rule_pt=0.0,
    ),
    ("wave", "totals"): TableSkin(
        bottom_rule_pt=0.0,
        header_rule=False,
        header_rule_pt=0.0,
        row_rule_pt=0.0,
        total_row_text_rgb=hex_rgb("#212529"),
    ),
}


#: `border: 2px solid` on `.o_report_layout_bubble #informations`.
INFORMATIONS_BORDER_PT = 2.0 * 72.0 / PX_PER_INCH
#: `border-radius: 0.75rem` at Bootstrap's 16px root.
INFORMATIONS_RADIUS_MM = 0.75 * MM_PER_REM
#: `padding: 8px 0.5rem` -- both sides land on the same 8px.
#: Retired to zero, not deleted: the panel still needs a padding and the
#: cascade now states it. `.o_report_layout_bubble #informations` and its
#: Wave twin declare `padding: 8px 0.5rem`, which reaches the grid through
#: `PADDING_STYLE_RULES`, so a second copy here would be the same
#: length applied twice -- which is exactly what it was, and what moved the
#: panel 1.806mm off the table it is supposed to span.
INFORMATIONS_PADDING_MM = 0.0


@dataclass(frozen=True, slots=True)
class PageShape:
    """A circle of page art, in the CSS pixels the template states it in.

    `web.external_layout_bubble` draws `<svg width="1100" height="1100">
    <circle cx="550" cy="550" r="550" fill="$primary" fill-opacity=".1"/>`
    and `report.scss` puts it at `top: -870px; right: -450px`, fixed to the
    page. So the geometry is literal in the source, and the only things that
    vary are the company colour and the paper size.

    `anchor_right` because the CSS positions it from the right edge; the two
    offsets are the svg box's own edges, not the circle's centre.
    """

    width_px: float
    height_px: float
    cx_px: float
    cy_px: float
    radius_px: float
    top_px: float
    #: Offset of the svg box from the named edge.
    right_px: float | None = None
    left_px: float | None = None
    #: Which company colour fills it, and at what opacity over paper.
    colour: str = "primary"
    opacity: float = 0.1
    #: An SVG path's `d`, when the shape is not a circle. Read by
    #: `docsubstrate.svg_path`, so the geometry stays the template's.
    path_d: str | None = None
    #: Where `top_px` is defined from. `"page"` is the sheet's top edge;
    #: `"footer"` is the top of the band the paperformat reserves, which is
    #: where a `position-fixed` svg in the footer comes to rest.
    anchor: str = "page"


#: The page art each layout draws, compiled from its template and the CSS
#: that positions it. Empty for the layouts that draw none.
LAYOUT_SHAPES: dict[str, tuple[PageShape, ...]] = {
    "bubble": (
        PageShape(
            width_px=1100.0, height_px=1100.0,
            cx_px=550.0, cy_px=550.0, radius_px=550.0,
            top_px=BUBBLE_CIRCLE_POSITION_PX[0],
            right_px=BUBBLE_CIRCLE_POSITION_PX[1],
            colour="primary", opacity=0.1,
        ),
        PageShape(
            width_px=500.0, height_px=228.0,
            cx_px=0.0, cy_px=0.0, radius_px=0.0,
            top_px=0.0, left_px=0.0, anchor="footer",
            colour="secondary", opacity=0.1,
            path_d=(
                "M500 228H0V6.52743C26.3323 2.23278 53.3561 0 80.9008 0"
                "C256.522 0 410.969 90.7656 500 228Z"
            ),
        ),
    ),
}


@dataclass(frozen=True, slots=True)
class InformationsBox:
    """The framed panel Bubble and Wave put the informations row inside."""

    fill: tuple[float, float, float] | None = None
    border_rgb: tuple[float, float, float] | None = None
    border_pt: float = 0.0
    radius_mm: float = 0.0
    padding_mm: float = 0.0


@dataclass(frozen=True, slots=True)
class ReportTheme:
    """One report's inherited look."""

    layout: str = "standard"
    table: str = "standard"
    primary: tuple[float, float, float] = rgb(DEFAULT_PRIMARY, DEFAULT_PRIMARY)
    secondary: tuple[float, float, float] = rgb(DEFAULT_SECONDARY, DEFAULT_SECONDARY)
    #: The ``o_company_N_layout`` class the HTML carries. Carried rather than
    #: used: :func:`company_overlay` works from the colours directly, but the
    #: class is what ``tools/derive_table_skins.py`` needs to check this
    #: module against a deployment's own generated stylesheet.
    company_class: str | None = None

    @classmethod
    def from_values(cls, values, document=None) -> ReportTheme:
        """Build from presentation values, falling back to what the HTML said.

        The company setting is authoritative; the ``o_report_layout_*`` class
        on the evaluated HTML is the fallback for callers that do not pass one.

        ``layout`` and ``table`` are two settings. Odoo's document layout
        picker and its table style are separate fields, and a company that
        changed one without the other -- ``o_report_layout_bubble`` with
        ``o_table_boxed-rounded``, which is what the reference deployment
        actually has -- gets the wrong table from any engine that treats the
        second as a synonym for the first. Falling back to the layout is only
        for HTML that named no table style at all.
        """
        values = values or {}
        layout = str(
            values.get("layout") or getattr(document, "layout", None) or "standard"
        ).lower()
        layout = layout if layout in LAYOUTS else "standard"
        # A layout's table style is not its name: see LAYOUT_TABLE_STYLE.
        table = str(
            values.get("table_theme")
            or getattr(document, "table_theme", None)
            or LAYOUT_TABLE_STYLE.get(layout, layout)
        ).lower()
        return cls(
            layout=layout,
            table=table,
            primary=rgb(values.get("primary_color"), DEFAULT_PRIMARY),
            secondary=rgb(values.get("secondary_color"), DEFAULT_SECONDARY),
            company_class=(
                values.get("company_class")
                or getattr(document, "company_class", None)
                or None
            ),
        )

    @property
    def band_fill(self) -> tuple[float, float, float] | None:
        """The wash behind the header. Folder only.

        Folder is the one layout whose 0.92-white tint lands on the header: the
        company template fills ``.o_folder_header_container``'s shape with
        ``mix(white, $primary, 0.92)``, and this engine does not draw that
        shape, so the wash is what survives of it.

        Bubble and Wave used to get this too, and it was the wrong thing in
        the wrong colour in the wrong place -- their 0.92-white tint is the
        *background of the informations row*, mixed from ``$secondary``, not
        a page-wide header band mixed from ``$primary``. Painting it as a
        band gave a bubble report half a folder's chrome. See
        :meth:`informations_box`.
        """
        if self.layout == "folder":
            return band_tint(self.primary)
        return None

    def page_shapes(self, width_mm: float, height_mm: float, footer_mm: float = 0.0):
        """This layout's page art, resolved onto a sheet of paper.

        Returns :class:`~docsubstrate.pageplan.Circle` commands in
        millimetres from the bottom-left, which is where the renderer works.
        """
        from docsubstrate.pageplan import Circle, Path
        from docsubstrate.svg_path import parse_path, transform_path

        drawn = []
        for shape in LAYOUT_SHAPES.get(self.layout, ()):
            if shape.right_px is not None:
                # CSS `right` measures inward from the container's right
                # edge, so a negative value pushes the box outward: the
                # bubble's `right: -450px` puts its right edge 450px past
                # the paper, which is what makes the circle bleed off.
                right_mm = width_mm - shape.right_px * MM_PER_PX
                left_mm = right_mm - shape.width_px * MM_PER_PX
            else:
                left_mm = (shape.left_px or 0.0) * MM_PER_PX
            top_mm = shape.top_px * MM_PER_PX
            if shape.anchor == "footer":
                # A `position-fixed` svg in the footer comes to rest at the
                # top of the band the paperformat reserves for it. Defined
                # at 265.29mm against a 265.0mm band on A4; the remainder is
                # the footer's own leading.
                top_mm += height_mm - footer_mm
            base = self.primary if shape.colour == "primary" else self.secondary
            # `shape.opacity` is a real `fill-opacity` (Bubble/Wave's
            # watermark shapes are `.1`), carried as true alpha rather than
            # pre-mixed with white: pre-mixing paints identically only while
            # the shape sits alone on blank paper, and stops being correct
            # the moment anything else shares its backdrop.
            alpha = max(0.0, min(1.0, shape.opacity))
            if shape.path_d:
                drawn.append(Path(
                    segments=tuple(transform_path(
                        parse_path(shape.path_d),
                        scale_x=MM_PER_PX, scale_y=MM_PER_PX,
                        offset_x=left_mm, offset_y=top_mm, height_mm=height_mm,
                    )),
                    fill_rgb=base,
                    fill_alpha=alpha,
                ))
                continue
            drawn.append(Circle(
                cx_mm=left_mm + shape.cx_px * MM_PER_PX,
                # The renderer measures up from the bottom of the sheet.
                cy_mm=height_mm - (top_mm + shape.cy_px * MM_PER_PX),
                radius_mm=shape.radius_px * MM_PER_PX,
                fill_rgb=base,
                fill_alpha=alpha,
            ))
        return tuple(drawn)

    @property
    def informations_box(self) -> InformationsBox | None:
        """The box Bubble and Wave draw around the informations row.

        Two stylesheets meet here. The stock one gives the shape --
        ``.o_report_layout_{bubble,wave} #informations { border-radius:
        .75rem; padding: 8px .5rem }``, with Bubble adding ``border: 2px
        solid`` and no colour -- and the company one supplies the colours:
        ``border-color: $secondary`` and ``background-color: mix(white,
        $secondary, 0.92)``. Wave takes the shape and no colours.
        """
        if self.layout == "bubble":
            return InformationsBox(
                fill=band_tint(self.secondary),
                border_rgb=self.secondary,
                border_pt=INFORMATIONS_BORDER_PT,
                radius_mm=INFORMATIONS_RADIUS_MM,
                padding_mm=INFORMATIONS_PADDING_MM,
            )
        if self.layout == "wave":
            return InformationsBox(
                fill=band_tint(self.secondary),
                radius_mm=INFORMATIONS_RADIUS_MM,
                padding_mm=INFORMATIONS_PADDING_MM,
            )
        return None

    @property
    def title_rgb(self) -> tuple[float, float, float]:
        """Every layout puts the document title in the company colour.

        `web.styles_company_report` emits `.o_company_N_layout h2 { color:
        $primary }` unconditionally, outside the `t-if` chain that varies by
        layout. Gating it on the layout -- which is what this did -- printed
        the title near-black on `standard`, `boxed` and `striped`.
        """
        return self.primary

    @property
    def tagline_rgb(self) -> tuple[float, float, float]:
        """`.o_company_tagline { color: $primary }`, also unconditional.

        The tagline sits in the header band and was being drawn in body
        black, because nothing asked the stylesheet what colour it was.
        """
        return self.primary

    def table_skin(self, kind: str = "lines") -> TableSkin:
        """Chrome for a table of this kind, under this theme and company.

        Two lookups, not one: :data:`TABLE_SKINS` says what the table style
        does, and :func:`company_overlay` mixes in what the company's own
        generated stylesheet does on top of it. The second depends on the
        *layout*, which is why a document can be `bubble` and `boxed-rounded`
        at once and needs both answers.
        """
        base = TABLE_SKINS.get(
            (self.table, kind), TABLE_SKINS[("standard", kind)]
        )
        return company_overlay(
            base, layout=self.layout, kind=kind,
            primary=self.primary, secondary=self.secondary,
        )


def contrast_on(colour: tuple[float, float, float]) -> tuple[float, float, float]:
    """Odoo's `preview-color-contrast()`: black on light, white on dark.

    Defined in ``web.styles_company_report`` as ``lightness($c) > 50`` in
    HSL terms, which is the midpoint of max and min channel -- not luminance,
    and not the WCAG contrast rule. Substituting a better formula would be a
    more legible document and a less faithful one.
    """
    return (0.0, 0.0, 0.0) if (max(colour) + min(colour)) / 2.0 > 0.5 else (1.0, 1.0, 1.0)


def mix_with_white(colour: tuple[float, float, float], white_share: float) -> tuple[
    float, float, float
]:
    """SCSS ``mix(white, $colour, $weight)``: `white_share` of white."""
    return tuple(white_share + (1.0 - white_share) * channel for channel in colour)


def company_overlay(
    skin: TableSkin,
    *,
    layout: str,
    kind: str,
    primary: tuple[float, float, float],
    secondary: tuple[float, float, float],
) -> TableSkin:
    """Apply the declared company colours for one supported skin context.

    The mapping is deliberately data-shaped: a layout/table-kind pair names
    only the fields that it owns.  A context with no table-colour
    contribution returns the original immutable skin unchanged.
    """
    update_factories = {
        ("boxed", "totals"): lambda: {
            "total_row_fill": primary,
            "total_row_text_rgb": contrast_on(primary),
        },
        ("bold", "lines"): lambda: {"rule_rgb": secondary},
        ("bubble", "totals"): lambda: {
            "total_row_fill": primary,
            "total_row_text_rgb": contrast_on(primary),
        },
        ("bubble", "lines"): lambda: {
            "header_fill": primary,
            "header_text_rgb": contrast_on(primary),
        },
    }
    factory = update_factories.get((layout, kind))
    return skin if factory is None else replace(skin, **factory())


def band_tint(colour: tuple[float, float, float]) -> tuple[float, float, float]:
    """The 0.92-white mix the shaped layouts wash their band in."""
    return mix_with_white(colour, 0.92)
