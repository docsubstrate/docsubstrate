# ADR 0033: Flat protected semantic components and independent key envelopes

## Status

Accepted as a generic logical contract. Cryptographic wire profiles advance
independently; the RFC 7516/7518 JWE profile is provisional interoperable, while
other candidate profiles remain experimental or unprofiled.

## Context

Durable institutional documents frequently mix information with different
disclosure boundaries. An ERP invoice may have human-readable identity and
totals, confidential commercial terms, accounting metadata, personal data, and
audit evidence. Treating the whole document as one ciphertext is too coarse.
Nesting ciphertext for every permission layer couples semantic composition to a
particular access hierarchy and makes partial disclosure, key rotation, recovery,
and independent preservation harder to reason about.

Existing standards already supply cryptographic structures. JWE General JSON
Serialization can encrypt the same content for multiple parties and supplies AAD
for integrity-protected public data. COSE_Encrypt separates encrypted content
from recipient information, supports multiple recipients, and permits detached
ciphertext. HPKE supplies a cryptographic building block, not DocSubstrate's
institutional ownership model. DocSubstrate must profile these standards rather
than invent algorithms.

## Decision

1. Every Representation carries an explicit `clear` or `encrypted` protection
   posture. Clear is the default for compatibility but is serialized explicitly.
2. An Expression may list parallel semantic component Representations. Components
   have their own stable identity, type/vocabulary, version, and content resource.
3. An encrypted Representation is a composition leaf. Semantic composition may
   be hierarchical, but ciphertext may not conceal another component graph.
4. Each encrypted component references exactly one `ProtectionDescriptor`, which
   names the ciphertext resource, an external encryption profile, and an
   identity-binding/AAD profile.
5. A component content key is never stored in the manifest. One or more
   independently versioned `KeyEnvelope` records may reference the same
   protection. This supports person, role/key-domain, enterprise KMS, regulator,
   escrow, and recovery recipients without encrypting the semantic content again.
6. Envelope addition, removal, or rewrapping is access-package evolution, not an
   Expression semantic revision. Component composition remains in the semantic
   migration projection; protection and envelope mechanics do not. This is a
   semantic/versioning rule, not a byte-preservation promise: a physical profile
   may require a new ciphertext container when its recipient set changes.
7. `recipient_ref` and `wrapping_key_ref` are declared durable references. An IdP
   subject, ERP role, KMS alias, or directory group may be an external binding,
   but is not silently promoted to institutional identity.
8. A key envelope is not a Grant, Authority, credential, or proof that access was
   lawful. Policy evaluation and key release are replaceable runtime operations.
   Their durable basis and actual disclosure consequences belong in typed
   Relations, credentials/resources, and Occurrences.
9. A public manifest may use opaque component identifiers and a generic protected
   type to avoid leaking classifications. The authorized plaintext must carry the
   preserved domain vocabulary and semantic descriptor needed for authorized
   interpretation. Public closure and authorized interpretation closure are not
   falsely treated as identical.

## Binding contract

The binding profile must integrity-bind, at minimum, its domain separator,
Object identity, containing Expression identity/version, component
identity/version, and the declared vocabulary/schema context. Package identity
and physical location are deliberately excluded so repackaging does not change
semantic identity. A physical JWE or COSE adapter
may serialize content and recipients together even though the logical ownership
model keeps the protection descriptor and envelopes independently addressable.

The current core validates declarations, references, resource fixity, flatness,
and the existence of at least one access or recovery envelope. It does not claim
that a key is currently available, that ciphertext decrypts, or that a recipient
is authorized. Those claims require cryptographic and institutional validation.

## Consequences

- Public and protected metadata coexist as sibling semantic components.
- Complexity scales by adding components and envelopes, not new core primitives.
- Re-encryption or key rotation cannot silently masquerade as semantic change;
  it may still replace physical ciphertext bytes and their fixity record.
- Lost external targets do not erase component identity or ciphertext fixity.
- Revocation can stop future key release but cannot retract plaintext already
  disclosed to a recipient.
- Domain packages retain classifications, access rules, ERP roles, and business
  vocabulary.

## Falsification cases

This decision must be revised if a proving ground shows that:

- a required partial-disclosure case cannot be expressed without nesting
  encrypted semantic components;
- standard JWE, COSE, CMS, or HPKE-based profiles cannot bind the required
  identities without a custom cryptographic format;
- envelope changes necessarily alter institutional content in a domain rather
  than merely its access paths;
- opaque public descriptors make authorized minimum survivable closure
  unverifiable even after decryption; or
- durable authority cannot be represented through existing entity, Relation,
  Occurrence, credential/resource, and vocabulary mechanisms.

## Standards references

- [RFC 7516: JSON Web Encryption](https://www.rfc-editor.org/rfc/rfc7516.html)
- [RFC 9052: CBOR Object Signing and Encryption](https://www.rfc-editor.org/rfc/rfc9052.html)
- [RFC 9180: Hybrid Public Key Encryption](https://www.rfc-editor.org/rfc/rfc9180.html)
