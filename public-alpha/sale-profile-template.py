"""Compiled geometry for the bounded Odoo 19 Community sale-order profile.

The selector tables are generated from the two public stylesheet inputs bound
by ``public-alpha/odoo19-stylesheet-inputs.json``.  Fixed values are exercised
by ``tests/test_public_sale_runtime_contract.py``.  This module does not claim
coverage for other report families.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

# --- CSS units ---------------------------------------------------------
# The compatibility profile keeps CSS reference pixels separate from the
# effective print density.  The public synthetic contract exercises both.
CSS_PX_PER_INCH = 96.0
PX_PER_INCH = 112.5
MM_PER_PX = 25.4 / PX_PER_INCH
MM_PER_REM = 16.0 * MM_PER_PX  # 3.6124...
#: The paperformat dpi the bridge above belongs to: Odoo's default A4.
DEFAULT_DPI = 90

# --- bounded shrink-to-fit compatibility profile ----------------------
#: Every printed page is first laid out this much wider than the paper.
PRINTING_MINIMUM_SHRINK_FACTOR = 1.25
#: The widest a page may be laid out, as a multiple of the paper.
PRINTING_MAXIMUM_SHRINK_FACTOR = 2.0
#: The floor of the shrink-to-fit scale, relative to a document that fits.
#: A document wider than this profile's maximum uses the minimum scale.
MINIMUM_SHRINK_TO_FIT_SCALE = (
    PRINTING_MINIMUM_SHRINK_FACTOR / PRINTING_MAXIMUM_SHRINK_FACTOR
)

#: How many CSS pixels a declared CSS point becomes.
#:
#: Defined by the two profile factors above and exercised synthetically.
PT_TO_CSS_PX = PRINTING_MAXIMUM_SHRINK_FACTOR / PRINTING_MINIMUM_SHRINK_FACTOR

#: wkhtml's smart-shrinking pipeline does not route CSS ``pt`` font sizes
#: through the same reference-pixel scale as ``px`` lengths.  It applies this
#: scale instead: 1.6 CSS pixels to the point, over the active bridge.
#:
#: This is the value at :data:`PX_PER_INCH`. Use
#: :func:`smart_shrink_pt_scale`, which is a function of the active bridge,
#: rather than this constant.
SMART_SHRINK_PT_SCALE = PT_TO_CSS_PX * 72.0 / PX_PER_INCH


def smart_shrink_px_per_inch(
    dpi: float | None = None, *, shrink_to_fit_scale: float = 1.0
) -> float:
    """Return the effective CSS-pixel density of a scaled print surface.

    The contract has three independent inputs: the device density, the
    layout enlargement used by this profile, and the final document scale.
    A missing or zero device density selects the profile default.  A final
    scale, once supplied, must be finite and positive; accepting an
    ambiguous value would silently invert or destroy every physical length.
    """
    device_density = float(dpi) if dpi else float(DEFAULT_DPI)
    document_scale = float(shrink_to_fit_scale)
    if not math.isfinite(device_density) or device_density <= 0.0:
        raise ValueError("dpi must resolve to a finite positive number")
    if not math.isfinite(document_scale) or document_scale <= 0.0:
        raise ValueError("shrink_to_fit_scale must be finite and positive")
    enlarged_density = device_density * PRINTING_MINIMUM_SHRINK_FACTOR
    return enlarged_density / document_scale


def smart_shrink_pt_scale(*, px_per_inch: float = PX_PER_INCH) -> float:
    """Convert this profile's point-to-pixel ratio into a paper scale.

    ``px_per_inch`` is keyword-only because it is a resolved pixel density,
    not a paperformat DPI.  Non-positive or non-finite densities have no
    physically meaningful answer and are rejected rather than propagated.
    """
    density = float(px_per_inch)
    if not math.isfinite(density) or density <= 0.0:
        raise ValueError("px_per_inch must be finite and positive")
    points_per_pixel = 72.0 / density
    return points_per_pixel * PT_TO_CSS_PX

# --- grid --------------------------------------------------------------
GRID_COLUMNS = 12
#: The bounded sale report's outer grid is gutterless.
GUTTER_MM = 0.0
BOOTSTRAP_GUTTER_MM = 1.5 * MM_PER_REM
TOTALS_SPAN = 6  # the `col-6 ms-auto` totals band
INFO_COL = "auto"  # a bare `col` in an informations row
RIGHT_ALIGNED_OFFSET = -1  # sentinel for `ms-auto`

#: Odoo's A4 paperformat states 0 horizontal margin, because the inset that
#: wkhtmltopdf actually renders comes from this compound report-CSS rule:
#: ``.o_body_pdf.o_css_margins { padding: 0 11mm }``.  This is a CSS length,
#: not eleven physical millimetres when smart shrinking is active; the parser
#: carries it through the same 96-reference-pixel bridge as every other CSS
#: absolute unit.
REPORT_BODY_PADDING_CSS_MM = 11.0
#: Below this, a stated horizontal margin is read as "the paper says nothing".
PAPER_MARGIN_EPSILON_MM = 2.0

# --- table geometry ----------------------------------------------------
MAIN_TABLE_KIND = "commerce-lines"
TOTALS_TABLE_KIND = "totals"
#: Column weights of the stock `o_main_table` line table
#: (description, quantity, unit price, discount, amount).
MAIN_TABLE_COLUMN_WEIGHTS = (5.7, 1.0, 0.92, 0.44, 1.08)
#: Column weights and page share of the stock `o_total_table` totals band.
TOTALS_TABLE_COLUMN_WEIGHTS = (1.5, 1.0)
#: Compatibility value retained for callers; layout reads the compiled width.
TOTALS_TABLE_WIDTH_FRACTION = 0.5
#: Bootstrap `.table` cell padding is .5rem; `.table-sm` halves it to .25rem.
TABLE_CELL_PAD_REM = 0.5
TABLE_SM_CELL_PAD_REM = 0.25
TABLE_SM_PAD_RATIO = TABLE_SM_CELL_PAD_REM / TABLE_CELL_PAD_REM
#: The authored `.table > … > *` inset in the active print-pixel bridge.
TABLE_CELL_PAD_MM = TABLE_CELL_PAD_REM * MM_PER_REM
#: WebKit's presentational ``<table border="1">`` hint is not an author
#: stylesheet rule.  In collapsed mode it paints the table's outside edge in
#: a dark bevel colour and the cell grid in a mid-grey.  Keep both readings
#: because flattening them to one generic table-rule colour is visibly wrong.
LEGACY_TABLE_OUTER_RGB = (44 / 255, 44 / 255, 44 / 255)
LEGACY_TABLE_INNER_RGB = (128 / 255, 128 / 255, 128 / 255)

#: Width declarations compiled from the public stylesheet inputs, with
#: selectors and cascade metadata intact.  The generator deliberately drops
#: values that the bounded compatibility profile cannot resolve.
BOX_STYLE_RULES = (
    (
        '#qrcode_odoo_logo',
        (
            ('width', '18%', False),
        ),
    ),
    (
        '.o_nocontent_help .o_empty_folder_image:before',
        (
            ('width', '120px', False),
        ),
    ),
    (
        'legend',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.container, .o_container_small, .container-fluid, .container-xxl, .container-xl, .container-lg, .container-md, .container-sm',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.row > *',
        (
            ('width', '100%', False),
            ('max-width', '100%', False),
        ),
    ),
    (
        '.row-cols-auto > *',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.row-cols-1 > *',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.row-cols-2 > *',
        (
            ('width', '50%', False),
        ),
    ),
    (
        '.row-cols-3 > *',
        (
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.row-cols-4 > *',
        (
            ('width', '25%', False),
        ),
    ),
    (
        '.row-cols-5 > *',
        (
            ('width', '20%', False),
        ),
    ),
    (
        '.row-cols-6 > *',
        (
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-auto',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.col-1',
        (
            ('width', '8.33333333%', False),
        ),
    ),
    (
        '.col-2',
        (
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-3',
        (
            ('width', '25%', False),
        ),
    ),
    (
        '.col-4',
        (
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.col-5',
        (
            ('width', '41.66666667%', False),
        ),
    ),
    (
        '.col-6',
        (
            ('width', '50%', False),
        ),
    ),
    (
        '.col-7',
        (
            ('width', '58.33333333%', False),
        ),
    ),
    (
        '.col-8',
        (
            ('width', '66.66666667%', False),
        ),
    ),
    (
        '.col-9',
        (
            ('width', '75%', False),
        ),
    ),
    (
        '.col-10',
        (
            ('width', '83.33333333%', False),
        ),
    ),
    (
        '.col-11',
        (
            ('width', '91.66666667%', False),
        ),
    ),
    (
        '.col-12',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.row-cols-sm-auto > *',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.row-cols-sm-1 > *',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.row-cols-sm-2 > *',
        (
            ('width', '50%', False),
        ),
    ),
    (
        '.row-cols-sm-3 > *',
        (
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.row-cols-sm-4 > *',
        (
            ('width', '25%', False),
        ),
    ),
    (
        '.row-cols-sm-5 > *',
        (
            ('width', '20%', False),
        ),
    ),
    (
        '.row-cols-sm-6 > *',
        (
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-sm-auto',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.col-sm-1',
        (
            ('width', '8.33333333%', False),
        ),
    ),
    (
        '.col-sm-2',
        (
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-sm-3',
        (
            ('width', '25%', False),
        ),
    ),
    (
        '.col-sm-4',
        (
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.col-sm-5',
        (
            ('width', '41.66666667%', False),
        ),
    ),
    (
        '.col-sm-6',
        (
            ('width', '50%', False),
        ),
    ),
    (
        '.col-sm-7',
        (
            ('width', '58.33333333%', False),
        ),
    ),
    (
        '.col-sm-8',
        (
            ('width', '66.66666667%', False),
        ),
    ),
    (
        '.col-sm-9',
        (
            ('width', '75%', False),
        ),
    ),
    (
        '.col-sm-10',
        (
            ('width', '83.33333333%', False),
        ),
    ),
    (
        '.col-sm-11',
        (
            ('width', '91.66666667%', False),
        ),
    ),
    (
        '.col-sm-12',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.row-cols-md-auto > *',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.row-cols-md-1 > *',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.row-cols-md-2 > *',
        (
            ('width', '50%', False),
        ),
    ),
    (
        '.row-cols-md-3 > *',
        (
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.row-cols-md-4 > *',
        (
            ('width', '25%', False),
        ),
    ),
    (
        '.row-cols-md-5 > *',
        (
            ('width', '20%', False),
        ),
    ),
    (
        '.row-cols-md-6 > *',
        (
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-md-auto',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.col-md-1',
        (
            ('width', '8.33333333%', False),
        ),
    ),
    (
        '.col-md-2',
        (
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-md-3',
        (
            ('width', '25%', False),
        ),
    ),
    (
        '.col-md-4',
        (
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.col-md-5',
        (
            ('width', '41.66666667%', False),
        ),
    ),
    (
        '.col-md-6',
        (
            ('width', '50%', False),
        ),
    ),
    (
        '.col-md-7',
        (
            ('width', '58.33333333%', False),
        ),
    ),
    (
        '.col-md-8',
        (
            ('width', '66.66666667%', False),
        ),
    ),
    (
        '.col-md-9',
        (
            ('width', '75%', False),
        ),
    ),
    (
        '.col-md-10',
        (
            ('width', '83.33333333%', False),
        ),
    ),
    (
        '.col-md-11',
        (
            ('width', '91.66666667%', False),
        ),
    ),
    (
        '.col-md-12',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.row-cols-lg-auto > *',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.row-cols-lg-1 > *',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.row-cols-lg-2 > *',
        (
            ('width', '50%', False),
        ),
    ),
    (
        '.row-cols-lg-3 > *',
        (
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.row-cols-lg-4 > *',
        (
            ('width', '25%', False),
        ),
    ),
    (
        '.row-cols-lg-5 > *',
        (
            ('width', '20%', False),
        ),
    ),
    (
        '.row-cols-lg-6 > *',
        (
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-lg-auto',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.col-lg-1',
        (
            ('width', '8.33333333%', False),
        ),
    ),
    (
        '.col-lg-2',
        (
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-lg-3',
        (
            ('width', '25%', False),
        ),
    ),
    (
        '.col-lg-4',
        (
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.col-lg-5',
        (
            ('width', '41.66666667%', False),
        ),
    ),
    (
        '.col-lg-6',
        (
            ('width', '50%', False),
        ),
    ),
    (
        '.col-lg-7',
        (
            ('width', '58.33333333%', False),
        ),
    ),
    (
        '.col-lg-8',
        (
            ('width', '66.66666667%', False),
        ),
    ),
    (
        '.col-lg-9',
        (
            ('width', '75%', False),
        ),
    ),
    (
        '.col-lg-10',
        (
            ('width', '83.33333333%', False),
        ),
    ),
    (
        '.col-lg-11',
        (
            ('width', '91.66666667%', False),
        ),
    ),
    (
        '.col-lg-12',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.row-cols-xl-auto > *',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.row-cols-xl-1 > *',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.row-cols-xl-2 > *',
        (
            ('width', '50%', False),
        ),
    ),
    (
        '.row-cols-xl-3 > *',
        (
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.row-cols-xl-4 > *',
        (
            ('width', '25%', False),
        ),
    ),
    (
        '.row-cols-xl-5 > *',
        (
            ('width', '20%', False),
        ),
    ),
    (
        '.row-cols-xl-6 > *',
        (
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-xl-auto',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.col-xl-1',
        (
            ('width', '8.33333333%', False),
        ),
    ),
    (
        '.col-xl-2',
        (
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-xl-3',
        (
            ('width', '25%', False),
        ),
    ),
    (
        '.col-xl-4',
        (
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.col-xl-5',
        (
            ('width', '41.66666667%', False),
        ),
    ),
    (
        '.col-xl-6',
        (
            ('width', '50%', False),
        ),
    ),
    (
        '.col-xl-7',
        (
            ('width', '58.33333333%', False),
        ),
    ),
    (
        '.col-xl-8',
        (
            ('width', '66.66666667%', False),
        ),
    ),
    (
        '.col-xl-9',
        (
            ('width', '75%', False),
        ),
    ),
    (
        '.col-xl-10',
        (
            ('width', '83.33333333%', False),
        ),
    ),
    (
        '.col-xl-11',
        (
            ('width', '91.66666667%', False),
        ),
    ),
    (
        '.col-xl-12',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.row-cols-xxl-auto > *',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.row-cols-xxl-1 > *',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.row-cols-xxl-2 > *',
        (
            ('width', '50%', False),
        ),
    ),
    (
        '.row-cols-xxl-3 > *',
        (
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.row-cols-xxl-4 > *',
        (
            ('width', '25%', False),
        ),
    ),
    (
        '.row-cols-xxl-5 > *',
        (
            ('width', '20%', False),
        ),
    ),
    (
        '.row-cols-xxl-6 > *',
        (
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-xxl-auto',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.col-xxl-1',
        (
            ('width', '8.33333333%', False),
        ),
    ),
    (
        '.col-xxl-2',
        (
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-xxl-3',
        (
            ('width', '25%', False),
        ),
    ),
    (
        '.col-xxl-4',
        (
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.col-xxl-5',
        (
            ('width', '41.66666667%', False),
        ),
    ),
    (
        '.col-xxl-6',
        (
            ('width', '50%', False),
        ),
    ),
    (
        '.col-xxl-7',
        (
            ('width', '58.33333333%', False),
        ),
    ),
    (
        '.col-xxl-8',
        (
            ('width', '66.66666667%', False),
        ),
    ),
    (
        '.col-xxl-9',
        (
            ('width', '75%', False),
        ),
    ),
    (
        '.col-xxl-10',
        (
            ('width', '83.33333333%', False),
        ),
    ),
    (
        '.col-xxl-11',
        (
            ('width', '91.66666667%', False),
        ),
    ),
    (
        '.col-xxl-12',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.table',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.form-control',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.form-control-plaintext',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.form-control-color',
        (
            ('width', '3rem', False),
        ),
    ),
    (
        '.form-select',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.form-check-input',
        (
            ('width', '1em', False),
        ),
    ),
    (
        '.form-switch .form-check-input',
        (
            ('width', '2em', False),
        ),
    ),
    (
        '.form-range',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.form-range::-webkit-slider-thumb',
        (
            ('width', '1rem', False),
        ),
    ),
    (
        '.form-range::-webkit-slider-runnable-track',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.form-range::-moz-range-thumb',
        (
            ('width', '1rem', False),
        ),
    ),
    (
        '.form-range::-moz-range-track',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.input-group',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.input-group > .form-control, .input-group > .form-select, .input-group > .form-floating',
        (
            ('width', '1%', False),
            ('min-width', '0', False),
        ),
    ),
    (
        '.valid-feedback',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.was-validated .form-control-color:valid, .form-control-color.is-valid',
        (
            ('width', 'calc(3rem + calc(1.5em + 0.625rem))', False),
        ),
    ),
    (
        '.invalid-feedback',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.was-validated .form-control-color:invalid, .form-control-color.is-invalid',
        (
            ('width', 'calc(3rem + calc(1.5em + 0.625rem))', False),
        ),
    ),
    (
        '.collapsing.collapse-horizontal',
        (
            ('width', '0', False),
        ),
    ),
    (
        '.dropdown-item',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.btn-toolbar .input-group',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.btn-group-vertical > .btn, .btn-group-vertical > .btn-group',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.nav-fill .nav-item .nav-link, .nav-justified .nav-item .nav-link',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.navbar-toggler-icon',
        (
            ('width', '1.5em', False),
        ),
    ),
    (
        '.navbar-expand-sm .offcanvas',
        (
            ('width', 'auto', True),
        ),
    ),
    (
        '.navbar-expand-md .offcanvas',
        (
            ('width', 'auto', True),
        ),
    ),
    (
        '.navbar-expand-lg .offcanvas',
        (
            ('width', 'auto', True),
        ),
    ),
    (
        '.navbar-expand-xl .offcanvas',
        (
            ('width', 'auto', True),
        ),
    ),
    (
        '.navbar-expand-xxl .offcanvas',
        (
            ('width', 'auto', True),
        ),
    ),
    (
        '.navbar-expand .offcanvas',
        (
            ('width', 'auto', True),
        ),
    ),
    (
        '.card-img, .card-img-top, .card-img-bottom',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.accordion-button',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.progress-stacked > .progress > .progress-bar',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.list-group-item-action',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.btn-close',
        (
            ('width', '1em', False),
        ),
    ),
    (
        '.toast-container',
        (
            ('width', 'max-content', False),
            ('max-width', '100%', False),
        ),
    ),
    (
        '.modal',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.modal-dialog',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.modal-content',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.modal-backdrop',
        (
            ('width', '100vw', False),
        ),
    ),
    (
        '.modal-fullscreen',
        (
            ('width', '100vw', False),
            ('max-width', 'none', False),
        ),
    ),
    (
        '.modal-fullscreen-sm-down',
        (
            ('width', '100vw', False),
            ('max-width', 'none', False),
        ),
    ),
    (
        '.modal-fullscreen-md-down',
        (
            ('width', '100vw', False),
            ('max-width', 'none', False),
        ),
    ),
    (
        '.modal-fullscreen-lg-down',
        (
            ('width', '100vw', False),
            ('max-width', 'none', False),
        ),
    ),
    (
        '.modal-fullscreen-xl-down',
        (
            ('width', '100vw', False),
            ('max-width', 'none', False),
        ),
    ),
    (
        '.modal-fullscreen-xxl-down',
        (
            ('width', '100vw', False),
            ('max-width', 'none', False),
        ),
    ),
    (
        '.carousel-inner',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.carousel-item',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.carousel-control-prev, .carousel-control-next',
        (
            ('width', '15%', False),
        ),
    ),
    (
        '.carousel-control-prev-icon, .carousel-control-next-icon',
        (
            ('width', '2rem', False),
        ),
    ),
    (
        '.carousel-indicators [data-bs-target]',
        (
            ('width', '30px', False),
        ),
    ),
    (
        '.offcanvas-backdrop',
        (
            ('width', '100vw', False),
        ),
    ),
    (
        '.icon-link > .bi',
        (
            ('width', '1em', False),
        ),
    ),
    (
        '.ratio',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.ratio > *',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.w-0',
        (
            ('width', '0', True),
        ),
    ),
    (
        '.w-25',
        (
            ('width', '25%', True),
        ),
    ),
    (
        '.w-50',
        (
            ('width', '50%', True),
        ),
    ),
    (
        '.w-75',
        (
            ('width', '75%', True),
        ),
    ),
    (
        '.w-100',
        (
            ('width', '100%', True),
        ),
    ),
    (
        '.w-auto',
        (
            ('width', 'auto', True),
        ),
    ),
    (
        '.vw-100',
        (
            ('width', '100vw', True),
        ),
    ),
    (
        '.w-sm-0',
        (
            ('width', '0', True),
        ),
    ),
    (
        '.w-sm-25',
        (
            ('width', '25%', True),
        ),
    ),
    (
        '.w-sm-50',
        (
            ('width', '50%', True),
        ),
    ),
    (
        '.w-sm-75',
        (
            ('width', '75%', True),
        ),
    ),
    (
        '.w-sm-100',
        (
            ('width', '100%', True),
        ),
    ),
    (
        '.w-sm-auto',
        (
            ('width', 'auto', True),
        ),
    ),
    (
        '.w-md-0',
        (
            ('width', '0', True),
        ),
    ),
    (
        '.w-md-25',
        (
            ('width', '25%', True),
        ),
    ),
    (
        '.w-md-50',
        (
            ('width', '50%', True),
        ),
    ),
    (
        '.w-md-75',
        (
            ('width', '75%', True),
        ),
    ),
    (
        '.w-md-100',
        (
            ('width', '100%', True),
        ),
    ),
    (
        '.w-md-auto',
        (
            ('width', 'auto', True),
        ),
    ),
    (
        '.w-lg-0',
        (
            ('width', '0', True),
        ),
    ),
    (
        '.w-lg-25',
        (
            ('width', '25%', True),
        ),
    ),
    (
        '.w-lg-50',
        (
            ('width', '50%', True),
        ),
    ),
    (
        '.w-lg-75',
        (
            ('width', '75%', True),
        ),
    ),
    (
        '.w-lg-100',
        (
            ('width', '100%', True),
        ),
    ),
    (
        '.w-lg-auto',
        (
            ('width', 'auto', True),
        ),
    ),
    (
        '.w-xl-0',
        (
            ('width', '0', True),
        ),
    ),
    (
        '.w-xl-25',
        (
            ('width', '25%', True),
        ),
    ),
    (
        '.w-xl-50',
        (
            ('width', '50%', True),
        ),
    ),
    (
        '.w-xl-75',
        (
            ('width', '75%', True),
        ),
    ),
    (
        '.w-xl-100',
        (
            ('width', '100%', True),
        ),
    ),
    (
        '.w-xl-auto',
        (
            ('width', 'auto', True),
        ),
    ),
    (
        '.w-xxl-0',
        (
            ('width', '0', True),
        ),
    ),
    (
        '.w-xxl-25',
        (
            ('width', '25%', True),
        ),
    ),
    (
        '.w-xxl-50',
        (
            ('width', '50%', True),
        ),
    ),
    (
        '.w-xxl-75',
        (
            ('width', '75%', True),
        ),
    ),
    (
        '.w-xxl-100',
        (
            ('width', '100%', True),
        ),
    ),
    (
        '.w-xxl-auto',
        (
            ('width', 'auto', True),
        ),
    ),
    (
        '.o_web_client .o_form_view .oe_styling_v8 .container',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.openerp .oe_form .oe_styling_v8',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.openerp .oe_form .oe_styling_v8 .container',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.oe_row',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.oe_row.oe_fit',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.oe_span12',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.oe_span10',
        (
            ('width', '83.33333%', False),
        ),
    ),
    (
        '.oe_span9',
        (
            ('width', '75%', False),
        ),
    ),
    (
        '.oe_span8',
        (
            ('width', '66.66667%', False),
        ),
    ),
    (
        '.oe_span6',
        (
            ('width', '50%', False),
        ),
    ),
    (
        '.oe_span4',
        (
            ('width', '33.33333%', False),
        ),
    ),
    (
        '.oe_span3',
        (
            ('width', '25%', False),
        ),
    ),
    (
        '.oe_span2',
        (
            ('width', '16.66667%', False),
        ),
    ),
    (
        ".oe_row.oe_flex [class*='oe_span']",
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_textarea',
        (
            ('width', '300px', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_form_layout_table',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.oe_styling_v8 h4.oe_slogan:before, .oe_styling_v8 h4.oe_slogan:after',
        (
            ('width', '100px', False),
        ),
    ),
    (
        '.oe_pic_ctr > img.oe_picture',
        (
            ('width', '100%', False),
            ('max-width', 'none', False),
        ),
    ),
    (
        'div.oe_demo span.oe_demo_play',
        (
            ('width', '80px', False),
        ),
    ),
    (
        'div.oe_demo img',
        (
            ('max-width', '100%', False),
            ('width', '100%', False),
        ),
    ),
    (
        'div.oe_demo div.oe_demo_footer',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.fa-fw',
        (
            ('width', '1.28571429em', False),
        ),
    ),
    (
        '.fa-li',
        (
            ('width', '2.14285714em', False),
        ),
    ),
    (
        '.fa-stack',
        (
            ('width', '2em', False),
        ),
    ),
    (
        '.fa-stack-1x, .fa-stack-2x',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.visually-hidden',
        (
            ('width', '1px', False),
        ),
    ),
    (
        '.footer .col-lg-3',
        (
            ('width', '25%', False),
        ),
    ),
    (
        '.footer .col-lg-4',
        (
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.footer .col-lg-6',
        (
            ('width', '50%', False),
        ),
    ),
    (
        'ul.o_checklist > li:not(.oe-nested):before',
        (
            ('width', '14px', False),
        ),
    ),
    (
        '.oe-tabs',
        (
            ('max-width', '40px', False),
            ('width', '40px', False),
        ),
    ),
    (
        'html, body',
        (
            ('width', '100%', False),
        ),
    ),
    (
        'ul.o_checklist > li:not(.oe-nested)::before',
        (
            ('width', '13px', False),
        ),
    ),
    (
        '.fa.card-img, .fa.card-img-top, .fa.card-img-bottom',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        'div.media_iframe_video iframe',
        (
            ('width', '100%', False),
        ),
    ),
    (
        'div.media_iframe_video .media_iframe_video_size',
        (
            ('width', '100%', False),
        ),
    ),
    (
        'div.media_iframe_video .css_editable_mode_display',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.o_we_search_prompt',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.o_we_search_prompt::before',
        (
            ('width', '100px', False),
        ),
    ),
    (
        '.o_label_page.o_label_dymo',
        (
            ('width', '57mm', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_legend_line',
        (
            ('width', '29%', False),
            ('min-width', '200px', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_legend_line > .o_report_stock_rule_legend_label',
        (
            ('width', '30%', False),
            ('min-width', '100px', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_legend_line > .o_report_stock_rule_legend_symbol',
        (
            ('width', '70%', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_arrow',
        (
            ('width', '20px', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_vertical_bar',
        (
            ('width', '2px', False),
        ),
    ),
    (
        '[name="so_total_summary"] div#total',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.img-fluid',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.img-thumbnail',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.container-sm, .container, .o_container_small',
        (
            ('max-width', '540px', False),
        ),
    ),
    (
        '.container-md, .container-sm, .container, .o_container_small',
        (
            ('max-width', '720px', False),
        ),
    ),
    (
        '.container-lg, .container-md, .container-sm, .container, .o_container_small',
        (
            ('max-width', '960px', False),
        ),
    ),
    (
        '.container-xl, .container-lg, .container-md, .container-sm, .container, .o_container_small',
        (
            ('max-width', '1140px', False),
        ),
    ),
    (
        '.container-xxl, .container-xl, .container-lg, .container-md, .container-sm, .container, .o_container_small',
        (
            ('max-width', '1320px', False),
        ),
    ),
    (
        '.valid-tooltip',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.invalid-tooltip',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.toast',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.offcanvas-sm',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.offcanvas-md',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.offcanvas-lg',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.offcanvas-xl',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.offcanvas-xxl',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.offcanvas',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.mw-0',
        (
            ('max-width', '0', True),
        ),
    ),
    (
        '.mw-25',
        (
            ('max-width', '25%', True),
        ),
    ),
    (
        '.mw-50',
        (
            ('max-width', '50%', True),
        ),
    ),
    (
        '.mw-75',
        (
            ('max-width', '75%', True),
        ),
    ),
    (
        '.mw-100',
        (
            ('max-width', '100%', True),
        ),
    ),
    (
        '.mw-auto',
        (
            ('max-width', 'auto', True),
        ),
    ),
    (
        '.mw-sm-0',
        (
            ('max-width', '0', True),
        ),
    ),
    (
        '.mw-sm-25',
        (
            ('max-width', '25%', True),
        ),
    ),
    (
        '.mw-sm-50',
        (
            ('max-width', '50%', True),
        ),
    ),
    (
        '.mw-sm-75',
        (
            ('max-width', '75%', True),
        ),
    ),
    (
        '.mw-sm-100',
        (
            ('max-width', '100%', True),
        ),
    ),
    (
        '.mw-sm-auto',
        (
            ('max-width', 'auto', True),
        ),
    ),
    (
        '.mw-md-0',
        (
            ('max-width', '0', True),
        ),
    ),
    (
        '.mw-md-25',
        (
            ('max-width', '25%', True),
        ),
    ),
    (
        '.mw-md-50',
        (
            ('max-width', '50%', True),
        ),
    ),
    (
        '.mw-md-75',
        (
            ('max-width', '75%', True),
        ),
    ),
    (
        '.mw-md-100',
        (
            ('max-width', '100%', True),
        ),
    ),
    (
        '.mw-md-auto',
        (
            ('max-width', 'auto', True),
        ),
    ),
    (
        '.mw-lg-0',
        (
            ('max-width', '0', True),
        ),
    ),
    (
        '.mw-lg-25',
        (
            ('max-width', '25%', True),
        ),
    ),
    (
        '.mw-lg-50',
        (
            ('max-width', '50%', True),
        ),
    ),
    (
        '.mw-lg-75',
        (
            ('max-width', '75%', True),
        ),
    ),
    (
        '.mw-lg-100',
        (
            ('max-width', '100%', True),
        ),
    ),
    (
        '.mw-lg-auto',
        (
            ('max-width', 'auto', True),
        ),
    ),
    (
        '.mw-xl-0',
        (
            ('max-width', '0', True),
        ),
    ),
    (
        '.mw-xl-25',
        (
            ('max-width', '25%', True),
        ),
    ),
    (
        '.mw-xl-50',
        (
            ('max-width', '50%', True),
        ),
    ),
    (
        '.mw-xl-75',
        (
            ('max-width', '75%', True),
        ),
    ),
    (
        '.mw-xl-100',
        (
            ('max-width', '100%', True),
        ),
    ),
    (
        '.mw-xl-auto',
        (
            ('max-width', 'auto', True),
        ),
    ),
    (
        '.mw-xxl-0',
        (
            ('max-width', '0', True),
        ),
    ),
    (
        '.mw-xxl-25',
        (
            ('max-width', '25%', True),
        ),
    ),
    (
        '.mw-xxl-50',
        (
            ('max-width', '50%', True),
        ),
    ),
    (
        '.mw-xxl-75',
        (
            ('max-width', '75%', True),
        ),
    ),
    (
        '.mw-xxl-100',
        (
            ('max-width', '100%', True),
        ),
    ),
    (
        '.mw-xxl-auto',
        (
            ('max-width', 'auto', True),
        ),
    ),
    (
        '.openerp .oe_form_sheet_width',
        (
            ('max-width', '960px', False),
        ),
    ),
    (
        '.oe_page',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.oe_row.oe_flex .oe_span12',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.oe_row.oe_flex .oe_span10',
        (
            ('max-width', '83.33333%', False),
        ),
    ),
    (
        '.oe_row.oe_flex .oe_span9',
        (
            ('max-width', '75%', False),
        ),
    ),
    (
        '.oe_row.oe_flex .oe_span8',
        (
            ('max-width', '66.66667%', False),
        ),
    ),
    (
        '.oe_row.oe_flex .oe_span6',
        (
            ('max-width', '50%', False),
        ),
    ),
    (
        '.oe_row.oe_flex .oe_span4',
        (
            ('max-width', '33.33333%', False),
        ),
    ),
    (
        '.oe_row.oe_flex .oe_span3',
        (
            ('max-width', '25%', False),
        ),
    ),
    (
        '.oe_row.oe_flex .oe_span2',
        (
            ('max-width', '16.66667%', False),
        ),
    ),
    (
        '.oe_picture',
        (
            ('max-width', '84%', False),
        ),
    ),
    (
        '.o_company_logo',
        (
            ('max-width', '12rem', False),
        ),
    ),
    (
        '.o_company_logo_small',
        (
            ('max-width', '11rem', False),
        ),
    ),
    (
        '.o_company_logo_big',
        (
            ('max-width', '16rem', False),
        ),
    ),
    (
        '.o_shape_bubble_1 ~ table .o_company_logo',
        (
            ('max-width', '9rem', False),
        ),
    ),
    (
        '.o_td_quantity',
        (
            ('min-width', '7rem', False),
            ('max-width', '9rem', False),
        ),
    ),
    (
        '.o_text_columns',
        (
            ('max-width', '100%', True),
        ),
    ),
    (
        '.o_nocontent_help',
        (
            ('max-width', '650px', False),
        ),
    ),
    (
        '.o_we_search_prompt > h2, .o_we_search_prompt > .h2',
        (
            ('max-width', '500px', False),
        ),
    ),
    (
        '.o_container_small',
        (
            ('max-width', '720px', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_legend',
        (
            ('max-width', '1000px', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_symbol_cell > div',
        (
            ('max-width', '200px', False),
        ),
    ),
    (
        'fieldset',
        (
            ('min-width', '0', False),
        ),
    ),
    (
        '.form-control::-webkit-date-and-time-value',
        (
            ('min-width', '85px', False),
        ),
    ),
    (
        '.card',
        (
            ('min-width', '0', False),
        ),
    ),
    (
        '.min-vw-100',
        (
            ('min-width', '100vw', True),
        ),
    ),
    (
        '.min-w-0',
        (
            ('min-width', '0', True),
        ),
    ),
    (
        '.oe_row_tab',
        (
            ('min-width', '120px', False),
        ),
    ),
    (
        '#wrapwrap table.table.table-bordered td, .o_editable table.table.table-bordered td',
        (
            ('min-width', '20px', False),
        ),
    ),
    (
        'div.media_iframe_video',
        (
            ('min-width', '100px', False),
        ),
    ),
    (
        '.o_stock_report_header_row > div',
        (
            ('min-width', '150px', False),
        ),
    ),
)


#: Every margin the two bundles state, on all four sides, selectors intact
#: and every rule expanded into the four longhands.
#:
#: Derived by `tools/derive_layout_rules.py`, 44 declarations dropped for
#: being `var()`-valued because wkhtmltopdf discards those whole.
#:
#: Why the whole property rather than the `auto` values it started as: a
#: class predicate over Bootstrap's spacer scale was supplying the numeric
#: ones, which is the substitution `GRID_COLUMNS` was making for `col-*`. It
#: agrees with the bundle wherever both speak -- `.mt-3{margin-top:16px}` and
#: the predicate's 1rem are the same 3.6124mm at 112.5px/inch -- and it is
#: silent everywhere else, so `div.o_employee_cv .o_sidebar`'s
#: `margin-top: -150px; margin-left: 500px` reached nothing. See
#: docs/cv-page-scale-2026-09-04.md.
#:
#: `auto` lives here too rather than in a slice of its own, so one sheet
#: answers for a margin however it is written.
#:
#: And every shorthand is expanded into its four sides, importance travelling
#: with each. A cascade that resolves per property name cannot resolve a
#: shorthand against a longhand: `.m-0{margin:0 !important}` has to beat
#: `p{margin-bottom:1rem}` on every side, and unexpanded both survived as
#: separate entries with the longhand winning -- which moved two of
MARGIN_STYLE_RULES = (
    (
        'html, body, div, span, applet, object, iframe, h1, h2, h3, h4, h5, h6, p, blockquote, pre, a, abbr, acronym, address, big, cite, code, del, dfn, em, font, img, ins, kbd, q, s, samp, small, strike, strong, sub, sup, tt, var, b, i, center, dl, dt, dd, ol, ul, li, fieldset, form, label, legend, table, caption, tbody, tfoot, thead, tr, th, td, article, aside, audio, canvas, details, figcaption, figure, footer, header, hgroup, mark, menu, meter, nav, output, progress, section, summary, time, video',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        'hr',
        (
            ('margin-top', '1em', False),
            ('margin-right', '0', False),
            ('margin-bottom', '1em', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        'input[type="submit"], input[type="button"], button',
        (
            ('margin-top', '0', True),
            ('margin-right', '0', True),
            ('margin-bottom', '0', True),
            ('margin-left', '0', True),
        ),
    ),
    (
        '.o_nocontent_help .o_empty_folder_image:before',
        (
            ('margin-top', '30px', False),
            ('margin-bottom', '30px', False),
        ),
    ),
    (
        'body',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        'hr',
        (
            ('margin-top', '16px', False),
            ('margin-right', '0', False),
            ('margin-bottom', '16px', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        'h6, .h6, h5, .h5, h4, .h4, h3, .h3, h2, .h2, h1, .h1',
        (
            ('margin-top', '0', False),
            ('margin-bottom', '0.75rem', False),
        ),
    ),
    (
        'p',
        (
            ('margin-top', '0', False),
            ('margin-bottom', '1rem', False),
        ),
    ),
    (
        'ol, ul, dl',
        (
            ('margin-top', '0', False),
            ('margin-bottom', '1rem', False),
        ),
    ),
    (
        'blockquote',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '1rem', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        'pre',
        (
            ('margin-top', '0', False),
            ('margin-bottom', '1rem', False),
        ),
    ),
    (
        'figure',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '1rem', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        'input, button, select, optgroup, textarea',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        'fieldset',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.blockquote-footer',
        (
            ('margin-top', '-16px', False),
            ('margin-bottom', '16px', False),
        ),
    ),
    (
        '.form-text',
        (
            ('margin-top', '0.25rem', False),
        ),
    ),
    (
        '.form-control::-webkit-date-and-time-value',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.form-control::file-selector-button',
        (
            ('margin-top', '-0.3125rem', False),
            ('margin-right', '-0.625rem', False),
            ('margin-bottom', '-0.3125rem', False),
            ('margin-left', '-0.625rem', False),
        ),
    ),
    (
        '.form-control-sm::file-selector-button',
        (
            ('margin-top', '-0.1875rem', False),
            ('margin-right', '-0.5rem', False),
            ('margin-bottom', '-0.1875rem', False),
            ('margin-left', '-0.5rem', False),
        ),
    ),
    (
        '.form-control-lg::file-selector-button',
        (
            ('margin-top', '-0.375rem', False),
            ('margin-right', '-0.75rem', False),
            ('margin-bottom', '-0.375rem', False),
            ('margin-left', '-0.75rem', False),
        ),
    ),
    (
        '.form-check-input',
        (
            ('margin-top', '0.25em', False),
        ),
    ),
    (
        '.form-range::-webkit-slider-thumb',
        (
            ('margin-top', '-0.25rem', False),
        ),
    ),
    (
        '.valid-feedback',
        (
            ('margin-top', '0.25rem', False),
        ),
    ),
    (
        '.valid-tooltip',
        (
            ('margin-top', '.1rem', False),
        ),
    ),
    (
        '.invalid-feedback',
        (
            ('margin-top', '0.25rem', False),
        ),
    ),
    (
        '.invalid-tooltip',
        (
            ('margin-top', '.1rem', False),
        ),
    ),
    (
        '.dropdown-menu',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.dropup .dropdown-menu[data-bs-popper]',
        (
            ('margin-top', '0', False),
        ),
    ),
    (
        '.dropend .dropdown-menu[data-bs-popper]',
        (
            ('margin-top', '0', False),
        ),
    ),
    (
        '.dropstart .dropdown-menu[data-bs-popper]',
        (
            ('margin-top', '0', False),
        ),
    ),
    (
        '.list-group-horizontal > .list-group-item.active',
        (
            ('margin-top', '0', False),
        ),
    ),
    (
        '.list-group-horizontal-sm > .list-group-item.active',
        (
            ('margin-top', '0', False),
        ),
    ),
    (
        '.list-group-horizontal-md > .list-group-item.active',
        (
            ('margin-top', '0', False),
        ),
    ),
    (
        '.list-group-horizontal-lg > .list-group-item.active',
        (
            ('margin-top', '0', False),
        ),
    ),
    (
        '.list-group-horizontal-xl > .list-group-item.active',
        (
            ('margin-top', '0', False),
        ),
    ),
    (
        '.list-group-horizontal-xxl > .list-group-item.active',
        (
            ('margin-top', '0', False),
        ),
    ),
    (
        '.modal-fullscreen',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.modal-fullscreen-sm-down',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.modal-fullscreen-md-down',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.modal-fullscreen-lg-down',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.modal-fullscreen-xl-down',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.modal-fullscreen-xxl-down',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.m-0',
        (
            ('margin-top', '0', True),
            ('margin-right', '0', True),
            ('margin-bottom', '0', True),
            ('margin-left', '0', True),
        ),
    ),
    (
        '.m-1',
        (
            ('margin-top', '4px', True),
            ('margin-right', '4px', True),
            ('margin-bottom', '4px', True),
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.m-2',
        (
            ('margin-top', '8px', True),
            ('margin-right', '8px', True),
            ('margin-bottom', '8px', True),
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.m-3',
        (
            ('margin-top', '16px', True),
            ('margin-right', '16px', True),
            ('margin-bottom', '16px', True),
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.m-4',
        (
            ('margin-top', '24px', True),
            ('margin-right', '24px', True),
            ('margin-bottom', '24px', True),
            ('margin-left', '24px', True),
        ),
    ),
    (
        '.m-5',
        (
            ('margin-top', '48px', True),
            ('margin-right', '48px', True),
            ('margin-bottom', '48px', True),
            ('margin-left', '48px', True),
        ),
    ),
    (
        '.m-auto',
        (
            ('margin-top', 'auto', True),
            ('margin-right', 'auto', True),
            ('margin-bottom', 'auto', True),
            ('margin-left', 'auto', True),
        ),
    ),
    (
        '.my-0',
        (
            ('margin-top', '0', True),
            ('margin-bottom', '0', True),
        ),
    ),
    (
        '.my-1',
        (
            ('margin-top', '4px', True),
            ('margin-bottom', '4px', True),
        ),
    ),
    (
        '.my-2',
        (
            ('margin-top', '8px', True),
            ('margin-bottom', '8px', True),
        ),
    ),
    (
        '.my-3',
        (
            ('margin-top', '16px', True),
            ('margin-bottom', '16px', True),
        ),
    ),
    (
        '.my-4',
        (
            ('margin-top', '24px', True),
            ('margin-bottom', '24px', True),
        ),
    ),
    (
        '.my-5',
        (
            ('margin-top', '48px', True),
            ('margin-bottom', '48px', True),
        ),
    ),
    (
        '.my-auto',
        (
            ('margin-top', 'auto', True),
            ('margin-bottom', 'auto', True),
        ),
    ),
    (
        '.mt-0',
        (
            ('margin-top', '0', True),
        ),
    ),
    (
        '.mt-1',
        (
            ('margin-top', '4px', True),
        ),
    ),
    (
        '.mt-2',
        (
            ('margin-top', '8px', True),
        ),
    ),
    (
        '.mt-3',
        (
            ('margin-top', '16px', True),
        ),
    ),
    (
        '.mt-4',
        (
            ('margin-top', '24px', True),
        ),
    ),
    (
        '.mt-5',
        (
            ('margin-top', '48px', True),
        ),
    ),
    (
        '.mt-auto',
        (
            ('margin-top', 'auto', True),
        ),
    ),
    (
        '.m-n1',
        (
            ('margin-top', '-4px', True),
            ('margin-right', '-4px', True),
            ('margin-bottom', '-4px', True),
            ('margin-left', '-4px', True),
        ),
    ),
    (
        '.m-n2',
        (
            ('margin-top', '-8px', True),
            ('margin-right', '-8px', True),
            ('margin-bottom', '-8px', True),
            ('margin-left', '-8px', True),
        ),
    ),
    (
        '.m-n3',
        (
            ('margin-top', '-16px', True),
            ('margin-right', '-16px', True),
            ('margin-bottom', '-16px', True),
            ('margin-left', '-16px', True),
        ),
    ),
    (
        '.m-n4',
        (
            ('margin-top', '-24px', True),
            ('margin-right', '-24px', True),
            ('margin-bottom', '-24px', True),
            ('margin-left', '-24px', True),
        ),
    ),
    (
        '.m-n5',
        (
            ('margin-top', '-48px', True),
            ('margin-right', '-48px', True),
            ('margin-bottom', '-48px', True),
            ('margin-left', '-48px', True),
        ),
    ),
    (
        '.my-n1',
        (
            ('margin-top', '-4px', True),
            ('margin-bottom', '-4px', True),
        ),
    ),
    (
        '.my-n2',
        (
            ('margin-top', '-8px', True),
            ('margin-bottom', '-8px', True),
        ),
    ),
    (
        '.my-n3',
        (
            ('margin-top', '-16px', True),
            ('margin-bottom', '-16px', True),
        ),
    ),
    (
        '.my-n4',
        (
            ('margin-top', '-24px', True),
            ('margin-bottom', '-24px', True),
        ),
    ),
    (
        '.my-n5',
        (
            ('margin-top', '-48px', True),
            ('margin-bottom', '-48px', True),
        ),
    ),
    (
        '.mt-n1',
        (
            ('margin-top', '-4px', True),
        ),
    ),
    (
        '.mt-n2',
        (
            ('margin-top', '-8px', True),
        ),
    ),
    (
        '.mt-n3',
        (
            ('margin-top', '-16px', True),
        ),
    ),
    (
        '.mt-n4',
        (
            ('margin-top', '-24px', True),
        ),
    ),
    (
        '.mt-n5',
        (
            ('margin-top', '-48px', True),
        ),
    ),
    (
        '.m-sm-0',
        (
            ('margin-top', '0', True),
            ('margin-right', '0', True),
            ('margin-bottom', '0', True),
            ('margin-left', '0', True),
        ),
    ),
    (
        '.m-sm-1',
        (
            ('margin-top', '4px', True),
            ('margin-right', '4px', True),
            ('margin-bottom', '4px', True),
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.m-sm-2',
        (
            ('margin-top', '8px', True),
            ('margin-right', '8px', True),
            ('margin-bottom', '8px', True),
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.m-sm-3',
        (
            ('margin-top', '16px', True),
            ('margin-right', '16px', True),
            ('margin-bottom', '16px', True),
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.m-sm-4',
        (
            ('margin-top', '24px', True),
            ('margin-right', '24px', True),
            ('margin-bottom', '24px', True),
            ('margin-left', '24px', True),
        ),
    ),
    (
        '.m-sm-5',
        (
            ('margin-top', '48px', True),
            ('margin-right', '48px', True),
            ('margin-bottom', '48px', True),
            ('margin-left', '48px', True),
        ),
    ),
    (
        '.m-sm-auto',
        (
            ('margin-top', 'auto', True),
            ('margin-right', 'auto', True),
            ('margin-bottom', 'auto', True),
            ('margin-left', 'auto', True),
        ),
    ),
    (
        '.my-sm-0',
        (
            ('margin-top', '0', True),
            ('margin-bottom', '0', True),
        ),
    ),
    (
        '.my-sm-1',
        (
            ('margin-top', '4px', True),
            ('margin-bottom', '4px', True),
        ),
    ),
    (
        '.my-sm-2',
        (
            ('margin-top', '8px', True),
            ('margin-bottom', '8px', True),
        ),
    ),
    (
        '.my-sm-3',
        (
            ('margin-top', '16px', True),
            ('margin-bottom', '16px', True),
        ),
    ),
    (
        '.my-sm-4',
        (
            ('margin-top', '24px', True),
            ('margin-bottom', '24px', True),
        ),
    ),
    (
        '.my-sm-5',
        (
            ('margin-top', '48px', True),
            ('margin-bottom', '48px', True),
        ),
    ),
    (
        '.my-sm-auto',
        (
            ('margin-top', 'auto', True),
            ('margin-bottom', 'auto', True),
        ),
    ),
    (
        '.mt-sm-0',
        (
            ('margin-top', '0', True),
        ),
    ),
    (
        '.mt-sm-1',
        (
            ('margin-top', '4px', True),
        ),
    ),
    (
        '.mt-sm-2',
        (
            ('margin-top', '8px', True),
        ),
    ),
    (
        '.mt-sm-3',
        (
            ('margin-top', '16px', True),
        ),
    ),
    (
        '.mt-sm-4',
        (
            ('margin-top', '24px', True),
        ),
    ),
    (
        '.mt-sm-5',
        (
            ('margin-top', '48px', True),
        ),
    ),
    (
        '.mt-sm-auto',
        (
            ('margin-top', 'auto', True),
        ),
    ),
    (
        '.m-sm-n1',
        (
            ('margin-top', '-4px', True),
            ('margin-right', '-4px', True),
            ('margin-bottom', '-4px', True),
            ('margin-left', '-4px', True),
        ),
    ),
    (
        '.m-sm-n2',
        (
            ('margin-top', '-8px', True),
            ('margin-right', '-8px', True),
            ('margin-bottom', '-8px', True),
            ('margin-left', '-8px', True),
        ),
    ),
    (
        '.m-sm-n3',
        (
            ('margin-top', '-16px', True),
            ('margin-right', '-16px', True),
            ('margin-bottom', '-16px', True),
            ('margin-left', '-16px', True),
        ),
    ),
    (
        '.m-sm-n4',
        (
            ('margin-top', '-24px', True),
            ('margin-right', '-24px', True),
            ('margin-bottom', '-24px', True),
            ('margin-left', '-24px', True),
        ),
    ),
    (
        '.m-sm-n5',
        (
            ('margin-top', '-48px', True),
            ('margin-right', '-48px', True),
            ('margin-bottom', '-48px', True),
            ('margin-left', '-48px', True),
        ),
    ),
    (
        '.my-sm-n1',
        (
            ('margin-top', '-4px', True),
            ('margin-bottom', '-4px', True),
        ),
    ),
    (
        '.my-sm-n2',
        (
            ('margin-top', '-8px', True),
            ('margin-bottom', '-8px', True),
        ),
    ),
    (
        '.my-sm-n3',
        (
            ('margin-top', '-16px', True),
            ('margin-bottom', '-16px', True),
        ),
    ),
    (
        '.my-sm-n4',
        (
            ('margin-top', '-24px', True),
            ('margin-bottom', '-24px', True),
        ),
    ),
    (
        '.my-sm-n5',
        (
            ('margin-top', '-48px', True),
            ('margin-bottom', '-48px', True),
        ),
    ),
    (
        '.mt-sm-n1',
        (
            ('margin-top', '-4px', True),
        ),
    ),
    (
        '.mt-sm-n2',
        (
            ('margin-top', '-8px', True),
        ),
    ),
    (
        '.mt-sm-n3',
        (
            ('margin-top', '-16px', True),
        ),
    ),
    (
        '.mt-sm-n4',
        (
            ('margin-top', '-24px', True),
        ),
    ),
    (
        '.mt-sm-n5',
        (
            ('margin-top', '-48px', True),
        ),
    ),
    (
        '.m-md-0',
        (
            ('margin-top', '0', True),
            ('margin-right', '0', True),
            ('margin-bottom', '0', True),
            ('margin-left', '0', True),
        ),
    ),
    (
        '.m-md-1',
        (
            ('margin-top', '4px', True),
            ('margin-right', '4px', True),
            ('margin-bottom', '4px', True),
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.m-md-2',
        (
            ('margin-top', '8px', True),
            ('margin-right', '8px', True),
            ('margin-bottom', '8px', True),
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.m-md-3',
        (
            ('margin-top', '16px', True),
            ('margin-right', '16px', True),
            ('margin-bottom', '16px', True),
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.m-md-4',
        (
            ('margin-top', '24px', True),
            ('margin-right', '24px', True),
            ('margin-bottom', '24px', True),
            ('margin-left', '24px', True),
        ),
    ),
    (
        '.m-md-5',
        (
            ('margin-top', '48px', True),
            ('margin-right', '48px', True),
            ('margin-bottom', '48px', True),
            ('margin-left', '48px', True),
        ),
    ),
    (
        '.m-md-auto',
        (
            ('margin-top', 'auto', True),
            ('margin-right', 'auto', True),
            ('margin-bottom', 'auto', True),
            ('margin-left', 'auto', True),
        ),
    ),
    (
        '.my-md-0',
        (
            ('margin-top', '0', True),
            ('margin-bottom', '0', True),
        ),
    ),
    (
        '.my-md-1',
        (
            ('margin-top', '4px', True),
            ('margin-bottom', '4px', True),
        ),
    ),
    (
        '.my-md-2',
        (
            ('margin-top', '8px', True),
            ('margin-bottom', '8px', True),
        ),
    ),
    (
        '.my-md-3',
        (
            ('margin-top', '16px', True),
            ('margin-bottom', '16px', True),
        ),
    ),
    (
        '.my-md-4',
        (
            ('margin-top', '24px', True),
            ('margin-bottom', '24px', True),
        ),
    ),
    (
        '.my-md-5',
        (
            ('margin-top', '48px', True),
            ('margin-bottom', '48px', True),
        ),
    ),
    (
        '.my-md-auto',
        (
            ('margin-top', 'auto', True),
            ('margin-bottom', 'auto', True),
        ),
    ),
    (
        '.mt-md-0',
        (
            ('margin-top', '0', True),
        ),
    ),
    (
        '.mt-md-1',
        (
            ('margin-top', '4px', True),
        ),
    ),
    (
        '.mt-md-2',
        (
            ('margin-top', '8px', True),
        ),
    ),
    (
        '.mt-md-3',
        (
            ('margin-top', '16px', True),
        ),
    ),
    (
        '.mt-md-4',
        (
            ('margin-top', '24px', True),
        ),
    ),
    (
        '.mt-md-5',
        (
            ('margin-top', '48px', True),
        ),
    ),
    (
        '.mt-md-auto',
        (
            ('margin-top', 'auto', True),
        ),
    ),
    (
        '.m-md-n1',
        (
            ('margin-top', '-4px', True),
            ('margin-right', '-4px', True),
            ('margin-bottom', '-4px', True),
            ('margin-left', '-4px', True),
        ),
    ),
    (
        '.m-md-n2',
        (
            ('margin-top', '-8px', True),
            ('margin-right', '-8px', True),
            ('margin-bottom', '-8px', True),
            ('margin-left', '-8px', True),
        ),
    ),
    (
        '.m-md-n3',
        (
            ('margin-top', '-16px', True),
            ('margin-right', '-16px', True),
            ('margin-bottom', '-16px', True),
            ('margin-left', '-16px', True),
        ),
    ),
    (
        '.m-md-n4',
        (
            ('margin-top', '-24px', True),
            ('margin-right', '-24px', True),
            ('margin-bottom', '-24px', True),
            ('margin-left', '-24px', True),
        ),
    ),
    (
        '.m-md-n5',
        (
            ('margin-top', '-48px', True),
            ('margin-right', '-48px', True),
            ('margin-bottom', '-48px', True),
            ('margin-left', '-48px', True),
        ),
    ),
    (
        '.my-md-n1',
        (
            ('margin-top', '-4px', True),
            ('margin-bottom', '-4px', True),
        ),
    ),
    (
        '.my-md-n2',
        (
            ('margin-top', '-8px', True),
            ('margin-bottom', '-8px', True),
        ),
    ),
    (
        '.my-md-n3',
        (
            ('margin-top', '-16px', True),
            ('margin-bottom', '-16px', True),
        ),
    ),
    (
        '.my-md-n4',
        (
            ('margin-top', '-24px', True),
            ('margin-bottom', '-24px', True),
        ),
    ),
    (
        '.my-md-n5',
        (
            ('margin-top', '-48px', True),
            ('margin-bottom', '-48px', True),
        ),
    ),
    (
        '.mt-md-n1',
        (
            ('margin-top', '-4px', True),
        ),
    ),
    (
        '.mt-md-n2',
        (
            ('margin-top', '-8px', True),
        ),
    ),
    (
        '.mt-md-n3',
        (
            ('margin-top', '-16px', True),
        ),
    ),
    (
        '.mt-md-n4',
        (
            ('margin-top', '-24px', True),
        ),
    ),
    (
        '.mt-md-n5',
        (
            ('margin-top', '-48px', True),
        ),
    ),
    (
        '.m-lg-0',
        (
            ('margin-top', '0', True),
            ('margin-right', '0', True),
            ('margin-bottom', '0', True),
            ('margin-left', '0', True),
        ),
    ),
    (
        '.m-lg-1',
        (
            ('margin-top', '4px', True),
            ('margin-right', '4px', True),
            ('margin-bottom', '4px', True),
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.m-lg-2',
        (
            ('margin-top', '8px', True),
            ('margin-right', '8px', True),
            ('margin-bottom', '8px', True),
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.m-lg-3',
        (
            ('margin-top', '16px', True),
            ('margin-right', '16px', True),
            ('margin-bottom', '16px', True),
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.m-lg-4',
        (
            ('margin-top', '24px', True),
            ('margin-right', '24px', True),
            ('margin-bottom', '24px', True),
            ('margin-left', '24px', True),
        ),
    ),
    (
        '.m-lg-5',
        (
            ('margin-top', '48px', True),
            ('margin-right', '48px', True),
            ('margin-bottom', '48px', True),
            ('margin-left', '48px', True),
        ),
    ),
    (
        '.m-lg-auto',
        (
            ('margin-top', 'auto', True),
            ('margin-right', 'auto', True),
            ('margin-bottom', 'auto', True),
            ('margin-left', 'auto', True),
        ),
    ),
    (
        '.my-lg-0',
        (
            ('margin-top', '0', True),
            ('margin-bottom', '0', True),
        ),
    ),
    (
        '.my-lg-1',
        (
            ('margin-top', '4px', True),
            ('margin-bottom', '4px', True),
        ),
    ),
    (
        '.my-lg-2',
        (
            ('margin-top', '8px', True),
            ('margin-bottom', '8px', True),
        ),
    ),
    (
        '.my-lg-3',
        (
            ('margin-top', '16px', True),
            ('margin-bottom', '16px', True),
        ),
    ),
    (
        '.my-lg-4',
        (
            ('margin-top', '24px', True),
            ('margin-bottom', '24px', True),
        ),
    ),
    (
        '.my-lg-5',
        (
            ('margin-top', '48px', True),
            ('margin-bottom', '48px', True),
        ),
    ),
    (
        '.my-lg-auto',
        (
            ('margin-top', 'auto', True),
            ('margin-bottom', 'auto', True),
        ),
    ),
    (
        '.mt-lg-0',
        (
            ('margin-top', '0', True),
        ),
    ),
    (
        '.mt-lg-1',
        (
            ('margin-top', '4px', True),
        ),
    ),
    (
        '.mt-lg-2',
        (
            ('margin-top', '8px', True),
        ),
    ),
    (
        '.mt-lg-3',
        (
            ('margin-top', '16px', True),
        ),
    ),
    (
        '.mt-lg-4',
        (
            ('margin-top', '24px', True),
        ),
    ),
    (
        '.mt-lg-5',
        (
            ('margin-top', '48px', True),
        ),
    ),
    (
        '.mt-lg-auto',
        (
            ('margin-top', 'auto', True),
        ),
    ),
    (
        '.m-lg-n1',
        (
            ('margin-top', '-4px', True),
            ('margin-right', '-4px', True),
            ('margin-bottom', '-4px', True),
            ('margin-left', '-4px', True),
        ),
    ),
    (
        '.m-lg-n2',
        (
            ('margin-top', '-8px', True),
            ('margin-right', '-8px', True),
            ('margin-bottom', '-8px', True),
            ('margin-left', '-8px', True),
        ),
    ),
    (
        '.m-lg-n3',
        (
            ('margin-top', '-16px', True),
            ('margin-right', '-16px', True),
            ('margin-bottom', '-16px', True),
            ('margin-left', '-16px', True),
        ),
    ),
    (
        '.m-lg-n4',
        (
            ('margin-top', '-24px', True),
            ('margin-right', '-24px', True),
            ('margin-bottom', '-24px', True),
            ('margin-left', '-24px', True),
        ),
    ),
    (
        '.m-lg-n5',
        (
            ('margin-top', '-48px', True),
            ('margin-right', '-48px', True),
            ('margin-bottom', '-48px', True),
            ('margin-left', '-48px', True),
        ),
    ),
    (
        '.my-lg-n1',
        (
            ('margin-top', '-4px', True),
            ('margin-bottom', '-4px', True),
        ),
    ),
    (
        '.my-lg-n2',
        (
            ('margin-top', '-8px', True),
            ('margin-bottom', '-8px', True),
        ),
    ),
    (
        '.my-lg-n3',
        (
            ('margin-top', '-16px', True),
            ('margin-bottom', '-16px', True),
        ),
    ),
    (
        '.my-lg-n4',
        (
            ('margin-top', '-24px', True),
            ('margin-bottom', '-24px', True),
        ),
    ),
    (
        '.my-lg-n5',
        (
            ('margin-top', '-48px', True),
            ('margin-bottom', '-48px', True),
        ),
    ),
    (
        '.mt-lg-n1',
        (
            ('margin-top', '-4px', True),
        ),
    ),
    (
        '.mt-lg-n2',
        (
            ('margin-top', '-8px', True),
        ),
    ),
    (
        '.mt-lg-n3',
        (
            ('margin-top', '-16px', True),
        ),
    ),
    (
        '.mt-lg-n4',
        (
            ('margin-top', '-24px', True),
        ),
    ),
    (
        '.mt-lg-n5',
        (
            ('margin-top', '-48px', True),
        ),
    ),
    (
        '.m-xl-0',
        (
            ('margin-top', '0', True),
            ('margin-right', '0', True),
            ('margin-bottom', '0', True),
            ('margin-left', '0', True),
        ),
    ),
    (
        '.m-xl-1',
        (
            ('margin-top', '4px', True),
            ('margin-right', '4px', True),
            ('margin-bottom', '4px', True),
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.m-xl-2',
        (
            ('margin-top', '8px', True),
            ('margin-right', '8px', True),
            ('margin-bottom', '8px', True),
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.m-xl-3',
        (
            ('margin-top', '16px', True),
            ('margin-right', '16px', True),
            ('margin-bottom', '16px', True),
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.m-xl-4',
        (
            ('margin-top', '24px', True),
            ('margin-right', '24px', True),
            ('margin-bottom', '24px', True),
            ('margin-left', '24px', True),
        ),
    ),
    (
        '.m-xl-5',
        (
            ('margin-top', '48px', True),
            ('margin-right', '48px', True),
            ('margin-bottom', '48px', True),
            ('margin-left', '48px', True),
        ),
    ),
    (
        '.m-xl-auto',
        (
            ('margin-top', 'auto', True),
            ('margin-right', 'auto', True),
            ('margin-bottom', 'auto', True),
            ('margin-left', 'auto', True),
        ),
    ),
    (
        '.my-xl-0',
        (
            ('margin-top', '0', True),
            ('margin-bottom', '0', True),
        ),
    ),
    (
        '.my-xl-1',
        (
            ('margin-top', '4px', True),
            ('margin-bottom', '4px', True),
        ),
    ),
    (
        '.my-xl-2',
        (
            ('margin-top', '8px', True),
            ('margin-bottom', '8px', True),
        ),
    ),
    (
        '.my-xl-3',
        (
            ('margin-top', '16px', True),
            ('margin-bottom', '16px', True),
        ),
    ),
    (
        '.my-xl-4',
        (
            ('margin-top', '24px', True),
            ('margin-bottom', '24px', True),
        ),
    ),
    (
        '.my-xl-5',
        (
            ('margin-top', '48px', True),
            ('margin-bottom', '48px', True),
        ),
    ),
    (
        '.my-xl-auto',
        (
            ('margin-top', 'auto', True),
            ('margin-bottom', 'auto', True),
        ),
    ),
    (
        '.mt-xl-0',
        (
            ('margin-top', '0', True),
        ),
    ),
    (
        '.mt-xl-1',
        (
            ('margin-top', '4px', True),
        ),
    ),
    (
        '.mt-xl-2',
        (
            ('margin-top', '8px', True),
        ),
    ),
    (
        '.mt-xl-3',
        (
            ('margin-top', '16px', True),
        ),
    ),
    (
        '.mt-xl-4',
        (
            ('margin-top', '24px', True),
        ),
    ),
    (
        '.mt-xl-5',
        (
            ('margin-top', '48px', True),
        ),
    ),
    (
        '.mt-xl-auto',
        (
            ('margin-top', 'auto', True),
        ),
    ),
    (
        '.m-xl-n1',
        (
            ('margin-top', '-4px', True),
            ('margin-right', '-4px', True),
            ('margin-bottom', '-4px', True),
            ('margin-left', '-4px', True),
        ),
    ),
    (
        '.m-xl-n2',
        (
            ('margin-top', '-8px', True),
            ('margin-right', '-8px', True),
            ('margin-bottom', '-8px', True),
            ('margin-left', '-8px', True),
        ),
    ),
    (
        '.m-xl-n3',
        (
            ('margin-top', '-16px', True),
            ('margin-right', '-16px', True),
            ('margin-bottom', '-16px', True),
            ('margin-left', '-16px', True),
        ),
    ),
    (
        '.m-xl-n4',
        (
            ('margin-top', '-24px', True),
            ('margin-right', '-24px', True),
            ('margin-bottom', '-24px', True),
            ('margin-left', '-24px', True),
        ),
    ),
    (
        '.m-xl-n5',
        (
            ('margin-top', '-48px', True),
            ('margin-right', '-48px', True),
            ('margin-bottom', '-48px', True),
            ('margin-left', '-48px', True),
        ),
    ),
    (
        '.my-xl-n1',
        (
            ('margin-top', '-4px', True),
            ('margin-bottom', '-4px', True),
        ),
    ),
    (
        '.my-xl-n2',
        (
            ('margin-top', '-8px', True),
            ('margin-bottom', '-8px', True),
        ),
    ),
    (
        '.my-xl-n3',
        (
            ('margin-top', '-16px', True),
            ('margin-bottom', '-16px', True),
        ),
    ),
    (
        '.my-xl-n4',
        (
            ('margin-top', '-24px', True),
            ('margin-bottom', '-24px', True),
        ),
    ),
    (
        '.my-xl-n5',
        (
            ('margin-top', '-48px', True),
            ('margin-bottom', '-48px', True),
        ),
    ),
    (
        '.mt-xl-n1',
        (
            ('margin-top', '-4px', True),
        ),
    ),
    (
        '.mt-xl-n2',
        (
            ('margin-top', '-8px', True),
        ),
    ),
    (
        '.mt-xl-n3',
        (
            ('margin-top', '-16px', True),
        ),
    ),
    (
        '.mt-xl-n4',
        (
            ('margin-top', '-24px', True),
        ),
    ),
    (
        '.mt-xl-n5',
        (
            ('margin-top', '-48px', True),
        ),
    ),
    (
        '.m-xxl-0',
        (
            ('margin-top', '0', True),
            ('margin-right', '0', True),
            ('margin-bottom', '0', True),
            ('margin-left', '0', True),
        ),
    ),
    (
        '.m-xxl-1',
        (
            ('margin-top', '4px', True),
            ('margin-right', '4px', True),
            ('margin-bottom', '4px', True),
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.m-xxl-2',
        (
            ('margin-top', '8px', True),
            ('margin-right', '8px', True),
            ('margin-bottom', '8px', True),
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.m-xxl-3',
        (
            ('margin-top', '16px', True),
            ('margin-right', '16px', True),
            ('margin-bottom', '16px', True),
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.m-xxl-4',
        (
            ('margin-top', '24px', True),
            ('margin-right', '24px', True),
            ('margin-bottom', '24px', True),
            ('margin-left', '24px', True),
        ),
    ),
    (
        '.m-xxl-5',
        (
            ('margin-top', '48px', True),
            ('margin-right', '48px', True),
            ('margin-bottom', '48px', True),
            ('margin-left', '48px', True),
        ),
    ),
    (
        '.m-xxl-auto',
        (
            ('margin-top', 'auto', True),
            ('margin-right', 'auto', True),
            ('margin-bottom', 'auto', True),
            ('margin-left', 'auto', True),
        ),
    ),
    (
        '.my-xxl-0',
        (
            ('margin-top', '0', True),
            ('margin-bottom', '0', True),
        ),
    ),
    (
        '.my-xxl-1',
        (
            ('margin-top', '4px', True),
            ('margin-bottom', '4px', True),
        ),
    ),
    (
        '.my-xxl-2',
        (
            ('margin-top', '8px', True),
            ('margin-bottom', '8px', True),
        ),
    ),
    (
        '.my-xxl-3',
        (
            ('margin-top', '16px', True),
            ('margin-bottom', '16px', True),
        ),
    ),
    (
        '.my-xxl-4',
        (
            ('margin-top', '24px', True),
            ('margin-bottom', '24px', True),
        ),
    ),
    (
        '.my-xxl-5',
        (
            ('margin-top', '48px', True),
            ('margin-bottom', '48px', True),
        ),
    ),
    (
        '.my-xxl-auto',
        (
            ('margin-top', 'auto', True),
            ('margin-bottom', 'auto', True),
        ),
    ),
    (
        '.mt-xxl-0',
        (
            ('margin-top', '0', True),
        ),
    ),
    (
        '.mt-xxl-1',
        (
            ('margin-top', '4px', True),
        ),
    ),
    (
        '.mt-xxl-2',
        (
            ('margin-top', '8px', True),
        ),
    ),
    (
        '.mt-xxl-3',
        (
            ('margin-top', '16px', True),
        ),
    ),
    (
        '.mt-xxl-4',
        (
            ('margin-top', '24px', True),
        ),
    ),
    (
        '.mt-xxl-5',
        (
            ('margin-top', '48px', True),
        ),
    ),
    (
        '.mt-xxl-auto',
        (
            ('margin-top', 'auto', True),
        ),
    ),
    (
        '.m-xxl-n1',
        (
            ('margin-top', '-4px', True),
            ('margin-right', '-4px', True),
            ('margin-bottom', '-4px', True),
            ('margin-left', '-4px', True),
        ),
    ),
    (
        '.m-xxl-n2',
        (
            ('margin-top', '-8px', True),
            ('margin-right', '-8px', True),
            ('margin-bottom', '-8px', True),
            ('margin-left', '-8px', True),
        ),
    ),
    (
        '.m-xxl-n3',
        (
            ('margin-top', '-16px', True),
            ('margin-right', '-16px', True),
            ('margin-bottom', '-16px', True),
            ('margin-left', '-16px', True),
        ),
    ),
    (
        '.m-xxl-n4',
        (
            ('margin-top', '-24px', True),
            ('margin-right', '-24px', True),
            ('margin-bottom', '-24px', True),
            ('margin-left', '-24px', True),
        ),
    ),
    (
        '.m-xxl-n5',
        (
            ('margin-top', '-48px', True),
            ('margin-right', '-48px', True),
            ('margin-bottom', '-48px', True),
            ('margin-left', '-48px', True),
        ),
    ),
    (
        '.my-xxl-n1',
        (
            ('margin-top', '-4px', True),
            ('margin-bottom', '-4px', True),
        ),
    ),
    (
        '.my-xxl-n2',
        (
            ('margin-top', '-8px', True),
            ('margin-bottom', '-8px', True),
        ),
    ),
    (
        '.my-xxl-n3',
        (
            ('margin-top', '-16px', True),
            ('margin-bottom', '-16px', True),
        ),
    ),
    (
        '.my-xxl-n4',
        (
            ('margin-top', '-24px', True),
            ('margin-bottom', '-24px', True),
        ),
    ),
    (
        '.my-xxl-n5',
        (
            ('margin-top', '-48px', True),
            ('margin-bottom', '-48px', True),
        ),
    ),
    (
        '.mt-xxl-n1',
        (
            ('margin-top', '-4px', True),
        ),
    ),
    (
        '.mt-xxl-n2',
        (
            ('margin-top', '-8px', True),
        ),
    ),
    (
        '.mt-xxl-n3',
        (
            ('margin-top', '-16px', True),
        ),
    ),
    (
        '.mt-xxl-n4',
        (
            ('margin-top', '-24px', True),
        ),
    ),
    (
        '.mt-xxl-n5',
        (
            ('margin-top', '-48px', True),
        ),
    ),
    (
        ':not(.s_popup) > .modal .modal-dialog',
        (
            ('margin-top', '0', False),
            ('margin-right', 'auto', False),
            ('margin-bottom', '0', False),
            ('margin-left', 'auto', False),
        ),
    ),
    (
        '.openerp .oe_form .oe_styling_v8',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.oe_page',
        (
            ('margin-top', '0px', False),
            ('margin-right', 'auto', False),
            ('margin-bottom', '64px', False),
            ('margin-left', 'auto', False),
        ),
    ),
    (
        '.oe_row',
        (
            ('margin-top', '16px', False),
            ('margin-bottom', '16px', False),
            ('margin-left', 'auto', False),
            ('margin-right', 'auto', False),
        ),
    ),
    (
        '.oe_mt0',
        (
            ('margin-top', '0px', True),
        ),
    ),
    (
        '.oe_mt4',
        (
            ('margin-top', '4px', True),
        ),
    ),
    (
        '.oe_mt8',
        (
            ('margin-top', '8px', True),
        ),
    ),
    (
        '.oe_mt16',
        (
            ('margin-top', '16px', True),
        ),
    ),
    (
        '.oe_mt32',
        (
            ('margin-top', '32px', True),
        ),
    ),
    (
        '.oe_mt48',
        (
            ('margin-top', '48px', True),
        ),
    ),
    (
        '.oe_mt64',
        (
            ('margin-top', '64px', True),
        ),
    ),
    (
        '.oe_spaced',
        (
            ('margin-top', '32px', False),
            ('margin-bottom', '32px', False),
        ),
    ),
    (
        '.oe_more_spaced',
        (
            ('margin-top', '64px', False),
            ('margin-bottom', '64px', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_slogan',
        (
            ('margin-top', '32px', False),
            ('margin-bottom', '32px', False),
        ),
    ),
    (
        '.oe_styling_v8 h1.oe_slogan',
        (
            ('margin-top', '48px', False),
            ('margin-bottom', '48px', False),
        ),
    ),
    (
        '.oe_styling_v8 h4.oe_slogan:before, .oe_styling_v8 h4.oe_slogan:after',
        (
            ('margin-top', '0', False),
            ('margin-right', '20px', False),
            ('margin-bottom', '0', False),
            ('margin-left', '20px', False),
        ),
    ),
    (
        '.oe_quote',
        (
            ('margin-top', '8px', False),
            ('margin-right', '8px', False),
            ('margin-bottom', '8px', False),
            ('margin-left', '8px', False),
        ),
    ),
    (
        '.oe_quote .oe_q, .oe_quote q',
        (
            ('margin-top', '10px', False),
            ('margin-right', '10px', False),
            ('margin-bottom', '10px', False),
            ('margin-left', '10px', False),
        ),
    ),
    (
        '.oe_quote cite',
        (
            ('margin-top', '16px', False),
        ),
    ),
    (
        '.oe_picture',
        (
            ('margin-top', '16px', False),
            ('margin-right', '8%', False),
            ('margin-bottom', '16px', False),
            ('margin-left', '8%', False),
        ),
    ),
    (
        '.oe_pic_ctr > img.oe_picture',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_pic_ctr > .oe_title',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        'div.oe_demo span.oe_demo_play',
        (
            ('margin-top', '-30px', False),
            ('margin-left', '-40px', False),
        ),
    ),
    (
        '.oe_row_tabs',
        (
            ('margin-top', '0px', False),
            ('margin-bottom', '0px', False),
        ),
    ),
    (
        '.oe_row_tab',
        (
            ('margin-top', '0px', False),
            ('margin-right', '-2px', False),
            ('margin-bottom', '0px', False),
            ('margin-left', '-2px', False),
        ),
    ),
    (
        '.oe_calltoaction',
        (
            ('margin-top', '-32px', False),
        ),
    ),
    (
        '.visually-hidden',
        (
            ('margin-top', '-1px', False),
            ('margin-right', '-1px', False),
            ('margin-bottom', '-1px', False),
            ('margin-left', '-1px', False),
        ),
    ),
    (
        '.o_report_layout_bubble #informations',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.o_report_layout_wave #informations',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row',
        (
            ('margin-top', '0', True),
            ('margin-right', '0', True),
            ('margin-bottom', '0', True),
            ('margin-left', '0', True),
        ),
    ),
    (
        'div.media_iframe_video',
        (
            ('margin-top', '0', False),
            ('margin-right', 'auto', False),
            ('margin-bottom', '0', False),
            ('margin-left', 'auto', False),
        ),
    ),
    (
        'div.media_iframe_video iframe',
        (
            ('margin-top', '0', False),
            ('margin-right', 'auto', False),
            ('margin-bottom', '0', False),
            ('margin-left', 'auto', False),
        ),
    ),
    (
        'address .fa.fa-mobile-phone',
        (
            ('margin-top', '0', False),
            ('margin-right', '3px', False),
            ('margin-bottom', '0', False),
            ('margin-left', '2px', False),
        ),
    ),
    (
        '.mt0',
        (
            ('margin-top', '0px', True),
        ),
    ),
    (
        '.mt8',
        (
            ('margin-top', '8px', True),
        ),
    ),
    (
        '.mt16',
        (
            ('margin-top', '16px', True),
        ),
    ),
    (
        '.mt24',
        (
            ('margin-top', '24px', True),
        ),
    ),
    (
        '.mt32',
        (
            ('margin-top', '32px', True),
        ),
    ),
    (
        '.mt40',
        (
            ('margin-top', '40px', True),
        ),
    ),
    (
        '.mt48',
        (
            ('margin-top', '48px', True),
        ),
    ),
    (
        '.mt56',
        (
            ('margin-top', '56px', True),
        ),
    ),
    (
        '.mt64',
        (
            ('margin-top', '64px', True),
        ),
    ),
    (
        '.mt72',
        (
            ('margin-top', '72px', True),
        ),
    ),
    (
        '.mt80',
        (
            ('margin-top', '80px', True),
        ),
    ),
    (
        '.mt88',
        (
            ('margin-top', '88px', True),
        ),
    ),
    (
        '.mt96',
        (
            ('margin-top', '96px', True),
        ),
    ),
    (
        '.mt104',
        (
            ('margin-top', '104px', True),
        ),
    ),
    (
        '.mt112',
        (
            ('margin-top', '112px', True),
        ),
    ),
    (
        '.mt120',
        (
            ('margin-top', '120px', True),
        ),
    ),
    (
        '.mt128',
        (
            ('margin-top', '128px', True),
        ),
    ),
    (
        '.mt136',
        (
            ('margin-top', '136px', True),
        ),
    ),
    (
        '.mt144',
        (
            ('margin-top', '144px', True),
        ),
    ),
    (
        '.mt152',
        (
            ('margin-top', '152px', True),
        ),
    ),
    (
        '.mt160',
        (
            ('margin-top', '160px', True),
        ),
    ),
    (
        '.mt168',
        (
            ('margin-top', '168px', True),
        ),
    ),
    (
        '.mt176',
        (
            ('margin-top', '176px', True),
        ),
    ),
    (
        '.mt184',
        (
            ('margin-top', '184px', True),
        ),
    ),
    (
        '.mt192',
        (
            ('margin-top', '192px', True),
        ),
    ),
    (
        '.mt200',
        (
            ('margin-top', '200px', True),
        ),
    ),
    (
        '.mt208',
        (
            ('margin-top', '208px', True),
        ),
    ),
    (
        '.mt216',
        (
            ('margin-top', '216px', True),
        ),
    ),
    (
        '.mt224',
        (
            ('margin-top', '224px', True),
        ),
    ),
    (
        '.mt232',
        (
            ('margin-top', '232px', True),
        ),
    ),
    (
        '.mt240',
        (
            ('margin-top', '240px', True),
        ),
    ),
    (
        '.mt248',
        (
            ('margin-top', '248px', True),
        ),
    ),
    (
        '.mt256',
        (
            ('margin-top', '256px', True),
        ),
    ),
    (
        '.mt4',
        (
            ('margin-top', '4px', True),
        ),
    ),
    (
        '.mt92',
        (
            ('margin-top', '92px', True),
        ),
    ),
    (
        '.o_nocontent_help',
        (
            ('margin-top', 'auto', False),
            ('margin-right', 'auto', False),
            ('margin-bottom', 'auto', False),
            ('margin-left', 'auto', False),
        ),
    ),
    (
        '.o_nocontent_help > p:first-of-type',
        (
            ('margin-top', '0', False),
        ),
    ),
    (
        '.ui-autocomplete .ui-menu-item > .ui-state-active',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_legend_line',
        (
            ('margin-right', '20px', False),
            ('margin-left', '20px', False),
            ('margin-top', '15px', False),
        ),
    ),
    (
        '[name="so_total_summary"] div#total',
        (
            ('margin-top', '0', False),
            ('margin-right', '0', False),
            ('margin-bottom', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.list-inline-item:not(:last-child)',
        (
            ('margin-right', '0.5rem', False),
        ),
    ),
    (
        '.container, .o_container_small, .container-fluid, .container-xxl, .container-xl, .container-lg, .container-md, .container-sm',
        (
            ('margin-right', 'auto', False),
            ('margin-left', 'auto', False),
        ),
    ),
    (
        '.form-check-reverse .form-check-input',
        (
            ('margin-right', '-1.5em', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.form-switch.form-check-reverse .form-check-input',
        (
            ('margin-right', '-2.5em', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.form-check-inline',
        (
            ('margin-right', '1rem', False),
        ),
    ),
    (
        '.dropstart .dropdown-toggle::before',
        (
            ('margin-right', '3.4px', False),
        ),
    ),
    (
        '.dropdown-divider',
        (
            ('margin-right', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.dropstart .dropdown-toggle-split::before',
        (
            ('margin-right', '0', False),
        ),
    ),
    (
        '.card > hr',
        (
            ('margin-right', '0', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        '.modal-dialog',
        (
            ('margin-right', 'auto', False),
            ('margin-left', 'auto', False),
        ),
    ),
    (
        '.carousel-item',
        (
            ('margin-right', '-100%', False),
        ),
    ),
    (
        '.carousel-indicators',
        (
            ('margin-right', '15%', False),
            ('margin-bottom', '1rem', False),
            ('margin-left', '15%', False),
        ),
    ),
    (
        '.carousel-indicators [data-bs-target]',
        (
            ('margin-right', '3px', False),
            ('margin-left', '3px', False),
        ),
    ),
    (
        '.mx-0',
        (
            ('margin-right', '0', True),
            ('margin-left', '0', True),
        ),
    ),
    (
        '.mx-1',
        (
            ('margin-right', '4px', True),
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.mx-2',
        (
            ('margin-right', '8px', True),
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.mx-3',
        (
            ('margin-right', '16px', True),
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.mx-4',
        (
            ('margin-right', '24px', True),
            ('margin-left', '24px', True),
        ),
    ),
    (
        '.mx-5',
        (
            ('margin-right', '48px', True),
            ('margin-left', '48px', True),
        ),
    ),
    (
        '.mx-auto',
        (
            ('margin-right', 'auto', True),
            ('margin-left', 'auto', True),
        ),
    ),
    (
        '.me-0',
        (
            ('margin-right', '0', True),
        ),
    ),
    (
        '.me-1',
        (
            ('margin-right', '4px', True),
        ),
    ),
    (
        '.me-2',
        (
            ('margin-right', '8px', True),
        ),
    ),
    (
        '.me-3',
        (
            ('margin-right', '16px', True),
        ),
    ),
    (
        '.me-4',
        (
            ('margin-right', '24px', True),
        ),
    ),
    (
        '.me-5',
        (
            ('margin-right', '48px', True),
        ),
    ),
    (
        '.me-auto',
        (
            ('margin-right', 'auto', True),
        ),
    ),
    (
        '.mx-n1',
        (
            ('margin-right', '-4px', True),
            ('margin-left', '-4px', True),
        ),
    ),
    (
        '.mx-n2',
        (
            ('margin-right', '-8px', True),
            ('margin-left', '-8px', True),
        ),
    ),
    (
        '.mx-n3',
        (
            ('margin-right', '-16px', True),
            ('margin-left', '-16px', True),
        ),
    ),
    (
        '.mx-n4',
        (
            ('margin-right', '-24px', True),
            ('margin-left', '-24px', True),
        ),
    ),
    (
        '.mx-n5',
        (
            ('margin-right', '-48px', True),
            ('margin-left', '-48px', True),
        ),
    ),
    (
        '.me-n1',
        (
            ('margin-right', '-4px', True),
        ),
    ),
    (
        '.me-n2',
        (
            ('margin-right', '-8px', True),
        ),
    ),
    (
        '.me-n3',
        (
            ('margin-right', '-16px', True),
        ),
    ),
    (
        '.me-n4',
        (
            ('margin-right', '-24px', True),
        ),
    ),
    (
        '.me-n5',
        (
            ('margin-right', '-48px', True),
        ),
    ),
    (
        '.mx-sm-0',
        (
            ('margin-right', '0', True),
            ('margin-left', '0', True),
        ),
    ),
    (
        '.mx-sm-1',
        (
            ('margin-right', '4px', True),
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.mx-sm-2',
        (
            ('margin-right', '8px', True),
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.mx-sm-3',
        (
            ('margin-right', '16px', True),
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.mx-sm-4',
        (
            ('margin-right', '24px', True),
            ('margin-left', '24px', True),
        ),
    ),
    (
        '.mx-sm-5',
        (
            ('margin-right', '48px', True),
            ('margin-left', '48px', True),
        ),
    ),
    (
        '.mx-sm-auto',
        (
            ('margin-right', 'auto', True),
            ('margin-left', 'auto', True),
        ),
    ),
    (
        '.me-sm-0',
        (
            ('margin-right', '0', True),
        ),
    ),
    (
        '.me-sm-1',
        (
            ('margin-right', '4px', True),
        ),
    ),
    (
        '.me-sm-2',
        (
            ('margin-right', '8px', True),
        ),
    ),
    (
        '.me-sm-3',
        (
            ('margin-right', '16px', True),
        ),
    ),
    (
        '.me-sm-4',
        (
            ('margin-right', '24px', True),
        ),
    ),
    (
        '.me-sm-5',
        (
            ('margin-right', '48px', True),
        ),
    ),
    (
        '.me-sm-auto',
        (
            ('margin-right', 'auto', True),
        ),
    ),
    (
        '.mx-sm-n1',
        (
            ('margin-right', '-4px', True),
            ('margin-left', '-4px', True),
        ),
    ),
    (
        '.mx-sm-n2',
        (
            ('margin-right', '-8px', True),
            ('margin-left', '-8px', True),
        ),
    ),
    (
        '.mx-sm-n3',
        (
            ('margin-right', '-16px', True),
            ('margin-left', '-16px', True),
        ),
    ),
    (
        '.mx-sm-n4',
        (
            ('margin-right', '-24px', True),
            ('margin-left', '-24px', True),
        ),
    ),
    (
        '.mx-sm-n5',
        (
            ('margin-right', '-48px', True),
            ('margin-left', '-48px', True),
        ),
    ),
    (
        '.me-sm-n1',
        (
            ('margin-right', '-4px', True),
        ),
    ),
    (
        '.me-sm-n2',
        (
            ('margin-right', '-8px', True),
        ),
    ),
    (
        '.me-sm-n3',
        (
            ('margin-right', '-16px', True),
        ),
    ),
    (
        '.me-sm-n4',
        (
            ('margin-right', '-24px', True),
        ),
    ),
    (
        '.me-sm-n5',
        (
            ('margin-right', '-48px', True),
        ),
    ),
    (
        '.mx-md-0',
        (
            ('margin-right', '0', True),
            ('margin-left', '0', True),
        ),
    ),
    (
        '.mx-md-1',
        (
            ('margin-right', '4px', True),
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.mx-md-2',
        (
            ('margin-right', '8px', True),
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.mx-md-3',
        (
            ('margin-right', '16px', True),
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.mx-md-4',
        (
            ('margin-right', '24px', True),
            ('margin-left', '24px', True),
        ),
    ),
    (
        '.mx-md-5',
        (
            ('margin-right', '48px', True),
            ('margin-left', '48px', True),
        ),
    ),
    (
        '.mx-md-auto',
        (
            ('margin-right', 'auto', True),
            ('margin-left', 'auto', True),
        ),
    ),
    (
        '.me-md-0',
        (
            ('margin-right', '0', True),
        ),
    ),
    (
        '.me-md-1',
        (
            ('margin-right', '4px', True),
        ),
    ),
    (
        '.me-md-2',
        (
            ('margin-right', '8px', True),
        ),
    ),
    (
        '.me-md-3',
        (
            ('margin-right', '16px', True),
        ),
    ),
    (
        '.me-md-4',
        (
            ('margin-right', '24px', True),
        ),
    ),
    (
        '.me-md-5',
        (
            ('margin-right', '48px', True),
        ),
    ),
    (
        '.me-md-auto',
        (
            ('margin-right', 'auto', True),
        ),
    ),
    (
        '.mx-md-n1',
        (
            ('margin-right', '-4px', True),
            ('margin-left', '-4px', True),
        ),
    ),
    (
        '.mx-md-n2',
        (
            ('margin-right', '-8px', True),
            ('margin-left', '-8px', True),
        ),
    ),
    (
        '.mx-md-n3',
        (
            ('margin-right', '-16px', True),
            ('margin-left', '-16px', True),
        ),
    ),
    (
        '.mx-md-n4',
        (
            ('margin-right', '-24px', True),
            ('margin-left', '-24px', True),
        ),
    ),
    (
        '.mx-md-n5',
        (
            ('margin-right', '-48px', True),
            ('margin-left', '-48px', True),
        ),
    ),
    (
        '.me-md-n1',
        (
            ('margin-right', '-4px', True),
        ),
    ),
    (
        '.me-md-n2',
        (
            ('margin-right', '-8px', True),
        ),
    ),
    (
        '.me-md-n3',
        (
            ('margin-right', '-16px', True),
        ),
    ),
    (
        '.me-md-n4',
        (
            ('margin-right', '-24px', True),
        ),
    ),
    (
        '.me-md-n5',
        (
            ('margin-right', '-48px', True),
        ),
    ),
    (
        '.mx-lg-0',
        (
            ('margin-right', '0', True),
            ('margin-left', '0', True),
        ),
    ),
    (
        '.mx-lg-1',
        (
            ('margin-right', '4px', True),
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.mx-lg-2',
        (
            ('margin-right', '8px', True),
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.mx-lg-3',
        (
            ('margin-right', '16px', True),
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.mx-lg-4',
        (
            ('margin-right', '24px', True),
            ('margin-left', '24px', True),
        ),
    ),
    (
        '.mx-lg-5',
        (
            ('margin-right', '48px', True),
            ('margin-left', '48px', True),
        ),
    ),
    (
        '.mx-lg-auto',
        (
            ('margin-right', 'auto', True),
            ('margin-left', 'auto', True),
        ),
    ),
    (
        '.me-lg-0',
        (
            ('margin-right', '0', True),
        ),
    ),
    (
        '.me-lg-1',
        (
            ('margin-right', '4px', True),
        ),
    ),
    (
        '.me-lg-2',
        (
            ('margin-right', '8px', True),
        ),
    ),
    (
        '.me-lg-3',
        (
            ('margin-right', '16px', True),
        ),
    ),
    (
        '.me-lg-4',
        (
            ('margin-right', '24px', True),
        ),
    ),
    (
        '.me-lg-5',
        (
            ('margin-right', '48px', True),
        ),
    ),
    (
        '.me-lg-auto',
        (
            ('margin-right', 'auto', True),
        ),
    ),
    (
        '.mx-lg-n1',
        (
            ('margin-right', '-4px', True),
            ('margin-left', '-4px', True),
        ),
    ),
    (
        '.mx-lg-n2',
        (
            ('margin-right', '-8px', True),
            ('margin-left', '-8px', True),
        ),
    ),
    (
        '.mx-lg-n3',
        (
            ('margin-right', '-16px', True),
            ('margin-left', '-16px', True),
        ),
    ),
    (
        '.mx-lg-n4',
        (
            ('margin-right', '-24px', True),
            ('margin-left', '-24px', True),
        ),
    ),
    (
        '.mx-lg-n5',
        (
            ('margin-right', '-48px', True),
            ('margin-left', '-48px', True),
        ),
    ),
    (
        '.me-lg-n1',
        (
            ('margin-right', '-4px', True),
        ),
    ),
    (
        '.me-lg-n2',
        (
            ('margin-right', '-8px', True),
        ),
    ),
    (
        '.me-lg-n3',
        (
            ('margin-right', '-16px', True),
        ),
    ),
    (
        '.me-lg-n4',
        (
            ('margin-right', '-24px', True),
        ),
    ),
    (
        '.me-lg-n5',
        (
            ('margin-right', '-48px', True),
        ),
    ),
    (
        '.mx-xl-0',
        (
            ('margin-right', '0', True),
            ('margin-left', '0', True),
        ),
    ),
    (
        '.mx-xl-1',
        (
            ('margin-right', '4px', True),
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.mx-xl-2',
        (
            ('margin-right', '8px', True),
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.mx-xl-3',
        (
            ('margin-right', '16px', True),
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.mx-xl-4',
        (
            ('margin-right', '24px', True),
            ('margin-left', '24px', True),
        ),
    ),
    (
        '.mx-xl-5',
        (
            ('margin-right', '48px', True),
            ('margin-left', '48px', True),
        ),
    ),
    (
        '.mx-xl-auto',
        (
            ('margin-right', 'auto', True),
            ('margin-left', 'auto', True),
        ),
    ),
    (
        '.me-xl-0',
        (
            ('margin-right', '0', True),
        ),
    ),
    (
        '.me-xl-1',
        (
            ('margin-right', '4px', True),
        ),
    ),
    (
        '.me-xl-2',
        (
            ('margin-right', '8px', True),
        ),
    ),
    (
        '.me-xl-3',
        (
            ('margin-right', '16px', True),
        ),
    ),
    (
        '.me-xl-4',
        (
            ('margin-right', '24px', True),
        ),
    ),
    (
        '.me-xl-5',
        (
            ('margin-right', '48px', True),
        ),
    ),
    (
        '.me-xl-auto',
        (
            ('margin-right', 'auto', True),
        ),
    ),
    (
        '.mx-xl-n1',
        (
            ('margin-right', '-4px', True),
            ('margin-left', '-4px', True),
        ),
    ),
    (
        '.mx-xl-n2',
        (
            ('margin-right', '-8px', True),
            ('margin-left', '-8px', True),
        ),
    ),
    (
        '.mx-xl-n3',
        (
            ('margin-right', '-16px', True),
            ('margin-left', '-16px', True),
        ),
    ),
    (
        '.mx-xl-n4',
        (
            ('margin-right', '-24px', True),
            ('margin-left', '-24px', True),
        ),
    ),
    (
        '.mx-xl-n5',
        (
            ('margin-right', '-48px', True),
            ('margin-left', '-48px', True),
        ),
    ),
    (
        '.me-xl-n1',
        (
            ('margin-right', '-4px', True),
        ),
    ),
    (
        '.me-xl-n2',
        (
            ('margin-right', '-8px', True),
        ),
    ),
    (
        '.me-xl-n3',
        (
            ('margin-right', '-16px', True),
        ),
    ),
    (
        '.me-xl-n4',
        (
            ('margin-right', '-24px', True),
        ),
    ),
    (
        '.me-xl-n5',
        (
            ('margin-right', '-48px', True),
        ),
    ),
    (
        '.mx-xxl-0',
        (
            ('margin-right', '0', True),
            ('margin-left', '0', True),
        ),
    ),
    (
        '.mx-xxl-1',
        (
            ('margin-right', '4px', True),
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.mx-xxl-2',
        (
            ('margin-right', '8px', True),
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.mx-xxl-3',
        (
            ('margin-right', '16px', True),
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.mx-xxl-4',
        (
            ('margin-right', '24px', True),
            ('margin-left', '24px', True),
        ),
    ),
    (
        '.mx-xxl-5',
        (
            ('margin-right', '48px', True),
            ('margin-left', '48px', True),
        ),
    ),
    (
        '.mx-xxl-auto',
        (
            ('margin-right', 'auto', True),
            ('margin-left', 'auto', True),
        ),
    ),
    (
        '.me-xxl-0',
        (
            ('margin-right', '0', True),
        ),
    ),
    (
        '.me-xxl-1',
        (
            ('margin-right', '4px', True),
        ),
    ),
    (
        '.me-xxl-2',
        (
            ('margin-right', '8px', True),
        ),
    ),
    (
        '.me-xxl-3',
        (
            ('margin-right', '16px', True),
        ),
    ),
    (
        '.me-xxl-4',
        (
            ('margin-right', '24px', True),
        ),
    ),
    (
        '.me-xxl-5',
        (
            ('margin-right', '48px', True),
        ),
    ),
    (
        '.me-xxl-auto',
        (
            ('margin-right', 'auto', True),
        ),
    ),
    (
        '.mx-xxl-n1',
        (
            ('margin-right', '-4px', True),
            ('margin-left', '-4px', True),
        ),
    ),
    (
        '.mx-xxl-n2',
        (
            ('margin-right', '-8px', True),
            ('margin-left', '-8px', True),
        ),
    ),
    (
        '.mx-xxl-n3',
        (
            ('margin-right', '-16px', True),
            ('margin-left', '-16px', True),
        ),
    ),
    (
        '.mx-xxl-n4',
        (
            ('margin-right', '-24px', True),
            ('margin-left', '-24px', True),
        ),
    ),
    (
        '.mx-xxl-n5',
        (
            ('margin-right', '-48px', True),
            ('margin-left', '-48px', True),
        ),
    ),
    (
        '.me-xxl-n1',
        (
            ('margin-right', '-4px', True),
        ),
    ),
    (
        '.me-xxl-n2',
        (
            ('margin-right', '-8px', True),
        ),
    ),
    (
        '.me-xxl-n3',
        (
            ('margin-right', '-16px', True),
        ),
    ),
    (
        '.me-xxl-n4',
        (
            ('margin-right', '-24px', True),
        ),
    ),
    (
        '.me-xxl-n5',
        (
            ('margin-right', '-48px', True),
        ),
    ),
    (
        '.oe_centered',
        (
            ('margin-left', 'auto', False),
            ('margin-right', 'auto', False),
        ),
    ),
    (
        '.oe_quote .oe_photo',
        (
            ('margin-right', '16px', False),
        ),
    ),
    (
        '.fa.fa-pull-left',
        (
            ('margin-right', '.3em', False),
        ),
    ),
    (
        '.o_folder_adaptative_shape .o_folder_title',
        (
            ('margin-right', '11mm', False),
        ),
    ),
    (
        'address .fa.fa-file-text-o',
        (
            ('margin-right', '1px', False),
        ),
    ),
    (
        '.mr0',
        (
            ('margin-right', '0px', True),
        ),
    ),
    (
        '.mr4',
        (
            ('margin-right', '4px', True),
        ),
    ),
    (
        '.mr8',
        (
            ('margin-right', '8px', True),
        ),
    ),
    (
        '.mr16',
        (
            ('margin-right', '16px', True),
        ),
    ),
    (
        '.mr32',
        (
            ('margin-right', '32px', True),
        ),
    ),
    (
        '.mr64',
        (
            ('margin-right', '64px', True),
        ),
    ),
    (
        '.o_label_page',
        (
            ('margin-left', '-3mm', False),
            ('margin-right', '-3mm', False),
        ),
    ),
    (
        '#payment_terms_note_id > p',
        (
            ('margin-bottom', '0', True),
        ),
    ),
    (
        '.tax_computation_company_currency',
        (
            ('margin-bottom', '5px', False),
        ),
    ),
    (
        'address',
        (
            ('margin-bottom', '1rem', False),
        ),
    ),
    (
        'ol ol, ul ul, ol ul, ul ol',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        'dd',
        (
            ('margin-bottom', '.5rem', False),
            ('margin-left', '0', False),
        ),
    ),
    (
        'legend',
        (
            ('margin-bottom', '0.5rem', False),
        ),
    ),
    (
        '.blockquote',
        (
            ('margin-bottom', '16px', False),
        ),
    ),
    (
        '.blockquote > :last-child',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        '.figure-img',
        (
            ('margin-bottom', '8px', False),
        ),
    ),
    (
        '.table',
        (
            ('margin-bottom', '16px', False),
        ),
    ),
    (
        '.form-label',
        (
            ('margin-bottom', '0.5rem', False),
        ),
    ),
    (
        '.col-form-label',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        '.form-control-plaintext',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        '.form-check',
        (
            ('margin-bottom', '0.125rem', False),
        ),
    ),
    (
        '.dropdown-header',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        '.nav',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        '.navbar-nav',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        '.card-subtitle',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        '.card-text:last-child',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        '.card-header',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        '.card-group > .card',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        '.accordion-header',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        '.list-group',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        '.modal-title',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        '.popover-header',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        '.offcanvas-title',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        '.mb-0',
        (
            ('margin-bottom', '0', True),
        ),
    ),
    (
        '.mb-1',
        (
            ('margin-bottom', '4px', True),
        ),
    ),
    (
        '.mb-2',
        (
            ('margin-bottom', '8px', True),
        ),
    ),
    (
        '.mb-3',
        (
            ('margin-bottom', '16px', True),
        ),
    ),
    (
        '.mb-4',
        (
            ('margin-bottom', '24px', True),
        ),
    ),
    (
        '.mb-5',
        (
            ('margin-bottom', '48px', True),
        ),
    ),
    (
        '.mb-auto',
        (
            ('margin-bottom', 'auto', True),
        ),
    ),
    (
        '.mb-n1',
        (
            ('margin-bottom', '-4px', True),
        ),
    ),
    (
        '.mb-n2',
        (
            ('margin-bottom', '-8px', True),
        ),
    ),
    (
        '.mb-n3',
        (
            ('margin-bottom', '-16px', True),
        ),
    ),
    (
        '.mb-n4',
        (
            ('margin-bottom', '-24px', True),
        ),
    ),
    (
        '.mb-n5',
        (
            ('margin-bottom', '-48px', True),
        ),
    ),
    (
        '.mb-sm-0',
        (
            ('margin-bottom', '0', True),
        ),
    ),
    (
        '.mb-sm-1',
        (
            ('margin-bottom', '4px', True),
        ),
    ),
    (
        '.mb-sm-2',
        (
            ('margin-bottom', '8px', True),
        ),
    ),
    (
        '.mb-sm-3',
        (
            ('margin-bottom', '16px', True),
        ),
    ),
    (
        '.mb-sm-4',
        (
            ('margin-bottom', '24px', True),
        ),
    ),
    (
        '.mb-sm-5',
        (
            ('margin-bottom', '48px', True),
        ),
    ),
    (
        '.mb-sm-auto',
        (
            ('margin-bottom', 'auto', True),
        ),
    ),
    (
        '.mb-sm-n1',
        (
            ('margin-bottom', '-4px', True),
        ),
    ),
    (
        '.mb-sm-n2',
        (
            ('margin-bottom', '-8px', True),
        ),
    ),
    (
        '.mb-sm-n3',
        (
            ('margin-bottom', '-16px', True),
        ),
    ),
    (
        '.mb-sm-n4',
        (
            ('margin-bottom', '-24px', True),
        ),
    ),
    (
        '.mb-sm-n5',
        (
            ('margin-bottom', '-48px', True),
        ),
    ),
    (
        '.mb-md-0',
        (
            ('margin-bottom', '0', True),
        ),
    ),
    (
        '.mb-md-1',
        (
            ('margin-bottom', '4px', True),
        ),
    ),
    (
        '.mb-md-2',
        (
            ('margin-bottom', '8px', True),
        ),
    ),
    (
        '.mb-md-3',
        (
            ('margin-bottom', '16px', True),
        ),
    ),
    (
        '.mb-md-4',
        (
            ('margin-bottom', '24px', True),
        ),
    ),
    (
        '.mb-md-5',
        (
            ('margin-bottom', '48px', True),
        ),
    ),
    (
        '.mb-md-auto',
        (
            ('margin-bottom', 'auto', True),
        ),
    ),
    (
        '.mb-md-n1',
        (
            ('margin-bottom', '-4px', True),
        ),
    ),
    (
        '.mb-md-n2',
        (
            ('margin-bottom', '-8px', True),
        ),
    ),
    (
        '.mb-md-n3',
        (
            ('margin-bottom', '-16px', True),
        ),
    ),
    (
        '.mb-md-n4',
        (
            ('margin-bottom', '-24px', True),
        ),
    ),
    (
        '.mb-md-n5',
        (
            ('margin-bottom', '-48px', True),
        ),
    ),
    (
        '.mb-lg-0',
        (
            ('margin-bottom', '0', True),
        ),
    ),
    (
        '.mb-lg-1',
        (
            ('margin-bottom', '4px', True),
        ),
    ),
    (
        '.mb-lg-2',
        (
            ('margin-bottom', '8px', True),
        ),
    ),
    (
        '.mb-lg-3',
        (
            ('margin-bottom', '16px', True),
        ),
    ),
    (
        '.mb-lg-4',
        (
            ('margin-bottom', '24px', True),
        ),
    ),
    (
        '.mb-lg-5',
        (
            ('margin-bottom', '48px', True),
        ),
    ),
    (
        '.mb-lg-auto',
        (
            ('margin-bottom', 'auto', True),
        ),
    ),
    (
        '.mb-lg-n1',
        (
            ('margin-bottom', '-4px', True),
        ),
    ),
    (
        '.mb-lg-n2',
        (
            ('margin-bottom', '-8px', True),
        ),
    ),
    (
        '.mb-lg-n3',
        (
            ('margin-bottom', '-16px', True),
        ),
    ),
    (
        '.mb-lg-n4',
        (
            ('margin-bottom', '-24px', True),
        ),
    ),
    (
        '.mb-lg-n5',
        (
            ('margin-bottom', '-48px', True),
        ),
    ),
    (
        '.mb-xl-0',
        (
            ('margin-bottom', '0', True),
        ),
    ),
    (
        '.mb-xl-1',
        (
            ('margin-bottom', '4px', True),
        ),
    ),
    (
        '.mb-xl-2',
        (
            ('margin-bottom', '8px', True),
        ),
    ),
    (
        '.mb-xl-3',
        (
            ('margin-bottom', '16px', True),
        ),
    ),
    (
        '.mb-xl-4',
        (
            ('margin-bottom', '24px', True),
        ),
    ),
    (
        '.mb-xl-5',
        (
            ('margin-bottom', '48px', True),
        ),
    ),
    (
        '.mb-xl-auto',
        (
            ('margin-bottom', 'auto', True),
        ),
    ),
    (
        '.mb-xl-n1',
        (
            ('margin-bottom', '-4px', True),
        ),
    ),
    (
        '.mb-xl-n2',
        (
            ('margin-bottom', '-8px', True),
        ),
    ),
    (
        '.mb-xl-n3',
        (
            ('margin-bottom', '-16px', True),
        ),
    ),
    (
        '.mb-xl-n4',
        (
            ('margin-bottom', '-24px', True),
        ),
    ),
    (
        '.mb-xl-n5',
        (
            ('margin-bottom', '-48px', True),
        ),
    ),
    (
        '.mb-xxl-0',
        (
            ('margin-bottom', '0', True),
        ),
    ),
    (
        '.mb-xxl-1',
        (
            ('margin-bottom', '4px', True),
        ),
    ),
    (
        '.mb-xxl-2',
        (
            ('margin-bottom', '8px', True),
        ),
    ),
    (
        '.mb-xxl-3',
        (
            ('margin-bottom', '16px', True),
        ),
    ),
    (
        '.mb-xxl-4',
        (
            ('margin-bottom', '24px', True),
        ),
    ),
    (
        '.mb-xxl-5',
        (
            ('margin-bottom', '48px', True),
        ),
    ),
    (
        '.mb-xxl-auto',
        (
            ('margin-bottom', 'auto', True),
        ),
    ),
    (
        '.mb-xxl-n1',
        (
            ('margin-bottom', '-4px', True),
        ),
    ),
    (
        '.mb-xxl-n2',
        (
            ('margin-bottom', '-8px', True),
        ),
    ),
    (
        '.mb-xxl-n3',
        (
            ('margin-bottom', '-16px', True),
        ),
    ),
    (
        '.mb-xxl-n4',
        (
            ('margin-bottom', '-24px', True),
        ),
    ),
    (
        '.mb-xxl-n5',
        (
            ('margin-bottom', '-48px', True),
        ),
    ),
    (
        '.oe_mb0',
        (
            ('margin-bottom', '0px', True),
        ),
    ),
    (
        '.oe_mb4',
        (
            ('margin-bottom', '4px', True),
        ),
    ),
    (
        '.oe_mb8',
        (
            ('margin-bottom', '8px', True),
        ),
    ),
    (
        '.oe_mb16',
        (
            ('margin-bottom', '16px', True),
        ),
    ),
    (
        '.oe_mb32',
        (
            ('margin-bottom', '32px', True),
        ),
    ),
    (
        '.oe_mb48',
        (
            ('margin-bottom', '48px', True),
        ),
    ),
    (
        '.oe_mb64',
        (
            ('margin-bottom', '64px', True),
        ),
    ),
    (
        '.oe_styling_v8 .oe_container.oe_separator',
        (
            ('margin-bottom', '16px', False),
        ),
    ),
    (
        '.o_shape_bubble_1 ~ table .o_company_logo',
        (
            ('margin-bottom', '4px', True),
        ),
    ),
    (
        '.o_company_tagline p',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        'div[name=comment] p, div[name=address] p',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        '.o_snail_mail .address div[name="address"] > address',
        (
            ('margin-bottom', '16px', True),
        ),
    ),
    (
        '.o_snail_mail .o_followup_address div[itemscope="itemscope"] > div:first-child',
        (
            ('margin-bottom', '16px', False),
        ),
    ),
    (
        '.alert',
        (
            ('margin-bottom', '1rem', False),
        ),
    ),
    (
        '.mb0',
        (
            ('margin-bottom', '0px', True),
        ),
    ),
    (
        '.mb8',
        (
            ('margin-bottom', '8px', True),
        ),
    ),
    (
        '.mb16',
        (
            ('margin-bottom', '16px', True),
        ),
    ),
    (
        '.mb24',
        (
            ('margin-bottom', '24px', True),
        ),
    ),
    (
        '.mb32',
        (
            ('margin-bottom', '32px', True),
        ),
    ),
    (
        '.mb40',
        (
            ('margin-bottom', '40px', True),
        ),
    ),
    (
        '.mb48',
        (
            ('margin-bottom', '48px', True),
        ),
    ),
    (
        '.mb56',
        (
            ('margin-bottom', '56px', True),
        ),
    ),
    (
        '.mb64',
        (
            ('margin-bottom', '64px', True),
        ),
    ),
    (
        '.mb72',
        (
            ('margin-bottom', '72px', True),
        ),
    ),
    (
        '.mb80',
        (
            ('margin-bottom', '80px', True),
        ),
    ),
    (
        '.mb88',
        (
            ('margin-bottom', '88px', True),
        ),
    ),
    (
        '.mb96',
        (
            ('margin-bottom', '96px', True),
        ),
    ),
    (
        '.mb104',
        (
            ('margin-bottom', '104px', True),
        ),
    ),
    (
        '.mb112',
        (
            ('margin-bottom', '112px', True),
        ),
    ),
    (
        '.mb120',
        (
            ('margin-bottom', '120px', True),
        ),
    ),
    (
        '.mb128',
        (
            ('margin-bottom', '128px', True),
        ),
    ),
    (
        '.mb136',
        (
            ('margin-bottom', '136px', True),
        ),
    ),
    (
        '.mb144',
        (
            ('margin-bottom', '144px', True),
        ),
    ),
    (
        '.mb152',
        (
            ('margin-bottom', '152px', True),
        ),
    ),
    (
        '.mb160',
        (
            ('margin-bottom', '160px', True),
        ),
    ),
    (
        '.mb168',
        (
            ('margin-bottom', '168px', True),
        ),
    ),
    (
        '.mb176',
        (
            ('margin-bottom', '176px', True),
        ),
    ),
    (
        '.mb184',
        (
            ('margin-bottom', '184px', True),
        ),
    ),
    (
        '.mb192',
        (
            ('margin-bottom', '192px', True),
        ),
    ),
    (
        '.mb200',
        (
            ('margin-bottom', '200px', True),
        ),
    ),
    (
        '.mb208',
        (
            ('margin-bottom', '208px', True),
        ),
    ),
    (
        '.mb216',
        (
            ('margin-bottom', '216px', True),
        ),
    ),
    (
        '.mb224',
        (
            ('margin-bottom', '224px', True),
        ),
    ),
    (
        '.mb232',
        (
            ('margin-bottom', '232px', True),
        ),
    ),
    (
        '.mb240',
        (
            ('margin-bottom', '240px', True),
        ),
    ),
    (
        '.mb248',
        (
            ('margin-bottom', '248px', True),
        ),
    ),
    (
        '.mb256',
        (
            ('margin-bottom', '256px', True),
        ),
    ),
    (
        '.mb4',
        (
            ('margin-bottom', '4px', True),
        ),
    ),
    (
        '.mb92',
        (
            ('margin-bottom', '92px', True),
        ),
    ),
    (
        'pre p',
        (
            ('margin-bottom', '0px', False),
        ),
    ),
    (
        '.o_editor_banner p, .o_editor_banner h1, .o_editor_banner .h1, .o_editor_banner h2, .o_editor_banner .h2, .o_editor_banner h3, .o_editor_banner .h3, .o_editor_banner ul, .o_editor_banner ol',
        (
            ('margin-bottom', '1rem', False),
        ),
    ),
    (
        '.o_editor_banner ol ol, .o_editor_banner ul ul, .o_editor_banner ol ul, .o_editor_banner ul ol',
        (
            ('margin-bottom', '0', False),
        ),
    ),
    (
        '.offset-1',
        (
            ('margin-left', '8.33333333%', False),
        ),
    ),
    (
        '.offset-2',
        (
            ('margin-left', '16.66666667%', False),
        ),
    ),
    (
        '.offset-3',
        (
            ('margin-left', '25%', False),
        ),
    ),
    (
        '.offset-4',
        (
            ('margin-left', '33.33333333%', False),
        ),
    ),
    (
        '.offset-5',
        (
            ('margin-left', '41.66666667%', False),
        ),
    ),
    (
        '.offset-6',
        (
            ('margin-left', '50%', False),
        ),
    ),
    (
        '.offset-7',
        (
            ('margin-left', '58.33333333%', False),
        ),
    ),
    (
        '.offset-8',
        (
            ('margin-left', '66.66666667%', False),
        ),
    ),
    (
        '.offset-9',
        (
            ('margin-left', '75%', False),
        ),
    ),
    (
        '.offset-10',
        (
            ('margin-left', '83.33333333%', False),
        ),
    ),
    (
        '.offset-11',
        (
            ('margin-left', '91.66666667%', False),
        ),
    ),
    (
        '.offset-sm-0',
        (
            ('margin-left', '0', False),
        ),
    ),
    (
        '.offset-sm-1',
        (
            ('margin-left', '8.33333333%', False),
        ),
    ),
    (
        '.offset-sm-2',
        (
            ('margin-left', '16.66666667%', False),
        ),
    ),
    (
        '.offset-sm-3',
        (
            ('margin-left', '25%', False),
        ),
    ),
    (
        '.offset-sm-4',
        (
            ('margin-left', '33.33333333%', False),
        ),
    ),
    (
        '.offset-sm-5',
        (
            ('margin-left', '41.66666667%', False),
        ),
    ),
    (
        '.offset-sm-6',
        (
            ('margin-left', '50%', False),
        ),
    ),
    (
        '.offset-sm-7',
        (
            ('margin-left', '58.33333333%', False),
        ),
    ),
    (
        '.offset-sm-8',
        (
            ('margin-left', '66.66666667%', False),
        ),
    ),
    (
        '.offset-sm-9',
        (
            ('margin-left', '75%', False),
        ),
    ),
    (
        '.offset-sm-10',
        (
            ('margin-left', '83.33333333%', False),
        ),
    ),
    (
        '.offset-sm-11',
        (
            ('margin-left', '91.66666667%', False),
        ),
    ),
    (
        '.offset-md-0',
        (
            ('margin-left', '0', False),
        ),
    ),
    (
        '.offset-md-1',
        (
            ('margin-left', '8.33333333%', False),
        ),
    ),
    (
        '.offset-md-2',
        (
            ('margin-left', '16.66666667%', False),
        ),
    ),
    (
        '.offset-md-3',
        (
            ('margin-left', '25%', False),
        ),
    ),
    (
        '.offset-md-4',
        (
            ('margin-left', '33.33333333%', False),
        ),
    ),
    (
        '.offset-md-5',
        (
            ('margin-left', '41.66666667%', False),
        ),
    ),
    (
        '.offset-md-6',
        (
            ('margin-left', '50%', False),
        ),
    ),
    (
        '.offset-md-7',
        (
            ('margin-left', '58.33333333%', False),
        ),
    ),
    (
        '.offset-md-8',
        (
            ('margin-left', '66.66666667%', False),
        ),
    ),
    (
        '.offset-md-9',
        (
            ('margin-left', '75%', False),
        ),
    ),
    (
        '.offset-md-10',
        (
            ('margin-left', '83.33333333%', False),
        ),
    ),
    (
        '.offset-md-11',
        (
            ('margin-left', '91.66666667%', False),
        ),
    ),
    (
        '.offset-lg-0',
        (
            ('margin-left', '0', False),
        ),
    ),
    (
        '.offset-lg-1',
        (
            ('margin-left', '8.33333333%', False),
        ),
    ),
    (
        '.offset-lg-2',
        (
            ('margin-left', '16.66666667%', False),
        ),
    ),
    (
        '.offset-lg-3',
        (
            ('margin-left', '25%', False),
        ),
    ),
    (
        '.offset-lg-4',
        (
            ('margin-left', '33.33333333%', False),
        ),
    ),
    (
        '.offset-lg-5',
        (
            ('margin-left', '41.66666667%', False),
        ),
    ),
    (
        '.offset-lg-6',
        (
            ('margin-left', '50%', False),
        ),
    ),
    (
        '.offset-lg-7',
        (
            ('margin-left', '58.33333333%', False),
        ),
    ),
    (
        '.offset-lg-8',
        (
            ('margin-left', '66.66666667%', False),
        ),
    ),
    (
        '.offset-lg-9',
        (
            ('margin-left', '75%', False),
        ),
    ),
    (
        '.offset-lg-10',
        (
            ('margin-left', '83.33333333%', False),
        ),
    ),
    (
        '.offset-lg-11',
        (
            ('margin-left', '91.66666667%', False),
        ),
    ),
    (
        '.offset-xl-0',
        (
            ('margin-left', '0', False),
        ),
    ),
    (
        '.offset-xl-1',
        (
            ('margin-left', '8.33333333%', False),
        ),
    ),
    (
        '.offset-xl-2',
        (
            ('margin-left', '16.66666667%', False),
        ),
    ),
    (
        '.offset-xl-3',
        (
            ('margin-left', '25%', False),
        ),
    ),
    (
        '.offset-xl-4',
        (
            ('margin-left', '33.33333333%', False),
        ),
    ),
    (
        '.offset-xl-5',
        (
            ('margin-left', '41.66666667%', False),
        ),
    ),
    (
        '.offset-xl-6',
        (
            ('margin-left', '50%', False),
        ),
    ),
    (
        '.offset-xl-7',
        (
            ('margin-left', '58.33333333%', False),
        ),
    ),
    (
        '.offset-xl-8',
        (
            ('margin-left', '66.66666667%', False),
        ),
    ),
    (
        '.offset-xl-9',
        (
            ('margin-left', '75%', False),
        ),
    ),
    (
        '.offset-xl-10',
        (
            ('margin-left', '83.33333333%', False),
        ),
    ),
    (
        '.offset-xl-11',
        (
            ('margin-left', '91.66666667%', False),
        ),
    ),
    (
        '.offset-xxl-0',
        (
            ('margin-left', '0', False),
        ),
    ),
    (
        '.offset-xxl-1',
        (
            ('margin-left', '8.33333333%', False),
        ),
    ),
    (
        '.offset-xxl-2',
        (
            ('margin-left', '16.66666667%', False),
        ),
    ),
    (
        '.offset-xxl-3',
        (
            ('margin-left', '25%', False),
        ),
    ),
    (
        '.offset-xxl-4',
        (
            ('margin-left', '33.33333333%', False),
        ),
    ),
    (
        '.offset-xxl-5',
        (
            ('margin-left', '41.66666667%', False),
        ),
    ),
    (
        '.offset-xxl-6',
        (
            ('margin-left', '50%', False),
        ),
    ),
    (
        '.offset-xxl-7',
        (
            ('margin-left', '58.33333333%', False),
        ),
    ),
    (
        '.offset-xxl-8',
        (
            ('margin-left', '66.66666667%', False),
        ),
    ),
    (
        '.offset-xxl-9',
        (
            ('margin-left', '75%', False),
        ),
    ),
    (
        '.offset-xxl-10',
        (
            ('margin-left', '83.33333333%', False),
        ),
    ),
    (
        '.offset-xxl-11',
        (
            ('margin-left', '91.66666667%', False),
        ),
    ),
    (
        '.form-check .form-check-input',
        (
            ('margin-left', '-1.5em', False),
        ),
    ),
    (
        '.form-switch .form-check-input',
        (
            ('margin-left', '-2.5em', False),
        ),
    ),
    (
        '.form-check-inline .form-check-input ~ .valid-feedback',
        (
            ('margin-left', '.5em', False),
        ),
    ),
    (
        '.form-check-inline .form-check-input ~ .invalid-feedback',
        (
            ('margin-left', '.5em', False),
        ),
    ),
    (
        '.dropdown-toggle::after',
        (
            ('margin-left', '3.4px', False),
        ),
    ),
    (
        '.dropdown-toggle:empty::after',
        (
            ('margin-left', '0', False),
        ),
    ),
    (
        '.dropup .dropdown-toggle::after',
        (
            ('margin-left', '3.4px', False),
        ),
    ),
    (
        '.dropup .dropdown-toggle:empty::after',
        (
            ('margin-left', '0', False),
        ),
    ),
    (
        '.dropend .dropdown-toggle::after',
        (
            ('margin-left', '3.4px', False),
        ),
    ),
    (
        '.dropend .dropdown-toggle:empty::after',
        (
            ('margin-left', '0', False),
        ),
    ),
    (
        '.dropstart .dropdown-toggle::after',
        (
            ('margin-left', '3.4px', False),
        ),
    ),
    (
        '.dropstart .dropdown-toggle:empty::after',
        (
            ('margin-left', '0', False),
        ),
    ),
    (
        '.dropdown-toggle-split::after, .dropup .dropdown-toggle-split::after, .dropend .dropdown-toggle-split::after',
        (
            ('margin-left', '0', False),
        ),
    ),
    (
        '.card-group > .card + .card',
        (
            ('margin-left', '0', False),
        ),
    ),
    (
        '.accordion-button::after',
        (
            ('margin-left', 'auto', False),
        ),
    ),
    (
        '.modal-header .btn-close',
        (
            ('margin-left', 'auto', False),
        ),
    ),
    (
        '.offcanvas-header .btn-close',
        (
            ('margin-left', 'auto', False),
        ),
    ),
    (
        '.ms-0',
        (
            ('margin-left', '0', True),
        ),
    ),
    (
        '.ms-1',
        (
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.ms-2',
        (
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.ms-3',
        (
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.ms-4',
        (
            ('margin-left', '24px', True),
        ),
    ),
    (
        '.ms-5',
        (
            ('margin-left', '48px', True),
        ),
    ),
    (
        '.ms-auto',
        (
            ('margin-left', 'auto', True),
        ),
    ),
    (
        '.ms-n1',
        (
            ('margin-left', '-4px', True),
        ),
    ),
    (
        '.ms-n2',
        (
            ('margin-left', '-8px', True),
        ),
    ),
    (
        '.ms-n3',
        (
            ('margin-left', '-16px', True),
        ),
    ),
    (
        '.ms-n4',
        (
            ('margin-left', '-24px', True),
        ),
    ),
    (
        '.ms-n5',
        (
            ('margin-left', '-48px', True),
        ),
    ),
    (
        '.ms-sm-0',
        (
            ('margin-left', '0', True),
        ),
    ),
    (
        '.ms-sm-1',
        (
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.ms-sm-2',
        (
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.ms-sm-3',
        (
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.ms-sm-4',
        (
            ('margin-left', '24px', True),
        ),
    ),
    (
        '.ms-sm-5',
        (
            ('margin-left', '48px', True),
        ),
    ),
    (
        '.ms-sm-auto',
        (
            ('margin-left', 'auto', True),
        ),
    ),
    (
        '.ms-sm-n1',
        (
            ('margin-left', '-4px', True),
        ),
    ),
    (
        '.ms-sm-n2',
        (
            ('margin-left', '-8px', True),
        ),
    ),
    (
        '.ms-sm-n3',
        (
            ('margin-left', '-16px', True),
        ),
    ),
    (
        '.ms-sm-n4',
        (
            ('margin-left', '-24px', True),
        ),
    ),
    (
        '.ms-sm-n5',
        (
            ('margin-left', '-48px', True),
        ),
    ),
    (
        '.ms-md-0',
        (
            ('margin-left', '0', True),
        ),
    ),
    (
        '.ms-md-1',
        (
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.ms-md-2',
        (
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.ms-md-3',
        (
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.ms-md-4',
        (
            ('margin-left', '24px', True),
        ),
    ),
    (
        '.ms-md-5',
        (
            ('margin-left', '48px', True),
        ),
    ),
    (
        '.ms-md-auto',
        (
            ('margin-left', 'auto', True),
        ),
    ),
    (
        '.ms-md-n1',
        (
            ('margin-left', '-4px', True),
        ),
    ),
    (
        '.ms-md-n2',
        (
            ('margin-left', '-8px', True),
        ),
    ),
    (
        '.ms-md-n3',
        (
            ('margin-left', '-16px', True),
        ),
    ),
    (
        '.ms-md-n4',
        (
            ('margin-left', '-24px', True),
        ),
    ),
    (
        '.ms-md-n5',
        (
            ('margin-left', '-48px', True),
        ),
    ),
    (
        '.ms-lg-0',
        (
            ('margin-left', '0', True),
        ),
    ),
    (
        '.ms-lg-1',
        (
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.ms-lg-2',
        (
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.ms-lg-3',
        (
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.ms-lg-4',
        (
            ('margin-left', '24px', True),
        ),
    ),
    (
        '.ms-lg-5',
        (
            ('margin-left', '48px', True),
        ),
    ),
    (
        '.ms-lg-auto',
        (
            ('margin-left', 'auto', True),
        ),
    ),
    (
        '.ms-lg-n1',
        (
            ('margin-left', '-4px', True),
        ),
    ),
    (
        '.ms-lg-n2',
        (
            ('margin-left', '-8px', True),
        ),
    ),
    (
        '.ms-lg-n3',
        (
            ('margin-left', '-16px', True),
        ),
    ),
    (
        '.ms-lg-n4',
        (
            ('margin-left', '-24px', True),
        ),
    ),
    (
        '.ms-lg-n5',
        (
            ('margin-left', '-48px', True),
        ),
    ),
    (
        '.ms-xl-0',
        (
            ('margin-left', '0', True),
        ),
    ),
    (
        '.ms-xl-1',
        (
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.ms-xl-2',
        (
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.ms-xl-3',
        (
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.ms-xl-4',
        (
            ('margin-left', '24px', True),
        ),
    ),
    (
        '.ms-xl-5',
        (
            ('margin-left', '48px', True),
        ),
    ),
    (
        '.ms-xl-auto',
        (
            ('margin-left', 'auto', True),
        ),
    ),
    (
        '.ms-xl-n1',
        (
            ('margin-left', '-4px', True),
        ),
    ),
    (
        '.ms-xl-n2',
        (
            ('margin-left', '-8px', True),
        ),
    ),
    (
        '.ms-xl-n3',
        (
            ('margin-left', '-16px', True),
        ),
    ),
    (
        '.ms-xl-n4',
        (
            ('margin-left', '-24px', True),
        ),
    ),
    (
        '.ms-xl-n5',
        (
            ('margin-left', '-48px', True),
        ),
    ),
    (
        '.ms-xxl-0',
        (
            ('margin-left', '0', True),
        ),
    ),
    (
        '.ms-xxl-1',
        (
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.ms-xxl-2',
        (
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.ms-xxl-3',
        (
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.ms-xxl-4',
        (
            ('margin-left', '24px', True),
        ),
    ),
    (
        '.ms-xxl-5',
        (
            ('margin-left', '48px', True),
        ),
    ),
    (
        '.ms-xxl-auto',
        (
            ('margin-left', 'auto', True),
        ),
    ),
    (
        '.ms-xxl-n1',
        (
            ('margin-left', '-4px', True),
        ),
    ),
    (
        '.ms-xxl-n2',
        (
            ('margin-left', '-8px', True),
        ),
    ),
    (
        '.ms-xxl-n3',
        (
            ('margin-left', '-16px', True),
        ),
    ),
    (
        '.ms-xxl-n4',
        (
            ('margin-left', '-24px', True),
        ),
    ),
    (
        '.ms-xxl-n5',
        (
            ('margin-left', '-48px', True),
        ),
    ),
    (
        '.fa-ul',
        (
            ('margin-left', '2.14285714em', False),
        ),
    ),
    (
        '.fa.fa-pull-right',
        (
            ('margin-left', '.3em', False),
        ),
    ),
    (
        'ul.o_checklist > li',
        (
            ('margin-left', '20px', False),
        ),
    ),
    (
        'ol > li.o_indent, ul > li.o_indent',
        (
            ('margin-left', '0', False),
        ),
    ),
    (
        '.ml0',
        (
            ('margin-left', '0px', True),
        ),
    ),
    (
        '.ml4',
        (
            ('margin-left', '4px', True),
        ),
    ),
    (
        '.ml8',
        (
            ('margin-left', '8px', True),
        ),
    ),
    (
        '.ml16',
        (
            ('margin-left', '16px', True),
        ),
    ),
    (
        '.ml32',
        (
            ('margin-left', '32px', True),
        ),
    ),
    (
        '.ml64',
        (
            ('margin-left', '64px', True),
        ),
    ),
    (
        '.o_we_search_prompt > h2, .o_we_search_prompt > .h2',
        (
            ('margin-left', '150px', False),
        ),
    ),
)


#: Where a declared family's file is. The cascade answers "which
#: family"; only `@font-face` answers "which file", and the two have
#: to be compiled together or the runtime is left parsing the bundle.
#: What the bundle generates before an element, selectors intact and the
#: pseudo suffix stripped so the ordinary cascade decides the winner. A
#: class census cannot answer this: `fa-phone` is in two evaluated
#: documents and in no template.
PSEUDO_BEFORE_RULES = (
    (
        'blockquote',
        (
            ('content', '""', False),
            ('content', 'none', False),
        ),
    ),
    (
        'q',
        (
            ('content', '""', False),
            ('content', 'none', False),
        ),
    ),
    (
        '.blockquote-footer',
        (
            ('content', '"\\2014\\00A0"', False),
        ),
    ),
    (
        '.dropstart .dropdown-toggle',
        (
            ('display', 'inline-block', False),
            ('margin-right', '3.4px', False),
            ('vertical-align', '3.4px', False),
            ('content', '""', False),
            ('border-top-width', '4px', False),
            ('border-top-style', 'solid', False),
            ('border-right-width', '4px', False),
            ('border-right-style', 'solid', False),
            ('border-bottom-width', '4px', False),
            ('border-bottom-style', 'solid', False),
        ),
    ),
    (
        '.breadcrumb-item + .breadcrumb-item',
        (
            ('float', 'left', False),
            ('padding-right', 'var(--breadcrumb-item-padding-x)', False),
            ('color', 'var(--breadcrumb-divider-color)', False),
            ('content', 'var(--breadcrumb-divider, "/")', False),
        ),
    ),
    (
        '.list-group-numbered > .list-group-item',
        (
            ('content', 'counters(section, ".") ". "', False),
        ),
    ),
    (
        '.tooltip .tooltip-arrow',
        (
            ('position', 'absolute', False),
            ('content', '""', False),
            ('border-top-style', 'solid', False),
            ('border-right-style', 'solid', False),
            ('border-bottom-style', 'solid', False),
            ('border-left-style', 'solid', False),
        ),
    ),
    (
        '.popover .popover-arrow',
        (
            ('position', 'absolute', False),
            ('display', 'block', False),
            ('content', '""', False),
            ('border-top-style', 'solid', False),
            ('border-right-style', 'solid', False),
            ('border-bottom-style', 'solid', False),
            ('border-left-style', 'solid', False),
            ('border-top-width', '0', False),
            ('border-right-width', '0', False),
            ('border-bottom-width', '0', False),
            ('border-left-width', '0', False),
        ),
    ),
    (
        '.bs-popover-bottom .popover-header',
        (
            ('position', 'absolute', False),
            ('top', '0', False),
            ('left', '50%', False),
            ('display', 'block', False),
            ('width', 'var(--popover-arrow-width)', False),
            ('margin-left', 'calc(-.5 * var(--popover-arrow-width))', False),
            ('content', '""', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
        ),
    ),
    (
        '.bs-popover-auto[data-popper-placement^="bottom"] .popover-header',
        (
            ('position', 'absolute', False),
            ('top', '0', False),
            ('left', '50%', False),
            ('display', 'block', False),
            ('width', 'var(--popover-arrow-width)', False),
            ('margin-left', 'calc(-.5 * var(--popover-arrow-width))', False),
            ('content', '""', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
        ),
    ),
    (
        '.placeholder.btn',
        (
            ('display', 'inline-block', False),
            ('content', '""', False),
        ),
    ),
    (
        '.ratio',
        (
            ('display', 'block', False),
            ('padding-top', 'var(--aspect-ratio)', False),
            ('content', '""', False),
        ),
    ),
    (
        '.oe_styling_v8 h4.oe_slogan',
        (
            ('margin-top', '0', False),
            ('margin-right', '20px', False),
            ('margin-bottom', '0', False),
            ('margin-left', '20px', False),
            ('content', '""', False),
            ('display', 'inline-block', False),
            ('width', '100px', False),
            ('height', '0px', False),
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('vertical-align', 'middle', False),
        ),
    ),
    (
        '.oe_quote .oe_q',
        (
            ('content', '\'"\'', False),
            ('font-weight', '900', False),
        ),
    ),
    (
        '.oe_quote q',
        (
            ('content', '\'"\'', False),
            ('font-weight', '900', False),
        ),
    ),
    (
        '.fa-glass',
        (
            ('content', '"\\f000"', False),
        ),
    ),
    (
        '.fa-music',
        (
            ('content', '"\\f001"', False),
        ),
    ),
    (
        '.fa-search',
        (
            ('content', '"\\f002"', False),
        ),
    ),
    (
        '.fa-envelope-o',
        (
            ('content', '"\\f003"', False),
        ),
    ),
    (
        '.fa-heart',
        (
            ('content', '"\\f004"', False),
        ),
    ),
    (
        '.fa-star',
        (
            ('content', '"\\f005"', False),
        ),
    ),
    (
        '.fa-star-o',
        (
            ('content', '"\\f006"', False),
        ),
    ),
    (
        '.fa-user',
        (
            ('content', '"\\f007"', False),
        ),
    ),
    (
        '.fa-film',
        (
            ('content', '"\\f008"', False),
        ),
    ),
    (
        '.fa-th-large',
        (
            ('content', '"\\f009"', False),
        ),
    ),
    (
        '.fa-th',
        (
            ('content', '"\\f00a"', False),
        ),
    ),
    (
        '.fa-th-list',
        (
            ('content', '"\\f00b"', False),
        ),
    ),
    (
        '.fa-check',
        (
            ('content', '"\\f00c"', False),
        ),
    ),
    (
        '.fa-remove',
        (
            ('content', '"\\f00d"', False),
        ),
    ),
    (
        '.fa-close',
        (
            ('content', '"\\f00d"', False),
        ),
    ),
    (
        '.fa-times',
        (
            ('content', '"\\f00d"', False),
        ),
    ),
    (
        '.fa-search-plus',
        (
            ('content', '"\\f00e"', False),
        ),
    ),
    (
        '.fa-search-minus',
        (
            ('content', '"\\f010"', False),
        ),
    ),
    (
        '.fa-power-off',
        (
            ('content', '"\\f011"', False),
        ),
    ),
    (
        '.fa-signal',
        (
            ('content', '"\\f012"', False),
        ),
    ),
    (
        '.fa-gear',
        (
            ('content', '"\\f013"', False),
        ),
    ),
    (
        '.fa-cog',
        (
            ('content', '"\\f013"', False),
        ),
    ),
    (
        '.fa-trash-o',
        (
            ('content', '"\\f014"', False),
        ),
    ),
    (
        '.fa-home',
        (
            ('content', '"\\f015"', False),
        ),
    ),
    (
        '.fa-file-o',
        (
            ('content', '"\\f016"', False),
        ),
    ),
    (
        '.fa-clock-o',
        (
            ('content', '"\\f017"', False),
        ),
    ),
    (
        '.fa-road',
        (
            ('content', '"\\f018"', False),
        ),
    ),
    (
        '.fa-download',
        (
            ('content', '"\\f019"', False),
        ),
    ),
    (
        '.fa-arrow-circle-o-down',
        (
            ('content', '"\\f01a"', False),
        ),
    ),
    (
        '.fa-arrow-circle-o-up',
        (
            ('content', '"\\f01b"', False),
        ),
    ),
    (
        '.fa-inbox',
        (
            ('content', '"\\f01c"', False),
        ),
    ),
    (
        '.fa-play-circle-o',
        (
            ('content', '"\\f01d"', False),
        ),
    ),
    (
        '.fa-rotate-right',
        (
            ('content', '"\\f01e"', False),
        ),
    ),
    (
        '.fa-repeat',
        (
            ('content', '"\\f01e"', False),
        ),
    ),
    (
        '.fa-refresh',
        (
            ('content', '"\\f021"', False),
        ),
    ),
    (
        '.fa-list-alt',
        (
            ('content', '"\\f022"', False),
        ),
    ),
    (
        '.fa-lock',
        (
            ('content', '"\\f023"', False),
        ),
    ),
    (
        '.fa-flag',
        (
            ('content', '"\\f024"', False),
        ),
    ),
    (
        '.fa-headphones',
        (
            ('content', '"\\f025"', False),
        ),
    ),
    (
        '.fa-volume-off',
        (
            ('content', '"\\f026"', False),
        ),
    ),
    (
        '.fa-volume-down',
        (
            ('content', '"\\f027"', False),
        ),
    ),
    (
        '.fa-volume-up',
        (
            ('content', '"\\f028"', False),
        ),
    ),
    (
        '.fa-qrcode',
        (
            ('content', '"\\f029"', False),
        ),
    ),
    (
        '.fa-barcode',
        (
            ('content', '"\\f02a"', False),
        ),
    ),
    (
        '.fa-tag',
        (
            ('content', '"\\f02b"', False),
        ),
    ),
    (
        '.fa-tags',
        (
            ('content', '"\\f02c"', False),
        ),
    ),
    (
        '.fa-book',
        (
            ('content', '"\\f02d"', False),
        ),
    ),
    (
        '.fa-bookmark',
        (
            ('content', '"\\f02e"', False),
        ),
    ),
    (
        '.fa-print',
        (
            ('content', '"\\f02f"', False),
        ),
    ),
    (
        '.fa-camera',
        (
            ('content', '"\\f030"', False),
        ),
    ),
    (
        '.fa-font',
        (
            ('content', '"\\f031"', False),
        ),
    ),
    (
        '.fa-bold',
        (
            ('content', '"\\f032"', False),
        ),
    ),
    (
        '.fa-italic',
        (
            ('content', '"\\f033"', False),
        ),
    ),
    (
        '.fa-text-height',
        (
            ('content', '"\\f034"', False),
        ),
    ),
    (
        '.fa-text-width',
        (
            ('content', '"\\f035"', False),
        ),
    ),
    (
        '.fa-align-left',
        (
            ('content', '"\\f036"', False),
        ),
    ),
    (
        '.fa-align-center',
        (
            ('content', '"\\f037"', False),
        ),
    ),
    (
        '.fa-align-right',
        (
            ('content', '"\\f038"', False),
        ),
    ),
    (
        '.fa-align-justify',
        (
            ('content', '"\\f039"', False),
        ),
    ),
    (
        '.fa-list',
        (
            ('content', '"\\f03a"', False),
        ),
    ),
    (
        '.fa-dedent',
        (
            ('content', '"\\f03b"', False),
        ),
    ),
    (
        '.fa-outdent',
        (
            ('content', '"\\f03b"', False),
        ),
    ),
    (
        '.fa-indent',
        (
            ('content', '"\\f03c"', False),
        ),
    ),
    (
        '.fa-video-camera',
        (
            ('content', '"\\f03d"', False),
        ),
    ),
    (
        '.fa-photo',
        (
            ('content', '"\\f03e"', False),
        ),
    ),
    (
        '.fa-image',
        (
            ('content', '"\\f03e"', False),
        ),
    ),
    (
        '.fa-picture-o',
        (
            ('content', '"\\f03e"', False),
        ),
    ),
    (
        '.fa-pencil',
        (
            ('content', '"\\f040"', False),
        ),
    ),
    (
        '.fa-map-marker',
        (
            ('content', '"\\f041"', False),
        ),
    ),
    (
        '.fa-adjust',
        (
            ('content', '"\\f042"', False),
        ),
    ),
    (
        '.fa-tint',
        (
            ('content', '"\\f043"', False),
        ),
    ),
    (
        '.fa-edit',
        (
            ('content', '"\\f044"', False),
        ),
    ),
    (
        '.fa-pencil-square-o',
        (
            ('content', '"\\f044"', False),
        ),
    ),
    (
        '.fa-share-square-o',
        (
            ('content', '"\\f045"', False),
        ),
    ),
    (
        '.fa-check-square-o',
        (
            ('content', '"\\f046"', False),
        ),
    ),
    (
        '.fa-arrows',
        (
            ('content', '"\\f047"', False),
        ),
    ),
    (
        '.fa-step-backward',
        (
            ('content', '"\\f048"', False),
        ),
    ),
    (
        '.fa-fast-backward',
        (
            ('content', '"\\f049"', False),
        ),
    ),
    (
        '.fa-backward',
        (
            ('content', '"\\f04a"', False),
        ),
    ),
    (
        '.fa-play',
        (
            ('content', '"\\f04b"', False),
        ),
    ),
    (
        '.fa-pause',
        (
            ('content', '"\\f04c"', False),
        ),
    ),
    (
        '.fa-stop',
        (
            ('content', '"\\f04d"', False),
        ),
    ),
    (
        '.fa-forward',
        (
            ('content', '"\\f04e"', False),
        ),
    ),
    (
        '.fa-fast-forward',
        (
            ('content', '"\\f050"', False),
        ),
    ),
    (
        '.fa-step-forward',
        (
            ('content', '"\\f051"', False),
        ),
    ),
    (
        '.fa-eject',
        (
            ('content', '"\\f052"', False),
        ),
    ),
    (
        '.fa-chevron-left',
        (
            ('content', '"\\f053"', False),
        ),
    ),
    (
        '.fa-chevron-right',
        (
            ('content', '"\\f054"', False),
        ),
    ),
    (
        '.fa-plus-circle',
        (
            ('content', '"\\f055"', False),
        ),
    ),
    (
        '.fa-minus-circle',
        (
            ('content', '"\\f056"', False),
        ),
    ),
    (
        '.fa-times-circle',
        (
            ('content', '"\\f057"', False),
        ),
    ),
    (
        '.fa-check-circle',
        (
            ('content', '"\\f058"', False),
        ),
    ),
    (
        '.fa-question-circle',
        (
            ('content', '"\\f059"', False),
        ),
    ),
    (
        '.fa-info-circle',
        (
            ('content', '"\\f05a"', False),
        ),
    ),
    (
        '.fa-crosshairs',
        (
            ('content', '"\\f05b"', False),
        ),
    ),
    (
        '.fa-times-circle-o',
        (
            ('content', '"\\f05c"', False),
        ),
    ),
    (
        '.fa-check-circle-o',
        (
            ('content', '"\\f05d"', False),
        ),
    ),
    (
        '.fa-ban',
        (
            ('content', '"\\f05e"', False),
        ),
    ),
    (
        '.fa-arrow-left',
        (
            ('content', '"\\f060"', False),
        ),
    ),
    (
        '.fa-arrow-right',
        (
            ('content', '"\\f061"', False),
        ),
    ),
    (
        '.fa-arrow-up',
        (
            ('content', '"\\f062"', False),
        ),
    ),
    (
        '.fa-arrow-down',
        (
            ('content', '"\\f063"', False),
        ),
    ),
    (
        '.fa-mail-forward',
        (
            ('content', '"\\f064"', False),
        ),
    ),
    (
        '.fa-share',
        (
            ('content', '"\\f064"', False),
        ),
    ),
    (
        '.fa-expand',
        (
            ('content', '"\\f065"', False),
        ),
    ),
    (
        '.fa-compress',
        (
            ('content', '"\\f066"', False),
        ),
    ),
    (
        '.fa-plus',
        (
            ('content', '"\\f067"', False),
        ),
    ),
    (
        '.fa-minus',
        (
            ('content', '"\\f068"', False),
        ),
    ),
    (
        '.fa-asterisk',
        (
            ('content', '"\\f069"', False),
        ),
    ),
    (
        '.fa-exclamation-circle',
        (
            ('content', '"\\f06a"', False),
        ),
    ),
    (
        '.fa-gift',
        (
            ('content', '"\\f06b"', False),
        ),
    ),
    (
        '.fa-leaf',
        (
            ('content', '"\\f06c"', False),
        ),
    ),
    (
        '.fa-fire',
        (
            ('content', '"\\f06d"', False),
        ),
    ),
    (
        '.fa-eye',
        (
            ('content', '"\\f06e"', False),
        ),
    ),
    (
        '.fa-eye-slash',
        (
            ('content', '"\\f070"', False),
        ),
    ),
    (
        '.fa-warning',
        (
            ('content', '"\\f071"', False),
        ),
    ),
    (
        '.fa-exclamation-triangle',
        (
            ('content', '"\\f071"', False),
        ),
    ),
    (
        '.fa-plane',
        (
            ('content', '"\\f072"', False),
        ),
    ),
    (
        '.fa-calendar',
        (
            ('content', '"\\f073"', False),
        ),
    ),
    (
        '.fa-random',
        (
            ('content', '"\\f074"', False),
        ),
    ),
    (
        '.fa-comment',
        (
            ('content', '"\\f075"', False),
        ),
    ),
    (
        '.fa-magnet',
        (
            ('content', '"\\f076"', False),
        ),
    ),
    (
        '.fa-chevron-up',
        (
            ('content', '"\\f077"', False),
        ),
    ),
    (
        '.fa-chevron-down',
        (
            ('content', '"\\f078"', False),
        ),
    ),
    (
        '.fa-retweet',
        (
            ('content', '"\\f079"', False),
        ),
    ),
    (
        '.fa-shopping-cart',
        (
            ('content', '"\\f07a"', False),
        ),
    ),
    (
        '.fa-folder',
        (
            ('content', '"\\f07b"', False),
        ),
    ),
    (
        '.fa-folder-open',
        (
            ('content', '"\\f07c"', False),
        ),
    ),
    (
        '.fa-arrows-v',
        (
            ('content', '"\\f07d"', False),
        ),
    ),
    (
        '.fa-arrows-h',
        (
            ('content', '"\\f07e"', False),
        ),
    ),
    (
        '.fa-bar-chart-o',
        (
            ('content', '"\\f080"', False),
        ),
    ),
    (
        '.fa-bar-chart',
        (
            ('content', '"\\f080"', False),
        ),
    ),
    (
        '.fa-twitter-square',
        (
            ('content', '"\\f081"', False),
        ),
    ),
    (
        '.fa-facebook-square',
        (
            ('content', '"\\f082"', False),
        ),
    ),
    (
        '.fa-camera-retro',
        (
            ('content', '"\\f083"', False),
        ),
    ),
    (
        '.fa-key',
        (
            ('content', '"\\f084"', False),
        ),
    ),
    (
        '.fa-gears',
        (
            ('content', '"\\f085"', False),
        ),
    ),
    (
        '.fa-cogs',
        (
            ('content', '"\\f085"', False),
        ),
    ),
    (
        '.fa-comments',
        (
            ('content', '"\\f086"', False),
        ),
    ),
    (
        '.fa-thumbs-o-up',
        (
            ('content', '"\\f087"', False),
        ),
    ),
    (
        '.fa-thumbs-o-down',
        (
            ('content', '"\\f088"', False),
        ),
    ),
    (
        '.fa-star-half',
        (
            ('content', '"\\f089"', False),
        ),
    ),
    (
        '.fa-heart-o',
        (
            ('content', '"\\f08a"', False),
        ),
    ),
    (
        '.fa-sign-out',
        (
            ('content', '"\\f08b"', False),
        ),
    ),
    (
        '.fa-linkedin-square',
        (
            ('content', '"\\f08c"', False),
        ),
    ),
    (
        '.fa-thumb-tack',
        (
            ('content', '"\\f08d"', False),
        ),
    ),
    (
        '.fa-external-link',
        (
            ('content', '"\\f08e"', False),
        ),
    ),
    (
        '.fa-sign-in',
        (
            ('content', '"\\f090"', False),
        ),
    ),
    (
        '.fa-trophy',
        (
            ('content', '"\\f091"', False),
        ),
    ),
    (
        '.fa-github-square',
        (
            ('content', '"\\f092"', False),
        ),
    ),
    (
        '.fa-upload',
        (
            ('content', '"\\f093"', False),
        ),
    ),
    (
        '.fa-lemon-o',
        (
            ('content', '"\\f094"', False),
        ),
    ),
    (
        '.fa-phone',
        (
            ('content', '"\\f095"', False),
        ),
    ),
    (
        '.fa-square-o',
        (
            ('content', '"\\f096"', False),
        ),
    ),
    (
        '.fa-bookmark-o',
        (
            ('content', '"\\f097"', False),
        ),
    ),
    (
        '.fa-phone-square',
        (
            ('content', '"\\f098"', False),
        ),
    ),
    (
        '.fa-twitter',
        (
            ('content', '"\\f099"', False),
        ),
    ),
    (
        '.fa-facebook-f',
        (
            ('content', '"\\f09a"', False),
        ),
    ),
    (
        '.fa-facebook',
        (
            ('content', '"\\f09a"', False),
        ),
    ),
    (
        '.fa-github',
        (
            ('content', '"\\f09b"', False),
        ),
    ),
    (
        '.fa-unlock',
        (
            ('content', '"\\f09c"', False),
        ),
    ),
    (
        '.fa-credit-card',
        (
            ('content', '"\\f09d"', False),
        ),
    ),
    (
        '.fa-feed',
        (
            ('content', '"\\f09e"', False),
        ),
    ),
    (
        '.fa-rss',
        (
            ('content', '"\\f09e"', False),
        ),
    ),
    (
        '.fa-hdd-o',
        (
            ('content', '"\\f0a0"', False),
        ),
    ),
    (
        '.fa-bullhorn',
        (
            ('content', '"\\f0a1"', False),
        ),
    ),
    (
        '.fa-bell',
        (
            ('content', '"\\f0f3"', False),
        ),
    ),
    (
        '.fa-certificate',
        (
            ('content', '"\\f0a3"', False),
        ),
    ),
    (
        '.fa-hand-o-right',
        (
            ('content', '"\\f0a4"', False),
        ),
    ),
    (
        '.fa-hand-o-left',
        (
            ('content', '"\\f0a5"', False),
        ),
    ),
    (
        '.fa-hand-o-up',
        (
            ('content', '"\\f0a6"', False),
        ),
    ),
    (
        '.fa-hand-o-down',
        (
            ('content', '"\\f0a7"', False),
        ),
    ),
    (
        '.fa-arrow-circle-left',
        (
            ('content', '"\\f0a8"', False),
        ),
    ),
    (
        '.fa-arrow-circle-right',
        (
            ('content', '"\\f0a9"', False),
        ),
    ),
    (
        '.fa-arrow-circle-up',
        (
            ('content', '"\\f0aa"', False),
        ),
    ),
    (
        '.fa-arrow-circle-down',
        (
            ('content', '"\\f0ab"', False),
        ),
    ),
    (
        '.fa-globe',
        (
            ('content', '"\\f0ac"', False),
        ),
    ),
    (
        '.fa-wrench',
        (
            ('content', '"\\f0ad"', False),
        ),
    ),
    (
        '.fa-tasks',
        (
            ('content', '"\\f0ae"', False),
        ),
    ),
    (
        '.fa-filter',
        (
            ('content', '"\\f0b0"', False),
        ),
    ),
    (
        '.fa-briefcase',
        (
            ('content', '"\\f0b1"', False),
        ),
    ),
    (
        '.fa-arrows-alt',
        (
            ('content', '"\\f0b2"', False),
        ),
    ),
    (
        '.fa-group',
        (
            ('content', '"\\f0c0"', False),
        ),
    ),
    (
        '.fa-users',
        (
            ('content', '"\\f0c0"', False),
        ),
    ),
    (
        '.fa-chain',
        (
            ('content', '"\\f0c1"', False),
        ),
    ),
    (
        '.fa-link',
        (
            ('content', '"\\f0c1"', False),
        ),
    ),
    (
        '.fa-cloud',
        (
            ('content', '"\\f0c2"', False),
        ),
    ),
    (
        '.fa-flask',
        (
            ('content', '"\\f0c3"', False),
        ),
    ),
    (
        '.fa-cut',
        (
            ('content', '"\\f0c4"', False),
        ),
    ),
    (
        '.fa-scissors',
        (
            ('content', '"\\f0c4"', False),
        ),
    ),
    (
        '.fa-copy',
        (
            ('content', '"\\f0c5"', False),
        ),
    ),
    (
        '.fa-files-o',
        (
            ('content', '"\\f0c5"', False),
        ),
    ),
    (
        '.fa-paperclip',
        (
            ('content', '"\\f0c6"', False),
        ),
    ),
    (
        '.fa-save',
        (
            ('content', '"\\f0c7"', False),
        ),
    ),
    (
        '.fa-floppy-o',
        (
            ('content', '"\\f0c7"', False),
        ),
    ),
    (
        '.fa-square',
        (
            ('content', '"\\f0c8"', False),
        ),
    ),
    (
        '.fa-navicon',
        (
            ('content', '"\\f0c9"', False),
        ),
    ),
    (
        '.fa-reorder',
        (
            ('content', '"\\f0c9"', False),
        ),
    ),
    (
        '.fa-bars',
        (
            ('content', '"\\f0c9"', False),
        ),
    ),
    (
        '.fa-list-ul',
        (
            ('content', '"\\f0ca"', False),
        ),
    ),
    (
        '.fa-list-ol',
        (
            ('content', '"\\f0cb"', False),
        ),
    ),
    (
        '.fa-strikethrough',
        (
            ('content', '"\\f0cc"', False),
        ),
    ),
    (
        '.fa-underline',
        (
            ('content', '"\\f0cd"', False),
        ),
    ),
    (
        '.fa-table',
        (
            ('content', '"\\f0ce"', False),
        ),
    ),
    (
        '.fa-magic',
        (
            ('content', '"\\f0d0"', False),
        ),
    ),
    (
        '.fa-truck',
        (
            ('content', '"\\f0d1"', False),
        ),
    ),
    (
        '.fa-pinterest',
        (
            ('content', '"\\f0d2"', False),
        ),
    ),
    (
        '.fa-pinterest-square',
        (
            ('content', '"\\f0d3"', False),
        ),
    ),
    (
        '.fa-google-plus-square',
        (
            ('content', '"\\f0d4"', False),
        ),
    ),
    (
        '.fa-google-plus',
        (
            ('content', '"\\f0d5"', False),
        ),
    ),
    (
        '.fa-money',
        (
            ('content', '"\\f0d6"', False),
        ),
    ),
    (
        '.fa-caret-down',
        (
            ('content', '"\\f0d7"', False),
        ),
    ),
    (
        '.fa-caret-up',
        (
            ('content', '"\\f0d8"', False),
        ),
    ),
    (
        '.fa-caret-left',
        (
            ('content', '"\\f0d9"', False),
        ),
    ),
    (
        '.fa-caret-right',
        (
            ('content', '"\\f0da"', False),
        ),
    ),
    (
        '.fa-columns',
        (
            ('content', '"\\f0db"', False),
        ),
    ),
    (
        '.fa-unsorted',
        (
            ('content', '"\\f0dc"', False),
        ),
    ),
    (
        '.fa-sort',
        (
            ('content', '"\\f0dc"', False),
        ),
    ),
    (
        '.fa-sort-down',
        (
            ('content', '"\\f0dd"', False),
        ),
    ),
    (
        '.fa-sort-desc',
        (
            ('content', '"\\f0dd"', False),
        ),
    ),
    (
        '.fa-sort-up',
        (
            ('content', '"\\f0de"', False),
        ),
    ),
    (
        '.fa-sort-asc',
        (
            ('content', '"\\f0de"', False),
        ),
    ),
    (
        '.fa-envelope',
        (
            ('content', '"\\f0e0"', False),
        ),
    ),
    (
        '.fa-linkedin',
        (
            ('content', '"\\f0e1"', False),
        ),
    ),
    (
        '.fa-rotate-left',
        (
            ('content', '"\\f0e2"', False),
        ),
    ),
    (
        '.fa-undo',
        (
            ('content', '"\\f0e2"', False),
        ),
    ),
    (
        '.fa-legal',
        (
            ('content', '"\\f0e3"', False),
        ),
    ),
    (
        '.fa-gavel',
        (
            ('content', '"\\f0e3"', False),
        ),
    ),
    (
        '.fa-dashboard',
        (
            ('content', '"\\f0e4"', False),
        ),
    ),
    (
        '.fa-tachometer',
        (
            ('content', '"\\f0e4"', False),
        ),
    ),
    (
        '.fa-comment-o',
        (
            ('content', '"\\f0e5"', False),
        ),
    ),
    (
        '.fa-comments-o',
        (
            ('content', '"\\f0e6"', False),
        ),
    ),
    (
        '.fa-flash',
        (
            ('content', '"\\f0e7"', False),
        ),
    ),
    (
        '.fa-bolt',
        (
            ('content', '"\\f0e7"', False),
        ),
    ),
    (
        '.fa-sitemap',
        (
            ('content', '"\\f0e8"', False),
        ),
    ),
    (
        '.fa-umbrella',
        (
            ('content', '"\\f0e9"', False),
        ),
    ),
    (
        '.fa-paste',
        (
            ('content', '"\\f0ea"', False),
        ),
    ),
    (
        '.fa-clipboard',
        (
            ('content', '"\\f0ea"', False),
        ),
    ),
    (
        '.fa-lightbulb-o',
        (
            ('content', '"\\f0eb"', False),
        ),
    ),
    (
        '.fa-exchange',
        (
            ('content', '"\\f0ec"', False),
        ),
    ),
    (
        '.fa-cloud-download',
        (
            ('content', '"\\f0ed"', False),
        ),
    ),
    (
        '.fa-cloud-upload',
        (
            ('content', '"\\f0ee"', False),
        ),
    ),
    (
        '.fa-user-md',
        (
            ('content', '"\\f0f0"', False),
        ),
    ),
    (
        '.fa-stethoscope',
        (
            ('content', '"\\f0f1"', False),
        ),
    ),
    (
        '.fa-suitcase',
        (
            ('content', '"\\f0f2"', False),
        ),
    ),
    (
        '.fa-bell-o',
        (
            ('content', '"\\f0a2"', False),
        ),
    ),
    (
        '.fa-coffee',
        (
            ('content', '"\\f0f4"', False),
        ),
    ),
    (
        '.fa-cutlery',
        (
            ('content', '"\\f0f5"', False),
        ),
    ),
    (
        '.fa-file-text-o',
        (
            ('content', '"\\f0f6"', False),
        ),
    ),
    (
        '.fa-building-o',
        (
            ('content', '"\\f0f7"', False),
        ),
    ),
    (
        '.fa-hospital-o',
        (
            ('content', '"\\f0f8"', False),
        ),
    ),
    (
        '.fa-ambulance',
        (
            ('content', '"\\f0f9"', False),
        ),
    ),
    (
        '.fa-medkit',
        (
            ('content', '"\\f0fa"', False),
        ),
    ),
    (
        '.fa-fighter-jet',
        (
            ('content', '"\\f0fb"', False),
        ),
    ),
    (
        '.fa-beer',
        (
            ('content', '"\\f0fc"', False),
        ),
    ),
    (
        '.fa-h-square',
        (
            ('content', '"\\f0fd"', False),
        ),
    ),
    (
        '.fa-plus-square',
        (
            ('content', '"\\f0fe"', False),
        ),
    ),
    (
        '.fa-angle-double-left',
        (
            ('content', '"\\f100"', False),
        ),
    ),
    (
        '.fa-angle-double-right',
        (
            ('content', '"\\f101"', False),
        ),
    ),
    (
        '.fa-angle-double-up',
        (
            ('content', '"\\f102"', False),
        ),
    ),
    (
        '.fa-angle-double-down',
        (
            ('content', '"\\f103"', False),
        ),
    ),
    (
        '.fa-angle-left',
        (
            ('content', '"\\f104"', False),
        ),
    ),
    (
        '.fa-angle-right',
        (
            ('content', '"\\f105"', False),
        ),
    ),
    (
        '.fa-angle-up',
        (
            ('content', '"\\f106"', False),
        ),
    ),
    (
        '.fa-angle-down',
        (
            ('content', '"\\f107"', False),
        ),
    ),
    (
        '.fa-desktop',
        (
            ('content', '"\\f108"', False),
        ),
    ),
    (
        '.fa-laptop',
        (
            ('content', '"\\f109"', False),
        ),
    ),
    (
        '.fa-tablet',
        (
            ('content', '"\\f10a"', False),
        ),
    ),
    (
        '.fa-mobile-phone',
        (
            ('content', '"\\f10b"', False),
        ),
    ),
    (
        '.fa-mobile',
        (
            ('content', '"\\f10b"', False),
        ),
    ),
    (
        '.fa-circle-o',
        (
            ('content', '"\\f10c"', False),
        ),
    ),
    (
        '.fa-quote-left',
        (
            ('content', '"\\f10d"', False),
        ),
    ),
    (
        '.fa-quote-right',
        (
            ('content', '"\\f10e"', False),
        ),
    ),
    (
        '.fa-spinner',
        (
            ('content', '"\\f110"', False),
        ),
    ),
    (
        '.fa-circle',
        (
            ('content', '"\\f111"', False),
        ),
    ),
    (
        '.fa-mail-reply',
        (
            ('content', '"\\f112"', False),
        ),
    ),
    (
        '.fa-reply',
        (
            ('content', '"\\f112"', False),
        ),
    ),
    (
        '.fa-github-alt',
        (
            ('content', '"\\f113"', False),
        ),
    ),
    (
        '.fa-folder-o',
        (
            ('content', '"\\f114"', False),
        ),
    ),
    (
        '.fa-folder-open-o',
        (
            ('content', '"\\f115"', False),
        ),
    ),
    (
        '.fa-smile-o',
        (
            ('content', '"\\f118"', False),
        ),
    ),
    (
        '.fa-frown-o',
        (
            ('content', '"\\f119"', False),
        ),
    ),
    (
        '.fa-meh-o',
        (
            ('content', '"\\f11a"', False),
        ),
    ),
    (
        '.fa-gamepad',
        (
            ('content', '"\\f11b"', False),
        ),
    ),
    (
        '.fa-keyboard-o',
        (
            ('content', '"\\f11c"', False),
        ),
    ),
    (
        '.fa-flag-o',
        (
            ('content', '"\\f11d"', False),
        ),
    ),
    (
        '.fa-flag-checkered',
        (
            ('content', '"\\f11e"', False),
        ),
    ),
    (
        '.fa-terminal',
        (
            ('content', '"\\f120"', False),
        ),
    ),
    (
        '.fa-code',
        (
            ('content', '"\\f121"', False),
        ),
    ),
    (
        '.fa-mail-reply-all',
        (
            ('content', '"\\f122"', False),
        ),
    ),
    (
        '.fa-reply-all',
        (
            ('content', '"\\f122"', False),
        ),
    ),
    (
        '.fa-star-half-empty',
        (
            ('content', '"\\f123"', False),
        ),
    ),
    (
        '.fa-star-half-full',
        (
            ('content', '"\\f123"', False),
        ),
    ),
    (
        '.fa-star-half-o',
        (
            ('content', '"\\f123"', False),
        ),
    ),
    (
        '.fa-location-arrow',
        (
            ('content', '"\\f124"', False),
        ),
    ),
    (
        '.fa-crop',
        (
            ('content', '"\\f125"', False),
        ),
    ),
    (
        '.fa-code-fork',
        (
            ('content', '"\\f126"', False),
        ),
    ),
    (
        '.fa-unlink',
        (
            ('content', '"\\f127"', False),
        ),
    ),
    (
        '.fa-chain-broken',
        (
            ('content', '"\\f127"', False),
        ),
    ),
    (
        '.fa-question',
        (
            ('content', '"\\f128"', False),
        ),
    ),
    (
        '.fa-info',
        (
            ('content', '"\\f129"', False),
        ),
    ),
    (
        '.fa-exclamation',
        (
            ('content', '"\\f12a"', False),
        ),
    ),
    (
        '.fa-superscript',
        (
            ('content', '"\\f12b"', False),
        ),
    ),
    (
        '.fa-subscript',
        (
            ('content', '"\\f12c"', False),
        ),
    ),
    (
        '.fa-eraser',
        (
            ('content', '"\\f12d"', False),
        ),
    ),
    (
        '.fa-puzzle-piece',
        (
            ('content', '"\\f12e"', False),
        ),
    ),
    (
        '.fa-microphone',
        (
            ('content', '"\\f130"', False),
        ),
    ),
    (
        '.fa-microphone-slash',
        (
            ('content', '"\\f131"', False),
        ),
    ),
    (
        '.fa-shield',
        (
            ('content', '"\\f132"', False),
        ),
    ),
    (
        '.fa-calendar-o',
        (
            ('content', '"\\f133"', False),
        ),
    ),
    (
        '.fa-fire-extinguisher',
        (
            ('content', '"\\f134"', False),
        ),
    ),
    (
        '.fa-rocket',
        (
            ('content', '"\\f135"', False),
        ),
    ),
    (
        '.fa-maxcdn',
        (
            ('content', '"\\f136"', False),
        ),
    ),
    (
        '.fa-chevron-circle-left',
        (
            ('content', '"\\f137"', False),
        ),
    ),
    (
        '.fa-chevron-circle-right',
        (
            ('content', '"\\f138"', False),
        ),
    ),
    (
        '.fa-chevron-circle-up',
        (
            ('content', '"\\f139"', False),
        ),
    ),
    (
        '.fa-chevron-circle-down',
        (
            ('content', '"\\f13a"', False),
        ),
    ),
    (
        '.fa-html5',
        (
            ('content', '"\\f13b"', False),
        ),
    ),
    (
        '.fa-css3',
        (
            ('content', '"\\f13c"', False),
        ),
    ),
    (
        '.fa-anchor',
        (
            ('content', '"\\f13d"', False),
        ),
    ),
    (
        '.fa-unlock-alt',
        (
            ('content', '"\\f13e"', False),
        ),
    ),
    (
        '.fa-bullseye',
        (
            ('content', '"\\f140"', False),
        ),
    ),
    (
        '.fa-ellipsis-h',
        (
            ('content', '"\\f141"', False),
        ),
    ),
    (
        '.fa-ellipsis-v',
        (
            ('content', '"\\f142"', False),
        ),
    ),
    (
        '.fa-rss-square',
        (
            ('content', '"\\f143"', False),
        ),
    ),
    (
        '.fa-play-circle',
        (
            ('content', '"\\f144"', False),
        ),
    ),
    (
        '.fa-ticket',
        (
            ('content', '"\\f145"', False),
        ),
    ),
    (
        '.fa-minus-square',
        (
            ('content', '"\\f146"', False),
        ),
    ),
    (
        '.fa-minus-square-o',
        (
            ('content', '"\\f147"', False),
        ),
    ),
    (
        '.fa-level-up',
        (
            ('content', '"\\f148"', False),
        ),
    ),
    (
        '.fa-level-down',
        (
            ('content', '"\\f149"', False),
        ),
    ),
    (
        '.fa-check-square',
        (
            ('content', '"\\f14a"', False),
        ),
    ),
    (
        '.fa-pencil-square',
        (
            ('content', '"\\f14b"', False),
        ),
    ),
    (
        '.fa-external-link-square',
        (
            ('content', '"\\f14c"', False),
        ),
    ),
    (
        '.fa-share-square',
        (
            ('content', '"\\f14d"', False),
        ),
    ),
    (
        '.fa-compass',
        (
            ('content', '"\\f14e"', False),
        ),
    ),
    (
        '.fa-toggle-down',
        (
            ('content', '"\\f150"', False),
        ),
    ),
    (
        '.fa-caret-square-o-down',
        (
            ('content', '"\\f150"', False),
        ),
    ),
    (
        '.fa-toggle-up',
        (
            ('content', '"\\f151"', False),
        ),
    ),
    (
        '.fa-caret-square-o-up',
        (
            ('content', '"\\f151"', False),
        ),
    ),
    (
        '.fa-toggle-right',
        (
            ('content', '"\\f152"', False),
        ),
    ),
    (
        '.fa-caret-square-o-right',
        (
            ('content', '"\\f152"', False),
        ),
    ),
    (
        '.fa-euro',
        (
            ('content', '"\\f153"', False),
        ),
    ),
    (
        '.fa-eur',
        (
            ('content', '"\\f153"', False),
        ),
    ),
    (
        '.fa-gbp',
        (
            ('content', '"\\f154"', False),
        ),
    ),
    (
        '.fa-dollar',
        (
            ('content', '"\\f155"', False),
        ),
    ),
    (
        '.fa-usd',
        (
            ('content', '"\\f155"', False),
        ),
    ),
    (
        '.fa-rupee',
        (
            ('content', '"\\f156"', False),
        ),
    ),
    (
        '.fa-inr',
        (
            ('content', '"\\f156"', False),
        ),
    ),
    (
        '.fa-cny',
        (
            ('content', '"\\f157"', False),
        ),
    ),
    (
        '.fa-rmb',
        (
            ('content', '"\\f157"', False),
        ),
    ),
    (
        '.fa-yen',
        (
            ('content', '"\\f157"', False),
        ),
    ),
    (
        '.fa-jpy',
        (
            ('content', '"\\f157"', False),
        ),
    ),
    (
        '.fa-ruble',
        (
            ('content', '"\\f158"', False),
        ),
    ),
    (
        '.fa-rouble',
        (
            ('content', '"\\f158"', False),
        ),
    ),
    (
        '.fa-rub',
        (
            ('content', '"\\f158"', False),
        ),
    ),
    (
        '.fa-won',
        (
            ('content', '"\\f159"', False),
        ),
    ),
    (
        '.fa-krw',
        (
            ('content', '"\\f159"', False),
        ),
    ),
    (
        '.fa-bitcoin',
        (
            ('content', '"\\f15a"', False),
        ),
    ),
    (
        '.fa-btc',
        (
            ('content', '"\\f15a"', False),
        ),
    ),
    (
        '.fa-file',
        (
            ('content', '"\\f15b"', False),
        ),
    ),
    (
        '.fa-file-text',
        (
            ('content', '"\\f15c"', False),
        ),
    ),
    (
        '.fa-sort-alpha-asc',
        (
            ('content', '"\\f15d"', False),
        ),
    ),
    (
        '.fa-sort-alpha-desc',
        (
            ('content', '"\\f15e"', False),
        ),
    ),
    (
        '.fa-sort-amount-asc',
        (
            ('content', '"\\f160"', False),
        ),
    ),
    (
        '.fa-sort-amount-desc',
        (
            ('content', '"\\f161"', False),
        ),
    ),
    (
        '.fa-sort-numeric-asc',
        (
            ('content', '"\\f162"', False),
        ),
    ),
    (
        '.fa-sort-numeric-desc',
        (
            ('content', '"\\f163"', False),
        ),
    ),
    (
        '.fa-thumbs-up',
        (
            ('content', '"\\f164"', False),
        ),
    ),
    (
        '.fa-thumbs-down',
        (
            ('content', '"\\f165"', False),
        ),
    ),
    (
        '.fa-youtube-square',
        (
            ('content', '"\\f166"', False),
        ),
    ),
    (
        '.fa-youtube',
        (
            ('content', '"\\f167"', False),
        ),
    ),
    (
        '.fa-xing',
        (
            ('content', '"\\f168"', False),
        ),
    ),
    (
        '.fa-xing-square',
        (
            ('content', '"\\f169"', False),
        ),
    ),
    (
        '.fa-youtube-play',
        (
            ('content', '"\\f16a"', False),
        ),
    ),
    (
        '.fa-dropbox',
        (
            ('content', '"\\f16b"', False),
        ),
    ),
    (
        '.fa-stack-overflow',
        (
            ('content', '"\\f16c"', False),
        ),
    ),
    (
        '.fa-instagram',
        (
            ('content', '"\\f16d"', False),
        ),
    ),
    (
        '.fa-flickr',
        (
            ('content', '"\\f16e"', False),
        ),
    ),
    (
        '.fa-adn',
        (
            ('content', '"\\f170"', False),
        ),
    ),
    (
        '.fa-bitbucket',
        (
            ('content', '"\\f171"', False),
        ),
    ),
    (
        '.fa-bitbucket-square',
        (
            ('content', '"\\f172"', False),
        ),
    ),
    (
        '.fa-tumblr',
        (
            ('content', '"\\f173"', False),
        ),
    ),
    (
        '.fa-tumblr-square',
        (
            ('content', '"\\f174"', False),
        ),
    ),
    (
        '.fa-long-arrow-down',
        (
            ('content', '"\\f175"', False),
        ),
    ),
    (
        '.fa-long-arrow-up',
        (
            ('content', '"\\f176"', False),
        ),
    ),
    (
        '.fa-long-arrow-left',
        (
            ('content', '"\\f177"', False),
        ),
    ),
    (
        '.fa-long-arrow-right',
        (
            ('content', '"\\f178"', False),
        ),
    ),
    (
        '.fa-apple',
        (
            ('content', '"\\f179"', False),
        ),
    ),
    (
        '.fa-windows',
        (
            ('content', '"\\f17a"', False),
        ),
    ),
    (
        '.fa-android',
        (
            ('content', '"\\f17b"', False),
        ),
    ),
    (
        '.fa-linux',
        (
            ('content', '"\\f17c"', False),
        ),
    ),
    (
        '.fa-dribbble',
        (
            ('content', '"\\f17d"', False),
        ),
    ),
    (
        '.fa-skype',
        (
            ('content', '"\\f17e"', False),
        ),
    ),
    (
        '.fa-foursquare',
        (
            ('content', '"\\f180"', False),
        ),
    ),
    (
        '.fa-trello',
        (
            ('content', '"\\f181"', False),
        ),
    ),
    (
        '.fa-female',
        (
            ('content', '"\\f182"', False),
        ),
    ),
    (
        '.fa-male',
        (
            ('content', '"\\f183"', False),
        ),
    ),
    (
        '.fa-gittip',
        (
            ('content', '"\\f184"', False),
        ),
    ),
    (
        '.fa-gratipay',
        (
            ('content', '"\\f184"', False),
        ),
    ),
    (
        '.fa-sun-o',
        (
            ('content', '"\\f185"', False),
        ),
    ),
    (
        '.fa-moon-o',
        (
            ('content', '"\\f186"', False),
        ),
    ),
    (
        '.fa-archive',
        (
            ('content', '"\\f187"', False),
        ),
    ),
    (
        '.fa-bug',
        (
            ('content', '"\\f188"', False),
        ),
    ),
    (
        '.fa-vk',
        (
            ('content', '"\\f189"', False),
        ),
    ),
    (
        '.fa-weibo',
        (
            ('content', '"\\f18a"', False),
        ),
    ),
    (
        '.fa-renren',
        (
            ('content', '"\\f18b"', False),
        ),
    ),
    (
        '.fa-pagelines',
        (
            ('content', '"\\f18c"', False),
        ),
    ),
    (
        '.fa-stack-exchange',
        (
            ('content', '"\\f18d"', False),
        ),
    ),
    (
        '.fa-arrow-circle-o-right',
        (
            ('content', '"\\f18e"', False),
        ),
    ),
    (
        '.fa-arrow-circle-o-left',
        (
            ('content', '"\\f190"', False),
        ),
    ),
    (
        '.fa-toggle-left',
        (
            ('content', '"\\f191"', False),
        ),
    ),
    (
        '.fa-caret-square-o-left',
        (
            ('content', '"\\f191"', False),
        ),
    ),
    (
        '.fa-dot-circle-o',
        (
            ('content', '"\\f192"', False),
        ),
    ),
    (
        '.fa-wheelchair',
        (
            ('content', '"\\f193"', False),
        ),
    ),
    (
        '.fa-vimeo-square',
        (
            ('content', '"\\f194"', False),
        ),
    ),
    (
        '.fa-turkish-lira',
        (
            ('content', '"\\f195"', False),
        ),
    ),
    (
        '.fa-try',
        (
            ('content', '"\\f195"', False),
        ),
    ),
    (
        '.fa-plus-square-o',
        (
            ('content', '"\\f196"', False),
        ),
    ),
    (
        '.fa-space-shuttle',
        (
            ('content', '"\\f197"', False),
        ),
    ),
    (
        '.fa-slack',
        (
            ('content', '"\\f198"', False),
        ),
    ),
    (
        '.fa-envelope-square',
        (
            ('content', '"\\f199"', False),
        ),
    ),
    (
        '.fa-wordpress',
        (
            ('content', '"\\f19a"', False),
        ),
    ),
    (
        '.fa-openid',
        (
            ('content', '"\\f19b"', False),
        ),
    ),
    (
        '.fa-institution',
        (
            ('content', '"\\f19c"', False),
        ),
    ),
    (
        '.fa-bank',
        (
            ('content', '"\\f19c"', False),
        ),
    ),
    (
        '.fa-university',
        (
            ('content', '"\\f19c"', False),
        ),
    ),
    (
        '.fa-mortar-board',
        (
            ('content', '"\\f19d"', False),
        ),
    ),
    (
        '.fa-graduation-cap',
        (
            ('content', '"\\f19d"', False),
        ),
    ),
    (
        '.fa-yahoo',
        (
            ('content', '"\\f19e"', False),
        ),
    ),
    (
        '.fa-google',
        (
            ('content', '"\\f1a0"', False),
        ),
    ),
    (
        '.fa-reddit',
        (
            ('content', '"\\f1a1"', False),
        ),
    ),
    (
        '.fa-reddit-square',
        (
            ('content', '"\\f1a2"', False),
        ),
    ),
    (
        '.fa-stumbleupon-circle',
        (
            ('content', '"\\f1a3"', False),
        ),
    ),
    (
        '.fa-stumbleupon',
        (
            ('content', '"\\f1a4"', False),
        ),
    ),
    (
        '.fa-delicious',
        (
            ('content', '"\\f1a5"', False),
        ),
    ),
    (
        '.fa-digg',
        (
            ('content', '"\\f1a6"', False),
        ),
    ),
    (
        '.fa-pied-piper-pp',
        (
            ('content', '"\\f1a7"', False),
        ),
    ),
    (
        '.fa-pied-piper-alt',
        (
            ('content', '"\\f1a8"', False),
        ),
    ),
    (
        '.fa-drupal',
        (
            ('content', '"\\f1a9"', False),
        ),
    ),
    (
        '.fa-joomla',
        (
            ('content', '"\\f1aa"', False),
        ),
    ),
    (
        '.fa-language',
        (
            ('content', '"\\f1ab"', False),
        ),
    ),
    (
        '.fa-fax',
        (
            ('content', '"\\f1ac"', False),
        ),
    ),
    (
        '.fa-building',
        (
            ('content', '"\\f1ad"', False),
        ),
    ),
    (
        '.fa-child',
        (
            ('content', '"\\f1ae"', False),
        ),
    ),
    (
        '.fa-paw',
        (
            ('content', '"\\f1b0"', False),
        ),
    ),
    (
        '.fa-spoon',
        (
            ('content', '"\\f1b1"', False),
        ),
    ),
    (
        '.fa-cube',
        (
            ('content', '"\\f1b2"', False),
        ),
    ),
    (
        '.fa-cubes',
        (
            ('content', '"\\f1b3"', False),
        ),
    ),
    (
        '.fa-behance',
        (
            ('content', '"\\f1b4"', False),
        ),
    ),
    (
        '.fa-behance-square',
        (
            ('content', '"\\f1b5"', False),
        ),
    ),
    (
        '.fa-steam',
        (
            ('content', '"\\f1b6"', False),
        ),
    ),
    (
        '.fa-steam-square',
        (
            ('content', '"\\f1b7"', False),
        ),
    ),
    (
        '.fa-recycle',
        (
            ('content', '"\\f1b8"', False),
        ),
    ),
    (
        '.fa-automobile',
        (
            ('content', '"\\f1b9"', False),
        ),
    ),
    (
        '.fa-car',
        (
            ('content', '"\\f1b9"', False),
        ),
    ),
    (
        '.fa-cab',
        (
            ('content', '"\\f1ba"', False),
        ),
    ),
    (
        '.fa-taxi',
        (
            ('content', '"\\f1ba"', False),
        ),
    ),
    (
        '.fa-tree',
        (
            ('content', '"\\f1bb"', False),
        ),
    ),
    (
        '.fa-spotify',
        (
            ('content', '"\\f1bc"', False),
        ),
    ),
    (
        '.fa-deviantart',
        (
            ('content', '"\\f1bd"', False),
        ),
    ),
    (
        '.fa-soundcloud',
        (
            ('content', '"\\f1be"', False),
        ),
    ),
    (
        '.fa-database',
        (
            ('content', '"\\f1c0"', False),
        ),
    ),
    (
        '.fa-file-pdf-o',
        (
            ('content', '"\\f1c1"', False),
        ),
    ),
    (
        '.fa-file-word-o',
        (
            ('content', '"\\f1c2"', False),
        ),
    ),
    (
        '.fa-file-excel-o',
        (
            ('content', '"\\f1c3"', False),
        ),
    ),
    (
        '.fa-file-powerpoint-o',
        (
            ('content', '"\\f1c4"', False),
        ),
    ),
    (
        '.fa-file-photo-o',
        (
            ('content', '"\\f1c5"', False),
        ),
    ),
    (
        '.fa-file-picture-o',
        (
            ('content', '"\\f1c5"', False),
        ),
    ),
    (
        '.fa-file-image-o',
        (
            ('content', '"\\f1c5"', False),
        ),
    ),
    (
        '.fa-file-zip-o',
        (
            ('content', '"\\f1c6"', False),
        ),
    ),
    (
        '.fa-file-archive-o',
        (
            ('content', '"\\f1c6"', False),
        ),
    ),
    (
        '.fa-file-sound-o',
        (
            ('content', '"\\f1c7"', False),
        ),
    ),
    (
        '.fa-file-audio-o',
        (
            ('content', '"\\f1c7"', False),
        ),
    ),
    (
        '.fa-file-movie-o',
        (
            ('content', '"\\f1c8"', False),
        ),
    ),
    (
        '.fa-file-video-o',
        (
            ('content', '"\\f1c8"', False),
        ),
    ),
    (
        '.fa-file-code-o',
        (
            ('content', '"\\f1c9"', False),
        ),
    ),
    (
        '.fa-vine',
        (
            ('content', '"\\f1ca"', False),
        ),
    ),
    (
        '.fa-codepen',
        (
            ('content', '"\\f1cb"', False),
        ),
    ),
    (
        '.fa-jsfiddle',
        (
            ('content', '"\\f1cc"', False),
        ),
    ),
    (
        '.fa-life-bouy',
        (
            ('content', '"\\f1cd"', False),
        ),
    ),
    (
        '.fa-life-buoy',
        (
            ('content', '"\\f1cd"', False),
        ),
    ),
    (
        '.fa-life-saver',
        (
            ('content', '"\\f1cd"', False),
        ),
    ),
    (
        '.fa-support',
        (
            ('content', '"\\f1cd"', False),
        ),
    ),
    (
        '.fa-life-ring',
        (
            ('content', '"\\f1cd"', False),
        ),
    ),
    (
        '.fa-circle-o-notch',
        (
            ('content', '"\\f1ce"', False),
        ),
    ),
    (
        '.fa-ra',
        (
            ('content', '"\\f1d0"', False),
        ),
    ),
    (
        '.fa-resistance',
        (
            ('content', '"\\f1d0"', False),
        ),
    ),
    (
        '.fa-rebel',
        (
            ('content', '"\\f1d0"', False),
        ),
    ),
    (
        '.fa-ge',
        (
            ('content', '"\\f1d1"', False),
        ),
    ),
    (
        '.fa-empire',
        (
            ('content', '"\\f1d1"', False),
        ),
    ),
    (
        '.fa-git-square',
        (
            ('content', '"\\f1d2"', False),
        ),
    ),
    (
        '.fa-git',
        (
            ('content', '"\\f1d3"', False),
        ),
    ),
    (
        '.fa-y-combinator-square',
        (
            ('content', '"\\f1d4"', False),
        ),
    ),
    (
        '.fa-yc-square',
        (
            ('content', '"\\f1d4"', False),
        ),
    ),
    (
        '.fa-hacker-news',
        (
            ('content', '"\\f1d4"', False),
        ),
    ),
    (
        '.fa-tencent-weibo',
        (
            ('content', '"\\f1d5"', False),
        ),
    ),
    (
        '.fa-qq',
        (
            ('content', '"\\f1d6"', False),
        ),
    ),
    (
        '.fa-wechat',
        (
            ('content', '"\\f1d7"', False),
        ),
    ),
    (
        '.fa-weixin',
        (
            ('content', '"\\f1d7"', False),
        ),
    ),
    (
        '.fa-send',
        (
            ('content', '"\\f1d8"', False),
        ),
    ),
    (
        '.fa-paper-plane',
        (
            ('content', '"\\f1d8"', False),
        ),
    ),
    (
        '.fa-send-o',
        (
            ('content', '"\\f1d9"', False),
        ),
    ),
    (
        '.fa-paper-plane-o',
        (
            ('content', '"\\f1d9"', False),
        ),
    ),
    (
        '.fa-history',
        (
            ('content', '"\\f1da"', False),
        ),
    ),
    (
        '.fa-circle-thin',
        (
            ('content', '"\\f1db"', False),
        ),
    ),
    (
        '.fa-header',
        (
            ('content', '"\\f1dc"', False),
        ),
    ),
    (
        '.fa-paragraph',
        (
            ('content', '"\\f1dd"', False),
        ),
    ),
    (
        '.fa-sliders',
        (
            ('content', '"\\f1de"', False),
        ),
    ),
    (
        '.fa-share-alt',
        (
            ('content', '"\\f1e0"', False),
        ),
    ),
    (
        '.fa-share-alt-square',
        (
            ('content', '"\\f1e1"', False),
        ),
    ),
    (
        '.fa-bomb',
        (
            ('content', '"\\f1e2"', False),
        ),
    ),
    (
        '.fa-soccer-ball-o',
        (
            ('content', '"\\f1e3"', False),
        ),
    ),
    (
        '.fa-futbol-o',
        (
            ('content', '"\\f1e3"', False),
        ),
    ),
    (
        '.fa-tty',
        (
            ('content', '"\\f1e4"', False),
        ),
    ),
    (
        '.fa-binoculars',
        (
            ('content', '"\\f1e5"', False),
        ),
    ),
    (
        '.fa-plug',
        (
            ('content', '"\\f1e6"', False),
        ),
    ),
    (
        '.fa-slideshare',
        (
            ('content', '"\\f1e7"', False),
        ),
    ),
    (
        '.fa-twitch',
        (
            ('content', '"\\f1e8"', False),
        ),
    ),
    (
        '.fa-yelp',
        (
            ('content', '"\\f1e9"', False),
        ),
    ),
    (
        '.fa-newspaper-o',
        (
            ('content', '"\\f1ea"', False),
        ),
    ),
    (
        '.fa-wifi',
        (
            ('content', '"\\f1eb"', False),
        ),
    ),
    (
        '.fa-calculator',
        (
            ('content', '"\\f1ec"', False),
        ),
    ),
    (
        '.fa-paypal',
        (
            ('content', '"\\f1ed"', False),
        ),
    ),
    (
        '.fa-google-wallet',
        (
            ('content', '"\\f1ee"', False),
        ),
    ),
    (
        '.fa-cc-visa',
        (
            ('content', '"\\f1f0"', False),
        ),
    ),
    (
        '.fa-cc-mastercard',
        (
            ('content', '"\\f1f1"', False),
        ),
    ),
    (
        '.fa-cc-discover',
        (
            ('content', '"\\f1f2"', False),
        ),
    ),
    (
        '.fa-cc-amex',
        (
            ('content', '"\\f1f3"', False),
        ),
    ),
    (
        '.fa-cc-paypal',
        (
            ('content', '"\\f1f4"', False),
        ),
    ),
    (
        '.fa-cc-stripe',
        (
            ('content', '"\\f1f5"', False),
        ),
    ),
    (
        '.fa-bell-slash',
        (
            ('content', '"\\f1f6"', False),
        ),
    ),
    (
        '.fa-bell-slash-o',
        (
            ('content', '"\\f1f7"', False),
        ),
    ),
    (
        '.fa-trash',
        (
            ('content', '"\\f1f8"', False),
        ),
    ),
    (
        '.fa-copyright',
        (
            ('content', '"\\f1f9"', False),
        ),
    ),
    (
        '.fa-at',
        (
            ('content', '"\\f1fa"', False),
        ),
    ),
    (
        '.fa-eyedropper',
        (
            ('content', '"\\f1fb"', False),
        ),
    ),
    (
        '.fa-paint-brush',
        (
            ('content', '"\\f1fc"', False),
        ),
    ),
    (
        '.fa-birthday-cake',
        (
            ('content', '"\\f1fd"', False),
        ),
    ),
    (
        '.fa-area-chart',
        (
            ('content', '"\\f1fe"', False),
        ),
    ),
    (
        '.fa-pie-chart',
        (
            ('content', '"\\f200"', False),
        ),
    ),
    (
        '.fa-line-chart',
        (
            ('content', '"\\f201"', False),
        ),
    ),
    (
        '.fa-lastfm',
        (
            ('content', '"\\f202"', False),
        ),
    ),
    (
        '.fa-lastfm-square',
        (
            ('content', '"\\f203"', False),
        ),
    ),
    (
        '.fa-toggle-off',
        (
            ('content', '"\\f204"', False),
        ),
    ),
    (
        '.fa-toggle-on',
        (
            ('content', '"\\f205"', False),
        ),
    ),
    (
        '.fa-bicycle',
        (
            ('content', '"\\f206"', False),
        ),
    ),
    (
        '.fa-bus',
        (
            ('content', '"\\f207"', False),
        ),
    ),
    (
        '.fa-ioxhost',
        (
            ('content', '"\\f208"', False),
        ),
    ),
    (
        '.fa-angellist',
        (
            ('content', '"\\f209"', False),
        ),
    ),
    (
        '.fa-cc',
        (
            ('content', '"\\f20a"', False),
        ),
    ),
    (
        '.fa-shekel',
        (
            ('content', '"\\f20b"', False),
        ),
    ),
    (
        '.fa-sheqel',
        (
            ('content', '"\\f20b"', False),
        ),
    ),
    (
        '.fa-ils',
        (
            ('content', '"\\f20b"', False),
        ),
    ),
    (
        '.fa-meanpath',
        (
            ('content', '"\\f20c"', False),
        ),
    ),
    (
        '.fa-buysellads',
        (
            ('content', '"\\f20d"', False),
        ),
    ),
    (
        '.fa-connectdevelop',
        (
            ('content', '"\\f20e"', False),
        ),
    ),
    (
        '.fa-dashcube',
        (
            ('content', '"\\f210"', False),
        ),
    ),
    (
        '.fa-forumbee',
        (
            ('content', '"\\f211"', False),
        ),
    ),
    (
        '.fa-leanpub',
        (
            ('content', '"\\f212"', False),
        ),
    ),
    (
        '.fa-sellsy',
        (
            ('content', '"\\f213"', False),
        ),
    ),
    (
        '.fa-shirtsinbulk',
        (
            ('content', '"\\f214"', False),
        ),
    ),
    (
        '.fa-simplybuilt',
        (
            ('content', '"\\f215"', False),
        ),
    ),
    (
        '.fa-skyatlas',
        (
            ('content', '"\\f216"', False),
        ),
    ),
    (
        '.fa-cart-plus',
        (
            ('content', '"\\f217"', False),
        ),
    ),
    (
        '.fa-cart-arrow-down',
        (
            ('content', '"\\f218"', False),
        ),
    ),
    (
        '.fa-diamond',
        (
            ('content', '"\\f219"', False),
        ),
    ),
    (
        '.fa-ship',
        (
            ('content', '"\\f21a"', False),
        ),
    ),
    (
        '.fa-user-secret',
        (
            ('content', '"\\f21b"', False),
        ),
    ),
    (
        '.fa-motorcycle',
        (
            ('content', '"\\f21c"', False),
        ),
    ),
    (
        '.fa-street-view',
        (
            ('content', '"\\f21d"', False),
        ),
    ),
    (
        '.fa-heartbeat',
        (
            ('content', '"\\f21e"', False),
        ),
    ),
    (
        '.fa-venus',
        (
            ('content', '"\\f221"', False),
        ),
    ),
    (
        '.fa-mars',
        (
            ('content', '"\\f222"', False),
        ),
    ),
    (
        '.fa-mercury',
        (
            ('content', '"\\f223"', False),
        ),
    ),
    (
        '.fa-intersex',
        (
            ('content', '"\\f224"', False),
        ),
    ),
    (
        '.fa-transgender',
        (
            ('content', '"\\f224"', False),
        ),
    ),
    (
        '.fa-transgender-alt',
        (
            ('content', '"\\f225"', False),
        ),
    ),
    (
        '.fa-venus-double',
        (
            ('content', '"\\f226"', False),
        ),
    ),
    (
        '.fa-mars-double',
        (
            ('content', '"\\f227"', False),
        ),
    ),
    (
        '.fa-venus-mars',
        (
            ('content', '"\\f228"', False),
        ),
    ),
    (
        '.fa-mars-stroke',
        (
            ('content', '"\\f229"', False),
        ),
    ),
    (
        '.fa-mars-stroke-v',
        (
            ('content', '"\\f22a"', False),
        ),
    ),
    (
        '.fa-mars-stroke-h',
        (
            ('content', '"\\f22b"', False),
        ),
    ),
    (
        '.fa-neuter',
        (
            ('content', '"\\f22c"', False),
        ),
    ),
    (
        '.fa-genderless',
        (
            ('content', '"\\f22d"', False),
        ),
    ),
    (
        '.fa-facebook-official',
        (
            ('content', '"\\f230"', False),
        ),
    ),
    (
        '.fa-pinterest-p',
        (
            ('content', '"\\f231"', False),
        ),
    ),
    (
        '.fa-whatsapp',
        (
            ('content', '"\\f232"', False),
        ),
    ),
    (
        '.fa-server',
        (
            ('content', '"\\f233"', False),
        ),
    ),
    (
        '.fa-user-plus',
        (
            ('content', '"\\f234"', False),
        ),
    ),
    (
        '.fa-user-times',
        (
            ('content', '"\\f235"', False),
        ),
    ),
    (
        '.fa-hotel',
        (
            ('content', '"\\f236"', False),
        ),
    ),
    (
        '.fa-bed',
        (
            ('content', '"\\f236"', False),
        ),
    ),
    (
        '.fa-viacoin',
        (
            ('content', '"\\f237"', False),
        ),
    ),
    (
        '.fa-train',
        (
            ('content', '"\\f238"', False),
        ),
    ),
    (
        '.fa-subway',
        (
            ('content', '"\\f239"', False),
        ),
    ),
    (
        '.fa-medium',
        (
            ('content', '"\\f23a"', False),
        ),
    ),
    (
        '.fa-yc',
        (
            ('content', '"\\f23b"', False),
        ),
    ),
    (
        '.fa-y-combinator',
        (
            ('content', '"\\f23b"', False),
        ),
    ),
    (
        '.fa-optin-monster',
        (
            ('content', '"\\f23c"', False),
        ),
    ),
    (
        '.fa-opencart',
        (
            ('content', '"\\f23d"', False),
        ),
    ),
    (
        '.fa-expeditedssl',
        (
            ('content', '"\\f23e"', False),
        ),
    ),
    (
        '.fa-battery-4',
        (
            ('content', '"\\f240"', False),
        ),
    ),
    (
        '.fa-battery',
        (
            ('content', '"\\f240"', False),
        ),
    ),
    (
        '.fa-battery-full',
        (
            ('content', '"\\f240"', False),
        ),
    ),
    (
        '.fa-battery-3',
        (
            ('content', '"\\f241"', False),
        ),
    ),
    (
        '.fa-battery-three-quarters',
        (
            ('content', '"\\f241"', False),
        ),
    ),
    (
        '.fa-battery-2',
        (
            ('content', '"\\f242"', False),
        ),
    ),
    (
        '.fa-battery-half',
        (
            ('content', '"\\f242"', False),
        ),
    ),
    (
        '.fa-battery-1',
        (
            ('content', '"\\f243"', False),
        ),
    ),
    (
        '.fa-battery-quarter',
        (
            ('content', '"\\f243"', False),
        ),
    ),
    (
        '.fa-battery-0',
        (
            ('content', '"\\f244"', False),
        ),
    ),
    (
        '.fa-battery-empty',
        (
            ('content', '"\\f244"', False),
        ),
    ),
    (
        '.fa-mouse-pointer',
        (
            ('content', '"\\f245"', False),
        ),
    ),
    (
        '.fa-i-cursor',
        (
            ('content', '"\\f246"', False),
        ),
    ),
    (
        '.fa-object-group',
        (
            ('content', '"\\f247"', False),
        ),
    ),
    (
        '.fa-object-ungroup',
        (
            ('content', '"\\f248"', False),
        ),
    ),
    (
        '.fa-sticky-note',
        (
            ('content', '"\\f249"', False),
        ),
    ),
    (
        '.fa-sticky-note-o',
        (
            ('content', '"\\f24a"', False),
        ),
    ),
    (
        '.fa-cc-jcb',
        (
            ('content', '"\\f24b"', False),
        ),
    ),
    (
        '.fa-cc-diners-club',
        (
            ('content', '"\\f24c"', False),
        ),
    ),
    (
        '.fa-clone',
        (
            ('content', '"\\f24d"', False),
        ),
    ),
    (
        '.fa-balance-scale',
        (
            ('content', '"\\f24e"', False),
        ),
    ),
    (
        '.fa-hourglass-o',
        (
            ('content', '"\\f250"', False),
        ),
    ),
    (
        '.fa-hourglass-1',
        (
            ('content', '"\\f251"', False),
        ),
    ),
    (
        '.fa-hourglass-start',
        (
            ('content', '"\\f251"', False),
        ),
    ),
    (
        '.fa-hourglass-2',
        (
            ('content', '"\\f252"', False),
        ),
    ),
    (
        '.fa-hourglass-half',
        (
            ('content', '"\\f252"', False),
        ),
    ),
    (
        '.fa-hourglass-3',
        (
            ('content', '"\\f253"', False),
        ),
    ),
    (
        '.fa-hourglass-end',
        (
            ('content', '"\\f253"', False),
        ),
    ),
    (
        '.fa-hourglass',
        (
            ('content', '"\\f254"', False),
        ),
    ),
    (
        '.fa-hand-grab-o',
        (
            ('content', '"\\f255"', False),
        ),
    ),
    (
        '.fa-hand-rock-o',
        (
            ('content', '"\\f255"', False),
        ),
    ),
    (
        '.fa-hand-stop-o',
        (
            ('content', '"\\f256"', False),
        ),
    ),
    (
        '.fa-hand-paper-o',
        (
            ('content', '"\\f256"', False),
        ),
    ),
    (
        '.fa-hand-scissors-o',
        (
            ('content', '"\\f257"', False),
        ),
    ),
    (
        '.fa-hand-lizard-o',
        (
            ('content', '"\\f258"', False),
        ),
    ),
    (
        '.fa-hand-spock-o',
        (
            ('content', '"\\f259"', False),
        ),
    ),
    (
        '.fa-hand-pointer-o',
        (
            ('content', '"\\f25a"', False),
        ),
    ),
    (
        '.fa-hand-peace-o',
        (
            ('content', '"\\f25b"', False),
        ),
    ),
    (
        '.fa-trademark',
        (
            ('content', '"\\f25c"', False),
        ),
    ),
    (
        '.fa-registered',
        (
            ('content', '"\\f25d"', False),
        ),
    ),
    (
        '.fa-creative-commons',
        (
            ('content', '"\\f25e"', False),
        ),
    ),
    (
        '.fa-gg',
        (
            ('content', '"\\f260"', False),
        ),
    ),
    (
        '.fa-gg-circle',
        (
            ('content', '"\\f261"', False),
        ),
    ),
    (
        '.fa-tripadvisor',
        (
            ('content', '"\\f262"', False),
        ),
    ),
    (
        '.fa-odnoklassniki',
        (
            ('content', '"\\f263"', False),
        ),
    ),
    (
        '.fa-odnoklassniki-square',
        (
            ('content', '"\\f264"', False),
        ),
    ),
    (
        '.fa-get-pocket',
        (
            ('content', '"\\f265"', False),
        ),
    ),
    (
        '.fa-wikipedia-w',
        (
            ('content', '"\\f266"', False),
        ),
    ),
    (
        '.fa-safari',
        (
            ('content', '"\\f267"', False),
        ),
    ),
    (
        '.fa-chrome',
        (
            ('content', '"\\f268"', False),
        ),
    ),
    (
        '.fa-firefox',
        (
            ('content', '"\\f269"', False),
        ),
    ),
    (
        '.fa-opera',
        (
            ('content', '"\\f26a"', False),
        ),
    ),
    (
        '.fa-internet-explorer',
        (
            ('content', '"\\f26b"', False),
        ),
    ),
    (
        '.fa-tv',
        (
            ('content', '"\\f26c"', False),
        ),
    ),
    (
        '.fa-television',
        (
            ('content', '"\\f26c"', False),
        ),
    ),
    (
        '.fa-contao',
        (
            ('content', '"\\f26d"', False),
        ),
    ),
    (
        '.fa-500px',
        (
            ('content', '"\\f26e"', False),
        ),
    ),
    (
        '.fa-amazon',
        (
            ('content', '"\\f270"', False),
        ),
    ),
    (
        '.fa-calendar-plus-o',
        (
            ('content', '"\\f271"', False),
        ),
    ),
    (
        '.fa-calendar-minus-o',
        (
            ('content', '"\\f272"', False),
        ),
    ),
    (
        '.fa-calendar-times-o',
        (
            ('content', '"\\f273"', False),
        ),
    ),
    (
        '.fa-calendar-check-o',
        (
            ('content', '"\\f274"', False),
        ),
    ),
    (
        '.fa-industry',
        (
            ('content', '"\\f275"', False),
        ),
    ),
    (
        '.fa-map-pin',
        (
            ('content', '"\\f276"', False),
        ),
    ),
    (
        '.fa-map-signs',
        (
            ('content', '"\\f277"', False),
        ),
    ),
    (
        '.fa-map-o',
        (
            ('content', '"\\f278"', False),
        ),
    ),
    (
        '.fa-map',
        (
            ('content', '"\\f279"', False),
        ),
    ),
    (
        '.fa-commenting',
        (
            ('content', '"\\f27a"', False),
        ),
    ),
    (
        '.fa-commenting-o',
        (
            ('content', '"\\f27b"', False),
        ),
    ),
    (
        '.fa-houzz',
        (
            ('content', '"\\f27c"', False),
        ),
    ),
    (
        '.fa-vimeo',
        (
            ('content', '"\\f27d"', False),
        ),
    ),
    (
        '.fa-black-tie',
        (
            ('content', '"\\f27e"', False),
        ),
    ),
    (
        '.fa-fonticons',
        (
            ('content', '"\\f280"', False),
        ),
    ),
    (
        '.fa-reddit-alien',
        (
            ('content', '"\\f281"', False),
        ),
    ),
    (
        '.fa-edge',
        (
            ('content', '"\\f282"', False),
        ),
    ),
    (
        '.fa-credit-card-alt',
        (
            ('content', '"\\f283"', False),
        ),
    ),
    (
        '.fa-codiepie',
        (
            ('content', '"\\f284"', False),
        ),
    ),
    (
        '.fa-modx',
        (
            ('content', '"\\f285"', False),
        ),
    ),
    (
        '.fa-fort-awesome',
        (
            ('content', '"\\f286"', False),
        ),
    ),
    (
        '.fa-usb',
        (
            ('content', '"\\f287"', False),
        ),
    ),
    (
        '.fa-product-hunt',
        (
            ('content', '"\\f288"', False),
        ),
    ),
    (
        '.fa-mixcloud',
        (
            ('content', '"\\f289"', False),
        ),
    ),
    (
        '.fa-scribd',
        (
            ('content', '"\\f28a"', False),
        ),
    ),
    (
        '.fa-pause-circle',
        (
            ('content', '"\\f28b"', False),
        ),
    ),
    (
        '.fa-pause-circle-o',
        (
            ('content', '"\\f28c"', False),
        ),
    ),
    (
        '.fa-stop-circle',
        (
            ('content', '"\\f28d"', False),
        ),
    ),
    (
        '.fa-stop-circle-o',
        (
            ('content', '"\\f28e"', False),
        ),
    ),
    (
        '.fa-shopping-bag',
        (
            ('content', '"\\f290"', False),
        ),
    ),
    (
        '.fa-shopping-basket',
        (
            ('content', '"\\f291"', False),
        ),
    ),
    (
        '.fa-hashtag',
        (
            ('content', '"\\f292"', False),
        ),
    ),
    (
        '.fa-bluetooth',
        (
            ('content', '"\\f293"', False),
        ),
    ),
    (
        '.fa-bluetooth-b',
        (
            ('content', '"\\f294"', False),
        ),
    ),
    (
        '.fa-percent',
        (
            ('content', '"\\f295"', False),
        ),
    ),
    (
        '.fa-gitlab',
        (
            ('content', '"\\f296"', False),
        ),
    ),
    (
        '.fa-wpbeginner',
        (
            ('content', '"\\f297"', False),
        ),
    ),
    (
        '.fa-wpforms',
        (
            ('content', '"\\f298"', False),
        ),
    ),
    (
        '.fa-envira',
        (
            ('content', '"\\f299"', False),
        ),
    ),
    (
        '.fa-universal-access',
        (
            ('content', '"\\f29a"', False),
        ),
    ),
    (
        '.fa-wheelchair-alt',
        (
            ('content', '"\\f29b"', False),
        ),
    ),
    (
        '.fa-question-circle-o',
        (
            ('content', '"\\f29c"', False),
        ),
    ),
    (
        '.fa-blind',
        (
            ('content', '"\\f29d"', False),
        ),
    ),
    (
        '.fa-audio-description',
        (
            ('content', '"\\f29e"', False),
        ),
    ),
    (
        '.fa-volume-control-phone',
        (
            ('content', '"\\f2a0"', False),
        ),
    ),
    (
        '.fa-braille',
        (
            ('content', '"\\f2a1"', False),
        ),
    ),
    (
        '.fa-assistive-listening-systems',
        (
            ('content', '"\\f2a2"', False),
        ),
    ),
    (
        '.fa-asl-interpreting',
        (
            ('content', '"\\f2a3"', False),
        ),
    ),
    (
        '.fa-american-sign-language-interpreting',
        (
            ('content', '"\\f2a3"', False),
        ),
    ),
    (
        '.fa-deafness',
        (
            ('content', '"\\f2a4"', False),
        ),
    ),
    (
        '.fa-hard-of-hearing',
        (
            ('content', '"\\f2a4"', False),
        ),
    ),
    (
        '.fa-deaf',
        (
            ('content', '"\\f2a4"', False),
        ),
    ),
    (
        '.fa-glide',
        (
            ('content', '"\\f2a5"', False),
        ),
    ),
    (
        '.fa-glide-g',
        (
            ('content', '"\\f2a6"', False),
        ),
    ),
    (
        '.fa-signing',
        (
            ('content', '"\\f2a7"', False),
        ),
    ),
    (
        '.fa-sign-language',
        (
            ('content', '"\\f2a7"', False),
        ),
    ),
    (
        '.fa-low-vision',
        (
            ('content', '"\\f2a8"', False),
        ),
    ),
    (
        '.fa-viadeo',
        (
            ('content', '"\\f2a9"', False),
        ),
    ),
    (
        '.fa-viadeo-square',
        (
            ('content', '"\\f2aa"', False),
        ),
    ),
    (
        '.fa-snapchat',
        (
            ('content', '"\\f2ab"', False),
        ),
    ),
    (
        '.fa-snapchat-ghost',
        (
            ('content', '"\\f2ac"', False),
        ),
    ),
    (
        '.fa-snapchat-square',
        (
            ('content', '"\\f2ad"', False),
        ),
    ),
    (
        '.fa-pied-piper',
        (
            ('content', '"\\f2ae"', False),
        ),
    ),
    (
        '.fa-first-order',
        (
            ('content', '"\\f2b0"', False),
        ),
    ),
    (
        '.fa-yoast',
        (
            ('content', '"\\f2b1"', False),
        ),
    ),
    (
        '.fa-themeisle',
        (
            ('content', '"\\f2b2"', False),
        ),
    ),
    (
        '.fa-google-plus-circle',
        (
            ('content', '"\\f2b3"', False),
        ),
    ),
    (
        '.fa-google-plus-official',
        (
            ('content', '"\\f2b3"', False),
        ),
    ),
    (
        '.fa-fa',
        (
            ('content', '"\\f2b4"', False),
        ),
    ),
    (
        '.fa-font-awesome',
        (
            ('content', '"\\f2b4"', False),
        ),
    ),
    (
        '.fa-handshake-o',
        (
            ('content', '"\\f2b5"', False),
        ),
    ),
    (
        '.fa-envelope-open',
        (
            ('content', '"\\f2b6"', False),
        ),
    ),
    (
        '.fa-envelope-open-o',
        (
            ('content', '"\\f2b7"', False),
        ),
    ),
    (
        '.fa-linode',
        (
            ('content', '"\\f2b8"', False),
        ),
    ),
    (
        '.fa-address-book',
        (
            ('content', '"\\f2b9"', False),
        ),
    ),
    (
        '.fa-address-book-o',
        (
            ('content', '"\\f2ba"', False),
        ),
    ),
    (
        '.fa-vcard',
        (
            ('content', '"\\f2bb"', False),
        ),
    ),
    (
        '.fa-address-card',
        (
            ('content', '"\\f2bb"', False),
        ),
    ),
    (
        '.fa-vcard-o',
        (
            ('content', '"\\f2bc"', False),
        ),
    ),
    (
        '.fa-address-card-o',
        (
            ('content', '"\\f2bc"', False),
        ),
    ),
    (
        '.fa-user-circle',
        (
            ('content', '"\\f2bd"', False),
        ),
    ),
    (
        '.fa-user-circle-o',
        (
            ('content', '"\\f2be"', False),
        ),
    ),
    (
        '.fa-user-o',
        (
            ('content', '"\\f2c0"', False),
        ),
    ),
    (
        '.fa-id-badge',
        (
            ('content', '"\\f2c1"', False),
        ),
    ),
    (
        '.fa-drivers-license',
        (
            ('content', '"\\f2c2"', False),
        ),
    ),
    (
        '.fa-id-card',
        (
            ('content', '"\\f2c2"', False),
        ),
    ),
    (
        '.fa-drivers-license-o',
        (
            ('content', '"\\f2c3"', False),
        ),
    ),
    (
        '.fa-id-card-o',
        (
            ('content', '"\\f2c3"', False),
        ),
    ),
    (
        '.fa-quora',
        (
            ('content', '"\\f2c4"', False),
        ),
    ),
    (
        '.fa-free-code-camp',
        (
            ('content', '"\\f2c5"', False),
        ),
    ),
    (
        '.fa-telegram',
        (
            ('content', '"\\f2c6"', False),
        ),
    ),
    (
        '.fa-thermometer-4',
        (
            ('content', '"\\f2c7"', False),
        ),
    ),
    (
        '.fa-thermometer',
        (
            ('content', '"\\f2c7"', False),
        ),
    ),
    (
        '.fa-thermometer-full',
        (
            ('content', '"\\f2c7"', False),
        ),
    ),
    (
        '.fa-thermometer-3',
        (
            ('content', '"\\f2c8"', False),
        ),
    ),
    (
        '.fa-thermometer-three-quarters',
        (
            ('content', '"\\f2c8"', False),
        ),
    ),
    (
        '.fa-thermometer-2',
        (
            ('content', '"\\f2c9"', False),
        ),
    ),
    (
        '.fa-thermometer-half',
        (
            ('content', '"\\f2c9"', False),
        ),
    ),
    (
        '.fa-thermometer-1',
        (
            ('content', '"\\f2ca"', False),
        ),
    ),
    (
        '.fa-thermometer-quarter',
        (
            ('content', '"\\f2ca"', False),
        ),
    ),
    (
        '.fa-thermometer-0',
        (
            ('content', '"\\f2cb"', False),
        ),
    ),
    (
        '.fa-thermometer-empty',
        (
            ('content', '"\\f2cb"', False),
        ),
    ),
    (
        '.fa-shower',
        (
            ('content', '"\\f2cc"', False),
        ),
    ),
    (
        '.fa-bathtub',
        (
            ('content', '"\\f2cd"', False),
        ),
    ),
    (
        '.fa-s15',
        (
            ('content', '"\\f2cd"', False),
        ),
    ),
    (
        '.fa-bath',
        (
            ('content', '"\\f2cd"', False),
        ),
    ),
    (
        '.fa-podcast',
        (
            ('content', '"\\f2ce"', False),
        ),
    ),
    (
        '.fa-window-maximize',
        (
            ('content', '"\\f2d0"', False),
        ),
    ),
    (
        '.fa-window-minimize',
        (
            ('content', '"\\f2d1"', False),
        ),
    ),
    (
        '.fa-window-restore',
        (
            ('content', '"\\f2d2"', False),
        ),
    ),
    (
        '.fa-times-rectangle',
        (
            ('content', '"\\f2d3"', False),
        ),
    ),
    (
        '.fa-window-close',
        (
            ('content', '"\\f2d3"', False),
        ),
    ),
    (
        '.fa-times-rectangle-o',
        (
            ('content', '"\\f2d4"', False),
        ),
    ),
    (
        '.fa-window-close-o',
        (
            ('content', '"\\f2d4"', False),
        ),
    ),
    (
        '.fa-bandcamp',
        (
            ('content', '"\\f2d5"', False),
        ),
    ),
    (
        '.fa-grav',
        (
            ('content', '"\\f2d6"', False),
        ),
    ),
    (
        '.fa-etsy',
        (
            ('content', '"\\f2d7"', False),
        ),
    ),
    (
        '.fa-imdb',
        (
            ('content', '"\\f2d8"', False),
        ),
    ),
    (
        '.fa-ravelry',
        (
            ('content', '"\\f2d9"', False),
        ),
    ),
    (
        '.fa-eercast',
        (
            ('content', '"\\f2da"', False),
        ),
    ),
    (
        '.fa-microchip',
        (
            ('content', '"\\f2db"', False),
        ),
    ),
    (
        '.fa-snowflake-o',
        (
            ('content', '"\\f2dc"', False),
        ),
    ),
    (
        '.fa-superpowers',
        (
            ('content', '"\\f2dd"', False),
        ),
    ),
    (
        '.fa-wpexplorer',
        (
            ('content', '"\\f2de"', False),
        ),
    ),
    (
        '.fa-meetup',
        (
            ('content', '"\\f2e0"', False),
        ),
    ),
    (
        '.fa.fa-tiktok',
        (
            ('content', "'\\e81b'", False),
        ),
    ),
    (
        '.fa-twitter.fa',
        (
            ('content', "'\\e81a'", False),
        ),
    ),
    (
        '.fa-twitter-square.fa',
        (
            ('content', "'\\e848'", False),
        ),
    ),
    (
        '.fa.fa-discord',
        (
            ('content', "'\\e811'", False),
        ),
    ),
    (
        '.fa.fa-google-play',
        (
            ('content', '"\\e81d"', False),
        ),
    ),
    (
        '.fa.fa-strava',
        (
            ('content', '"\\e80f"', False),
        ),
    ),
    (
        '.fa.fa-bluesky',
        (
            ('content', '"\\e81c"', False),
        ),
    ),
    (
        '.fa.fa-kickstarter',
        (
            ('content', '"\\e819"', False),
        ),
    ),
    (
        '.fa.fa-threads',
        (
            ('content', '"\\e818"', False),
        ),
    ),
    (
        '.oi-view-pivot',
        (
            ('content', "'\\e800'", False),
        ),
    ),
    (
        '.oi-text-break',
        (
            ('content', "'\\e801'", False),
        ),
    ),
    (
        '.oi-text-inline',
        (
            ('content', "'\\e802'", False),
        ),
    ),
    (
        '.oi-voip',
        (
            ('content', "'\\e803'", False),
        ),
    ),
    (
        '.oi-odoo',
        (
            ('content', "'\\e806'", False),
        ),
    ),
    (
        '.oi-search',
        (
            ('content', "'\\e808'", False),
        ),
    ),
    (
        '.oi-group',
        (
            ('content', "'\\e80a'", False),
        ),
    ),
    (
        '.oi-settings-adjust',
        (
            ('content', "'\\e80c'", False),
        ),
    ),
    (
        '.oi-apps',
        (
            ('content', "'\\e80d'", False),
        ),
    ),
    (
        '.oi-panel-right',
        (
            ('content', "'\\e810'", False),
        ),
    ),
    (
        '.oi-launch',
        (
            ('content', "'\\e812'", False),
        ),
    ),
    (
        '.oi-studio',
        (
            ('content', "'\\e813'", False),
        ),
    ),
    (
        '.oi-view-kanban',
        (
            ('content', "'\\e814'", False),
        ),
    ),
    (
        '.oi-text-wrap',
        (
            ('content', "'\\e815'", False),
        ),
    ),
    (
        '.oi-view-cohort',
        (
            ('content', "'\\e816'", False),
        ),
    ),
    (
        '.oi-view-list',
        (
            ('content', "'\\e817'", False),
        ),
    ),
    (
        '.oi-gif-picker',
        (
            ('content', "'\\e82e'", False),
        ),
    ),
    (
        '.oi-chevron-down',
        (
            ('content', "'\\e839'", False),
        ),
    ),
    (
        '.oi-chevron-left',
        (
            ('content', "'\\e83a'", False),
        ),
    ),
    (
        '.oi-chevron-right',
        (
            ('content', "'\\e83b'", False),
        ),
    ),
    (
        '.oi-chevron-up',
        (
            ('content', "'\\e83c'", False),
        ),
    ),
    (
        '.oi-arrows-h',
        (
            ('content', "'\\e83d'", False),
        ),
    ),
    (
        '.oi-arrows-v',
        (
            ('content', "'\\e83e'", False),
        ),
    ),
    (
        '.oi-arrow-down-left',
        (
            ('content', "'\\e83f'", False),
        ),
    ),
    (
        '.oi-arrow-down-right',
        (
            ('content', "'\\e840'", False),
        ),
    ),
    (
        '.oi-arrow-down',
        (
            ('content', "'\\e841'", False),
        ),
    ),
    (
        '.oi-arrow-left',
        (
            ('content', "'\\e842'", False),
        ),
    ),
    (
        '.oi-arrow-right',
        (
            ('content', "'\\e843'", False),
        ),
    ),
    (
        '.oi-arrow-up-left',
        (
            ('content', "'\\e844'", False),
        ),
    ),
    (
        '.oi-arrow-up-right',
        (
            ('content', "'\\e845'", False),
        ),
    ),
    (
        '.oi-arrow-up',
        (
            ('content', "'\\e846'", False),
        ),
    ),
    (
        '.oi-draggable',
        (
            ('content', "'\\e847'", False),
        ),
    ),
    (
        '.oi-view',
        (
            ('content', "'\\e861'", False),
        ),
    ),
    (
        '.oi-archive',
        (
            ('content', "'\\e862'", False),
        ),
    ),
    (
        '.oi-unarchive',
        (
            ('content', "'\\e863'", False),
        ),
    ),
    (
        '.oi-text-effect',
        (
            ('content', "'\\e827'", False),
        ),
    ),
    (
        '.oi-smile-add',
        (
            ('content', "'\\e84e'", False),
        ),
    ),
    (
        '.oi-close',
        (
            ('content', "'\\e852'", False),
        ),
    ),
    (
        '.oi-food-delivery',
        (
            ('content', "'\\e82a'", False),
        ),
    ),
    (
        '.oi-schedule-today',
        (
            ('content', "'\\e82c'", False),
        ),
    ),
    (
        '.oi-schedule-tomorrow',
        (
            ('content', "'\\e82d'", False),
        ),
    ),
    (
        '.oi-schedule-later',
        (
            ('content', "'\\e804'", False),
        ),
    ),
    (
        '.oi-activity',
        (
            ('content', "'\\e82f'", False),
        ),
    ),
    (
        '.oi-activity-plus',
        (
            ('content', "'\\e830'", False),
        ),
    ),
    (
        '.oi-numpad',
        (
            ('content', "'\\e833'", False),
        ),
    ),
    (
        '.oi-transfer',
        (
            ('content', "'\\e834'", False),
        ),
    ),
    (
        '.oi-suitcase',
        (
            ('content', "'\\e835'", False),
        ),
    ),
    (
        '.oi-suitcase-plus',
        (
            ('content', "'\\e832'", False),
        ),
    ),
    (
        '.oi-merge',
        (
            ('content', "'\\e836'", False),
        ),
    ),
    (
        '.oi-record',
        (
            ('content', "'\\e837'", False),
        ),
    ),
    (
        '.oi-backspace-o',
        (
            ('content', "'\\e838'", False),
        ),
    ),
    (
        '.oi-user',
        (
            ('content', "'\\e805'", False),
        ),
    ),
    (
        '.oi-user-plus',
        (
            ('content', "'\\e831'", False),
        ),
    ),
    (
        '.oi-users',
        (
            ('content', "'\\e807'", False),
        ),
    ),
    (
        '.oi-ellipsis-h',
        (
            ('content', "'\\e867'", False),
        ),
    ),
    (
        '.oi-ellipsis-v',
        (
            ('content', "'\\e868'", False),
        ),
    ),
    (
        '.oi-plus',
        (
            ('content', "'\\e809'", False),
        ),
    ),
    (
        '.oi-minus',
        (
            ('content', "'\\e80b'", False),
        ),
    ),
    (
        '.oi-star-plus',
        (
            ('content', "'\\e87c'", False),
        ),
    ),
    (
        '.oi-subtitle',
        (
            ('content', "'\\e80e'", False),
        ),
    ),
    (
        '.oi-threads',
        (
            ('content', "'\\e818'", False),
        ),
    ),
    (
        '.oi-kickstarter',
        (
            ('content', "'\\e819'", False),
        ),
    ),
    (
        '.oi-x',
        (
            ('content', "'\\e81a'", False),
        ),
    ),
    (
        '.oi-x-square',
        (
            ('content', "'\\e848'", False),
        ),
    ),
    (
        '.oi-tiktok',
        (
            ('content', "'\\e81b'", False),
        ),
    ),
    (
        '.oi-bluesky',
        (
            ('content', "'\\e81c'", False),
        ),
    ),
    (
        '.oi-google-play',
        (
            ('content', "'\\e81d'", False),
        ),
    ),
    (
        '.oi-strava',
        (
            ('content', "'\\e80f'", False),
        ),
    ),
    (
        '.oi-discord',
        (
            ('content', "'\\e811'", False),
        ),
    ),
    (
        'ul.o_checklist > li:not(.oe-nested)',
        (
            ('content', "''", False),
            ('position', 'absolute', False),
            ('left', '-20px', False),
            ('display', 'block', False),
            ('height', '14px', False),
            ('width', '14px', False),
            ('top', '1px', False),
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
        ),
    ),
    (
        '.o_table_boxed table:not(.o_ignore_layout_styling)',
        (
            ('content', "''", False),
            ('position', 'absolute', False),
            ('top', '0', False),
            ('left', '0', False),
            ('bottom', '0', False),
            ('right', '0', False),
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
        ),
    ),
    (
        '.o_table_boxed-rounded table:not(.o_ignore_layout_styling)',
        (
            ('content', "''", False),
            ('position', 'absolute', False),
            ('top', '0', False),
            ('left', '0', False),
            ('bottom', '0', False),
            ('right', '0', False),
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
        ),
    ),
    (
        'ul.o_checklist > li:not(.oe-nested)',
        (
            ('content', "''", False),
            ('position', 'absolute', False),
            ('left', '-20px', False),
            ('display', 'block', False),
            ('height', '13px', False),
            ('width', '13px', False),
            ('top', '4px', False),
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
        ),
    ),
    (
        'ul.o_checklist > li.o_checked',
        (
            ('content', '"✓"', False),
            ('display', 'flex', False),
            ('font-size', '13px', False),
            ('padding-left', '1px', False),
            ('padding-top', '1px', False),
        ),
    ),
    (
        'ol > li.o_indent',
        (
            ('content', 'none', False),
        ),
    ),
    (
        'ul > li.o_indent',
        (
            ('content', 'none', False),
        ),
    ),
    (
        '.o_we_search_prompt',
        (
            ('content', '""', False),
            ('position', 'absolute', False),
            ('top', '12px', False),
            ('left', '40px', False),
            ('bottom', 'auto', False),
            ('right', 'auto', False),
            ('width', '100px', False),
            ('height', '150px', False),
        ),
    ),
)


#: The same, after.
PSEUDO_AFTER_RULES = (
    (
        'blockquote',
        (
            ('content', '""', False),
            ('content', 'none', False),
        ),
    ),
    (
        'q',
        (
            ('content', '""', False),
            ('content', 'none', False),
        ),
    ),
    (
        '.dropdown-toggle',
        (
            ('display', 'inline-block', False),
            ('margin-left', '3.4px', False),
            ('vertical-align', '3.4px', False),
            ('content', '""', False),
            ('border-top-width', '4px', False),
            ('border-top-style', 'solid', False),
            ('border-right-width', '4px', False),
            ('border-right-style', 'solid', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '4px', False),
            ('border-left-style', 'solid', False),
        ),
    ),
    (
        '.dropup .dropdown-toggle',
        (
            ('display', 'inline-block', False),
            ('margin-left', '3.4px', False),
            ('vertical-align', '3.4px', False),
            ('content', '""', False),
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '4px', False),
            ('border-right-style', 'solid', False),
            ('border-bottom-width', '4px', False),
            ('border-bottom-style', 'solid', False),
            ('border-left-width', '4px', False),
            ('border-left-style', 'solid', False),
        ),
    ),
    (
        '.dropend .dropdown-toggle',
        (
            ('display', 'inline-block', False),
            ('margin-left', '3.4px', False),
            ('vertical-align', '3.4px', False),
            ('content', '""', False),
            ('border-top-width', '4px', False),
            ('border-top-style', 'solid', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '4px', False),
            ('border-bottom-style', 'solid', False),
            ('border-left-width', '4px', False),
            ('border-left-style', 'solid', False),
        ),
    ),
    (
        '.dropstart .dropdown-toggle',
        (
            ('display', 'inline-block', False),
            ('margin-left', '3.4px', False),
            ('vertical-align', '3.4px', False),
            ('content', '""', False),
        ),
    ),
    (
        '.accordion-button',
        (
            ('width', 'var(--accordion-btn-icon-width)', False),
            ('height', 'var(--accordion-btn-icon-width)', False),
            ('margin-left', 'auto', False),
            ('content', '""', False),
        ),
    ),
    (
        '.popover .popover-arrow',
        (
            ('position', 'absolute', False),
            ('display', 'block', False),
            ('content', '""', False),
            ('border-top-style', 'solid', False),
            ('border-right-style', 'solid', False),
            ('border-bottom-style', 'solid', False),
            ('border-left-style', 'solid', False),
            ('border-top-width', '0', False),
            ('border-right-width', '0', False),
            ('border-bottom-width', '0', False),
            ('border-left-width', '0', False),
        ),
    ),
    (
        '.carousel-inner',
        (
            ('display', 'block', False),
            ('clear', 'both', False),
            ('content', '""', False),
        ),
    ),
    (
        '.clearfix',
        (
            ('display', 'block', False),
            ('clear', 'both', False),
            ('content', '""', False),
        ),
    ),
    (
        '.stretched-link',
        (
            ('position', 'absolute', False),
            ('top', '0', False),
            ('right', '0', False),
            ('bottom', '0', False),
            ('left', '0', False),
            ('content', '""', False),
        ),
    ),
    (
        '.oe_clearfix',
        (
            ('content', '"."', False),
            ('display', 'block', False),
            ('clear', 'both', False),
            ('line-height', '0', False),
            ('height', '0', False),
        ),
    ),
    (
        '.oe_row',
        (
            ('content', '"."', False),
            ('display', 'block', False),
            ('clear', 'both', False),
            ('line-height', '0', False),
            ('height', '0', False),
        ),
    ),
    (
        '.oe_styling_v8 h4.oe_slogan',
        (
            ('margin-top', '0', False),
            ('margin-right', '20px', False),
            ('margin-bottom', '0', False),
            ('margin-left', '20px', False),
            ('content', '""', False),
            ('display', 'inline-block', False),
            ('width', '100px', False),
            ('height', '0px', False),
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('vertical-align', 'middle', False),
        ),
    ),
    (
        '.oe_quote .oe_q',
        (
            ('content', '\'"\'', False),
            ('font-weight', '900', False),
        ),
    ),
    (
        '.oe_quote q',
        (
            ('content', '\'"\'', False),
            ('font-weight', '900', False),
        ),
    ),
    (
        'ul.o_checklist > li.o_checked',
        (
            ('content', '"✓"', False),
            ('position', 'absolute', False),
            ('left', '-18px', False),
            ('top', '-1px', False),
        ),
    ),
)


FONT_FACE_RULES = (
    (
        'FontAwesome',
        (
            ('/web/static/src/libs/fontawesome/css/../fonts/fontawesome-webfont.woff2?v=4.7.0', 'woff2'),
            ('/web/static/src/libs/fontawesome/css/../fonts/fontawesome-webfont.woff?v=4.7.0', 'woff'),
        ),
        'normal',
        'normal',
    ),
    (
        'odoo_ui_icons',
        (
            ('/web/static/lib/odoo_ui_icons/fonts/odoo_ui_icons.woff2', 'woff2'),
            ('/web/static/lib/odoo_ui_icons/fonts/odoo_ui_icons.woff', 'woff'),
        ),
        'normal',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-Hai.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-Hai.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-Hai.ttf', 'truetype'),
        ),
        '100',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-Hai.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-Hai.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-Hai.ttf', 'truetype'),
        ),
        '100',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-Hai.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-Hai.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-Hai.ttf', 'truetype'),
        ),
        '100',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-Hai.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-Hai.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-Hai.ttf', 'truetype'),
        ),
        '100',
        'normal',
    ),
    (
        'Lato',
        (
            ('/web/static/fonts/./lato/Lato-Hai-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-Hai-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-Hai-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-Hai-webfont.svg#Lato', 'svg'),
        ),
        '100',
        'normal',
    ),
    (
        'Lato-Hai',
        (
            ('/web/static/fonts/./lato/Lato-Hai-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-Hai-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-Hai-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-Hai-webfont.svg#Roboto', 'svg'),
        ),
        'normal',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-HaiIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-HaiIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-HaiIta.ttf', 'truetype'),
        ),
        '100',
        'italic',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-HaiIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-HaiIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-HaiIta.ttf', 'truetype'),
        ),
        '100',
        'italic',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-HaiIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-HaiIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-HaiIta.ttf', 'truetype'),
        ),
        '100',
        'italic',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-HaiIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-HaiIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-HaiIta.ttf', 'truetype'),
        ),
        '100',
        'italic',
    ),
    (
        'Lato',
        (
            ('/web/static/fonts/./lato/Lato-HaiIta-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-HaiIta-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-HaiIta-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-HaiIta-webfont.svg#Lato', 'svg'),
        ),
        '100',
        'italic',
    ),
    (
        'Lato-HaiIta',
        (
            ('/web/static/fonts/./lato/Lato-HaiIta-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-HaiIta-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-HaiIta-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-HaiIta-webfont.svg#Roboto', 'svg'),
        ),
        'normal',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-Lig.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-Lig.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-Lig.ttf', 'truetype'),
        ),
        '300',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-Lig.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-Lig.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-Lig.ttf', 'truetype'),
        ),
        '300',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-Lig.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-Lig.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-Lig.ttf', 'truetype'),
        ),
        '300',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-Lig.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-Lig.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-Lig.ttf', 'truetype'),
        ),
        '300',
        'normal',
    ),
    (
        'Lato',
        (
            ('/web/static/fonts/./lato/Lato-Lig-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-Lig-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-Lig-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-Lig-webfont.svg#Lato', 'svg'),
        ),
        '300',
        'normal',
    ),
    (
        'Lato-Lig',
        (
            ('/web/static/fonts/./lato/Lato-Lig-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-Lig-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-Lig-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-Lig-webfont.svg#Roboto', 'svg'),
        ),
        'normal',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-LigIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-LigIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-LigIta.ttf', 'truetype'),
        ),
        '300',
        'italic',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-LigIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-LigIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-LigIta.ttf', 'truetype'),
        ),
        '300',
        'italic',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-LigIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-LigIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-LigIta.ttf', 'truetype'),
        ),
        '300',
        'italic',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-LigIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-LigIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-LigIta.ttf', 'truetype'),
        ),
        '300',
        'italic',
    ),
    (
        'Lato',
        (
            ('/web/static/fonts/./lato/Lato-LigIta-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-LigIta-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-LigIta-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-LigIta-webfont.svg#Lato', 'svg'),
        ),
        '300',
        'italic',
    ),
    (
        'Lato-LigIta',
        (
            ('/web/static/fonts/./lato/Lato-LigIta-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-LigIta-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-LigIta-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-LigIta-webfont.svg#Roboto', 'svg'),
        ),
        'normal',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-Reg.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-Reg.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-Reg.ttf', 'truetype'),
        ),
        '400',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-Reg.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-Reg.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-Reg.ttf', 'truetype'),
        ),
        '400',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-Reg.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-Reg.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-Reg.ttf', 'truetype'),
        ),
        '400',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-Reg.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-Reg.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-Reg.ttf', 'truetype'),
        ),
        '400',
        'normal',
    ),
    (
        'Lato',
        (
            ('/web/static/fonts/./lato/Lato-Reg-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-Reg-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-Reg-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-Reg-webfont.svg#Lato', 'svg'),
        ),
        '400',
        'normal',
    ),
    (
        'Lato-Reg',
        (
            ('/web/static/fonts/./lato/Lato-Reg-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-Reg-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-Reg-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-Reg-webfont.svg#Roboto', 'svg'),
        ),
        'normal',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-RegIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-RegIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-RegIta.ttf', 'truetype'),
        ),
        '400',
        'italic',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-RegIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-RegIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-RegIta.ttf', 'truetype'),
        ),
        '400',
        'italic',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-RegIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-RegIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-RegIta.ttf', 'truetype'),
        ),
        '400',
        'italic',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-RegIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-RegIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-RegIta.ttf', 'truetype'),
        ),
        '400',
        'italic',
    ),
    (
        'Lato',
        (
            ('/web/static/fonts/./lato/Lato-RegIta-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-RegIta-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-RegIta-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-RegIta-webfont.svg#Lato', 'svg'),
        ),
        '400',
        'italic',
    ),
    (
        'Lato-RegIta',
        (
            ('/web/static/fonts/./lato/Lato-RegIta-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-RegIta-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-RegIta-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-RegIta-webfont.svg#Roboto', 'svg'),
        ),
        'normal',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-Bol.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-Bol.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-Bol.ttf', 'truetype'),
        ),
        '700',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-Bol.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-Bol.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-Bol.ttf', 'truetype'),
        ),
        '700',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-Bol.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-Bol.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-Bol.ttf', 'truetype'),
        ),
        '700',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-Bol.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-Bol.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-Bol.ttf', 'truetype'),
        ),
        '700',
        'normal',
    ),
    (
        'Lato',
        (
            ('/web/static/fonts/./lato/Lato-Bol-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-Bol-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-Bol-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-Bol-webfont.svg#Lato', 'svg'),
        ),
        '700',
        'normal',
    ),
    (
        'Lato-Bol',
        (
            ('/web/static/fonts/./lato/Lato-Bol-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-Bol-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-Bol-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-Bol-webfont.svg#Roboto', 'svg'),
        ),
        'normal',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-BolIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-BolIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-BolIta.ttf', 'truetype'),
        ),
        '700',
        'italic',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-BolIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-BolIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-BolIta.ttf', 'truetype'),
        ),
        '700',
        'italic',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-BolIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-BolIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-BolIta.ttf', 'truetype'),
        ),
        '700',
        'italic',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-BolIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-BolIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-BolIta.ttf', 'truetype'),
        ),
        '700',
        'italic',
    ),
    (
        'Lato',
        (
            ('/web/static/fonts/./lato/Lato-BolIta-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-BolIta-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-BolIta-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-BolIta-webfont.svg#Lato', 'svg'),
        ),
        '700',
        'italic',
    ),
    (
        'Lato-BolIta',
        (
            ('/web/static/fonts/./lato/Lato-BolIta-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-BolIta-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-BolIta-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-BolIta-webfont.svg#Roboto', 'svg'),
        ),
        'normal',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-Bla.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-Bla.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-Bla.ttf', 'truetype'),
        ),
        '900',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-Bla.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-Bla.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-Bla.ttf', 'truetype'),
        ),
        '900',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-Bla.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-Bla.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-Bla.ttf', 'truetype'),
        ),
        '900',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-Bla.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-Bla.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-Bla.ttf', 'truetype'),
        ),
        '900',
        'normal',
    ),
    (
        'Lato',
        (
            ('/web/static/fonts/./lato/Lato-Bla-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-Bla-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-Bla-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-Bla-webfont.svg#Lato', 'svg'),
        ),
        '900',
        'normal',
    ),
    (
        'Lato-Bla',
        (
            ('/web/static/fonts/./lato/Lato-Bla-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-Bla-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-Bla-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-Bla-webfont.svg#Roboto', 'svg'),
        ),
        'normal',
        'normal',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-BlaIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-BlaIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSans-BlaIta.ttf', 'truetype'),
        ),
        '900',
        'italic',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-BlaIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-BlaIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansHebrew-BlaIta.ttf', 'truetype'),
        ),
        '900',
        'italic',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-BlaIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-BlaIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansArabic-BlaIta.ttf', 'truetype'),
        ),
        '900',
        'italic',
    ),
    (
        'Odoo Unicode Support Noto',
        (
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-BlaIta.woff2', 'woff2'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-BlaIta.woff', 'woff'),
            ('https://fonts.odoocdn.com/fonts/noto/NotoSansTelugu-BlaIta.ttf', 'truetype'),
        ),
        '900',
        'italic',
    ),
    (
        'Lato',
        (
            ('/web/static/fonts/./lato/Lato-BlaIta-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-BlaIta-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-BlaIta-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-BlaIta-webfont.svg#Lato', 'svg'),
        ),
        '900',
        'italic',
    ),
    (
        'Lato-BlaIta',
        (
            ('/web/static/fonts/./lato/Lato-BlaIta-webfont.eot?#iefix', 'embedded-opentype'),
            ('/web/static/fonts/./lato/Lato-BlaIta-webfont.woff', 'woff'),
            ('/web/static/fonts/./lato/Lato-BlaIta-webfont.ttf', 'truetype'),
            ('/web/static/fonts/./lato/Lato-BlaIta-webfont.svg#Roboto', 'svg'),
        ),
        'normal',
        'normal',
    ),
    (
        'Montserrat',
        (
            ('/web/static/fonts/./google/Montserrat/Montserrat-Regular.ttf', 'truetype'),
        ),
        '400',
        'normal',
    ),
    (
        'Open_Sans',
        (
            ('/web/static/fonts/./google/Open_Sans/Open_Sans-Regular.ttf', 'truetype'),
        ),
        '400',
        'normal',
    ),
    (
        'Oswald',
        (
            ('/web/static/fonts/./google/Oswald/Oswald-Regular.ttf', 'truetype'),
        ),
        '400',
        'normal',
    ),
    (
        'Raleway',
        (
            ('/web/static/fonts/./google/Raleway/Raleway-Regular.ttf', 'truetype'),
        ),
        '400',
        'normal',
    ),
    (
        'Roboto',
        (
            ('/web/static/fonts/./google/Roboto/Roboto-Regular.ttf', 'truetype'),
        ),
        '400',
        'normal',
    ),
    (
        'Tajawal',
        (
            ('/web/static/fonts/./google/Tajawal/Tajawal-Regular.ttf', 'truetype'),
        ),
        '400',
        'normal',
    ),
    (
        'Fira_Mono',
        (
            ('/web/static/fonts/./google/Fira_Mono/Fira_Mono-Regular.ttf', 'truetype'),
        ),
        '400',
        'normal',
    ),
)


TYPE_STYLE_RULES = (
    (
        '.o_report_reception .bg-dark-light h1, .o_colored_level .o_report_reception .bg-dark-light h1, .o_report_reception .bg-light-light h1, .o_colored_level .o_report_reception .bg-light-light h1, .o_report_reception .bg-danger-light h1, .o_colored_level .o_report_reception .bg-danger-light h1, .o_report_reception .bg-warning-light h1, .o_colored_level .o_report_reception .bg-warning-light h1, .o_report_reception .bg-info-light h1, .o_colored_level .o_report_reception .bg-info-light h1, .o_report_reception .bg-success-light h1, .o_colored_level .o_report_reception .bg-success-light h1, .o_report_reception .bg-secondary-light h1, .o_colored_level .o_report_reception .bg-secondary-light h1, .o_report_reception .bg-primary-light h1, .o_colored_level .o_report_reception .bg-primary-light h1, .o_cc5 h1, .o_colored_level .o_cc5 h1, .o_cc4 h1, .o_colored_level .o_cc4 h1, .o_cc3 h1, .o_colored_level .o_cc3 h1, .o_cc2 h1, .o_colored_level .o_cc2 h1, .o_cc1 h1, .o_colored_level .o_cc1 h1, .bg-o-color-5 h1, .o_colored_level .bg-o-color-5 h1, .bg-o-color-4 h1, .o_colored_level .bg-o-color-4 h1, .bg-o-color-3 h1, .o_colored_level .bg-o-color-3 h1, .bg-o-color-2 h1, .o_colored_level .bg-o-color-2 h1, .bg-o-color-1 h1, .o_colored_level .bg-o-color-1 h1, .o_report_reception .bg-dark-light .h1, .o_colored_level .o_report_reception .bg-dark-light .h1, .o_report_reception .bg-light-light .h1, .o_colored_level .o_report_reception .bg-light-light .h1, .o_report_reception .bg-danger-light .h1, .o_colored_level .o_report_reception .bg-danger-light .h1, .o_report_reception .bg-warning-light .h1, .o_colored_level .o_report_reception .bg-warning-light .h1, .o_report_reception .bg-info-light .h1, .o_colored_level .o_report_reception .bg-info-light .h1, .o_report_reception .bg-success-light .h1, .o_colored_level .o_report_reception .bg-success-light .h1, .o_report_reception .bg-secondary-light .h1, .o_colored_level .o_report_reception .bg-secondary-light .h1, .o_report_reception .bg-primary-light .h1, .o_colored_level .o_report_reception .bg-primary-light .h1, .o_cc5 .h1, .o_colored_level .o_cc5 .h1, .o_cc4 .h1, .o_colored_level .o_cc4 .h1, .o_cc3 .h1, .o_colored_level .o_cc3 .h1, .o_cc2 .h1, .o_colored_level .o_cc2 .h1, .o_cc1 .h1, .o_colored_level .o_cc1 .h1, .bg-o-color-5 .h1, .o_colored_level .bg-o-color-5 .h1, .bg-o-color-4 .h1, .bg-o-color-3 .h1, .bg-o-color-2 .h1, .bg-o-color-1 .h1, .o_report_reception .bg-dark-light h2, .o_colored_level .o_report_reception .bg-dark-light h2, .o_report_reception .bg-light-light h2, .o_colored_level .o_report_reception .bg-light-light h2, .o_report_reception .bg-danger-light h2, .o_colored_level .o_report_reception .bg-danger-light h2, .o_report_reception .bg-warning-light h2, .o_colored_level .o_report_reception .bg-warning-light h2, .o_report_reception .bg-info-light h2, .o_colored_level .o_report_reception .bg-info-light h2, .o_report_reception .bg-success-light h2, .o_colored_level .o_report_reception .bg-success-light h2, .o_report_reception .bg-secondary-light h2, .o_colored_level .o_report_reception .bg-secondary-light h2, .o_report_reception .bg-primary-light h2, .o_colored_level .o_report_reception .bg-primary-light h2, .o_cc5 h2, .o_colored_level .o_cc5 h2, .o_cc4 h2, .o_colored_level .o_cc4 h2, .o_cc3 h2, .o_colored_level .o_cc3 h2, .o_cc2 h2, .o_colored_level .o_cc2 h2, .o_cc1 h2, .o_colored_level .o_cc1 h2, .bg-o-color-5 h2, .o_colored_level .bg-o-color-5 h2, .bg-o-color-4 h2, .o_colored_level .bg-o-color-4 h2, .bg-o-color-3 h2, .o_colored_level .bg-o-color-3 h2, .bg-o-color-2 h2, .o_colored_level .bg-o-color-2 h2, .bg-o-color-1 h2, .o_colored_level .bg-o-color-1 h2, .o_report_reception .bg-dark-light .h2, .o_colored_level .o_report_reception .bg-dark-light .h2, .o_report_reception .bg-light-light .h2, .o_colored_level .o_report_reception .bg-light-light .h2, .o_report_reception .bg-danger-light .h2, .o_colored_level .o_report_reception .bg-danger-light .h2, .o_report_reception .bg-warning-light .h2, .o_colored_level .o_report_reception .bg-warning-light .h2, .o_report_reception .bg-info-light .h2, .o_colored_level .o_report_reception .bg-info-light .h2, .o_report_reception .bg-success-light .h2, .o_colored_level .o_report_reception .bg-success-light .h2, .o_report_reception .bg-secondary-light .h2, .o_colored_level .o_report_reception .bg-secondary-light .h2, .o_report_reception .bg-primary-light .h2, .o_colored_level .o_report_reception .bg-primary-light .h2, .o_cc5 .h2, .o_colored_level .o_cc5 .h2, .o_cc4 .h2, .o_colored_level .o_cc4 .h2, .o_cc3 .h2, .o_colored_level .o_cc3 .h2, .o_cc2 .h2, .o_colored_level .o_cc2 .h2, .o_cc1 .h2, .o_colored_level .o_cc1 .h2, .bg-o-color-5 .h2, .o_colored_level .bg-o-color-5 .h2, .bg-o-color-4 .h2, .bg-o-color-3 .h2, .bg-o-color-2 .h2, .bg-o-color-1 .h2, .o_report_reception .bg-dark-light h3, .o_colored_level .o_report_reception .bg-dark-light h3, .o_report_reception .bg-light-light h3, .o_colored_level .o_report_reception .bg-light-light h3, .o_report_reception .bg-danger-light h3, .o_colored_level .o_report_reception .bg-danger-light h3, .o_report_reception .bg-warning-light h3, .o_colored_level .o_report_reception .bg-warning-light h3, .o_report_reception .bg-info-light h3, .o_colored_level .o_report_reception .bg-info-light h3, .o_report_reception .bg-success-light h3, .o_colored_level .o_report_reception .bg-success-light h3, .o_report_reception .bg-secondary-light h3, .o_colored_level .o_report_reception .bg-secondary-light h3, .o_report_reception .bg-primary-light h3, .o_colored_level .o_report_reception .bg-primary-light h3, .o_cc5 h3, .o_colored_level .o_cc5 h3, .o_cc4 h3, .o_colored_level .o_cc4 h3, .o_cc3 h3, .o_colored_level .o_cc3 h3, .o_cc2 h3, .o_colored_level .o_cc2 h3, .o_cc1 h3, .o_colored_level .o_cc1 h3, .bg-o-color-5 h3, .o_colored_level .bg-o-color-5 h3, .bg-o-color-4 h3, .o_colored_level .bg-o-color-4 h3, .bg-o-color-3 h3, .o_colored_level .bg-o-color-3 h3, .bg-o-color-2 h3, .o_colored_level .bg-o-color-2 h3, .bg-o-color-1 h3, .o_colored_level .bg-o-color-1 h3, .o_report_reception .bg-dark-light .h3, .o_colored_level .o_report_reception .bg-dark-light .h3, .o_report_reception .bg-light-light .h3, .o_colored_level .o_report_reception .bg-light-light .h3, .o_report_reception .bg-danger-light .h3, .o_colored_level .o_report_reception .bg-danger-light .h3, .o_report_reception .bg-warning-light .h3, .o_colored_level .o_report_reception .bg-warning-light .h3, .o_report_reception .bg-info-light .h3, .o_colored_level .o_report_reception .bg-info-light .h3, .o_report_reception .bg-success-light .h3, .o_colored_level .o_report_reception .bg-success-light .h3, .o_report_reception .bg-secondary-light .h3, .o_colored_level .o_report_reception .bg-secondary-light .h3, .o_report_reception .bg-primary-light .h3, .o_colored_level .o_report_reception .bg-primary-light .h3, .o_cc5 .h3, .o_colored_level .o_cc5 .h3, .o_cc4 .h3, .o_colored_level .o_cc4 .h3, .o_cc3 .h3, .o_colored_level .o_cc3 .h3, .o_cc2 .h3, .o_colored_level .o_cc2 .h3, .o_cc1 .h3, .o_colored_level .o_cc1 .h3, .bg-o-color-5 .h3, .o_colored_level .bg-o-color-5 .h3, .bg-o-color-4 .h3, .bg-o-color-3 .h3, .bg-o-color-2 .h3, .bg-o-color-1 .h3, .o_report_reception .bg-dark-light h4, .o_colored_level .o_report_reception .bg-dark-light h4, .o_report_reception .bg-light-light h4, .o_colored_level .o_report_reception .bg-light-light h4, .o_report_reception .bg-danger-light h4, .o_colored_level .o_report_reception .bg-danger-light h4, .o_report_reception .bg-warning-light h4, .o_colored_level .o_report_reception .bg-warning-light h4, .o_report_reception .bg-info-light h4, .o_colored_level .o_report_reception .bg-info-light h4, .o_report_reception .bg-success-light h4, .o_colored_level .o_report_reception .bg-success-light h4, .o_report_reception .bg-secondary-light h4, .o_colored_level .o_report_reception .bg-secondary-light h4, .o_report_reception .bg-primary-light h4, .o_colored_level .o_report_reception .bg-primary-light h4, .o_cc5 h4, .o_colored_level .o_cc5 h4, .o_cc4 h4, .o_colored_level .o_cc4 h4, .o_cc3 h4, .o_colored_level .o_cc3 h4, .o_cc2 h4, .o_colored_level .o_cc2 h4, .o_cc1 h4, .o_colored_level .o_cc1 h4, .bg-o-color-5 h4, .o_colored_level .bg-o-color-5 h4, .bg-o-color-4 h4, .o_colored_level .bg-o-color-4 h4, .bg-o-color-3 h4, .o_colored_level .bg-o-color-3 h4, .bg-o-color-2 h4, .o_colored_level .bg-o-color-2 h4, .bg-o-color-1 h4, .o_colored_level .bg-o-color-1 h4, .o_report_reception .bg-dark-light .h4, .o_colored_level .o_report_reception .bg-dark-light .h4, .o_report_reception .bg-light-light .h4, .o_colored_level .o_report_reception .bg-light-light .h4, .o_report_reception .bg-danger-light .h4, .o_colored_level .o_report_reception .bg-danger-light .h4, .o_report_reception .bg-warning-light .h4, .o_colored_level .o_report_reception .bg-warning-light .h4, .o_report_reception .bg-info-light .h4, .o_colored_level .o_report_reception .bg-info-light .h4, .o_report_reception .bg-success-light .h4, .o_colored_level .o_report_reception .bg-success-light .h4, .o_report_reception .bg-secondary-light .h4, .o_colored_level .o_report_reception .bg-secondary-light .h4, .o_report_reception .bg-primary-light .h4, .o_colored_level .o_report_reception .bg-primary-light .h4, .o_cc5 .h4, .o_colored_level .o_cc5 .h4, .o_cc4 .h4, .o_colored_level .o_cc4 .h4, .o_cc3 .h4, .o_colored_level .o_cc3 .h4, .o_cc2 .h4, .o_colored_level .o_cc2 .h4, .o_cc1 .h4, .o_colored_level .o_cc1 .h4, .bg-o-color-5 .h4, .o_colored_level .bg-o-color-5 .h4, .bg-o-color-4 .h4, .bg-o-color-3 .h4, .bg-o-color-2 .h4, .bg-o-color-1 .h4, .o_report_reception .bg-dark-light h5, .o_colored_level .o_report_reception .bg-dark-light h5, .o_report_reception .bg-light-light h5, .o_colored_level .o_report_reception .bg-light-light h5, .o_report_reception .bg-danger-light h5, .o_colored_level .o_report_reception .bg-danger-light h5, .o_report_reception .bg-warning-light h5, .o_colored_level .o_report_reception .bg-warning-light h5, .o_report_reception .bg-info-light h5, .o_colored_level .o_report_reception .bg-info-light h5, .o_report_reception .bg-success-light h5, .o_colored_level .o_report_reception .bg-success-light h5, .o_report_reception .bg-secondary-light h5, .o_colored_level .o_report_reception .bg-secondary-light h5, .o_report_reception .bg-primary-light h5, .o_colored_level .o_report_reception .bg-primary-light h5, .o_cc5 h5, .o_colored_level .o_cc5 h5, .o_cc4 h5, .o_colored_level .o_cc4 h5, .o_cc3 h5, .o_colored_level .o_cc3 h5, .o_cc2 h5, .o_colored_level .o_cc2 h5, .o_cc1 h5, .o_colored_level .o_cc1 h5, .bg-o-color-5 h5, .o_colored_level .bg-o-color-5 h5, .bg-o-color-4 h5, .o_colored_level .bg-o-color-4 h5, .bg-o-color-3 h5, .o_colored_level .bg-o-color-3 h5, .bg-o-color-2 h5, .o_colored_level .bg-o-color-2 h5, .bg-o-color-1 h5, .o_colored_level .bg-o-color-1 h5, .o_report_reception .bg-dark-light .h5, .o_colored_level .o_report_reception .bg-dark-light .h5, .o_report_reception .bg-light-light .h5, .o_colored_level .o_report_reception .bg-light-light .h5, .o_report_reception .bg-danger-light .h5, .o_colored_level .o_report_reception .bg-danger-light .h5, .o_report_reception .bg-warning-light .h5, .o_colored_level .o_report_reception .bg-warning-light .h5, .o_report_reception .bg-info-light .h5, .o_colored_level .o_report_reception .bg-info-light .h5, .o_report_reception .bg-success-light .h5, .o_colored_level .o_report_reception .bg-success-light .h5, .o_report_reception .bg-secondary-light .h5, .o_colored_level .o_report_reception .bg-secondary-light .h5, .o_report_reception .bg-primary-light .h5, .o_colored_level .o_report_reception .bg-primary-light .h5, .o_cc5 .h5, .o_colored_level .o_cc5 .h5, .o_cc4 .h5, .o_colored_level .o_cc4 .h5, .o_cc3 .h5, .o_colored_level .o_cc3 .h5, .o_cc2 .h5, .o_colored_level .o_cc2 .h5, .o_cc1 .h5, .o_colored_level .o_cc1 .h5, .bg-o-color-5 .h5, .o_colored_level .bg-o-color-5 .h5, .bg-o-color-4 .h5, .bg-o-color-3 .h5, .bg-o-color-2 .h5, .bg-o-color-1 .h5, .o_report_reception .bg-dark-light h6, .o_colored_level .o_report_reception .bg-dark-light h6, .o_report_reception .bg-light-light h6, .o_colored_level .o_report_reception .bg-light-light h6, .o_report_reception .bg-danger-light h6, .o_colored_level .o_report_reception .bg-danger-light h6, .o_report_reception .bg-warning-light h6, .o_colored_level .o_report_reception .bg-warning-light h6, .o_report_reception .bg-info-light h6, .o_colored_level .o_report_reception .bg-info-light h6, .o_report_reception .bg-success-light h6, .o_colored_level .o_report_reception .bg-success-light h6, .o_report_reception .bg-secondary-light h6, .o_colored_level .o_report_reception .bg-secondary-light h6, .o_report_reception .bg-primary-light h6, .o_colored_level .o_report_reception .bg-primary-light h6, .o_cc5 h6, .o_colored_level .o_cc5 h6, .o_cc4 h6, .o_colored_level .o_cc4 h6, .o_cc3 h6, .o_colored_level .o_cc3 h6, .o_cc2 h6, .o_colored_level .o_cc2 h6, .o_cc1 h6, .o_colored_level .o_cc1 h6, .bg-o-color-5 h6, .o_colored_level .bg-o-color-5 h6, .bg-o-color-4 h6, .o_colored_level .bg-o-color-4 h6, .bg-o-color-3 h6, .o_colored_level .bg-o-color-3 h6, .bg-o-color-2 h6, .o_colored_level .bg-o-color-2 h6, .bg-o-color-1 h6, .o_colored_level .bg-o-color-1 h6, .o_report_reception .bg-dark-light .h6, .o_colored_level .o_report_reception .bg-dark-light .h6, .o_report_reception .bg-light-light .h6, .o_colored_level .o_report_reception .bg-light-light .h6, .o_report_reception .bg-danger-light .h6, .o_colored_level .o_report_reception .bg-danger-light .h6, .o_report_reception .bg-warning-light .h6, .o_colored_level .o_report_reception .bg-warning-light .h6, .o_report_reception .bg-info-light .h6, .o_colored_level .o_report_reception .bg-info-light .h6, .o_report_reception .bg-success-light .h6, .o_colored_level .o_report_reception .bg-success-light .h6, .o_report_reception .bg-secondary-light .h6, .o_colored_level .o_report_reception .bg-secondary-light .h6, .o_report_reception .bg-primary-light .h6, .o_colored_level .o_report_reception .bg-primary-light .h6, .o_cc5 .h6, .o_colored_level .o_cc5 .h6, .o_cc4 .h6, .o_colored_level .o_cc4 .h6, .o_cc3 .h6, .o_colored_level .o_cc3 .h6, .o_cc2 .h6, .o_colored_level .o_cc2 .h6, .o_cc1 .h6, .o_colored_level .o_cc1 .h6, .bg-o-color-5 .h6, .o_colored_level .bg-o-color-5 .h6, .bg-o-color-4 .h6, .bg-o-color-3 .h6, .bg-o-color-2 .h6, .bg-o-color-1 .h6',
        (
            ('color', 'inherit', False),
        ),
    ),
    (
        'hr',
        (
            ('color', 'inherit', False),
        ),
    ),
    (
        'pre code',
        (
            ('font-size', 'inherit', False),
            ('color', 'inherit', False),
        ),
    ),
    (
        'a > code',
        (
            ('color', 'inherit', False),
        ),
    ),
    (
        'kbd',
        (
            ('font-size', '0.8125rem', False),
            ('color', '#495057', False),
        ),
    ),
    (
        '.blockquote-footer',
        (
            ('font-size', '0.8125rem', False),
            ('color', '#6c757d', False),
        ),
    ),
    (
        '.form-control::placeholder',
        (
            ('color', '#bec5cc', False),
        ),
    ),
    (
        '.form-select:-moz-focusring',
        (
            ('color', 'transparent', False),
        ),
    ),
    (
        '.form-range::-webkit-slider-runnable-track',
        (
            ('color', 'transparent', False),
        ),
    ),
    (
        '.form-range::-moz-range-track',
        (
            ('color', 'transparent', False),
        ),
    ),
    (
        '.form-floating > .form-control::placeholder, .form-floating > .form-control-plaintext::placeholder',
        (
            ('color', 'transparent', False),
        ),
    ),
    (
        '.form-floating > :disabled ~ label, .form-floating > .form-control:disabled ~ label',
        (
            ('color', '#6c757d', False),
        ),
    ),
    (
        '.valid-tooltip',
        (
            ('font-size', '0.8125rem', False),
            ('color', '#fff', False),
        ),
    ),
    (
        '.invalid-tooltip',
        (
            ('font-size', '0.8125rem', False),
            ('color', '#fff', False),
        ),
    ),
    (
        '.alert-heading',
        (
            ('color', 'inherit', False),
        ),
    ),
    (
        '.carousel-control-prev, .carousel-control-next',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.carousel-caption',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.carousel-dark .carousel-caption',
        (
            ('color', '#000000', False),
        ),
    ),
    (
        '.text-bg-primary',
        (
            ('color', '#FFFFFF', True),
        ),
    ),
    (
        '.text-bg-secondary',
        (
            ('color', '#000000', True),
        ),
    ),
    (
        '.text-bg-success',
        (
            ('color', '#FFFFFF', True),
        ),
    ),
    (
        '.text-bg-info',
        (
            ('color', '#FFFFFF', True),
        ),
    ),
    (
        '.text-bg-warning',
        (
            ('color', '#000000', True),
        ),
    ),
    (
        '.text-bg-danger',
        (
            ('color', '#FFFFFF', True),
        ),
    ),
    (
        '.text-bg-light',
        (
            ('color', '#000000', True),
        ),
    ),
    (
        '.text-bg-dark',
        (
            ('color', '#FFFFFF', True),
        ),
    ),
    (
        '.openerp .oe_form .oe_styling_v8',
        (
            ('font-family', '"Open Sans", "Helvetica", Sans', False),
            ('color', '#646464', False),
            ('font-size', '16px', False),
        ),
    ),
    (
        '.openerp .oe_form .oe_styling_v8 a',
        (
            ('color', '#6D57E0', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_button, .oe_styling_v8 a.oe_button',
        (
            ('color', 'white', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_input.oe_valid',
        (
            ('color', '#0f610f', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_input.oe_invalid',
        (
            ('color', '#610F0F', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_slogan',
        (
            ('color', '#333333', False),
            ('font-family', '"Lato", "Open Sans", "Helvetica", Sans', False),
        ),
    ),
    (
        '.oe_quote .oe_q, .oe_quote q',
        (
            ('font-size', '20px', False),
            ('color', '#4e66e7', False),
        ),
    ),
    (
        '.oe_quote .oe_author',
        (
            ('font-size', '20px', False),
            ('color', '#8d7bac', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_pic_ctr > .oe_title',
        (
            ('font-size', '64px', False),
            ('color', 'white', False),
        ),
    ),
    (
        'div.oe_demo div.oe_demo_footer',
        (
            ('color', 'white', False),
            ('font-size', '14px', False),
        ),
    ),
    (
        '.fa-inverse',
        (
            ('color', '#ffffff', False),
        ),
    ),
    (
        '.text-primary',
        (
            ('color', '#71639e', True),
        ),
    ),
    (
        '.text-secondary',
        (
            ('color', '#dee2e6', True),
        ),
    ),
    (
        '.text-success',
        (
            ('color', '#008818', True),
        ),
    ),
    (
        '.text-info',
        (
            ('color', '#0180a5', True),
        ),
    ),
    (
        '.text-warning',
        (
            ('color', '#9a6b01', True),
        ),
    ),
    (
        '.text-danger',
        (
            ('color', '#d23f3a', True),
        ),
    ),
    (
        '.text-light',
        (
            ('color', '#f8f9fa', True),
        ),
    ),
    (
        '.text-dark',
        (
            ('color', '#212529', True),
        ),
    ),
    (
        '.text-100',
        (
            ('color', '#f8f9fa', True),
        ),
    ),
    (
        '.text-200',
        (
            ('color', '#e9ecef', True),
        ),
    ),
    (
        '.text-300',
        (
            ('color', '#dee2e6', True),
        ),
    ),
    (
        '.text-400',
        (
            ('color', '#ced4da', True),
        ),
    ),
    (
        '.text-500',
        (
            ('color', '#adb5bd', True),
        ),
    ),
    (
        '.text-600',
        (
            ('color', '#6c757d', True),
        ),
    ),
    (
        '.text-700',
        (
            ('color', '#495057', True),
        ),
    ),
    (
        '.text-800',
        (
            ('color', '#343a40', True),
        ),
    ),
    (
        '.text-900',
        (
            ('color', '#212529', True),
        ),
    ),
    (
        '.text-white-85',
        (
            ('color', 'rgba(255, 255, 255, 0.85)', True),
        ),
    ),
    (
        '.text-white-75',
        (
            ('color', 'rgba(255, 255, 255, 0.75)', True),
        ),
    ),
    (
        '.text-white-50',
        (
            ('color', 'rgba(255, 255, 255, 0.5)', True),
        ),
    ),
    (
        '.text-white-25',
        (
            ('color', 'rgba(255, 255, 255, 0.25)', True),
        ),
    ),
    (
        '.text-black-75',
        (
            ('color', 'rgba(0, 0, 0, 0.75)', True),
        ),
    ),
    (
        '.text-black-50',
        (
            ('color', 'rgba(0, 0, 0, 0.5)', True),
        ),
    ),
    (
        '.text-black-25',
        (
            ('color', 'rgba(0, 0, 0, 0.25)', True),
        ),
    ),
    (
        '.text-black-15',
        (
            ('color', 'rgba(0, 0, 0, 0.15)', True),
        ),
    ),
    (
        '.text-body',
        (
            ('color', '#212529', True),
        ),
    ),
    (
        '.text-muted',
        (
            ('color', '#6c757d', True),
        ),
    ),
    (
        '.table > :not(caption) > * > *',
        (
            ('color', '#212529', False),
        ),
    ),
    (
        'body',
        (
            ('color', '#212529', False),
            ('font-family', '"Lato"', False),
        ),
    ),
    (
        '.alert',
        (
            ('color', 'inherit', False),
        ),
    ),
    (
        '.alert-link',
        (
            ('color', 'inherit', False),
        ),
    ),
    (
        '.alert-primary',
        (
            ('color', '#2d283f', False),
        ),
    ),
    (
        '.alert-secondary',
        (
            ('color', '#595a5c', False),
        ),
    ),
    (
        '.alert-success',
        (
            ('color', '#10431c', False),
        ),
    ),
    (
        '.alert-info',
        (
            ('color', '#09414a', False),
        ),
    ),
    (
        '.alert-warning',
        (
            ('color', '#664500', False),
        ),
    ),
    (
        '.alert-danger',
        (
            ('color', '#58151c', False),
        ),
    ),
    (
        '.alert-light',
        (
            ('color', '#495057', False),
        ),
    ),
    (
        '.alert-dark',
        (
            ('color', '#495057', False),
        ),
    ),
    (
        '.btn-primary',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.btn-fill-primary',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.btn-secondary',
        (
            ('color', '#212529', False),
        ),
    ),
    (
        '.btn-fill-secondary',
        (
            ('color', '#212529', False),
        ),
    ),
    (
        '.btn-light',
        (
            ('color', '#212529', False),
        ),
    ),
    (
        '.btn-fill-light',
        (
            ('color', '#212529', False),
        ),
    ),
    (
        '.btn-outline-secondary',
        (
            ('color', '#212529', False),
        ),
    ),
    (
        '.btn-outline-primary',
        (
            ('color', '#71639e', False),
        ),
    ),
    (
        '.btn-success',
        (
            ('color', '#28a745', False),
        ),
    ),
    (
        '.btn-outline-success',
        (
            ('color', '#28a745', False),
        ),
    ),
    (
        '.btn-info',
        (
            ('color', '#17a2b8', False),
        ),
    ),
    (
        '.btn-outline-info',
        (
            ('color', '#17a2b8', False),
        ),
    ),
    (
        '.btn-warning',
        (
            ('color', '#ffac00', False),
        ),
    ),
    (
        '.btn-outline-warning',
        (
            ('color', '#ffac00', False),
        ),
    ),
    (
        '.btn-danger',
        (
            ('color', '#dc3545', False),
        ),
    ),
    (
        '.btn-outline-danger',
        (
            ('color', '#dc3545', False),
        ),
    ),
    (
        '.btn-outline-light',
        (
            ('color', '#f8f9fa', False),
        ),
    ),
    (
        '.btn-dark',
        (
            ('color', '#212529', False),
        ),
    ),
    (
        '.btn-outline-dark',
        (
            ('color', '#212529', False),
        ),
    ),
    (
        'pre',
        (
            ('color', '#212529', False),
        ),
    ),
    (
        '.o_stars .fa.fa-star',
        (
            ('color', 'gold', False),
        ),
    ),
    (
        '.o_nocontent_help',
        (
            ('color', '#212529', False),
            ('font-size', '115%', False),
        ),
    ),
    (
        '.o_nocontent_help > p:first-of-type',
        (
            ('color', '#000000', False),
            ('font-size', '125%', False),
        ),
    ),
    (
        '.bg-o-color-1',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.bg-o-color-1 .text-muted, .o_colored_level .bg-o-color-1 .text-muted',
        (
            ('color', 'rgba(255, 255, 255, 0.7)', True),
        ),
    ),
    (
        '.bg-o-color-2',
        (
            ('color', '#000000', False),
        ),
    ),
    (
        '.bg-o-color-2 .text-muted, .o_colored_level .bg-o-color-2 .text-muted',
        (
            ('color', 'rgba(0, 0, 0, 0.7)', True),
        ),
    ),
    (
        '.bg-o-color-3',
        (
            ('color', '#000000', False),
        ),
    ),
    (
        '.bg-o-color-3 .text-muted, .o_colored_level .bg-o-color-3 .text-muted',
        (
            ('color', 'rgba(0, 0, 0, 0.7)', True),
        ),
    ),
    (
        '.bg-o-color-4',
        (
            ('color', '#000000', False),
        ),
    ),
    (
        '.bg-o-color-4 .text-muted, .o_colored_level .bg-o-color-4 .text-muted',
        (
            ('color', 'rgba(0, 0, 0, 0.7)', True),
        ),
    ),
    (
        '.bg-o-color-5',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.bg-o-color-5 .text-muted, .o_colored_level .bg-o-color-5 .text-muted',
        (
            ('color', 'rgba(255, 255, 255, 0.7)', True),
        ),
    ),
    (
        '.o_cc .dropdown-menu .dropdown-item, .o_cc .dropdown-menu .dropdown-item h6, .o_cc .dropdown-menu .dropdown-item .h6, .o_colored_level .o_cc .dropdown-menu .dropdown-item, .o_colored_level .o_cc .dropdown-menu .dropdown-item h6',
        (
            ('color', '#212529', True),
        ),
    ),
    (
        '.o_cc .dropdown-menu .dropdown-item.disabled, .o_cc .dropdown-menu .dropdown-item.disabled h6, .o_cc .dropdown-menu .dropdown-item.disabled .h6, .o_cc .dropdown-menu .dropdown-item:disabled, .o_cc .dropdown-menu .dropdown-item:disabled h6, .o_cc .dropdown-menu .dropdown-item:disabled .h6, .o_colored_level .o_cc .dropdown-menu .dropdown-item.disabled, .o_colored_level .o_cc .dropdown-menu .dropdown-item.disabled h6, .o_colored_level .o_cc .dropdown-menu .dropdown-item:disabled, .o_colored_level .o_cc .dropdown-menu .dropdown-item:disabled h6',
        (
            ('color', 'rgba(73, 80, 87, 0.76)', True),
        ),
    ),
    (
        '.o_cc .dropdown-menu .dropdown-item .btn-link:disabled, .o_colored_level .o_cc .dropdown-menu .dropdown-item .btn-link:disabled',
        (
            ('color', '#6c757d', False),
        ),
    ),
    (
        '.o_cc .dropdown-menu .dropdown-item-text .text-muted a, .o_colored_level .o_cc .dropdown-menu .dropdown-item-text .text-muted a',
        (
            ('color', '#66598f', False),
        ),
    ),
    (
        '.o_cc1',
        (
            ('color', '#000000', False),
        ),
    ),
    (
        '.o_cc1 .text-muted, .o_colored_level .o_cc1 .text-muted',
        (
            ('color', 'rgba(0, 0, 0, 0.7)', True),
        ),
    ),
    (
        '.o_cc1 a:not(.btn), .o_cc1 .btn-link, .o_colored_level .o_cc1 a:not(.btn), .o_colored_level .o_cc1 .btn-link',
        (
            ('color', '#4f456f', False),
        ),
    ),
    (
        '.o_cc1 .nav-pills .nav-link.active, .o_cc1 .nav-pills .show > .nav-link, .o_colored_level .o_cc1 .nav-pills .nav-link.active, .o_colored_level .o_cc1 .nav-pills .show > .nav-link',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.o_cc1 a.list-group-item, .o_colored_level .o_cc1 a.list-group-item',
        (
            ('color', '#71639e', False),
        ),
    ),
    (
        '.o_cc1 a.list-group-item.active, .o_colored_level .o_cc1 a.list-group-item.active',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.o_cc2',
        (
            ('color', '#000000', False),
        ),
    ),
    (
        '.o_cc2 .text-muted, .o_colored_level .o_cc2 .text-muted',
        (
            ('color', 'rgba(0, 0, 0, 0.7)', True),
        ),
    ),
    (
        '.o_cc2 h1, .o_cc2 .h1, .o_cc2 h2, .o_cc2 .h2, .o_cc2 h3, .o_cc2 .h3, .o_cc2 h4, .o_cc2 .h4, .o_cc2 h5, .o_cc2 .h5, .o_cc2 h6, .o_cc2 .h6, .o_colored_level .o_cc2 h1, .o_colored_level .o_cc2 h2, .o_colored_level .o_cc2 h3, .o_colored_level .o_cc2 h4, .o_colored_level .o_cc2 h5, .o_colored_level .o_cc2 h6',
        (
            ('color', '#1B1319', False),
        ),
    ),
    (
        '.o_cc2 a:not(.btn), .o_cc2 .btn-link, .o_colored_level .o_cc2 a:not(.btn), .o_colored_level .o_cc2 .btn-link',
        (
            ('color', '#463d63', False),
        ),
    ),
    (
        '.o_cc2 .nav-pills .nav-link.active, .o_cc2 .nav-pills .show > .nav-link, .o_colored_level .o_cc2 .nav-pills .nav-link.active, .o_colored_level .o_cc2 .nav-pills .show > .nav-link',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.o_cc2 a.list-group-item, .o_colored_level .o_cc2 a.list-group-item',
        (
            ('color', '#71639e', False),
        ),
    ),
    (
        '.o_cc2 a.list-group-item.active, .o_colored_level .o_cc2 a.list-group-item.active',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.o_cc3',
        (
            ('color', '#000000', False),
        ),
    ),
    (
        '.o_cc3 .text-muted, .o_colored_level .o_cc3 .text-muted',
        (
            ('color', 'rgba(0, 0, 0, 0.7)', True),
        ),
    ),
    (
        '.o_cc3 a:not(.btn), .o_cc3 .btn-link, .o_colored_level .o_cc3 a:not(.btn), .o_colored_level .o_cc3 .btn-link',
        (
            ('color', '#393250', False),
        ),
    ),
    (
        '.o_cc3 .nav-pills .nav-link.active, .o_cc3 .nav-pills .show > .nav-link, .o_colored_level .o_cc3 .nav-pills .nav-link.active, .o_colored_level .o_cc3 .nav-pills .show > .nav-link',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.o_cc3 a.list-group-item, .o_colored_level .o_cc3 a.list-group-item',
        (
            ('color', '#71639e', False),
        ),
    ),
    (
        '.o_cc3 a.list-group-item.active, .o_colored_level .o_cc3 a.list-group-item.active',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.o_cc4',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.o_cc4 .text-muted, .o_colored_level .o_cc4 .text-muted',
        (
            ('color', 'rgba(255, 255, 255, 0.7)', True),
        ),
    ),
    (
        '.o_cc4 a:not(.btn), .o_cc4 .btn-link, .o_colored_level .o_cc4 a:not(.btn), .o_colored_level .o_cc4 .btn-link',
        (
            ('color', 'black', False),
        ),
    ),
    (
        '.o_cc4 .nav-pills .nav-link.active, .o_cc4 .nav-pills .show > .nav-link, .o_colored_level .o_cc4 .nav-pills .nav-link.active, .o_colored_level .o_cc4 .nav-pills .show > .nav-link',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.o_cc4 a.list-group-item, .o_colored_level .o_cc4 a.list-group-item',
        (
            ('color', '#1B1319', False),
        ),
    ),
    (
        '.o_cc4 a.list-group-item.active, .o_colored_level .o_cc4 a.list-group-item.active',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.o_cc5',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.o_cc5 .text-muted, .o_colored_level .o_cc5 .text-muted',
        (
            ('color', 'rgba(255, 255, 255, 0.7)', True),
        ),
    ),
    (
        '.o_cc5 h1, .o_cc5 .h1, .o_cc5 h2, .o_cc5 .h2, .o_cc5 h3, .o_cc5 .h3, .o_cc5 h4, .o_cc5 .h4, .o_cc5 h5, .o_cc5 .h5, .o_cc5 h6, .o_cc5 .h6, .o_colored_level .o_cc5 h1, .o_colored_level .o_cc5 h2, .o_colored_level .o_cc5 h3, .o_colored_level .o_cc5 h4, .o_colored_level .o_cc5 h5, .o_colored_level .o_cc5 h6',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.o_cc5 a:not(.btn), .o_cc5 .btn-link, .o_colored_level .o_cc5 a:not(.btn), .o_colored_level .o_cc5 .btn-link',
        (
            ('color', '#b9b2cf', False),
        ),
    ),
    (
        '.o_cc5 .nav-pills .nav-link.active, .o_cc5 .nav-pills .show > .nav-link, .o_colored_level .o_cc5 .nav-pills .nav-link.active, .o_colored_level .o_cc5 .nav-pills .show > .nav-link',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.o_cc5 a.list-group-item, .o_colored_level .o_cc5 a.list-group-item',
        (
            ('color', '#71639e', False),
        ),
    ),
    (
        '.o_cc5 a.list-group-item.active, .o_colored_level .o_cc5 a.list-group-item.active',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.text-gradient u:not(font[style*="-webkit-text-fill-color"] u), .text-gradient s:not(font[style*="-webkit-text-fill-color"] s)',
        (
            ('color', 'transparent', False),
        ),
    ),
    (
        'code.o_inline_code',
        (
            ('font-size', '85%', False),
            ('color', '#212529', False),
        ),
    ),
    (
        'font[class^="text-o-"] a, font[style*="color"] a',
        (
            ('color', 'inherit', True),
        ),
    ),
    (
        '.o_report_reception .o_priority.o_priority_star.fa-star',
        (
            ('color', 'gold', False),
        ),
    ),
    (
        '.o_report_reception .bg-primary-light',
        (
            ('color', '#000000', False),
        ),
    ),
    (
        '.o_report_reception .bg-primary-light .text-muted, .o_colored_level .o_report_reception .bg-primary-light .text-muted',
        (
            ('color', 'rgba(0, 0, 0, 0.7)', True),
        ),
    ),
    (
        '.o_report_reception .bg-secondary-light',
        (
            ('color', '#000000', False),
        ),
    ),
    (
        '.o_report_reception .bg-secondary-light .text-muted, .o_colored_level .o_report_reception .bg-secondary-light .text-muted',
        (
            ('color', 'rgba(0, 0, 0, 0.7)', True),
        ),
    ),
    (
        '.o_report_reception .bg-success-light',
        (
            ('color', '#000000', False),
        ),
    ),
    (
        '.o_report_reception .bg-success-light .text-muted, .o_colored_level .o_report_reception .bg-success-light .text-muted',
        (
            ('color', 'rgba(0, 0, 0, 0.7)', True),
        ),
    ),
    (
        '.o_report_reception .bg-info-light',
        (
            ('color', '#000000', False),
        ),
    ),
    (
        '.o_report_reception .bg-info-light .text-muted, .o_colored_level .o_report_reception .bg-info-light .text-muted',
        (
            ('color', 'rgba(0, 0, 0, 0.7)', True),
        ),
    ),
    (
        '.o_report_reception .bg-warning-light',
        (
            ('color', '#000000', False),
        ),
    ),
    (
        '.o_report_reception .bg-warning-light .text-muted, .o_colored_level .o_report_reception .bg-warning-light .text-muted',
        (
            ('color', 'rgba(0, 0, 0, 0.7)', True),
        ),
    ),
    (
        '.o_report_reception .bg-danger-light',
        (
            ('color', '#000000', False),
        ),
    ),
    (
        '.o_report_reception .bg-danger-light .text-muted, .o_colored_level .o_report_reception .bg-danger-light .text-muted',
        (
            ('color', 'rgba(0, 0, 0, 0.7)', True),
        ),
    ),
    (
        '.o_report_reception .bg-light-light',
        (
            ('color', '#000000', False),
        ),
    ),
    (
        '.o_report_reception .bg-light-light .text-muted, .o_colored_level .o_report_reception .bg-light-light .text-muted',
        (
            ('color', 'rgba(0, 0, 0, 0.7)', True),
        ),
    ),
    (
        '.o_report_reception .bg-dark-light',
        (
            ('color', '#FFFFFF', False),
        ),
    ),
    (
        '.o_report_reception .bg-dark-light .text-muted, .o_colored_level .o_report_reception .bg-dark-light .text-muted',
        (
            ('color', 'rgba(255, 255, 255, 0.7)', True),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_putaway > p',
        (
            ('color', 'black', False),
            ('font-size', '12px', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_location_header > a > div',
        (
            ('color', 'black', False),
        ),
    ),
    (
        'html, body, div, span, applet, object, iframe, h1, h2, h3, h4, h5, h6, p, blockquote, pre, a, abbr, acronym, address, big, cite, code, del, dfn, em, font, img, ins, kbd, q, s, samp, small, strike, strong, sub, sup, tt, var, b, i, center, dl, dt, dd, ol, ul, li, fieldset, form, label, legend, table, caption, tbody, tfoot, thead, tr, th, td, article, aside, audio, canvas, details, figcaption, figure, footer, header, hgroup, mark, menu, meter, nav, output, progress, section, summary, time, video',
        (
            ('font-size', '100%', False),
        ),
    ),
    (
        'h1, .h1',
        (
            ('font-size', '2.5rem', False),
        ),
    ),
    (
        'h2, .h2',
        (
            ('font-size', '2rem', False),
        ),
    ),
    (
        'h3, .h3',
        (
            ('font-size', '1.75rem', False),
        ),
    ),
    (
        'h4, .h4',
        (
            ('font-size', '1.5rem', False),
        ),
    ),
    (
        'h5, .h5',
        (
            ('font-size', '1.25rem', False),
        ),
    ),
    (
        'h6, .h6',
        (
            ('font-size', '1rem', False),
        ),
    ),
    (
        'small, .small',
        (
            ('font-size', '0.8125rem', False),
        ),
    ),
    (
        'sub, sup',
        (
            ('font-size', '0.75em', False),
        ),
    ),
    (
        'pre, code, kbd, samp',
        (
            ('font-size', '1em', False),
        ),
    ),
    (
        'pre',
        (
            ('font-size', '0.8125rem', False),
        ),
    ),
    (
        'code',
        (
            ('font-size', '0.8125rem', False),
        ),
    ),
    (
        'kbd kbd',
        (
            ('font-size', '1em', False),
        ),
    ),
    (
        'input, button, select, optgroup, textarea',
        (
            ('font-family', 'inherit', False),
            ('font-size', 'inherit', False),
        ),
    ),
    (
        'legend',
        (
            ('font-size', '1.5rem', False),
        ),
    ),
    (
        '::file-selector-button',
        (
            ('font-size', 'inherit', False),
            ('font-family', 'inherit', False),
        ),
    ),
    (
        '.lead',
        (
            ('font-size', '1.25rem', False),
        ),
    ),
    (
        '.display-1',
        (
            ('font-size', '5rem', False),
        ),
    ),
    (
        '.display-2',
        (
            ('font-size', '4.5rem', False),
        ),
    ),
    (
        '.display-3',
        (
            ('font-size', '4rem', False),
        ),
    ),
    (
        '.display-4',
        (
            ('font-size', '3.5rem', False),
        ),
    ),
    (
        '.display-5',
        (
            ('font-size', '3rem', False),
        ),
    ),
    (
        '.display-6',
        (
            ('font-size', '2.5rem', False),
        ),
    ),
    (
        '.initialism',
        (
            ('font-size', '0.8125rem', False),
        ),
    ),
    (
        '.blockquote',
        (
            ('font-size', '1.25rem', False),
        ),
    ),
    (
        '.figure-caption',
        (
            ('font-size', '0.8125rem', False),
        ),
    ),
    (
        '.col-form-label',
        (
            ('font-size', 'inherit', False),
        ),
    ),
    (
        '.col-form-label-lg',
        (
            ('font-size', '1.25rem', False),
        ),
    ),
    (
        '.col-form-label-sm',
        (
            ('font-size', '0.8125rem', False),
        ),
    ),
    (
        '.form-text',
        (
            ('font-size', '0.8125rem', False),
        ),
    ),
    (
        '.form-control',
        (
            ('font-size', '1rem', False),
        ),
    ),
    (
        '.form-control-sm',
        (
            ('font-size', '0.8125rem', False),
        ),
    ),
    (
        '.form-control-lg',
        (
            ('font-size', '1.25rem', False),
        ),
    ),
    (
        '.form-select',
        (
            ('font-size', '1rem', False),
        ),
    ),
    (
        '.form-select-sm',
        (
            ('font-size', '0.8125rem', False),
        ),
    ),
    (
        '.form-select-lg',
        (
            ('font-size', '1.25rem', False),
        ),
    ),
    (
        '.input-group-text',
        (
            ('font-size', '1rem', False),
        ),
    ),
    (
        '.input-group-lg > .form-control, .input-group-lg > .form-select, .input-group-lg > .input-group-text, .input-group-lg > .btn',
        (
            ('font-size', '1.25rem', False),
        ),
    ),
    (
        '.input-group-sm > .form-control, .input-group-sm > .form-select, .input-group-sm > .input-group-text, .input-group-sm > .btn',
        (
            ('font-size', '0.8125rem', False),
        ),
    ),
    (
        '.valid-feedback',
        (
            ('font-size', '0.8125rem', False),
        ),
    ),
    (
        '.invalid-feedback',
        (
            ('font-size', '0.8125rem', False),
        ),
    ),
    (
        '.dropdown-header',
        (
            ('font-size', '0.8125rem', False),
        ),
    ),
    (
        '.accordion-button',
        (
            ('font-size', '1rem', False),
        ),
    ),
    (
        '.smaller',
        (
            ('font-size', '0.75rem', False),
        ),
    ),
    (
        '.fs-1',
        (
            ('font-size', '2.5rem', True),
        ),
    ),
    (
        '.fs-2',
        (
            ('font-size', '2rem', True),
        ),
    ),
    (
        '.fs-3',
        (
            ('font-size', '1.75rem', True),
        ),
    ),
    (
        '.fs-4',
        (
            ('font-size', '1.5rem', True),
        ),
    ),
    (
        '.fs-5',
        (
            ('font-size', '1.25rem', True),
        ),
    ),
    (
        '.fs-6',
        (
            ('font-size', '1rem', True),
        ),
    ),
    (
        '.oe_styling_v8 .oe_button.oe_big, .oe_styling_v8 a.oe_button.oe_big',
        (
            ('font-size', '24px', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_button.oe_bigger, .oe_styling_v8 a.oe_button.oe_bigger',
        (
            ('font-size', '32px', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_button.oe_small, .oe_styling_v8 a.oe_button.oe_small',
        (
            ('font-size', '13px', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_button.oe_medium, .oe_styling_v8 a.oe_button.oe_medium',
        (
            ('font-size', '16px', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_input_label',
        (
            ('font-size', '16px', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_input_label.oe_big',
        (
            ('font-size', '20px', False),
        ),
    ),
    (
        '.oe_styling_v8 h1.oe_slogan',
        (
            ('font-size', '64px', False),
        ),
    ),
    (
        '.oe_styling_v8 h2.oe_slogan',
        (
            ('font-size', '40px', False),
        ),
    ),
    (
        '.oe_styling_v8 h3.oe_slogan',
        (
            ('font-size', '26px', False),
        ),
    ),
    (
        '.oe_styling_v8 h4.oe_slogan',
        (
            ('font-size', '24px', False),
        ),
    ),
    (
        '.oe_row_tab',
        (
            ('font-size', '20px', False),
        ),
    ),
    (
        '.fa',
        (
            ('font-size', '14px', False),
            ('font-family', 'FontAwesome', False),
            ('font-size', 'inherit', False),
        ),
    ),
    (
        '.fa-lg',
        (
            ('font-size', '1.315em', False),
        ),
    ),
    (
        '.fa-2x',
        (
            ('font-size', '2em', False),
        ),
    ),
    (
        '.fa-3x',
        (
            ('font-size', '3em', False),
        ),
    ),
    (
        '.fa-4x',
        (
            ('font-size', '4em', False),
        ),
    ),
    (
        '.fa-5x',
        (
            ('font-size', '5em', False),
        ),
    ),
    (
        '.fa-stack-2x',
        (
            ('font-size', '2em', False),
        ),
    ),
    (
        '.display-1-fs',
        (
            ('font-size', '6rem', False),
        ),
    ),
    (
        '.display-2-fs',
        (
            ('font-size', '5.5rem', False),
        ),
    ),
    (
        '.display-3-fs',
        (
            ('font-size', '4.5rem', False),
        ),
    ),
    (
        '.display-4-fs',
        (
            ('font-size', '3.5rem', False),
        ),
    ),
    (
        '.h1-fs',
        (
            ('font-size', '2.5rem', False),
        ),
    ),
    (
        '.h2-fs',
        (
            ('font-size', '2rem', False),
        ),
    ),
    (
        '.h3-fs',
        (
            ('font-size', '1.75rem', False),
        ),
    ),
    (
        '.h4-fs',
        (
            ('font-size', '1.5rem', False),
        ),
    ),
    (
        '.h5-fs',
        (
            ('font-size', '1.25rem', False),
        ),
    ),
    (
        '.h6-fs',
        (
            ('font-size', '1rem', False),
        ),
    ),
    (
        '.btn',
        (
            ('font-size', '1rem', False),
        ),
    ),
    (
        'ul.o_checklist > li.o_checked::before',
        (
            ('font-size', '13px', False),
        ),
    ),
    (
        '.fa-6x',
        (
            ('font-size', '6em', False),
        ),
    ),
    (
        '.fa-7x',
        (
            ('font-size', '7em', False),
        ),
    ),
    (
        '.fa-8x',
        (
            ('font-size', '8em', False),
        ),
    ),
    (
        '.fa-9x',
        (
            ('font-size', '9em', False),
        ),
    ),
    (
        '.fa-10x',
        (
            ('font-size', '10em', False),
        ),
    ),
    (
        '.o_small',
        (
            ('font-size', '0.875rem', False),
        ),
    ),
    (
        '.display-1-fs',
        (
            ('font-size', '5rem', False),
        ),
    ),
    (
        '.display-2-fs',
        (
            ('font-size', '4.5rem', False),
        ),
    ),
    (
        '.display-3-fs',
        (
            ('font-size', '4rem', False),
        ),
    ),
    (
        '.base-fs',
        (
            ('font-size', '1rem', False),
        ),
    ),
    (
        '.o_small-fs',
        (
            ('font-size', '0.8125rem', False),
        ),
    ),
    (
        '.o_report_reception .o_priority.o_priority_star',
        (
            ('font-size', '1.35em', False),
        ),
    ),
    (
        '.o_label_page.o_label_dymo',
        (
            ('font-size', '80%', False),
        ),
    ),
    (
        'h6, .h6, h5, .h5, h4, .h4, h3, .h3, h2, .h2, h1, .h1',
        (
            ('font-family', 'inherit', False),
        ),
    ),
    (
        '.openerp .oe_form .oe_styling_v8 .oe_title_font',
        (
            ('font-family', '"Lato", "Open Sans", "Helvetica", Sans', False),
        ),
    ),
    (
        '.fa.fa-threads, .fa.fa-kickstarter, .fa.fa-bluesky, .fa.fa-strava, .fa.fa-google-play, .fa.fa-discord, .fa-twitter-square.fa, .fa-twitter.fa, .fa.fa-tiktok',
        (
            ('font-family', "'odoo_ui_icons'", True),
        ),
    ),
    (
        '.oi',
        (
            ('font-family', "'odoo_ui_icons'", True),
        ),
    ),
)

#: Body type for the bounded public sale profile.
FONT_SIZE_PT = 10.24
#: The bordered table line box: the authored 24px body line-height plus the
#: authored 1px row rule. Padding remains independently resolved per edge.
LINE_HEIGHT_MM = (24.0 + 1.0) * MM_PER_PX

#: The first selector-preserving slice of the offline report CSS profile.
#:
#: Values stay in CSS units and the selector stays attached. Runtime parses
#: neither SCSS nor the 450KB CSS bundle; it only matches these pre-tokenised
#: rules against the evaluated element tree.  This is intentionally not a
#: ``theme -> padding`` table: ``table-sm`` and ``o_table_bold`` are selectors
#: with different specificity, and flattening either predicate was the bug.
#: Every rule in the bundle that makes an element a flex container, with its
#: selector attached. Same shape and same reasoning as TABLE_STYLE_RULES: the
#: runtime matches these rather than being handed a flattened answer.
#:
#: The parser used to decide "is this a flex row" by looking for the class
#: `d-flex`, which is a hand-written predicate standing where the cascade has
#: an answer. `.o_stock_report_header_row` declares `display: flex` and
#: fields out as a vertical stack. `.d-flex` is itself one of these rules, so
#: asking the cascade subsumes the class check rather than joining it.
#:
#: Derived, not generated: `python tools/derive_layout_rules.py --emit`,
#: and the same tool without arguments reports drift against the bundle.
LAYOUT_STYLE_RULES = (
    (
        '.row',
        (
            ('display', 'flex', False),
            ('flex-wrap', 'wrap', False),
        ),
    ),
    (
        '.input-group',
        (
            ('display', 'flex', False),
            ('flex-wrap', 'wrap', False),
            ('align-items', 'stretch', False),
        ),
    ),
    (
        '.input-group-text',
        (
            ('display', 'flex', False),
            ('align-items', 'center', False),
        ),
    ),
    (
        '.btn-group, .btn-group-vertical',
        (
            ('display', 'inline-flex', False),
        ),
    ),
    (
        '.btn-toolbar',
        (
            ('display', 'flex', False),
            ('flex-wrap', 'wrap', False),
            ('justify-content', 'flex-start', False),
        ),
    ),
    (
        '.nav',
        (
            ('display', 'flex', False),
            ('flex-wrap', 'wrap', False),
        ),
    ),
    (
        '.navbar',
        (
            ('display', 'flex', False),
            ('flex-wrap', 'wrap', False),
            ('align-items', 'center', False),
            ('justify-content', 'space-between', False),
        ),
    ),
    (
        '.navbar > .container, .navbar > .o_container_small, .navbar > .container-fluid, .navbar > .container-sm, .navbar > .container-md, .navbar > .container-lg, .navbar > .container-xl, .navbar > .container-xxl',
        (
            ('display', 'flex', False),
            ('flex-wrap', 'inherit', False),
            ('align-items', 'center', False),
            ('justify-content', 'space-between', False),
        ),
    ),
    (
        '.navbar-nav',
        (
            ('display', 'flex', False),
            ('flex-direction', 'column', False),
        ),
    ),
    (
        '.navbar-expand-sm .navbar-collapse',
        (
            ('display', 'flex', True),
        ),
    ),
    (
        '.navbar-expand-sm .offcanvas .offcanvas-body',
        (
            ('display', 'flex', False),
        ),
    ),
    (
        '.navbar-expand-md .navbar-collapse',
        (
            ('display', 'flex', True),
        ),
    ),
    (
        '.navbar-expand-md .offcanvas .offcanvas-body',
        (
            ('display', 'flex', False),
        ),
    ),
    (
        '.navbar-expand-lg .navbar-collapse',
        (
            ('display', 'flex', True),
        ),
    ),
    (
        '.navbar-expand-lg .offcanvas .offcanvas-body',
        (
            ('display', 'flex', False),
        ),
    ),
    (
        '.navbar-expand-xl .navbar-collapse',
        (
            ('display', 'flex', True),
        ),
    ),
    (
        '.navbar-expand-xl .offcanvas .offcanvas-body',
        (
            ('display', 'flex', False),
        ),
    ),
    (
        '.navbar-expand-xxl .navbar-collapse',
        (
            ('display', 'flex', True),
        ),
    ),
    (
        '.navbar-expand-xxl .offcanvas .offcanvas-body',
        (
            ('display', 'flex', False),
        ),
    ),
    (
        '.navbar-expand .navbar-collapse',
        (
            ('display', 'flex', True),
        ),
    ),
    (
        '.navbar-expand .offcanvas .offcanvas-body',
        (
            ('display', 'flex', False),
        ),
    ),
    (
        '.card',
        (
            ('display', 'flex', False),
            ('flex-direction', 'column', False),
        ),
    ),
    (
        '.card-group',
        (
            ('display', 'flex', False),
            ('flex-flow', 'row wrap', False),
        ),
    ),
    (
        '.accordion-button',
        (
            ('display', 'flex', False),
            ('align-items', 'center', False),
        ),
    ),
    (
        '.breadcrumb',
        (
            ('display', 'flex', False),
            ('flex-wrap', 'wrap', False),
        ),
    ),
    (
        '.pagination',
        (
            ('display', 'flex', False),
        ),
    ),
    (
        '.progress, .progress-stacked',
        (
            ('display', 'flex', False),
        ),
    ),
    (
        '.progress-bar',
        (
            ('display', 'flex', False),
            ('flex-direction', 'column', False),
            ('justify-content', 'center', False),
        ),
    ),
    (
        '.list-group',
        (
            ('display', 'flex', False),
            ('flex-direction', 'column', False),
        ),
    ),
    (
        '.toast-header',
        (
            ('display', 'flex', False),
            ('align-items', 'center', False),
        ),
    ),
    (
        '.modal-dialog-centered',
        (
            ('display', 'flex', False),
            ('align-items', 'center', False),
        ),
    ),
    (
        '.modal-content',
        (
            ('display', 'flex', False),
            ('flex-direction', 'column', False),
        ),
    ),
    (
        '.modal-header',
        (
            ('display', 'flex', False),
            ('align-items', 'center', False),
        ),
    ),
    (
        '.modal-footer',
        (
            ('display', 'flex', False),
            ('flex-wrap', 'wrap', False),
            ('align-items', 'center', False),
            ('justify-content', 'flex-end', False),
        ),
    ),
    (
        '.carousel-control-prev, .carousel-control-next',
        (
            ('display', 'flex', False),
            ('align-items', 'center', False),
            ('justify-content', 'center', False),
        ),
    ),
    (
        '.carousel-indicators',
        (
            ('display', 'flex', False),
            ('justify-content', 'center', False),
        ),
    ),
    (
        '.offcanvas-sm',
        (
            ('display', 'flex', False),
            ('flex-direction', 'column', False),
        ),
    ),
    (
        '.offcanvas-sm .offcanvas-body',
        (
            ('display', 'flex', False),
        ),
    ),
    (
        '.offcanvas-md',
        (
            ('display', 'flex', False),
            ('flex-direction', 'column', False),
        ),
    ),
    (
        '.offcanvas-md .offcanvas-body',
        (
            ('display', 'flex', False),
        ),
    ),
    (
        '.offcanvas-lg',
        (
            ('display', 'flex', False),
            ('flex-direction', 'column', False),
        ),
    ),
    (
        '.offcanvas-lg .offcanvas-body',
        (
            ('display', 'flex', False),
        ),
    ),
    (
        '.offcanvas-xl',
        (
            ('display', 'flex', False),
            ('flex-direction', 'column', False),
        ),
    ),
    (
        '.offcanvas-xl .offcanvas-body',
        (
            ('display', 'flex', False),
        ),
    ),
    (
        '.offcanvas-xxl',
        (
            ('display', 'flex', False),
            ('flex-direction', 'column', False),
        ),
    ),
    (
        '.offcanvas-xxl .offcanvas-body',
        (
            ('display', 'flex', False),
        ),
    ),
    (
        '.offcanvas',
        (
            ('display', 'flex', False),
            ('flex-direction', 'column', False),
        ),
    ),
    (
        '.offcanvas-header',
        (
            ('display', 'flex', False),
            ('align-items', 'center', False),
        ),
    ),
    (
        '.icon-link',
        (
            ('display', 'inline-flex', False),
            ('gap', '0.375rem', False),
            ('align-items', 'center', False),
        ),
    ),
    (
        '.hstack',
        (
            ('display', 'flex', False),
            ('flex-direction', 'row', False),
            ('align-items', 'center', False),
        ),
    ),
    (
        '.vstack',
        (
            ('display', 'flex', False),
            ('flex-direction', 'column', False),
        ),
    ),
    (
        '.d-flex',
        (
            ('display', 'flex', True),
        ),
    ),
    (
        '.d-inline-flex',
        (
            ('display', 'inline-flex', True),
        ),
    ),
    (
        '.d-sm-flex',
        (
            ('display', 'flex', True),
        ),
    ),
    (
        '.d-sm-inline-flex',
        (
            ('display', 'inline-flex', True),
        ),
    ),
    (
        '.d-md-flex',
        (
            ('display', 'flex', True),
        ),
    ),
    (
        '.d-md-inline-flex',
        (
            ('display', 'inline-flex', True),
        ),
    ),
    (
        '.d-lg-flex',
        (
            ('display', 'flex', True),
        ),
    ),
    (
        '.d-lg-inline-flex',
        (
            ('display', 'inline-flex', True),
        ),
    ),
    (
        '.d-xl-flex',
        (
            ('display', 'flex', True),
        ),
    ),
    (
        '.d-xl-inline-flex',
        (
            ('display', 'inline-flex', True),
        ),
    ),
    (
        '.d-xxl-flex',
        (
            ('display', 'flex', True),
        ),
    ),
    (
        '.d-xxl-inline-flex',
        (
            ('display', 'inline-flex', True),
        ),
    ),
    (
        '.d-print-flex',
        (
            ('display', 'flex', True),
        ),
    ),
    (
        '.d-print-inline-flex',
        (
            ('display', 'inline-flex', True),
        ),
    ),
    (
        'ul.o_checklist > li.o_checked::before',
        (
            ('display', 'flex', False),
            ('align-items', 'center', False),
            ('justify-content', 'center', False),
        ),
    ),
    (
        '.o_we_search_prompt',
        (
            ('display', 'flex', False),
            ('align-items', 'center', False),
            ('justify-content', 'flex-start', False),
        ),
    ),
    (
        '.o_full_screen_height, .cover_full, .o_half_screen_height, .cover_mid',
        (
            ('display', 'flex', False),
            ('flex-direction', 'column', False),
            ('justify-content', 'space-around', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_rule',
        (
            ('display', 'flex', False),
            ('flex-flow', 'row nowrap', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_legend',
        (
            ('display', 'flex', False),
            ('flex-flow', 'row wrap', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_legend_line',
        (
            ('display', 'flex', False),
            ('flex-flow', 'row nowrap', False),
        ),
    ),
    (
        '.o_stock_report_header_row',
        (
            ('display', '-webkit-box', False),
            ('display', 'flex', False),
            ('flex-wrap', 'wrap', False),
            ('justify-content', 'center', False),
            ('flex-direction', 'row', False),
        ),
    ),
)


#: What the bundle says about a flex *item*, selectors intact and every
#: declaration under its own CSS name.
#:
#: This exists because the engine under measurement has no CSS3 flexbox: its
#: `EDisplay` carries `BOX`/`INLINE_BOX` and no `FLEX`
#: in the fixed compatibility vocabulary, so `flex: 1` is dropped
#: and `-webkit-box-flex: 1` is the declaration that actually grows a child
#: (`tests/test_legacy_flex_items.py`). The compiled profile previously kept
#: `justify-content` and `align-items` -- names this engine ignores -- and
#: none of the `-webkit-box-*` family it obeys, so the growth on
#: `.o_stock_report_header_row > div` reached nothing and its four items were
#: split equally instead of grown from their preferred widths.
#:
#: `min-width`/`max-width`/`width` travel with it because the box algorithm
#: clamps a child's pass-one width to them before distributing any growth.
#:
#: Note `.flex-grow-1` appears here as an ordinary rule. The parser used to
#: test that class name by hand; the cascade states it, so the predicate is
#: not needed and is gone.
#:
#: Derived by `tools/derive_layout_rules.py`, 140 rules.
#: What the bundle says about a block's padding, selectors intact and
#: under the four CSS names. The only route before this was
#: `box_spacing(classes)`, a regular expression over Bootstrap's
#: spacing utilities, so a padding stated by any other selector reached
#: nothing -- `div.o_employee_cv .o_company { padding-left: 30px }`
#: among them.
#: `float`, under its own CSS name and with its own CSS values. The only
#: route before this was one hand-written class predicate that recognised
#: nothing of `float: left`.
FLOAT_RULES = (
    (
        'legend',
        (
            ('float', 'left', False),
        ),
    ),
    (
        '.form-check .form-check-input',
        (
            ('float', 'left', False),
        ),
    ),
    (
        '.form-check-reverse .form-check-input',
        (
            ('float', 'right', False),
        ),
    ),
    (
        '.carousel-item',
        (
            ('float', 'left', False),
        ),
    ),
    (
        '.float-start',
        (
            ('float', 'left', True),
        ),
    ),
    (
        '.float-end',
        (
            ('float', 'right', True),
        ),
    ),
    (
        '.float-none',
        (
            ('float', 'none', True),
        ),
    ),
    (
        '.float-sm-start',
        (
            ('float', 'left', True),
        ),
    ),
    (
        '.float-sm-end',
        (
            ('float', 'right', True),
        ),
    ),
    (
        '.float-sm-none',
        (
            ('float', 'none', True),
        ),
    ),
    (
        '.float-md-start',
        (
            ('float', 'left', True),
        ),
    ),
    (
        '.float-md-end',
        (
            ('float', 'right', True),
        ),
    ),
    (
        '.float-md-none',
        (
            ('float', 'none', True),
        ),
    ),
    (
        '.float-lg-start',
        (
            ('float', 'left', True),
        ),
    ),
    (
        '.float-lg-end',
        (
            ('float', 'right', True),
        ),
    ),
    (
        '.float-lg-none',
        (
            ('float', 'none', True),
        ),
    ),
    (
        '.float-xl-start',
        (
            ('float', 'left', True),
        ),
    ),
    (
        '.float-xl-end',
        (
            ('float', 'right', True),
        ),
    ),
    (
        '.float-xl-none',
        (
            ('float', 'none', True),
        ),
    ),
    (
        '.float-xxl-start',
        (
            ('float', 'left', True),
        ),
    ),
    (
        '.float-xxl-end',
        (
            ('float', 'right', True),
        ),
    ),
    (
        '.float-xxl-none',
        (
            ('float', 'none', True),
        ),
    ),
    (
        "[class*='oe_span']",
        (
            ('float', 'left', False),
        ),
    ),
    (
        ".oe_row.oe_flex [class*='oe_span']",
        (
            ('float', 'none', False),
        ),
    ),
    (
        '.oe_quote .oe_photo',
        (
            ('float', 'left', False),
        ),
    ),
    (
        '.fa-pull-left',
        (
            ('float', 'left', False),
        ),
    ),
    (
        '.fa-pull-right',
        (
            ('float', 'right', False),
        ),
    ),
    (
        '.report-wrapping-flexbox > .col',
        (
            ('float', 'left', False),
        ),
    ),
)


#: is a generated `.clearfix::after`, which the pseudo slices carry. The
#: slice exists because a bundle may state one and because float and clear
#: are one capability -- placing floats with no way to clear them is the
#: half that breaks the other.
CLEAR_RULES = (
    (
        'legend + *',
        (
            ('clear', 'left', False),
        ),
    ),
    (
        '.dropdown-item',
        (
            ('clear', 'both', False),
        ),
    ),
    (
        '.alert',
        (
            ('clear', 'both', False),
        ),
    ),
)

#: How a legacy box distributes the space its children do not fill.
#:
#: `justify-content` is deliberately absent. The string does not appear
#: anywhere in the fixed compatibility vocabulary, so its parser
#: drops the declaration before the cascade sees it, `!important` and all;
#: `-webkit-box-pack` is the property that engine obeys, and
#: `tests/test_box_pack.py` fixes its placement contract.
#:
#: Derived by property, not by a flex `display` on the same rule. Bootstrap
#: states this on `.justify-content-between`, which declares no display, so
#: the display-triggered slice never saw it -- the compiler defect
#: `docs/flex-row-packing-2026-09-05.md` named, fixed as that document
#: proposed: the trigger is the property the slice keeps.
#:
#: Derived by `tools/derive_layout_rules.py`, 24 rules.
BOX_PACK_RULES = (
    (
        '.justify-content-center',
        (
            ('-webkit-box-pack', 'center', False),
        ),
    ),
    (
        '.justify-content-between',
        (
            ('-webkit-box-pack', 'justify', False),
        ),
    ),
    (
        '.o_stock_report_header_row',
        (
            ('-webkit-box-pack', 'center', False),
        ),
    ),
)

#: How a block aligns the content of its line boxes.
#:
#: Derived by property, so a rule stating one without stating a display
#: enters -- `div.o_employee_cv .o_sidebar .o_profile` among them, which is
#: the CV's own contributed stylesheet and why its sidebar headings were
#: drawn flush left.
#:
#: Values outside the fixed ten-value alignment vocabulary are already gone,
#: so the
#: compatibility parser refuses anything else before
#: its cascade sees it -- and the bundle writes
#: `th { text-align: inherit; text-align: -webkit-match-parent }`, where
#: than the `inherit` that survives there.
#:
#: `inherit` and `var()` stay: they state no alignment of their own but must
#: reach the cascade to be resolved or inherited through.
#:
#: Derived by `tools/derive_layout_rules.py`, 71 rules.
TEXT_ALIGN_RULES = (
    (
        '.justify-text',
        (
            ('text-align', 'justify', False),
        ),
    ),
    (
        'body',
        (
            ('text-align', 'var(--body-text-align)', False),
        ),
    ),
    (
        'caption',
        (
            ('text-align', 'left', False),
        ),
    ),
    (
        'th',
        (
            ('text-align', 'inherit', False),
        ),
    ),
    (
        '.form-check-reverse',
        (
            ('text-align', 'right', False),
        ),
    ),
    (
        '.form-floating > label',
        (
            ('text-align', 'start', False),
        ),
    ),
    (
        '.input-group-text',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.btn',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.dropdown-menu',
        (
            ('text-align', 'left', False),
        ),
    ),
    (
        '.dropdown-item',
        (
            ('text-align', 'inherit', False),
        ),
    ),
    (
        '.nav-fill > .nav-link, .nav-fill .nav-item',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.nav-justified > .nav-link, .nav-justified .nav-item',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.accordion-button',
        (
            ('text-align', 'left', False),
        ),
    ),
    (
        '.badge',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.progress-bar',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.list-group-item-action',
        (
            ('text-align', 'inherit', False),
        ),
    ),
    (
        '.tooltip',
        (
            ('text-align', 'left', False),
            ('text-align', 'start', False),
        ),
    ),
    (
        '.tooltip-inner',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.popover',
        (
            ('text-align', 'left', False),
            ('text-align', 'start', False),
        ),
    ),
    (
        '.carousel-control-prev, .carousel-control-next',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.carousel-caption',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.text-start',
        (
            ('text-align', 'left', True),
        ),
    ),
    (
        '.text-end',
        (
            ('text-align', 'right', True),
        ),
    ),
    (
        '.text-center',
        (
            ('text-align', 'center', True),
        ),
    ),
    (
        '.text-sm-start',
        (
            ('text-align', 'left', True),
        ),
    ),
    (
        '.text-sm-end',
        (
            ('text-align', 'right', True),
        ),
    ),
    (
        '.text-sm-center',
        (
            ('text-align', 'center', True),
        ),
    ),
    (
        '.text-md-start',
        (
            ('text-align', 'left', True),
        ),
    ),
    (
        '.text-md-end',
        (
            ('text-align', 'right', True),
        ),
    ),
    (
        '.text-md-center',
        (
            ('text-align', 'center', True),
        ),
    ),
    (
        '.text-lg-start',
        (
            ('text-align', 'left', True),
        ),
    ),
    (
        '.text-lg-end',
        (
            ('text-align', 'right', True),
        ),
    ),
    (
        '.text-lg-center',
        (
            ('text-align', 'center', True),
        ),
    ),
    (
        '.text-xl-start',
        (
            ('text-align', 'left', True),
        ),
    ),
    (
        '.text-xl-end',
        (
            ('text-align', 'right', True),
        ),
    ),
    (
        '.text-xl-center',
        (
            ('text-align', 'center', True),
        ),
    ),
    (
        '.text-xxl-start',
        (
            ('text-align', 'left', True),
        ),
    ),
    (
        '.text-xxl-end',
        (
            ('text-align', 'right', True),
        ),
    ),
    (
        '.text-xxl-center',
        (
            ('text-align', 'center', True),
        ),
    ),
    (
        '.oe_leftalign',
        (
            ('text-align', 'left', False),
        ),
    ),
    (
        '.oe_rightalign',
        (
            ('text-align', 'right', False),
        ),
    ),
    (
        '.oe_centeralign',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_form_layout_table td:first-child',
        (
            ('text-align', 'right', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_slogan',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.oe_quote .oe_q, .oe_quote q',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.oe_row_tabs',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.fa-fw',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.fa-li',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.fa-stack-1x, .fa-stack-2x',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        'table.table th',
        (
            ('text-align', 'left', False),
        ),
    ),
    (
        '.fa.mx-auto',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        'div.media_iframe_video',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.o_nocontent_help',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.o_we_search_prompt > h2, .o_we_search_prompt > .h2',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.justify-text',
        (
            ('text-align', 'justify', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_putaway > p',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_rule_name',
        (
            ('text-align', 'center', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_location_header',
        (
            ('text-align', 'center', False),
        ),
    ),
)

#: A box's edges, under their own CSS names.
#:
#: Derived by property, for the same reason padding is. The table slice
#: carries border only incidentally -- eleven selectors of table chrome --
#: so a cell whose edge is stated by any other rule reached nothing.
#: `.o_table_bold table:not(.o_ignore_layout_styling) tbody tr:last-child td`
#: is one of them, and its 3px is the whole of bold's difference from the
#: other layouts in the totals-to-terms distance.
#:
#: A strict superset of what the table slice says about borders: 400
#: selectors against 11, none missing, with comma-separated lists expanded
#: before comparing -- the naive comparison is what made the padding round's
#: first reading wrong.
#:
#: Derived by `tools/derive_layout_rules.py`, 285 rules.
BORDER_STYLE_RULES = (
    (
        'html, body, div, span, applet, object, iframe, h1, h2, h3, h4, h5, h6, p, blockquote, pre, a, abbr, acronym, address, big, cite, code, del, dfn, em, font, img, ins, kbd, q, s, samp, small, strike, strong, sub, sup, tt, var, b, i, center, dl, dt, dd, ol, ul, li, fieldset, form, label, legend, table, caption, tbody, tfoot, thead, tr, th, td, article, aside, audio, canvas, details, figcaption, figure, footer, header, hgroup, mark, menu, meter, nav, output, progress, section, summary, time, video',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        'abbr[title], dfn[title]',
        (
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'dotted', False),
            ('border-bottom-color', '#000', False),
        ),
    ),
    (
        'hr',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#ccc', False),
        ),
    ),
    (
        '#qrcode_odoo_logo',
        (
            ('border-top-color', 'white', True),
            ('border-right-color', 'white', True),
            ('border-bottom-color', 'white', True),
            ('border-left-color', 'white', True),
        ),
    ),
    (
        'hr',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--border-width)', False),
        ),
    ),
    (
        'thead, tbody, tfoot, tr, td, th',
        (
            ('border-top-color', 'inherit', False),
            ('border-right-color', 'inherit', False),
            ('border-bottom-color', 'inherit', False),
            ('border-left-color', 'inherit', False),
            ('border-top-style', 'solid', False),
            ('border-right-style', 'solid', False),
            ('border-bottom-style', 'solid', False),
            ('border-left-style', 'solid', False),
            ('border-top-width', '0', False),
            ('border-right-width', '0', False),
            ('border-bottom-width', '0', False),
            ('border-left-width', '0', False),
        ),
    ),
    (
        '::-moz-focus-inner',
        (
            ('border-top-style', 'none', False),
            ('border-right-style', 'none', False),
            ('border-bottom-style', 'none', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        'fieldset',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        'iframe',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.img-thumbnail',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--border-color)', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--border-color)', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--border-color)', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--border-color)', False),
        ),
    ),
    (
        '.table',
        (
            ('border-top-color', 'var(--table-border-color)', False),
            ('border-right-color', 'var(--table-border-color)', False),
            ('border-bottom-color', 'var(--table-border-color)', False),
            ('border-left-color', 'var(--table-border-color)', False),
        ),
    ),
    (
        '.table > :not(caption) > * > *',
        (
            ('border-bottom-width', 'var(--border-width)', False),
        ),
    ),
    (
        '.table-group-divider',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#e9ecef', False),
        ),
    ),
    (
        '.table-bordered > :not(caption) > *',
        (
            ('border-top-width', 'var(--border-width)', False),
            ('border-right-width', '0', False),
            ('border-bottom-width', 'var(--border-width)', False),
            ('border-left-width', '0', False),
        ),
    ),
    (
        '.table-bordered > :not(caption) > * > *',
        (
            ('border-top-width', '0', False),
            ('border-right-width', 'var(--border-width)', False),
            ('border-bottom-width', '0', False),
            ('border-left-width', 'var(--border-width)', False),
        ),
    ),
    (
        '.table-borderless > :not(caption) > * > *',
        (
            ('border-bottom-width', '0', False),
        ),
    ),
    (
        '.table-borderless > :not(:first-child)',
        (
            ('border-top-width', '0', False),
        ),
    ),
    (
        '.table-primary',
        (
            ('border-top-color', 'var(--table-border-color)', False),
            ('border-right-color', 'var(--table-border-color)', False),
            ('border-bottom-color', 'var(--table-border-color)', False),
            ('border-left-color', 'var(--table-border-color)', False),
        ),
    ),
    (
        '.table-secondary',
        (
            ('border-top-color', 'var(--table-border-color)', False),
            ('border-right-color', 'var(--table-border-color)', False),
            ('border-bottom-color', 'var(--table-border-color)', False),
            ('border-left-color', 'var(--table-border-color)', False),
        ),
    ),
    (
        '.table-success',
        (
            ('border-top-color', 'var(--table-border-color)', False),
            ('border-right-color', 'var(--table-border-color)', False),
            ('border-bottom-color', 'var(--table-border-color)', False),
            ('border-left-color', 'var(--table-border-color)', False),
        ),
    ),
    (
        '.table-info',
        (
            ('border-top-color', 'var(--table-border-color)', False),
            ('border-right-color', 'var(--table-border-color)', False),
            ('border-bottom-color', 'var(--table-border-color)', False),
            ('border-left-color', 'var(--table-border-color)', False),
        ),
    ),
    (
        '.table-warning',
        (
            ('border-top-color', 'var(--table-border-color)', False),
            ('border-right-color', 'var(--table-border-color)', False),
            ('border-bottom-color', 'var(--table-border-color)', False),
            ('border-left-color', 'var(--table-border-color)', False),
        ),
    ),
    (
        '.table-danger',
        (
            ('border-top-color', 'var(--table-border-color)', False),
            ('border-right-color', 'var(--table-border-color)', False),
            ('border-bottom-color', 'var(--table-border-color)', False),
            ('border-left-color', 'var(--table-border-color)', False),
        ),
    ),
    (
        '.table-light',
        (
            ('border-top-color', 'var(--table-border-color)', False),
            ('border-right-color', 'var(--table-border-color)', False),
            ('border-bottom-color', 'var(--table-border-color)', False),
            ('border-left-color', 'var(--table-border-color)', False),
        ),
    ),
    (
        '.table-dark',
        (
            ('border-top-color', 'var(--table-border-color)', False),
            ('border-right-color', 'var(--table-border-color)', False),
            ('border-bottom-color', 'var(--table-border-color)', False),
            ('border-left-color', 'var(--table-border-color)', False),
        ),
    ),
    (
        '.form-control',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--border-color)', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--border-color)', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--border-color)', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--border-color)', False),
        ),
    ),
    (
        '.form-control::file-selector-button',
        (
            ('border-top-color', 'inherit', False),
            ('border-right-color', 'inherit', False),
            ('border-bottom-color', 'inherit', False),
            ('border-left-color', 'inherit', False),
            ('border-top-style', 'solid', False),
            ('border-right-style', 'solid', False),
            ('border-bottom-style', 'solid', False),
            ('border-left-style', 'solid', False),
            ('border-top-width', '0', False),
            ('border-right-width', '0', False),
            ('border-bottom-width', '0', False),
            ('border-left-width', '0', False),
        ),
    ),
    (
        '.form-control-plaintext',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'transparent', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'transparent', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'transparent', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'transparent', False),
            ('border-top-width', 'var(--border-width)', False),
            ('border-right-width', '0', False),
            ('border-bottom-width', 'var(--border-width)', False),
            ('border-left-width', '0', False),
        ),
    ),
    (
        '.form-control-color::-moz-color-swatch',
        (
            ('border-top-width', '0', True),
            ('border-top-style', 'none', True),
            ('border-right-width', '0', True),
            ('border-right-style', 'none', True),
            ('border-bottom-width', '0', True),
            ('border-bottom-style', 'none', True),
            ('border-left-width', '0', True),
            ('border-left-style', 'none', True),
        ),
    ),
    (
        '.form-control-color::-webkit-color-swatch',
        (
            ('border-top-width', '0', True),
            ('border-top-style', 'none', True),
            ('border-right-width', '0', True),
            ('border-right-style', 'none', True),
            ('border-bottom-width', '0', True),
            ('border-bottom-style', 'none', True),
            ('border-left-width', '0', True),
            ('border-left-style', 'none', True),
        ),
    ),
    (
        '.form-select',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--border-color)', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--border-color)', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--border-color)', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--border-color)', False),
        ),
    ),
    (
        '.form-check-input',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--border-color)', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--border-color)', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--border-color)', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--border-color)', False),
        ),
    ),
    (
        '.form-check-input:checked',
        (
            ('border-top-color', '#71639e', False),
            ('border-right-color', '#71639e', False),
            ('border-bottom-color', '#71639e', False),
            ('border-left-color', '#71639e', False),
        ),
    ),
    (
        '.form-check-input[type="checkbox"]:indeterminate',
        (
            ('border-top-color', '#dddbe8', False),
            ('border-right-color', '#dddbe8', False),
            ('border-bottom-color', '#dddbe8', False),
            ('border-left-color', '#dddbe8', False),
        ),
    ),
    (
        '.form-range::-moz-focus-outer',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.form-range::-webkit-slider-thumb',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.form-range::-webkit-slider-runnable-track',
        (
            ('border-top-color', 'transparent', False),
            ('border-right-color', 'transparent', False),
            ('border-bottom-color', 'transparent', False),
            ('border-left-color', 'transparent', False),
        ),
    ),
    (
        '.form-range::-moz-range-thumb',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.form-range::-moz-range-track',
        (
            ('border-top-color', 'transparent', False),
            ('border-right-color', 'transparent', False),
            ('border-bottom-color', 'transparent', False),
            ('border-left-color', 'transparent', False),
        ),
    ),
    (
        '.form-floating > label',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'transparent', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'transparent', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'transparent', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'transparent', False),
        ),
    ),
    (
        '.form-floating > .form-control-plaintext ~ label',
        (
            ('border-top-width', 'var(--border-width)', False),
            ('border-right-width', '0', False),
            ('border-bottom-width', 'var(--border-width)', False),
            ('border-left-width', '0', False),
        ),
    ),
    (
        '.input-group-text',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--border-color)', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--border-color)', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--border-color)', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--border-color)', False),
        ),
    ),
    (
        '.was-validated .form-control:valid, .form-control.is-valid',
        (
            ('border-top-color', 'var(--form-valid-border-color)', False),
            ('border-right-color', 'var(--form-valid-border-color)', False),
            ('border-bottom-color', 'var(--form-valid-border-color)', False),
            ('border-left-color', 'var(--form-valid-border-color)', False),
        ),
    ),
    (
        '.was-validated .form-select:valid, .form-select.is-valid',
        (
            ('border-top-color', 'var(--form-valid-border-color)', False),
            ('border-right-color', 'var(--form-valid-border-color)', False),
            ('border-bottom-color', 'var(--form-valid-border-color)', False),
            ('border-left-color', 'var(--form-valid-border-color)', False),
        ),
    ),
    (
        '.was-validated .form-check-input:valid, .form-check-input.is-valid',
        (
            ('border-top-color', 'var(--form-valid-border-color)', False),
            ('border-right-color', 'var(--form-valid-border-color)', False),
            ('border-bottom-color', 'var(--form-valid-border-color)', False),
            ('border-left-color', 'var(--form-valid-border-color)', False),
        ),
    ),
    (
        '.was-validated .form-control:invalid, .form-control.is-invalid',
        (
            ('border-top-color', 'var(--form-invalid-border-color)', False),
            ('border-right-color', 'var(--form-invalid-border-color)', False),
            ('border-bottom-color', 'var(--form-invalid-border-color)', False),
            ('border-left-color', 'var(--form-invalid-border-color)', False),
        ),
    ),
    (
        '.was-validated .form-select:invalid, .form-select.is-invalid',
        (
            ('border-top-color', 'var(--form-invalid-border-color)', False),
            ('border-right-color', 'var(--form-invalid-border-color)', False),
            ('border-bottom-color', 'var(--form-invalid-border-color)', False),
            ('border-left-color', 'var(--form-invalid-border-color)', False),
        ),
    ),
    (
        '.was-validated .form-check-input:invalid, .form-check-input.is-invalid',
        (
            ('border-top-color', 'var(--form-invalid-border-color)', False),
            ('border-right-color', 'var(--form-invalid-border-color)', False),
            ('border-bottom-color', 'var(--form-invalid-border-color)', False),
            ('border-left-color', 'var(--form-invalid-border-color)', False),
        ),
    ),
    (
        '.btn',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--btn-border-color)', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--btn-border-color)', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--btn-border-color)', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--btn-border-color)', False),
        ),
    ),
    (
        '.btn-check:checked + .btn, .btn.active, .btn.show',
        (
            ('border-top-color', 'var(--btn-active-border-color)', False),
            ('border-right-color', 'var(--btn-active-border-color)', False),
            ('border-bottom-color', 'var(--btn-active-border-color)', False),
            ('border-left-color', 'var(--btn-active-border-color)', False),
        ),
    ),
    (
        '.btn:disabled, .btn.disabled, fieldset:disabled .btn',
        (
            ('border-top-color', 'var(--btn-disabled-border-color)', False),
            ('border-right-color', 'var(--btn-disabled-border-color)', False),
            ('border-bottom-color', 'var(--btn-disabled-border-color)', False),
            ('border-left-color', 'var(--btn-disabled-border-color)', False),
        ),
    ),
    (
        '.dropdown-menu',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--dropdown-border-color)', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--dropdown-border-color)', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--dropdown-border-color)', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--dropdown-border-color)', False),
        ),
    ),
    (
        '.dropdown-divider',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--dropdown-divider-bg)', False),
        ),
    ),
    (
        '.dropdown-item',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.nav-link',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.nav-tabs',
        (
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--nav-tabs-border-color)', False),
        ),
    ),
    (
        '.nav-tabs .nav-link',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'transparent', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'transparent', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'transparent', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'transparent', False),
        ),
    ),
    (
        '.nav-tabs .nav-link.active, .nav-tabs .nav-item.show .nav-link',
        (
            ('border-top-color', 'var(--nav-tabs-link-active-border-color)', False),
            ('border-right-color', 'var(--nav-tabs-link-active-border-color)', False),
            ('border-bottom-color', 'var(--nav-tabs-link-active-border-color)', False),
            ('border-left-color', 'var(--nav-tabs-link-active-border-color)', False),
        ),
    ),
    (
        '.nav-underline .nav-link',
        (
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'transparent', False),
        ),
    ),
    (
        '.nav-underline .nav-link.active, .nav-underline .show > .nav-link',
        (
            ('border-bottom-color', 'currentcolor', False),
        ),
    ),
    (
        '.navbar-toggler',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--navbar-toggler-border-color)', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--navbar-toggler-border-color)', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--navbar-toggler-border-color)', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--navbar-toggler-border-color)', False),
        ),
    ),
    (
        '.navbar-expand-sm .offcanvas',
        (
            ('border-top-width', '0', True),
            ('border-top-style', 'none', True),
            ('border-right-width', '0', True),
            ('border-right-style', 'none', True),
            ('border-bottom-width', '0', True),
            ('border-bottom-style', 'none', True),
            ('border-left-width', '0', True),
            ('border-left-style', 'none', True),
        ),
    ),
    (
        '.navbar-expand-md .offcanvas',
        (
            ('border-top-width', '0', True),
            ('border-top-style', 'none', True),
            ('border-right-width', '0', True),
            ('border-right-style', 'none', True),
            ('border-bottom-width', '0', True),
            ('border-bottom-style', 'none', True),
            ('border-left-width', '0', True),
            ('border-left-style', 'none', True),
        ),
    ),
    (
        '.navbar-expand-lg .offcanvas',
        (
            ('border-top-width', '0', True),
            ('border-top-style', 'none', True),
            ('border-right-width', '0', True),
            ('border-right-style', 'none', True),
            ('border-bottom-width', '0', True),
            ('border-bottom-style', 'none', True),
            ('border-left-width', '0', True),
            ('border-left-style', 'none', True),
        ),
    ),
    (
        '.navbar-expand-xl .offcanvas',
        (
            ('border-top-width', '0', True),
            ('border-top-style', 'none', True),
            ('border-right-width', '0', True),
            ('border-right-style', 'none', True),
            ('border-bottom-width', '0', True),
            ('border-bottom-style', 'none', True),
            ('border-left-width', '0', True),
            ('border-left-style', 'none', True),
        ),
    ),
    (
        '.navbar-expand-xxl .offcanvas',
        (
            ('border-top-width', '0', True),
            ('border-top-style', 'none', True),
            ('border-right-width', '0', True),
            ('border-right-style', 'none', True),
            ('border-bottom-width', '0', True),
            ('border-bottom-style', 'none', True),
            ('border-left-width', '0', True),
            ('border-left-style', 'none', True),
        ),
    ),
    (
        '.navbar-expand .offcanvas',
        (
            ('border-top-width', '0', True),
            ('border-top-style', 'none', True),
            ('border-right-width', '0', True),
            ('border-right-style', 'none', True),
            ('border-bottom-width', '0', True),
            ('border-bottom-style', 'none', True),
            ('border-left-width', '0', True),
            ('border-left-style', 'none', True),
        ),
    ),
    (
        '.card',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--card-border-color)', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--card-border-color)', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--card-border-color)', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--card-border-color)', False),
        ),
    ),
    (
        '.card > .list-group',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'none', False),
            ('border-top-color', 'inherit', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'none', False),
            ('border-bottom-color', 'inherit', False),
        ),
    ),
    (
        '.card > .list-group:first-child',
        (
            ('border-top-width', '0', False),
        ),
    ),
    (
        '.card > .list-group:last-child',
        (
            ('border-bottom-width', '0', False),
        ),
    ),
    (
        '.card > .card-header + .list-group, .card > .list-group + .card-footer',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
        ),
    ),
    (
        '.card-header',
        (
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--card-border-color)', False),
        ),
    ),
    (
        '.card-footer',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--card-border-color)', False),
        ),
    ),
    (
        '.card-header-tabs',
        (
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
        ),
    ),
    (
        '.card-header-tabs .nav-link.active',
        (
            ('border-bottom-color', 'var(--card-bg)', False),
        ),
    ),
    (
        '.card-group > .card + .card',
        (
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.accordion-button',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.accordion-item',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--accordion-border-color)', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--accordion-border-color)', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--accordion-border-color)', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--accordion-border-color)', False),
        ),
    ),
    (
        '.accordion-item:not(:first-of-type)',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
        ),
    ),
    (
        '.accordion-flush > .accordion-item',
        (
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.accordion-flush > .accordion-item:first-child',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
        ),
    ),
    (
        '.accordion-flush > .accordion-item:last-child',
        (
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
        ),
    ),
    (
        '.page-link',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--pagination-border-color)', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--pagination-border-color)', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--pagination-border-color)', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--pagination-border-color)', False),
        ),
    ),
    (
        '.page-link.active, .active > .page-link',
        (
            ('border-top-color', 'var(--pagination-active-border-color)', False),
            ('border-right-color', 'var(--pagination-active-border-color)', False),
            ('border-bottom-color', 'var(--pagination-active-border-color)', False),
            ('border-left-color', 'var(--pagination-active-border-color)', False),
        ),
    ),
    (
        '.page-link.disabled, .disabled > .page-link',
        (
            ('border-top-color', 'var(--pagination-disabled-border-color)', False),
            ('border-right-color', 'var(--pagination-disabled-border-color)', False),
            ('border-bottom-color', 'var(--pagination-disabled-border-color)', False),
            ('border-left-color', 'var(--pagination-disabled-border-color)', False),
        ),
    ),
    (
        '.alert',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'none', False),
            ('border-top-color', 'var(--alert-border)', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'none', False),
            ('border-right-color', 'var(--alert-border)', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'none', False),
            ('border-bottom-color', 'var(--alert-border)', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'none', False),
            ('border-left-color', 'var(--alert-border)', False),
        ),
    ),
    (
        '.list-group-item',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--list-group-border-color)', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--list-group-border-color)', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--list-group-border-color)', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--list-group-border-color)', False),
        ),
    ),
    (
        '.list-group-item.active',
        (
            ('border-top-color', 'var(--list-group-active-border-color)', False),
            ('border-right-color', 'var(--list-group-active-border-color)', False),
            ('border-bottom-color', 'var(--list-group-active-border-color)', False),
            ('border-left-color', 'var(--list-group-active-border-color)', False),
        ),
    ),
    (
        '.list-group-item + .list-group-item',
        (
            ('border-top-width', '0', False),
        ),
    ),
    (
        '.list-group-item + .list-group-item.active',
        (
            ('border-top-width', 'var(--list-group-border-width)', False),
        ),
    ),
    (
        '.list-group-horizontal > .list-group-item + .list-group-item',
        (
            ('border-top-width', 'var(--list-group-border-width)', False),
            ('border-left-width', '0', False),
        ),
    ),
    (
        '.list-group-horizontal > .list-group-item + .list-group-item.active',
        (
            ('border-left-width', 'var(--list-group-border-width)', False),
        ),
    ),
    (
        '.list-group-horizontal-sm > .list-group-item + .list-group-item',
        (
            ('border-top-width', 'var(--list-group-border-width)', False),
            ('border-left-width', '0', False),
        ),
    ),
    (
        '.list-group-horizontal-sm > .list-group-item + .list-group-item.active',
        (
            ('border-left-width', 'var(--list-group-border-width)', False),
        ),
    ),
    (
        '.list-group-horizontal-md > .list-group-item + .list-group-item',
        (
            ('border-top-width', 'var(--list-group-border-width)', False),
            ('border-left-width', '0', False),
        ),
    ),
    (
        '.list-group-horizontal-md > .list-group-item + .list-group-item.active',
        (
            ('border-left-width', 'var(--list-group-border-width)', False),
        ),
    ),
    (
        '.list-group-horizontal-lg > .list-group-item + .list-group-item',
        (
            ('border-top-width', 'var(--list-group-border-width)', False),
            ('border-left-width', '0', False),
        ),
    ),
    (
        '.list-group-horizontal-lg > .list-group-item + .list-group-item.active',
        (
            ('border-left-width', 'var(--list-group-border-width)', False),
        ),
    ),
    (
        '.list-group-horizontal-xl > .list-group-item + .list-group-item',
        (
            ('border-top-width', 'var(--list-group-border-width)', False),
            ('border-left-width', '0', False),
        ),
    ),
    (
        '.list-group-horizontal-xl > .list-group-item + .list-group-item.active',
        (
            ('border-left-width', 'var(--list-group-border-width)', False),
        ),
    ),
    (
        '.list-group-horizontal-xxl > .list-group-item + .list-group-item',
        (
            ('border-top-width', 'var(--list-group-border-width)', False),
            ('border-left-width', '0', False),
        ),
    ),
    (
        '.list-group-horizontal-xxl > .list-group-item + .list-group-item.active',
        (
            ('border-left-width', 'var(--list-group-border-width)', False),
        ),
    ),
    (
        '.list-group-flush > .list-group-item',
        (
            ('border-top-width', '0', False),
            ('border-right-width', '0', False),
            ('border-bottom-width', 'var(--list-group-border-width)', False),
            ('border-left-width', '0', False),
        ),
    ),
    (
        '.list-group-flush > .list-group-item:last-child',
        (
            ('border-bottom-width', '0', False),
        ),
    ),
    (
        '.btn-close',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.toast',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--toast-border-color)', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--toast-border-color)', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--toast-border-color)', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--toast-border-color)', False),
        ),
    ),
    (
        '.toast-header',
        (
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--toast-header-border-color)', False),
        ),
    ),
    (
        '.modal-content',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--modal-border-color)', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--modal-border-color)', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--modal-border-color)', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--modal-border-color)', False),
        ),
    ),
    (
        '.modal-header',
        (
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--modal-header-border-color)', False),
        ),
    ),
    (
        '.modal-footer',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--modal-footer-border-color)', False),
        ),
    ),
    (
        '.modal-fullscreen .modal-content',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.modal-fullscreen-sm-down .modal-content',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.modal-fullscreen-md-down .modal-content',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.modal-fullscreen-lg-down .modal-content',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.modal-fullscreen-xl-down .modal-content',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.modal-fullscreen-xxl-down .modal-content',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.popover',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--popover-border-color)', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--popover-border-color)', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--popover-border-color)', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--popover-border-color)', False),
        ),
    ),
    (
        '.popover-header',
        (
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--popover-border-color)', False),
        ),
    ),
    (
        '.carousel-control-prev, .carousel-control-next',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.carousel-indicators [data-bs-target]',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
            ('border-top-width', '10px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'transparent', False),
            ('border-bottom-width', '10px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'transparent', False),
        ),
    ),
    (
        '.spinner-border',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'currentcolor', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'currentcolor', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'currentcolor', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'currentcolor', False),
            ('border-right-color', 'transparent', False),
        ),
    ),
    (
        '.offcanvas-sm.offcanvas-start',
        (
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-sm.offcanvas-end',
        (
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-sm.offcanvas-top',
        (
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-sm.offcanvas-bottom',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-md.offcanvas-start',
        (
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-md.offcanvas-end',
        (
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-md.offcanvas-top',
        (
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-md.offcanvas-bottom',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-lg.offcanvas-start',
        (
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-lg.offcanvas-end',
        (
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-lg.offcanvas-top',
        (
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-lg.offcanvas-bottom',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-xl.offcanvas-start',
        (
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-xl.offcanvas-end',
        (
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-xl.offcanvas-top',
        (
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-xl.offcanvas-bottom',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-xxl.offcanvas-start',
        (
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-xxl.offcanvas-end',
        (
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-xxl.offcanvas-top',
        (
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas-xxl.offcanvas-bottom',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas.offcanvas-start',
        (
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas.offcanvas-end',
        (
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas.offcanvas-top',
        (
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.offcanvas.offcanvas-bottom',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'var(--offcanvas-border-color)', False),
        ),
    ),
    (
        '.visually-hidden',
        (
            ('border-top-width', '0', True),
            ('border-top-style', 'none', True),
            ('border-right-width', '0', True),
            ('border-right-style', 'none', True),
            ('border-bottom-width', '0', True),
            ('border-bottom-style', 'none', True),
            ('border-left-width', '0', True),
            ('border-left-style', 'none', True),
        ),
    ),
    (
        '.border',
        (
            ('border-top-width', '1px', True),
            ('border-top-style', 'solid', True),
            ('border-top-color', '#212529', True),
            ('border-right-width', '1px', True),
            ('border-right-style', 'solid', True),
            ('border-right-color', '#212529', True),
            ('border-bottom-width', '1px', True),
            ('border-bottom-style', 'solid', True),
            ('border-bottom-color', '#212529', True),
            ('border-left-width', '1px', True),
            ('border-left-style', 'solid', True),
            ('border-left-color', '#212529', True),
        ),
    ),
    (
        '.border-0',
        (
            ('border-top-width', '0', True),
            ('border-top-style', 'none', True),
            ('border-right-width', '0', True),
            ('border-right-style', 'none', True),
            ('border-bottom-width', '0', True),
            ('border-bottom-style', 'none', True),
            ('border-left-width', '0', True),
            ('border-left-style', 'none', True),
        ),
    ),
    (
        '.border-top',
        (
            ('border-top-width', '1px', True),
            ('border-top-style', 'solid', True),
            ('border-top-color', '#212529', True),
        ),
    ),
    (
        '.border-top-0',
        (
            ('border-top-width', '0', True),
            ('border-top-style', 'none', True),
        ),
    ),
    (
        '.border-end',
        (
            ('border-right-width', '1px', True),
            ('border-right-style', 'solid', True),
            ('border-right-color', '#212529', True),
        ),
    ),
    (
        '.border-end-0',
        (
            ('border-right-width', '0', True),
            ('border-right-style', 'none', True),
        ),
    ),
    (
        '.border-bottom',
        (
            ('border-bottom-width', '1px', True),
            ('border-bottom-style', 'solid', True),
            ('border-bottom-color', '#212529', True),
        ),
    ),
    (
        '.border-bottom-0',
        (
            ('border-bottom-width', '0', True),
            ('border-bottom-style', 'none', True),
        ),
    ),
    (
        '.border-start',
        (
            ('border-left-width', '1px', True),
            ('border-left-style', 'solid', True),
            ('border-left-color', '#212529', True),
        ),
    ),
    (
        '.border-start-0',
        (
            ('border-left-width', '0', True),
            ('border-left-style', 'none', True),
        ),
    ),
    (
        '.border-primary',
        (
            ('border-top-color', 'rgba(var(--primary-rgb), var(--border-opacity))', True),
            ('border-right-color', 'rgba(var(--primary-rgb), var(--border-opacity))', True),
            ('border-bottom-color', 'rgba(var(--primary-rgb), var(--border-opacity))', True),
            ('border-left-color', 'rgba(var(--primary-rgb), var(--border-opacity))', True),
        ),
    ),
    (
        '.border-secondary',
        (
            ('border-top-color', 'rgba(var(--secondary-rgb), var(--border-opacity))', True),
            ('border-right-color', 'rgba(var(--secondary-rgb), var(--border-opacity))', True),
            ('border-bottom-color', 'rgba(var(--secondary-rgb), var(--border-opacity))', True),
            ('border-left-color', 'rgba(var(--secondary-rgb), var(--border-opacity))', True),
        ),
    ),
    (
        '.border-success',
        (
            ('border-top-color', 'rgba(var(--success-rgb), var(--border-opacity))', True),
            ('border-right-color', 'rgba(var(--success-rgb), var(--border-opacity))', True),
            ('border-bottom-color', 'rgba(var(--success-rgb), var(--border-opacity))', True),
            ('border-left-color', 'rgba(var(--success-rgb), var(--border-opacity))', True),
        ),
    ),
    (
        '.border-info',
        (
            ('border-top-color', 'rgba(var(--info-rgb), var(--border-opacity))', True),
            ('border-right-color', 'rgba(var(--info-rgb), var(--border-opacity))', True),
            ('border-bottom-color', 'rgba(var(--info-rgb), var(--border-opacity))', True),
            ('border-left-color', 'rgba(var(--info-rgb), var(--border-opacity))', True),
        ),
    ),
    (
        '.border-warning',
        (
            ('border-top-color', 'rgba(var(--warning-rgb), var(--border-opacity))', True),
            ('border-right-color', 'rgba(var(--warning-rgb), var(--border-opacity))', True),
            ('border-bottom-color', 'rgba(var(--warning-rgb), var(--border-opacity))', True),
            ('border-left-color', 'rgba(var(--warning-rgb), var(--border-opacity))', True),
        ),
    ),
    (
        '.border-danger',
        (
            ('border-top-color', 'rgba(var(--danger-rgb), var(--border-opacity))', True),
            ('border-right-color', 'rgba(var(--danger-rgb), var(--border-opacity))', True),
            ('border-bottom-color', 'rgba(var(--danger-rgb), var(--border-opacity))', True),
            ('border-left-color', 'rgba(var(--danger-rgb), var(--border-opacity))', True),
        ),
    ),
    (
        '.border-light',
        (
            ('border-top-color', 'rgba(var(--light-rgb), var(--border-opacity))', True),
            ('border-right-color', 'rgba(var(--light-rgb), var(--border-opacity))', True),
            ('border-bottom-color', 'rgba(var(--light-rgb), var(--border-opacity))', True),
            ('border-left-color', 'rgba(var(--light-rgb), var(--border-opacity))', True),
        ),
    ),
    (
        '.border-dark',
        (
            ('border-top-color', 'rgba(var(--dark-rgb), var(--border-opacity))', True),
            ('border-right-color', 'rgba(var(--dark-rgb), var(--border-opacity))', True),
            ('border-bottom-color', 'rgba(var(--dark-rgb), var(--border-opacity))', True),
            ('border-left-color', 'rgba(var(--dark-rgb), var(--border-opacity))', True),
        ),
    ),
    (
        '.border-black',
        (
            ('border-top-color', 'rgba(var(--black-rgb), var(--border-opacity))', True),
            ('border-right-color', 'rgba(var(--black-rgb), var(--border-opacity))', True),
            ('border-bottom-color', 'rgba(var(--black-rgb), var(--border-opacity))', True),
            ('border-left-color', 'rgba(var(--black-rgb), var(--border-opacity))', True),
        ),
    ),
    (
        '.border-white',
        (
            ('border-top-color', 'rgba(var(--white-rgb), var(--border-opacity))', True),
            ('border-right-color', 'rgba(var(--white-rgb), var(--border-opacity))', True),
            ('border-bottom-color', 'rgba(var(--white-rgb), var(--border-opacity))', True),
            ('border-left-color', 'rgba(var(--white-rgb), var(--border-opacity))', True),
        ),
    ),
    (
        '.border-transparent',
        (
            ('border-top-color', 'transparent', True),
            ('border-right-color', 'transparent', True),
            ('border-bottom-color', 'transparent', True),
            ('border-left-color', 'transparent', True),
        ),
    ),
    (
        '.border-primary-subtle',
        (
            ('border-top-color', 'var(--primary-border-subtle)', True),
            ('border-right-color', 'var(--primary-border-subtle)', True),
            ('border-bottom-color', 'var(--primary-border-subtle)', True),
            ('border-left-color', 'var(--primary-border-subtle)', True),
        ),
    ),
    (
        '.border-secondary-subtle',
        (
            ('border-top-color', 'var(--secondary-border-subtle)', True),
            ('border-right-color', 'var(--secondary-border-subtle)', True),
            ('border-bottom-color', 'var(--secondary-border-subtle)', True),
            ('border-left-color', 'var(--secondary-border-subtle)', True),
        ),
    ),
    (
        '.border-success-subtle',
        (
            ('border-top-color', 'var(--success-border-subtle)', True),
            ('border-right-color', 'var(--success-border-subtle)', True),
            ('border-bottom-color', 'var(--success-border-subtle)', True),
            ('border-left-color', 'var(--success-border-subtle)', True),
        ),
    ),
    (
        '.border-info-subtle',
        (
            ('border-top-color', 'var(--info-border-subtle)', True),
            ('border-right-color', 'var(--info-border-subtle)', True),
            ('border-bottom-color', 'var(--info-border-subtle)', True),
            ('border-left-color', 'var(--info-border-subtle)', True),
        ),
    ),
    (
        '.border-warning-subtle',
        (
            ('border-top-color', 'var(--warning-border-subtle)', True),
            ('border-right-color', 'var(--warning-border-subtle)', True),
            ('border-bottom-color', 'var(--warning-border-subtle)', True),
            ('border-left-color', 'var(--warning-border-subtle)', True),
        ),
    ),
    (
        '.border-danger-subtle',
        (
            ('border-top-color', 'var(--danger-border-subtle)', True),
            ('border-right-color', 'var(--danger-border-subtle)', True),
            ('border-bottom-color', 'var(--danger-border-subtle)', True),
            ('border-left-color', 'var(--danger-border-subtle)', True),
        ),
    ),
    (
        '.border-light-subtle',
        (
            ('border-top-color', 'var(--light-border-subtle)', True),
            ('border-right-color', 'var(--light-border-subtle)', True),
            ('border-bottom-color', 'var(--light-border-subtle)', True),
            ('border-left-color', 'var(--light-border-subtle)', True),
        ),
    ),
    (
        '.border-dark-subtle',
        (
            ('border-top-color', 'var(--dark-border-subtle)', True),
            ('border-right-color', 'var(--dark-border-subtle)', True),
            ('border-bottom-color', 'var(--dark-border-subtle)', True),
            ('border-left-color', 'var(--dark-border-subtle)', True),
        ),
    ),
    (
        '.border-1',
        (
            ('border-top-width', '1px', True),
            ('border-right-width', '1px', True),
            ('border-bottom-width', '1px', True),
            ('border-left-width', '1px', True),
        ),
    ),
    (
        '.border-2',
        (
            ('border-top-width', '2px', True),
            ('border-right-width', '2px', True),
            ('border-bottom-width', '2px', True),
            ('border-left-width', '2px', True),
        ),
    ),
    (
        '.border-3',
        (
            ('border-top-width', '3px', True),
            ('border-right-width', '3px', True),
            ('border-bottom-width', '3px', True),
            ('border-left-width', '3px', True),
        ),
    ),
    (
        '.border-4',
        (
            ('border-top-width', '4px', True),
            ('border-right-width', '4px', True),
            ('border-bottom-width', '4px', True),
            ('border-left-width', '4px', True),
        ),
    ),
    (
        '.border-5',
        (
            ('border-top-width', '5px', True),
            ('border-right-width', '5px', True),
            ('border-bottom-width', '5px', True),
            ('border-left-width', '5px', True),
        ),
    ),
    (
        '.oe_styling_v8 .oe_button, .oe_styling_v8 a.oe_button',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'rgba(0, 0, 0, 0.09)', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'rgba(0, 0, 0, 0.09)', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'rgba(0, 0, 0, 0.09)', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'rgba(0, 0, 0, 0.09)', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_input',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#d6d6d6', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#d6d6d6', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#d6d6d6', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#d6d6d6', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_input.oe_valid',
        (
            ('border-top-color', '#b1ebb6', False),
            ('border-right-color', '#b1ebb6', False),
            ('border-bottom-color', '#b1ebb6', False),
            ('border-left-color', '#b1ebb6', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_input.oe_invalid',
        (
            ('border-top-color', '#EBB1B1', False),
            ('border-right-color', '#EBB1B1', False),
            ('border-bottom-color', '#EBB1B1', False),
            ('border-left-color', '#EBB1B1', False),
        ),
    ),
    (
        '.oe_quote',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'rgba(0, 0, 0, 0.06)', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'rgba(0, 0, 0, 0.06)', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'rgba(0, 0, 0, 0.06)', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'rgba(0, 0, 0, 0.06)', False),
        ),
    ),
    (
        '.oe_dark .oe_quote',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#f0f0ff', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#f0f0ff', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#f0f0ff', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#f0f0ff', False),
        ),
    ),
    (
        'div.oe_demo',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#dedede', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#dedede', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#dedede', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#dedede', False),
        ),
    ),
    (
        '.oe_row_tab',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'rgba(0, 0, 0, 0.1)', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'rgba(0, 0, 0, 0.1)', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'rgba(0, 0, 0, 0.1)', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'rgba(0, 0, 0, 0.1)', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'none', False),
        ),
    ),
    (
        '.oe_row_tab.oe_active',
        (
            ('border-top-color', '#8272b6', False),
            ('border-top-width', '2px', False),
        ),
    ),
    (
        '.fa-border',
        (
            ('border-top-width', '0.08em', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#eeeeee', False),
            ('border-right-width', '0.08em', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#eeeeee', False),
            ('border-bottom-width', '0.08em', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#eeeeee', False),
            ('border-left-width', '0.08em', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#eeeeee', False),
        ),
    ),
    (
        '.visually-hidden',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.table-borderless tbody, .table-borderless thead, .table-borderless tfoot, .table-borderless tr, .table-borderless td, .table-borderless th',
        (
            ('border-top-width', '0', False),
            ('border-top-style', 'none', False),
            ('border-right-width', '0', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', '0', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', '0', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '.table-borderless > :not(:first-child)',
        (
            ('border-top-style', 'none', False),
        ),
    ),
    (
        '.o_black_border tr th',
        (
            ('border-bottom-width', '2px', True),
            ('border-bottom-style', 'solid', True),
            ('border-bottom-color', 'black', True),
        ),
    ),
    (
        'blockquote',
        (
            ('border-left-width', '5px', False),
            ('border-left-style', 'solid', False),
            ('border-top-color', '#dee2e6', False),
            ('border-right-color', '#dee2e6', False),
            ('border-bottom-color', '#dee2e6', False),
            ('border-left-color', '#dee2e6', False),
        ),
    ),
    (
        '.alert',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'transparent', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'transparent', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'transparent', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'transparent', False),
        ),
    ),
    (
        '.alert-primary',
        (
            ('border-top-color', '#c6c1d8', False),
            ('border-right-color', '#c6c1d8', False),
            ('border-bottom-color', '#c6c1d8', False),
            ('border-left-color', '#c6c1d8', False),
        ),
    ),
    (
        '.alert-secondary',
        (
            ('border-top-color', '#f2f3f5', False),
            ('border-right-color', '#f2f3f5', False),
            ('border-bottom-color', '#f2f3f5', False),
            ('border-left-color', '#f2f3f5', False),
        ),
    ),
    (
        '.alert-success',
        (
            ('border-top-color', '#a9dcb5', False),
            ('border-right-color', '#a9dcb5', False),
            ('border-bottom-color', '#a9dcb5', False),
            ('border-left-color', '#a9dcb5', False),
        ),
    ),
    (
        '.alert-info',
        (
            ('border-top-color', '#a2dae3', False),
            ('border-right-color', '#a2dae3', False),
            ('border-bottom-color', '#a2dae3', False),
            ('border-left-color', '#a2dae3', False),
        ),
    ),
    (
        '.alert-warning',
        (
            ('border-top-color', '#ffde99', False),
            ('border-right-color', '#ffde99', False),
            ('border-bottom-color', '#ffde99', False),
            ('border-left-color', '#ffde99', False),
        ),
    ),
    (
        '.alert-danger',
        (
            ('border-top-color', '#f1aeb5', False),
            ('border-right-color', '#f1aeb5', False),
            ('border-bottom-color', '#f1aeb5', False),
            ('border-left-color', '#f1aeb5', False),
        ),
    ),
    (
        '.alert-light',
        (
            ('border-top-color', '#e9ecef', False),
            ('border-right-color', '#e9ecef', False),
            ('border-bottom-color', '#e9ecef', False),
            ('border-left-color', '#e9ecef', False),
        ),
    ),
    (
        '.alert-dark',
        (
            ('border-top-color', '#adb5bd', False),
            ('border-right-color', '#adb5bd', False),
            ('border-bottom-color', '#adb5bd', False),
            ('border-left-color', '#adb5bd', False),
        ),
    ),
    (
        'hr',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
        ),
    ),
    (
        '.btn',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'transparent', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', 'transparent', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', 'transparent', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', 'transparent', False),
        ),
    ),
    (
        '.btn-primary',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#71639e', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#71639e', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#71639e', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#71639e', False),
        ),
    ),
    (
        '.btn-fill-primary',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#71639e', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#71639e', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#71639e', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#71639e', False),
        ),
    ),
    (
        '.btn-secondary',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#dee2e6', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#dee2e6', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#dee2e6', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#dee2e6', False),
        ),
    ),
    (
        '.btn-fill-secondary',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#dee2e6', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#dee2e6', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#dee2e6', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#dee2e6', False),
        ),
    ),
    (
        '.btn-light',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#ffffff', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#ffffff', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#ffffff', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#ffffff', False),
        ),
    ),
    (
        '.btn-fill-light',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#ffffff', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#ffffff', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#ffffff', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#ffffff', False),
        ),
    ),
    (
        '.btn-outline-secondary',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#dee2e6', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#dee2e6', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#dee2e6', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#dee2e6', False),
        ),
    ),
    (
        '.btn-outline-primary',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#71639e', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#71639e', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#71639e', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#71639e', False),
        ),
    ),
    (
        '.btn-success',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#28a745', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#28a745', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#28a745', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#28a745', False),
        ),
    ),
    (
        '.btn-outline-success',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#28a745', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#28a745', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#28a745', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#28a745', False),
        ),
    ),
    (
        '.btn-info',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#17a2b8', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#17a2b8', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#17a2b8', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#17a2b8', False),
        ),
    ),
    (
        '.btn-outline-info',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#17a2b8', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#17a2b8', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#17a2b8', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#17a2b8', False),
        ),
    ),
    (
        '.btn-warning',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#ffac00', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#ffac00', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#ffac00', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#ffac00', False),
        ),
    ),
    (
        '.btn-outline-warning',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#ffac00', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#ffac00', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#ffac00', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#ffac00', False),
        ),
    ),
    (
        '.btn-danger',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#dc3545', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#dc3545', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#dc3545', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#dc3545', False),
        ),
    ),
    (
        '.btn-outline-danger',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#dc3545', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#dc3545', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#dc3545', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#dc3545', False),
        ),
    ),
    (
        '.btn-outline-light',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#f8f9fa', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#f8f9fa', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#f8f9fa', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#f8f9fa', False),
        ),
    ),
    (
        '.btn-dark',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#212529', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#212529', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#212529', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#212529', False),
        ),
    ),
    (
        '.btn-outline-dark',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#212529', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#212529', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#212529', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#212529', False),
        ),
    ),
    (
        '.o_table_standard table:not(.o_ignore_layout_styling) thead',
        (
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#212529', False),
        ),
    ),
    (
        '.o_table_standard .o_total_table:not(.o_ignore_layout_styling), .o_table_standard .o_total_table:not(.o_ignore_layout_styling) .o_total',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#212529', False),
        ),
    ),
    (
        '.o_table_bold table:not(.o_ignore_layout_styling) thead th',
        (
            ('border-top-width', '3px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#212529', False),
        ),
    ),
    (
        '.o_table_bold table:not(.o_ignore_layout_styling) tbody tr:last-child td',
        (
            ('border-bottom-width', '3px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#212529', False),
        ),
    ),
    (
        '.o_table_bold .o_total_table:not(.o_ignore_layout_styling) .o_total, .o_table_bold .o_total_table:not(.o_ignore_layout_styling) .o_price_total',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#e9ecef', False),
        ),
    ),
    (
        '.o_table_striped table:not(.o_ignore_layout_styling) tr:not(:first-child)',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#e9ecef', False),
        ),
    ),
    (
        '.o_table_striped table:not(.o_ignore_layout_styling) tbody tr:first-child, .o_table_striped table:not(.o_ignore_layout_styling) tbody tr.o_line_section',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#ced4da', False),
        ),
    ),
    (
        '.o_table_striped table:not(.o_ignore_layout_styling) tbody tr:last-child',
        (
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#e9ecef', False),
        ),
    ),
    (
        '.o_table_striped table:not(.o_ignore_layout_styling) tbody tr.is-subtotal',
        (
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#ced4da', False),
        ),
    ),
    (
        '.o_table_striped .o_total_table:not(.o_ignore_layout_styling) tr:first-child',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'none', False),
        ),
    ),
    (
        '.o_table_boxed table:not(.o_ignore_layout_styling) thead th:not(:last-child), .o_table_boxed-rounded table:not(.o_ignore_layout_styling) thead th:not(:last-child)',
        (
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#495057', False),
        ),
    ),
    (
        '.o_table_boxed table:not(.o_ignore_layout_styling) thead th, .o_table_boxed-rounded table:not(.o_ignore_layout_styling) thead th',
        (
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#212529', False),
        ),
    ),
    (
        '.o_table_boxed table:not(.o_ignore_layout_styling) tbody tr:not(:last-child) td, .o_table_boxed-rounded table:not(.o_ignore_layout_styling) tbody tr:not(:last-child) td',
        (
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#ced4da', False),
        ),
    ),
    (
        '.o_table_boxed table:not(.o_ignore_layout_styling) tbody td:not(:last-child), .o_table_boxed-rounded table:not(.o_ignore_layout_styling) tbody td:not(:last-child)',
        (
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#ced4da', False),
        ),
    ),
    (
        '.o_table_boxed table:not(.o_ignore_layout_styling) tbody.o_line_section td, .o_table_boxed table:not(.o_ignore_layout_styling) tbody.o_line_note td, .o_table_boxed table:not(.o_ignore_layout_styling) tbody.is-subtotal td, .o_table_boxed-rounded table:not(.o_ignore_layout_styling) tbody.o_line_section td, .o_table_boxed-rounded table:not(.o_ignore_layout_styling) tbody.o_line_note td, .o_table_boxed-rounded table:not(.o_ignore_layout_styling) tbody.is-subtotal td',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#495057', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#495057', False),
        ),
    ),
    (
        '.o_table_boxed .o_total_table:not(.o_ignore_layout_styling) td, .o_table_boxed-rounded .o_total_table:not(.o_ignore_layout_styling) td',
        (
            ('border-right-width', 'medium', False),
            ('border-right-style', 'none', False),
        ),
    ),
    (
        '.o_table_boxed-rounded table:not(.o_ignore_layout_styling) th',
        (
            ('border-top-color', '#dee2e6', True),
            ('border-right-color', '#dee2e6', True),
            ('border-bottom-color', '#dee2e6', True),
            ('border-left-color', '#dee2e6', True),
        ),
    ),
    (
        '.o_report_layout_bubble #informations',
        (
            ('border-top-width', '2px', False),
            ('border-top-style', 'solid', False),
            ('border-right-width', '2px', False),
            ('border-right-style', 'solid', False),
            ('border-bottom-width', '2px', False),
            ('border-bottom-style', 'solid', False),
            ('border-left-width', '2px', False),
            ('border-left-style', 'solid', False),
        ),
    ),
    (
        '.o_table tr',
        (
            ('border-top-color', '#dee2e6', False),
            ('border-right-color', '#dee2e6', False),
            ('border-bottom-color', '#dee2e6', False),
            ('border-left-color', '#dee2e6', False),
        ),
    ),
    (
        '.table-bordered > :not(caption) > *',
        (
            ('border-top-width', '1px', False),
            ('border-right-width', '0', False),
            ('border-bottom-width', '1px', False),
            ('border-left-width', '0', False),
        ),
    ),
    (
        '.table-bordered > :not(caption) > * > *',
        (
            ('border-top-width', '0', False),
            ('border-right-width', '1px', False),
            ('border-bottom-width', '0', False),
            ('border-left-width', '1px', False),
        ),
    ),
    (
        'pre',
        (
            ('border-top-width', '1px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', '#212529', False),
            ('border-right-width', '1px', False),
            ('border-right-style', 'solid', False),
            ('border-right-color', '#212529', False),
            ('border-bottom-width', '1px', False),
            ('border-bottom-style', 'solid', False),
            ('border-bottom-color', '#212529', False),
            ('border-left-width', '1px', False),
            ('border-left-style', 'solid', False),
            ('border-left-color', '#212529', False),
        ),
    ),
    (
        '.o_cc1 a.list-group-item.active, .o_colored_level .o_cc1 a.list-group-item.active',
        (
            ('border-top-color', '#71639e', False),
            ('border-right-color', '#71639e', False),
            ('border-bottom-color', '#71639e', False),
            ('border-left-color', '#71639e', False),
        ),
    ),
    (
        '.o_cc2 a.list-group-item.active, .o_colored_level .o_cc2 a.list-group-item.active',
        (
            ('border-top-color', '#71639e', False),
            ('border-right-color', '#71639e', False),
            ('border-bottom-color', '#71639e', False),
            ('border-left-color', '#71639e', False),
        ),
    ),
    (
        '.o_cc3 a.list-group-item.active, .o_colored_level .o_cc3 a.list-group-item.active',
        (
            ('border-top-color', '#71639e', False),
            ('border-right-color', '#71639e', False),
            ('border-bottom-color', '#71639e', False),
            ('border-left-color', '#71639e', False),
        ),
    ),
    (
        '.o_cc4 a.list-group-item.active, .o_colored_level .o_cc4 a.list-group-item.active',
        (
            ('border-top-color', '#1B1319', False),
            ('border-right-color', '#1B1319', False),
            ('border-bottom-color', '#1B1319', False),
            ('border-left-color', '#1B1319', False),
        ),
    ),
    (
        '.o_cc5 a.list-group-item.active, .o_colored_level .o_cc5 a.list-group-item.active',
        (
            ('border-top-color', '#71639e', False),
            ('border-right-color', '#71639e', False),
            ('border-bottom-color', '#71639e', False),
            ('border-left-color', '#71639e', False),
        ),
    ),
    (
        '.ui-autocomplete .ui-menu-item > .ui-state-active',
        (
            ('border-top-width', 'medium', False),
            ('border-top-style', 'none', False),
            ('border-right-width', 'medium', False),
            ('border-right-style', 'none', False),
            ('border-bottom-width', 'medium', False),
            ('border-bottom-style', 'none', False),
            ('border-left-width', 'medium', False),
            ('border-left-style', 'none', False),
        ),
    ),
    (
        '#qrcode_odoo_logo',
        (
            ('border-top-color', 'white', True),
            ('border-right-color', 'white', True),
            ('border-bottom-color', 'white', True),
            ('border-left-color', 'white', True),
        ),
    ),
    (
        '.o_report_reception .btn.btn-primary',
        (
            ('border-top-color', '#71639e', False),
            ('border-right-color', '#71639e', False),
            ('border-bottom-color', '#71639e', False),
            ('border-left-color', '#71639e', False),
        ),
    ),
    (
        '.o_report_stock_rule .table > :not(:first-child)',
        (
            ('border-top-width', '2px', False),
            ('border-top-style', 'solid', False),
            ('border-top-color', 'currentcolor', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_symbol_cell',
        (
            ('border-top-width', 'medium', True),
            ('border-top-style', 'none', True),
            ('border-right-width', 'medium', True),
            ('border-right-style', 'none', True),
            ('border-bottom-width', 'medium', True),
            ('border-bottom-style', 'none', True),
            ('border-left-width', 'medium', True),
            ('border-left-style', 'none', True),
        ),
    ),
)

#: What kind of box an element makes, under its own CSS name.
#:
#: Derived by property, so the slice is complete by construction: block,
#: inline, inline-block, none, grid and both legacy box spellings, whatever
#: selector states them.
#:
#: Asking a partial slice is how `.d-block` came to be invisible.
#: `INLINE_LEVEL_RULES` keeps only rules whose display is an inline spelling,
#: so a rule that turns an inline element *into* a block was in no slice at
#: all -- and `<span class="d-block">` still looked like an inline box to the
#: walk that finds which block owns a line.
#:
#: anything picks a winner. The compatibility display vocabulary
#: has no FLEX, INLINE_FLEX or GRID, so Bootstrap's `.d-flex` survives as
#: `-webkit-box` and `.d-inline-flex` as `-webkit-inline-box` -- which is
#: inline-level, and is lost if the modern spelling in the same rule is
#: allowed to win. `.d-grid` survives as nothing at all.
#:
#: It does not carry the UA default: a bare `<span>` has no rule and is
#: inline because HTML says so. `_ELEMENTS` is that half.
#:
#: Derived by `tools/derive_layout_rules.py`, 233 rules.
DISPLAY_RULES = (
    (
        'article, aside, dialog, figure, footer, header, hgroup, nav, section, blockquote',
        (
            ('display', 'block', False),
        ),
    ),
    (
        'hr',
        (
            ('display', 'block', False),
        ),
    ),
    (
        'pre',
        (
            ('display', 'block', False),
        ),
    ),
    (
        'label',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        '[list]:not([type="date"]):not([type="datetime-local"]):not([type="month"]):not([type="week"]):not([type="time"])::-webkit-calendar-picker-indicator',
        (
            ('display', 'none', True),
        ),
    ),
    (
        'output',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        'summary',
        (
            ('display', 'list-item', False),
        ),
    ),
    (
        '[hidden]',
        (
            ('display', 'none', True),
        ),
    ),
    (
        '.list-inline-item',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        '.figure',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        '.form-control',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.form-control::-webkit-datetime-edit',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.form-control-plaintext',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.form-select',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.form-check',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.form-check-inline',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        '.valid-feedback',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.valid-tooltip',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.was-validated :valid ~ .valid-feedback, .was-validated :valid ~ .valid-tooltip, .is-valid ~ .valid-feedback, .is-valid ~ .valid-tooltip',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.invalid-feedback',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.invalid-tooltip',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.was-validated :invalid ~ .invalid-feedback, .was-validated :invalid ~ .invalid-tooltip, .is-invalid ~ .invalid-feedback, .is-invalid ~ .invalid-tooltip',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.btn',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        '.collapse:not(.show)',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.dropdown-menu',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.dropdown-item',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.dropdown-menu.show',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.dropdown-header',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.dropdown-item-text',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.nav-link',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.tab-content > .tab-pane',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.tab-content > .active',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.navbar-toggler-icon',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        '.navbar-expand-sm .navbar-toggler',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.navbar-expand-sm .offcanvas .offcanvas-header',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.navbar-expand-md .navbar-toggler',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.navbar-expand-md .offcanvas .offcanvas-header',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.navbar-expand-lg .navbar-toggler',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.navbar-expand-lg .offcanvas .offcanvas-header',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.navbar-expand-xl .navbar-toggler',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.navbar-expand-xl .offcanvas .offcanvas-header',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.navbar-expand-xxl .navbar-toggler',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.navbar-expand-xxl .offcanvas .offcanvas-header',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.navbar-expand .navbar-toggler',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.navbar-expand .offcanvas .offcanvas-header',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.page-link',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.badge',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        '.badge:empty',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.list-group-item',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.toast:not(.show)',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.modal',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.tooltip',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.tooltip .tooltip-arrow',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.popover',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.popover .popover-arrow',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.popover-header:empty',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.carousel-item',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.carousel-item.active, .carousel-item-next, .carousel-item-prev',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.carousel-control-prev-icon, .carousel-control-next-icon',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        '.spinner-grow, .spinner-border',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        '.offcanvas-sm .offcanvas-header',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.offcanvas-md .offcanvas-header',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.offcanvas-lg .offcanvas-header',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.offcanvas-xl .offcanvas-header',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.offcanvas-xxl .offcanvas-header',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.placeholder',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        '.vr',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        '.d-empty-none:empty',
        (
            ('display', 'none', True),
        ),
    ),
    (
        '.d-inline',
        (
            ('display', 'inline', True),
        ),
    ),
    (
        '.d-inline-block',
        (
            ('display', 'inline-block', True),
        ),
    ),
    (
        '.d-block',
        (
            ('display', 'block', True),
        ),
    ),
    (
        '.d-table',
        (
            ('display', 'table', True),
        ),
    ),
    (
        '.d-table-row',
        (
            ('display', 'table-row', True),
        ),
    ),
    (
        '.d-table-cell',
        (
            ('display', 'table-cell', True),
        ),
    ),
    (
        '.d-none',
        (
            ('display', 'none', True),
        ),
    ),
    (
        '.d-sm-inline',
        (
            ('display', 'inline', True),
        ),
    ),
    (
        '.d-sm-inline-block',
        (
            ('display', 'inline-block', True),
        ),
    ),
    (
        '.d-sm-block',
        (
            ('display', 'block', True),
        ),
    ),
    (
        '.d-sm-table',
        (
            ('display', 'table', True),
        ),
    ),
    (
        '.d-sm-table-row',
        (
            ('display', 'table-row', True),
        ),
    ),
    (
        '.d-sm-table-cell',
        (
            ('display', 'table-cell', True),
        ),
    ),
    (
        '.d-sm-none',
        (
            ('display', 'none', True),
        ),
    ),
    (
        '.d-md-inline',
        (
            ('display', 'inline', True),
        ),
    ),
    (
        '.d-md-inline-block',
        (
            ('display', 'inline-block', True),
        ),
    ),
    (
        '.d-md-block',
        (
            ('display', 'block', True),
        ),
    ),
    (
        '.d-md-table',
        (
            ('display', 'table', True),
        ),
    ),
    (
        '.d-md-table-row',
        (
            ('display', 'table-row', True),
        ),
    ),
    (
        '.d-md-table-cell',
        (
            ('display', 'table-cell', True),
        ),
    ),
    (
        '.d-md-none',
        (
            ('display', 'none', True),
        ),
    ),
    (
        '.d-lg-inline',
        (
            ('display', 'inline', True),
        ),
    ),
    (
        '.d-lg-inline-block',
        (
            ('display', 'inline-block', True),
        ),
    ),
    (
        '.d-lg-block',
        (
            ('display', 'block', True),
        ),
    ),
    (
        '.d-lg-table',
        (
            ('display', 'table', True),
        ),
    ),
    (
        '.d-lg-table-row',
        (
            ('display', 'table-row', True),
        ),
    ),
    (
        '.d-lg-table-cell',
        (
            ('display', 'table-cell', True),
        ),
    ),
    (
        '.d-lg-none',
        (
            ('display', 'none', True),
        ),
    ),
    (
        '.d-xl-inline',
        (
            ('display', 'inline', True),
        ),
    ),
    (
        '.d-xl-inline-block',
        (
            ('display', 'inline-block', True),
        ),
    ),
    (
        '.d-xl-block',
        (
            ('display', 'block', True),
        ),
    ),
    (
        '.d-xl-table',
        (
            ('display', 'table', True),
        ),
    ),
    (
        '.d-xl-table-row',
        (
            ('display', 'table-row', True),
        ),
    ),
    (
        '.d-xl-table-cell',
        (
            ('display', 'table-cell', True),
        ),
    ),
    (
        '.d-xl-none',
        (
            ('display', 'none', True),
        ),
    ),
    (
        '.d-xxl-inline',
        (
            ('display', 'inline', True),
        ),
    ),
    (
        '.d-xxl-inline-block',
        (
            ('display', 'inline-block', True),
        ),
    ),
    (
        '.d-xxl-block',
        (
            ('display', 'block', True),
        ),
    ),
    (
        '.d-xxl-table',
        (
            ('display', 'table', True),
        ),
    ),
    (
        '.d-xxl-table-row',
        (
            ('display', 'table-row', True),
        ),
    ),
    (
        '.d-xxl-table-cell',
        (
            ('display', 'table-cell', True),
        ),
    ),
    (
        '.d-xxl-none',
        (
            ('display', 'none', True),
        ),
    ),
    (
        '.d-print-inline',
        (
            ('display', 'inline', True),
        ),
    ),
    (
        '.d-print-inline-block',
        (
            ('display', 'inline-block', True),
        ),
    ),
    (
        '.d-print-block',
        (
            ('display', 'block', True),
        ),
    ),
    (
        '.d-print-table',
        (
            ('display', 'table', True),
        ),
    ),
    (
        '.d-print-table-row',
        (
            ('display', 'table-row', True),
        ),
    ),
    (
        '.d-print-table-cell',
        (
            ('display', 'table-cell', True),
        ),
    ),
    (
        '.d-print-none',
        (
            ('display', 'none', True),
        ),
    ),
    (
        '.modal-backdrop',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.openerp .oe_form .oe_styling_v8 .oe_websiteonly',
        (
            ('display', 'none', False),
        ),
    ),
    (
        ".oe_row.oe_flex [class*='oe_span']",
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        '.oe_hidden',
        (
            ('display', 'none', True),
        ),
    ),
    (
        '.oe_button',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        '.oe_quote .oe_q, .oe_quote q',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.oe_quote cite',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.oe_picture',
        (
            ('display', 'block', False),
        ),
    ),
    (
        'div.oe_demo span.oe_demo_play',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.oe_row_tab',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        '.fa',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        '.fa-stack',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        '.oi',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        '.d-print-none',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.report-wrapping-flexbox',
        (
            ('display', 'block', True),
        ),
    ),
    (
        'span.o_force_ltr',
        (
            ('display', 'inline', False),
        ),
    ),
    (
        'li.oe-nested',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.o_portal_address span[itemprop="telephone"]',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        'li.oe-nested',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.oe-tabs',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        '.css_non_editable_mode_hidden',
        (
            ('display', 'none', True),
        ),
    ),
    (
        '.editor_enable .css_editable_mode_hidden',
        (
            ('display', 'none', True),
        ),
    ),
    (
        'img.o_we_custom_image',
        (
            ('display', 'inline-block', False),
        ),
    ),
    (
        'img.ms-auto, img.mx-auto',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.fa.mx-auto',
        (
            ('display', 'block', False),
        ),
    ),
    (
        'div.media_iframe_video .css_editable_mode_display',
        (
            ('display', 'none', False),
        ),
    ),
    (
        '.text-gradient .fa',
        (
            ('display', 'inherit', False),
        ),
    ),
    (
        '.o_report_reception thead',
        (
            ('display', 'table-row-group', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_location_header > a',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_rule_cell > a',
        (
            ('display', 'block', False),
        ),
    ),
    (
        '.o_stock_report_header_row',
        (
            ('display', '-webkit-box', False),
        ),
    ),
    (
        '[name="so_total_summary"] div#total',
        (
            ('display', 'table', False),
        ),
    ),
)


#: Whether an element paints at all, under its own CSS name -- derived by
#: property so the slice is complete by construction, the same shape
#: `FLOAT_RULES`/`CLEAR_RULES`/`BORDER_STYLE_RULES` already have.
#:
#: `var()`-valued declarations are kept unresolved rather than dropped:
#: `.btn:disabled` states `var(--btn-disabled-opacity)`, which this slice
#: preserves as text for the runtime to refuse explicitly rather than guess.
#:
#: (all `folder`-layout, all the same hidden duplicate `<h3
#: class="opacity-0">` title Odoo repeats for that layout's own visible
#: title art); a real partial value, `hr { opacity: 0.25 }`, on two more.
#: Every other rule here -- `:disabled`, `.fade`, `.tooltip`, `.modal-*`,
#: `.carousel-*`, the `.opacity-25/50/75/100` utility scale, `.oe_hidden`,
#: reach; kept because a selector slice states what the bundle says, not
#:
#: Derived by `tools/derive_layout_rules.py`, 42 rules.
OPACITY_RULES = (
    (
        'hr',
        (
            ('opacity', '0.25', False),
        ),
    ),
    (
        'select:disabled',
        (
            ('opacity', '1', False),
        ),
    ),
    (
        '.form-control::placeholder',
        (
            ('opacity', '1', False),
        ),
    ),
    (
        '.form-control:disabled',
        (
            ('opacity', '1', False),
        ),
    ),
    (
        '.form-check-input:disabled',
        (
            ('opacity', '0.5', False),
        ),
    ),
    (
        '.form-check-input[disabled] ~ .form-check-label, .form-check-input:disabled ~ .form-check-label',
        (
            ('opacity', '0.5', False),
        ),
    ),
    (
        '.btn-check[disabled] + .btn, .btn-check:disabled + .btn',
        (
            ('opacity', '0.5', False),
        ),
    ),
    (
        '.btn:disabled, .btn.disabled, fieldset:disabled .btn',
        (
            ('opacity', 'var(--btn-disabled-opacity)', False),
        ),
    ),
    (
        '.fade:not(.show)',
        (
            ('opacity', '0', False),
        ),
    ),
    (
        '.dropdown-divider',
        (
            ('opacity', '1', False),
        ),
    ),
    (
        '.btn-close',
        (
            ('opacity', 'var(--btn-close-opacity)', False),
        ),
    ),
    (
        '.btn-close:disabled, .btn-close.disabled',
        (
            ('opacity', 'var(--btn-close-disabled-opacity)', False),
        ),
    ),
    (
        '.toast.showing',
        (
            ('opacity', '0', False),
        ),
    ),
    (
        '.modal-backdrop.fade',
        (
            ('opacity', '0', False),
        ),
    ),
    (
        '.modal-backdrop.show',
        (
            ('opacity', 'var(--backdrop-opacity)', False),
        ),
    ),
    (
        '.tooltip',
        (
            ('opacity', '0', False),
        ),
    ),
    (
        '.tooltip.show',
        (
            ('opacity', 'var(--tooltip-opacity)', False),
        ),
    ),
    (
        '.carousel-fade .carousel-item',
        (
            ('opacity', '0', False),
        ),
    ),
    (
        '.carousel-fade .carousel-item.active, .carousel-fade .carousel-item-next.carousel-item-start, .carousel-fade .carousel-item-prev.carousel-item-end',
        (
            ('opacity', '1', False),
        ),
    ),
    (
        '.carousel-fade .active.carousel-item-start, .carousel-fade .active.carousel-item-end',
        (
            ('opacity', '0', False),
        ),
    ),
    (
        '.carousel-control-prev, .carousel-control-next',
        (
            ('opacity', '0.5', False),
        ),
    ),
    (
        '.carousel-indicators [data-bs-target]',
        (
            ('opacity', '0.5', False),
        ),
    ),
    (
        '.carousel-indicators .active',
        (
            ('opacity', '1', False),
        ),
    ),
    (
        '.spinner-grow',
        (
            ('opacity', '0', False),
        ),
    ),
    (
        '.offcanvas-backdrop.fade',
        (
            ('opacity', '0', False),
        ),
    ),
    (
        '.offcanvas-backdrop.show',
        (
            ('opacity', '0.5', False),
        ),
    ),
    (
        '.placeholder',
        (
            ('opacity', '0.5', False),
        ),
    ),
    (
        '.vr',
        (
            ('opacity', '0.25', False),
        ),
    ),
    (
        '.opacity-0',
        (
            ('opacity', '0', True),
        ),
    ),
    (
        '.opacity-25',
        (
            ('opacity', '0.25', True),
        ),
    ),
    (
        '.opacity-50',
        (
            ('opacity', '0.5', True),
        ),
    ),
    (
        '.opacity-75',
        (
            ('opacity', '0.75', True),
        ),
    ),
    (
        '.opacity-100',
        (
            ('opacity', '1', True),
        ),
    ),
    (
        '.opacity-disabled',
        (
            ('opacity', '0.5', True),
        ),
    ),
    (
        '.opacity-muted',
        (
            ('opacity', '0.76', True),
        ),
    ),
    (
        '.oe_hidden',
        (
            ('opacity', '0', True),
        ),
    ),
    (
        '.oe_transparent',
        (
            ('opacity', '0', True),
        ),
    ),
    (
        '.oe_styling_v8 h3.oe_slogan',
        (
            ('opacity', '0.5', False),
        ),
    ),
    (
        'div.oe_demo div.oe_demo_footer',
        (
            ('opacity', '0.85', False),
        ),
    ),
    (
        'ul.o_checklist > li.o_checked:not(.o_checked_has_nested_list)',
        (
            ('opacity', '0.5', False),
        ),
    ),
    (
        'ul.o_checklist > li.o_checked.o_checked_has_nested_list > :not(ul, ol)',
        (
            ('opacity', '0.5', False),
        ),
    ),
)


PADDING_STYLE_RULES = (
    (
        'html, body, div, span, applet, object, iframe, h1, h2, h3, h4, h5, h6, p, blockquote, pre, a, abbr, acronym, address, big, cite, code, del, dfn, em, font, img, ins, kbd, q, s, samp, small, strike, strong, sub, sup, tt, var, b, i, center, dl, dt, dd, ol, ul, li, fieldset, form, label, legend, table, caption, tbody, tfoot, thead, tr, th, td, article, aside, audio, canvas, details, figcaption, figure, footer, header, hgroup, mark, menu, meter, nav, output, progress, section, summary, time, video',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        'ul',
        (
            ('padding-left', '40px', False),
        ),
    ),
    (
        'hr',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        'input[type="submit"], input[type="button"], button',
        (
            ('padding-top', '0', True),
            ('padding-right', '0', True),
            ('padding-bottom', '0', True),
            ('padding-left', '0', True),
        ),
    ),
    (
        'ol, ul',
        (
            ('padding-left', '2rem', False),
        ),
    ),
    (
        'mark, .mark',
        (
            ('padding-top', '0.1875em', False),
            ('padding-right', '0.1875em', False),
            ('padding-bottom', '0.1875em', False),
            ('padding-left', '0.1875em', False),
        ),
    ),
    (
        'kbd',
        (
            ('padding-top', '0.1875rem', False),
            ('padding-right', '0.375rem', False),
            ('padding-bottom', '0.1875rem', False),
            ('padding-left', '0.375rem', False),
        ),
    ),
    (
        'kbd kbd',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        'caption',
        (
            ('padding-top', '0.5rem', False),
            ('padding-bottom', '0.5rem', False),
        ),
    ),
    (
        '::-moz-focus-inner',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        'fieldset',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        'legend',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '::-webkit-datetime-edit-fields-wrapper, ::-webkit-datetime-edit-text, ::-webkit-datetime-edit-minute, ::-webkit-datetime-edit-hour-field, ::-webkit-datetime-edit-day-field, ::-webkit-datetime-edit-month-field, ::-webkit-datetime-edit-year-field',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '::-webkit-color-swatch-wrapper',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.list-unstyled',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.list-inline',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.img-thumbnail',
        (
            ('padding-top', '0.25rem', False),
            ('padding-right', '0.25rem', False),
            ('padding-bottom', '0.25rem', False),
            ('padding-left', '0.25rem', False),
        ),
    ),
    (
        '.container, .o_container_small, .container-fluid, .container-xxl, .container-xl, .container-lg, .container-md, .container-sm',
        (
            ('padding-right', 'calc(var(--gutter-x) * .5)', False),
            ('padding-left', 'calc(var(--gutter-x) * .5)', False),
        ),
    ),
    (
        '.row > *',
        (
            ('padding-right', 'calc(var(--gutter-x) * .5)', False),
            ('padding-left', 'calc(var(--gutter-x) * .5)', False),
        ),
    ),
    (
        '.table > :not(caption) > * > *',
        (
            ('padding-top', '0.5rem', False),
            ('padding-right', '0.5rem', False),
            ('padding-bottom', '0.5rem', False),
            ('padding-left', '0.5rem', False),
        ),
    ),
    (
        '.table-sm > :not(caption) > * > *',
        (
            ('padding-top', '0.25rem', False),
            ('padding-right', '0.25rem', False),
            ('padding-bottom', '0.25rem', False),
            ('padding-left', '0.25rem', False),
        ),
    ),
    (
        '.col-form-label',
        (
            ('padding-top', 'calc(0.3125rem + var(--border-width))', False),
            ('padding-bottom', 'calc(0.3125rem + var(--border-width))', False),
        ),
    ),
    (
        '.col-form-label-lg',
        (
            ('padding-top', 'calc(0.375rem + var(--border-width))', False),
            ('padding-bottom', 'calc(0.375rem + var(--border-width))', False),
        ),
    ),
    (
        '.col-form-label-sm',
        (
            ('padding-top', 'calc(0.1875rem + var(--border-width))', False),
            ('padding-bottom', 'calc(0.1875rem + var(--border-width))', False),
        ),
    ),
    (
        '.form-control',
        (
            ('padding-top', '0.3125rem', False),
            ('padding-right', '0.625rem', False),
            ('padding-bottom', '0.3125rem', False),
            ('padding-left', '0.625rem', False),
        ),
    ),
    (
        '.form-control::-webkit-datetime-edit',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.form-control::file-selector-button',
        (
            ('padding-top', '0.3125rem', False),
            ('padding-right', '0.625rem', False),
            ('padding-bottom', '0.3125rem', False),
            ('padding-left', '0.625rem', False),
        ),
    ),
    (
        '.form-control-plaintext',
        (
            ('padding-top', '0.3125rem', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0.3125rem', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.form-control-plaintext.form-control-sm, .form-control-plaintext.form-control-lg',
        (
            ('padding-right', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.form-control-sm',
        (
            ('padding-top', '0.1875rem', False),
            ('padding-right', '0.5rem', False),
            ('padding-bottom', '0.1875rem', False),
            ('padding-left', '0.5rem', False),
        ),
    ),
    (
        '.form-control-sm::file-selector-button',
        (
            ('padding-top', '0.1875rem', False),
            ('padding-right', '0.5rem', False),
            ('padding-bottom', '0.1875rem', False),
            ('padding-left', '0.5rem', False),
        ),
    ),
    (
        '.form-control-lg',
        (
            ('padding-top', '0.375rem', False),
            ('padding-right', '0.75rem', False),
            ('padding-bottom', '0.375rem', False),
            ('padding-left', '0.75rem', False),
        ),
    ),
    (
        '.form-control-lg::file-selector-button',
        (
            ('padding-top', '0.375rem', False),
            ('padding-right', '0.75rem', False),
            ('padding-bottom', '0.375rem', False),
            ('padding-left', '0.75rem', False),
        ),
    ),
    (
        '.form-control-color',
        (
            ('padding-top', '0.3125rem', False),
            ('padding-right', '0.3125rem', False),
            ('padding-bottom', '0.3125rem', False),
            ('padding-left', '0.3125rem', False),
        ),
    ),
    (
        '.form-select',
        (
            ('padding-top', '0.3125rem', False),
            ('padding-right', '1.875rem', False),
            ('padding-bottom', '0.3125rem', False),
            ('padding-left', '0.625rem', False),
        ),
    ),
    (
        '.form-select[multiple], .form-select[size]:not([size="1"])',
        (
            ('padding-right', '0.625rem', False),
        ),
    ),
    (
        '.form-select-sm',
        (
            ('padding-top', '0.1875rem', False),
            ('padding-bottom', '0.1875rem', False),
            ('padding-left', '0.5rem', False),
        ),
    ),
    (
        '.form-select-lg',
        (
            ('padding-top', '0.375rem', False),
            ('padding-bottom', '0.375rem', False),
            ('padding-left', '0.75rem', False),
        ),
    ),
    (
        '.form-check',
        (
            ('padding-left', '1.5em', False),
        ),
    ),
    (
        '.form-check-reverse',
        (
            ('padding-right', '1.5em', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.form-switch',
        (
            ('padding-left', '2.5em', False),
        ),
    ),
    (
        '.form-switch.form-check-reverse',
        (
            ('padding-right', '2.5em', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.form-range',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.form-floating > label',
        (
            ('padding-top', '1rem', False),
            ('padding-right', '0.625rem', False),
            ('padding-bottom', '1rem', False),
            ('padding-left', '0.625rem', False),
        ),
    ),
    (
        '.form-floating > .form-control, .form-floating > .form-control-plaintext',
        (
            ('padding-top', '1rem', False),
            ('padding-right', '0.625rem', False),
            ('padding-bottom', '1rem', False),
            ('padding-left', '0.625rem', False),
        ),
    ),
    (
        '.form-floating > .form-control:-webkit-autofill, .form-floating > .form-control-plaintext:-webkit-autofill',
        (
            ('padding-top', '1.625rem', False),
            ('padding-bottom', '0.625rem', False),
        ),
    ),
    (
        '.form-floating > .form-select',
        (
            ('padding-top', '1.625rem', False),
            ('padding-bottom', '0.625rem', False),
        ),
    ),
    (
        '.input-group-text',
        (
            ('padding-top', '0.3125rem', False),
            ('padding-right', '0.625rem', False),
            ('padding-bottom', '0.3125rem', False),
            ('padding-left', '0.625rem', False),
        ),
    ),
    (
        '.input-group-lg > .form-control, .input-group-lg > .form-select, .input-group-lg > .input-group-text, .input-group-lg > .btn',
        (
            ('padding-top', '0.375rem', False),
            ('padding-right', '0.75rem', False),
            ('padding-bottom', '0.375rem', False),
            ('padding-left', '0.75rem', False),
        ),
    ),
    (
        '.input-group-sm > .form-control, .input-group-sm > .form-select, .input-group-sm > .input-group-text, .input-group-sm > .btn',
        (
            ('padding-top', '0.1875rem', False),
            ('padding-right', '0.5rem', False),
            ('padding-bottom', '0.1875rem', False),
            ('padding-left', '0.5rem', False),
        ),
    ),
    (
        '.input-group-lg > .form-select, .input-group-sm > .form-select',
        (
            ('padding-right', '2.5rem', False),
        ),
    ),
    (
        '.valid-tooltip',
        (
            ('padding-top', '4px', False),
            ('padding-right', '8px', False),
            ('padding-bottom', '4px', False),
            ('padding-left', '8px', False),
        ),
    ),
    (
        '.was-validated .form-control:valid, .form-control.is-valid',
        (
            ('padding-right', 'calc(1.5em + 0.625rem)', False),
        ),
    ),
    (
        '.was-validated textarea.form-control:valid, textarea.form-control.is-valid',
        (
            ('padding-right', 'calc(1.5em + 0.625rem)', False),
        ),
    ),
    (
        '.was-validated .form-select:valid:not([multiple]):not([size]), .was-validated .form-select:valid:not([multiple])[size="1"], .form-select.is-valid:not([multiple]):not([size]), .form-select.is-valid:not([multiple])[size="1"]',
        (
            ('padding-right', '3.4375rem', False),
        ),
    ),
    (
        '.invalid-tooltip',
        (
            ('padding-top', '4px', False),
            ('padding-right', '8px', False),
            ('padding-bottom', '4px', False),
            ('padding-left', '8px', False),
        ),
    ),
    (
        '.was-validated .form-control:invalid, .form-control.is-invalid',
        (
            ('padding-right', 'calc(1.5em + 0.625rem)', False),
        ),
    ),
    (
        '.was-validated textarea.form-control:invalid, textarea.form-control.is-invalid',
        (
            ('padding-right', 'calc(1.5em + 0.625rem)', False),
        ),
    ),
    (
        '.was-validated .form-select:invalid:not([multiple]):not([size]), .was-validated .form-select:invalid:not([multiple])[size="1"], .form-select.is-invalid:not([multiple]):not([size]), .form-select.is-invalid:not([multiple])[size="1"]',
        (
            ('padding-right', '3.4375rem', False),
        ),
    ),
    (
        '.btn',
        (
            ('padding-top', 'var(--btn-padding-y)', False),
            ('padding-right', 'var(--btn-padding-x)', False),
            ('padding-bottom', 'var(--btn-padding-y)', False),
            ('padding-left', 'var(--btn-padding-x)', False),
        ),
    ),
    (
        '.dropdown-menu',
        (
            ('padding-top', 'var(--dropdown-padding-y)', False),
            ('padding-right', 'var(--dropdown-padding-x)', False),
            ('padding-bottom', 'var(--dropdown-padding-y)', False),
            ('padding-left', 'var(--dropdown-padding-x)', False),
        ),
    ),
    (
        '.dropdown-item',
        (
            ('padding-top', 'var(--dropdown-item-padding-y)', False),
            ('padding-right', 'var(--dropdown-item-padding-x)', False),
            ('padding-bottom', 'var(--dropdown-item-padding-y)', False),
            ('padding-left', 'var(--dropdown-item-padding-x)', False),
        ),
    ),
    (
        '.dropdown-header',
        (
            ('padding-top', 'var(--dropdown-header-padding-y)', False),
            ('padding-right', 'var(--dropdown-header-padding-x)', False),
            ('padding-bottom', 'var(--dropdown-header-padding-y)', False),
            ('padding-left', 'var(--dropdown-header-padding-x)', False),
        ),
    ),
    (
        '.dropdown-item-text',
        (
            ('padding-top', 'var(--dropdown-item-padding-y)', False),
            ('padding-right', 'var(--dropdown-item-padding-x)', False),
            ('padding-bottom', 'var(--dropdown-item-padding-y)', False),
            ('padding-left', 'var(--dropdown-item-padding-x)', False),
        ),
    ),
    (
        '.dropdown-toggle-split',
        (
            ('padding-right', '0.46875rem', False),
            ('padding-left', '0.46875rem', False),
        ),
    ),
    (
        '.btn-sm + .dropdown-toggle-split, .btn-group-sm > .btn + .dropdown-toggle-split',
        (
            ('padding-right', '0.375rem', False),
            ('padding-left', '0.375rem', False),
        ),
    ),
    (
        '.btn-lg + .dropdown-toggle-split, .btn-group-lg > .btn + .dropdown-toggle-split',
        (
            ('padding-right', '0.5625rem', False),
            ('padding-left', '0.5625rem', False),
        ),
    ),
    (
        '.nav',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.nav-link',
        (
            ('padding-top', 'var(--nav-link-padding-y)', False),
            ('padding-right', 'var(--nav-link-padding-x)', False),
            ('padding-bottom', 'var(--nav-link-padding-y)', False),
            ('padding-left', 'var(--nav-link-padding-x)', False),
        ),
    ),
    (
        '.nav-underline .nav-link',
        (
            ('padding-right', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.navbar',
        (
            ('padding-top', 'var(--navbar-padding-y)', False),
            ('padding-right', 'var(--navbar-padding-x)', False),
            ('padding-bottom', 'var(--navbar-padding-y)', False),
            ('padding-left', 'var(--navbar-padding-x)', False),
        ),
    ),
    (
        '.navbar-brand',
        (
            ('padding-top', 'var(--navbar-brand-padding-y)', False),
            ('padding-bottom', 'var(--navbar-brand-padding-y)', False),
        ),
    ),
    (
        '.navbar-nav',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.navbar-text',
        (
            ('padding-top', '0.5rem', False),
            ('padding-bottom', '0.5rem', False),
        ),
    ),
    (
        '.navbar-toggler',
        (
            ('padding-top', 'var(--navbar-toggler-padding-y)', False),
            ('padding-right', 'var(--navbar-toggler-padding-x)', False),
            ('padding-bottom', 'var(--navbar-toggler-padding-y)', False),
            ('padding-left', 'var(--navbar-toggler-padding-x)', False),
        ),
    ),
    (
        '.navbar-expand-sm .navbar-nav .nav-link',
        (
            ('padding-right', 'var(--navbar-nav-link-padding-x)', False),
            ('padding-left', 'var(--navbar-nav-link-padding-x)', False),
        ),
    ),
    (
        '.navbar-expand-sm .offcanvas .offcanvas-body',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.navbar-expand-md .navbar-nav .nav-link',
        (
            ('padding-right', 'var(--navbar-nav-link-padding-x)', False),
            ('padding-left', 'var(--navbar-nav-link-padding-x)', False),
        ),
    ),
    (
        '.navbar-expand-md .offcanvas .offcanvas-body',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.navbar-expand-lg .navbar-nav .nav-link',
        (
            ('padding-right', 'var(--navbar-nav-link-padding-x)', False),
            ('padding-left', 'var(--navbar-nav-link-padding-x)', False),
        ),
    ),
    (
        '.navbar-expand-lg .offcanvas .offcanvas-body',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.navbar-expand-xl .navbar-nav .nav-link',
        (
            ('padding-right', 'var(--navbar-nav-link-padding-x)', False),
            ('padding-left', 'var(--navbar-nav-link-padding-x)', False),
        ),
    ),
    (
        '.navbar-expand-xl .offcanvas .offcanvas-body',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.navbar-expand-xxl .navbar-nav .nav-link',
        (
            ('padding-right', 'var(--navbar-nav-link-padding-x)', False),
            ('padding-left', 'var(--navbar-nav-link-padding-x)', False),
        ),
    ),
    (
        '.navbar-expand-xxl .offcanvas .offcanvas-body',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.navbar-expand .navbar-nav .nav-link',
        (
            ('padding-right', 'var(--navbar-nav-link-padding-x)', False),
            ('padding-left', 'var(--navbar-nav-link-padding-x)', False),
        ),
    ),
    (
        '.navbar-expand .offcanvas .offcanvas-body',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.card-body',
        (
            ('padding-top', 'var(--card-spacer-y)', False),
            ('padding-right', 'var(--card-spacer-x)', False),
            ('padding-bottom', 'var(--card-spacer-y)', False),
            ('padding-left', 'var(--card-spacer-x)', False),
        ),
    ),
    (
        '.card-header',
        (
            ('padding-top', 'var(--card-cap-padding-y)', False),
            ('padding-right', 'var(--card-cap-padding-x)', False),
            ('padding-bottom', 'var(--card-cap-padding-y)', False),
            ('padding-left', 'var(--card-cap-padding-x)', False),
        ),
    ),
    (
        '.card-footer',
        (
            ('padding-top', 'var(--card-cap-padding-y)', False),
            ('padding-right', 'var(--card-cap-padding-x)', False),
            ('padding-bottom', 'var(--card-cap-padding-y)', False),
            ('padding-left', 'var(--card-cap-padding-x)', False),
        ),
    ),
    (
        '.card-img-overlay',
        (
            ('padding-top', 'var(--card-img-overlay-padding)', False),
            ('padding-right', 'var(--card-img-overlay-padding)', False),
            ('padding-bottom', 'var(--card-img-overlay-padding)', False),
            ('padding-left', 'var(--card-img-overlay-padding)', False),
        ),
    ),
    (
        '.accordion-button',
        (
            ('padding-top', 'var(--accordion-btn-padding-y)', False),
            ('padding-right', 'var(--accordion-btn-padding-x)', False),
            ('padding-bottom', 'var(--accordion-btn-padding-y)', False),
            ('padding-left', 'var(--accordion-btn-padding-x)', False),
        ),
    ),
    (
        '.accordion-body',
        (
            ('padding-top', 'var(--accordion-body-padding-y)', False),
            ('padding-right', 'var(--accordion-body-padding-x)', False),
            ('padding-bottom', 'var(--accordion-body-padding-y)', False),
            ('padding-left', 'var(--accordion-body-padding-x)', False),
        ),
    ),
    (
        '.breadcrumb',
        (
            ('padding-top', 'var(--breadcrumb-padding-y)', False),
            ('padding-right', 'var(--breadcrumb-padding-x)', False),
            ('padding-bottom', 'var(--breadcrumb-padding-y)', False),
            ('padding-left', 'var(--breadcrumb-padding-x)', False),
        ),
    ),
    (
        '.breadcrumb-item + .breadcrumb-item',
        (
            ('padding-left', 'var(--breadcrumb-item-padding-x)', False),
        ),
    ),
    (
        '.breadcrumb-item + .breadcrumb-item::before',
        (
            ('padding-right', 'var(--breadcrumb-item-padding-x)', False),
        ),
    ),
    (
        '.pagination',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.page-link',
        (
            ('padding-top', 'var(--pagination-padding-y)', False),
            ('padding-right', 'var(--pagination-padding-x)', False),
            ('padding-bottom', 'var(--pagination-padding-y)', False),
            ('padding-left', 'var(--pagination-padding-x)', False),
        ),
    ),
    (
        '.badge',
        (
            ('padding-top', 'var(--badge-padding-y)', False),
            ('padding-right', 'var(--badge-padding-x)', False),
            ('padding-bottom', 'var(--badge-padding-y)', False),
            ('padding-left', 'var(--badge-padding-x)', False),
        ),
    ),
    (
        '.alert',
        (
            ('padding-top', 'var(--alert-padding-y)', False),
            ('padding-right', 'var(--alert-padding-x)', False),
            ('padding-bottom', 'var(--alert-padding-y)', False),
            ('padding-left', 'var(--alert-padding-x)', False),
        ),
    ),
    (
        '.alert-dismissible',
        (
            ('padding-right', '48px', False),
        ),
    ),
    (
        '.alert-dismissible .btn-close',
        (
            ('padding-top', '20px', False),
            ('padding-right', '16px', False),
            ('padding-bottom', '20px', False),
            ('padding-left', '16px', False),
        ),
    ),
    (
        '.list-group',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.list-group-item',
        (
            ('padding-top', 'var(--list-group-item-padding-y)', False),
            ('padding-right', 'var(--list-group-item-padding-x)', False),
            ('padding-bottom', 'var(--list-group-item-padding-y)', False),
            ('padding-left', 'var(--list-group-item-padding-x)', False),
        ),
    ),
    (
        '.btn-close',
        (
            ('padding-top', '0.25em', False),
            ('padding-right', '0.25em', False),
            ('padding-bottom', '0.25em', False),
            ('padding-left', '0.25em', False),
        ),
    ),
    (
        '.toast-header',
        (
            ('padding-top', 'var(--toast-padding-y)', False),
            ('padding-right', 'var(--toast-padding-x)', False),
            ('padding-bottom', 'var(--toast-padding-y)', False),
            ('padding-left', 'var(--toast-padding-x)', False),
        ),
    ),
    (
        '.toast-body',
        (
            ('padding-top', 'var(--toast-padding-x)', False),
            ('padding-right', 'var(--toast-padding-x)', False),
            ('padding-bottom', 'var(--toast-padding-x)', False),
            ('padding-left', 'var(--toast-padding-x)', False),
        ),
    ),
    (
        '.modal-header',
        (
            ('padding-top', 'var(--modal-header-padding)', False),
            ('padding-right', 'var(--modal-header-padding)', False),
            ('padding-bottom', 'var(--modal-header-padding)', False),
            ('padding-left', 'var(--modal-header-padding)', False),
        ),
    ),
    (
        '.modal-header .btn-close',
        (
            ('padding-top', 'calc(var(--modal-header-padding-y) * .5)', False),
            ('padding-right', 'calc(var(--modal-header-padding-x) * .5)', False),
            ('padding-bottom', 'calc(var(--modal-header-padding-y) * .5)', False),
            ('padding-left', 'calc(var(--modal-header-padding-x) * .5)', False),
        ),
    ),
    (
        '.modal-body',
        (
            ('padding-top', 'var(--modal-padding)', False),
            ('padding-right', 'var(--modal-padding)', False),
            ('padding-bottom', 'var(--modal-padding)', False),
            ('padding-left', 'var(--modal-padding)', False),
        ),
    ),
    (
        '.modal-footer',
        (
            ('padding-top', 'calc(var(--modal-padding) - var(--modal-footer-gap) * .5)', False),
            ('padding-right', 'calc(var(--modal-padding) - var(--modal-footer-gap) * .5)', False),
            ('padding-bottom', 'calc(var(--modal-padding) - var(--modal-footer-gap) * .5)', False),
            ('padding-left', 'calc(var(--modal-padding) - var(--modal-footer-gap) * .5)', False),
        ),
    ),
    (
        '.tooltip-inner',
        (
            ('padding-top', 'var(--tooltip-padding-y)', False),
            ('padding-right', 'var(--tooltip-padding-x)', False),
            ('padding-bottom', 'var(--tooltip-padding-y)', False),
            ('padding-left', 'var(--tooltip-padding-x)', False),
        ),
    ),
    (
        '.popover-header',
        (
            ('padding-top', 'var(--popover-header-padding-y)', False),
            ('padding-right', 'var(--popover-header-padding-x)', False),
            ('padding-bottom', 'var(--popover-header-padding-y)', False),
            ('padding-left', 'var(--popover-header-padding-x)', False),
        ),
    ),
    (
        '.popover-body',
        (
            ('padding-top', 'var(--popover-body-padding-y)', False),
            ('padding-right', 'var(--popover-body-padding-x)', False),
            ('padding-bottom', 'var(--popover-body-padding-y)', False),
            ('padding-left', 'var(--popover-body-padding-x)', False),
        ),
    ),
    (
        '.carousel-control-prev, .carousel-control-next',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.carousel-indicators',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.carousel-indicators [data-bs-target]',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.carousel-caption',
        (
            ('padding-top', '1.25rem', False),
            ('padding-bottom', '1.25rem', False),
        ),
    ),
    (
        '.offcanvas-sm .offcanvas-body',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.offcanvas-md .offcanvas-body',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.offcanvas-lg .offcanvas-body',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.offcanvas-xl .offcanvas-body',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.offcanvas-xxl .offcanvas-body',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.offcanvas-header',
        (
            ('padding-top', 'var(--offcanvas-padding-y)', False),
            ('padding-right', 'var(--offcanvas-padding-x)', False),
            ('padding-bottom', 'var(--offcanvas-padding-y)', False),
            ('padding-left', 'var(--offcanvas-padding-x)', False),
        ),
    ),
    (
        '.offcanvas-header .btn-close',
        (
            ('padding-top', 'calc(var(--offcanvas-padding-y) * .5)', False),
            ('padding-right', 'calc(var(--offcanvas-padding-x) * .5)', False),
            ('padding-bottom', 'calc(var(--offcanvas-padding-y) * .5)', False),
            ('padding-left', 'calc(var(--offcanvas-padding-x) * .5)', False),
        ),
    ),
    (
        '.offcanvas-body',
        (
            ('padding-top', 'var(--offcanvas-padding-y)', False),
            ('padding-right', 'var(--offcanvas-padding-x)', False),
            ('padding-bottom', 'var(--offcanvas-padding-y)', False),
            ('padding-left', 'var(--offcanvas-padding-x)', False),
        ),
    ),
    (
        '.ratio::before',
        (
            ('padding-top', 'var(--aspect-ratio)', False),
        ),
    ),
    (
        '.p-0',
        (
            ('padding-top', '0', True),
            ('padding-right', '0', True),
            ('padding-bottom', '0', True),
            ('padding-left', '0', True),
        ),
    ),
    (
        '.p-1',
        (
            ('padding-top', '4px', True),
            ('padding-right', '4px', True),
            ('padding-bottom', '4px', True),
            ('padding-left', '4px', True),
        ),
    ),
    (
        '.p-2',
        (
            ('padding-top', '8px', True),
            ('padding-right', '8px', True),
            ('padding-bottom', '8px', True),
            ('padding-left', '8px', True),
        ),
    ),
    (
        '.p-3',
        (
            ('padding-top', '16px', True),
            ('padding-right', '16px', True),
            ('padding-bottom', '16px', True),
            ('padding-left', '16px', True),
        ),
    ),
    (
        '.p-4',
        (
            ('padding-top', '24px', True),
            ('padding-right', '24px', True),
            ('padding-bottom', '24px', True),
            ('padding-left', '24px', True),
        ),
    ),
    (
        '.p-5',
        (
            ('padding-top', '48px', True),
            ('padding-right', '48px', True),
            ('padding-bottom', '48px', True),
            ('padding-left', '48px', True),
        ),
    ),
    (
        '.px-0',
        (
            ('padding-right', '0', True),
            ('padding-left', '0', True),
        ),
    ),
    (
        '.px-1',
        (
            ('padding-right', '4px', True),
            ('padding-left', '4px', True),
        ),
    ),
    (
        '.px-2',
        (
            ('padding-right', '8px', True),
            ('padding-left', '8px', True),
        ),
    ),
    (
        '.px-3',
        (
            ('padding-right', '16px', True),
            ('padding-left', '16px', True),
        ),
    ),
    (
        '.px-4',
        (
            ('padding-right', '24px', True),
            ('padding-left', '24px', True),
        ),
    ),
    (
        '.px-5',
        (
            ('padding-right', '48px', True),
            ('padding-left', '48px', True),
        ),
    ),
    (
        '.py-0',
        (
            ('padding-top', '0', True),
            ('padding-bottom', '0', True),
        ),
    ),
    (
        '.py-1',
        (
            ('padding-top', '4px', True),
            ('padding-bottom', '4px', True),
        ),
    ),
    (
        '.py-2',
        (
            ('padding-top', '8px', True),
            ('padding-bottom', '8px', True),
        ),
    ),
    (
        '.py-3',
        (
            ('padding-top', '16px', True),
            ('padding-bottom', '16px', True),
        ),
    ),
    (
        '.py-4',
        (
            ('padding-top', '24px', True),
            ('padding-bottom', '24px', True),
        ),
    ),
    (
        '.py-5',
        (
            ('padding-top', '48px', True),
            ('padding-bottom', '48px', True),
        ),
    ),
    (
        '.pt-0',
        (
            ('padding-top', '0', True),
        ),
    ),
    (
        '.pt-1',
        (
            ('padding-top', '4px', True),
        ),
    ),
    (
        '.pt-2',
        (
            ('padding-top', '8px', True),
        ),
    ),
    (
        '.pt-3',
        (
            ('padding-top', '16px', True),
        ),
    ),
    (
        '.pt-4',
        (
            ('padding-top', '24px', True),
        ),
    ),
    (
        '.pt-5',
        (
            ('padding-top', '48px', True),
        ),
    ),
    (
        '.pe-0',
        (
            ('padding-right', '0', True),
        ),
    ),
    (
        '.pe-1',
        (
            ('padding-right', '4px', True),
        ),
    ),
    (
        '.pe-2',
        (
            ('padding-right', '8px', True),
        ),
    ),
    (
        '.pe-3',
        (
            ('padding-right', '16px', True),
        ),
    ),
    (
        '.pe-4',
        (
            ('padding-right', '24px', True),
        ),
    ),
    (
        '.pe-5',
        (
            ('padding-right', '48px', True),
        ),
    ),
    (
        '.pb-0',
        (
            ('padding-bottom', '0', True),
        ),
    ),
    (
        '.pb-1',
        (
            ('padding-bottom', '4px', True),
        ),
    ),
    (
        '.pb-2',
        (
            ('padding-bottom', '8px', True),
        ),
    ),
    (
        '.pb-3',
        (
            ('padding-bottom', '16px', True),
        ),
    ),
    (
        '.pb-4',
        (
            ('padding-bottom', '24px', True),
        ),
    ),
    (
        '.pb-5',
        (
            ('padding-bottom', '48px', True),
        ),
    ),
    (
        '.ps-0',
        (
            ('padding-left', '0', True),
        ),
    ),
    (
        '.ps-1',
        (
            ('padding-left', '4px', True),
        ),
    ),
    (
        '.ps-2',
        (
            ('padding-left', '8px', True),
        ),
    ),
    (
        '.ps-3',
        (
            ('padding-left', '16px', True),
        ),
    ),
    (
        '.ps-4',
        (
            ('padding-left', '24px', True),
        ),
    ),
    (
        '.ps-5',
        (
            ('padding-left', '48px', True),
        ),
    ),
    (
        '.p-sm-0',
        (
            ('padding-top', '0', True),
            ('padding-right', '0', True),
            ('padding-bottom', '0', True),
            ('padding-left', '0', True),
        ),
    ),
    (
        '.p-sm-1',
        (
            ('padding-top', '4px', True),
            ('padding-right', '4px', True),
            ('padding-bottom', '4px', True),
            ('padding-left', '4px', True),
        ),
    ),
    (
        '.p-sm-2',
        (
            ('padding-top', '8px', True),
            ('padding-right', '8px', True),
            ('padding-bottom', '8px', True),
            ('padding-left', '8px', True),
        ),
    ),
    (
        '.p-sm-3',
        (
            ('padding-top', '16px', True),
            ('padding-right', '16px', True),
            ('padding-bottom', '16px', True),
            ('padding-left', '16px', True),
        ),
    ),
    (
        '.p-sm-4',
        (
            ('padding-top', '24px', True),
            ('padding-right', '24px', True),
            ('padding-bottom', '24px', True),
            ('padding-left', '24px', True),
        ),
    ),
    (
        '.p-sm-5',
        (
            ('padding-top', '48px', True),
            ('padding-right', '48px', True),
            ('padding-bottom', '48px', True),
            ('padding-left', '48px', True),
        ),
    ),
    (
        '.px-sm-0',
        (
            ('padding-right', '0', True),
            ('padding-left', '0', True),
        ),
    ),
    (
        '.px-sm-1',
        (
            ('padding-right', '4px', True),
            ('padding-left', '4px', True),
        ),
    ),
    (
        '.px-sm-2',
        (
            ('padding-right', '8px', True),
            ('padding-left', '8px', True),
        ),
    ),
    (
        '.px-sm-3',
        (
            ('padding-right', '16px', True),
            ('padding-left', '16px', True),
        ),
    ),
    (
        '.px-sm-4',
        (
            ('padding-right', '24px', True),
            ('padding-left', '24px', True),
        ),
    ),
    (
        '.px-sm-5',
        (
            ('padding-right', '48px', True),
            ('padding-left', '48px', True),
        ),
    ),
    (
        '.py-sm-0',
        (
            ('padding-top', '0', True),
            ('padding-bottom', '0', True),
        ),
    ),
    (
        '.py-sm-1',
        (
            ('padding-top', '4px', True),
            ('padding-bottom', '4px', True),
        ),
    ),
    (
        '.py-sm-2',
        (
            ('padding-top', '8px', True),
            ('padding-bottom', '8px', True),
        ),
    ),
    (
        '.py-sm-3',
        (
            ('padding-top', '16px', True),
            ('padding-bottom', '16px', True),
        ),
    ),
    (
        '.py-sm-4',
        (
            ('padding-top', '24px', True),
            ('padding-bottom', '24px', True),
        ),
    ),
    (
        '.py-sm-5',
        (
            ('padding-top', '48px', True),
            ('padding-bottom', '48px', True),
        ),
    ),
    (
        '.pt-sm-0',
        (
            ('padding-top', '0', True),
        ),
    ),
    (
        '.pt-sm-1',
        (
            ('padding-top', '4px', True),
        ),
    ),
    (
        '.pt-sm-2',
        (
            ('padding-top', '8px', True),
        ),
    ),
    (
        '.pt-sm-3',
        (
            ('padding-top', '16px', True),
        ),
    ),
    (
        '.pt-sm-4',
        (
            ('padding-top', '24px', True),
        ),
    ),
    (
        '.pt-sm-5',
        (
            ('padding-top', '48px', True),
        ),
    ),
    (
        '.pe-sm-0',
        (
            ('padding-right', '0', True),
        ),
    ),
    (
        '.pe-sm-1',
        (
            ('padding-right', '4px', True),
        ),
    ),
    (
        '.pe-sm-2',
        (
            ('padding-right', '8px', True),
        ),
    ),
    (
        '.pe-sm-3',
        (
            ('padding-right', '16px', True),
        ),
    ),
    (
        '.pe-sm-4',
        (
            ('padding-right', '24px', True),
        ),
    ),
    (
        '.pe-sm-5',
        (
            ('padding-right', '48px', True),
        ),
    ),
    (
        '.pb-sm-0',
        (
            ('padding-bottom', '0', True),
        ),
    ),
    (
        '.pb-sm-1',
        (
            ('padding-bottom', '4px', True),
        ),
    ),
    (
        '.pb-sm-2',
        (
            ('padding-bottom', '8px', True),
        ),
    ),
    (
        '.pb-sm-3',
        (
            ('padding-bottom', '16px', True),
        ),
    ),
    (
        '.pb-sm-4',
        (
            ('padding-bottom', '24px', True),
        ),
    ),
    (
        '.pb-sm-5',
        (
            ('padding-bottom', '48px', True),
        ),
    ),
    (
        '.ps-sm-0',
        (
            ('padding-left', '0', True),
        ),
    ),
    (
        '.ps-sm-1',
        (
            ('padding-left', '4px', True),
        ),
    ),
    (
        '.ps-sm-2',
        (
            ('padding-left', '8px', True),
        ),
    ),
    (
        '.ps-sm-3',
        (
            ('padding-left', '16px', True),
        ),
    ),
    (
        '.ps-sm-4',
        (
            ('padding-left', '24px', True),
        ),
    ),
    (
        '.ps-sm-5',
        (
            ('padding-left', '48px', True),
        ),
    ),
    (
        '.p-md-0',
        (
            ('padding-top', '0', True),
            ('padding-right', '0', True),
            ('padding-bottom', '0', True),
            ('padding-left', '0', True),
        ),
    ),
    (
        '.p-md-1',
        (
            ('padding-top', '4px', True),
            ('padding-right', '4px', True),
            ('padding-bottom', '4px', True),
            ('padding-left', '4px', True),
        ),
    ),
    (
        '.p-md-2',
        (
            ('padding-top', '8px', True),
            ('padding-right', '8px', True),
            ('padding-bottom', '8px', True),
            ('padding-left', '8px', True),
        ),
    ),
    (
        '.p-md-3',
        (
            ('padding-top', '16px', True),
            ('padding-right', '16px', True),
            ('padding-bottom', '16px', True),
            ('padding-left', '16px', True),
        ),
    ),
    (
        '.p-md-4',
        (
            ('padding-top', '24px', True),
            ('padding-right', '24px', True),
            ('padding-bottom', '24px', True),
            ('padding-left', '24px', True),
        ),
    ),
    (
        '.p-md-5',
        (
            ('padding-top', '48px', True),
            ('padding-right', '48px', True),
            ('padding-bottom', '48px', True),
            ('padding-left', '48px', True),
        ),
    ),
    (
        '.px-md-0',
        (
            ('padding-right', '0', True),
            ('padding-left', '0', True),
        ),
    ),
    (
        '.px-md-1',
        (
            ('padding-right', '4px', True),
            ('padding-left', '4px', True),
        ),
    ),
    (
        '.px-md-2',
        (
            ('padding-right', '8px', True),
            ('padding-left', '8px', True),
        ),
    ),
    (
        '.px-md-3',
        (
            ('padding-right', '16px', True),
            ('padding-left', '16px', True),
        ),
    ),
    (
        '.px-md-4',
        (
            ('padding-right', '24px', True),
            ('padding-left', '24px', True),
        ),
    ),
    (
        '.px-md-5',
        (
            ('padding-right', '48px', True),
            ('padding-left', '48px', True),
        ),
    ),
    (
        '.py-md-0',
        (
            ('padding-top', '0', True),
            ('padding-bottom', '0', True),
        ),
    ),
    (
        '.py-md-1',
        (
            ('padding-top', '4px', True),
            ('padding-bottom', '4px', True),
        ),
    ),
    (
        '.py-md-2',
        (
            ('padding-top', '8px', True),
            ('padding-bottom', '8px', True),
        ),
    ),
    (
        '.py-md-3',
        (
            ('padding-top', '16px', True),
            ('padding-bottom', '16px', True),
        ),
    ),
    (
        '.py-md-4',
        (
            ('padding-top', '24px', True),
            ('padding-bottom', '24px', True),
        ),
    ),
    (
        '.py-md-5',
        (
            ('padding-top', '48px', True),
            ('padding-bottom', '48px', True),
        ),
    ),
    (
        '.pt-md-0',
        (
            ('padding-top', '0', True),
        ),
    ),
    (
        '.pt-md-1',
        (
            ('padding-top', '4px', True),
        ),
    ),
    (
        '.pt-md-2',
        (
            ('padding-top', '8px', True),
        ),
    ),
    (
        '.pt-md-3',
        (
            ('padding-top', '16px', True),
        ),
    ),
    (
        '.pt-md-4',
        (
            ('padding-top', '24px', True),
        ),
    ),
    (
        '.pt-md-5',
        (
            ('padding-top', '48px', True),
        ),
    ),
    (
        '.pe-md-0',
        (
            ('padding-right', '0', True),
        ),
    ),
    (
        '.pe-md-1',
        (
            ('padding-right', '4px', True),
        ),
    ),
    (
        '.pe-md-2',
        (
            ('padding-right', '8px', True),
        ),
    ),
    (
        '.pe-md-3',
        (
            ('padding-right', '16px', True),
        ),
    ),
    (
        '.pe-md-4',
        (
            ('padding-right', '24px', True),
        ),
    ),
    (
        '.pe-md-5',
        (
            ('padding-right', '48px', True),
        ),
    ),
    (
        '.pb-md-0',
        (
            ('padding-bottom', '0', True),
        ),
    ),
    (
        '.pb-md-1',
        (
            ('padding-bottom', '4px', True),
        ),
    ),
    (
        '.pb-md-2',
        (
            ('padding-bottom', '8px', True),
        ),
    ),
    (
        '.pb-md-3',
        (
            ('padding-bottom', '16px', True),
        ),
    ),
    (
        '.pb-md-4',
        (
            ('padding-bottom', '24px', True),
        ),
    ),
    (
        '.pb-md-5',
        (
            ('padding-bottom', '48px', True),
        ),
    ),
    (
        '.ps-md-0',
        (
            ('padding-left', '0', True),
        ),
    ),
    (
        '.ps-md-1',
        (
            ('padding-left', '4px', True),
        ),
    ),
    (
        '.ps-md-2',
        (
            ('padding-left', '8px', True),
        ),
    ),
    (
        '.ps-md-3',
        (
            ('padding-left', '16px', True),
        ),
    ),
    (
        '.ps-md-4',
        (
            ('padding-left', '24px', True),
        ),
    ),
    (
        '.ps-md-5',
        (
            ('padding-left', '48px', True),
        ),
    ),
    (
        '.p-lg-0',
        (
            ('padding-top', '0', True),
            ('padding-right', '0', True),
            ('padding-bottom', '0', True),
            ('padding-left', '0', True),
        ),
    ),
    (
        '.p-lg-1',
        (
            ('padding-top', '4px', True),
            ('padding-right', '4px', True),
            ('padding-bottom', '4px', True),
            ('padding-left', '4px', True),
        ),
    ),
    (
        '.p-lg-2',
        (
            ('padding-top', '8px', True),
            ('padding-right', '8px', True),
            ('padding-bottom', '8px', True),
            ('padding-left', '8px', True),
        ),
    ),
    (
        '.p-lg-3',
        (
            ('padding-top', '16px', True),
            ('padding-right', '16px', True),
            ('padding-bottom', '16px', True),
            ('padding-left', '16px', True),
        ),
    ),
    (
        '.p-lg-4',
        (
            ('padding-top', '24px', True),
            ('padding-right', '24px', True),
            ('padding-bottom', '24px', True),
            ('padding-left', '24px', True),
        ),
    ),
    (
        '.p-lg-5',
        (
            ('padding-top', '48px', True),
            ('padding-right', '48px', True),
            ('padding-bottom', '48px', True),
            ('padding-left', '48px', True),
        ),
    ),
    (
        '.px-lg-0',
        (
            ('padding-right', '0', True),
            ('padding-left', '0', True),
        ),
    ),
    (
        '.px-lg-1',
        (
            ('padding-right', '4px', True),
            ('padding-left', '4px', True),
        ),
    ),
    (
        '.px-lg-2',
        (
            ('padding-right', '8px', True),
            ('padding-left', '8px', True),
        ),
    ),
    (
        '.px-lg-3',
        (
            ('padding-right', '16px', True),
            ('padding-left', '16px', True),
        ),
    ),
    (
        '.px-lg-4',
        (
            ('padding-right', '24px', True),
            ('padding-left', '24px', True),
        ),
    ),
    (
        '.px-lg-5',
        (
            ('padding-right', '48px', True),
            ('padding-left', '48px', True),
        ),
    ),
    (
        '.py-lg-0',
        (
            ('padding-top', '0', True),
            ('padding-bottom', '0', True),
        ),
    ),
    (
        '.py-lg-1',
        (
            ('padding-top', '4px', True),
            ('padding-bottom', '4px', True),
        ),
    ),
    (
        '.py-lg-2',
        (
            ('padding-top', '8px', True),
            ('padding-bottom', '8px', True),
        ),
    ),
    (
        '.py-lg-3',
        (
            ('padding-top', '16px', True),
            ('padding-bottom', '16px', True),
        ),
    ),
    (
        '.py-lg-4',
        (
            ('padding-top', '24px', True),
            ('padding-bottom', '24px', True),
        ),
    ),
    (
        '.py-lg-5',
        (
            ('padding-top', '48px', True),
            ('padding-bottom', '48px', True),
        ),
    ),
    (
        '.pt-lg-0',
        (
            ('padding-top', '0', True),
        ),
    ),
    (
        '.pt-lg-1',
        (
            ('padding-top', '4px', True),
        ),
    ),
    (
        '.pt-lg-2',
        (
            ('padding-top', '8px', True),
        ),
    ),
    (
        '.pt-lg-3',
        (
            ('padding-top', '16px', True),
        ),
    ),
    (
        '.pt-lg-4',
        (
            ('padding-top', '24px', True),
        ),
    ),
    (
        '.pt-lg-5',
        (
            ('padding-top', '48px', True),
        ),
    ),
    (
        '.pe-lg-0',
        (
            ('padding-right', '0', True),
        ),
    ),
    (
        '.pe-lg-1',
        (
            ('padding-right', '4px', True),
        ),
    ),
    (
        '.pe-lg-2',
        (
            ('padding-right', '8px', True),
        ),
    ),
    (
        '.pe-lg-3',
        (
            ('padding-right', '16px', True),
        ),
    ),
    (
        '.pe-lg-4',
        (
            ('padding-right', '24px', True),
        ),
    ),
    (
        '.pe-lg-5',
        (
            ('padding-right', '48px', True),
        ),
    ),
    (
        '.pb-lg-0',
        (
            ('padding-bottom', '0', True),
        ),
    ),
    (
        '.pb-lg-1',
        (
            ('padding-bottom', '4px', True),
        ),
    ),
    (
        '.pb-lg-2',
        (
            ('padding-bottom', '8px', True),
        ),
    ),
    (
        '.pb-lg-3',
        (
            ('padding-bottom', '16px', True),
        ),
    ),
    (
        '.pb-lg-4',
        (
            ('padding-bottom', '24px', True),
        ),
    ),
    (
        '.pb-lg-5',
        (
            ('padding-bottom', '48px', True),
        ),
    ),
    (
        '.ps-lg-0',
        (
            ('padding-left', '0', True),
        ),
    ),
    (
        '.ps-lg-1',
        (
            ('padding-left', '4px', True),
        ),
    ),
    (
        '.ps-lg-2',
        (
            ('padding-left', '8px', True),
        ),
    ),
    (
        '.ps-lg-3',
        (
            ('padding-left', '16px', True),
        ),
    ),
    (
        '.ps-lg-4',
        (
            ('padding-left', '24px', True),
        ),
    ),
    (
        '.ps-lg-5',
        (
            ('padding-left', '48px', True),
        ),
    ),
    (
        '.p-xl-0',
        (
            ('padding-top', '0', True),
            ('padding-right', '0', True),
            ('padding-bottom', '0', True),
            ('padding-left', '0', True),
        ),
    ),
    (
        '.p-xl-1',
        (
            ('padding-top', '4px', True),
            ('padding-right', '4px', True),
            ('padding-bottom', '4px', True),
            ('padding-left', '4px', True),
        ),
    ),
    (
        '.p-xl-2',
        (
            ('padding-top', '8px', True),
            ('padding-right', '8px', True),
            ('padding-bottom', '8px', True),
            ('padding-left', '8px', True),
        ),
    ),
    (
        '.p-xl-3',
        (
            ('padding-top', '16px', True),
            ('padding-right', '16px', True),
            ('padding-bottom', '16px', True),
            ('padding-left', '16px', True),
        ),
    ),
    (
        '.p-xl-4',
        (
            ('padding-top', '24px', True),
            ('padding-right', '24px', True),
            ('padding-bottom', '24px', True),
            ('padding-left', '24px', True),
        ),
    ),
    (
        '.p-xl-5',
        (
            ('padding-top', '48px', True),
            ('padding-right', '48px', True),
            ('padding-bottom', '48px', True),
            ('padding-left', '48px', True),
        ),
    ),
    (
        '.px-xl-0',
        (
            ('padding-right', '0', True),
            ('padding-left', '0', True),
        ),
    ),
    (
        '.px-xl-1',
        (
            ('padding-right', '4px', True),
            ('padding-left', '4px', True),
        ),
    ),
    (
        '.px-xl-2',
        (
            ('padding-right', '8px', True),
            ('padding-left', '8px', True),
        ),
    ),
    (
        '.px-xl-3',
        (
            ('padding-right', '16px', True),
            ('padding-left', '16px', True),
        ),
    ),
    (
        '.px-xl-4',
        (
            ('padding-right', '24px', True),
            ('padding-left', '24px', True),
        ),
    ),
    (
        '.px-xl-5',
        (
            ('padding-right', '48px', True),
            ('padding-left', '48px', True),
        ),
    ),
    (
        '.py-xl-0',
        (
            ('padding-top', '0', True),
            ('padding-bottom', '0', True),
        ),
    ),
    (
        '.py-xl-1',
        (
            ('padding-top', '4px', True),
            ('padding-bottom', '4px', True),
        ),
    ),
    (
        '.py-xl-2',
        (
            ('padding-top', '8px', True),
            ('padding-bottom', '8px', True),
        ),
    ),
    (
        '.py-xl-3',
        (
            ('padding-top', '16px', True),
            ('padding-bottom', '16px', True),
        ),
    ),
    (
        '.py-xl-4',
        (
            ('padding-top', '24px', True),
            ('padding-bottom', '24px', True),
        ),
    ),
    (
        '.py-xl-5',
        (
            ('padding-top', '48px', True),
            ('padding-bottom', '48px', True),
        ),
    ),
    (
        '.pt-xl-0',
        (
            ('padding-top', '0', True),
        ),
    ),
    (
        '.pt-xl-1',
        (
            ('padding-top', '4px', True),
        ),
    ),
    (
        '.pt-xl-2',
        (
            ('padding-top', '8px', True),
        ),
    ),
    (
        '.pt-xl-3',
        (
            ('padding-top', '16px', True),
        ),
    ),
    (
        '.pt-xl-4',
        (
            ('padding-top', '24px', True),
        ),
    ),
    (
        '.pt-xl-5',
        (
            ('padding-top', '48px', True),
        ),
    ),
    (
        '.pe-xl-0',
        (
            ('padding-right', '0', True),
        ),
    ),
    (
        '.pe-xl-1',
        (
            ('padding-right', '4px', True),
        ),
    ),
    (
        '.pe-xl-2',
        (
            ('padding-right', '8px', True),
        ),
    ),
    (
        '.pe-xl-3',
        (
            ('padding-right', '16px', True),
        ),
    ),
    (
        '.pe-xl-4',
        (
            ('padding-right', '24px', True),
        ),
    ),
    (
        '.pe-xl-5',
        (
            ('padding-right', '48px', True),
        ),
    ),
    (
        '.pb-xl-0',
        (
            ('padding-bottom', '0', True),
        ),
    ),
    (
        '.pb-xl-1',
        (
            ('padding-bottom', '4px', True),
        ),
    ),
    (
        '.pb-xl-2',
        (
            ('padding-bottom', '8px', True),
        ),
    ),
    (
        '.pb-xl-3',
        (
            ('padding-bottom', '16px', True),
        ),
    ),
    (
        '.pb-xl-4',
        (
            ('padding-bottom', '24px', True),
        ),
    ),
    (
        '.pb-xl-5',
        (
            ('padding-bottom', '48px', True),
        ),
    ),
    (
        '.ps-xl-0',
        (
            ('padding-left', '0', True),
        ),
    ),
    (
        '.ps-xl-1',
        (
            ('padding-left', '4px', True),
        ),
    ),
    (
        '.ps-xl-2',
        (
            ('padding-left', '8px', True),
        ),
    ),
    (
        '.ps-xl-3',
        (
            ('padding-left', '16px', True),
        ),
    ),
    (
        '.ps-xl-4',
        (
            ('padding-left', '24px', True),
        ),
    ),
    (
        '.ps-xl-5',
        (
            ('padding-left', '48px', True),
        ),
    ),
    (
        '.p-xxl-0',
        (
            ('padding-top', '0', True),
            ('padding-right', '0', True),
            ('padding-bottom', '0', True),
            ('padding-left', '0', True),
        ),
    ),
    (
        '.p-xxl-1',
        (
            ('padding-top', '4px', True),
            ('padding-right', '4px', True),
            ('padding-bottom', '4px', True),
            ('padding-left', '4px', True),
        ),
    ),
    (
        '.p-xxl-2',
        (
            ('padding-top', '8px', True),
            ('padding-right', '8px', True),
            ('padding-bottom', '8px', True),
            ('padding-left', '8px', True),
        ),
    ),
    (
        '.p-xxl-3',
        (
            ('padding-top', '16px', True),
            ('padding-right', '16px', True),
            ('padding-bottom', '16px', True),
            ('padding-left', '16px', True),
        ),
    ),
    (
        '.p-xxl-4',
        (
            ('padding-top', '24px', True),
            ('padding-right', '24px', True),
            ('padding-bottom', '24px', True),
            ('padding-left', '24px', True),
        ),
    ),
    (
        '.p-xxl-5',
        (
            ('padding-top', '48px', True),
            ('padding-right', '48px', True),
            ('padding-bottom', '48px', True),
            ('padding-left', '48px', True),
        ),
    ),
    (
        '.px-xxl-0',
        (
            ('padding-right', '0', True),
            ('padding-left', '0', True),
        ),
    ),
    (
        '.px-xxl-1',
        (
            ('padding-right', '4px', True),
            ('padding-left', '4px', True),
        ),
    ),
    (
        '.px-xxl-2',
        (
            ('padding-right', '8px', True),
            ('padding-left', '8px', True),
        ),
    ),
    (
        '.px-xxl-3',
        (
            ('padding-right', '16px', True),
            ('padding-left', '16px', True),
        ),
    ),
    (
        '.px-xxl-4',
        (
            ('padding-right', '24px', True),
            ('padding-left', '24px', True),
        ),
    ),
    (
        '.px-xxl-5',
        (
            ('padding-right', '48px', True),
            ('padding-left', '48px', True),
        ),
    ),
    (
        '.py-xxl-0',
        (
            ('padding-top', '0', True),
            ('padding-bottom', '0', True),
        ),
    ),
    (
        '.py-xxl-1',
        (
            ('padding-top', '4px', True),
            ('padding-bottom', '4px', True),
        ),
    ),
    (
        '.py-xxl-2',
        (
            ('padding-top', '8px', True),
            ('padding-bottom', '8px', True),
        ),
    ),
    (
        '.py-xxl-3',
        (
            ('padding-top', '16px', True),
            ('padding-bottom', '16px', True),
        ),
    ),
    (
        '.py-xxl-4',
        (
            ('padding-top', '24px', True),
            ('padding-bottom', '24px', True),
        ),
    ),
    (
        '.py-xxl-5',
        (
            ('padding-top', '48px', True),
            ('padding-bottom', '48px', True),
        ),
    ),
    (
        '.pt-xxl-0',
        (
            ('padding-top', '0', True),
        ),
    ),
    (
        '.pt-xxl-1',
        (
            ('padding-top', '4px', True),
        ),
    ),
    (
        '.pt-xxl-2',
        (
            ('padding-top', '8px', True),
        ),
    ),
    (
        '.pt-xxl-3',
        (
            ('padding-top', '16px', True),
        ),
    ),
    (
        '.pt-xxl-4',
        (
            ('padding-top', '24px', True),
        ),
    ),
    (
        '.pt-xxl-5',
        (
            ('padding-top', '48px', True),
        ),
    ),
    (
        '.pe-xxl-0',
        (
            ('padding-right', '0', True),
        ),
    ),
    (
        '.pe-xxl-1',
        (
            ('padding-right', '4px', True),
        ),
    ),
    (
        '.pe-xxl-2',
        (
            ('padding-right', '8px', True),
        ),
    ),
    (
        '.pe-xxl-3',
        (
            ('padding-right', '16px', True),
        ),
    ),
    (
        '.pe-xxl-4',
        (
            ('padding-right', '24px', True),
        ),
    ),
    (
        '.pe-xxl-5',
        (
            ('padding-right', '48px', True),
        ),
    ),
    (
        '.pb-xxl-0',
        (
            ('padding-bottom', '0', True),
        ),
    ),
    (
        '.pb-xxl-1',
        (
            ('padding-bottom', '4px', True),
        ),
    ),
    (
        '.pb-xxl-2',
        (
            ('padding-bottom', '8px', True),
        ),
    ),
    (
        '.pb-xxl-3',
        (
            ('padding-bottom', '16px', True),
        ),
    ),
    (
        '.pb-xxl-4',
        (
            ('padding-bottom', '24px', True),
        ),
    ),
    (
        '.pb-xxl-5',
        (
            ('padding-bottom', '48px', True),
        ),
    ),
    (
        '.ps-xxl-0',
        (
            ('padding-left', '0', True),
        ),
    ),
    (
        '.ps-xxl-1',
        (
            ('padding-left', '4px', True),
        ),
    ),
    (
        '.ps-xxl-2',
        (
            ('padding-left', '8px', True),
        ),
    ),
    (
        '.ps-xxl-3',
        (
            ('padding-left', '16px', True),
        ),
    ),
    (
        '.ps-xxl-4',
        (
            ('padding-left', '24px', True),
        ),
    ),
    (
        '.ps-xxl-5',
        (
            ('padding-left', '48px', True),
        ),
    ),
    (
        ':not(.s_popup) > .modal .modal-dialog',
        (
            ('padding-top', '1.75rem', False),
            ('padding-right', '0', False),
            ('padding-bottom', '1.75rem', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.openerp .oe_form .oe_styling_v8',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.openerp .oe_form .oe_styling_v8 .oe_website_contents',
        (
            ('padding-bottom', '1px', False),
        ),
    ),
    (
        "[class*='oe_span']",
        (
            ('padding-top', '0', False),
            ('padding-right', '16px', False),
            ('padding-bottom', '0', False),
            ('padding-left', '16px', False),
        ),
    ),
    (
        "[class*='oe_span'].oe_fit",
        (
            ('padding-left', '0px', True),
            ('padding-right', '0px', True),
        ),
    ),
    (
        ".oe_row.oe_flex [class*='oe_span']",
        (
            ('padding-top', '0', False),
            ('padding-right', '16px', False),
            ('padding-bottom', '0', False),
            ('padding-left', '16px', False),
        ),
    ),
    (
        '.oe_rightfit',
        (
            ('padding-right', '0px', True),
        ),
    ),
    (
        '.oe_leftfit',
        (
            ('padding-left', '0px', True),
        ),
    ),
    (
        '.oe_padded',
        (
            ('padding-top', '16px', False),
            ('padding-bottom', '16px', False),
        ),
    ),
    (
        '.oe_more_padded',
        (
            ('padding-top', '32px', False),
            ('padding-bottom', '32px', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_button, .oe_styling_v8 a.oe_button',
        (
            ('padding-top', '8px', False),
            ('padding-right', '14px', False),
            ('padding-bottom', '8px', False),
            ('padding-left', '14px', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_button.oe_small, .oe_styling_v8 a.oe_button.oe_small',
        (
            ('padding-top', '2px', False),
            ('padding-right', '4px', False),
            ('padding-bottom', '2px', False),
            ('padding-left', '4px', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_button.oe_medium, .oe_styling_v8 a.oe_button.oe_medium',
        (
            ('padding-top', '5px', False),
            ('padding-right', '12px', False),
            ('padding-bottom', '5px', False),
            ('padding-left', '12px', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_input',
        (
            ('padding-top', '4px', False),
            ('padding-right', '7px', False),
            ('padding-bottom', '4px', False),
            ('padding-left', '7px', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_input.oe_big',
        (
            ('padding-top', '8px', False),
            ('padding-right', '14px', False),
            ('padding-bottom', '8px', False),
            ('padding-left', '14px', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_form_layout_table td',
        (
            ('padding-bottom', '16px', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_form_layout_table td:first-child',
        (
            ('padding-right', '16px', False),
        ),
    ),
    (
        '.oe_quote',
        (
            ('padding-top', '16px', False),
            ('padding-right', '16px', False),
            ('padding-bottom', '16px', False),
            ('padding-left', '16px', False),
        ),
    ),
    (
        '.oe_quote .oe_author',
        (
            ('padding-top', '6px', False),
        ),
    ),
    (
        'div.oe_demo div.oe_demo_footer',
        (
            ('padding-top', '7px', False),
            ('padding-bottom', '7px', False),
        ),
    ),
    (
        '.oe_row_tabs',
        (
            ('padding-top', '21px', False),
        ),
    ),
    (
        '.oe_row_tab',
        (
            ('padding-top', '8px', False),
            ('padding-right', '8px', False),
            ('padding-bottom', '8px', False),
            ('padding-left', '8px', False),
        ),
    ),
    (
        '.fa-ul',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.fa-border',
        (
            ('padding-top', '.2em', False),
            ('padding-right', '.25em', False),
            ('padding-bottom', '.15em', False),
            ('padding-left', '.25em', False),
        ),
    ),
    (
        '.visually-hidden',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        '.container, .o_container_small',
        (
            ('padding-right', '16px', False),
            ('padding-left', '16px', False),
        ),
    ),
    (
        '.o_body_html, .o_body_pdf.o_css_margins',
        (
            ('padding-top', '0', False),
            ('padding-right', '11mm', False),
            ('padding-bottom', '0', False),
            ('padding-left', '11mm', False),
        ),
    ),
    (
        '.o_body_html .header, .o_body_pdf.o_css_margins .header',
        (
            ('padding-top', '11mm', False),
        ),
    ),
    (
        '.o_body_html .footer > .o_footer_content, .o_body_pdf.o_css_margins .footer > .o_footer_content',
        (
            ('padding-bottom', '11mm', False),
        ),
    ),
    (
        'blockquote',
        (
            ('padding-top', '8px', False),
            ('padding-right', '16px', False),
            ('padding-bottom', '8px', False),
            ('padding-left', '16px', False),
        ),
    ),
    (
        '.o_snail_mail .address',
        (
            ('padding-top', '42px', False),
        ),
    ),
    (
        '.o_snail_mail .o_followup_address',
        (
            ('padding-top', '42px', False),
        ),
    ),
    (
        '.alert',
        (
            ('padding-top', '16px', False),
            ('padding-right', '16px', False),
            ('padding-bottom', '16px', False),
            ('padding-left', '16px', False),
        ),
    ),
    (
        '.btn',
        (
            ('padding-top', '0.625rem', False),
            ('padding-right', '0.3125rem', False),
            ('padding-bottom', '0.625rem', False),
            ('padding-left', '0.3125rem', False),
        ),
    ),
    (
        '.o_table_standard table:not(.o_ignore_layout_styling) th:first-child, .o_table_standard table:not(.o_ignore_layout_styling) td:first-child',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_table_standard table:not(.o_ignore_layout_styling) th:last-child, .o_table_standard table:not(.o_ignore_layout_styling) td:last-child',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_table_bold table:not(.o_ignore_layout_styling) tbody tr td',
        (
            ('padding-top', '1rem', False),
            ('padding-right', '0.5rem', False),
            ('padding-bottom', '1rem', False),
            ('padding-left', '0.5rem', False),
        ),
    ),
    (
        '.o_report_layout_bubble #informations',
        (
            ('padding-top', '8px', False),
            ('padding-right', '0.5rem', False),
            ('padding-bottom', '8px', False),
            ('padding-left', '0.5rem', False),
        ),
    ),
    (
        '.o_report_layout_bubble #informations div:first-child',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_report_layout_bubble #informations div:last-child',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_report_layout_wave #informations',
        (
            ('padding-top', '8px', False),
            ('padding-right', '0.5rem', False),
            ('padding-bottom', '8px', False),
            ('padding-left', '0.5rem', False),
        ),
    ),
    (
        '.o_report_layout_wave #informations div:first-child',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_report_layout_wave #informations div:last-child',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_table tr td',
        (
            ('padding-top', '0.5rem', False),
            ('padding-right', '0.5rem', False),
            ('padding-bottom', '0.5rem', False),
            ('padding-left', '0.5rem', False),
        ),
    ),
    (
        '.o_text_columns',
        (
            ('padding-top', '0', True),
            ('padding-right', '0', True),
            ('padding-bottom', '0', True),
            ('padding-left', '0', True),
        ),
    ),
    (
        '.o_text_columns > .row > .col-1:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-1:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-2:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-2:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-3:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-3:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-4:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-4:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-5:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-5:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-6:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-6:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-7:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-7:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-8:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-8:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-9:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-9:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-10:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-10:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-11:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-11:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-12:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-12:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-1:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-1:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-2:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-2:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-3:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-3:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-4:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-4:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-5:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-5:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-6:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-6:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-7:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-7:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-8:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-8:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-9:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-9:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-10:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-10:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-11:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-11:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-12:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xs-12:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-1:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-1:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-2:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-2:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-3:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-3:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-4:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-4:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-5:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-5:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-6:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-6:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-7:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-7:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-8:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-8:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-9:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-9:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-10:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-10:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-11:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-11:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-12:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-sm-12:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-1:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-1:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-2:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-2:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-3:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-3:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-4:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-4:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-5:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-5:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-6:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-6:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-7:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-7:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-8:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-8:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-9:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-9:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-10:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-10:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-11:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-11:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-12:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-md-12:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-1:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-1:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-2:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-2:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-3:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-3:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-4:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-4:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-5:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-5:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-6:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-6:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-7:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-7:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-8:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-8:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-9:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-9:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-10:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-10:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-11:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-11:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-12:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-lg-12:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-1:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-1:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-2:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-2:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-3:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-3:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-4:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-4:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-5:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-5:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-6:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-6:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-7:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-7:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-8:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-8:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-9:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-9:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-10:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-10:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-11:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-11:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-12:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xl-12:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-1:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-1:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-2:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-2:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-3:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-3:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-4:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-4:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-5:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-5:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-6:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-6:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-7:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-7:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-8:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-8:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-9:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-9:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-10:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-10:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-11:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-11:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-12:first-of-type',
        (
            ('padding-left', '0', False),
        ),
    ),
    (
        '.o_text_columns > .row > .col-xxl-12:last-of-type',
        (
            ('padding-right', '0', False),
        ),
    ),
    (
        'pre',
        (
            ('padding-top', '8px', False),
            ('padding-right', '16px', False),
            ('padding-bottom', '8px', False),
            ('padding-left', '16px', False),
        ),
    ),
    (
        'ul.o_checklist > li.o_checked::before',
        (
            ('padding-left', '1px', False),
            ('padding-top', '1px', False),
        ),
    ),
    (
        'img.padding-small, .img.padding-small, span.fa.padding-small, iframe.padding-small',
        (
            ('padding-top', '4px', False),
            ('padding-right', '4px', False),
            ('padding-bottom', '4px', False),
            ('padding-left', '4px', False),
        ),
    ),
    (
        'img.padding-medium, .img.padding-medium, span.fa.padding-medium, iframe.padding-medium',
        (
            ('padding-top', '8px', False),
            ('padding-right', '8px', False),
            ('padding-bottom', '8px', False),
            ('padding-left', '8px', False),
        ),
    ),
    (
        'img.padding-large, .img.padding-large, span.fa.padding-large, iframe.padding-large',
        (
            ('padding-top', '16px', False),
            ('padding-right', '16px', False),
            ('padding-bottom', '16px', False),
            ('padding-left', '16px', False),
        ),
    ),
    (
        'img.padding-xl, .img.padding-xl, span.fa.padding-xl, iframe.padding-xl',
        (
            ('padding-top', '32px', False),
            ('padding-right', '32px', False),
            ('padding-bottom', '32px', False),
            ('padding-left', '32px', False),
        ),
    ),
    (
        'div.media_iframe_video.padding-small iframe',
        (
            ('padding-top', '4px', False),
            ('padding-right', '4px', False),
            ('padding-bottom', '4px', False),
            ('padding-left', '4px', False),
        ),
    ),
    (
        'div.media_iframe_video.padding-medium iframe',
        (
            ('padding-top', '8px', False),
            ('padding-right', '8px', False),
            ('padding-bottom', '8px', False),
            ('padding-left', '8px', False),
        ),
    ),
    (
        'div.media_iframe_video.padding-large iframe',
        (
            ('padding-top', '16px', False),
            ('padding-right', '16px', False),
            ('padding-bottom', '16px', False),
            ('padding-left', '16px', False),
        ),
    ),
    (
        'div.media_iframe_video.padding-xl iframe',
        (
            ('padding-top', '32px', False),
            ('padding-right', '32px', False),
            ('padding-bottom', '32px', False),
            ('padding-left', '32px', False),
        ),
    ),
    (
        'div.media_iframe_video .media_iframe_video_size',
        (
            ('padding-bottom', '56.25%', False),
        ),
    ),
    (
        '.pt0',
        (
            ('padding-top', '0px', True),
        ),
    ),
    (
        '.pb0',
        (
            ('padding-bottom', '0px', True),
        ),
    ),
    (
        '.pt8',
        (
            ('padding-top', '8px', True),
        ),
    ),
    (
        '.pb8',
        (
            ('padding-bottom', '8px', True),
        ),
    ),
    (
        '.pt16',
        (
            ('padding-top', '16px', True),
        ),
    ),
    (
        '.pb16',
        (
            ('padding-bottom', '16px', True),
        ),
    ),
    (
        '.pt24',
        (
            ('padding-top', '24px', True),
        ),
    ),
    (
        '.pb24',
        (
            ('padding-bottom', '24px', True),
        ),
    ),
    (
        '.pt32',
        (
            ('padding-top', '32px', True),
        ),
    ),
    (
        '.pb32',
        (
            ('padding-bottom', '32px', True),
        ),
    ),
    (
        '.pt40',
        (
            ('padding-top', '40px', True),
        ),
    ),
    (
        '.pb40',
        (
            ('padding-bottom', '40px', True),
        ),
    ),
    (
        '.pt48',
        (
            ('padding-top', '48px', True),
        ),
    ),
    (
        '.pb48',
        (
            ('padding-bottom', '48px', True),
        ),
    ),
    (
        '.pt56',
        (
            ('padding-top', '56px', True),
        ),
    ),
    (
        '.pb56',
        (
            ('padding-bottom', '56px', True),
        ),
    ),
    (
        '.pt64',
        (
            ('padding-top', '64px', True),
        ),
    ),
    (
        '.pb64',
        (
            ('padding-bottom', '64px', True),
        ),
    ),
    (
        '.pt72',
        (
            ('padding-top', '72px', True),
        ),
    ),
    (
        '.pb72',
        (
            ('padding-bottom', '72px', True),
        ),
    ),
    (
        '.pt80',
        (
            ('padding-top', '80px', True),
        ),
    ),
    (
        '.pb80',
        (
            ('padding-bottom', '80px', True),
        ),
    ),
    (
        '.pt88',
        (
            ('padding-top', '88px', True),
        ),
    ),
    (
        '.pb88',
        (
            ('padding-bottom', '88px', True),
        ),
    ),
    (
        '.pt96',
        (
            ('padding-top', '96px', True),
        ),
    ),
    (
        '.pb96',
        (
            ('padding-bottom', '96px', True),
        ),
    ),
    (
        '.pt104',
        (
            ('padding-top', '104px', True),
        ),
    ),
    (
        '.pb104',
        (
            ('padding-bottom', '104px', True),
        ),
    ),
    (
        '.pt112',
        (
            ('padding-top', '112px', True),
        ),
    ),
    (
        '.pb112',
        (
            ('padding-bottom', '112px', True),
        ),
    ),
    (
        '.pt120',
        (
            ('padding-top', '120px', True),
        ),
    ),
    (
        '.pb120',
        (
            ('padding-bottom', '120px', True),
        ),
    ),
    (
        '.pt128',
        (
            ('padding-top', '128px', True),
        ),
    ),
    (
        '.pb128',
        (
            ('padding-bottom', '128px', True),
        ),
    ),
    (
        '.pt136',
        (
            ('padding-top', '136px', True),
        ),
    ),
    (
        '.pb136',
        (
            ('padding-bottom', '136px', True),
        ),
    ),
    (
        '.pt144',
        (
            ('padding-top', '144px', True),
        ),
    ),
    (
        '.pb144',
        (
            ('padding-bottom', '144px', True),
        ),
    ),
    (
        '.pt152',
        (
            ('padding-top', '152px', True),
        ),
    ),
    (
        '.pb152',
        (
            ('padding-bottom', '152px', True),
        ),
    ),
    (
        '.pt160',
        (
            ('padding-top', '160px', True),
        ),
    ),
    (
        '.pb160',
        (
            ('padding-bottom', '160px', True),
        ),
    ),
    (
        '.pt168',
        (
            ('padding-top', '168px', True),
        ),
    ),
    (
        '.pb168',
        (
            ('padding-bottom', '168px', True),
        ),
    ),
    (
        '.pt176',
        (
            ('padding-top', '176px', True),
        ),
    ),
    (
        '.pb176',
        (
            ('padding-bottom', '176px', True),
        ),
    ),
    (
        '.pt184',
        (
            ('padding-top', '184px', True),
        ),
    ),
    (
        '.pb184',
        (
            ('padding-bottom', '184px', True),
        ),
    ),
    (
        '.pt192',
        (
            ('padding-top', '192px', True),
        ),
    ),
    (
        '.pb192',
        (
            ('padding-bottom', '192px', True),
        ),
    ),
    (
        '.pt200',
        (
            ('padding-top', '200px', True),
        ),
    ),
    (
        '.pb200',
        (
            ('padding-bottom', '200px', True),
        ),
    ),
    (
        '.pt208',
        (
            ('padding-top', '208px', True),
        ),
    ),
    (
        '.pb208',
        (
            ('padding-bottom', '208px', True),
        ),
    ),
    (
        '.pt216',
        (
            ('padding-top', '216px', True),
        ),
    ),
    (
        '.pb216',
        (
            ('padding-bottom', '216px', True),
        ),
    ),
    (
        '.pt224',
        (
            ('padding-top', '224px', True),
        ),
    ),
    (
        '.pb224',
        (
            ('padding-bottom', '224px', True),
        ),
    ),
    (
        '.pt232',
        (
            ('padding-top', '232px', True),
        ),
    ),
    (
        '.pb232',
        (
            ('padding-bottom', '232px', True),
        ),
    ),
    (
        '.pt240',
        (
            ('padding-top', '240px', True),
        ),
    ),
    (
        '.pb240',
        (
            ('padding-bottom', '240px', True),
        ),
    ),
    (
        '.pt248',
        (
            ('padding-top', '248px', True),
        ),
    ),
    (
        '.pb248',
        (
            ('padding-bottom', '248px', True),
        ),
    ),
    (
        '.pt256',
        (
            ('padding-top', '256px', True),
        ),
    ),
    (
        '.pb256',
        (
            ('padding-bottom', '256px', True),
        ),
    ),
    (
        '.pt4',
        (
            ('padding-top', '4px', True),
        ),
    ),
    (
        '.pb4',
        (
            ('padding-bottom', '4px', True),
        ),
    ),
    (
        '.o_nocontent_help',
        (
            ('padding-top', '15px', False),
            ('padding-right', '15px', False),
            ('padding-bottom', '15px', False),
            ('padding-left', '15px', False),
        ),
    ),
    (
        'blockquote',
        (
            ('padding-top', '8px', False),
            ('padding-right', '16px', False),
            ('padding-bottom', '8px', False),
            ('padding-left', '16px', False),
        ),
    ),
    (
        '.ui-autocomplete .ui-menu-item',
        (
            ('padding-top', '0', False),
            ('padding-right', '0', False),
            ('padding-bottom', '0', False),
            ('padding-left', '0', False),
        ),
    ),
    (
        'code.o_inline_code',
        (
            ('padding-top', '.2em', False),
            ('padding-right', '.4em', False),
            ('padding-bottom', '.2em', False),
            ('padding-left', '.4em', False),
        ),
    ),
    (
        '.o_label_page',
        (
            ('padding-top', '1mm', False),
            ('padding-right', '0mm', False),
            ('padding-bottom', '0mm', False),
            ('padding-left', '0mm', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_rule_main',
        (
            ('padding-top', '2px', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_rule_cell',
        (
            ('padding-top', '0', True),
            ('padding-right', '0', True),
            ('padding-bottom', '0', True),
            ('padding-left', '0', True),
        ),
    ),
)


FLEX_ITEM_RULES = (
    (
        '#qrcode_odoo_logo',
        (
            ('width', '18%', False),
        ),
    ),
    (
        '.o_nocontent_help .o_empty_folder_image:before',
        (
            ('width', '120px', False),
        ),
    ),
    (
        'fieldset',
        (
            ('min-width', '0', False),
        ),
    ),
    (
        'legend',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.img-fluid',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.img-thumbnail',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.container, .o_container_small, .container-fluid, .container-xxl, .container-xl, .container-lg, .container-md, .container-sm',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.container-sm, .container, .o_container_small',
        (
            ('max-width', '540px', False),
        ),
    ),
    (
        '.container-md, .container-sm, .container, .o_container_small',
        (
            ('max-width', '720px', False),
        ),
    ),
    (
        '.container-lg, .container-md, .container-sm, .container, .o_container_small',
        (
            ('max-width', '960px', False),
        ),
    ),
    (
        '.container-xl, .container-lg, .container-md, .container-sm, .container, .o_container_small',
        (
            ('max-width', '1140px', False),
        ),
    ),
    (
        '.container-xxl, .container-xl, .container-lg, .container-md, .container-sm, .container, .o_container_small',
        (
            ('max-width', '1320px', False),
        ),
    ),
    (
        '.row > *',
        (
            ('width', '100%', False),
            ('max-width', '100%', False),
        ),
    ),
    (
        '.col',
        (
            ('flex', '1 0 0%', False),
        ),
    ),
    (
        '.row-cols-auto > *',
        (
            ('flex', '0 0 auto', False),
            ('width', 'auto', False),
        ),
    ),
    (
        '.row-cols-1 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '100%', False),
        ),
    ),
    (
        '.row-cols-2 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '50%', False),
        ),
    ),
    (
        '.row-cols-3 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.row-cols-4 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '25%', False),
        ),
    ),
    (
        '.row-cols-5 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '20%', False),
        ),
    ),
    (
        '.row-cols-6 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-auto',
        (
            ('flex', '0 0 auto', False),
            ('width', 'auto', False),
        ),
    ),
    (
        '.col-1',
        (
            ('flex', '0 0 auto', False),
            ('width', '8.33333333%', False),
        ),
    ),
    (
        '.col-2',
        (
            ('flex', '0 0 auto', False),
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-3',
        (
            ('flex', '0 0 auto', False),
            ('width', '25%', False),
        ),
    ),
    (
        '.col-4',
        (
            ('flex', '0 0 auto', False),
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.col-5',
        (
            ('flex', '0 0 auto', False),
            ('width', '41.66666667%', False),
        ),
    ),
    (
        '.col-6',
        (
            ('flex', '0 0 auto', False),
            ('width', '50%', False),
        ),
    ),
    (
        '.col-7',
        (
            ('flex', '0 0 auto', False),
            ('width', '58.33333333%', False),
        ),
    ),
    (
        '.col-8',
        (
            ('flex', '0 0 auto', False),
            ('width', '66.66666667%', False),
        ),
    ),
    (
        '.col-9',
        (
            ('flex', '0 0 auto', False),
            ('width', '75%', False),
        ),
    ),
    (
        '.col-10',
        (
            ('flex', '0 0 auto', False),
            ('width', '83.33333333%', False),
        ),
    ),
    (
        '.col-11',
        (
            ('flex', '0 0 auto', False),
            ('width', '91.66666667%', False),
        ),
    ),
    (
        '.col-12',
        (
            ('flex', '0 0 auto', False),
            ('width', '100%', False),
        ),
    ),
    (
        '.col-sm',
        (
            ('flex', '1 0 0%', False),
        ),
    ),
    (
        '.row-cols-sm-auto > *',
        (
            ('flex', '0 0 auto', False),
            ('width', 'auto', False),
        ),
    ),
    (
        '.row-cols-sm-1 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '100%', False),
        ),
    ),
    (
        '.row-cols-sm-2 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '50%', False),
        ),
    ),
    (
        '.row-cols-sm-3 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.row-cols-sm-4 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '25%', False),
        ),
    ),
    (
        '.row-cols-sm-5 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '20%', False),
        ),
    ),
    (
        '.row-cols-sm-6 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-sm-auto',
        (
            ('flex', '0 0 auto', False),
            ('width', 'auto', False),
        ),
    ),
    (
        '.col-sm-1',
        (
            ('flex', '0 0 auto', False),
            ('width', '8.33333333%', False),
        ),
    ),
    (
        '.col-sm-2',
        (
            ('flex', '0 0 auto', False),
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-sm-3',
        (
            ('flex', '0 0 auto', False),
            ('width', '25%', False),
        ),
    ),
    (
        '.col-sm-4',
        (
            ('flex', '0 0 auto', False),
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.col-sm-5',
        (
            ('flex', '0 0 auto', False),
            ('width', '41.66666667%', False),
        ),
    ),
    (
        '.col-sm-6',
        (
            ('flex', '0 0 auto', False),
            ('width', '50%', False),
        ),
    ),
    (
        '.col-sm-7',
        (
            ('flex', '0 0 auto', False),
            ('width', '58.33333333%', False),
        ),
    ),
    (
        '.col-sm-8',
        (
            ('flex', '0 0 auto', False),
            ('width', '66.66666667%', False),
        ),
    ),
    (
        '.col-sm-9',
        (
            ('flex', '0 0 auto', False),
            ('width', '75%', False),
        ),
    ),
    (
        '.col-sm-10',
        (
            ('flex', '0 0 auto', False),
            ('width', '83.33333333%', False),
        ),
    ),
    (
        '.col-sm-11',
        (
            ('flex', '0 0 auto', False),
            ('width', '91.66666667%', False),
        ),
    ),
    (
        '.col-sm-12',
        (
            ('flex', '0 0 auto', False),
            ('width', '100%', False),
        ),
    ),
    (
        '.col-md',
        (
            ('flex', '1 0 0%', False),
        ),
    ),
    (
        '.row-cols-md-auto > *',
        (
            ('flex', '0 0 auto', False),
            ('width', 'auto', False),
        ),
    ),
    (
        '.row-cols-md-1 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '100%', False),
        ),
    ),
    (
        '.row-cols-md-2 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '50%', False),
        ),
    ),
    (
        '.row-cols-md-3 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.row-cols-md-4 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '25%', False),
        ),
    ),
    (
        '.row-cols-md-5 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '20%', False),
        ),
    ),
    (
        '.row-cols-md-6 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-md-auto',
        (
            ('flex', '0 0 auto', False),
            ('width', 'auto', False),
        ),
    ),
    (
        '.col-md-1',
        (
            ('flex', '0 0 auto', False),
            ('width', '8.33333333%', False),
        ),
    ),
    (
        '.col-md-2',
        (
            ('flex', '0 0 auto', False),
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-md-3',
        (
            ('flex', '0 0 auto', False),
            ('width', '25%', False),
        ),
    ),
    (
        '.col-md-4',
        (
            ('flex', '0 0 auto', False),
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.col-md-5',
        (
            ('flex', '0 0 auto', False),
            ('width', '41.66666667%', False),
        ),
    ),
    (
        '.col-md-6',
        (
            ('flex', '0 0 auto', False),
            ('width', '50%', False),
        ),
    ),
    (
        '.col-md-7',
        (
            ('flex', '0 0 auto', False),
            ('width', '58.33333333%', False),
        ),
    ),
    (
        '.col-md-8',
        (
            ('flex', '0 0 auto', False),
            ('width', '66.66666667%', False),
        ),
    ),
    (
        '.col-md-9',
        (
            ('flex', '0 0 auto', False),
            ('width', '75%', False),
        ),
    ),
    (
        '.col-md-10',
        (
            ('flex', '0 0 auto', False),
            ('width', '83.33333333%', False),
        ),
    ),
    (
        '.col-md-11',
        (
            ('flex', '0 0 auto', False),
            ('width', '91.66666667%', False),
        ),
    ),
    (
        '.col-md-12',
        (
            ('flex', '0 0 auto', False),
            ('width', '100%', False),
        ),
    ),
    (
        '.col-lg',
        (
            ('flex', '1 0 0%', False),
        ),
    ),
    (
        '.row-cols-lg-auto > *',
        (
            ('flex', '0 0 auto', False),
            ('width', 'auto', False),
        ),
    ),
    (
        '.row-cols-lg-1 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '100%', False),
        ),
    ),
    (
        '.row-cols-lg-2 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '50%', False),
        ),
    ),
    (
        '.row-cols-lg-3 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.row-cols-lg-4 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '25%', False),
        ),
    ),
    (
        '.row-cols-lg-5 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '20%', False),
        ),
    ),
    (
        '.row-cols-lg-6 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-lg-auto',
        (
            ('flex', '0 0 auto', False),
            ('width', 'auto', False),
        ),
    ),
    (
        '.col-lg-1',
        (
            ('flex', '0 0 auto', False),
            ('width', '8.33333333%', False),
        ),
    ),
    (
        '.col-lg-2',
        (
            ('flex', '0 0 auto', False),
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-lg-3',
        (
            ('flex', '0 0 auto', False),
            ('width', '25%', False),
        ),
    ),
    (
        '.col-lg-4',
        (
            ('flex', '0 0 auto', False),
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.col-lg-5',
        (
            ('flex', '0 0 auto', False),
            ('width', '41.66666667%', False),
        ),
    ),
    (
        '.col-lg-6',
        (
            ('flex', '0 0 auto', False),
            ('width', '50%', False),
        ),
    ),
    (
        '.col-lg-7',
        (
            ('flex', '0 0 auto', False),
            ('width', '58.33333333%', False),
        ),
    ),
    (
        '.col-lg-8',
        (
            ('flex', '0 0 auto', False),
            ('width', '66.66666667%', False),
        ),
    ),
    (
        '.col-lg-9',
        (
            ('flex', '0 0 auto', False),
            ('width', '75%', False),
        ),
    ),
    (
        '.col-lg-10',
        (
            ('flex', '0 0 auto', False),
            ('width', '83.33333333%', False),
        ),
    ),
    (
        '.col-lg-11',
        (
            ('flex', '0 0 auto', False),
            ('width', '91.66666667%', False),
        ),
    ),
    (
        '.col-lg-12',
        (
            ('flex', '0 0 auto', False),
            ('width', '100%', False),
        ),
    ),
    (
        '.col-xl',
        (
            ('flex', '1 0 0%', False),
        ),
    ),
    (
        '.row-cols-xl-auto > *',
        (
            ('flex', '0 0 auto', False),
            ('width', 'auto', False),
        ),
    ),
    (
        '.row-cols-xl-1 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '100%', False),
        ),
    ),
    (
        '.row-cols-xl-2 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '50%', False),
        ),
    ),
    (
        '.row-cols-xl-3 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.row-cols-xl-4 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '25%', False),
        ),
    ),
    (
        '.row-cols-xl-5 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '20%', False),
        ),
    ),
    (
        '.row-cols-xl-6 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-xl-auto',
        (
            ('flex', '0 0 auto', False),
            ('width', 'auto', False),
        ),
    ),
    (
        '.col-xl-1',
        (
            ('flex', '0 0 auto', False),
            ('width', '8.33333333%', False),
        ),
    ),
    (
        '.col-xl-2',
        (
            ('flex', '0 0 auto', False),
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-xl-3',
        (
            ('flex', '0 0 auto', False),
            ('width', '25%', False),
        ),
    ),
    (
        '.col-xl-4',
        (
            ('flex', '0 0 auto', False),
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.col-xl-5',
        (
            ('flex', '0 0 auto', False),
            ('width', '41.66666667%', False),
        ),
    ),
    (
        '.col-xl-6',
        (
            ('flex', '0 0 auto', False),
            ('width', '50%', False),
        ),
    ),
    (
        '.col-xl-7',
        (
            ('flex', '0 0 auto', False),
            ('width', '58.33333333%', False),
        ),
    ),
    (
        '.col-xl-8',
        (
            ('flex', '0 0 auto', False),
            ('width', '66.66666667%', False),
        ),
    ),
    (
        '.col-xl-9',
        (
            ('flex', '0 0 auto', False),
            ('width', '75%', False),
        ),
    ),
    (
        '.col-xl-10',
        (
            ('flex', '0 0 auto', False),
            ('width', '83.33333333%', False),
        ),
    ),
    (
        '.col-xl-11',
        (
            ('flex', '0 0 auto', False),
            ('width', '91.66666667%', False),
        ),
    ),
    (
        '.col-xl-12',
        (
            ('flex', '0 0 auto', False),
            ('width', '100%', False),
        ),
    ),
    (
        '.col-xxl',
        (
            ('flex', '1 0 0%', False),
        ),
    ),
    (
        '.row-cols-xxl-auto > *',
        (
            ('flex', '0 0 auto', False),
            ('width', 'auto', False),
        ),
    ),
    (
        '.row-cols-xxl-1 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '100%', False),
        ),
    ),
    (
        '.row-cols-xxl-2 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '50%', False),
        ),
    ),
    (
        '.row-cols-xxl-3 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.row-cols-xxl-4 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '25%', False),
        ),
    ),
    (
        '.row-cols-xxl-5 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '20%', False),
        ),
    ),
    (
        '.row-cols-xxl-6 > *',
        (
            ('flex', '0 0 auto', False),
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-xxl-auto',
        (
            ('flex', '0 0 auto', False),
            ('width', 'auto', False),
        ),
    ),
    (
        '.col-xxl-1',
        (
            ('flex', '0 0 auto', False),
            ('width', '8.33333333%', False),
        ),
    ),
    (
        '.col-xxl-2',
        (
            ('flex', '0 0 auto', False),
            ('width', '16.66666667%', False),
        ),
    ),
    (
        '.col-xxl-3',
        (
            ('flex', '0 0 auto', False),
            ('width', '25%', False),
        ),
    ),
    (
        '.col-xxl-4',
        (
            ('flex', '0 0 auto', False),
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.col-xxl-5',
        (
            ('flex', '0 0 auto', False),
            ('width', '41.66666667%', False),
        ),
    ),
    (
        '.col-xxl-6',
        (
            ('flex', '0 0 auto', False),
            ('width', '50%', False),
        ),
    ),
    (
        '.col-xxl-7',
        (
            ('flex', '0 0 auto', False),
            ('width', '58.33333333%', False),
        ),
    ),
    (
        '.col-xxl-8',
        (
            ('flex', '0 0 auto', False),
            ('width', '66.66666667%', False),
        ),
    ),
    (
        '.col-xxl-9',
        (
            ('flex', '0 0 auto', False),
            ('width', '75%', False),
        ),
    ),
    (
        '.col-xxl-10',
        (
            ('flex', '0 0 auto', False),
            ('width', '83.33333333%', False),
        ),
    ),
    (
        '.col-xxl-11',
        (
            ('flex', '0 0 auto', False),
            ('width', '91.66666667%', False),
        ),
    ),
    (
        '.col-xxl-12',
        (
            ('flex', '0 0 auto', False),
            ('width', '100%', False),
        ),
    ),
    (
        '.table',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.form-control',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.form-control::-webkit-date-and-time-value',
        (
            ('min-width', '85px', False),
        ),
    ),
    (
        '.form-control-plaintext',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.form-control-color',
        (
            ('width', '3rem', False),
        ),
    ),
    (
        '.form-select',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.form-check-input',
        (
            ('width', '1em', False),
        ),
    ),
    (
        '.form-switch .form-check-input',
        (
            ('width', '2em', False),
        ),
    ),
    (
        '.form-range',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.form-range::-webkit-slider-thumb',
        (
            ('width', '1rem', False),
        ),
    ),
    (
        '.form-range::-webkit-slider-runnable-track',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.form-range::-moz-range-thumb',
        (
            ('width', '1rem', False),
        ),
    ),
    (
        '.form-range::-moz-range-track',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.input-group',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.input-group > .form-control, .input-group > .form-select, .input-group > .form-floating',
        (
            ('flex', '1 1 auto', False),
            ('width', '1%', False),
            ('min-width', '0', False),
        ),
    ),
    (
        '.valid-feedback',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.valid-tooltip',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.was-validated .form-control-color:valid, .form-control-color.is-valid',
        (
            ('width', 'calc(3rem + calc(1.5em + 0.625rem))', False),
        ),
    ),
    (
        '.invalid-feedback',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.invalid-tooltip',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.was-validated .form-control-color:invalid, .form-control-color.is-invalid',
        (
            ('width', 'calc(3rem + calc(1.5em + 0.625rem))', False),
        ),
    ),
    (
        '.collapsing.collapse-horizontal',
        (
            ('width', '0', False),
        ),
    ),
    (
        '.dropdown-menu',
        (
            ('min-width', 'var(--dropdown-min-width)', False),
        ),
    ),
    (
        '.dropdown-item',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.btn-group > .btn, .btn-group-vertical > .btn',
        (
            ('flex', '1 1 auto', False),
        ),
    ),
    (
        '.btn-toolbar .input-group',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.btn-group-vertical > .btn, .btn-group-vertical > .btn-group',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.nav-fill > .nav-link, .nav-fill .nav-item',
        (
            ('flex', '1 1 auto', False),
        ),
    ),
    (
        '.nav-justified > .nav-link, .nav-justified .nav-item',
        (
            ('flex-basis', '0', False),
            ('flex-grow', '1', False),
        ),
    ),
    (
        '.nav-fill .nav-item .nav-link, .nav-justified .nav-item .nav-link',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.navbar-collapse',
        (
            ('flex-basis', '100%', False),
            ('flex-grow', '1', False),
        ),
    ),
    (
        '.navbar-toggler-icon',
        (
            ('width', '1.5em', False),
        ),
    ),
    (
        '.navbar-expand-sm .navbar-collapse',
        (
            ('flex-basis', 'auto', False),
        ),
    ),
    (
        '.navbar-expand-sm .offcanvas',
        (
            ('flex-grow', '1', False),
            ('width', 'auto', True),
        ),
    ),
    (
        '.navbar-expand-sm .offcanvas .offcanvas-body',
        (
            ('flex-grow', '0', False),
        ),
    ),
    (
        '.navbar-expand-md .navbar-collapse',
        (
            ('flex-basis', 'auto', False),
        ),
    ),
    (
        '.navbar-expand-md .offcanvas',
        (
            ('flex-grow', '1', False),
            ('width', 'auto', True),
        ),
    ),
    (
        '.navbar-expand-md .offcanvas .offcanvas-body',
        (
            ('flex-grow', '0', False),
        ),
    ),
    (
        '.navbar-expand-lg .navbar-collapse',
        (
            ('flex-basis', 'auto', False),
        ),
    ),
    (
        '.navbar-expand-lg .offcanvas',
        (
            ('flex-grow', '1', False),
            ('width', 'auto', True),
        ),
    ),
    (
        '.navbar-expand-lg .offcanvas .offcanvas-body',
        (
            ('flex-grow', '0', False),
        ),
    ),
    (
        '.navbar-expand-xl .navbar-collapse',
        (
            ('flex-basis', 'auto', False),
        ),
    ),
    (
        '.navbar-expand-xl .offcanvas',
        (
            ('flex-grow', '1', False),
            ('width', 'auto', True),
        ),
    ),
    (
        '.navbar-expand-xl .offcanvas .offcanvas-body',
        (
            ('flex-grow', '0', False),
        ),
    ),
    (
        '.navbar-expand-xxl .navbar-collapse',
        (
            ('flex-basis', 'auto', False),
        ),
    ),
    (
        '.navbar-expand-xxl .offcanvas',
        (
            ('flex-grow', '1', False),
            ('width', 'auto', True),
        ),
    ),
    (
        '.navbar-expand-xxl .offcanvas .offcanvas-body',
        (
            ('flex-grow', '0', False),
        ),
    ),
    (
        '.navbar-expand .navbar-collapse',
        (
            ('flex-basis', 'auto', False),
        ),
    ),
    (
        '.navbar-expand .offcanvas',
        (
            ('flex-grow', '1', False),
            ('width', 'auto', True),
        ),
    ),
    (
        '.navbar-expand .offcanvas .offcanvas-body',
        (
            ('flex-grow', '0', False),
        ),
    ),
    (
        '.card',
        (
            ('min-width', '0', False),
        ),
    ),
    (
        '.card-body',
        (
            ('flex', '1 1 auto', False),
        ),
    ),
    (
        '.card-img, .card-img-top, .card-img-bottom',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.card-group > .card',
        (
            ('flex', '1 0 0%', False),
        ),
    ),
    (
        '.accordion-button',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.accordion-button::after',
        (
            ('width', 'var(--accordion-btn-icon-width)', False),
        ),
    ),
    (
        '.progress-stacked > .progress > .progress-bar',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.list-group-item-action',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.btn-close',
        (
            ('width', '1em', False),
        ),
    ),
    (
        '.toast',
        (
            ('width', 'var(--toast-max-width)', False),
            ('max-width', '100%', False),
        ),
    ),
    (
        '.toast-container',
        (
            ('width', 'max-content', False),
            ('max-width', '100%', False),
        ),
    ),
    (
        '.modal',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.modal-dialog',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.modal-content',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.modal-backdrop',
        (
            ('width', '100vw', False),
        ),
    ),
    (
        '.modal-body',
        (
            ('flex', '1 1 auto', False),
        ),
    ),
    (
        '.modal-dialog',
        (
            ('max-width', 'var(--modal-width)', False),
        ),
    ),
    (
        '.modal-fullscreen',
        (
            ('width', '100vw', False),
            ('max-width', 'none', False),
        ),
    ),
    (
        '.modal-fullscreen-sm-down',
        (
            ('width', '100vw', False),
            ('max-width', 'none', False),
        ),
    ),
    (
        '.modal-fullscreen-md-down',
        (
            ('width', '100vw', False),
            ('max-width', 'none', False),
        ),
    ),
    (
        '.modal-fullscreen-lg-down',
        (
            ('width', '100vw', False),
            ('max-width', 'none', False),
        ),
    ),
    (
        '.modal-fullscreen-xl-down',
        (
            ('width', '100vw', False),
            ('max-width', 'none', False),
        ),
    ),
    (
        '.modal-fullscreen-xxl-down',
        (
            ('width', '100vw', False),
            ('max-width', 'none', False),
        ),
    ),
    (
        '.tooltip .tooltip-arrow',
        (
            ('width', 'var(--tooltip-arrow-width)', False),
        ),
    ),
    (
        '.bs-tooltip-end .tooltip-arrow, .bs-tooltip-auto[data-popper-placement^="right"] .tooltip-arrow',
        (
            ('width', 'var(--tooltip-arrow-height)', False),
        ),
    ),
    (
        '.bs-tooltip-start .tooltip-arrow, .bs-tooltip-auto[data-popper-placement^="left"] .tooltip-arrow',
        (
            ('width', 'var(--tooltip-arrow-height)', False),
        ),
    ),
    (
        '.tooltip-inner',
        (
            ('max-width', 'var(--tooltip-max-width)', False),
        ),
    ),
    (
        '.popover',
        (
            ('max-width', 'var(--popover-max-width)', False),
        ),
    ),
    (
        '.popover .popover-arrow',
        (
            ('width', 'var(--popover-arrow-width)', False),
        ),
    ),
    (
        '.bs-popover-end > .popover-arrow, .bs-popover-auto[data-popper-placement^="right"] > .popover-arrow',
        (
            ('width', 'var(--popover-arrow-height)', False),
        ),
    ),
    (
        '.bs-popover-bottom .popover-header::before, .bs-popover-auto[data-popper-placement^="bottom"] .popover-header::before',
        (
            ('width', 'var(--popover-arrow-width)', False),
        ),
    ),
    (
        '.bs-popover-start > .popover-arrow, .bs-popover-auto[data-popper-placement^="left"] > .popover-arrow',
        (
            ('width', 'var(--popover-arrow-height)', False),
        ),
    ),
    (
        '.carousel-inner',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.carousel-item',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.carousel-control-prev, .carousel-control-next',
        (
            ('width', '15%', False),
        ),
    ),
    (
        '.carousel-control-prev-icon, .carousel-control-next-icon',
        (
            ('width', '2rem', False),
        ),
    ),
    (
        '.carousel-indicators [data-bs-target]',
        (
            ('flex', '0 1 auto', False),
            ('width', '30px', False),
        ),
    ),
    (
        '.spinner-grow, .spinner-border',
        (
            ('width', 'var(--spinner-width)', False),
        ),
    ),
    (
        '.offcanvas-sm',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.offcanvas-sm.offcanvas-start',
        (
            ('width', 'var(--offcanvas-width)', False),
        ),
    ),
    (
        '.offcanvas-sm.offcanvas-end',
        (
            ('width', 'var(--offcanvas-width)', False),
        ),
    ),
    (
        '.offcanvas-sm .offcanvas-body',
        (
            ('flex-grow', '0', False),
        ),
    ),
    (
        '.offcanvas-md',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.offcanvas-md.offcanvas-start',
        (
            ('width', 'var(--offcanvas-width)', False),
        ),
    ),
    (
        '.offcanvas-md.offcanvas-end',
        (
            ('width', 'var(--offcanvas-width)', False),
        ),
    ),
    (
        '.offcanvas-md .offcanvas-body',
        (
            ('flex-grow', '0', False),
        ),
    ),
    (
        '.offcanvas-lg',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.offcanvas-lg.offcanvas-start',
        (
            ('width', 'var(--offcanvas-width)', False),
        ),
    ),
    (
        '.offcanvas-lg.offcanvas-end',
        (
            ('width', 'var(--offcanvas-width)', False),
        ),
    ),
    (
        '.offcanvas-lg .offcanvas-body',
        (
            ('flex-grow', '0', False),
        ),
    ),
    (
        '.offcanvas-xl',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.offcanvas-xl.offcanvas-start',
        (
            ('width', 'var(--offcanvas-width)', False),
        ),
    ),
    (
        '.offcanvas-xl.offcanvas-end',
        (
            ('width', 'var(--offcanvas-width)', False),
        ),
    ),
    (
        '.offcanvas-xl .offcanvas-body',
        (
            ('flex-grow', '0', False),
        ),
    ),
    (
        '.offcanvas-xxl',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.offcanvas-xxl.offcanvas-start',
        (
            ('width', 'var(--offcanvas-width)', False),
        ),
    ),
    (
        '.offcanvas-xxl.offcanvas-end',
        (
            ('width', 'var(--offcanvas-width)', False),
        ),
    ),
    (
        '.offcanvas-xxl .offcanvas-body',
        (
            ('flex-grow', '0', False),
        ),
    ),
    (
        '.offcanvas',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.offcanvas.offcanvas-start',
        (
            ('width', 'var(--offcanvas-width)', False),
        ),
    ),
    (
        '.offcanvas.offcanvas-end',
        (
            ('width', 'var(--offcanvas-width)', False),
        ),
    ),
    (
        '.offcanvas-backdrop',
        (
            ('width', '100vw', False),
        ),
    ),
    (
        '.offcanvas-body',
        (
            ('flex-grow', '1', False),
        ),
    ),
    (
        '.icon-link > .bi',
        (
            ('width', '1em', False),
        ),
    ),
    (
        '.ratio',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.ratio > *',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.vstack',
        (
            ('flex', '1 1 auto', False),
        ),
    ),
    (
        '.vr',
        (
            ('width', 'var(--border-width)', False),
        ),
    ),
    (
        '.w-0',
        (
            ('width', '0', True),
        ),
    ),
    (
        '.w-25',
        (
            ('width', '25%', True),
        ),
    ),
    (
        '.w-50',
        (
            ('width', '50%', True),
        ),
    ),
    (
        '.w-75',
        (
            ('width', '75%', True),
        ),
    ),
    (
        '.w-100',
        (
            ('width', '100%', True),
        ),
    ),
    (
        '.w-auto',
        (
            ('width', 'auto', True),
        ),
    ),
    (
        '.mw-0',
        (
            ('max-width', '0', True),
        ),
    ),
    (
        '.mw-25',
        (
            ('max-width', '25%', True),
        ),
    ),
    (
        '.mw-50',
        (
            ('max-width', '50%', True),
        ),
    ),
    (
        '.mw-75',
        (
            ('max-width', '75%', True),
        ),
    ),
    (
        '.mw-100',
        (
            ('max-width', '100%', True),
        ),
    ),
    (
        '.mw-auto',
        (
            ('max-width', 'auto', True),
        ),
    ),
    (
        '.vw-100',
        (
            ('width', '100vw', True),
        ),
    ),
    (
        '.min-vw-100',
        (
            ('min-width', '100vw', True),
        ),
    ),
    (
        '.flex-fill',
        (
            ('flex', '1 1 auto', True),
        ),
    ),
    (
        '.flex-grow-0',
        (
            ('flex-grow', '0', True),
        ),
    ),
    (
        '.flex-grow-1',
        (
            ('flex-grow', '1', True),
        ),
    ),
    (
        '.order-first',
        (
            ('order', '-1', True),
        ),
    ),
    (
        '.order-last',
        (
            ('order', '13', True),
        ),
    ),
    (
        '.order-0',
        (
            ('order', '0', True),
        ),
    ),
    (
        '.order-1',
        (
            ('order', '1', True),
        ),
    ),
    (
        '.order-2',
        (
            ('order', '2', True),
        ),
    ),
    (
        '.order-3',
        (
            ('order', '3', True),
        ),
    ),
    (
        '.order-4',
        (
            ('order', '4', True),
        ),
    ),
    (
        '.order-5',
        (
            ('order', '5', True),
        ),
    ),
    (
        '.order-6',
        (
            ('order', '6', True),
        ),
    ),
    (
        '.order-7',
        (
            ('order', '7', True),
        ),
    ),
    (
        '.order-8',
        (
            ('order', '8', True),
        ),
    ),
    (
        '.order-9',
        (
            ('order', '9', True),
        ),
    ),
    (
        '.order-10',
        (
            ('order', '10', True),
        ),
    ),
    (
        '.order-11',
        (
            ('order', '11', True),
        ),
    ),
    (
        '.order-12',
        (
            ('order', '12', True),
        ),
    ),
    (
        '.flex-basis-0',
        (
            ('flex-basis', '0', True),
        ),
    ),
    (
        '.flex-basis-25',
        (
            ('flex-basis', '25%', True),
        ),
    ),
    (
        '.flex-basis-50',
        (
            ('flex-basis', '50%', True),
        ),
    ),
    (
        '.flex-basis-75',
        (
            ('flex-basis', '75%', True),
        ),
    ),
    (
        '.flex-basis-100',
        (
            ('flex-basis', '100%', True),
        ),
    ),
    (
        '.flex-basis-auto',
        (
            ('flex-basis', 'auto', True),
        ),
    ),
    (
        '.min-w-0',
        (
            ('min-width', '0', True),
        ),
    ),
    (
        '.w-sm-0',
        (
            ('width', '0', True),
        ),
    ),
    (
        '.w-sm-25',
        (
            ('width', '25%', True),
        ),
    ),
    (
        '.w-sm-50',
        (
            ('width', '50%', True),
        ),
    ),
    (
        '.w-sm-75',
        (
            ('width', '75%', True),
        ),
    ),
    (
        '.w-sm-100',
        (
            ('width', '100%', True),
        ),
    ),
    (
        '.w-sm-auto',
        (
            ('width', 'auto', True),
        ),
    ),
    (
        '.mw-sm-0',
        (
            ('max-width', '0', True),
        ),
    ),
    (
        '.mw-sm-25',
        (
            ('max-width', '25%', True),
        ),
    ),
    (
        '.mw-sm-50',
        (
            ('max-width', '50%', True),
        ),
    ),
    (
        '.mw-sm-75',
        (
            ('max-width', '75%', True),
        ),
    ),
    (
        '.mw-sm-100',
        (
            ('max-width', '100%', True),
        ),
    ),
    (
        '.mw-sm-auto',
        (
            ('max-width', 'auto', True),
        ),
    ),
    (
        '.flex-sm-fill',
        (
            ('flex', '1 1 auto', True),
        ),
    ),
    (
        '.flex-sm-grow-0',
        (
            ('flex-grow', '0', True),
        ),
    ),
    (
        '.flex-sm-grow-1',
        (
            ('flex-grow', '1', True),
        ),
    ),
    (
        '.order-sm-first',
        (
            ('order', '-1', True),
        ),
    ),
    (
        '.order-sm-last',
        (
            ('order', '13', True),
        ),
    ),
    (
        '.order-sm-0',
        (
            ('order', '0', True),
        ),
    ),
    (
        '.order-sm-1',
        (
            ('order', '1', True),
        ),
    ),
    (
        '.order-sm-2',
        (
            ('order', '2', True),
        ),
    ),
    (
        '.order-sm-3',
        (
            ('order', '3', True),
        ),
    ),
    (
        '.order-sm-4',
        (
            ('order', '4', True),
        ),
    ),
    (
        '.order-sm-5',
        (
            ('order', '5', True),
        ),
    ),
    (
        '.order-sm-6',
        (
            ('order', '6', True),
        ),
    ),
    (
        '.order-sm-7',
        (
            ('order', '7', True),
        ),
    ),
    (
        '.order-sm-8',
        (
            ('order', '8', True),
        ),
    ),
    (
        '.order-sm-9',
        (
            ('order', '9', True),
        ),
    ),
    (
        '.order-sm-10',
        (
            ('order', '10', True),
        ),
    ),
    (
        '.order-sm-11',
        (
            ('order', '11', True),
        ),
    ),
    (
        '.order-sm-12',
        (
            ('order', '12', True),
        ),
    ),
    (
        '.flex-basis-sm-0',
        (
            ('flex-basis', '0', True),
        ),
    ),
    (
        '.flex-basis-sm-25',
        (
            ('flex-basis', '25%', True),
        ),
    ),
    (
        '.flex-basis-sm-50',
        (
            ('flex-basis', '50%', True),
        ),
    ),
    (
        '.flex-basis-sm-75',
        (
            ('flex-basis', '75%', True),
        ),
    ),
    (
        '.flex-basis-sm-100',
        (
            ('flex-basis', '100%', True),
        ),
    ),
    (
        '.flex-basis-sm-auto',
        (
            ('flex-basis', 'auto', True),
        ),
    ),
    (
        '.w-md-0',
        (
            ('width', '0', True),
        ),
    ),
    (
        '.w-md-25',
        (
            ('width', '25%', True),
        ),
    ),
    (
        '.w-md-50',
        (
            ('width', '50%', True),
        ),
    ),
    (
        '.w-md-75',
        (
            ('width', '75%', True),
        ),
    ),
    (
        '.w-md-100',
        (
            ('width', '100%', True),
        ),
    ),
    (
        '.w-md-auto',
        (
            ('width', 'auto', True),
        ),
    ),
    (
        '.mw-md-0',
        (
            ('max-width', '0', True),
        ),
    ),
    (
        '.mw-md-25',
        (
            ('max-width', '25%', True),
        ),
    ),
    (
        '.mw-md-50',
        (
            ('max-width', '50%', True),
        ),
    ),
    (
        '.mw-md-75',
        (
            ('max-width', '75%', True),
        ),
    ),
    (
        '.mw-md-100',
        (
            ('max-width', '100%', True),
        ),
    ),
    (
        '.mw-md-auto',
        (
            ('max-width', 'auto', True),
        ),
    ),
    (
        '.flex-md-fill',
        (
            ('flex', '1 1 auto', True),
        ),
    ),
    (
        '.flex-md-grow-0',
        (
            ('flex-grow', '0', True),
        ),
    ),
    (
        '.flex-md-grow-1',
        (
            ('flex-grow', '1', True),
        ),
    ),
    (
        '.order-md-first',
        (
            ('order', '-1', True),
        ),
    ),
    (
        '.order-md-last',
        (
            ('order', '13', True),
        ),
    ),
    (
        '.order-md-0',
        (
            ('order', '0', True),
        ),
    ),
    (
        '.order-md-1',
        (
            ('order', '1', True),
        ),
    ),
    (
        '.order-md-2',
        (
            ('order', '2', True),
        ),
    ),
    (
        '.order-md-3',
        (
            ('order', '3', True),
        ),
    ),
    (
        '.order-md-4',
        (
            ('order', '4', True),
        ),
    ),
    (
        '.order-md-5',
        (
            ('order', '5', True),
        ),
    ),
    (
        '.order-md-6',
        (
            ('order', '6', True),
        ),
    ),
    (
        '.order-md-7',
        (
            ('order', '7', True),
        ),
    ),
    (
        '.order-md-8',
        (
            ('order', '8', True),
        ),
    ),
    (
        '.order-md-9',
        (
            ('order', '9', True),
        ),
    ),
    (
        '.order-md-10',
        (
            ('order', '10', True),
        ),
    ),
    (
        '.order-md-11',
        (
            ('order', '11', True),
        ),
    ),
    (
        '.order-md-12',
        (
            ('order', '12', True),
        ),
    ),
    (
        '.flex-basis-md-0',
        (
            ('flex-basis', '0', True),
        ),
    ),
    (
        '.flex-basis-md-25',
        (
            ('flex-basis', '25%', True),
        ),
    ),
    (
        '.flex-basis-md-50',
        (
            ('flex-basis', '50%', True),
        ),
    ),
    (
        '.flex-basis-md-75',
        (
            ('flex-basis', '75%', True),
        ),
    ),
    (
        '.flex-basis-md-100',
        (
            ('flex-basis', '100%', True),
        ),
    ),
    (
        '.flex-basis-md-auto',
        (
            ('flex-basis', 'auto', True),
        ),
    ),
    (
        '.w-lg-0',
        (
            ('width', '0', True),
        ),
    ),
    (
        '.w-lg-25',
        (
            ('width', '25%', True),
        ),
    ),
    (
        '.w-lg-50',
        (
            ('width', '50%', True),
        ),
    ),
    (
        '.w-lg-75',
        (
            ('width', '75%', True),
        ),
    ),
    (
        '.w-lg-100',
        (
            ('width', '100%', True),
        ),
    ),
    (
        '.w-lg-auto',
        (
            ('width', 'auto', True),
        ),
    ),
    (
        '.mw-lg-0',
        (
            ('max-width', '0', True),
        ),
    ),
    (
        '.mw-lg-25',
        (
            ('max-width', '25%', True),
        ),
    ),
    (
        '.mw-lg-50',
        (
            ('max-width', '50%', True),
        ),
    ),
    (
        '.mw-lg-75',
        (
            ('max-width', '75%', True),
        ),
    ),
    (
        '.mw-lg-100',
        (
            ('max-width', '100%', True),
        ),
    ),
    (
        '.mw-lg-auto',
        (
            ('max-width', 'auto', True),
        ),
    ),
    (
        '.flex-lg-fill',
        (
            ('flex', '1 1 auto', True),
        ),
    ),
    (
        '.flex-lg-grow-0',
        (
            ('flex-grow', '0', True),
        ),
    ),
    (
        '.flex-lg-grow-1',
        (
            ('flex-grow', '1', True),
        ),
    ),
    (
        '.order-lg-first',
        (
            ('order', '-1', True),
        ),
    ),
    (
        '.order-lg-last',
        (
            ('order', '13', True),
        ),
    ),
    (
        '.order-lg-0',
        (
            ('order', '0', True),
        ),
    ),
    (
        '.order-lg-1',
        (
            ('order', '1', True),
        ),
    ),
    (
        '.order-lg-2',
        (
            ('order', '2', True),
        ),
    ),
    (
        '.order-lg-3',
        (
            ('order', '3', True),
        ),
    ),
    (
        '.order-lg-4',
        (
            ('order', '4', True),
        ),
    ),
    (
        '.order-lg-5',
        (
            ('order', '5', True),
        ),
    ),
    (
        '.order-lg-6',
        (
            ('order', '6', True),
        ),
    ),
    (
        '.order-lg-7',
        (
            ('order', '7', True),
        ),
    ),
    (
        '.order-lg-8',
        (
            ('order', '8', True),
        ),
    ),
    (
        '.order-lg-9',
        (
            ('order', '9', True),
        ),
    ),
    (
        '.order-lg-10',
        (
            ('order', '10', True),
        ),
    ),
    (
        '.order-lg-11',
        (
            ('order', '11', True),
        ),
    ),
    (
        '.order-lg-12',
        (
            ('order', '12', True),
        ),
    ),
    (
        '.flex-basis-lg-0',
        (
            ('flex-basis', '0', True),
        ),
    ),
    (
        '.flex-basis-lg-25',
        (
            ('flex-basis', '25%', True),
        ),
    ),
    (
        '.flex-basis-lg-50',
        (
            ('flex-basis', '50%', True),
        ),
    ),
    (
        '.flex-basis-lg-75',
        (
            ('flex-basis', '75%', True),
        ),
    ),
    (
        '.flex-basis-lg-100',
        (
            ('flex-basis', '100%', True),
        ),
    ),
    (
        '.flex-basis-lg-auto',
        (
            ('flex-basis', 'auto', True),
        ),
    ),
    (
        '.w-xl-0',
        (
            ('width', '0', True),
        ),
    ),
    (
        '.w-xl-25',
        (
            ('width', '25%', True),
        ),
    ),
    (
        '.w-xl-50',
        (
            ('width', '50%', True),
        ),
    ),
    (
        '.w-xl-75',
        (
            ('width', '75%', True),
        ),
    ),
    (
        '.w-xl-100',
        (
            ('width', '100%', True),
        ),
    ),
    (
        '.w-xl-auto',
        (
            ('width', 'auto', True),
        ),
    ),
    (
        '.mw-xl-0',
        (
            ('max-width', '0', True),
        ),
    ),
    (
        '.mw-xl-25',
        (
            ('max-width', '25%', True),
        ),
    ),
    (
        '.mw-xl-50',
        (
            ('max-width', '50%', True),
        ),
    ),
    (
        '.mw-xl-75',
        (
            ('max-width', '75%', True),
        ),
    ),
    (
        '.mw-xl-100',
        (
            ('max-width', '100%', True),
        ),
    ),
    (
        '.mw-xl-auto',
        (
            ('max-width', 'auto', True),
        ),
    ),
    (
        '.flex-xl-fill',
        (
            ('flex', '1 1 auto', True),
        ),
    ),
    (
        '.flex-xl-grow-0',
        (
            ('flex-grow', '0', True),
        ),
    ),
    (
        '.flex-xl-grow-1',
        (
            ('flex-grow', '1', True),
        ),
    ),
    (
        '.order-xl-first',
        (
            ('order', '-1', True),
        ),
    ),
    (
        '.order-xl-last',
        (
            ('order', '13', True),
        ),
    ),
    (
        '.order-xl-0',
        (
            ('order', '0', True),
        ),
    ),
    (
        '.order-xl-1',
        (
            ('order', '1', True),
        ),
    ),
    (
        '.order-xl-2',
        (
            ('order', '2', True),
        ),
    ),
    (
        '.order-xl-3',
        (
            ('order', '3', True),
        ),
    ),
    (
        '.order-xl-4',
        (
            ('order', '4', True),
        ),
    ),
    (
        '.order-xl-5',
        (
            ('order', '5', True),
        ),
    ),
    (
        '.order-xl-6',
        (
            ('order', '6', True),
        ),
    ),
    (
        '.order-xl-7',
        (
            ('order', '7', True),
        ),
    ),
    (
        '.order-xl-8',
        (
            ('order', '8', True),
        ),
    ),
    (
        '.order-xl-9',
        (
            ('order', '9', True),
        ),
    ),
    (
        '.order-xl-10',
        (
            ('order', '10', True),
        ),
    ),
    (
        '.order-xl-11',
        (
            ('order', '11', True),
        ),
    ),
    (
        '.order-xl-12',
        (
            ('order', '12', True),
        ),
    ),
    (
        '.flex-basis-xl-0',
        (
            ('flex-basis', '0', True),
        ),
    ),
    (
        '.flex-basis-xl-25',
        (
            ('flex-basis', '25%', True),
        ),
    ),
    (
        '.flex-basis-xl-50',
        (
            ('flex-basis', '50%', True),
        ),
    ),
    (
        '.flex-basis-xl-75',
        (
            ('flex-basis', '75%', True),
        ),
    ),
    (
        '.flex-basis-xl-100',
        (
            ('flex-basis', '100%', True),
        ),
    ),
    (
        '.flex-basis-xl-auto',
        (
            ('flex-basis', 'auto', True),
        ),
    ),
    (
        '.w-xxl-0',
        (
            ('width', '0', True),
        ),
    ),
    (
        '.w-xxl-25',
        (
            ('width', '25%', True),
        ),
    ),
    (
        '.w-xxl-50',
        (
            ('width', '50%', True),
        ),
    ),
    (
        '.w-xxl-75',
        (
            ('width', '75%', True),
        ),
    ),
    (
        '.w-xxl-100',
        (
            ('width', '100%', True),
        ),
    ),
    (
        '.w-xxl-auto',
        (
            ('width', 'auto', True),
        ),
    ),
    (
        '.mw-xxl-0',
        (
            ('max-width', '0', True),
        ),
    ),
    (
        '.mw-xxl-25',
        (
            ('max-width', '25%', True),
        ),
    ),
    (
        '.mw-xxl-50',
        (
            ('max-width', '50%', True),
        ),
    ),
    (
        '.mw-xxl-75',
        (
            ('max-width', '75%', True),
        ),
    ),
    (
        '.mw-xxl-100',
        (
            ('max-width', '100%', True),
        ),
    ),
    (
        '.mw-xxl-auto',
        (
            ('max-width', 'auto', True),
        ),
    ),
    (
        '.flex-xxl-fill',
        (
            ('flex', '1 1 auto', True),
        ),
    ),
    (
        '.flex-xxl-grow-0',
        (
            ('flex-grow', '0', True),
        ),
    ),
    (
        '.flex-xxl-grow-1',
        (
            ('flex-grow', '1', True),
        ),
    ),
    (
        '.order-xxl-first',
        (
            ('order', '-1', True),
        ),
    ),
    (
        '.order-xxl-last',
        (
            ('order', '13', True),
        ),
    ),
    (
        '.order-xxl-0',
        (
            ('order', '0', True),
        ),
    ),
    (
        '.order-xxl-1',
        (
            ('order', '1', True),
        ),
    ),
    (
        '.order-xxl-2',
        (
            ('order', '2', True),
        ),
    ),
    (
        '.order-xxl-3',
        (
            ('order', '3', True),
        ),
    ),
    (
        '.order-xxl-4',
        (
            ('order', '4', True),
        ),
    ),
    (
        '.order-xxl-5',
        (
            ('order', '5', True),
        ),
    ),
    (
        '.order-xxl-6',
        (
            ('order', '6', True),
        ),
    ),
    (
        '.order-xxl-7',
        (
            ('order', '7', True),
        ),
    ),
    (
        '.order-xxl-8',
        (
            ('order', '8', True),
        ),
    ),
    (
        '.order-xxl-9',
        (
            ('order', '9', True),
        ),
    ),
    (
        '.order-xxl-10',
        (
            ('order', '10', True),
        ),
    ),
    (
        '.order-xxl-11',
        (
            ('order', '11', True),
        ),
    ),
    (
        '.order-xxl-12',
        (
            ('order', '12', True),
        ),
    ),
    (
        '.flex-basis-xxl-0',
        (
            ('flex-basis', '0', True),
        ),
    ),
    (
        '.flex-basis-xxl-25',
        (
            ('flex-basis', '25%', True),
        ),
    ),
    (
        '.flex-basis-xxl-50',
        (
            ('flex-basis', '50%', True),
        ),
    ),
    (
        '.flex-basis-xxl-75',
        (
            ('flex-basis', '75%', True),
        ),
    ),
    (
        '.flex-basis-xxl-100',
        (
            ('flex-basis', '100%', True),
        ),
    ),
    (
        '.flex-basis-xxl-auto',
        (
            ('flex-basis', 'auto', True),
        ),
    ),
    (
        ':not(.s_popup) > .modal .modal-header, :not(.s_popup) > .modal .modal-footer',
        (
            ('flex', '0 0 auto', False),
        ),
    ),
    (
        '.openerp .oe_form_sheet_width',
        (
            ('max-width', '960px', False),
        ),
    ),
    (
        '.o_web_client .o_form_view .oe_styling_v8 .container',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.openerp .oe_form .oe_styling_v8',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.openerp .oe_form .oe_styling_v8 .container',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.oe_page',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.oe_row',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.oe_row.oe_fit',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.oe_span12',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.oe_span10',
        (
            ('width', '83.33333%', False),
        ),
    ),
    (
        '.oe_span9',
        (
            ('width', '75%', False),
        ),
    ),
    (
        '.oe_span8',
        (
            ('width', '66.66667%', False),
        ),
    ),
    (
        '.oe_span6',
        (
            ('width', '50%', False),
        ),
    ),
    (
        '.oe_span4',
        (
            ('width', '33.33333%', False),
        ),
    ),
    (
        '.oe_span3',
        (
            ('width', '25%', False),
        ),
    ),
    (
        '.oe_span2',
        (
            ('width', '16.66667%', False),
        ),
    ),
    (
        ".oe_row.oe_flex [class*='oe_span']",
        (
            ('width', 'auto', False),
        ),
    ),
    (
        '.oe_row.oe_flex .oe_span12',
        (
            ('max-width', '100%', False),
        ),
    ),
    (
        '.oe_row.oe_flex .oe_span10',
        (
            ('max-width', '83.33333%', False),
        ),
    ),
    (
        '.oe_row.oe_flex .oe_span9',
        (
            ('max-width', '75%', False),
        ),
    ),
    (
        '.oe_row.oe_flex .oe_span8',
        (
            ('max-width', '66.66667%', False),
        ),
    ),
    (
        '.oe_row.oe_flex .oe_span6',
        (
            ('max-width', '50%', False),
        ),
    ),
    (
        '.oe_row.oe_flex .oe_span4',
        (
            ('max-width', '33.33333%', False),
        ),
    ),
    (
        '.oe_row.oe_flex .oe_span3',
        (
            ('max-width', '25%', False),
        ),
    ),
    (
        '.oe_row.oe_flex .oe_span2',
        (
            ('max-width', '16.66667%', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_textarea',
        (
            ('width', '300px', False),
        ),
    ),
    (
        '.oe_styling_v8 .oe_form_layout_table',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.oe_styling_v8 h4.oe_slogan:before, .oe_styling_v8 h4.oe_slogan:after',
        (
            ('width', '100px', False),
        ),
    ),
    (
        '.oe_picture',
        (
            ('max-width', '84%', False),
        ),
    ),
    (
        '.oe_pic_ctr > img.oe_picture',
        (
            ('width', '100%', False),
            ('max-width', 'none', False),
        ),
    ),
    (
        'div.oe_demo span.oe_demo_play',
        (
            ('width', '80px', False),
        ),
    ),
    (
        'div.oe_demo img',
        (
            ('max-width', '100%', False),
            ('width', '100%', False),
        ),
    ),
    (
        'div.oe_demo div.oe_demo_footer',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.oe_row_tab',
        (
            ('min-width', '120px', False),
        ),
    ),
    (
        '.fa-fw',
        (
            ('width', '1.28571429em', False),
        ),
    ),
    (
        '.fa-li',
        (
            ('width', '2.14285714em', False),
        ),
    ),
    (
        '.fa-stack',
        (
            ('width', '2em', False),
        ),
    ),
    (
        '.fa-stack-1x, .fa-stack-2x',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.visually-hidden',
        (
            ('width', '1px', False),
        ),
    ),
    (
        '.col',
        (
            ('-webkit-box-flex', '1', False),
            ('flex', '1 0 0%', False),
        ),
    ),
    (
        '.footer .row, .footer .col-lg-3, .footer .col-lg-4, .footer .col-lg-6',
        (
            ('-webkit-box-flex', '1', True),
        ),
    ),
    (
        '.footer .col-lg-3, .footer .col-lg-4, .footer .col-lg-6',
        (
            ('flex', '0 0 auto', False),
        ),
    ),
    (
        '.footer .col-lg-3',
        (
            ('width', '25%', False),
        ),
    ),
    (
        '.footer .col-lg-4',
        (
            ('width', '33.33333333%', False),
        ),
    ),
    (
        '.footer .col-lg-6',
        (
            ('width', '50%', False),
        ),
    ),
    (
        '.flex-grow-0',
        (
            ('-webkit-box-flex', '0', False),
        ),
    ),
    (
        '.flex-grow-1',
        (
            ('-webkit-box-flex', '1', False),
        ),
    ),
    (
        '.flex-shrink-0',
        (
            ('-webkit-box-flex-group', '0', False),
        ),
    ),
    (
        '.flex-shrink-1',
        (
            ('-webkit-box-flex-group', '1', False),
        ),
    ),
    (
        'ul.o_checklist > li:not(.oe-nested):before',
        (
            ('width', '14px', False),
        ),
    ),
    (
        '.o_company_logo',
        (
            ('max-width', '12rem', False),
        ),
    ),
    (
        '.o_company_logo_small',
        (
            ('max-width', '11rem', False),
        ),
    ),
    (
        '.o_company_logo_big',
        (
            ('max-width', '16rem', False),
        ),
    ),
    (
        '.o_shape_bubble_1 ~ table .o_company_logo',
        (
            ('max-width', '9rem', False),
        ),
    ),
    (
        '.o_td_quantity',
        (
            ('min-width', '7rem', False),
            ('max-width', '9rem', False),
        ),
    ),
    (
        '.o_text_columns',
        (
            ('max-width', '100%', True),
        ),
    ),
    (
        '.oe-tabs',
        (
            ('max-width', '40px', False),
            ('width', '40px', False),
        ),
    ),
    (
        'html, body',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '#wrapwrap table.table.table-bordered td, .o_editable table.table.table-bordered td',
        (
            ('min-width', '20px', False),
        ),
    ),
    (
        'ul.o_checklist > li:not(.oe-nested)::before',
        (
            ('width', '13px', False),
        ),
    ),
    (
        '.fa.card-img, .fa.card-img-top, .fa.card-img-bottom',
        (
            ('width', 'auto', False),
        ),
    ),
    (
        'div.media_iframe_video',
        (
            ('min-width', '100px', False),
        ),
    ),
    (
        'div.media_iframe_video iframe',
        (
            ('width', '100%', False),
        ),
    ),
    (
        'div.media_iframe_video .media_iframe_video_size',
        (
            ('width', '100%', False),
        ),
    ),
    (
        'div.media_iframe_video .css_editable_mode_display',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.o_nocontent_help',
        (
            ('max-width', '650px', False),
        ),
    ),
    (
        '.o_we_search_prompt',
        (
            ('width', '100%', False),
        ),
    ),
    (
        '.o_we_search_prompt > h2, .o_we_search_prompt > .h2',
        (
            ('max-width', '500px', False),
        ),
    ),
    (
        '.o_we_search_prompt::before',
        (
            ('width', '100px', False),
        ),
    ),
    (
        '.o_container_small',
        (
            ('max-width', '720px', False),
        ),
    ),
    (
        '#qrcode_odoo_logo',
        (
            ('width', '18%', False),
        ),
    ),
    (
        '.o_label_page.o_label_dymo',
        (
            ('width', '57mm', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_legend',
        (
            ('max-width', '1000px', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_legend_line',
        (
            ('flex', '0 1 auto', False),
            ('width', '29%', False),
            ('min-width', '200px', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_legend_line > .o_report_stock_rule_legend_label',
        (
            ('flex', '1 1 auto', False),
            ('width', '30%', False),
            ('min-width', '100px', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_legend_line > .o_report_stock_rule_legend_symbol',
        (
            ('flex', '1 1 auto', False),
            ('width', '70%', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_line',
        (
            ('flex', '1 1 auto', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_arrow',
        (
            ('flex', '0 0 auto', False),
            ('width', '20px', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_vertical_bar',
        (
            ('flex', '0 0 auto', False),
            ('width', '2px', False),
        ),
    ),
    (
        '.o_report_stock_rule .o_report_stock_rule_symbol_cell > div',
        (
            ('max-width', '200px', False),
        ),
    ),
    (
        '.o_stock_report_header_row > div',
        (
            ('flex', '1', False),
            ('-webkit-flex', '1', False),
            ('-webkit-box-flex', '1', False),
            ('min-width', '150px', False),
        ),
    ),
    (
        '[name="so_total_summary"] div#total',
        (
            ('width', '100%', False),
        ),
    ),
)


#: Every rule in the bundle that makes an element `inline-block`, selectors
#: intact and the CSS property under its own name.
#:
#: The layout slice above keeps a rule only when its `display` is one of the
#: flex spellings, so `display: inline-block` reached nothing and the parser
#: fell back on the element's user-agent default. For `li.list-inline-item`
#: that default is `list-item`, which is a text block, so the three items of
#: The standard page counter -- `<span class="page"/>`, `/`,
#: `<span class="topage"/>` at
#: lays them on one line.
#:
#: `margin-right` travels with it because it is the space between two inline
#: items, and a slice with the display and not the spacing would describe
#: half the rule -- `.list-inline-item:not(:last-child)` states 0.5rem.
#:
#: Derived by `tools/derive_layout_rules.py`, 44 rules.
INLINE_LEVEL_RULES = (
    ('div.o_employee_cv .o_sidebar', (('margin-left', '500px', False), ('display', 'inline-block', False))),
    ('div.o_employee_cv .o_company', (('display', 'inline-block', False),)),
    ('div.o_employee_cv .o_main_panel', (('display', 'inline-block', False),)),
    ('div.o_employee_cv .o_main_panel .o_main_panel_title .o_main_panel_icon', (('margin-right', '8px', False), ('display', 'inline-block', False))),
    ('div.o_employee_cv .o_main_panel .o_main_panel_resume_title .o_main_panel_resume_title_job', (('display', 'inline-block', False),)),
    ('label', (('display', 'inline-block', False),)),
    ('output', (('display', 'inline-block', False),)),
    ('.list-inline-item', (('display', 'inline-block', False),)),
    ('.figure', (('display', 'inline-block', False),)),
    ('.form-check-inline', (('display', 'inline-block', False), ('margin-right', '1rem', False))),
    ('.btn', (('display', 'inline-block', False),)),
    ('.dropdown-toggle::after', (('display', 'inline-block', False), ('margin-left', '3.4px', False))),
    ('.dropup .dropdown-toggle::after', (('display', 'inline-block', False), ('margin-left', '3.4px', False))),
    ('.dropend .dropdown-toggle::after', (('display', 'inline-block', False), ('margin-left', '3.4px', False))),
    ('.dropstart .dropdown-toggle::after', (('display', 'inline-block', False), ('margin-left', '3.4px', False))),
    ('.dropstart .dropdown-toggle::before', (('display', 'inline-block', False), ('margin-right', '3.4px', False))),
    ('.navbar-toggler-icon', (('display', 'inline-block', False),)),
    ('.badge', (('display', 'inline-block', False),)),
    ('.carousel-control-prev-icon, .carousel-control-next-icon', (('display', 'inline-block', False),)),
    ('.spinner-grow, .spinner-border', (('display', 'inline-block', False),)),
    ('.placeholder', (('display', 'inline-block', False),)),
    ('.placeholder.btn::before', (('display', 'inline-block', False),)),
    ('.vr', (('display', 'inline-block', False),)),
    ('.d-inline-block', (('display', 'inline-block', True),)),
    ('.d-sm-inline-block', (('display', 'inline-block', True),)),
    ('.d-md-inline-block', (('display', 'inline-block', True),)),
    ('.d-lg-inline-block', (('display', 'inline-block', True),)),
    ('.d-xl-inline-block', (('display', 'inline-block', True),)),
    ('.d-xxl-inline-block', (('display', 'inline-block', True),)),
    ('.d-print-inline-block', (('display', 'inline-block', True),)),
    (".oe_row.oe_flex [class*='oe_span']", (('display', 'inline-block', False),)),
    ('.oe_button', (('display', 'inline-block', False),)),
    ('.oe_styling_v8 h4.oe_slogan:before, .oe_styling_v8 h4.oe_slogan:after', (('display', 'inline-block', False),)),
    ('.oe_row_tab', (('display', 'inline-block', False),)),
    ('.fa', (('display', 'inline-block', False),)),
    ('.fa-stack', (('display', 'inline-block', False),)),
    ('.oi', (('display', 'inline-block', False),)),
    ('.o_portal_address span[itemprop="telephone"]', (('display', 'inline-block', False),)),
    ('.oe-tabs', (('display', 'inline-block', False),)),
    ('img.o_we_custom_image', (('display', 'inline-block', False),)),
    ('.o_content .o_table > tbody .o_cell_td > .o_last_comment', (('display', 'inline-block', False),)),
    ('.o_content .o_table > tbody .o_line_name', (('display', 'inline-block', False),)),
    ('.o_content .o_table > tbody .o_status_badge', (('display', 'inline-block', False), ('margin-left', '8px', False))),
    ('.o_overflow_value', (('display', 'inline-block', False),)),
)


#: What the bundle says about `white-space`. The engine collapses a run of
#: spaces to one unless the value is `pre` or `pre-wrap`
#: (`tests/test_ignorable_whitespace.py`: "Pre and prewrap do not collapse
#: whitespace"), so this is what decides whether the whitespace between two
#: inline-level siblings is a single space or is kept verbatim.
#:
#: Derived by `tools/derive_layout_rules.py`, 31 rules.
WHITE_SPACE_RULES = (
    ('div.o_employee_cv .o_main_panel .o_main_panel_resume_title .o_main_panel_resume_title_dates', (('white-space', 'nowrap', False),)),
    ('.form-floating > label', (('white-space', 'nowrap', False),)),
    ('.input-group-text', (('white-space', 'nowrap', False),)),
    ('.dropdown-toggle', (('white-space', 'nowrap', False),)),
    ('.dropdown-item', (('white-space', 'nowrap', False),)),
    ('.dropdown-header', (('white-space', 'nowrap', False),)),
    ('.navbar-brand', (('white-space', 'nowrap', False),)),
    ('.badge', (('white-space', 'nowrap', False),)),
    ('.progress-bar', (('white-space', 'nowrap', False),)),
    ('.tooltip', (('white-space', 'normal', False),)),
    ('.popover', (('white-space', 'normal', False),)),
    ('.text-truncate', (('white-space', 'nowrap', False),)),
    ('.text-wrap', (('white-space', 'normal', True),)),
    ('.text-nowrap', (('white-space', 'nowrap', True),)),
    ('.text-prewrap', (('white-space', 'pre-wrap', True),)),
    ('.o_portal_address span[itemprop="telephone"]', (('white-space', 'nowrap', False),)),
    ('span[itemprop="streetAddress"]', (('white-space', 'normal', False),)),
    ('.oe-tabs', (('white-space', 'pre-wrap', False),)),
    ('span[data-oe-type="monetary"]', (('white-space', 'nowrap', False),)),
    ('pre', (('white-space', 'pre-wrap', False),)),
    ('.o_label_page.o_label_dymo span, .o_label_page.o_label_dymo div', (('white-space', 'nowrap', False),)),
    ('.o_overflow', (('white-space', 'normal', True),)),
    ('.o_content .o_table > thead', (('white-space', 'nowrap', False),)),
    ('.o_content .o_table > tbody', (('white-space', 'nowrap', False),)),
    ('.o_content .o_table > tbody .o_cell_td > .o_line_cell_value_number', (('white-space', 'nowrap', False),)),
    ('.o_content .o_table > tbody .o_cell_td > .o_last_comment', (('white-space', 'pre-wrap', False),)),
    ('.o_content .o_table > tbody .o_status_badge', (('white-space', 'nowrap', False),)),
    ('.o_overflow_value', (('white-space', 'normal', True),)),
    ('.o_overflow_name', (('white-space', 'normal', True),)),
    ('body[dir="rtl"] .o_line_name_level', (('white-space', 'normal', True),)),
)


#: Every rule in the bundle that makes an element `display: none`, selectors
#: intact and the property under its own CSS name.
#:
#: An element with no display builds no renderer -- the bounded `NONE`
#: contract is pinned by `tests/test_display_none.py` -- and a node whose parent has no
#: renderer cannot build one either, whatever its own display says
#: (the parent-renderer guard): a node without a rendered parent is skipped. So the
#: suppression covers the whole subtree and a `display: block` child does not
#: never reached for a hidden cell and it contributes no effective column.
#:
#: This is `display` only. `visibility: hidden` keeps its box and its
#: geometry and merely does not paint, and `visibility: collapse` is its own
#: distinction.
#:
#: Derived by `tools/derive_layout_rules.py`, 48 rules.
HIDDEN_RULES = (
    ('[list]:not([type="date"]):not([type="datetime-local"]):not([type="month"]):not([type="week"]):not([type="time"])::-webkit-calendar-picker-indicator', (('display', 'none', True),)),
    ('[hidden]', (('display', 'none', True),)),
    ('.valid-feedback', (('display', 'none', False),)),
    ('.valid-tooltip', (('display', 'none', False),)),
    ('.invalid-feedback', (('display', 'none', False),)),
    ('.invalid-tooltip', (('display', 'none', False),)),
    ('.collapse:not(.show)', (('display', 'none', False),)),
    ('.dropdown-menu', (('display', 'none', False),)),
    ('.dropstart .dropdown-toggle::after', (('display', 'none', False),)),
    ('.tab-content > .tab-pane', (('display', 'none', False),)),
    ('.navbar-expand-sm .navbar-toggler', (('display', 'none', False),)),
    ('.navbar-expand-sm .offcanvas .offcanvas-header', (('display', 'none', False),)),
    ('.navbar-expand-md .navbar-toggler', (('display', 'none', False),)),
    ('.navbar-expand-md .offcanvas .offcanvas-header', (('display', 'none', False),)),
    ('.navbar-expand-lg .navbar-toggler', (('display', 'none', False),)),
    ('.navbar-expand-lg .offcanvas .offcanvas-header', (('display', 'none', False),)),
    ('.navbar-expand-xl .navbar-toggler', (('display', 'none', False),)),
    ('.navbar-expand-xl .offcanvas .offcanvas-header', (('display', 'none', False),)),
    ('.navbar-expand-xxl .navbar-toggler', (('display', 'none', False),)),
    ('.navbar-expand-xxl .offcanvas .offcanvas-header', (('display', 'none', False),)),
    ('.navbar-expand .navbar-toggler', (('display', 'none', False),)),
    ('.navbar-expand .offcanvas .offcanvas-header', (('display', 'none', False),)),
    ('.badge:empty', (('display', 'none', False),)),
    ('.toast:not(.show)', (('display', 'none', False),)),
    ('.modal', (('display', 'none', False),)),
    ('.popover-header:empty', (('display', 'none', False),)),
    ('.carousel-item', (('display', 'none', False),)),
    ('.offcanvas-sm .offcanvas-header', (('display', 'none', False),)),
    ('.offcanvas-md .offcanvas-header', (('display', 'none', False),)),
    ('.offcanvas-lg .offcanvas-header', (('display', 'none', False),)),
    ('.offcanvas-xl .offcanvas-header', (('display', 'none', False),)),
    ('.offcanvas-xxl .offcanvas-header', (('display', 'none', False),)),
    ('.d-empty-none:empty', (('display', 'none', True),)),
    ('.d-none', (('display', 'none', True),)),
    ('.d-sm-none', (('display', 'none', True),)),
    ('.d-md-none', (('display', 'none', True),)),
    ('.d-lg-none', (('display', 'none', True),)),
    ('.d-xl-none', (('display', 'none', True),)),
    ('.d-xxl-none', (('display', 'none', True),)),
    ('.d-print-none', (('display', 'none', True),)),
    ('.modal-backdrop', (('display', 'none', False),)),
    ('.openerp .oe_form .oe_styling_v8 .oe_websiteonly', (('display', 'none', False),)),
    ('.oe_hidden', (('display', 'none', True),)),
    ('.d-print-none', (('display', 'none', False),)),
    ('.css_non_editable_mode_hidden', (('display', 'none', True),)),
    ('.editor_enable .css_editable_mode_hidden', (('display', 'none', True),)),
    ('div.media_iframe_video .css_editable_mode_display', (('display', 'none', False),)),
    ('.o_d_none', (('display', 'none', False),)),
)

#: What the bundle says about casing, derived the same way and for the same
#: reason. The parser looked up the classes `text-uppercase` and friends, so
#: `.o_table_bold table thead th { text-transform: uppercase }` never reached
#: prints `DESCRIPTION`. Those utility classes are themselves rules here, so
#: asking the stylesheet subsumes the lookup rather than joining it.
TEXT_TRANSFORM_RULES = (
    (
        '.initialism',
        (
            ('text-transform', 'uppercase', False),
        ),
    ),
    (
        '.text-lowercase',
        (
            ('text-transform', 'lowercase', True),
        ),
    ),
    (
        '.text-uppercase',
        (
            ('text-transform', 'uppercase', True),
        ),
    ),
    (
        '.text-capitalize',
        (
            ('text-transform', 'capitalize', True),
        ),
    ),
    (
        '.o_table_bold table:not(.o_ignore_layout_styling) thead th',
        (
            ('text-transform', 'uppercase', False),
        ),
    ),
    (
        '.o_table_boxed table:not(.o_ignore_layout_styling) thead, .o_table_boxed-rounded table:not(.o_ignore_layout_styling) thead',
        (
            ('text-transform', 'uppercase', False),
        ),
    ),
)

TABLE_STYLE_RULES = (
    (':root', (('--border-width', '1px', False), ('--emphasis-color-rgb', '0, 0, 0', False))),
    ('body', (('color', '#212529', False),)),
    ('thead, tbody, tfoot, tr, td, th', tuple((declaration for side in ('top', 'right', 'bottom', 'left') for declaration in ((f'border-{side}-color', 'inherit', False), (f'border-{side}-style', 'solid', False), (f'border-{side}-width', '0', False))))),
    ('.table', (('--table-color-type', 'initial', False), ('--table-bg-type', 'initial', False), ('--table-color-state', 'initial', False), ('--table-bg-state', 'initial', False), ('--table-color', '#212529', False), ('--table-bg', 'transparent', False), ('--table-border-color', '#212529', False), ('--table-accent-bg', 'transparent', False), ('--table-striped-color', 'inherit', False), ('--table-striped-bg', 'rgba(var(--emphasis-color-rgb), 0.01)', False), ('border-top-color', 'var(--table-border-color)', False), ('border-right-color', 'var(--table-border-color)', False), ('border-bottom-color', 'var(--table-border-color)', False), ('border-left-color', 'var(--table-border-color)', False))),
    ('.table > :not(caption) > * > *', (('padding-top', '0.5rem', False), ('padding-right', '0.5rem', False), ('padding-bottom', '0.5rem', False), ('padding-left', '0.5rem', False), ('color', '#212529', False), ('background-color', 'transparent', False), ('border-bottom-width', 'var(--border-width)', False), ('box-shadow', 'inset 0 0 0 9999px var(--table-bg-state, var(--table-bg-type, var(--table-accent-bg)))', False))),
    ('.table-sm > :not(caption) > * > *', (('padding-top', '0.25rem', False), ('padding-right', '0.25rem', False), ('padding-bottom', '0.25rem', False), ('padding-left', '0.25rem', False))),
    ('.table-striped > tbody > tr:nth-of-type(even) > *', (('--table-color-type', 'var(--table-striped-color)', False), ('--table-bg-type', 'var(--table-striped-bg)', False))),
    ('.table-bordered > :not(caption) > *', (('border-top-width', '1px', False), ('border-right-width', '0', False), ('border-bottom-width', '1px', False), ('border-left-width', '0', False))),
    ('.table-bordered > :not(caption) > * > *', (('border-top-width', '0', False), ('border-right-width', '1px', False), ('border-bottom-width', '0', False), ('border-left-width', '1px', False))),
    ('.table-borderless > :not(caption) > * > *', (('border-top-width', '0', False), ('border-right-width', '0', False), ('border-bottom-width', '0', False), ('border-left-width', '0', False))),
    ('.o_table_standard table:not(.o_ignore_layout_styling) th:first-child', (('padding-left', '0', False),)),
    ('.o_table_standard table:not(.o_ignore_layout_styling) td:first-child', (('padding-left', '0', False),)),
    ('.o_table_standard table:not(.o_ignore_layout_styling) th:last-child', (('padding-right', '0', False),)),
    ('.o_table_standard table:not(.o_ignore_layout_styling) td:last-child', (('padding-right', '0', False),)),
    ('.o_table_bold table:not(.o_ignore_layout_styling) tbody tr td', (('padding-top', '1rem', False), ('padding-right', '0.5rem', False), ('padding-bottom', '1rem', False), ('padding-left', '0.5rem', False))),
    ('.o_table tr td', (('padding-top', '0.5rem', False), ('padding-right', '0.5rem', False), ('padding-bottom', '0.5rem', False), ('padding-left', '0.5rem', False))),
)

# --- headings ----------------------------------------------------------
#: Heading sizes, in rem, as the report stylesheet states them. Compiled the
#: same way as the table skins: resolved once by the stylesheet compiler
#: over the pinned public bundle, then shipped.
#:
#: The reset in `report_assets_pdf` zeroes these to `font-size: 100%` and the
#: Bootstrap rules in `report_assets_common` give them back, so which one wins
#: is decided purely by bundle order -- and reading the bundles in the wrong
#: order collapses every heading to body size.
HEADING_SIZES_REM = {
    "h1": 2.5,
    "h2": 2.0,
    "h3": 1.75,
    "h4": 1.5,
    "h5": 1.25,
    "h6": 1.0,
}
#: Odoo puts the document title in an `h2` and its number in a sibling span,
#: so both take the same size.
DOCUMENT_TITLE_REM = HEADING_SIZES_REM["h2"]

#: Line height as a multiple of the font size, as the stylesheet states it:
#: `body { line-height: 1.5 }` and Bootstrap's `$headings-line-height: 1.2`.
#: A heading is set tighter than body text, which is why reusing the body
#: metric for it -- or, as the planner did, adding a flat 1.2mm to the font
#: size -- puts a 20pt title on the wrong baseline.
LINE_HEIGHT_RATIO = 1.5
HEADING_LINE_HEIGHT_RATIO = 1.2

#: Bootstrap's `line-height` utilities, resolved off the report bundle rather
#: than read out of Bootstrap's documentation. Odoo's partner address puts
#: `lh-sm` on the street span, so four of the six lines in every customer
#: address step tighter than the body does; treating the class as inert cost
#: 1.14mm per line.
LINE_HEIGHT_CLASSES = {
    "lh-1": 1.0,
    "lh-sm": 1.25,
    "lh-base": 1.5,
    "lh-lg": 2.0,
}


def line_height_ratio(classes) -> float | None:
    """The `lh-*` ratio a class list states, if any."""
    for name in classes:
        ratio = LINE_HEIGHT_CLASSES.get(name)
        if ratio is not None:
            return ratio
    return None

#: WebKit's **user-agent** link colour, not Bootstrap's.
#:
#: The bundle's only rule that would colour an anchor is
#: `a { color: rgba(var(--link-color-rgb), var(--link-opacity, 1)) }`, and
#: wkhtmltopdf 0.12.6 does not implement custom properties, so it drops the
#: whole declaration because this engine does not resolve custom properties.
#: What that exposes is the UA stylesheet's `-webkit-link`, which is
#: #0000EE. Dropping an author declaration falls through to the UA sheet,
#: not to inheritance, which is the part worth remembering: the guess on
#: record was that links would inherit body colour.
#:
#: terms URL [0, 0, 238] where this engine painted [1, 126, 132]. The old
#: value was #017e84, which occurs once in the bundle -- under
#: `.o_cc .dropdown-menu .dropdown-item-text .text-muted a`, a selector no
#: report body can match. So it was wrong twice over: read off a rule that
#:
#: Only `a[href]` takes it: `a:not([href]):not([class])` resets to
#: `inherit`, and that rule outranks the plain `a` one.
LINK_COLOUR = "#0000EE"

#: The inherited root paint in the shipped report bundle.  Ordinary elements
#: have no colour of their own; they inherit the body's computed colour, which
#: ``body { color: #111827 }`` states literally.
#:
#: Headings are deliberately not an exception.  Bootstrap does assign
#: ``--heading-color`` to h1--h6, but it does so as
#: ``color: var(--heading-color)``, and wkhtmltopdf 0.12.6 does not implement
#: custom properties: it drops the declaration and the heading inherits this
#: value.  There is no separate heading constant, because resolving that
#: variable the way a modern browser does is what put a heading at #000 where
#: ``var()`` value, 102 of them ``color``, so this is a general property of the
#: ``.o_company_1_layout h2 { color: #5e4766 }`` is literal.
BODY_TEXT_RGB = (33 / 255, 37 / 255, 41 / 255)
#: wkhtmltopdf's initial text paint for a prepared region that carries no
#: report stylesheet at all.  This is deliberately distinct from
#: ``BODY_TEXT_RGB``: a custom report body may be a bare HTML fragment while
#: its independently rendered header/footer load the normal report bundle.
UNSTYLED_TEXT_RGB = (0.0, 0.0, 0.0)

#: Bootstrap's `.border-*` utilities, as the report bundle resolves them.
#: Only `border-top` appears in the stock report closure -- it is what puts
#: the rule above the footer text -- but the width and colour are shared by
#: all of them.
#:
#: The `hr` chain is worth reading once, because its three parts come from
#: three different places. `hr { color: inherit; border-top:
#: var(--border-width) solid; opacity: 0.25 }` supplies the colour by
#: inheritance and the opacity literally, but its *width* is var()-valued
#: and wkhtml discards it -- so the width comes from the separate literal
#: `hr { border: 1px solid }` further down the bundle, which is why
#: BLOCK_RULE_PT is one pixel rather than Bootstrap's `--border-width`.
BLOCK_RULE_PT = 1.0 * 72.0 / PX_PER_INCH
BLOCK_RULE_RGB = "#212529"
BLOCK_RULE_OPACITY = 0.25
#: dash/gap lengths relative to the rendered rule width.  ReportLab consumes
#: the same dimensionless multiples once the edge width is known.
BORDER_DASH_MULTIPLIERS = {
    "dashed": (1.0, 2.0),
    "dotted": (1.0, 1.0),
}
#: A deliberately bounded Bootstrap utility vocabulary, compiled from the
#: report bundle. These are framework words, not report signatures.
UTILITY_BORDER_WIDTH_PX = {
    "border-bottom": 1.0,
    "border-2": 2.0,
}
UTILITY_RADIUS_REM = {
    "rounded": 0.25,
}
#: Bootstrap's `.text-muted` utility after variables resolve in the shipped
#: Odoo report bundle. It is bounded framework vocabulary, not company paint.
UTILITY_TEXT_RGB = {
    "text-muted": (95 / 255, 99 / 255, 111 / 255),
}

#: Positioned page-art insets compiled from the stock report bundle.  The SVG
#: carries its circle geometry, while this selector positions its 1100px box;
#: neither source can substitute for the other.
BUBBLE_CIRCLE_POSITION_PX = (-870.0, -450.0)  # top, right


def utility_box_declarations(classes) -> dict[str, str]:
    """Resolve the bounded box utilities the runtime promises to read.

    Bootstrap emits these declarations with ``!important``, so they win over
    ordinary inline declarations when the parser merges the two channels.
    """
    names = set(classes)
    declarations = {}
    if "border-bottom" in names:
        width = (
            UTILITY_BORDER_WIDTH_PX["border-2"]
            if "border-2" in names
            else UTILITY_BORDER_WIDTH_PX["border-bottom"]
        )
        declarations.update({
            "border-bottom-width": f"{width:g}px",
            "border-bottom-style": "solid",
            "border-bottom-color": BLOCK_RULE_RGB,
        })
    for name in names:
        match = GAP_RE.match(name)
        if match:
            # Bootstrap's flex gap, on the same $spacers scale as `m*`/`p*`.
            # The IR has carried a `gap_mm` since it was written and nothing
            # ever supplied it, so every flex row used the dataclass default
            # regardless of what the row actually declared.
            declarations["gap"] = f"{SPACER_REM[int(match.group(1))]:g}rem"
            break
    for name in ("center", "start", "end", "baseline", "stretch"):
        if f"align-items-{name}" in names:
            declarations["align-items"] = name
            break
    if "rounded" in names:
        declarations["border-radius"] = f'{UTILITY_RADIUS_REM["rounded"]:g}rem'
    return declarations


def utility_text_declarations(classes) -> dict[str, str]:
    """Resolve bounded text-paint utilities compiled from the report bundle."""
    for name in classes:
        if name not in UTILITY_TEXT_RGB:
            continue
        return {
            "color": "#" + "".join(
                f"{round(channel * 255):02x}"
                for channel in UTILITY_TEXT_RGB[name]
            )
        }
    return {}

#: Cell width constraints the report stylesheet states by class, in rem.
#: `(min, max)`; `None` for "unconstrained". Compiled off the bundle like
#: the heading sizes -- an HTML table sizes its columns from content, and
#: these are the only places Odoo overrides that.
CELL_WIDTH_REM = {
    "o_td_quantity": (7.0, 9.0),
}

#: The bottom margin the stylesheet gives an element that carries no
#: spacing class, in rem. Compiled off the bundle like the table skins.
#:
#: This is the difference between spacing a document and inventing a gap.
#: The adapter read Bootstrap's `mb-*` utilities and nothing else, so any
#: block without one -- the line table, a paragraph, the totals band -- fell
#: back on a made-up constant. CSS has no such constant: a `<table class=
#: "table">` has `margin-bottom: 1rem` and a `<div>` has none, and the gap
#: between two blocks is whichever of their facing margins is larger.
#: Anything not named here is zero, because the reset says so -- it is a
#: lookup with a default, not a list of special cases.
ELEMENT_MARGIN_BOTTOM_REM = {
    "p": 1.0,
    "table": 1.0,   # from `.table`; a bare <table> has none, and Odoo's
                    # report tables all carry the class
    "ul": 1.0,
    "ol": 1.0,
    "address": 1.0,
    "h1": 0.75,
    "h2": 0.75,
    "h3": 0.75,
    "h4": 0.75,
    "h5": 0.75,
    "h6": 0.75,
}

# --- images ------------------------------------------------------------
#: The report CSS constrains the logo's *height*; its width follows the
#: image's own aspect ratio. Modelling it as a width is why a wide logo came
#: out too narrow and a tall one too wide.
#: The `max-width`/`max-height` the stylesheet caps each logo class at, in
#: rem. A cap is not a size: the drawn box is the image's own dimensions
#: scaled down to fit inside both, which is why the aspect has to come from
#: the image and only the cap can come from here.
LOGO_CAPS_REM = {
    "o_company_logo": (12.0, 6.0),
    "o_company_logo_small": (11.0, 4.0),
    "o_company_logo_big": (16.0, 8.0),
    "o_logo": (12.0, 6.0),
}
#: `.o_shape_bubble_1 ~ table .o_company_logo` -- a sibling rule that fires
#: only when the Bubble layout's page art precedes the logo's table, and
#: halves the cap. The classes are not orthogonal to the layout.
LOGO_CAPS_REM_BY_LAYOUT = {
    "bubble": {"o_company_logo": (9.0, 3.0)},
}

LOGO_HEIGHTS_MM = {
    "o_company_logo_big": 15.3,
    "o_company_logo_small": 9.4,
    "o_company_logo": 11.0,
    "o_logo": 11.0,
}

# --- class grammar -----------------------------------------------------
COL_RE = re.compile(r"^col(?:-(?:sm|md|lg|xl|xxl))?-(\d+)$")
OFFSET_RE = re.compile(r"^offset(?:-(?:sm|md|lg|xl|xxl))?-(\d+)$")
#: Bootstrap spacing utilities: `mt-3`, `px-2`, `mb-0`, `mt-n3`, `m-0`, ...
SPACING_RE = re.compile(r"^([mp])([tbsexy])?-(n)?([0-5])$")
#: Odoo 16-era legacy spacing that survives in some templates: `mb32` = 32px.
LEGACY_SPACING_RE = re.compile(r"^(m|p)(t|b|l|r)?(\d{1,3})$")
#: Bootstrap width, responsive-display and font-scale utilities.
WIDTH_RE = re.compile(r"^[wh]-(25|50|75|100|auto)$")
DISPLAY_RE = re.compile(r"^d-(?:sm|md|lg|xl|xxl|print)-[a-z-]+$")
FONT_SIZE_RE = re.compile(r"^fs-[1-6]$")

#: `.o_snail_mail .address` reserves the address window of a window envelope.
SNAIL_MAIL_ADDRESS_PADDING_PX = 42.0

#: Bootstrap's flex/grid gap utilities, on the $spacers scale.
GAP_RE = re.compile(r"^gap-([0-5])$")

#: Bootstrap $spacers, in rem.
SPACER_REM = {0: 0.0, 1: 0.25, 2: 0.5, 3: 1.0, 4: 1.5, 5: 3.0}


def spacer_mm(step: int, *, px_per_inch: float = PX_PER_INCH) -> float:
    """Millimetres for a Bootstrap spacing step (`-3` -> 1rem)."""
    return SPACER_REM[step] * MM_PER_REM * PX_PER_INCH / px_per_inch


@dataclass(frozen=True, slots=True)
class BoxSpacing:
    """Resolved Bootstrap margin/padding for one element, in millimetres.

    ``None`` means the element said nothing about that side, which is not the
    same as saying zero: an unspecified side keeps the engine default, while
    ``mb-0`` is an explicit request for no gap.
    """

    margin_top: float | None = None
    margin_bottom: float | None = None
    margin_start: float | None = None
    margin_end: float | None = None
    padding_top: float | None = None
    padding_bottom: float | None = None
    padding_start: float | None = None
    padding_end: float | None = None

    @property
    def pulls_up(self) -> bool:
        """True for `mt-n*`: the block is pulled onto the one above it."""
        return (self.margin_top or 0.0) < 0.0


_SIDES = {
    None: ("top", "bottom", "start", "end"),
    "t": ("top",),
    "b": ("bottom",),
    "s": ("start",),
    "e": ("end",),
    "x": ("start", "end"),
    "y": ("top", "bottom"),
}
_LEGACY_SIDES = {
    None: _SIDES[None],
    "t": ("top",),
    "b": ("bottom",),
    "l": ("start",),
    "r": ("end",),
}


def box_spacing(classes, *, px_per_inch: float = PX_PER_INCH) -> BoxSpacing:
    """Resolve the Bootstrap spacing utilities on one element."""
    values: dict[str, float | None] = {
        f"{kind}_{side}": None
        for kind in ("margin", "padding")
        for side in ("top", "bottom", "start", "end")
    }
    for cls in classes:
        match = SPACING_RE.match(cls)
        if match:
            prefix, side, negative, step = match.groups()
            amount = spacer_mm(int(step), px_per_inch=px_per_inch)
            if negative:
                amount = -amount
            kind = "margin" if prefix == "m" else "padding"
            for name in _SIDES[side]:
                values[f"{kind}_{name}"] = amount
            continue
        legacy = LEGACY_SPACING_RE.match(cls)
        if legacy:
            prefix, side, pixels = legacy.groups()
            kind = "margin" if prefix == "m" else "padding"
            amount = int(pixels) * MM_PER_PX * PX_PER_INCH / px_per_inch
            for name in _LEGACY_SIDES[side]:
                values[f"{kind}_{name}"] = amount
    return BoxSpacing(**values)


def scoped_box_declarations(tag, classes, ancestor_classes):
    """Bounded structural rules whose selectors need an ancestor context.

    This is a compiled selector vocabulary, not a report-name adapter.
    Folder contributes three source rules: its adaptative row states
    ``top:-1px; height:3rem``, the angle states ``left:-1px``, and the title
    states ``margin-right:11mm``.  The last two are descendant selectors, so
    probing either element without its ancestor gives the wrong empty answer.
    recovered by asking one class at a time.
    """
    if tag == "svg" and "o_shape_bubble_1" in classes:
        top, right = BUBBLE_CIRCLE_POSITION_PX
        return {"top": f"{top:g}px", "right": f"{right:g}px"}
    if "o_report_layout_background" in classes:
        # on the article, while this class supplies the three box semantics.
        # They are one selector contract; resolving only the inline URL draws
        # the right payload with the wrong geometry.
        return {
            "background-size": "contain",
            "background-position": "center",
            "background-repeat": "no-repeat",
        }
    pdf_body = {"o_body_pdf", "o_css_margins"}
    if tag == "body" and pdf_body.issubset(classes):
        return {"padding": f"0 {REPORT_BODY_PADDING_CSS_MM:g}mm"}
    if "header" in classes and any(
        pdf_body.issubset(ancestor) for ancestor in ancestor_classes
    ):
        return {"padding-top": f"{REPORT_BODY_PADDING_CSS_MM:g}mm"}
    # The footer's counterpart, stated by the same bundle as
    # `.o_body_pdf.o_css_margins .footer > .o_footer_content
    # { padding-bottom: 11mm }`. The header half was carried and this one was
    # not, so footer content sat that much closer to the paper edge.
    if (
        "o_footer_content" in classes
        and any("footer" in ancestor for ancestor in ancestor_classes)
        and any(pdf_body.issubset(ancestor) for ancestor in ancestor_classes)
    ):
        return {"padding-bottom": f"{REPORT_BODY_PADDING_CSS_MM:g}mm"}
    if tag == "body" and "container" in classes and "o_css_margins" not in classes:
        # `.container, .o_container_small { padding-right:16px;
        # padding-left:16px }`. Badge/label report bodies omit
        # `o_css_margins`, so this is their horizontal inset; substituting
        return {"padding-left": "16px", "padding-right": "16px"}
    if tag == "div" and {"o_label_page", "o_label_dymo"}.issubset(classes):
        # This compact page family states its own four-fifths font size;
        # states a four-fifths font size; inheriting the ordinary report root made all
        # four lines 10.24pt instead of the authored 9.6pt at 96px/in.
        return {"font-size": "80%"}
    in_folder_tab = any(
        "o_folder_adaptative_shape" in ancestor
        for ancestor in ancestor_classes
    )
    if tag == "div" and "o_folder_adaptative_shape" in classes:
        return {"top": "-1px", "height": "3rem"}
    if in_folder_tab and "o_folder_angle_shape" in classes:
        return {"left": "-1px"}
    if in_folder_tab and "o_folder_title" in classes:
        return {"margin-right": "11mm"}
    # `.o_snail_mail .o_followup_address` at `padding-top: 42px`, reserving the
    # window of a physical envelope. The class sits on the article in the four
    # unshaped layouts, so the rule is descendant-scoped and invisible to a
    # probe that asks about `address` alone.
    if any("o_snail_mail" in ancestor for ancestor in ancestor_classes) and (
        "address" in classes or "o_followup_address" in classes
    ):
        return {"padding-top": f"{SNAIL_MAIL_ADDRESS_PADDING_PX:g}px"}
    return {}


def grid_span(classes) -> int:
    """Column span for a grid cell; 0 means "bare ``col``, split what is left"."""
    for cls in classes:
        match = COL_RE.match(cls)
        if match:
            return max(1, min(GRID_COLUMNS, int(match.group(1))))
    return 0 if "col" in classes else GRID_COLUMNS


def grid_offset(classes) -> int:
    """Column offset, or :data:`RIGHT_ALIGNED_OFFSET` for ``ms-auto``."""
    for cls in classes:
        match = OFFSET_RE.match(cls)
        if match:
            return max(0, min(GRID_COLUMNS - 1, int(match.group(1))))
    return RIGHT_ALIGNED_OFFSET if "ms-auto" in classes else 0


def is_grid_cell(classes) -> bool:
    return any(cls == "col" or COL_RE.match(cls) or OFFSET_RE.match(cls) for cls in classes)


def alignment(classes) -> str | None:
    if "text-end" in classes:
        return "right"
    if "text-center" in classes:
        return "center"
    if "text-start" in classes:
        return "left"
    return None


def valign(classes) -> str | None:
    if "align-bottom" in classes:
        return "bottom"
    if "align-middle" in classes:
        return "middle"
    if "align-top" in classes:
        return "top"
    return None


def is_bold(classes) -> bool:
    return bool({"fw-bold", "fw-bolder"} & set(classes))


def is_compact_table(classes) -> bool:
    """`.table-sm` (and its Bootstrap 3 spelling) halves cell padding."""
    return bool({"table-sm", "table-condensed"} & set(classes))


def logo_height_mm(classes) -> float | None:
    """Height cap for known Odoo logo classes only.

    Generic images keep their intrinsic size; do not invent millimetres. The
    width is left unset on purpose so it follows the image's aspect ratio,
    which is what the report CSS does.
    """
    for cls, height in LOGO_HEIGHTS_MM.items():
        if cls in classes:
            return height
    return None


def logo_box_mm(classes, natural_px, layout=None):
    """The box a logo is drawn in: its own size, scaled to fit the caps.

    `max-width` and `max-height` are caps, not dimensions. An engine that
    treats one of them as the height draws every logo whose shape differs
    height when the image is width-limited, as Odoo's own 450x120 logo is,
    gets both axes wrong.
    """
    caps = None
    for cls, box in LOGO_CAPS_REM_BY_LAYOUT.get(layout or "", {}).items():
        if cls in classes:
            caps = box
            break
    if caps is None:
        for cls, box in LOGO_CAPS_REM.items():
            if cls in classes:
                caps = box
                break
    if caps is None or not natural_px:
        return (None, None)
    natural_w, natural_h = (side * MM_PER_PX for side in natural_px)
    if natural_w <= 0 or natural_h <= 0:
        return (None, None)
    cap_w, cap_h = (side * MM_PER_REM for side in caps)
    scale = min(cap_w / natural_w, cap_h / natural_h, 1.0)
    return (natural_w * scale, natural_h * scale)


#: Classes the adapter reads and acts on.
SUPPORTED_CLASSES = frozenset({
    # grid
    "row", "col", "ms-auto",
    # alignment / typography
    "text-start", "text-center", "text-end", "text-nowrap", "text-truncate",
    "fw-bold", "fw-bolder", "small", "text-muted",
    "align-top", "align-middle", "align-bottom", "align-text-top",
    # line height, read through LINE_HEIGHT_CLASSES
    "lh-1", "lh-sm", "lh-base", "lh-lg",
    # display functions, recorded beside the value rather than baked into it
    "text-uppercase", "text-lowercase", "text-capitalize",
    # tables
    "table", "table-sm", "table-condensed", "table-borderless",
    "table-bordered", "table-striped",
    "o_main_table", "o_total_table", "o_has_total_table", "o_total",
    "o_price_total", "o_td_quantity", "o_ignore_layout_styling",
    # layout containers Odoo gives semantics to
    "d-flex", "flex-column", "flex-grow-1", "justify-content-between",
    "o_footer_content", "o_company_tagline",
    "o_report_layout_background",
    "o_body_pdf", "o_css_margins", "header",
    # `.o_snail_mail .address` / `.o_snail_mail .o_followup_address` reserve
    # the window of a physical envelope; read through scoped_box_declarations.
    "o_snail_mail", "address", "o_followup_address",
    # the ancestor context of `.footer > .o_footer_content`, read the same way
    "footer",
    # already acted on, and previously recorded as gaps only because nothing
    # declared them: `overflow-hidden` ends margin collapsing (it establishes
    # a block formatting context), `o_taxes` names a table row role, and the
    # company layout class is matched by `_COMPANY_LAYOUT_RE`.
    "overflow-hidden", "o_taxes", "o_company_1_layout",

    "o_company_logo", "o_company_logo_big", "o_company_logo_small", "o_logo",
    # print visibility / chrome the adapter must obey
    "d-none", "d-block", "d-inline-block", "float-end", "opacity-0",
    "position-absolute", "position-fixed", "position-relative", "top-0", "start-0",
    # bounded box utilities, read through utility_box_declarations
    "border-bottom", "border-2", "border-dark", "rounded",
    "clearfix", "page", "topage",  # wkhtml page-number spans
})

#: Classes that are pure paint or wkhtml-viewport chrome.  The adapter reads
#: them and deliberately produces no geometry, so they are covered, not
#: missing.  Anything not listed here and not supported is a real gap.
INERT_CLASSES = frozenset({
    "oe_structure",      # editable drop zone, no box of its own
    "article", "container", "container-fluid",  # report body wrappers
    "bg-light", "bg-100", "bg-white",
    "fst-italic",  # still unread: ReportLab has no italic companion mapping
    "border", "border-0", "border-1", "border-top",
    "border-end", "border-start", "border-top-0",
    "border-bottom-0", "border-info", "border-end-0", "border-start-0",
    "shadow", "fa",
    "align-items-center", "align-items-start", "align-items-end",
    "justify-content-center", "justify-content-end", "justify-content-start",
    "opacity-25", "opacity-50", "opacity-75",
    "table-light", "table-secondary", "table-active",  # row tint only
    # `text-truncate` and `text-break` used to sit here too. Both are false:
    # `text-truncate` implies `white-space: nowrap` (WHITE_SPACE_RULES
    # already derives this from the real bundle) and `text-break` implies
    # `word-break`/`overflow-wrap: break-word`, which this engine has no
    # representation for at all. `text-truncate` moved to SUPPORTED_CLASSES
    # once Paragraph.nowrap started consuming it; `text-break` is left
    # unclassified -- `classify()` reports it `unhandled`, a real gap, not a
    # covered one.
    "text-decoration-underline",
    "text-justify", "list-inline", "list-unstyled",
    "o_black_border", "oe_currency_value",
    "cp-data", "digital-stamp-content", "o_right_alignment",  # l10n paint
    "avoid-page-break-inside",
})


def classify(name: str) -> str:
    """Return ``supported``, ``inert``, ``geometry`` or ``unhandled``.

    ``geometry`` means the class is parsed by one of the grammars above
    (``col-*``, ``offset-*``, spacing utilities, width utilities) rather than
    being named literally.
    """
    if name in SUPPORTED_CLASSES:
        return "supported"
    if name in INERT_CLASSES:
        return "inert"
    prefixes = ("o_table_", "o_report_layout_", "o_folder_", "o_shape")
    if name == "o_table" or name.startswith(prefixes):
        return "supported"
    if (
        COL_RE.match(name)
        or OFFSET_RE.match(name)
        or SPACING_RE.match(name)
        or LEGACY_SPACING_RE.match(name)
        or WIDTH_RE.match(name)
        or DISPLAY_RE.match(name)
        or FONT_SIZE_RE.match(name)
    ):
        return "geometry"
    return "unhandled"



# --- where these numbers came from -------------------------------------
#: Every constant above answers for itself. `tests/test_measurement_
#: the review ledger rejects any that does not, and
#: `tools/measure_report_geometry.py` re-derives the wkhtmltopdf ones from a
#: real PDF so drift shows up as a number rather than as a surprise.
