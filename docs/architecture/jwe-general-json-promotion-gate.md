# JWE General JSON source promotion gate

Date: 2026-09-07

## Scope and ownership

This gate evaluates the existing
`docsubstrate.jwe-general-json/rsa-oaep-256+a256gcm/0.1` adapter. It does not add
or change a DocSubstrate semantic primitive. RFC 7516 continues to own General
JWE JSON Serialization and external AAD; RFC 7518 owns `RSA-OAEP-256` and
`A256GCM`. DocSubstrate owns only the strict profile and the mapping of existing
component-binding and key-envelope records.

All executable interoperability input is synthetic. RSA keys are generated for
each test run and are neither checked in nor treated as institutional
credentials. The only fixed inputs are public RFC 7520 vectors.

## Interoperability result

PASS with JWCrypto 1.6.0 as the independent JOSE implementation and
Cryptography 50.0.1 as the primitive provider:

1. DocSubstrate writer to JWCrypto reader: both independently generated RSA
   recipient keys decrypt the same authenticated synthetic component.
2. JWCrypto General JSON writer to DocSubstrate reader: both declared
   `KeyEnvelope` recipient paths decrypt with the exact semantic component
   binding as external AAD.
3. The RFC 7520 Section 5.2 `A256GCM` vector passes.
4. The RFC 7520 Section 5.10 external-AAD construction and AES-GCM vector pass.

The round trips test the full profile composition. The RFC vectors separately
anchor the applicable standardized content-encryption and AAD sub-contracts.

## Counterexamples and non-claims

- RFC 7520 has no single vector combining this profile's
  `RSA-OAEP-256` + `A256GCM` + multiple recipients + external AAD. Section 5.2
  uses `RSA-OAEP`; Section 5.10 uses `A128KW` + `A128GCM`. Treating either as a
  full-profile vector would be false.
- A JWE with an extra shared unprotected header is valid and decryptable in
  JWCrypto, but is deliberately rejected by the narrower DocSubstrate profile.
  General JOSE interoperability therefore does not imply profile conformance.
- Successful decryption proves key possession and AEAD authentication. It does
  not prove institutional identity, authorization, lawful key release, purpose,
  consent, or policy compliance.
- This source-only gate does not cover a KMS/HSM, remote key discovery or
  release, revocation, deployment, customer evidence, side-channel review, or
  operational recovery.

## Promotion decision

The profile may advance beyond experimental to **provisional interoperable**.
It must not advance to stable or production on this evidence alone. The smallest
next gate is a versioned negative/fuzz conformance corpus reviewed independently
of the adapter implementation, followed by an independent cryptographic design
review. No generic representational gap was discovered, so no new primitive is
justified.
