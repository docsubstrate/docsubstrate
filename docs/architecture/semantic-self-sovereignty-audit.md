# DOCSUBSTRATE SELF-SOVEREIGNTY AUDIT

## Current architecture interpretation

The repository already separates source adapters, Representation, Artifact,
resources, durable dependency roles, canonical interchange, Occurrence, and
runtime projections. It is an application-neutral institutional document
substrate in formation, not only a renderer.

The baseline architecture had package-scoped resource closure but not an
entity-rooted survivability contract. Structural validity could therefore be
mistaken for semantic sufficiency.

## Existing primitives that satisfy the axiom

- `PackageObject` owns stable institutional identity and vocabulary-defined type.
- `PackageRepresentation` separates expression identity/version/schema/content
  references from Object identity.
- `PackageArtifact` binds material fixity to an exact Representation.
- `OccurrenceRecord` owns the correlated basis-qualified occurrence fact bundle.
- `ResourceDescriptor` separates resource identity, materialization, and fixity.
- Preservation closure roles distinguish interpretation, evidence, verification,
  reproduction, and context.
- Metadata basis distinguishes asserted, observed, derived, and inferred values.
- State is explicitly rejected as a generic durable primitive.

## Entities with hidden external dependencies

Baseline counterexamples:

- a PreservationClaim containing only resource requirements could report full
  kill readiness with no entity whose survivability was being claimed;
- Relation had no identity and could not own metadata, basis, time, or provenance;
- Relation endpoints were restricted to locally packaged Objects, forcing graph
  copying or failure when a legitimate external target was unavailable;
- Occurrences were serialized outside the package-owned structural graph;
- Metadata assertion subjects and source references were not structurally checked;
- Representation could omit vocabulary, version, and all content resources;
- vocabulary version and preserved definition were optional.

## Identity gaps

Relation identity was missing. External source/IdP/application identifiers remain
bindings, not institutional identity. The package now detects identity reuse in
the strong profile and provides declared external reference stubs.

## Vocabulary/version gaps

The permissive profile allows unversioned or unpreserved vocabularies. The strong
profile now rejects a used vocabulary without both a version and a fixity-bearing
preserved resource. A future standards profile may permit another independently
verifiable preservation strategy.

## Relation ownership gaps

Baseline Relation was an anonymous binary edge. It now has `relation_id`, may be
a metadata subject, and may relate any declared entity identity or explicit
external stub. N-ary participant-role syntax remains unproven and is not added.

## Artifact survivability gaps

The package already verifies that an Artifact references a material, fixity-
bearing resource and an existing Representation. A bare PDF outside its companion
package still cannot prove Expression correspondence. PDF Associated Files or an
equivalent inseparable/archived companion profile remains necessary.

## Authority/provenance gaps

Occurrence and Metadata basis are explicit, but no universal Authority or
Evidence primitive is justified. Authority, delegation, credentials, and source
basis remain vocabulary-defined entities/Relations/resources. The strong profile
rejects asserted Occurrences without source basis and observed Occurrences without
an observing actor.

## Counterexamples

1. Resource-only closure falsely reporting kill readiness.
2. Anonymous Relation whose institutional meaning cannot be independently cited.
3. External relation target disappearance invalidating an otherwise intact local entity.
4. Occurrence references to undeclared application/runtime identities.
5. Unversioned vocabulary allowing later semantic drift.
6. Representation with identity but no preserved content.
7. Bare Artifact whose source Expression is knowable only through its renderer/database.
8. IdP subject or ERP row identifier used as the only durable party identity.
9. Application status used as the only carrier of an institutional consequence.
10. Derived/inferred metadata preserved without its producer or source basis.

## Possible generic gaps

Confirmed gaps in the baseline were entity-rooted claims, Relation identity,
declared external identity stubs, and package-owned Occurrence validation. These
received minimal changes.

The baseline could not describe one Expression as parallel public and protected
semantic components while rotating access recipients independently. This is now
represented without defining a cryptographic algorithm: Representations compose
components; every component declares a clear/encrypted posture; encrypted leaves
bind to a protection descriptor and one or more independent key envelopes.
Authority credentials and identity bindings remain standards-composition
candidates rather than new institutional primitives.

## What can remain in domain packages

- invoice, order, contract, medical, QMS, and workflow vocabulary;
- approval, acceptance, issue, delegation, evidence, and authority predicates;
- operational status projection policy;
- host-system roles, record rules, and authorization objects;
- protected component classifications and disclosure policy;
- permissible commands, invariants, and workflow definition semantics.

## Minimal proposed generic changes

Implemented:

- stable `relation_id`;
- `ExternalReference` identity/type stub;
- package-owned Occurrences with reference validation;
- PreservationClaim entity roots;
- ClosureRequirement entity owner;
- Relation metadata subject kind;
- strong, separate minimum-survivable-closure validator;
- entity-aware independent reader and closure report.
- explicit parallel Representation components and protection posture;
- external-profile protection descriptors that bind ciphertext to one component;
- independently versioned, multi-recipient key envelopes separated from
  Expression semantics and authority truth.

Not implemented:

- generic State, Authority, Evidence, Grant, Identity, Workflow, or
  ProtectedMetadata domain primitive;
