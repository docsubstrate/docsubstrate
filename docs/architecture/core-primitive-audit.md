# Core primitive / first-class / query-owner audit

This note applies two rules:

1. **the DocSubstrate core should get smaller as understanding improves**;
2. **algebraic reducibility does not automatically imply architectural disposability**.

A concept may be expressible as entities and relations yet still deserve a stable first-class binding because integrity, indexing, preservation, or intrinsic queries need a canonical owner.

This is a living audit. Accepted ADRs supersede earlier candidate language.

## Three categories

### A. Irreducible primitive

A primitive belongs in the algebra only when representing it entirely through other constructs loses an invariant that the substrate itself must preserve.

### B. First-class concept / query owner

A first-class concept may be algebraically reducible, but receives a stable envelope or contract because it owns important cross-domain queries, integrity rules, lifecycle semantics, or preservation behavior.

### C. Vocabulary / capability / derived view

A concept stays outside the kernel when it can be represented losslessly by typed entities, relations, occurrences, representations, artifacts, profile rules, or domain vocabularies.

## Promotion tests

A candidate is an irreducible core primitive only when all are true:

1. it is required across unrelated institutional domains;
2. representing it only with existing primitives loses an invariant the core must enforce;
3. the invariant survives host applications and executable implementations;
4. it is not more naturally a profile rule, capability, vocabulary term, or derived graph view;
5. making it primitive reduces ambiguity more than it increases ontology surface.

Even if algebraically reducible, a concept may deserve first-class binding when one or more are true:

- it intrinsically owns common substrate-level queries;
- it has independent identity or integrity semantics;
- it is a natural preservation or migration boundary;
- it requires canonical indexing across vocabularies;
- independent readers must agree on its existence even if they disagree on domain interpretation.

## Current audit

| Candidate | Current decision | Reason |
| --- | --- | --- |
| Identity | Irreducible primitive | Cross-domain correspondence, references, versioning, and preservation require identity independent of host primary keys. |
| Entity/Object envelope | Irreducible primitive | The graph needs addressable typed subjects/objects while domain classes remain external vocabularies. |
| Typed Relation | Irreducible primitive | Institutional meaning is graph-shaped; relation cannot be reduced to containment or representation. |
| Representation / Expression | Irreducible envelope | The same institutional object can have multiple content-bearing expressions independently of their material bytes. Semantic snapshots belong here, not in `State`. |
| Artifact | First-class, kernel-stable direction | Exact bytes, digest, size, material identity, and evidentiary/reproduction use require a canonical query/integrity owner. |
| Occurrence | **Promoted first-class query owner** | Capture/preservation, legal corpus, and artifact validation independently require actor/time/input/output/outcome/source-basis queries. Collapsing this into Relation + Metadata requires inventing an event node under another name. |
| Dependency | Relation/profile semantics | Closure roles and resolution/integrity expectations are currently expressible without a separate universal object. |
| State / SemanticState | **Rejected as core primitive/query owner** | Operational status is a projection over Occurrences + Relations + temporal/policy context. Content-bearing snapshots are Representations / Expressions. |
| Evidence | Query surface via relations, not primitive | `What supports assertion X?` is intrinsic, but the answer can be artifacts, representations, occurrences, assertions, or resources linked by typed support/basis relations. |
| Authority | Vocabulary/capability + relations | Authority is expressed through grants, roles, delegations, credentials, policies, actor scope, and temporal context; cryptographic trust is a capability. |
| Agent | Typed entity, not primitive | Human, organization, software, device, or AI actors can share the Entity envelope; roles belong to vocabularies/relations. |
| Provenance | Derived graph requirement | Provenance is graph traversal over entities, occurrences, relations, representations, artifacts, resources, and metadata basis. |
| Effectivity | Typed relation/assertion + temporal semantics | Applicability is a relationship between information/assertion and context over time, not a universal object status. |
| Time | Value/temporal capability | Point time, intervals, uncertainty, valid-time, and legal effect should be explicit where required without forcing one universal state machine. |
| Policy / Contract | Above minimal core | Policy defines interpretations, constraints, authority requirements, and state projections; its language/vocabulary evolves above the minimal algebra. |
| Workflow | Execution realization | Workflow topology is one strategy for satisfying policy. Completed institutionally significant occurrences survive; engine topology generally does not. |

