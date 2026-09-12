# A2 public-alpha engineering closure

This directory describes the bounded public alpha and its reproducible
verification inputs.

The bounded alpha path is:

```text
Odoo 19 Community sale.report_saleorder (one sale.order)
  -> record-native projection
  -> DocSubstrate page plan
  -> ReportLab PDF producer
```

The path returns a PDF without evaluating QWeb and without
starting wkhtmltopdf.  Unsupported or unqualified report actions retain the
Odoo fallback.  The behavioral contract is in
`behavior/odoo19-sale-order-v1.json`; the demo input is generated from code and
contains invented values only.

The public synthetic demo has exactly four outputs:

- `quotation.pdf`
- `render-trace.json`
- `support-manifest.json`
- `CHECKSUMS.sha256`

The PDF, trace, and support manifest must be byte-identical across two runs.
The checksum file covers the other three outputs.

`CLEAN-INSTALL.md` defines the separate wheel and disposable Odoo 19
Community checks, including final-PDF byte reproducibility.

A standalone Core checkout or sdist lacks the adapter repository and public
assembler and therefore cannot perform the cross-repository byte comparison.
Its adapter assembly and Odoo checks must be recorded as **EXCLUDED / NOT
PASSED** until the adapter procedure has run separately; Core-only success is
not a substitute.

## Verification status

The public artifact and targeted release-contract suites pass. The full
development tree retains exactly three inherited failures outside this
bounded wheel/addon runtime closure; they are non-release-gate for this alpha:

- `tests/test_legacy_flex_items.py::test_growth_is_added_on_top_of_the_preferred_width`
- `tests/test_report_css.py::test_a_link_inside_a_paragraph_is_coloured_on_its_own`
- `tests/test_report_css.py::test_a_table_cell_styles_its_runs_too`

These disclosures do not turn an excluded check into a pass.

This alpha does not claim arbitrary QWeb/CSS compatibility, every Odoo report
or lifecycle path, PDF conformance beyond a PDF 1.4 header, or production
performance. The public nowrap boundary is fixed and regression-tested:
`Paragraph.nowrap` suppresses soft wrapping while preserving authored hard
breaks. This does not claim that an unmarked operator template is automatically
assigned nowrap semantics.
