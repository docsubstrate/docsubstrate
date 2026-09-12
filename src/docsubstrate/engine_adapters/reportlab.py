"""ReportLab engine adapter for the universal DocumentContext contract."""

from __future__ import annotations

from dataclasses import dataclass

from docsubstrate.commerce import CommercialDocumentData, commercial_document_semantic_graph
from docsubstrate.context import DocumentContext, PresentationProfile
from docsubstrate.engines import EngineArtifact, EngineCapabilities, EngineSupport
from docsubstrate.ir import Container
from docsubstrate.odoo_report_profile import (
    CSS_PX_PER_INCH,
    PAPER_MARGIN_EPSILON_MM,
    REPORT_BODY_PADDING_CSS_MM,
)
from docsubstrate.odoo_report_theme import ReportTheme
from docsubstrate.page_planner import PagePlanner, PagePolicy
from docsubstrate.renderers.reportlab_canvas import ReportLabCanvasRenderer, registered_text_font
from docsubstrate.structure_policies import CommercialDocumentStructurePolicy
from docsubstrate.text_provenance import sidecar


def sourced_page_inset_mm(css_px_per_inch: float) -> float:
    """Odoo's own horizontal page padding, in this bridge's millimetres.

    The source value is 11 CSS mm. CSS absolute units first become 96
    reference pixels; the paperformat then decides whether wkhtml puts them
    down at 112.5px/in (smart shrinking, possibly shrunk further to fit) or
    at 96 (shrinking disabled).
    """
    return REPORT_BODY_PADDING_CSS_MM * CSS_PX_PER_INCH / css_px_per_inch


@dataclass(frozen=True, slots=True)
class PageInsets:
    """The page box's horizontal insets, and where each one came from.

    The distinction is not cosmetic. A paperformat margin is *physical*:
    wkhtml receives it as ``--margin-left`` and the web viewport is the
    printable width, so it is outside the layout entirely. The sourced
    11mm is CSS padding *inside* that viewport, so it is part of what the
    document demands. Shrink-to-fit divides one by the other, and treating
    both alike would compute the scale against a page that is not the one
    being drawn.
    """

    left_mm: float
    right_mm: float
    #: True when the value came from the report stylesheet, not the paper.
    sourced_left: bool
    sourced_right: bool

    @property
    def paper_mm(self) -> float:
        """The part that reduces the printable width."""
        return (
            (0.0 if self.sourced_left else self.left_mm)
            + (0.0 if self.sourced_right else self.right_mm)
        )

    @property
    def css_mm(self) -> float:
        """The part that lives inside the viewport, as document demand."""
        return (
            (self.left_mm if self.sourced_left else 0.0)
            + (self.right_mm if self.sourced_right else 0.0)
        )


def horizontal_insets_mm(
    structure, *, margin_left_mm: float, margin_right_mm: float,
    css_px_per_inch: float,
) -> PageInsets:
    """The page box's left and right inset.

    Odoo's A4 paperformat carries no horizontal margin -- the inset comes
    from the report CSS -- so a literal 0 means "use the sourced one" rather
    than "print against the page edge". A fragment root that states its own
    horizontal padding has already put that box in the IR, so adding the
    sourced inset there would apply it twice.

    Shared with the shrink-to-fit walk rather than kept private to the
    planner, so that the scale and the drawing cannot disagree about how
    wide the page's content is.
    """
    source_inset = sourced_page_inset_mm(css_px_per_inch)

    def fragment_boxes(blocks):
        for block in blocks:
            if not isinstance(block, Container):
                continue
            if block.fragment_root:
                yield block
            # Evaluated QWeb is `html > body > article`; the body box is
            # therefore inside the transparent html fragment root, not a
            # top-level sibling in Document.body.
            yield from fragment_boxes(block.children)

    root_boxes = tuple(fragment_boxes(structure.body))
    owns_left = any(box.padding_mm[3] > 0.0 for box in root_boxes)
    owns_right = any(box.padding_mm[1] > 0.0 for box in root_boxes)
    left, right = margin_left_mm, margin_right_mm
    sourced_left = left < PAPER_MARGIN_EPSILON_MM and not owns_left
    sourced_right = right < PAPER_MARGIN_EPSILON_MM and not owns_right
    return PageInsets(
        left_mm=source_inset if sourced_left else left,
        right_mm=source_inset if sourced_right else right,
        sourced_left=sourced_left,
        sourced_right=sourced_right,
    )


