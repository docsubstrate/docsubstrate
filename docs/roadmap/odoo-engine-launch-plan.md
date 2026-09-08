# Odoo report engine launch plan

Status: launch proposal. It does not claim that a public engine release exists
or that wkhtmltopdf can already be replaced for every report.

## Release thesis

The first release is a **drop-in Odoo report engine with automatic
wkhtmltopdf fallback and an automatically generated compatibility report**.
It must never be announced as “fully replaces wkhtmltopdf.” Unsupported or
failed custom reports taking the documented fallback path is expected product
behavior, not a hidden success.

The engine proves one practical edge of DocSubstrate: a renderer is a
replaceable execution mechanism, while document identity, intended content,
artifacts, provenance, and correspondence remain explicit.

## Naming options

Every option carries the substrate name so installation remains visibly linked
to the underlying architecture.

| Repository/distribution option | Python import | Odoo entry module | Note |
| --- | --- | --- | --- |
| `docsubstrate/docsubstrate-odoo-report-engine` | `docsubstrate_odoo_engine` | `report_docsubstrate` | Recommended: source system and responsibility are immediately clear. |
| `docsubstrate/docsubstrate-report-engine-odoo` | `docsubstrate_report_engine.odoo` | `report_docsubstrate` | Groups future engines lexically, but reads less naturally. |
| `docsubstrate/odoo-docsubstrate-report` | `odoo_docsubstrate_report` | `report_docsubstrate` | Familiar Odoo naming, but makes the substrate look secondary. |

The public package/repository name should not be the name of a consultancy,
customer, or deployment. Final package-index availability and trademark checks
remain a release task.

## Repository split

```text
docsubstrate/docsubstrate
    generic A0 contracts, profiles, independent readers, conformance fixtures

docsubstrate/docsubstrate-odoo-report-engine
    Apache-2.0 renderer engine, compatibility runner, synthetic reports,
    fallback contract, generated matrix, engine documentation

OCA/reporting-engine (proposed upstream entry)
    thin AGPL-compatible report_docsubstrate Odoo module only

private/managed repositories
    hosting, production configuration, customer reports/evidence, paid support
```

The OCA module translates the supported Odoo call surface into the engine
contract. It must not contain the engine, private compatibility evidence, or a
forked DocSubstrate core. Exact AGPL/linkage and packaging compatibility must be
reviewed before submission.

## First public release contract

1. Detect whether a report and runtime combination is supported.
2. Attempt DocSubstrate-backed rendering only inside the declared compatibility
   envelope.
3. Fall back automatically to wkhtmltopdf on an unsupported feature or a
   classified engine failure when the fallback policy allows it.
4. Preserve the selected engine, failure classification, fallback result, test
   fixture identity, source version, and output comparison as diagnostic
   evidence; do not represent engine success as document authority.
5. Generate a machine-readable and human-readable compatibility report from the
   same test results.

Fallback must be bounded against loops, duplicate side effects, timeouts, and
loss of the original failure. A fallback-rendered artifact must identify its
actual renderer rather than masquerading as engine output.

## Automatically generated compatibility matrix

The matrix is release evidence, not a hand-maintained marketing table. One test
result record should contain at least:

```text
engine commit and release
Odoo edition/version/build
Python version
report fixture identity and digest
feature tags (tables, headers, RTL, images, barcodes, page totals, ...)
primary engine result
fallback attempted/result
output artifact digest
comparison policy/version
fidelity-axis results
execution duration and failure classification
```

The generator publishes:

- per-case JSON suitable for independent analysis;
- a Markdown summary by Odoo/Python/report/feature;
- the exact tested/unsupported/fallback counts;
- links to synthetic fixtures and reproducible commands; and
- a clear distinction between local conformance evidence and live deployment
  evidence.

No release may convert a fallback pass into a native-render pass. The initial
matrix reports only the cases actually executed at the tagged commit.

## Support scope fixed from day one

Publish and version this statement with the first release:

> We support only the Odoo editions/versions, Python versions, installation
> modes, and report features marked supported in the compatibility matrix for
> this release. Custom QWeb templates and third-party modules are accepted as
> diagnostic reports, not presumed supported configurations. When an
> unsupported or classified-failure case automatically renders successfully
> through the documented wkhtmltopdf fallback, fallback is working as designed
> and is not an engine defect. We investigate reproducible failures against
> public or redistributable fixtures. We do not accept customer documents,
> credentials, databases, or remote production access through public issues.

Also declare:

- supported community/enterprise editions and exact version ranges;
- supported CPython and operating-system/container baselines;
- what “drop-in” covers (installation/call path), not visual identity for every
  possible report;
- comparison tolerances and known fidelity limitations;
- security response path and supported maintenance window; and
- whether a failure belongs to the engine, Odoo entry module, source report,
  dependency, or deployment.

## Issue template

```markdown
### Environment
- engine release/commit:
- Odoo edition and exact version/build:
- Python version:
- installation mode:
- wkhtmltopdf version (fallback cases):

### Reproduction
- public/minimal report fixture or repository:
- exact command/action:
- expected result:
- primary engine result:
- was fallback attempted, and what happened:

### Compatibility evidence
- generated case/report ID:
- feature tags:
- failure classification:
- sanitized logs or comparison output:

### Data and security confirmation
- [ ] No credentials, customer data, production document, database dump, or
      restricted artifact is attached.
```

The template must route suspected vulnerabilities to private security
reporting rather than a public issue.

## Announcement skeleton

### Shared factual core

> DocSubstrate Odoo Report Engine `[release]` is available for testing. This is
> an Apache-2.0 drop-in report-engine experiment for the declared Odoo/Python
> matrix. It uses automatic wkhtmltopdf fallback for unsupported or classified
> failure cases and publishes a compatibility report generated from the tagged
> test run. It does **not** claim to replace wkhtmltopdf for every Odoo report.
> Start with `[quickstart]`, inspect `[compatibility matrix]`, and report only
> sanitized, reproducible cases through `[issue link]`.

### Channel-specific additions

- **Odoo forum:** installation path, supported versions, one minimal report,
  fallback behavior, and request for reproducible community/enterprise cases.
- **OCA mailing list:** proposed thin AGPL entry-module boundary, why engine
  ownership stays in the DocSubstrate organization, license/linkage review, and
  request for maintainer feedback before an OCA PR.
- **r/odoo:** short demo, honest supported/unsupported counts, quick rollback,
  and a warning not to test first on production.
- **LinkedIn:** the architectural reason for separating durable document meaning
  from the renderer, with links to source and executable evidence rather than a
  “complete replacement” claim.

Announcements are published under the owner’s chosen public name, not under a
customer identity. Digiter sponsorship may be acknowledged separately from
maintenance and copyright ownership.

## Launch gates

- [ ] Clean-room public repository and dependency/license inventory completed.
- [ ] No customer reports, identifiers, credentials, deployment paths, or
  restricted evidence exist in files or reachable history.
- [ ] Drop-in installation and uninstall/rollback tested from a clean Odoo
  environment.
- [ ] Automatic fallback, failure preservation, and no-loop behavior tested.
- [ ] Compatibility JSON and Markdown regenerate deterministically from the
  tagged result set.
- [ ] Support matrix and support-scope statement name exact versions.
- [ ] Public issue and private security-reporting paths enabled.
- [ ] OCA boundary and AGPL compatibility reviewed before any submission.
- [ ] Release notes and all four announcement variants reviewed for unsupported
  claims.
- [ ] Explicit human approval recorded for tag, packages, repository visibility,
  and publication.
