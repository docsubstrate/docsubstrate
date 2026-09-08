# Standards subtraction matrix

DocSubstrate must not claim novelty for mechanisms already standardized. The
question is what disappears if DocSubstrate's ownership and closure contract is
subtracted while the standards remain.

| Requirement | Existing coverage | DocSubstrate action | Remaining contract |
|---|---|---|---|
| Identifiers | URI, UUID, DID, OIDC `iss` + `sub` | Adopt/profile | Separate institutional identity from source and IdP bindings |
| Graph and vocabulary | RDF, JSON-LD, published ontologies | Adopt/profile | Require vocabulary version and preservation strategy for durable interpretation |
| Provenance | W3C PROV, PREMIS, C2PA | Compose | Assign provenance to the entity/claim it qualifies; do not infer basis |
| Logical package | RO-Crate and domain package profiles | Evaluate/adopt | Entity roots, closure roles, critical-extension failure behavior |
| Physical preservation | BagIt, OCFL, E-ARK | Adopt/profile | Keep physical location separate from institutional identity |
| Content descriptors | OCI-style media type, length, digest | Adopt | Bind descriptors to Expression/Artifact ownership |
| Artifact preservation | PDF/A, PDF 2.0 Associated Files | Adopt/profile | Exact Artifact-to-Expression/version correspondence |
| Signatures | CMS, JWS, COSE, PAdES/XAdES/CAdES | Adopt | Signature is verification evidence, not authority by itself |
| Encryption | JWE, COSE, HPKE, CMS | Adopt/profile; provisional interoperable RFC 7516/7518 JWE profile | Flat component ownership, identity/AAD binding, and access-envelope independence from Expression version |
| Authentication | OIDC, SAML, WebAuthn, X.509 | Adopt | IdP principal is an external binding, not institutional identity |
| Portable credentials | DID/VC | Adopt/compose | Capacity, delegation, authority basis, time, and institutional consequence |
| Business documents | UBL, Factur-X, FHIR and domain standards | Domain package | Do not move domain vocabulary into generic core |
| Occurrences | PROV Activity and domain event models | Map/profile | Preserve one basis-qualified occurrence identity and its correlated fact bundle |
| Authorization | XACML, Cedar, OPA/Rego, ERP IAM | Adapter/profile | Durable Grant/Policy/Authority semantics separated from runtime decision and key release |

## Subtraction result

Most serialization, cryptographic, preservation, identity, and vocabulary
mechanisms are already covered. The uncovered generic responsibility is:

1. entity-rooted minimum survivable closure;
2. orthogonal ownership of Object, Expression, Occurrence, Relation, and Artifact;
3. explicit distinction among asserted, observed, derived, and inferred facts;
4. rejection of application status, source binding, or runtime convention as
   hidden durable truth;
5. executable kill-runtime, kill-database, broken-reference, vocabulary,
   correspondence, minimality, and composition tests.
6. a component-level protection posture that keeps semantic composition,
   ciphertext, access paths, and institutional authority as separate concerns.

If a mature standard or profile later covers this complete contract, the custom
wire/model should be reduced to an adapter and conformance suite.

## Deferred candidates

- IdP/DID/VC bindings for institutional parties, credentials, and keys.
- Explicit representation content-resource versus dependency-resource roles.
- Stable/production validation criteria for the provisional JWE profile, plus
  candidate COSE, CMS, or HPKE-based adapters.
- Durable grant/authority semantics, if proving grounds demonstrate that typed
  Relations, Occurrences, credentials, and vocabulary packages are insufficient.

These remain candidates until proving grounds show a generic representational
gap. They are not new kernel primitives in this decision.