- custom cryptographic algorithms;
- graph replication;
- a new universal ontology.

## Tests proposed

Implemented executable tests:

1. Detached Entity Test
2. Kill Runtime Test
3. Kill Database Test
4. Broken Reference Test
5. Vocabulary Survival Test
6. Artifact Correspondence Test
7. No Hidden Status Test
8. Independent Reader Test
9. Minimality Test
10. Composition Test

An additional regression test rejects resource-only claims as entity survivability.
Protected-component tests additionally require flat encrypted leaves, ciphertext
fixity, at least one declared access/recovery path, multiple parallel envelopes,
no Expression semantic-projection change when an envelope changes, and
byte-identical AAD binding reconstruction by the stdlib-only independent reader.
For the strict JWE profile, changing the recipient/envelope set still requires a
new JWE container, CEK, ciphertext bytes, and fixity record.

## Files likely affected

- `src/docsubstrate/package.py`
- `src/docsubstrate/durable.py`
- `src/docsubstrate/occurrence.py`
- `src/docsubstrate/interchange_json.py`
- `src/docsubstrate/self_sovereignty.py`
- `src/docsubstrate/migration.py`
- `tools/independent_reader.py`
- `tools/closure_report.py`
- package/interchange/migration/closure tests
- README and architecture/ADR documentation

## Implementation recommendation

Keep permissive structural interchange separate from the strong survivability
profile. The independent reader can now reconstruct the logical AAD binding
without importing DocSubstrate. The provisional interoperable JWE General JSON
profile consumes that binding in a synthetic multi-recipient physical round
trip and fails closed when Object, Expression, or component identity context changes.
The profile has now passed bidirectional JWCrypto interoperability and the
applicable RFC 7520 `A256GCM` and external-AAD vectors, supporting that status.
A stable or production claim still requires a broader negative/fuzz corpus and
independent security review. Separately test
whether RO-Crate/JSON-LD can replace or profile the current logical wire and
whether PDF Associated Files can carry the exact companion manifest. Keep key
release and runtime authorization outside core; preserve their institutional
basis as Relations, credentials, and Occurrences rather than treating a
successful unwrap as authority.

## PASS / PARTIAL / FAIL

**Baseline: PARTIAL.**

**After the minimal changes: PASS for the structural minimum-survivable-closure
candidate profile; PARTIAL for cryptographic execution, authority, and long-term
vocabulary-standard integration.** These remain explicit proving
grounds, not hidden success claims.

## GENERIC GAP: protected semantic component composition

Current example: an ERP invoice has public identity metadata, confidential
commercial terms, accounting details, PII, and audit material with different
recipient and recovery requirements.

What cannot be represented: one stable Expression composed from independently
protected semantic parts whose access envelopes may change without changing the
Expression version.

Why substrate-generic: the same separation occurs in commercial, medical,
government, legal, HR, and regulated archive documents; only component
vocabularies and access policies vary.

Why vocabulary/policy/adapter cannot solve it: vocabulary can classify a
component and policy can decide release, but neither gives an independent reader
a structural binding from Expression/component identity to ciphertext and its
replaceable access paths. Adapter-only conventions recreate hidden runtime truth.

Minimal proposed generic change: `component_ids`, explicit `protection_mode`,
`ProtectionDescriptor`, and independently versioned `KeyEnvelope` records. The
core names external cryptographic profiles and never stores a plaintext content
key or interprets an envelope as authority.

## GENERIC GAP: entity-rooted preservation claims

Current example: a package with one fixity-bearing vocabulary resource and no
Object, Expression, Relation, Occurrence, or Artifact reported kill readiness.

What cannot be represented: which durable entity owns the closure claim and
which entity owns each dependency.

Why substrate-generic: every domain must distinguish package resources from the
institutional entity whose survival is claimed.

Why vocabulary/policy/adapter cannot solve it: an adapter-only convention would
be invisible to an independent reader and recreate the hidden dependency.

Minimal proposed generic change: `PreservationClaim.root_refs` and
`ClosureRequirement.subject_ref`.

## GENERIC GAP: first-class Relation ownership

Current example: an anonymous `source/predicate/target` edge cannot be cited as
the subject of provenance, authority basis, time, evidence, or integrity claims.

What cannot be represented: the continuing identity of the institutional
relationship itself.

Why substrate-generic: contracts, delegation, correspondence, supersession, and
source bindings all require relations that own their own meaning.

Why vocabulary/policy/adapter cannot solve it: a vocabulary defines the
predicate but cannot assign identity to a particular relation instance.

Minimal proposed generic change: required `relation_id`; metadata may target it.

## GENERIC GAP: explicit unresolved external references

Current example: a missing purchase-order target made an invoice relation
structurally invalid unless the target entity was copied into the package.

What cannot be represented: an explicit durable target identity/type whose full
entity is intentionally unavailable.

Why substrate-generic: broken references occur across every deployment and
institutional boundary.

Why vocabulary/policy/adapter cannot solve it: silently accepting arbitrary
unknown strings hides typos and unresolved application IDs; forcing adapters to
materialize targets creates total-closure pressure.

Minimal proposed generic change: `ExternalReference` identity/type stub accepted
as a relation or occurrence endpoint without claiming ownership of its closure.
