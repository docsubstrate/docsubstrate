#!/usr/bin/env python3
"""Create a deterministic PDF from invented sale-order data."""

from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

from docsubstrate import CommercialDocumentData, CommercialLineData, render_sale_order_pdf


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    document = CommercialDocumentData(
        id="sale-order.synthetic.quickstart",
        number="SO-DEMO-001",
        display_title="Quotation # SO-DEMO-001",
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
    pdf = render_sale_order_pdf(document)
    if not pdf.startswith(b"%PDF-1.4"):
        raise RuntimeError("the bounded producer did not emit PDF 1.4")
    args.output.write_bytes(pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
