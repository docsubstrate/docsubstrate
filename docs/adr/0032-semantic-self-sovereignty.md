# ADR 0032: Semantic self-sovereignty and entity-rooted closure

## Status

Accepted as the highest generic design axiom.

## Axiom

> Responsibility is pushed to the point of semantic self-definition.

A durable institutional entity must carry or explicitly close over the minimum
information required to identify, interpret, verify, and continue itself after
the source application, database, ORM, workflow runtime, UI, and undocumented
conventions disappear.

This is **minimum survivable closure**, not total closure. Related entities may
remain outside the package. Their absence must not erase the local entity's own
identity or basic institutional meaning.

## Ownership

- Object owns continuing institutional identity.
- Representation/Expression owns the content it expresses and its version.
- Occurrence owns the basis-qualified fact bundle of what happened.
- Relation owns its identity and vocabulary-defined institutional connection.
- Artifact owns material identity, fixity, and correspondence to an Expression.
- Projection owns no durable truth.
- Source bindings, runtimes, databases, renderers, IdPs, and workflow engines
  remain replaceable harnesses.

## Standards posture

DocSubstrate does not replace JSON-LD/RDF, PROV, RO-Crate, BagIt, OCFL, PDF,
JWS/COSE, JWE/HPKE, OIDC, DID/VC, UBL, FHIR, or domain vocabularies. It adopts,
profiles, or composes them wherever they already own the mechanism.

The irreducible DocSubstrate contract is responsibility allocation:

- which entity owns each durable truth;
- which dependencies form its declared closure;
- which references may remain external;
- which facts are asserted, observed, derived, or inferred;
- which runtime projections must not be mistaken for institutional truth;
- which failure must be reported rather than repaired by hidden lookup.

## Minimal model changes

1. `PackageRelation` receives a stable `relation_id`.
2. `ExternalReference` declares an external identity/type stub without copying
   the external entity or making a locator its identity.
3. `OccurrenceRecord` becomes package-owned while the top-level occurrence
   collection remains readable; the canonical JSON experiment advances to 0.2.
4. `PreservationClaim.root_refs` identifies the entities whose survivability is
   claimed.
5. `ClosureRequirement.subject_ref` identifies which entity owns a dependency.
6. `validate_minimum_survivable_closure` applies the strong profile separately
   from permissive structural validation.
7. Metadata may target a first-class Relation and its basis is validated by the
   strong profile.

No generic State, ERP event, workflow event, Authority, Evidence, protected
metadata, or identity-provider primitive is introduced by this ADR.

## Consequences

A resource-only package can still be structurally valid, but it cannot claim
entity survivability without entity roots and dependency ownership. A broken
external target can remain explicit and unavailable while the local entity
continues to pass its own closure test.

Operational status remains a projection over Occurrences, Relations, temporal
context, and policy. Content-bearing snapshots remain Expressions.

## Re-open criteria

Re-open an individual primitive decision only when a cross-domain counterexample
cannot be represented through existing primitives, a versioned vocabulary or
profile, a standards adapter, or an opaque critical extension without creating
a hidden semantic dependency.
