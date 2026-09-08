# Interchange, dependency closure, and durable institutional records

## One-line boundary

AFP preserves reliable presentation across devices; DocSubstrate preserves reliable institutional meaning across systems.

The architectural lesson is therefore about separation of concerns, not about copying a presentation stream.

## Invariants first

The portable representation model is derived from these invariants:

1. **Core knows structure, not domain meaning.** Domain semantics are declared vocabularies, not kernel classes.
2. **Durable meaning must not depend on executable DocSubstrate implementation.** Killing the source application, database, Python code, and DocSubstrate implementation must not destroy the meaning claimed to be preserved.
3. **Self-describing does not imply always physically self-contained.** General interchange may resolve declared external dependencies.
4. **Durable preservation requires dependency closure.** A preservation boundary is valid only when all dependencies critical to its declared claim are captured or durably resolvable without the killed systems.
5. **Material identity is distinct from semantic identity.** Exact bytes and their integrity remain meaningful even when two artifacts express equivalent semantics.
6. **Unknown semantics must remain unknown.** Readers may preserve opaque future objects but must not silently reinterpret them.
7. **Evidence placement follows query ownership.** Evidence belongs where the assertion/query that needs it can identify and validate it; packaging must not force a false ownership hierarchy.
8. **The core should shrink as understanding improves.** New domain requirements first test vocabularies, relations, and capabilities before becoming core primitives.

## Representation stack

```text
DocSubstrate Core
    identity
    entity/object envelope
    typed relation
    representation envelope
    dependency envelope
    artifact identity/integrity
        |
        v
Interchange Profile
    mandatory constructs
    validation rules
    writer/reader compliance
        |
        v
Optional Capability Sets
    signatures
    cryptographic timestamps
    bitemporal relations
    external resolution
    physical provenance
    content addressing
        |
        v
Domain Vocabularies
    ERP commerce
    legal
    QMS
    clinical
```

A profile constrains the architecture. A capability extends mechanisms. A vocabulary supplies domain meaning. None should be confused with the core.

## Artifact, Representation, and Semantic State

These concepts have different identity semantics and should not be collapsed.

### Semantic State

An institutional assertion or state of meaning: what is claimed, observed, agreed, ordered, measured, accepted, or otherwise institutionally represented.

Its identity is semantic/institutional, not byte identity.

### Representation

A typed expression of semantic state. It declares enough information to identify what kind of representation it is and what is required to interpret it.

Candidate envelope fields, not yet a wire schema:

```text
Representation
    id
    media/type classification
    semantic/vocabulary type
    vocabulary identifier/version
    schema identifier/version
    encoding
    dependencies[]
    relations[]
    materialization -> Artifact | external locator
```

A representation may be PDF, XML, JSON, CDA, FHIR, DICOM, an image, a signed document, a vendor-specific payload, or an unknown future format. Core conformance does not imply understanding the payload.

### Artifact

A materialized object with exact material identity and integrity semantics.

Candidate properties:

```text
Artifact
    id
    media_type
    digest algorithm + digest
    byte length
    encoding/container metadata
    materialization location or package membership
```

Artifact remains first-class because material identity cannot be reduced to representation identity. Two byte-distinct signed PDFs may express equivalent semantics while remaining distinct evidence.

## Dependency is broader than resource

Presentation architectures often resolve fonts, images, overlays, or reusable objects as resources. Institutional records also depend on vocabularies, authorities, evidence, certificates, standards, prior records, and external medical images.

DocSubstrate therefore models the general concept as a typed dependency.

Candidate dependency roles:

- **interpretation** — required to determine the declared meaning
- **evidentiary** — required to substantiate an assertion
- **verification** — required to verify integrity, signature, authority, or timestamp
- **reproduction** — required to reproduce a material/presentation result
- **contextual** — useful context whose absence does not invalidate the preservation claim

A dependency should declare at least its role, target identity, resolution policy, integrity expectation where applicable, and durability requirement under the selected profile.

## General Interchange Profile

General interchange optimizes interoperability during live operation. It MAY use external dependencies when resolution is explicit.

An external reference is acceptable only if the package can state:

- what the target is expected to be;
- why it is needed;
- how it is identified;
- how it is resolved;
- whether integrity is expected and how it is checked;
- what failure to resolve means.

A mutable URL without stable identity is not equivalent to a content-addressed reference. A database primary key meaningful only inside a dead application is not a portable identity.

## Durable Institutional Profile

Durable interchange is a constrained profile of the same architecture, not a separate document model.

The durable boundary is evaluated against a **preservation claim**. Example:

