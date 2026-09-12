#!/usr/bin/env python3
"""Run the bounded, fully synthetic A2 public-alpha demonstration."""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import sys
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

OUTPUT_NAMES = (
    "quotation.pdf",
    "render-trace.json",
    "support-manifest.json",
    "CHECKSUMS.sha256",
)
SUPPORTED_PDF_HEADERS = {b"%PDF-1.4", b"%PDF-1.5", b"%PDF-1.6", b"%PDF-1.7"}


class DemoError(RuntimeError):
    pass


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_json(path: Path) -> tuple[dict, bytes]:
    content = path.read_bytes()
    try:
        value = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DemoError(f"invalid JSON input: {path.name}") from exc
    if not isinstance(value, dict):
        raise DemoError(f"JSON input is not an object: {path.name}")
    return value, content


def _document(fixture: dict):
    from docsubstrate.commerce import (
        AddressData,
        CommercialDocumentData,
        CommercialLineData,
        TaxGroupData,
    )

    source = fixture["document"]

    def address(value):
        return AddressData(value["name"], tuple(value["lines"]))

    return CommercialDocumentData(
        id=source["id"],
        number=source["number"],
        display_title=source["display_title"],
        customer_name=source["customer_name"],
        seller_name=source["seller_name"],
        currency=source["currency"],
        date=source["date"],
        validity_date=source["validity_date"],
        salesperson=source["salesperson"],
        payment_terms=source["payment_terms"],
        note=source["note"],
        customer_address=address(source["customer_address"]),
        shipping_address=address(source["shipping_address"]),
        lines=tuple(
            CommercialLineData(
                id=row["id"],
                description=row["description"],
                quantity=Decimal(row["quantity"]),
                unit_price=Decimal(row["unit_price"]),
                subtotal=Decimal(row["subtotal"]),
                uom=row.get("uom"),
                taxes_label=row.get("taxes_label"),
            )
            for row in source["lines"]
        ),
        tax_groups=tuple(
            TaxGroupData(row["name"], Decimal(row["amount"]), row.get("amount_text"))
            for row in source["tax_groups"]
        ),
        untaxed_amount=Decimal(source["untaxed_amount"]),
        tax_amount=Decimal(source["tax_amount"]),
        total_amount=Decimal(source["total_amount"]),
        layout=fixture["layout"],
    )


@contextmanager
def _offline_renderer():
    from reportlab import rl_config

    old_invariant = rl_config.invariant
    rl_config.invariant = 1

    def denied(*_args, **_kwargs):
        raise DemoError("renderer attempted external I/O")

    try:
        with patch("subprocess.Popen", side_effect=denied), patch(
            "socket.create_connection", side_effect=denied
        ), patch.object(socket.socket, "connect", side_effect=denied):
            yield
    finally:
        rl_config.invariant = old_invariant


def _render(document, layout: str):
    from docsubstrate.commerce import commercial_document_semantic_graph
    from docsubstrate.context import DocumentContext, PresentationProfile
    from docsubstrate.engine_adapters.reportlab import ReportLabEngine
    from docsubstrate.structure_policies import CommercialDocumentStructurePolicy

    semantic = commercial_document_semantic_graph(document)
    structure, relations = CommercialDocumentStructurePolicy().project(document)
    context = DocumentContext(
        kind="commerce.quotation",
        semantic=semantic,
        structure=structure,
        relations=relations,
        presentation=PresentationProfile(
            id="public-alpha-synthetic-odoo19-community",
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
                "layout": layout,
                "primary_color": "#714B67",
                "secondary_color": "#D8DADD",
            },
        ),
        metadata={
            "source": "generated-synthetic",
            "report_action": "sale.report_saleorder",
            "render_host": "record-native",
            "qweb_evaluated": False,
        },
    )
    with _offline_renderer():
        return ReportLabEngine().materialize(context)


def _visible_text(value: object) -> str:
    if isinstance(value, dict):
        values = value.values()
    elif isinstance(value, (list, tuple)):
        values = value
    elif isinstance(value, str):
        return value
    else:
        return ""
    return " ".join(filter(None, (_visible_text(item) for item in values)))


def _strings(value: object):
    if isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value


