# Proposed public README opening

Status: copy proposal only. It does not replace the current technical README or
change any A0 contract.

---

# DocSubstrate

**DocSubstrate lets an institutional document keep saying what it is, what it
means, where it came from, and how it relates to other records after the
software that created it is gone.**

Negotiable instruments and bills of lading are old examples of documents doing
more than displaying data. The document identifies a claim, carries
institutional consequences, and can preserve a chain of endorsement or
transfer without depending on the software screen that produced it. Modern
enterprise systems often invert that relationship: the database, workflow, and
status fields own the meaning, while the “document” is only a report. When the
application disappears, much of the record becomes an unexplained picture or
an opaque export.

LLMs make it dramatically cheaper to generate interfaces, integrations,
workflows, and replacement applications. That alone can also generate more
incompatible schemas and hidden assumptions. The middle layer decides which
future arrives. DocSubstrate keeps identity, Expressions, Occurrences, typed
Relations, Artifacts, basis, provenance, integrity, and declared dependencies
explicit, so models can help interpret and compose systems without being asked
to invent the institutional facts they read.

This work stands beside, rather than replaces, standards for provenance,
preservation, signatures, encryption, identity, domain exchange, and
local-first operation. Its narrow contribution is an hourglass waist: allocate
each durable responsibility to the smallest entity that can own it, declare the
minimum closure needed for that entity to survive, and test that applications,
databases, workflows, renderers, and model implementations can be removed.
Existing formats and vocabularies stay above or below that waist through
profiles and adapters.

> Responsibility is pushed to the point of semantic self-definition.

DocSubstrate A0 is currently a research/reference implementation. Its semantic
model and reference wire are not yet a stable public API or frozen standard.

---

## Editorial notes

- Follow this opening with the existing `A0 architectural center`, review guide,
  boundary/non-goals, and verification sections.
- Keep the historical examples as precedents, not novelty claims or legal
  equivalence claims.
- Keep “LLM” on the reader/mapping/composition side. Deterministic records own
  identity, basis, authority evidence, and durable consequences.
- Do not expand the opening into a universal-ontology claim. The standards
  subtraction matrix remains the precise neighbor comparison.
