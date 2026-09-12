"""Odoo-shell payload for the synthetic public-alpha record-native route.

The runner supplies a fresh database containing only Odoo Community base data
and this invented record.  The payload prints one machine-readable result line
and does not write a fixture or PDF outside that disposable database/process.
"""

from __future__ import annotations

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
    """Ephemeral event history for this disposable process only."""

    def __init__(self):
        super().__init__()
        self.events = []

    def update(self, *args, **kwargs):
        values = dict(*args, **kwargs)
        super().update(values)
        event = {key: values[key] for key in sorted(values) if key in _TRACE_KEYS}
        if event:
            self.events.append(event)


class SyntheticForcedRendererError(RuntimeError):
    pass


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
    requests = [
        event["requested"]
        for event in trace.events
        if "requested" in event
    ]
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
parameter.set_param("docsubstrate.strict", "false")

counts = {"reportlab_render_bytes": 0, "wkhtmltopdf": 0}
force_reportlab_failure = {"active": False}
original_render_bytes = ReportLabCanvasRenderer.render_bytes


def observed_render_bytes(renderer, document):
    counts["reportlab_render_bytes"] += 1
    if force_reportlab_failure["active"]:
        raise SyntheticForcedRendererError("synthetic forced ReportLab producer failure")
    return original_render_bytes(renderer, document)


wkhtml_owners = [
    owner
    for owner in type(report).__mro__
    if "_run_wkhtmltopdf" in owner.__dict__
]
if len(wkhtml_owners) < 2:
    fail("could not locate the Odoo wkhtmltopdf implementation below the adapter")
wkhtml_owner = wkhtml_owners[1]
original_wkhtmltopdf = wkhtml_owner.__dict__["_run_wkhtmltopdf"]


def observed_wkhtmltopdf(recordset, *args, **kwargs):
    counts["wkhtmltopdf"] += 1
    return original_wkhtmltopdf(recordset, *args, **kwargs)


report_class = type(report)


def no_record_native_document(recordset, report_ref, res_ids, data=None):
    return None


with (
    patch.object(ReportLabCanvasRenderer, "render_bytes", observed_render_bytes),
    patch.object(wkhtml_owner, "_run_wkhtmltopdf", observed_wkhtmltopdf),
):
    native_before = dict(counts)
    native_trace = RecordingTrace()
    native_pdf, native_kind = render(report, order, native_trace)
    native_counts = {
        key: counts[key] - native_before[key]
        for key in sorted(counts)
    }

    forced_before = dict(counts)
    forced_trace = RecordingTrace()
    force_reportlab_failure["active"] = True
    with patch.object(
        report_class,
        "_docsubstrate_native_document",
        no_record_native_document,
    ):
        fallback_pdf, fallback_kind = render(report, order, forced_trace)
    force_reportlab_failure["active"] = False
    forced_counts = {
        key: counts[key] - forced_before[key]
        for key in sorted(counts)
    }

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
        fail(
            f"native trace mismatch for {key}: "
            f"{native_trace.get(key)!r} != {expected!r}"
        )
if requested_renderer(native_trace) != "reportlab":
    fail("record-native case did not record a ReportLab request")
if native_counts != {"reportlab_render_bytes": 1, "wkhtmltopdf": 0}:
    fail(f"record-native producer calls are wrong: {native_counts!r}")

if fallback_kind != "pdf" or not fallback_pdf.startswith(b"%PDF-"):
    fail("forced fallback did not return a PDF stream")
if requested_renderer(forced_trace) != "reportlab":
    fail("forced case did not begin with a ReportLab request")
if forced_trace.get("actual") != "wkhtmltopdf":
    fail(f"forced actual renderer is wrong: {forced_trace.get('actual')!r}")
if forced_trace.get("fallback") is not True:
    fail("forced producer failure did not set fallback=true")
if forced_trace.get("qweb_evaluated") is not True:
    fail("forced fallback did not record QWeb evaluation")
if "SyntheticForcedRendererError" not in forced_trace.get("fallback_reason", ""):
    fail(f"forced fallback reason is wrong: {forced_trace.get('fallback_reason')!r}")
if forced_counts != {"reportlab_render_bytes": 1, "wkhtmltopdf": 1}:
    fail(f"forced producer calls are wrong: {forced_counts!r}")
if not env["docsubstrate.artifact"].sudo().search_count([]):
    fail("record-native route did not persist its artifact manifest")

cases = [
    {
        "name": "record-native",
        "forced_condition": False,
        "requested": requested_renderer(native_trace),
        "actual": native_trace["actual"],
        "fallback": native_trace["fallback"],
        "render_host": native_trace["render_host"],
        "qweb_evaluated": native_trace["qweb_evaluated"],
        "producer_calls": native_counts,
        "trace_events": native_trace.events,
        "pdf_header": native_pdf.splitlines()[0].decode("ascii"),
        "pdf_sha256": hashlib.sha256(native_pdf).hexdigest(),
    },
    {
        "name": "forced-reportlab-producer-failure",
        "forced_condition": True,
        "forced_exception": "SyntheticForcedRendererError",
        "requested": requested_renderer(forced_trace),
        "actual": forced_trace["actual"],
        "fallback": forced_trace["fallback"],
        "fallback_reason": forced_trace["fallback_reason"],
        "render_host": forced_trace["render_host"],
        "qweb_evaluated": forced_trace["qweb_evaluated"],
        "producer_calls": forced_counts,
        "trace_events": forced_trace.events,
        "pdf_header": fallback_pdf.splitlines()[0].decode("ascii"),
        "pdf_sha256": hashlib.sha256(fallback_pdf).hexdigest(),
    },
]
if [case["name"] for case in cases if case["fallback"]] != [
    "forced-reportlab-producer-failure"
]:
    fail("fallback occurred outside the one explicit forced condition")

result = {
    "schema": "docsubstrate.public-alpha-odoo19-harness/v2",
    "status": "PASS",
    "synthetic_only": True,
    "odoo_edition": "Community",
    "odoo_version": "19.0",
    "report_action": report.report_name,
    "model": report.model,
    "default_policy": "qweb",
    "selected_policy": "reportlab",
    "cases": cases,
    "fallback_case_names": [case["name"] for case in cases if case["fallback"]],
    "tenant_accessed": False,
}
print("DOCSUBSTRATE_PUBLIC_ALPHA_RESULT=" + json.dumps(result, sort_keys=True))
