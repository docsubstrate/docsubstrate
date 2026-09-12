# Clean-install verification

These instructions describe the bounded public-alpha reproducibility check.
They do not publish or deploy anything.

A standalone Core checkout or sdist does not contain the adapter repository
or `tools/assemble_a2_addon.py`, so it cannot perform the cross-repository byte
comparison or the Odoo seam check. Record both as **EXCLUDED / NOT PASSED** in
Core-only verification. To pass them, obtain the separately reviewed adapter
source and continue with the adapter procedure below; never infer their result
from a successful Core build.

## Core producer

Use Python 3.12 and the build backend pinned by `pyproject.toml`. The certified
Core wheel is built from the root of the exact reviewed Core commit with this
offline command (verified with `uv 0.11.14`):

```text
SOURCE_DATE_EPOCH=1788912000 uv build \
  --python 3.12 \
  --offline \
  --no-python-downloads \
  --no-create-gitignore \
  --wheel \
  --out-dir <new-build-directory> \
  .
```

The only output must be
`docsubstrate-0.1.0a1-py3-none-any.whl`, with SHA-256
`72fb708ab0630de5bf3242f0e3f15a21f820f37c0110339095925a93ffaa4ad4`.
Repeat into a second new directory and require identical bytes. The adapter
assembler accepts exactly that filename and digest. A wheel built without the
specified epoch is not the certified artifact.

In a new virtual environment, install that Core wheel and the exact
`reportlab==5.0.1` wheel, then run:

```text
python tools/public_alpha_synthetic_demo.py \
  --candidate-sha <fresh-history-commit> \
  --fixture examples/synthetic/public_alpha_sale_order.json \
  --behavior public-alpha/behavior/odoo19-sale-order-v1.json \
  --output <new-output-directory>
```

Run it twice into two new directories. Each directory must contain exactly
`quotation.pdf`, `render-trace.json`, `support-manifest.json`, and
`CHECKSUMS.sha256`; corresponding bytes must agree.

## Odoo 19 Community seam

From the public adapter source checkout, build the directly loadable release
directory first. Both wheel paths are mandatory and hash-verified; ambient
Odoo ReportLab 4.1.0 is not accepted:

```text
python tools/assemble_a2_addon.py \
  --ref <reviewed-adapter-commit> \
  --core-wheel <docsubstrate-0.1.0a1-py3-none-any.whl> \
  --reportlab-wheel <reportlab-5.0.1-py3-none-any.whl> \
  --out-dir <new-release-directory>
```

The result must be `<new-release-directory>/docsubstrate_report/`, containing
`__manifest__.py`, `lib/docsubstrate/`, `lib/reportlab/`, `PUBLIC_RELEASE.json`,
and `SHA256SUMS`. Pass that `docsubstrate_report/` directory to the harness.

Every Odoo service, module-install, module-upgrade, and shell process that can
load the addon must start with the assembled addon's `lib/` directory ahead of
ambient site-packages. Use `PYTHONPATH` or an equivalent process-wide startup
mechanism before Python starts. For example:

```sh
ADDON_DIR=/absolute/path/to/docsubstrate_report
PYTHONPATH="${ADDON_DIR}/lib${PYTHONPATH:+:${PYTHONPATH}}" \
  /absolute/path/to/odoo-bin <service-or-install-or-upgrade-or-shell-arguments>
```

Apply that environment to every worker and helper process, including the
process that performs install or upgrade. The addon `__init__` cannot repair a
prior ReportLab import: if ReportLab or DocSubstrate is already bound outside
the assembled `lib/`, the guard fails closed and the process must be restarted
with the correct process-start environment.

`tools/run_public_alpha_odoo19_harness.py` uses only caller-supplied wheels,
the addon tree, an invented sale order, and locally cached Odoo/PostgreSQL
images. It refuses to pull a missing image, places its containers on an
isolated internal network, checks that the default policy is QWeb, selects the
ReportLab policy explicitly, and expects the certified record-native path to
return PDF 1.4 without QWeb evaluation or fallback.

Run the record-native-only payload explicitly and retain both the JSON result
and final PDF:

```text
python tools/run_public_alpha_odoo19_harness.py \
  --core-wheel <docsubstrate-wheel> \
  --reportlab-wheel <cached-reportlab-wheel> \
  --addon <assembled-docsubstrate_report-directory> \
  --payload public-alpha/odoo-harness/sale_order_smoke_record_native_only.py \
  --output <new-output-directory>
```

Run it twice with identical artifact inputs. The machine-readable trace must
say `requested=reportlab`, `actual=reportlab-native`, `qweb_evaluated=false`,
and `fallback=false`; `final.pdf` must be byte-identical across the two runs.
ReportLab producer failure and invalid engine configuration must raise with
`fallback=false`; neither may automatically invoke wkhtmltopdf. An uncertified
report action remains on its preselected QWeb path and is not a producer-failure
fallback. The only accepted `docsubstrate.render_policy` values are `qweb` and
`reportlab`; Typst and combined policies are unsupported configuration errors.

The fully synthetic PDF demo alone does not exercise the Odoo seam.
