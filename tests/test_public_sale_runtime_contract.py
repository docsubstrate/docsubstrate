"""Source-free executable contracts for the bounded public sale renderer."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from docsubstrate import CommercialDocumentData, CommercialLineData, render_sale_order_pdf
from docsubstrate.image_assets import image_natural_size_px, vectorize_svg
from docsubstrate.ir import Container, Document, Grid, GridCell, LineBreak, Paragraph, Text
from docsubstrate.odoo_report_profile import (
    GRID_COLUMNS,
    MM_PER_PX,
    PX_PER_INCH,
    TABLE_CELL_PAD_MM,
    TABLE_CELL_PAD_REM,
)
from docsubstrate.page_planner import PagePlanner, PagePolicy
from docsubstrate.pageplan import PagePlan, Rect, ResolvedDocument
from docsubstrate.renderers.reportlab_canvas import ReportLabCanvasRenderer

POLICY = PagePolicy(
    width_mm=100,
    height_mm=100,
    margin_left_mm=10,
    margin_right_mm=10,
    margin_top_mm=10,
    margin_bottom_mm=10,
    font_name="Helvetica",
)


def test_contract_01_embedded_svg_has_a_deterministic_natural_size():
    source = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0nMTInIGhlaWdodD0nOCcvPg=="
    assert image_natural_size_px(source) == (12, 8)


def test_contract_02_visible_svg_rectangles_remain_vector_shapes():
    size, shapes = vectorize_svg(
        b'<svg width="12" height="8"><rect x="1" y="2" width="3" height="4" fill="#123456"/></svg>'
    )
    assert size == (12.0, 8.0)
    assert [(shape.x, shape.y, shape.width, shape.height) for shape in shapes] == [
        (1.0, 2.0, 3.0, 4.0)
    ]


def test_contract_03_text_transform_is_presentation_not_source_mutation():
    item = Text("Quotation Ab-1", transform="upper")
    assert item.value == "Quotation Ab-1"
    assert item.displayed == "QUOTATION AB-1"


def test_contract_04_document_structure_is_backend_neutral_and_immutable():
    paragraph = Paragraph((Text("alpha"),))
    document = Document(body=(Container(children=(paragraph,)),))
    assert document.body[0].children == (paragraph,)
    with pytest.raises(AttributeError):
        paragraph.align = "right"


def test_contract_05_fixed_profile_values_are_explicit_and_self_consistent():
    assert GRID_COLUMNS == 12
    assert PX_PER_INCH > 0
    assert MM_PER_PX == pytest.approx(25.4 / PX_PER_INCH)
    assert TABLE_CELL_PAD_MM == pytest.approx(TABLE_CELL_PAD_REM * 16 * MM_PER_PX)
    review_map = json.loads(
        (Path(__file__).resolve().parents[1] / "public-alpha/profile-review-map.json")
        .read_text(encoding="utf-8")
    )
    names = {row["name"] for row in review_map["profile_constants"]}
    assert {"GRID_COLUMNS", "PX_PER_INCH", "MM_PER_PX", "TABLE_CELL_PAD_MM"} <= names


def test_contract_06_public_profile_contains_no_product_label_selectors():
    from docsubstrate import odoo_report_profile as profile

    source = profile.__loader__.get_source(profile.__name__)
    assert source is not None
    assert "label_sheet" not in source


def test_contract_07_normal_prose_wraps_inside_a_narrow_box():
    paragraph = Paragraph((Text("alpha beta gamma delta epsilon " * 8),))
    plan = PagePlanner(POLICY).plan(Document(body=(paragraph,)))
    runs = [command for page in plan.pages for command in page.commands if hasattr(command, "text")]
    assert len({run.y_mm for run in runs}) > 1


def test_contract_08_nowrap_content_stays_on_one_line():
    paragraph = Paragraph((Text("alpha beta gamma delta epsilon"),), nowrap=True)
    plan = PagePlanner(POLICY).plan(Document(body=(paragraph,)))
    runs = [command for page in plan.pages for command in page.commands if hasattr(command, "text")]
    assert len({run.y_mm for run in runs}) == 1


def test_contract_09_grid_padding_changes_outer_advance_not_content_width_twice():
    marker = Container(children=(), height_mm=10, fill_rgb=(0.5, 0.5, 0.5))
    grid = Grid(cells=(GridCell(blocks=(marker,), span=12),), padding_mm=(2, 3, 4, 3))
    plan = PagePlanner(POLICY).plan(Document(body=(grid,)))
    rect = next(command for command in plan.pages[0].commands if isinstance(command, Rect))
    assert rect.width_mm == pytest.approx(74.0)
    assert rect.height_mm == pytest.approx(10.0)


def test_contract_10_float_and_clear_are_scoped_to_one_formatting_context():
    floated = Container(
        children=(), height_mm=10, width_mm=20, float_side="left", fill_rgb=(0.2, 0.2, 0.2)
    )
    clearing = Container(children=(), clear="both")
    probe = Container(children=(), height_mm=1, fill_rgb=(0.6, 0.6, 0.6))
    plan = PagePlanner(POLICY).plan(Document(body=(floated, clearing, probe)))
    rects = [command for command in plan.pages[0].commands if isinstance(command, Rect)]
    assert rects[-1].y_mm + rects[-1].height_mm <= rects[0].y_mm


def test_contract_11_canvas_emits_pdf_14_and_transparency_state():
    document = ResolvedDocument(
        pages=(
            PagePlan(
                width_mm=20,
                height_mm=20,
                commands=(Rect(0, 0, 10, 10, fill=True, stroke=False, fill_alpha=0.5),),
            ),
        )
    )
    payload = ReportLabCanvasRenderer().render_bytes(document)
    assert payload.startswith(b"%PDF-1.4\n")
    assert b"/ExtGState" in payload


def test_contract_12_sale_api_is_byte_deterministic():
    record = CommercialDocumentData(
        id="sale-order.synthetic.contract",
        number="SO-CONTRACT-001",
        display_title="Quotation # SO-CONTRACT-001",
        customer_name="Example Buyer",
        seller_name="Example Seller",
        currency="USD",
        lines=(
            CommercialLineData(
                id="line.synthetic.1",
                description="Calibration service",
                quantity=Decimal(2),
                unit_price=Decimal("125.00"),
                subtotal=Decimal("250.00"),
            ),
        ),
        untaxed_amount=Decimal("250.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("250.00"),
    )
    first = render_sale_order_pdf(record)
    second = render_sale_order_pdf(record)
    assert first == second
    assert first.startswith(b"%PDF-1.4\n")


def test_contract_13_nowrap_preserves_an_authored_hard_break():
    paragraph = Paragraph(
        (Text("First field"), LineBreak(), Text("Second field")),
        nowrap=True,
    )
    plan = PagePlanner(POLICY).plan(Document(body=(paragraph,)))
    runs = [
        command
        for page in plan.pages
        for command in page.commands
        if hasattr(command, "text")
    ]
    assert [run.text for run in runs] == ["First field", "Second field"]
    assert len({run.y_mm for run in runs}) == 2
