# DocSubstrate

DocSubstrate A0 is a generic, application-neutral substrate for preserving the
identity, meaning, provenance, fixity, and declared dependency closure of
institutional documents and records.

Status: research/reference implementation. The semantic model and reference
wire are not a stable public API or frozen standard.

## Thesis

> Responsibility is pushed to the point of semantic self-definition.

An institutional entity should remain identifiable and interpretable after its
source application, database, workflow runtime, renderer, and DocSubstrate
implementation disappear. It therefore owns or explicitly closes over its
minimum sufficient identity, expression, temporal/basis context, provenance,
integrity, and critical dependencies. This is **minimum survivable closure**,
not a copy of the entire source graph.

DocSubstrate adopts existing standards for cryptography, packaging, provenance,
identity, and domain semantics. Its generic contribution is the allocation of
durable responsibility and executable conformance tests for their composition.

## A0 architectural center

The current minimal center is:

- stable Identity and Object envelopes;
- typed Relations;
- Representation/Expression envelopes;
- first-class query ownership for Artifacts and Occurrences;
- Resources, preservation claims, and explicit dependency closure; and
- flat protected semantic components with independently replaceable key
  envelopes.

Operational `State` is deliberately not a generic primitive. It is normally a
projection over expressions, occurrences, relations, policy, vocabulary, and
time. A key envelope is likewise not an authorization or authority claim.

Start with [Architecture](docs/architecture.md), then use the
[A0 external-review guide](docs/a0-review-guide.md) for the exact review surface,
primitive map, verification commands, data classification, publication gates,
and disclosed limitations.

## A0 boundary and non-goals

A0 owns the generic semantic/package contracts and their independent
verification. It does not own:

- commerce, legal, clinical, ERP, or other domain vocabularies;
- source-system models, workflow topology, UI state, or database identifiers;
- institutional authorization, key-release policy, or identity-provider truth;
- storage, deployment, renderer, or integration operations; or
- new cryptographic algorithms.

The RFC 7516/7518 JWE adapter is **provisional interoperable**, not stable or a
production-security claim. The canonical JSON and reference directory are
executable reference profiles, not frozen wire standards.

The development repository also contains non-A0 work. Do not treat a repository
checkout as the approved external-review or publication surface; the review
bundle is a deliberately smaller source artifact.

## Clean verification

Requirements: Python 3.11 or newer. The primary commands use
[uv](https://docs.astral.sh/uv/) to create an isolated environment without
depending on an existing project virtualenv.

```bash
uv run --isolated --extra a0-review python -m pytest -q -p no:cacheprovider
uv run --isolated --extra a0-review ruff check .
```

For an explicit local environment instead:

```bash
uv venv .venv
uv pip install --python .venv/bin/python '.[a0-review]'
.venv/bin/python -m pytest -q
```

The entire manifest-bounded extraction must pass `ruff check .`; there is no
legacy-lint exception inside a fresh-history public candidate.

## Independent-reader round trip

Choose an output directory that does not already exist. The generator refuses
to overwrite one.

```bash
uv run --isolated --extra a0-review python tools/generate_review_fixture.py \
  /tmp/docsubstrate-a0-review
python3 -I tools/independent_reader.py /tmp/docsubstrate-a0-review
python3 -I tools/closure_report.py /tmp/docsubstrate-a0-review
```

The generator uses DocSubstrate to write a package containing only fixed
synthetic text. The two readers use only the Python standard library and can be
run with isolated imports. They verify the resulting graph, payload fixity, and
minimum survivable closure without importing `docsubstrate`.

## A0-only source review bundle

The local builder creates one deterministic, allowlist-only ZIP from the exact
clean `HEAD`. The destination must be outside this repository and must not
already exist.

```bash
python3 tools/build_a0_review_bundle.py /tmp/docsubstrate-a0-review.zip
mkdir /tmp/docsubstrate-a0-review-extracted
python3 -m zipfile -e /tmp/docsubstrate-a0-review.zip \
  /tmp/docsubstrate-a0-review-extracted
python3 /tmp/docsubstrate-a0-review-extracted/tools/verify_review_bundle.py \
  /tmp/docsubstrate-a0-review.zip
python3 /tmp/docsubstrate-a0-review-extracted/tools/verify_review_bundle.py \
  /tmp/docsubstrate-a0-review-extracted
```

From inside the verified Git-less extraction, reproduce the exact archive using
the source commit recorded in its manifest:

```bash
cd /tmp/docsubstrate-a0-review-extracted
python3 tools/build_a0_review_bundle.py --source-commit \
  "$(python3 -c 'import json; print(json.load(open("A0-REVIEW-MANIFEST.json"))["source"]["commit"])')" \
  /tmp/docsubstrate-a0-review-rebuilt.zip
cmp /tmp/docsubstrate-a0-review.zip /tmp/docsubstrate-a0-review-rebuilt.zip
```

Without `--source-commit`, the CLI retains its stricter repository mode and
requires a clean Git `HEAD`. The extraction mode validates an exact lowercase
40-hex commit and does not claim that the private commit is publicly reachable.

The verifier uses only the Python standard library. From the verified
extraction, reviewers can run the bounded tests and independent-reader example:

```bash
cd /tmp/docsubstrate-a0-review-extracted
PYTHONDONTWRITEBYTECODE=1 uv run --isolated --extra a0-review \
  python -m pytest -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 uv run --isolated --extra a0-review \
  python tools/generate_review_fixture.py /tmp/docsubstrate-a0-review-fixture
python3 -I tools/independent_reader.py /tmp/docsubstrate-a0-review-fixture
python3 -I tools/closure_report.py /tmp/docsubstrate-a0-review-fixture
```

This is a source-review artifact. It is not a release, wheel, sdist, frozen API,
or frozen wire profile. Its SHA-256 manifest checks content against the manifest;
it is not a signature or publisher-identity attestation. An eventual publisher
must distribute the archive digest through a separately authenticated channel
(preferably with a detached signature). See the
[A0 external-review guide](docs/a0-review-guide.md) for its exact contents and
limits.

## Review-bundle map

```text
src/docsubstrate/       A0 modules plus a no-re-export package initializer
tools/                  Independent readers and synthetic review-fixture tool
tests/                  Synthetic/public test evidence
docs/                   Bounded architecture and review decisions
```

## License

The manifest-bounded A0 review artifact is offered under Apache License 2.0;
see [LICENSE](LICENSE) and its A0-specific `NOTICE`. DocSubstrate is maintained
by Zen (Chen-Yu) Hsieh and sponsored by Digiter; the non-exclusive copyright
attribution remains “DocSubstrate contributors.” This does not extend the A0
publication scope to non-allowlisted source. Optional and review-only
dependencies retain their own licenses; provenance, publication gates, and
disclosed limitations are recorded in the A0 review guide. See
[SECURITY.md](SECURITY.md) for the public issue and not-yet-enabled
sensitive-reporting boundaries.
