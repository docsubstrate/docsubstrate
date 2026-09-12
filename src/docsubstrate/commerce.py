"""Commerce semantic vocabulary and renderer-neutral document projection.

The structures in this module describe the recurring *business document*
shape shared by quotations, orders, invoices, and credit notes.  Odoo model
adapters own field selection and model methods; this vocabulary owns only the
facts those adapters have already resolved.  The historical ``Quotation*``
names remain aliases so stored callers do not acquire a migration merely
because a second model now uses the same honest prototype.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from docsubstrate.semantics import SemanticEntity, SemanticGraph, SemanticRelation


@dataclass(frozen=True, slots=True)
class AddressData:
    name: str
    lines: Sequence[str] = ()


@dataclass(frozen=True, slots=True)
class TaxGroupData:
    name: str
    amount: Decimal
    amount_text: str | None = None


@dataclass(frozen=True, slots=True)
class CommercialLineData:
    id: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal
    product_name: str | None = None
    display_type: str | None = None
    uom: str | None = None
    discount: Decimal | None = None
    taxes_label: str | None = None
    quantity_text: str | None = None
    unit_price_text: str | None = None
    discount_text: str | None = None
    subtotal_text: str | None = None


@dataclass(frozen=True, slots=True)
class InformationFieldData:
    """One authored label/value pair in the document information band."""

    id: str
    label: str
    value: str
    # Zero means CSS ``.col`` semantics: share the row equally with the other
    # active fields. A positive span is an authored 12-column constraint.
    span: int = 0


@dataclass(frozen=True, slots=True)
class CommercialDocumentData:
    id: str
    number: str
    customer_name: str
    seller_name: str
    currency: str
    lines: Sequence[CommercialLineData]
    untaxed_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    semantic_kind: str = "commerce.quotation"
    payment_terms: str | None = None
    validity_date: str | None = None
    salesperson: str | None = None
    document_label: str = "Quotation"
    date: str | None = None
    customer_address: AddressData | None = None
    shipping_address: AddressData | None = None
    note: str | None = None
    tax_groups: Sequence[TaxGroupData] = ()
    layout: str = "standard"
    display_title: str | None = None
    date_label: str = "Date:"
    validity_label: str = "Expiration:"
    salesperson_label: str = "Salesperson:"
    information_space_after_mm: float | None = None
    description_label: str = "Description"
    quantity_label: str = "Quantity"
    unit_price_label: str = "Unit Price"
    discount_label: str = "Disc.%"
    taxes_label: str = "Taxes"
    amount_label: str = "Amount"
    customer_address_label: str | None = "Invoice Address"
    shipping_address_label: str = "Delivery Address"
    untaxed_label: str = "Untaxed Amount"
    total_label: str = "Total"
    untaxed_amount_text: str | None = None
    tax_amount_text: str | None = None
    total_amount_text: str | None = None
    information_fields: Sequence[InformationFieldData] = ()


def commercial_document_semantic_graph(data: CommercialDocumentData) -> SemanticGraph:
    """Build commercial-document truth without prescribing a page or template."""
    entities = [
        SemanticEntity(data.id, data.semantic_kind, value=data.number),
        SemanticEntity("customer", "party.customer", value=data.customer_name),
        SemanticEntity("seller", "party.seller", value=data.seller_name),
        SemanticEntity("currency", "finance.currency", value=data.currency),
        SemanticEntity("amount.untaxed", "finance.amount.untaxed", value=data.untaxed_amount),
        SemanticEntity("amount.tax", "finance.amount.tax", value=data.tax_amount),
        SemanticEntity("amount.total", "finance.amount.total", value=data.total_amount),
    ]
    relations = [
        SemanticRelation(data.id, "customer", "customer"),
        SemanticRelation(data.id, "seller", "seller"),
        SemanticRelation(data.id, "currency", "currency"),
        SemanticRelation(data.id, "has_total", "amount.total"),
    ]
    if data.payment_terms:
        entities.append(SemanticEntity("payment_terms", "commerce.payment_terms", value=data.payment_terms))
        relations.append(SemanticRelation(data.id, "has_terms", "payment_terms"))
    if data.validity_date:
        entities.append(SemanticEntity("validity", "commerce.validity_date", value=data.validity_date))
        relations.append(SemanticRelation(data.id, "valid_until", "validity"))
    if data.salesperson:
        entities.append(SemanticEntity("salesperson", "party.salesperson", value=data.salesperson))
        relations.append(SemanticRelation(data.id, "handled_by", "salesperson"))
    if data.date:
        entities.append(SemanticEntity("order_date", "commerce.order_date", value=data.date))
        relations.append(SemanticRelation(data.id, "dated", "order_date"))
    for group in data.tax_groups:
        entity_id = f"tax.{group.name}"
        entities.append(SemanticEntity(entity_id, "finance.tax.group", value=group.amount))
        relations.append(SemanticRelation(data.id, "has_tax_group", entity_id))

    for line in data.lines:
        entities.append(
            SemanticEntity(
                line.id,
                "commerce.line_item",
                value=line.description,
                attributes={
                    "product_name": line.product_name,
                    "quantity": line.quantity,
                    "unit_price": line.unit_price,
                    "subtotal": line.subtotal,
                },
            )
        )
        relations.append(SemanticRelation(data.id, "has_line", line.id))

    return SemanticGraph(tuple(entities), tuple(relations))


# Compatibility is deliberate: these were public before the prototype was
# recognised as shared by sale.order and account.move.  They are aliases, not
# parallel types or a second projection path.
QuotationLineData = CommercialLineData
QuotationData = CommercialDocumentData
quotation_semantic_graph = commercial_document_semantic_graph
