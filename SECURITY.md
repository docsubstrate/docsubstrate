# Security Policy

DocSubstrate is pre-1.0 infrastructure. The public interfaces and storage formats are not yet promised to be stable, and the project does not currently claim regulatory compliance, legal evidentiary sufficiency, or suitability as a sole system of record.

## Reporting a vulnerability

Suspected vulnerabilities must not be disclosed in public issues. Use GitHub
Private Vulnerability Reporting for the Core repository
`docsubstrate/docsubstrate`; reports are handled by that repository's
maintainers. No personal email address or corporate contact identity is part
of this policy.

Public issues remain appropriate for ordinary, non-security bugs.

Useful reports include:

- affected version or commit;
- impact and threat model;
- reproduction steps or proof of concept;
- whether integrity, confidentiality, authenticity, or authorization is affected;
- suggested mitigation, if known.

## Security-sensitive areas

Changes involving canonicalization, hashing, signatures, verification, authority, provenance, artifact identity, or source-system adapters should be treated as security-sensitive and require focused review.

## Supported versions

Before the first stable release, only the latest published version is supported.

## Response commitment

During the alpha the maintainers do not commit to a fixed response SLA.
