# ADR 0034: JWE General JSON protected-component physical profile

## Status

Accepted as a provisional interoperable physical adapter profile. It has passed
the source-level interoperability gate described below, but it is not a stable
production-cryptography or institutional-authorization claim.

## Ownership and dependency gate

- RFC 7516 owns General JWE JSON Serialization, multi-recipient structure,
  base64url encoding, and the protected-header plus external-AAD construction.
- RFC 7518 owns `RSA-OAEP-256`, its SHA-256/MGF1 parameters and 2048-bit RSA
  minimum, and `A256GCM`.
- `cryptography` supplies the reviewed RSA-OAEP and AES-GCM primitives through
  the optional `jwe` dependency group.
- DocSubstrate owns only the profile restriction and the mapping from existing
  `ProtectionDescriptor`, `KeyEnvelope`, and component-binding records to JWE.

No new generic primitive is required. The protected-component gap was already
recorded before `ProtectionDescriptor` and `KeyEnvelope` were introduced; this
slice is an adapter proving ground over those primitives.

## Named profile

`docsubstrate.jwe-general-json/rsa-oaep-256+a256gcm/0.1`

The profile requires:

1. General JWE JSON Serialization, including a `recipients` array;
2. one recipient member for every logical KeyEnvelope selected by the component;
3. `RSA-OAEP-256` key encryption with RSA keys of at least 2048 bits;
4. `A256GCM` content encryption with a newly generated CEK and 96-bit IV;
5. exact `docsubstrate.semantic-component-binding/0.1` bytes as external JWE AAD;
6. a per-recipient `kid` equal to the logical `envelope_id`; and
7. fail-closed parsing, profile matching, envelope matching, key unwrap, and AEAD
   authentication.

The physical JWE document may be the resource addressed by both the protection
descriptor and its logical envelope records. This follows RFC 7516's combined
serialization without collapsing their distinct logical ownership.
Per-recipient `kid` headers are unprotected JWE selector data. The adapter checks
their complete one-to-one correspondence with declared envelopes but never
interprets a `kid` as integrity evidence or authorization.

Because this strict profile requires the JWE recipient set to equal the
declared logical envelope set, adding or removing an envelope requires a new JWE
container with a new CEK and therefore new ciphertext bytes. The Expression's
semantic projection remains unchanged, but the ciphertext resource and its
fixity must be updated.

## Security and authorization boundary

Successful decryption establishes that one RSA private key unwrapped the CEK and
that the protected header, ciphertext, and component binding authenticated. It
does not establish that the caller is an institutional actor, that key release
was lawful, or that a Grant, Authority, consent, purpose, or policy condition was
satisfied. Those remain external policy decisions whose durable basis and
consequences belong in existing Relations, credentials/resources, and
Occurrences.

Keys used by the executable profile tests are freshly generated synthetic keys.
No key is stored in the package, fixture, repository, or core model.

## Compatibility and limits

The adapter is optional so the generic package and independent-reader core remain
dependency-free. Version 0.1 deliberately permits only one algorithm pair and
rejects additional top-level or recipient members.

The source-level promotion gate passed with JWCrypto 1.6.0 as a second JOSE
implementation: both recipients of a DocSubstrate-produced document decrypted
independently, and DocSubstrate decrypted both recipient paths of a
JWCrypto-produced document. The test uses only freshly generated RSA keys,
synthetic component data, and the deterministic component binding.

Applicable public vectors from RFC 7520 also pass:

- Section 5.2 validates the `A256GCM` CEK, IV, protected-header authenticated
  data, ciphertext, and tag path.
- Section 5.10 validates the external-AAD construction required by RFC 7516,
  including `Encoded Protected Header || "." || BASE64URL(AAD)`.

These are sub-contract vectors, not a single vector for this complete profile.
RFC 7520 does not publish one example combining `RSA-OAEP-256`, `A256GCM`,
multiple recipients, and external AAD. Its Section 5.2 uses `RSA-OAEP`, and its
Section 5.10 uses `A128KW` plus `A128GCM`. Bidirectional second-implementation
tests close that composition gap without claiming a nonexistent RFC vector.

The profile is intentionally a strict subset of RFC 7516. For example, a
cryptographically valid JWE with an additional shared unprotected header is
accepted by JWCrypto but rejected by this adapter. This is fail-closed profile
enforcement, not a claim that the broader JWE is invalid.

The profile can advance from experimental to provisional interoperable. It does
not yet specify remote KMS operations, key discovery, key release, revocation,
or authorization, and has not received an independent security review or a
broad negative/fuzz corpus. Those omissions prevent stable or production
promotion.
