# A0 external-review guide

Audit snapshot: 2026-09-08

This guide defines the bounded source surface that two external technical
reviewers can evaluate as DocSubstrate A0. It is an allowlist, not a declaration
that every file in this repository is cleared for external access.

## Review question

Can an independent implementation preserve and verify the minimum institutional
meaning owned by a document/record entity without relying on its source
application, a running DocSubstrate implementation, or hidden database and
workflow conventions?

Reviewers should try to falsify the thesis by finding:

- durable meaning with no explicit owner;
- an entity that fails after its source runtime is removed;
- a critical dependency that is neither captured nor durably resolvable;
- a domain or execution concept incorrectly promoted into the generic core;
- a projection treated as ground truth;
- protected content whose identity binding or recovery path is ambiguous; or
- a reader behavior that requires importing the DocSubstrate implementation.

## Primitive and query-owner map

| Construct | A0 responsibility | Deliberately does not own |
| --- | --- | --- |
| Identity / Object | Continuing institutional identity and type envelope | Host primary key or descriptive domain fields |
| Relation | Stable, typed graph connection | Undeclared application joins |
| Representation / Expression | What an object expressed, including version and components | Current operational status |
| Artifact | Exact material identity and correspondence to an Expression | Semantic equivalence by itself |
| Occurrence | Basis-qualified account of what happened, when, and through which inputs/outputs | Plan, workflow state, or omniscient truth |
| Resource | Media, location-independent descriptor, materialization, and fixity | Institutional identity |
| Preservation claim | Entity-rooted dependency roles and minimum survivable closure | Total graph replication |
| Protection descriptor / key envelope | Component posture, cryptographic profile, identity binding, and replaceable access paths | Grant, authority, lawful release, or policy decision |

`State`, Authority, Evidence, Agent, Policy, Workflow, and domain document types
do not become new generic primitives merely because applications name them.
Their durable facts are represented through the owners above, declared
vocabularies/profiles, or explicit external bindings.

## A0 source allowlist

The primary review path is:

1. [README](../README.md)
2. [Architecture](architecture.md)
3. [ADR 0032](adr/0032-semantic-self-sovereignty.md)
4. [Core primitive audit](architecture/core-primitive-audit.md)
5. [Interchange profiles](architecture/interchange-profiles.md)
6. [ADR 0033](adr/0033-protected-semantic-components.md)
7. [ADR 0034](adr/0034-jwe-general-json-physical-profile.md)
8. [Standards subtraction matrix](architecture/standards-subtraction-matrix.md)

The executable A0 review surface is limited to these source groups:

- graph/package: `package.py`, `occurrence.py`;
- resources/closure: `resources.py`, `resource_catalog.py`, `durable.py`,
  `self_sovereignty.py`;
- interchange: `preflight.py`, `compliance.py`, `interchange_json.py`,
  `migration.py`, `physical_package.py`;
- protected components: `component_protection.py`, `jwe_general_json.py`;
- independent verification: `tools/independent_reader.py`,
  `tools/closure_report.py`, `tools/generate_review_fixture.py`,
  `tools/build_a0_review_bundle.py`, `tools/verify_review_bundle.py`; and
- the directly corresponding `test_package`, `test_resources`,
  `test_resource_catalog`, `test_durable_closure`, `test_preflight`,
  `test_compliance`, `test_interchange_json`, `test_migration`,
  `test_physical_package`, `test_independent_closure_report`,
  `test_self_sovereignty`, `test_protected_semantic_components`,
  `test_jwe_general_json`, `test_review_fixture`, and `test_a0_review_bundle`
  test modules, plus `tests/conftest.py`.

The review artifact source-maps a minimal A0-specific package initializer with
no re-exports or runtime registration. The private repository's renderer-heavy
initializer stays outside the artifact, while the explicit initializer prevents
the A0 package from silently merging as a namespace package. A0 classes remain
provisional direct-module APIs; neither their presence nor the ability to build
a local wheel is an API-stability promise.

The bundle also includes two local documentation link targets,
[ADR 0006](adr/0006-interchange-and-durability-profiles.md) and the
[semantic model](architecture/semantic-model.md), as supporting context.

## Reproduce the bounded review

From either the verified review-bundle extraction or its exact source commit:

