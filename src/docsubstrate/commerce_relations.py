"""Canonical commerce document relationship vocabulary."""

CONFIRMED_AS = "confirmed_as"
FULFILLED_BY = "fulfilled_by"
BILLED_BY = "billed_by"
SETTLED_BY = "settled_by"
CREDITED_BY = "credited_by"
RETURNED_BY = "returned_by"

COMMERCE_DOCUMENT_KINDS = {
    "quotation": "commerce.quotation",
    "sales_order": "commerce.sales_order",
    "delivery": "commerce.delivery",
    "invoice": "commerce.invoice",
    "payment": "commerce.payment",
    "credit_note": "commerce.credit_note",
    "return": "commerce.return",
}
