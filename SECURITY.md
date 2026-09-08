# Security reporting boundary

DocSubstrate A0 is a research/reference implementation. There are no supported
production versions and no security certification. In particular, the
provisional JWE adapter has not received an independent cryptographic review or
a broad negative/fuzz campaign.

Successful JWE decryption authenticates the profile's ciphertext and component
binding. It does not establish identity, authority, consent, purpose, lawful key
release, or any other institutional authorization decision. Callers must bound
untrusted input sizes and place key custody, release policy, audit, and runtime
hardening outside this reference adapter.

The public maintainer identity for the bounded A0 artifact is
Zen (Chen-Yu) Hsieh. Non-sensitive defects may be reported at
<https://github.com/docsubstrate/docsubstrate/issues>.

Do not place vulnerability details, secrets, personal data, or restricted
evidence in a public issue. No private vulnerability-reporting channel has been
verified or enabled for this candidate. A sensitive report must wait for the
maintainer to publish an authenticated private channel; this file does not claim
that GitHub private vulnerability reporting or any email endpoint is available.
