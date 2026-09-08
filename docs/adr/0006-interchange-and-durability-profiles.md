# ADR 0006: Separate interchange from durable preservation

Status: Proposed

## Context

DocSubstrate must carry institutional meaning across implementations without making every runtime representation an archival package. Runtime systems benefit from external resolution, shared resources, mutable services, and domain-specific capabilities. Long-term preservation has the opposite requirement: critical interpretation and verification dependencies must survive the systems that created the record.

AFP/MO:DCA and AFP/A provide a useful architectural precedent: a general architecture can permit resource resolution and extensibility while a stricter archival profile constrains the same architecture for durable reproduction. DocSubstrate adopts the decomposition, not AFP's presentation hierarchy or binary serialization.

## Decision

DocSubstrate separates four compatibility layers:

1. **Core** defines host-neutral identity, typed relations, representation/dependency envelopes, and material identity/integrity.
2. **Interchange profiles** define mandatory constructs and interoperability contracts for writers and readers.
3. **Capability sets** define optional mechanisms such as signatures, cryptographic timestamps, bitemporal relations, external resolution, or physical provenance.
4. **Domain vocabularies** define institutional meaning such as commerce, legal, QMS, or clinical semantics.

At least two profile classes are expected:

- **General Interchange** may contain externally resolvable dependencies when their identity, role, integrity expectations, and resolution requirements are explicit.
- **Durable Institutional** requires dependency closure for the declared preservation claim. No critical dependency may remain resolvable only through the executable application, database, vendor service, or DocSubstrate implementation that created the package.

Durability is therefore not defined as "all bytes are embedded". It is defined as **closure of the dependencies required to preserve the declared institutional claim**.

## Preservation invariant

A durable institutional record must preserve enough explicit structure, semantics, evidence, and verification material that its declared institutional meaning can survive the executable systems that created it.

More precisely:

> Durability requires closure of interpretation and verification dependencies at the preservation boundary, not independence of every semantic object.

The graph may remain a graph. Closure does not require flattening relations or duplicating every referenced object into every node.

## Writer and reader compliance

A conforming writer MUST declare the profile/version, used capability sets, and used vocabularies. It MUST NOT emit undeclared semantics or dependencies that violate the selected profile.

A reader claiming a profile MUST understand all mandatory constructs of that profile. It MUST identify unsupported optional capabilities or vocabularies, MUST NOT silently reinterpret unknown semantics, and SHOULD preserve unknown optional envelopes opaquely when round-trip behavior is offered.

Unknown-as-opaque is valid. Unknown-as-something-else is not.

## Consequences

- Archival restrictions do not pollute ordinary runtime use.
- The core does not grow every time a domain adds a capability.
- Forward-compatible readers can preserve future objects they cannot interpret.
- A durable-package validator can compute dependency closure instead of relying on a boolean `archive=true` flag.
- Serialization remains a separate decision; this ADR does not create a DocSubstrate binary format.

## Non-decisions

This ADR does not yet choose JSON-LD, RDF, PROV, BagIt, RO-Crate, OCFL, or another serialization/packaging standard. Existing standards should be reused wherever they satisfy the invariants.

It also does not promote `Evidence`, `Authority`, `Agent`, or `Occurrence` to irreducible core primitives. Those concepts must first be tested against the smaller entity/relation/capability model.
