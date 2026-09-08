# Architecture

## Goal

DocSubstrate is a host-neutral institutional document substrate.

Its core requirement is:

> Preserve the correspondence between institutional meaning, document representations, material artifacts, and system state without making any source application, renderer, storage system, or executable DocSubstrate implementation the owner of that meaning.

Source applications are proving grounds, not part of the core domain model.
Renderers, document formats, databases, and future agent runtimes are
representations, adapters, or execution mechanisms—not substrate identity.

## A0 review boundary

A0 is the generic semantic/package kernel and its independent verification
surface. It owns identity, typed relations, expressions, occurrences, artifacts,
resources, dependency closure, and protected-component ownership. Domain
vocabularies, operational state projections, authorization decisions, source
adapters, renderers, storage, deployments, and workflow engines remain outside
that boundary.

The [A0 external-review guide](a0-review-guide.md) gives the exact source
allowlist, primitive/query-owner map, clean verification commands, data
classification, dependency inventory, publication gates, and disclosed
limitations.

## Architectural center

```text
Institutional meaning
        |
        v
identity + typed graph relations
        |
        +---- semantic representations
        +---- structural representations
        +---- physical representations
        +---- material artifacts
        +---- dependencies / provenance
        |
        v
profiles + capabilities + vocabularies
        |
        v
adapters / resolvers / renderers / agents
```

The dimensions coexist. Rendering is not the canonical lifecycle of a document and generated PDF bytes are not the terminal form of the model.

## Core boundaries

1. **Core knows structure, not domain meaning.** Commerce, legal, QMS, and clinical semantics belong in declared vocabularies.
2. **Portable representation is separate from execution.** A renderer or runtime may die without invalidating the representation it executed.
3. **Material identity is distinct from semantic identity.** Exact artifacts remain addressable and verifiable independently of equivalent semantic representations.
4. **Documents and institutional records form graphs, not canonical folder trees.** Folder/case/customer/timeline views are projections.
5. **Unknown semantics are never silently reinterpreted.** Opaque preservation is preferable to false understanding.
6. **The core should shrink as understanding improves.** New domain pressure first tests typed relations, profiles, capabilities, and vocabularies before adding primitives.

## Interchange and durability

Runtime interchange and durable preservation intentionally have different constraints.

```text
DocSubstrate Core
        |
        +-- General Interchange Profile
        |       external resolution may be allowed
        |
        +-- Durable Institutional Profile
                critical dependency closure required
```

Durability is not synonymous with physically embedding every referenced byte. It means that dependencies required by the declared preservation claim are closed or durably resolvable without the executable systems being retired.

See [Interchange, dependency closure, and durable institutional records](architecture/interchange-profiles.md) and [ADR 0006](adr/0006-interchange-and-durability-profiles.md).

## Model references

- [A0 external-review guide](a0-review-guide.md)
- [Multidimensional semantic/structural model](architecture/semantic-model.md)
- [Interchange and durable profiles](architecture/interchange-profiles.md)
- [Core primitive audit](architecture/core-primitive-audit.md)
