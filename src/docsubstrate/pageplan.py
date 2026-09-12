"""Resolved page plans: the execution boundary between layout and rendering.

A PagePlan contains only final page geometry.  It deliberately carries no flow,
wrapping, pagination, or business semantics.  Those concerns must be resolved by
a planner before a renderer sees the page.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True, slots=True)
class TextRun:
    x_mm: float
    y_mm: float
    text: str
    font_name: str = "Helvetica"
    font_size_pt: float = 10.0
    fill_rgb: tuple[float, float, float] | None = None
    char_space_pt: float = 0.0
    #: The `ir.Paragraph.source_block_id` this run was drawn for, carried
    #: through planning so a renderer can emit a provenance sidecar. It is
    #: not page geometry and no renderer may draw differently for it.
    source_block_id: str | None = None


@dataclass(frozen=True, slots=True)
class Line:
    x1_mm: float
    y1_mm: float
    x2_mm: float
    y2_mm: float
    width_pt: float = 0.5
    stroke_rgb: tuple[float, float, float] | None = None
    dash_array_pt: tuple[float, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Rect:
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    stroke: bool = True
    fill: bool = False
    line_width_pt: float = 0.5
    fill_rgb: tuple[float, float, float] | None = None
    stroke_rgb: tuple[float, float, float] | None = None
    #: True alpha for `fill_rgb`, `1.0` meaning opaque. A CSS source colour
    #: with less than full alpha (Bootstrap's translucent table stripe) must
    #: reach the renderer this way rather than as a colour pre-flattened
    #: against an assumed backdrop -- page art is painted before the body,
    #: so a stripe over it has to blend with what is actually there.
    fill_alpha: float = 1.0
    #: Corner radius. Bubble and Wave round their informations box by
    #: 0.75rem, and a square box is the wrong shape in a layout named for
    #: the rounded one.
    radius_mm: float = 0.0
    #: Per-corner override, clockwise from the top left. `boxed-rounded`
    #: needs it: a line table with a totals band below squares off its
    #: bottom-right so the band tucks into it, and the band rounds only its
    #: own two bottom corners. One radius for all four puts the curve under
    #: the wrong row.
    corner_radii_mm: tuple[float, float, float, float] | None = None
    dash_array_pt: tuple[float, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Circle:
    """A filled circle, for the page art the shaped layouts draw.

    Odoo states these as an `<svg><circle>` in the layout template and
    positions them with CSS, so they are geometry rather than an image --
    which is why they survive into a vector engine at all.
    """

    cx_mm: float
    cy_mm: float
    radius_mm: float
    fill_rgb: tuple[float, float, float] | None = None
    #: True alpha for `fill_rgb`, `1.0` meaning opaque. See `Rect.fill_alpha`
    #: -- a shape's own `fill-opacity` (Bubble's watermark circle is drawn at
    #: `.1`) must reach the renderer this way rather than pre-flattened, so
    #: it still composites correctly against anything else drawn under it.
    fill_alpha: float = 1.0


@dataclass(frozen=True, slots=True)
class Path:
    """A filled path, in the page's own millimetres.

    `segments` is a flat list of ``("m"|"l"|"c"|"z", *coords)`` with every
    coordinate already resolved onto the sheet, so a renderer only has to
    replay them. The SVG lives in the layout template; turning it into this
    is `docsubstrate.svg_path`.
    """

    segments: tuple
    fill_rgb: tuple[float, float, float] | None = None
    #: True alpha for `fill_rgb`, `1.0` meaning opaque. See `Rect.fill_alpha`
    #: -- Wave/Bubble/Folder's watermark shapes are drawn at `fill-opacity:
    #: .1` in the real template and must reach the renderer as real alpha,
    #: not pre-flattened against an assumed backdrop.
    fill_alpha: float = 1.0


@dataclass(frozen=True, slots=True)
class ImageRef:
    path: str
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    preserve_aspect_ratio: bool = False


PageCommand = TextRun | Line | Rect | ImageRef


@dataclass(frozen=True, slots=True)
class PagePlan:
    """One fully resolved physical page.

    Coordinates use a bottom-left origin in millimetres, matching the PDF page
    model while remaining independent from ReportLab.
    """

    width_mm: float = 210.0
    height_mm: float = 297.0
    commands: Sequence[PageCommand] = field(default_factory=tuple)
    #: Preserve the host paper kind and printer grid through planning. They
    #: affect only PDF page-box serialisation, never layout coordinates.
    paper_format: str = "A4"
    dpi: int = 90


@dataclass(frozen=True, slots=True)
class ResolvedDocument:
    """A document after pagination/layout, ready for deterministic execution."""

    pages: Sequence[PagePlan] = field(default_factory=tuple)
