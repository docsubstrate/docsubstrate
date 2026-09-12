"""Native structural policies independent of source templates and renderers."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from docsubstrate.commerce import (
    AddressData,
    CommercialDocumentData,
    CommercialLineData,
    InformationFieldData,
)
from docsubstrate.ir import (
    Border,
    Container,
    Document,
    Grid,
    GridCell,
    LineBreak,
    PageBreak,
    Paragraph,
    Table,
    TableCell,
    TableRow,
    Text,
)
from docsubstrate.relations import RepresentationGraph, RepresentationRef, RepresentationRelation


def _p(value: object, *, bold: bool = False, role: str | None = None, align: str | None = None):
    return Paragraph((Text(str(value), bold=bold),), role=role, align=align)


def _lines(*values: str, role: str | None = None, bold_first: bool = False):
    children: list[Text | LineBreak] = []
    for index, value in enumerate(values):
        if not value:
            continue
        if children:
            children.append(LineBreak())
        children.append(Text(value, bold=bold_first and index == 0))
    return Paragraph(tuple(children), role=role)


def _qty(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _money(value: Decimal) -> str:
    return f"{value:.2f}"


class CommercialDocumentStructurePolicy:
    """Project commercial facts into the shared Odoo business-document shape.

    The policy owns address, title, information, line, totals, and trailing
    prose placement.  It deliberately knows neither ``sale.order`` nor
    ``account.move``: model adapters resolve ORM methods and authored labels
    before calling it.  This keeps one structural IR rather than one renderer
    branch per model.
    """

    name = "commerce.document.standard"

    def project(self, data: CommercialDocumentData) -> tuple[Document, RepresentationGraph]:
        relations = [
            RepresentationRelation(
                RepresentationRef("semantic", "customer"),
                "represented_by",
                RepresentationRef("structure", "customer-block"),
            ),
            RepresentationRelation(
                RepresentationRef("semantic", "amount.total"),
                "represented_by",
                RepresentationRef("structure", "totals-block"),
            ),
        ]
        show_taxes = any(line.taxes_label for line in data.lines if not line.display_type)
        show_discount = any(line.discount for line in data.lines if not line.display_type)
        columns = 4 + int(show_taxes) + int(show_discount)
        header_cells = [
            TableCell(
                (_p(data.description_label, bold=True),),
                header=True,
                role="line.description.header",
            ),
            TableCell(
                (_p(data.quantity_label, bold=True),),
                header=True,
                align="right",
                role="line.quantity.header",
            ),
            TableCell(
                (_p(data.unit_price_label, bold=True),),
                header=True,
                align="right",
                role="line.unit_price.header",
            ),
        ]
        if show_discount:
            header_cells.append(
                TableCell(
                    (_p(data.discount_label, bold=True),),
                    header=True,
                    align="right",
                    role="line.discount.header",
                ),
            )
        if show_taxes:
            header_cells.append(
                TableCell(
                    (_p(data.taxes_label, bold=True),), header=True, role="line.taxes.header"
                ),
            )
        header_cells.append(
            TableCell(
                (_p(data.amount_label, bold=True),),
                header=True,
                align="right",
                role="line.amount.header",
            ),
        )
        rows = [TableRow(tuple(header_cells))]
        for line in data.lines:
            rows.append(self._line_row(line, columns, show_taxes, show_discount))
            relations.append(
                RepresentationRelation(
                    RepresentationRef("semantic", line.id),
                    "represented_by",
                    RepresentationRef("structure", f"{line.id}.row"),
                )
            )

        body: list = [
            self._address_table(data),
            _p(
                data.display_title or data.document_label,
                bold=True,
                role="document-title",
            ),
            *(() if data.display_title else (_p(data.number, bold=True, role="document-number"),)),
            self._information_table(data),
            Table(
                tuple(rows),
                repeat_header_rows=1,
                kind="commerce-lines",
            ),
            self._totals_table(data),
        ]
        if data.payment_terms:
            body.append(_p(data.payment_terms, role="payment-terms"))
        if data.note:
            body.append(_p(data.note, role="notes"))

        header = (_p(data.seller_name, role="seller-block"),) if data.seller_name else ()
        return Document(
            header=header,
            body=tuple(block for block in body if block is not None),
            # Compatibility identifier. It predates the generic policy but is
            # not a sale-only rendering branch; changing it would churn stored
            # native snapshots without changing one structural fact.
            layout="commerce.quotation",
        ), RepresentationGraph(tuple(relations))

    def _line_row(
        self, line: CommercialLineData, columns: int, show_taxes: bool, show_discount: bool
    ) -> TableRow:
        if line.display_type in {"line_section", "line_subsection", "line_note"}:
            if line.display_type in {"line_section", "line_subsection"} and line.subtotal_text:
                return TableRow(
                    (
                        TableCell(
                            (_p(line.description, bold=True),),
                            colspan=columns - 1,
                            role=f"{line.id}.{line.display_type}",
                        ),
                        TableCell(
                            (_p(line.subtotal_text),),
                            align="right",
                            role=f"{line.id}.amount",
                        ),
                    )
                )
            return TableRow(
                (
                    TableCell(
                        (
                            _p(
                                line.description,
                                bold=line.display_type in {"line_section", "line_subsection"},
                            ),
                        ),
                        colspan=columns,
                        role=f"{line.id}.{line.display_type}",
                    ),
                )
            )
        quantity = line.quantity_text or _qty(line.quantity)
        if line.uom:
            quantity = f"{quantity} {line.uom}"
        cells = [
            TableCell((_p(line.description),), role=f"{line.id}.description"),
            TableCell((_p(quantity),), align="right", role=f"{line.id}.quantity"),
            TableCell(
                (_p(line.unit_price_text or _money(line.unit_price)),),
                align="right",
                role=f"{line.id}.unit_price",
            ),
        ]
        if show_discount:
            discount = line.discount_text or (_qty(line.discount) if line.discount else "")
            cells.append(TableCell((_p(discount),), align="right", role=f"{line.id}.discount"))
        if show_taxes:
            cells.append(TableCell((_p(line.taxes_label or ""),), role=f"{line.id}.taxes"))
        cells.append(
            TableCell(
                (_p(line.subtotal_text or _money(line.subtotal)),),
                align="right",
                role=f"{line.id}.amount",
            )
        )
        return TableRow(tuple(cells))

    def _address_table(self, data: CommercialDocumentData) -> Table | Paragraph:
        customer = data.customer_address or AddressData(data.customer_name)
        customer_lines = (customer.name, *customer.lines)
        shipping = data.shipping_address
        if shipping and tuple(shipping.lines) != tuple(customer.lines):
            customer_values = (
                *((data.customer_address_label,) if data.customer_address_label else ()),
                *customer_lines,
            )
            return Table(
                (
                    TableRow(
                        (
                            TableCell(
                                (_lines(*customer_values, bold_first=True, role="customer-block"),)
                            ),
                            TableCell(
                                (
                                    _lines(
                                        data.shipping_address_label,
                                        shipping.name,
                                        *shipping.lines,
                                        bold_first=True,
                                    ),
                                )
                            ),
                        )
                    ),
                ),
                borderless=True,
                column_weights=(1.0, 1.0),
                kind="addresses",
            )
        customer_values = (
            *((data.customer_address_label,) if data.customer_address_label else ()),
            *customer_lines,
        )
        return _lines(*customer_values, bold_first=True, role="customer-block")

    def _information_table(self, data: CommercialDocumentData) -> Grid | None:
        fields: list[InformationFieldData] = []
        if data.date:
            fields.append(InformationFieldData("date", data.date_label, data.date))
        if data.validity_date:
            fields.append(
                InformationFieldData("expiration", data.validity_label, data.validity_date)
            )
        if data.salesperson:
            fields.append(
                InformationFieldData("salesperson", data.salesperson_label, data.salesperson)
            )
        fields.extend(data.information_fields)
        if not fields:
            return None
        auto_span = max(1, 12 // len(fields))
        cells = []
        for field in fields:
            cells.append(
                GridCell(
                    (
                        _p(field.label, bold=True, role=f"info.{field.id}.label"),
                        _p(field.value, role=f"info.{field.id}"),
                    ),
                    span=field.span or auto_span,
                )
            )
        return Grid(
            tuple(cells),
            gutter_mm=0.0,
            kind="info",
            space_before_mm=0.0,
            space_after_mm=data.information_space_after_mm,
        )

    def _totals_table(self, data: CommercialDocumentData) -> Table:
        rows = [
            TableRow(
                (
                    TableCell((_p(data.untaxed_label),)),
                    TableCell(
                        (_p(data.untaxed_amount_text or _money(data.untaxed_amount)),),
                        align="right",
                        role="totals.untaxed",
                    ),
                )
            ),
        ]
        groups = data.tax_groups or ()
        if groups:
            for group in groups:
                rows.append(
                    TableRow(
                        (
                            TableCell((_p(group.name),)),
                            TableCell(
                                (_p(group.amount_text or _money(group.amount)),),
                                align="right",
                                role=f"totals.tax.{group.name}",
                            ),
                        )
                    )
                )
        elif data.tax_amount:
            rows.append(
                TableRow(
                    (
                        TableCell((_p(data.taxes_label),)),
                        TableCell(
                            (_p(data.tax_amount_text or _money(data.tax_amount)),),
                            align="right",
                            role="totals.tax",
                        ),
                    )
                )
            )
        rows.append(
            TableRow(
                (
                    TableCell((_p(data.total_label, bold=True),)),
                    TableCell(
                        (
                            _p(
                                data.total_amount_text
                                or f"{_money(data.total_amount)} {data.currency}",
                                bold=True,
                            ),
                        ),
                        align="right",
                        role="totals.total",
                    ),
                )
            )
        )
        return Table(
            tuple(rows),
            column_weights=(2.0, 1.0),
            align="right",
            width_fraction=0.45,
            kind="totals",
        )


# Public compatibility alias; there is only one implementation.
QuotationStructurePolicy = CommercialDocumentStructurePolicy


class LabelSheetStructurePolicy:
    """Place authored panels without inventing external-layout chrome.

    The policy knows no Odoo model and calls no model method.  A binding has
    already resolved the facts and ordinary IR blocks inside every panel.
    Here we preserve only the bounded sheet geometry shared by the adapter.
    """

    name = "label.sheet"

    @staticmethod
    def _panel(panel: Any) -> Container:
        edge = Border(
            width_pt=panel.border_width_pt,
            colour=panel.border_rgb,
            style=panel.border_style if panel.border_width_pt else "none",
        )
        return Container(
            tuple(panel.blocks),
            preserve_fragment_leading_margin=True,
            width_mm=panel.width_mm,
            height_mm=panel.height_mm,
            padding_mm=panel.padding_mm,
            border=(edge, edge, edge, edge),
            fill_rgb=panel.fill_rgb,
            radius_mm=panel.radius_mm,
            space_before_mm=0.0,
            space_after_mm=0.0,
        )

    def project(self, data: Any) -> Document:
        capacity = data.rows * data.columns
        pages: list = []
        panels = list(data.panels)
        for page_index in range(0, max(1, len(panels)), capacity):
            page_panels = panels[page_index : page_index + capacity]
            # A one-panel document is normal block flow, not a one-cell
            # table.  This distinction is observable on thermal invoices:
            # their authored body may continue onto a second page, whereas a
            # table row is deliberately atomic and cannot split.
            if data.columns == data.rows == 1 and len(page_panels) == 1:
                pages.append(self._panel(page_panels[0]))
                if page_index + capacity < len(panels):
                    pages.append(PageBreak())
                continue
            # Odoo authors a complete sheet on every page.  Slots beyond the
            # requested quantity reuse the first label's geometry under
            # ``visibility:hidden``: they still size every row and column but
            # paint nothing.  Carry that same structure instead of emitting
            # empty cells, whose rows collapse in an ordinary table layout.
            slot_template = page_panels[0] if page_panels else panels[0]
            table_rows = []
            for row_index in range(data.rows):
                cells = []
                for column_index in range(data.columns):
                    index = row_index * data.columns + column_index
                    occupied = index < len(page_panels)
                    panel = page_panels[index] if occupied else slot_template
                    cells.append(
                        TableCell(
                            (self._panel(panel),),
                            width_fraction=1.0 / data.columns,
                            padding_mm=(0.0, 0.0, 0.0, 0.0),
                            visible=occupied,
                        )
                    )
                table_rows.append(TableRow(tuple(cells)))
            sheet = Table(
                tuple(table_rows),
                borderless=True,
                width_fraction=1.0,
                layout_mode="fixed",
                border_collapse="separate" if any(data.gap_mm) else "collapse",
                border_spacing_mm=data.gap_mm,
                kind="label-sheet",
                space_before_mm=0.0,
                space_after_mm=0.0,
            )
            pages.append(
                Container(
                    (sheet,),
                    fragment_root=True,
                    padding_mm=data.page_padding_mm,
                    space_before_mm=0.0,
                    space_after_mm=0.0,
                )
            )
            if page_index + capacity < len(panels):
                pages.append(PageBreak())
        return Document(body=tuple(pages), layout=self.name)


class OperationalListStructurePolicy:
    """Project line-oriented operational facts without calling an ORM API.

    A section decides *what* rows exist in a binding; this policy decides that
    its column labels are a repeating table header and that a requested page
    break is structural.  It deliberately has no party or monetary-total
    vocabulary: those belong to the commercial prototype.
    """

    name = "operational.list"

    @staticmethod
    def _table(data: Any) -> Table:
        rows = []
        if data.columns:
            rows.append(
                TableRow(
                    tuple(
                        TableCell(
                            (_p(column.label, bold=True),),
                            colspan=column.colspan,
                            header=True,
                            align=column.align,
                            width_fraction=column.width_fraction,
                            nowrap=column.nowrap,
                            role=f"{data.id}.{column.id}.header",
                        )
                        for column in data.columns
                    ),
                    group="thead",
                    group_index=1,
                )
            )
        for index, row in enumerate(data.rows, start=1):
            rows.append(
                TableRow(
                    tuple(
                        TableCell(
                            tuple(cell.blocks),
                            colspan=cell.colspan,
                            align=cell.align,
                            width_fraction=cell.width_fraction,
                            nowrap=cell.nowrap,
                            role=cell.role or f"{data.id}.{row.id}.{cell_index}",
                        )
                        for cell_index, cell in enumerate(row.cells)
                    ),
                    group="tbody",
                    group_index=index,
                    role=row.role,
                )
            )
        return Table(
            tuple(rows),
            repeat_header_rows=1 if data.columns else 0,
            borderless=data.borderless,
            compact=data.compact,
            column_weights=tuple(data.column_weights),
            width_fraction=data.width_fraction,
            layout_mode=data.layout_mode,
            kind="lines",
            theme=data.theme,
        )

    def project(self, data: Any) -> Document:
        body: list = []
        if data.title:
            body.append(_p(data.title, bold=True, role=data.title_role))
        body.extend(data.leading_blocks)
        for section in data.sections:
            if section.page_break_before:
                body.append(PageBreak())
            if section.title:
                body.append(_p(section.title, bold=True, role=section.title_role))
            body.extend(section.blocks)
            body.extend(self._table(table) for table in section.tables)
        body.extend(data.trailing_blocks)
        return Document(body=tuple(body), layout=self.name)