```bash
uv run --isolated --extra a0-review python -m pytest -q -p no:cacheprovider
uv run --isolated --extra a0-review ruff check .
```

The same source can be installed as a built, non-editable local package:

```bash
uv venv .venv
uv pip install --python .venv/bin/python '.[a0-review]'
.venv/bin/python -m pytest -q
```

Generate and inspect a fresh package without customer or downloaded data:

```bash
uv run --isolated --extra a0-review python tools/generate_review_fixture.py \
  /tmp/docsubstrate-a0-review
python3 -I tools/independent_reader.py /tmp/docsubstrate-a0-review
python3 -I tools/closure_report.py /tmp/docsubstrate-a0-review
```

The output directory must not already exist. `-I` prevents the independent
readers from importing the installed project or current working directory.

## Deterministic source-review artifact

From an exact clean commit, create one archive outside the repository:

```bash
python3 tools/build_a0_review_bundle.py /tmp/docsubstrate-a0-review.zip
```

The builder reads only its closed path/role allowlist, confirms every selected
file is byte-identical to clean `HEAD`, recomputes the internal Python import
closure, checks external imports, and rejects missing or unknown dependencies.
It writes an uncompressed ZIP with sorted members and fixed timestamps/modes;
no wall-clock timestamp enters the artifact. Repeating the build from identical
source bytes and commit produces identical archive bytes.

The generated canonical `A0-REVIEW-MANIFEST.json` records the full source commit,
scope/classification, Apache-2.0 license/copyright declaration, artifact path,
repository source path, file role, byte length, and SHA-256 for every other member.
The manifest deliberately cannot hash itself and records that exclusion. It is
an integrity inventory, not a signature or an attestation of publisher identity.
The bundled CLI accepts `--source-commit` only for a verified Git-less
extraction, validates the exact 40-hex value, and can reproduce byte-identical
archive bytes using the literal command in the
[README](../README.md). Omitting the option preserves clean-Git-HEAD mode.

After extracting into a new empty directory, use the bundled stdlib-only tool to
verify both the original archive and the extraction:

```bash
python3 -m zipfile -e /tmp/docsubstrate-a0-review.zip \
  /tmp/docsubstrate-a0-review-extracted
python3 /tmp/docsubstrate-a0-review-extracted/tools/verify_review_bundle.py \
  /tmp/docsubstrate-a0-review.zip
python3 /tmp/docsubstrate-a0-review-extracted/tools/verify_review_bundle.py \
  /tmp/docsubstrate-a0-review-extracted
```

The verifier rejects unknown or missing members, duplicate ZIP members,
non-canonical archive metadata, symlinks/non-regular files, path traversal,
forbidden repository/deployment/client/restricted path segments, forbidden
artifact/key/database/archive suffixes, and size or digest changes. The archive
contains no Git repository or history.

Run the complete bounded test set and synthetic independent-reader round trip
from the verified extraction using the commands in the
[README](../README.md). This archive is only a technical **source-review
artifact**. It is not a release, wheel, sdist, frozen API, frozen canonical JSON
wire, security attestation, or authorization decision.

## Code and data classification

### A0-PUBLIC-CANDIDATE

Only the allowlisted A0 files above, the A0-specific `pyproject.toml` and
`NOTICE`, root `LICENSE`, [SECURITY](../SECURITY.md), and their synthetic/public
tests are within this bounded review scope. Test identities such as
`object:synthetic-record` are placeholders. JWE RSA keys are generated for each
test run. Fixed cryptographic inputs are identified public RFC 7520 vectors.
Reserved/example identifiers and locators are synthetic test vocabulary, not
customer, machine, or production identifiers.

### REPOSITORY-PRIVATE / OUT OF A0

The following paths are present in the same private repository but are not A0
review evidence and are not cleared by this audit for external distribution:

- `.github/workflows/` operational and deployment automation;
- `integrations/` host and tool integrations;
- `benchmarks/` and proving-ground measurements;
- renderer, QWeb, daemon, and compatibility modules; and
- historical rendering ADRs and corpus-specific research notes.

An external reviewer receiving the entire repository would also receive these
paths. That requires separate authority even if the A0 allowlist itself passes.

### RESTRICTED / NEVER IMPLIED BY A0

