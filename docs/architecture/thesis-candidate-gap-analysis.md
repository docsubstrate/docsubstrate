# Thesis candidate gap analysis

Status: planning analysis, not an accepted ADR or a stable wire contract.

This document tests eight candidate claims against the current A0 public
surface. A missing product demonstration is not automatically a missing kernel
primitive. The default placement order remains vocabulary, profile, adapter,
proving ground, and only then a generic-core change supported by a cross-domain
counterexample.

## Results

| Candidate | Result | Existing A0 coverage | Actual gap | Recommended owner |
| --- | --- | --- | --- | --- |
| C1 — reconstructible transaction chain | **Partial** | Objects, stable typed Relations, Expressions, Occurrences, external references, and semantic migration are already representable. See [ADR 0032](../adr/0032-semantic-self-sovereignty.md), the [semantic model](semantic-model.md), and `tests/test_migration.py`. | The loose three-field formulation conflates recorded lineage with future permission and execution. Predecessor links are durable Relations; allowed successor types and effects require a versioned domain vocabulary/policy. What is missing is an executable order-to-cash kill-runtime proving ground that reconstructs consequences from independently readable packages. | Commerce vocabulary + policy + proving ground; **not kernel**. |
| C2 — truth-freshness boundary | **Existing in principle; wording partial** | A0 already separates durable facts/Expressions from replaceable operational projections and temporal evaluation. See the [semantic model](semantic-model.md), [interchange profiles](interchange-profiles.md), and [ADR 0032](../adr/0032-semantic-self-sovereignty.md). | “Millisecond truth belongs to a database; everything else belongs to documents” is too absolute. Concurrency control and immediate coordination remain runtime responsibilities, while durable institutional consequences belong to the substrate regardless of latency. A concise public boundary statement and a concurrency counterexample are still useful. | Architecture narrative + proving test; **not kernel**. |
| C3 — custodian/authority succession | **Partial** | A0 can express a basis-qualified succession Occurrence and typed Relations. It already states that signatures are verification evidence, and that a key envelope is not authority. See the [standards matrix](standards-subtraction-matrix.md) and [ADR 0033 §8](../adr/0033-protected-semantic-components.md). | There is no accepted signature profile, durable authority vocabulary, or executable succession case showing that a position can pass custody without equating a key holder, IdP account, or human with the position. | Signature profile + authority vocabulary + proving ground. Promote to kernel only after a cross-domain representational failure. |
| C4 — selective disclosure and cryptographic erasure | **Partial** | Flat protected semantic components, opaque public descriptors, independently replaceable key envelopes, ciphertext fixity, and identity/AAD binding already exist. See [ADR 0033](../adr/0033-protected-semantic-components.md) and [ADR 0034](../adr/0034-jwe-general-json-physical-profile.md). | A0 does not specify Merkle disclosure proofs, BBS+/SD-JWT disclosure, or prove that destroying a key satisfies any legal deletion duty. Those are distinct mechanisms and policy claims. They must be evaluated before adding a profile. | Standards subtraction + optional protection profile + legal/domain policy; **not kernel**. |
| C5 — human/machine hybrid document | **Partial** | A0 distinguishes Expression from Artifact and already adopts PDF Associated Files and domain formats rather than replacing them. See the [standards matrix](standards-subtraction-matrix.md) and [interchange profiles](interchange-profiles.md). | There is no concrete profile or fixture proving a human-readable health-report PDF, an embedded FHIR document payload, signature evidence, provenance, and Artifact-to-Expression correspondence survive independently. | Clinical vocabulary profile + PDF adapter + proving ground. |
| C6 — neighboring architectures | **Partial** | The [standards subtraction matrix](standards-subtraction-matrix.md) already positions provenance, preservation, identity, cryptography, domain documents, and authorization standards. | Local-first software, UCAN-style delegation, and process-mining/SAP document-flow approaches are not yet subtracted explicitly. Their mechanisms should be adopted or bounded without claiming their problem spaces as DocSubstrate inventions. | Architecture comparison; **not kernel**. |
| C7 — LLM responsibility split | **Existing in architecture; public explanation partial** | A0 requires deterministic identity, vocabulary, basis, fixity, and dependency declarations; unknown semantics must remain unknown. The [interchange profiles](interchange-profiles.md) define deterministic reader obligations. | The public surface does not yet state the division plainly: models may map vocabularies and plan interpretations, but they cannot manufacture authority, basis, identity, or durable facts. A context-cost experiment is also absent. | Public narrative + reader/context-slicing proving ground; **not kernel**. |
| C8 — public “documents as systems” narrative | **Missing from the public opening** | The current [README](../../README.md) is technically accurate and states semantic self-sovereignty, but begins at the abstraction rather than the historical and practical problem. | Add a restrained opening that uses negotiable instruments and bills of lading as precedents, explains the LLM-era economic inversion, and positions DocSubstrate as a narrow composition contract rather than claiming invention of every neighboring mechanism. | Narrative only. |

## C1 naming options

The three ideas should not be frozen as generic fields until the proving ground
shows that they are always properties of the same owner. Candidate terminology:

| Option | Recorded ancestry | Permitted continuation | Declared result |
| --- | --- | --- | --- |
| A | `predecessor_refs` | `allowed_successor_types` | `institutional_effects` |
| B | `lineage_refs` | `continuation_constraints` | `declared_consequences` |
| C | `antecedent_refs` | `admissible_continuations` | `effect_declarations` |

Option A is easiest to read; option B most clearly separates durable lineage
from policy constraints; option C is the most formal. This document chooses
none. In particular, an effect declaration is not proof that an effect actually
occurred. The corresponding durable consequence still needs its responsible
Expression, Occurrence, or Relation and basis.

## Identity naming options

Three strategies remain available and should be tested by the version-chain
profile rather than settled by prose:

1. **Content hash only.** Strong material or canonical-content correlation, but
   awkward for continuing institutional identity and any legitimate equivalent
   re-materialization.
2. **Assigned identifier only (for example UUID/URI).** Stable across
   materializations, but integrity and equivalence require separate evidence.
3. **Coexisting identities.** An assigned institutional identifier owns
   continuity; content/resource digests own fixity; explicit Relations bind
   versions and manifestations.

A0 already follows the third shape in practice by separating Object,
Representation, Artifact, and resource digest responsibilities. That is an
architectural observation, not a decision about a future canonical identifier
syntax.

## No generic gap established

None of C1–C8 currently demonstrates something that cannot be represented by
the A0 algebra plus a vocabulary, profile, adapter, policy, or proving ground.
The next work should therefore try to falsify the existing owners before adding
another primitive.