class ReportLabEngine:
    """Materialize structural document contexts through resolved page execution.

    Native transactional structures use the multipage PagePlanner.  Evaluated
    QWeb remains on the deliberately narrow single-page compatibility planner.
    Both paths converge only after pagination, at immutable PagePlan execution.
    """

    name = "reportlab"
    capabilities = EngineCapabilities(
        structure=True,
        presentation=True,
        page_execution=True,
        paginated_output=True,
        output_media_types=("application/pdf",),
    )

    def __init__(self, planner=None, *, encoded_image_store=None):
        self.planner = planner
        self.renderer = ReportLabCanvasRenderer(
            encoded_image_store=encoded_image_store
        )

    def supports(self, context: DocumentContext) -> EngineSupport:
        if context.structure is None:
            return EngineSupport(False, "ReportLab currently requires a structural representation")
        return EngineSupport(True)

    def _planner_for(self, context: DocumentContext) -> PagePlanner:
        """One planner for both sources.

        Native structures and evaluated QWeb used to take different planners,
        which meant a quotation printed from Odoo could not paginate while the
        same document built natively could. They plan the same way now; what
        differs is only where the structure came from.
        """
        if self.planner is not None:
            return self.planner

        values = context.presentation.values
        required = tuple(context.metadata.get("required_presentation_keys", ()))
        missing = [
            key for key in required
            if key not in values or values[key] is None or values[key] == ""
        ]
        if missing:
            raise ValueError(
                "required presentation contract keys are absent: "
                + ", ".join(missing)
            )
        defaults = PagePolicy()
        css_px_per_inch = float(
            values.get("css_px_per_inch", defaults.css_px_per_inch)
        )
        source_inset = sourced_page_inset_mm(css_px_per_inch)
        insets = horizontal_insets_mm(
            context.structure,
            margin_left_mm=float(values.get("margin_left_mm", defaults.margin_left_mm)),
            margin_right_mm=float(values.get("margin_right_mm", defaults.margin_right_mm)),
            css_px_per_inch=css_px_per_inch,
        )
        # A page shrunk to fit is a page whose every CSS length is smaller,
        # including the ones this engine holds as physical millimetres
        # measured at the unshrunk bridge. The shrink scale is 1.0 for every
        # document that fits, which makes all four of these exact no-ops
        # there; see `table_layout.shrink_to_fit_scale`.
        shrink = float(values.get("shrink_to_fit_scale", 1.0))

        def containers(blocks):
            for block in blocks:
                if isinstance(block, Container):
                    yield block
                    yield from containers(block.children)

        header_owns_top_inset = any(
            box.padding_mm[0] > 0.0 for box in containers(context.structure.header)
        )
        policy = PagePolicy(
            width_mm=float(values.get("width_mm", defaults.width_mm)),
            height_mm=float(values.get("height_mm", defaults.height_mm)),
            margin_left_mm=insets.left_mm,
            margin_right_mm=insets.right_mm,
            # A sourced `.header` padding starts from the top of wkhtml's
            # header viewport.  The fallback preserves the same source value
            # for fragments that omit the wrapper; it is no longer a measured
            # physical constant masquerading as CSS.
            band_inset_mm=0.0 if header_owns_top_inset else source_inset,
            margin_top_mm=float(values.get("margin_top_mm", defaults.margin_top_mm)),
            margin_bottom_mm=float(values.get("margin_bottom_mm", defaults.margin_bottom_mm)),
            font_name=str(values.get("font_name") or registered_text_font()),
            font_size_pt=float(
                values.get("font_size_pt", defaults.font_size_pt * shrink)
            ),
            line_height_mm=float(
                values.get("line_height_mm", defaults.line_height_mm * shrink)
            ),
            block_gap_mm=float(
                values.get("block_gap_mm", defaults.block_gap_mm * shrink)
            ),
            table_cell_pad_mm=float(
                values.get("table_cell_pad_mm", defaults.table_cell_pad_mm * shrink)
            ),
            css_px_per_inch=css_px_per_inch,
            image_base_url=values.get("image_base_url") or None,
            latin_font_path=values.get("latin_font_path") or None,
            font_assets=values.get("font_assets") or None,
            paper_format=str(values.get("paper_format", defaults.paper_format)),
            dpi=int(values.get("dpi", defaults.dpi)),
        )
        # The company's layout choice travels with the presentation profile;
        # the `o_report_layout_*` class on the evaluated HTML is the fallback.
        # Table chrome is supplied as a fixed profile.  Runtime materialization
        # therefore does not need a stylesheet parser.
        theme = ReportTheme.from_values(values, context.structure)
        return PagePlanner(policy, theme=theme)

    def materialize(self, context: DocumentContext) -> EngineArtifact:
        support = self.supports(context)
        if not support.supported:
            raise ValueError(support.reason)
        planner = self._planner_for(context)
        resolved = planner.plan(context.structure)
        content = self.renderer.render_bytes(resolved)
        return EngineArtifact(
            content=content,
            media_type="application/pdf",
            engine=self.name,
            metadata={
                "pages": len(resolved.pages),
                "execution_ir": "PagePlan",
                "warnings": tuple(planner.warnings),
                # Out of band on purpose: provenance that changed the bytes
                # under comparison would be measuring itself.
                "text_provenance": sidecar(resolved),
            },
        )


def render_sale_order_pdf(
    document: CommercialDocumentData,
    *,
    layout: str | None = None,
    primary_color: str = "#714B67",
    secondary_color: str = "#D8DADD",
) -> bytes:
    """Render the bounded public-alpha sale-order projection to PDF bytes.

    This convenience API owns a portable A4 presentation.  Odoo integrations
    use the same structure policy with the company's actual paper and colours.
    """
    if document.semantic_kind != "commerce.quotation":
        raise ValueError("the public-alpha PDF helper accepts a quotation-shaped sale order")
    chosen_layout = layout or document.layout
    structure, relations = CommercialDocumentStructurePolicy().project(document)
    context = DocumentContext(
        kind="commerce.quotation",
        semantic=commercial_document_semantic_graph(document),
        structure=structure,
        relations=relations,
        presentation=PresentationProfile(
            id="public-alpha.sale-order",
            values={
                "width_mm": 210.0,
                "height_mm": 297.0,
                "margin_top_mm": 10.0,
                "margin_right_mm": 0.0,
                "margin_bottom_mm": 10.0,
                "margin_left_mm": 0.0,
                "paper_format": "A4",
                "dpi": 90,
                "css_px_per_inch": 112.5,
                "font_name": "Helvetica",
                "layout": chosen_layout,
                "primary_color": primary_color,
                "secondary_color": secondary_color,
            },
        ),
        metadata={
            "source": "public-api",
            "report_action": "sale.report_saleorder",
            "render_host": "record-native",
            "qweb_evaluated": False,
        },
    )
    artifact = ReportLabEngine().materialize(context)
    warnings = tuple(artifact.metadata.get("warnings", ()))
    if warnings:
        raise RuntimeError(f"sale-order PDF produced warnings: {warnings!r}")
    return artifact.content