## Current minimal center

The current architectural center is:

```text
Identity
Entity / Object envelope
Typed Relation
Representation / Expression envelope
```

with stable first-class query ownership for:

```text
Artifact
Occurrence
```

This does not claim that Artifact and Occurrence are algebraically irreducible. It claims that independent readers need stable semantics for their intrinsic queries.

## Durable facts, expressions, and projections

The State falsification produces a stronger boundary than the earlier phrase "state is often reconstructable":

```text
PRESERVED GROUND TRUTH

  Representation / Expression
  -> what was expressed

  Occurrence + Relation
  -> what actually happened

  Artifact / Resource
  -> what exact materialization exists

---------------- projection boundary ----------------

  Policy + vocabulary + temporal context
  -> operational state / status
```

Operational systems may cache `paid`, `accepted`, `validated`, or `completed`, but those values are replaceable views unless a domain explicitly preserves the assertion itself as a content-bearing institutional statement.

A semantic snapshot is not operational state. The question "what did version 3 say?" is owned by Representation / Expression and must not depend on replaying mutation history.

This projection boundary is the operative A0 rule; no unavailable historical
decision record is required to interpret it.

## Query ownership test

The following queries have deterministic architectural owners:

```text
What is this institutional thing?
-> Object / Identity

What did it say?
-> Representation / Expression

What exact material artifact expressed it?
-> Artifact / Resource + fixity

What happened, who/what acted, and when?
-> Occurrence

How are these things related?
-> Typed Relation

What supports assertion X?
-> evidence/basis relations rooted at X

Why is X considered authorized?
-> authority/policy relations rooted at X or the relevant Occurrence

Where did X come from?
-> provenance graph traversal

When does X apply or have effect?
-> temporal/effectivity relations rooted at X

What is its current operational status?
-> domain projection policy over facts + time
```

The last query deliberately has no generic State owner in the kernel.

## Dependency and durable closure

Dependency remains a relation/profile concern unless a proving ground demonstrates loss of portable meaning. Current closure semantics can identify roles such as:

```text
interpretation
evidentiary
verification
reproduction
contextual
```

and test whether required resources are resolvable, immutable, and integrity-verified without creating a second graph ontology.

## State and workflow

`State` is not the backbone of the substrate.

Likewise:

```text
workflow topology != institutional ontology
```

A small organization and a large organization may realize the same institutional requirement through different workflows. What must survive is the relevant policy/contract semantics, required authority/evidence constraints, content-bearing expressions, and completed institutional occurrences.

Normative process constraints such as separation of duties or mandatory waiting periods belong to policy semantics; the particular workflow engine remains replaceable.

## Kill-test implications

### Kill Domain Implementation

Core remains ignorant of domain words such as quotation, approval, consent, or clinical order. Domain vocabularies map them onto objects, relations, occurrences, representations, artifacts, resources, and policies.

### Kill DocSubstrate Implementation

An independent reader must reconstruct declared institutional meaning from documented profiles/vocabularies plus portable identities, relations, occurrences, representations, artifacts, resources, and closure claims. Python classes or database schemas must not be required.

### Kill Source ERP

A new operational system should reconstruct institutionally relevant facts and expressions — commitments, obligations, deliveries, payments, acceptance, effectivity, document versions — without restoring application-specific status columns, UI caches, temporary wizards, or workflow bookkeeping.

The new application may project different status labels from the same durable facts. That is compatible with institutional continuity.

## Open questions before schema freeze

Resolved since the first audit:

- Occurrence has passed the first-class query-owner test.
- State / SemanticState has failed the core promotion test.

Still open:

1. Does Artifact need separate content identity and materialization/copy identity in the portable model?
2. Can every Dependency requirement remain a relation/profile concern without creating a second graph model?
3. What minimal temporal capability is required before Effectivity is portable across legal, ERP, clinical, and preservation domains?
4. Which authority/evidence relations are substrate-generic and which belong entirely to vocabularies?
5. Should Occurrence eventually move physically inside the package envelope, or remain a parallel canonical interchange section while retaining core semantic ownership?
6. Can package lineage and migration verification preserve institutional history without promoting generic State or Provenance objects?

No portable package wire schema should be frozen merely because the Python model is convenient. Independent readers and proving grounds remain the falsification mechanism.
