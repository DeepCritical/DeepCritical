# ADR 0001: Project-owned canonical document view

- Status: Accepted
- Date: 2026-07-27

## Context

DeepCritical currently preserves Docling, JATS, BioC, GROBID, and OCR outputs.
Calling a serialized `DoclingDocument` canonical would make downstream
annotations and processor-independent contracts depend permanently on one
processor's data model. Rewriting native outputs into a shared structure during
ingestion would also discard useful native fidelity and make upgrades harder to
audit.

## Decision

DeepCritical will introduce a versioned, project-owned
`CanonicalDocumentView` in a separate change.

Each processor will preserve its native output unchanged as a typed
`DataProductRef`. An adapter may then create a canonical view with ordered
blocks, immutable content hashes, source anchors, native-product references,
document metadata, and explicit figure, table, caption, citation, and reference
relationships.

Until that view exists:

- `docling_document` is a native Docling product, not a canonical product;
- `ContentSpan.representation_anchor` identifies the exact product ID, native
  node ID, and character range it targets;
- `DoclingItemLocator` remains a valid native locator for formats without a
  stable source-coordinate contract; and
- annotations must not claim processor-independent identity.

Native products remain immutable after the canonical view is introduced.
Annotations will identify the exact canonical-view product they target so that
reprocessing cannot silently move labels between blocks.

## Consequences

Downstream code must use adapters when it needs a processor-independent view,
while audit and debugging code can retain full access to native representations.
This adds an explicit conversion stage, but avoids a repository-wide migration
whenever Docling or another processor changes its native schema.
