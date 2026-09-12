"""Odoo-shell payload for the A2 alpha's own acceptance target.

This payload exercises exactly the shipped record-native acceptance target:
requested=reportlab, actual=reportlab-native, qweb_evaluated=false, and
fallback=false. Producer failures and unsupported engine configuration fail
closed rather than automatically invoking wkhtmltopdf.
"""

from __future__ import annotations

import base64
import hashlib
import json
from unittest.mock import patch

from docsubstrate.renderers.reportlab_canvas import ReportLabCanvasRenderer

env = globals()["env"]


def fail(message):
    raise AssertionError(message)


_TRACE_KEYS = {
    "actual",
    "fallback",
    "fallback_reason",
    "native_certified",
    "native_selected",
    "qweb_evaluated",
    "render_host",
    "requested",
    "seam_reached",
}


class RecordingTrace(dict):
    def __init__(self):
        super().__init__()
        self.events = []

    def update(self, *args, **kwargs):
        values = dict(*args, **kwargs)
        super().update(values)
        event = {key: values[key] for key in sorted(values) if key in _TRACE_KEYS}
        if event:
            self.events.append(event)


def render(report, order, trace):
    streams, kind = report.with_context(
        docsubstrate_render_trace=trace
    )._pre_render_qweb_pdf(
        report.report_name,
        res_ids=[order.id],
    )
    stream = streams[order.id]["stream"]
    return stream.getvalue(), kind


def requested_renderer(trace):
    requests = [event["requested"] for event in trace.events if "requested" in event]
    if not requests:
        fail("renderer request was not recorded")
    return requests[0]


parameter = env["ir.config_parameter"].sudo()
if parameter.get_param("docsubstrate.render_policy", "qweb") != "qweb":
    fail("public alpha is not default-off")

partner = env["res.partner"].create(
    {
        "name": "Example Buyer Cooperative",
        "street": "100 Example Avenue",
        "city": "Sample City",
        "zip": "00000",
        "country_id": False,
    }
)
product = env["product.product"].create(
    {
        "name": "Calibration fixture",
        "type": "service",
        "list_price": 125.0,
    }
)
order = env["sale.order"].create(
    {
        "partner_id": partner.id,
        "partner_invoice_id": partner.id,
        "partner_shipping_id": partner.id,
        "date_order": "2026-01-15 10:30:00",
        "order_line": [
            (
                0,
                0,
                {
                    "product_id": product.id,
                    "name": "Calibration fixture",
                    "product_uom_qty": 2.0,
                    "price_unit": 125.0,
                },
            )
        ],
    }
)
report = env.ref("sale.action_report_saleorder")
parameter.set_param("docsubstrate.render_policy", "reportlab")

counts = {"reportlab_render_bytes": 0, "wkhtmltopdf": 0}
original_render_bytes = ReportLabCanvasRenderer.render_bytes


def observed_render_bytes(renderer, document):
    counts["reportlab_render_bytes"] += 1
    return original_render_bytes(renderer, document)


wkhtml_owners = [
    owner for owner in type(report).__mro__ if "_run_wkhtmltopdf" in owner.__dict__
]
if len(wkhtml_owners) < 2:
    fail("could not locate the Odoo wkhtmltopdf implementation below the adapter")
wkhtml_owner = wkhtml_owners[1]
original_wkhtmltopdf = wkhtml_owner.__dict__["_run_wkhtmltopdf"]


def observed_wkhtmltopdf(recordset, *args, **kwargs):
    counts["wkhtmltopdf"] += 1
    return original_wkhtmltopdf(recordset, *args, **kwargs)


with (
    patch.object(ReportLabCanvasRenderer, "render_bytes", observed_render_bytes),
    patch.object(wkhtml_owner, "_run_wkhtmltopdf", observed_wkhtmltopdf),
):
    native_trace = RecordingTrace()
    native_pdf, native_kind = render(report, order, native_trace)
    native_counts = dict(counts)

if native_kind != "pdf" or not native_pdf.startswith(b"%PDF-1.4"):
    fail("record-native route did not return the expected PDF 1.4 stream")

expected_trace = {
    "actual": "reportlab-native",
    "render_host": "record-native",
    "native_certified": True,
    "native_selected": True,
    "qweb_evaluated": False,
    "fallback": False,
}
for key, expected in expected_trace.items():
    if native_trace.get(key) != expected:
        fail(f"native trace mismatch for {key}: {native_trace.get(key)!r} != {expected!r}")
if requested_renderer(native_trace) != "reportlab":
    fail("record-native case did not record a ReportLab request")
if native_counts != {"reportlab_render_bytes": 1, "wkhtmltopdf": 0}:
    fail(f"record-native producer calls are wrong: {native_counts!r}")
if not env["docsubstrate.artifact"].sudo().search_count([]):
    fail("record-native route did not persist its artifact manifest")

result = {
    "schema": "docsubstrate.public-alpha-odoo19-harness-native-only/v1",
    "status": "PASS",
    "synthetic_only": True,
    "odoo_edition": "Community",
    "odoo_version": "19.0",
    "report_action": report.report_name,
    "model": report.model,
    "default_policy": "qweb",
    "selected_policy": "reportlab",
    "case": {
        "name": "record-native",
        "requested": requested_renderer(native_trace),
        "actual": native_trace["actual"],
        "fallback": native_trace["fallback"],
        "render_host": native_trace["render_host"],
        "qweb_evaluated": native_trace["qweb_evaluated"],
        "producer_calls": native_counts,
        "artifact_persisted": True,
        "trace_events": native_trace.events,
        "pdf_header": native_pdf.splitlines()[0].decode("ascii"),
        "pdf_sha256": hashlib.sha256(native_pdf).hexdigest(),
        "pdf_base64": base64.b64encode(native_pdf).decode("ascii"),
    },
    "out_of_scope": {"producer-failure": "fails closed; not exercised here"},
    "tenant_accessed": False,
}
print("DOCSUBSTRATE_PUBLIC_ALPHA_RESULT=" + json.dumps(result, sort_keys=True))
