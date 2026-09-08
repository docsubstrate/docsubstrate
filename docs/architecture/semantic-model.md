# DocSubstrate multidimensional model

## Thesis

A document is not a linear pipeline of business data that becomes structure
that becomes presentation. Those are distinct representation dimensions of
the same document and they remain meaningful at the same time.

DocSubstrate therefore models **correspondence between dimensions**, rather
than treating each dimension as a disposable intermediate representation.

It also distinguishes preserved institutional ground truth from replaceable
application projections. A mutable application `state` is not the container for
the dimensions below.

## Initial dimensions

### Semantic dimension — what it means

Examples:

- `party.customer`
- `party.seller`
- `commerce.line_item`
- `commerce.tax`
- `commerce.total`
- `clinical.measurement`
- `clinical.finding`
- `document.signature`

Domain vocabularies belong here. A clinical standard, an ERP database, or an LLM may
all be sources for semantic entities, but none defines the DocSubstrate core.

### Structural dimension — how it exists in a document

Examples:

- document
- section
- paragraph
- table
- row
- cell
- image
- header
- footer
- page number

Structural nodes describe composition and containment. They do not acquire
business meaning merely because a renderer can draw them.

### Presentation dimension — how it should appear

Examples:

- typography
- spacing
- alignment
- borders
- column sizing
- pagination policy
- repeated table headers

Presentation is neither business meaning nor structural identity.

### Physical dimension — the material page/media constraints

Examples:

- A4 / Letter / label / receipt media
- fixed page width and height
- printable regions and reserved regions
- margins and orientation
- duplex / bleed constraints
- resolved physical pages

Physical media is first-class because formal documents and printer execution
operate against finite physical containers. A page is an execution boundary of
a resolved document, not the semantic boundary of the institutional object.

## Correspondence is first-class

The same semantic entity can have multiple structural representations:

```text
party.customer ──represented_by──> party block
               └─represented_by──> compact address line
```

The same structural primitive can represent unrelated semantics:

```text
table ──represents──> commerce.line_items
table ──represents──> clinical.measurements
table ──represents──> audit.findings
```

This is why DocSubstrate does not define a canonical chain such as
`semantics -> structure -> layout`. Rendering may consume projections of all
four dimensions, while the relations remain available for validation,
provenance, accessibility, document comparison, and cross-document reasoning.

## Durable record, not Document State

Earlier architecture sketches used a box named `Document state`. That name is
now rejected because it collapses two different kinds of truth:

- facts that happened, owned by Occurrences and typed Relations;
- content that was expressed, owned by Representations / Expressions and their
  resources or Artifacts.

Operational state is derived below that boundary.

```text
source systems / standards / APIs / LLMs
              │
              ▼
       semantic adapters
              │
      ┌───────┴───────────────────────┐
      │ Durable institutional record │
      │                               │
      │ objects / identities          │
      │ representations / expressions│
      │ occurrences                   │
      │ typed relations               │
      │ artifacts / resources         │
      │                               │
      │ semantic correspondence       │
      │ structural correspondence     │
      │ presentation intent           │
      │ physical constraints          │
      └───────┬───────────────────────┘
              │
       ┌──────┴───────────────┐
       │                      │
       ▼                      ▼
 renderer adapters      projection policy
       │                 + time/vocabulary
       ▼                      │
PDF / DOCX / printer          ▼
                         operational status
```

The renderer and the status projection are both consumers of preserved meaning.
Neither owns the institutional ground truth.

The diagram above defines the A0 projection boundary.

## Source systems and renderers are adapters

Source systems and renderers are proving grounds, not the architecture.
Formats and printer languages are execution or materialization choices, not
the institutional model.

Source adapters recover source-system meaning into explicit identities,
representations, occurrences, relations, and correspondence. Renderer adapters
consume resolved document intent without acquiring ownership of that meaning.

## Consequence: documents form graphs, not folders

When semantic identity and typed relations survive across artifacts, documents
can participate in business and institutional relationships directly:

```text
quotation ──accepted_as──> sales order
sales order ──fulfilled_by──> delivery
sales order ──billed_by──> invoice
invoice ──settled_by──> payment
```

A folder hierarchy can still be projected for human convenience, but it is not
canonical organization. Customer, transaction, case, patient, provenance,
time, version, and evidence are simultaneous dimensions and should not be
forced into one tree.

## Current design rule

Do not let a source adapter, renderer, storage system, document format, or
application status column own the ontology.

New core concepts must describe durable institutional meaning, durable
representation/material identity, or a proven cross-domain query owner.
Host-specific concepts and operational projections stay outside the kernel.
