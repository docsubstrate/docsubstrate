#!/usr/bin/env python3
"""Generate the public-alpha sale-order fixture from invented values only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SCHEMA = "docsubstrate.public-alpha-sale-order/v1"


def fixture() -> dict:
    """Return a deterministic input with no captured document or asset."""
    return {
        "schema": SCHEMA,
        "synthetic_only": True,
        "report_action": "sale.report_saleorder",
        "layout": "standard",
        "document": {
            "id": "sale-order.synthetic.alpha-001",
            "number": "SO-ALPHA-000123",
            "display_title": "Quotation # SO-ALPHA-000123",
            "customer_name": "Example Buyer Cooperative",
            "seller_name": "Example Maker Laboratory",
            "currency": "USD",
            "date": "2030-01-15",
            "validity_date": "2030-02-15",
            "salesperson": "Synthetic Operator",
            "payment_terms": "Payment due within 30 days.",
            "note": (
                "Generated demonstration only. No person, tenant, or customer "
                "record is represented."
            ),
            "customer_address": {
                "name": "Example Buyer Cooperative",
                "lines": [
                    "100 Example Avenue",
                    "Sample City 00000",
                    "Exampleland",
                ],
            },
            "shipping_address": {
                "name": "Example Receiving Dock",
                "lines": [
                    "200 Demonstration Road",
                    "Sample City 00001",
                    "Exampleland",
                ],
            },
            "lines": [
                {
                    "id": "line.synthetic.1",
                    "description": "Calibration fixture",
                    "quantity": "2",
                    "unit_price": "125.00",
                    "subtotal": "250.00",
                    "uom": "Units",
                    "taxes_label": "Example tax 5%",
                },
                {
                    "id": "line.synthetic.2",
                    "description": (
                        "Ordinary prose is intentionally allowed to wrap when "
                        "its containing column is narrow."
                    ),
                    "quantity": "1",
                    "unit_price": "50.00",
                    "subtotal": "50.00",
                    "uom": "Service",
                    "taxes_label": None,
                },
            ],
            "tax_groups": [
                {
                    "name": "Example tax 5%",
                    "amount": "15.00",
                    "amount_text": "15.00",
                }
            ],
            "untaxed_amount": "300.00",
            "tax_amount": "15.00",
            "total_amount": "315.00",
        },
        "expected_text": [
            "Quotation # SO-ALPHA-000123",
            "Example Buyer Cooperative",
            "Calibration fixture",
            "315.00 USD",
        ],
    }


def encoded_fixture() -> bytes:
    return (json.dumps(fixture(), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    args.output.write_bytes(encoded_fixture())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