Do not add customer/client records, production documents, raw private evidence,
credentials, private keys, access tokens, private identity mappings, deployment
values, internal hostnames/paths, account or tenant identifiers, or reversible
de-identification maps. Public availability also does not override copyright or
redistribution licensing.

## Dependency and license inventory

The manifest-bounded A0 artifact uses the repository's existing Apache-2.0
license with the non-exclusive attribution `Copyright 2026 DocSubstrate
contributors` in its `NOTICE`. This is not a relicensing. Project metadata names
Zen (Chen-Yu) Hsieh as the public maintainer/publisher; it does not claim that
the maintainer solely owns every contribution. The repository root remains
Apache-2.0, while the A0 allowlist and manifest define publication scope and do
not authorize disclosure of other repository content. The A0 runtime declares
no mandatory third-party dependency. Optional dependencies remain separated by
capability:

| Group | Declared dependency | Purpose | Metadata observed during audit |
| --- | --- | --- | --- |
| build | `hatchling>=1.25` | Wheel/sdist build backend | Hatchling 1.32.0, MIT |
| jwe | `cryptography>=42` | Optional JWE primitive provider | Cryptography 50.0.1, Apache-2.0 OR BSD-3-Clause |
| a0-review | `cryptography>=42`, `pytest>=8`, `ruff>=0.6`, `jwcrypto>=1.6` | Bounded A0 tests, lint, JWE, independent JOSE cross-check | Cryptography 50.0.1 Apache-2.0 OR BSD-3-Clause; pytest 9.1.1 MIT; Ruff 0.16.6 MIT; JWCrypto 1.6.0 LGPL-3.0-or-later |

Versions are an audit observation, not a lock. Lower-bound ranges can resolve
different future versions and licenses must be rechecked before a release.
JWCrypto is review/test-only and is not imported by the distributed A0 runtime.
The artifact uses A0-specific project metadata and exposes only `jwe` and
`a0-review` extras. Repository-only renderer/development extras are absent.

The manifest commit names source provenance but cannot prove that a private
commit is reachable or who produced the archive. Any future distributor should
publish the archive SHA-256 through a separately authenticated channel; a
detached signature is preferable when publisher identity matters.

## Publication hygiene and gate model

The current A0 allowlist and the source history audited before building it
contain no detected
high-signal credential material, restricted artifact files, non-synthetic
customer names or IDs, private host/path values, or non-synthetic test evidence.
This is a bounded pattern-and-review result, not a proof that the entire
repository is publishable.
The bundle contains neither Git history nor contributor-email metadata. That
omission does not erase copyright provenance. Line blame and the reachable
commit graph contain multiple Git author identities; Apache-2.0 already governs
their repository contributions, so the A0 artifact requires no license change.
The generic `DocSubstrate contributors` attribution avoids presenting the
maintainer as sole owner.

The existing private repository contains many non-A0 branches and surfaces and
must not simply be made public. This determines the safe publication mechanism;
it does not block fresh-history publication of a cleared A0 source artifact. A
new public repository must be initialized with fresh history from one exact,
verified A0 archive. Publishing it is a separate external mutation.

### Generic pre-publication gates

A specific A0 candidate may seed that fresh history only after:

1. an independent reviewer audits the exact artifact identified by its digest;
2. the publisher gives explicit authorization for that exact artifact and
   destination; and
3. the new repository is created from a verified extraction, with its resulting
   public tree checked against the authorized artifact.

These are gates applied to each candidate, not a claim that this document's
future build has already passed them.

### Disclosed limitations

The following do not prevent a caveated fresh-history source publication, but
they do prevent stable-release or production-security claims:

1. semantic direct-module APIs and the canonical JSON wire are not frozen;
2. JWE is provisional interoperable, without independent cryptographic security
   review or a broad negative/fuzz corpus;
3. dependencies are lower-bound ranges without a committed lock/SBOM;
4. public issue reporting is identified, but no authenticated private channel
   for sensitive vulnerability reports has been verified; and
5. local wheel/sdist builds are allowlist-membership checks and verification
   output, not package releases.

The private repository and all non-A0 branches, integrations, deployment paths,
and evidence remain outside the cleared source surface and must never be copied
into the fresh-history publication.