```text
Preserve the institutional meaning, source evidence, and verifiability
of record X as it stood at time T.
```

The validator walks dependencies reachable from the preserved roots and classifies whether closure is satisfied for the claim.

Candidate closure dimensions:

```text
interpretation closure
    Can an independent reader determine the declared institutional meaning?

evidence closure
    Can the preserved assertions still reach the evidence the claim requires?

verification closure
    Can integrity/authority/signature claims be evaluated with preserved material?

reproduction closure
    Can exact or declared-equivalent presentation be reproduced where the claim requires it?
```

A durable profile does not necessarily require reproduction closure when preservation of visual reproduction was never claimed. Conversely, a signed or legally fixed-form document may require both semantic and material preservation.

### Capture policy

The rule is not "important things embed". For every dependency ask:

1. Does absence change institutional meaning?
2. Does absence break evidence for a preserved assertion?
3. Does absence break verification?
4. Does absence break a required reproduction guarantee?
5. Is the target mutable?
6. Is it content-addressable or otherwise stably identifiable?
7. Is availability guaranteed independently of the killed systems?
8. Can it legally be copied or embedded?
9. Is its size/material nature incompatible with physical embedding?

A critical dependency MUST be captured into the preservation boundary or replaced by a durable resolution mechanism whose continued availability is itself part of the preservation contract. No critical dependency may resolve only through the killed application/runtime.

Legal/licensing constraints may prevent embedding an external standard. In that case the package must preserve the stable identifier, vocabulary/schema declaration, required interpretation boundary, and an explicit unresolved/external status; a profile cannot falsely claim closure it does not possess.

## Writer compliance

A writer conforming to profile P MUST:

- declare profile identifier and version;
- declare every capability set used;
- declare every vocabulary/schema needed to interpret emitted semantics;
- emit only constructs legal under P;
- emit no undeclared extension semantics;
- provide stable identity for externally resolved critical targets;
- satisfy P's dependency rules;
- preserve material digest/integrity metadata when material identity is asserted.

A writer may implement only a subset of optional capabilities. It may not claim a profile whose mandatory output rules it cannot satisfy.

## Reader compliance

A reader claiming profile P MUST:

- understand every mandatory core/profile construct;
- validate the declared profile/version;
- identify unsupported optional capabilities and vocabularies;
- never silently reinterpret an unknown type as a known one;
- expose opaque representations when payload semantics are unsupported;
- preserve unknown optional envelopes when it offers read-modify-write/round-trip behavior;
- distinguish "valid but unsupported" from "invalid";
- distinguish "reference unresolved" from "target absent by design".

This gives useful backward operation: a 2027 reader encountering a 2035 optional object can retain and relay it without pretending to understand it.

## Extension and versioning model

Evolution should prefer this order:

1. new vocabulary term;
2. new optional capability;
3. new profile version/rule;
4. core change only when a new invariant cannot be represented by the existing algebra.

A core version change must be rarer than vocabulary or capability evolution.

Capabilities must have stable identifiers and versions. Profiles declare mandatory/allowed capability behavior. Vocabularies are independently versioned and must not imply executable code.

## Why this is not MO:DCA for semantics

DocSubstrate does **not** adopt an ordered structured-field hierarchy as the canonical semantic model. Institutional semantics are graph-shaped and must not be forced into Begin/End containment.

Likewise, a resource group is not authoritative ownership. Content-addressed objects and typed graph relations may be shared by many records without being copied into a false containment tree.

The patterns worth borrowing are:

- portable representation separated from execution;
- stable typed envelopes;
- embedded and referenced dependency resolution;
- unknown-object carriage;
- interoperability profiles;
- distinct writer and reader obligations;
- stricter archival constraints layered on the general architecture.

## Existing standards before new serialization

DocSubstrate should invent semantics only where existing standards fail these invariants. Candidate standards to evaluate before defining a wire format include JSON-LD/RDF for graph representation, PROV for provenance concepts, BagIt/OCFL for preservation packaging, and RO-Crate for graph-plus-artifact packaging.

The value of DocSubstrate may lie primarily in institutional invariants, dependency closure, identity/correspondence, profile contracts, and semantic/physical provenance rather than in a novel serializer.

## Candidate package projection — deliberately non-normative

Only after the invariants above are satisfied might a portable package project roughly as:

```text
Package
    manifest / profile declarations
    roots / preservation claims
    entities
    relations
    representations
    artifacts
    dependencies
    vocabulary declarations
    capability declarations
    integrity/provenance material
```

This is a projection for discussion, not a canonical containment hierarchy and not yet a schema.