def run_demo(
    *,
    candidate_sha: str,
    fixture_path: Path,
    behavior_path: Path,
    output: Path,
) -> dict:
    if len(candidate_sha) != 40 or any(char not in "0123456789abcdef" for char in candidate_sha):
        raise DemoError("candidate SHA must be a full lowercase SHA-1")
    if output.exists():
        raise DemoError(f"refusing to overwrite output: {output}")

    fixture, fixture_bytes = _read_json(fixture_path)
    behavior, behavior_bytes = _read_json(behavior_path)
    if fixture.get("schema") != "docsubstrate.public-alpha-sale-order/v1":
        raise DemoError("fixture schema is not the public-alpha sale-order schema")
    if fixture.get("synthetic_only") is not True:
        raise DemoError("fixture is not marked synthetic-only")
    if behavior.get("schema") != "docsubstrate.public-alpha-behavior/v1":
        raise DemoError("behavior schema is not supported")
    if fixture.get("report_action") != behavior["input"]["report_action"]:
        raise DemoError("fixture and behavior report actions disagree")
    for value in _strings(fixture):
        scheme = urlsplit(value).scheme.lower()
        if value.startswith("/") or scheme in {"data", "file", "http", "https"}:
            raise DemoError("fixture contains an external, local-path, or embedded input")

    document = _document(fixture)
    first = _render(document, fixture["layout"])
    second = _render(document, fixture["layout"])
    if first.content != second.content:
        raise DemoError("two synthetic renders are not byte-identical")
    if first.media_type != "application/pdf" or first.engine != "reportlab":
        raise DemoError("producer identity is not ReportLab PDF")
    if first.metadata.get("warnings"):
        raise DemoError(f"render warnings are not allowed: {first.metadata['warnings']!r}")
    header = first.content.splitlines()[0]
    if header not in SUPPORTED_PDF_HEADERS:
        raise DemoError(f"PDF header is outside the public-alpha contract: {header!r}")
    visible = _visible_text(first.metadata.get("text_provenance"))
    missing = [text for text in fixture["expected_text"] if text not in visible]
    if missing:
        raise DemoError(f"expected synthetic text is absent: {missing!r}")

    output.mkdir(parents=True)
    pdf_sha = _sha256(first.content)
    output.joinpath("quotation.pdf").write_bytes(first.content)
    trace = {
        "schema": "docsubstrate.public-alpha-render-trace/v1",
        "candidate_commit": candidate_sha,
        "fixture_sha256": _sha256(fixture_bytes),
        "behavior_sha256": _sha256(behavior_bytes),
        "report_action": fixture["report_action"],
        "layout": fixture["layout"],
        "mode": "record-native",
        "renderer": "reportlab",
        "render_host": "record-native",
        "fallback": False,
        "qweb_evaluated": False,
        "wkhtmltopdf_started": False,
        "subprocess_started": False,
        "network_access": False,
        "pages": first.metadata["pages"],
        "warnings": [],
        "pdf_version": header.decode().removeprefix("%PDF-"),
        "pdf_sha256": pdf_sha,
        "expected_text_present": True,
        "second_run_byte_identical": True,
    }
    trace_bytes = _canonical(trace)
    output.joinpath("render-trace.json").write_bytes(trace_bytes)
    support = {
        "schema": "docsubstrate.public-alpha-support/v1",
        "product": "docsubstrate-odoo-reportlab",
        "candidate_commit": candidate_sha,
        "platform": {"odoo_edition": "Community", "odoo_version": "19.0"},
        "backend": {
            "name": "reportlab",
            "pdf_version": trace["pdf_version"],
            "pdf_conformance": "unvalidated",
        },
        "paths": [
            {
                "report_action": "sale.report_saleorder",
                "model": "sale.order",
                "cardinality": "exactly-one",
                "layout": "standard",
                "mode": "record-native",
                "status": "synthetic-certified",
                "fallback": False,
                "qweb_evaluated": False,
                "no_wkhtml": True,
                "behavior_sha256": trace["behavior_sha256"],
                "trace_sha256": _sha256(trace_bytes),
            }
        ],
        "unsupported": list(behavior["nonclaims"]),
    }
    support_bytes = _canonical(support)
    output.joinpath("support-manifest.json").write_bytes(support_bytes)
    names = ("quotation.pdf", "render-trace.json", "support-manifest.json")
    checksums = "".join(
        f"{_sha256(output.joinpath(name).read_bytes())}  {name}\n" for name in names
    )
    output.joinpath("CHECKSUMS.sha256").write_text(checksums)
    actual = tuple(sorted(path.name for path in output.iterdir()))
    if actual != tuple(sorted(OUTPUT_NAMES)):
        raise DemoError(f"demo output set drifted: {actual!r}")
    return {
        "candidate_commit": candidate_sha,
        "output_names": list(OUTPUT_NAMES),
        "pdf_sha256": pdf_sha,
        "checksums_sha256": _sha256(output.joinpath("CHECKSUMS.sha256").read_bytes()),
        "second_run_byte_identical": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--behavior", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run_demo(
            candidate_sha=args.candidate_sha,
            fixture_path=args.fixture.resolve(),
            behavior_path=args.behavior.resolve(),
            output=args.output.resolve(),
        )
    except (DemoError, KeyError, TypeError, ValueError) as exc:
        print(f"public-alpha-demo: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
