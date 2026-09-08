# Public project checklist

Status: operational checklist. Checked items describe the current A0 public
repository as observed on 2026-09-08; they are not a release or API-stability
claim.

## Repository and provenance

- [x] Publish A0 from a fresh, audited history rather than exposing the private
  research repository or its branches.
- [x] Canonical public repository: `docsubstrate/docsubstrate`.
- [x] Original research and non-A0 work remain in a separate private repository.
- [x] Public root records the audited private source commit and source-archive
  digest in `NOTICE` without making private history reachable.
- [x] Public fixtures are synthetic and the independent reader does not require
  the source application or DocSubstrate implementation.
- [ ] Repeat file, reachable-history, credential, customer-data, and dependency
  license scans for every release candidate.
- [ ] Publish a release artifact digest through an authenticated channel and add
  a detached publisher signature when publisher identity is claimed.

## License decision

The owner decision recorded for the A0 substrate is **Apache License 2.0**. The
repository `LICENSE`, `NOTICE`, and project metadata already agree. This table
records the trade-off rather than silently reopening the decision:

| Concern | MIT | Apache-2.0 |
| --- | --- | --- |
| Permission grant | Very short permissive grant | Permissive grant with explicit conditions and definitions |
| Patent treatment | No explicit patent license | Explicit contributor patent license and termination on certain patent litigation |
| Redistribution notices | Preserve copyright and license | Preserve license; retain NOTICE information where applicable; mark modified files |
| Operational burden | Minimal | Slightly more release/compliance bookkeeping |
| Fit for a substrate intended for broad implementation | Simple adoption | Clearer patent posture for implementers and contributors |
| Owner trade-off | Less text and process, but more patent ambiguity | Gives downstream users an explicit patent grant while also granting the same defined patent rights from contributors; the owner must be comfortable with that grant and NOTICE discipline |

- [x] Keep A0 Apache-2.0 unless a separately authorized relicensing process is
  supported by complete contributor rights.
- [ ] Add a short licensing section to `CONTRIBUTING.md` explaining that
  contributions are submitted under Apache-2.0 and must not contain code the
  contributor cannot license.
- [ ] Obtain legal review before making product-specific claims about patent,
  regulatory, signature, erasure, or evidentiary effect.

## Repository boundaries

- [x] Keep generic A0 core, profiles, independent verification, and synthetic
  conformance evidence in `docsubstrate/docsubstrate`.
- [ ] Put the Odoo report engine in a separate public repository whose name
  carries `docsubstrate`; keep its engine code Apache-2.0 where dependencies and
  linkage allow.
- [ ] Keep the OCA entry module thin and AGPL-compatible; do not move ownership
  of the engine repository or generic architecture into OCA.
- [ ] Keep managed services, commercial engines, customer deployments,
  production adapters, and restricted evidence outside the A0 repository.
- [ ] Give every split repository its own license inventory, support matrix,
  security policy, release process, and no-customer-data scan.

## GitHub discoverability

- [ ] Organization profile explains: “Application-neutral infrastructure for
  durable, self-describing institutional documents and records.”
- [ ] Public maintainer profile uses the searchable name `Zen (Chen-Yu) Hsieh`
  and links the organization without exposing login/recovery addresses.
- [ ] Pin `docsubstrate/docsubstrate` and, after its first supported release, the
  Odoo report-engine repository.
- [ ] Add restrained repository topics such as `document-infrastructure`,
  `digital-preservation`, `provenance`, `institutional-records`, and
  `application-independent`.
- [ ] Add a social preview only after its wording is reviewed for unsupported
  novelty, security, legal, and production-readiness claims.

## Contribution invitation

- [ ] Add `CONTRIBUTING.md` with a “Write an engine adapter” path that asks a
  contributor to:
  1. identify the exact source/renderer/runtime boundary;
  2. declare which meanings remain owned by an existing vocabulary or source;
  3. map inputs to DocSubstrate Objects, Expressions, Occurrences, Relations,
     Artifacts, basis, and dependencies without using host status as truth;
  4. provide deterministic fixtures and negative cases;
  5. run a kill-runtime and independent-reader test;
  6. document fallback, unsupported cases, security, and version compatibility;
  7. propose a core change only with a cross-domain counterexample.
- [ ] Add issue and pull-request templates for profile proposals, engine
  adapters, generic-gap reports, and security-sensitive reports.
- [ ] State that an adapter may be valuable without being promoted into the
  generic repository.

## Release readiness

- [ ] Freeze and document the supported API/profile surface for the named
  release; the present A0 README still correctly says pre-alpha and unstable.
- [ ] Run isolated tests, Ruff, build/install smoke tests, deterministic bundle
  reproduction, and the independent-reader round trip from the exact tag.
- [ ] Enable a private security-reporting route before inviting untrusted input
  or making production cryptographic claims.
- [ ] Document compatibility, migration, deprecation, and support windows.
- [ ] Publish limitations prominently: A0 is a reference implementation, the
  JWE profile is provisional interoperable, and signatures do not establish
  institutional authority by themselves.
