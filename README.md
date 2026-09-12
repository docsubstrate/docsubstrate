# DocSubstrate A2 — Odoo 19 ReportLab alpha

Requires Python 3.12 or newer. The public components are
[DocSubstrate Core](https://github.com/docsubstrate/docsubstrate) and the
[Odoo adapter](https://github.com/docsubstrate/odoo-adapter).

This alpha is a bounded PDF producer for one Odoo 19 Community report path:
one `sale.order` rendered through `sale.report_saleorder` by the record-native
ReportLab backend. On that path the adapter does not evaluate QWeb and does
not start wkhtmltopdf.

The Odoo policy remains **QWeb by default**. An operator must explicitly
select the ReportLab policy. Unsupported report actions remain outside this
alpha. Automatic fallback after a ReportLab producer failure is neither
packaged nor claimed by this release.

This is not a claim of arbitrary HTML/CSS support, every Odoo report, every
external layout, production performance, or PDF conformance beyond emitting
a PDF 1.4 header. The executable boundary is the exact report action above.

## Installation shape

The integration has two parts:

1. the Apache-2.0 `docsubstrate==0.1.0a1` wheel;
2. the pinned ReportLab 5.0.1 wheel; and
3. the LGPL-3 `docsubstrate_report` Odoo addon source.

The public assembler stages both wheels into the release addon's own `lib/`
directory. The directly loadable release asset is rooted at
`docsubstrate_report/`; its import guard fails closed if either managed module
was previously imported from anywhere outside that directory. The source
checkout alone is assembly input, not the installable addon asset. See
`public-alpha/CLEAN-INSTALL.md` in the source distribution for the exact
assembly and disposable Odoo 19 verification procedure.

## Executable wheel quickstart

Install `docsubstrate==0.1.0a1` with `reportlab==5.0.1`, then run the
packaged-API example:

```bash
python examples/a2_sale_order_quickstart.py quotation.pdf
```

The example uses only names exported by `docsubstrate`:

```python
from decimal import Decimal
from docsubstrate import CommercialDocumentData, CommercialLineData, render_sale_order_pdf

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
            quantity=Decimal("2"),
            unit_price=Decimal("125.00"),
            subtotal=Decimal("250.00"),
        ),
    ),
    untaxed_amount=Decimal("250.00"),
    tax_amount=Decimal("0.00"),
    total_amount=Decimal("250.00"),
)

pdf = render_sale_order_pdf(document)
assert pdf.startswith(b"%PDF-1.4")
open("quotation.pdf", "wb").write(pdf)
```

All values in the example are invented. The repository test executes the
same API and verifies deterministic bytes.

## Code review evidence

`CODE-PROVENANCE.json` records byte digests for the retained runtime modules,
the bounded synthetic contract that exercises them, and exact public source
coordinates for the two external compatibility inputs. It is an input to
independent review, not evidence that the review has passed, and makes no
authorship, ownership, right-to-license, legal-clearance, publication-readiness,
or publication-authority claim.

A standalone Core checkout or sdist does not contain the adapter repository
or its assembler, so it cannot perform a cross-repository byte comparison.
In that environment the adapter assembly and Odoo checks are **EXCLUDED / NOT
PASSED**, never inferred from Core-only results. Run the separate adapter
procedure in `public-alpha/CLEAN-INSTALL.md` before making an assembled-addon
claim.

The public artifact and targeted release-contract suites pass. The full
development tree has exactly three inherited, non-release-gate failures outside
the bounded alpha runtime closure:

- `tests/test_legacy_flex_items.py::test_growth_is_added_on_top_of_the_preferred_width`
- `tests/test_report_css.py::test_a_link_inside_a_paragraph_is_coloured_on_its_own`
- `tests/test_report_css.py::test_a_table_cell_styles_its_runs_too`

## Odoo path contract

- Supported report action: `sale.report_saleorder` only.
- Source model: `sale.order`.
- Cardinality: exactly one source record.
- Requested policy: `reportlab`.
- Actual producer on success: `reportlab-native`.
- QWeb evaluation on the bounded path: false.
- wkhtmltopdf calls on the bounded path: zero.
- Default global policy after installation: `qweb`.

## Security

Use GitHub Private Vulnerability Reporting in
`docsubstrate/docsubstrate` for suspected Core vulnerabilities.
Do not disclose them in public issues. Ordinary non-security bugs may use
public issues. See `SECURITY.md`; the alpha has no fixed response SLA.

## Licences

The core wheel is Apache-2.0. The separately assembled Odoo addon is
LGPL-3.0-only and includes the complete LGPL-3.0 and GPL-3.0 texts. See
`NOTICE` for the package
boundary. This README does not make a rights or publication determination.
