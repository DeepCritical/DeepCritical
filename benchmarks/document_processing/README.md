# Scientific document-processing bake-off

This harness compares parser outputs against a pinned, reusable PMC corpus without
network access and without starting Docling, GROBID, OCRmyPDF, or any managed parser.
It tests document conversion fidelity and provenance. It does **not** assess biomedical
truth, scientific claims, clinical evidence quality, or Alzheimer's relevance.

The checked-in `manifest.example.json` is a schema example, not a usable corpus. Its
PMC IDs, paths, URLs, hashes, and unverified licenses are placeholders. Replace every
placeholder and verify article-specific reuse rights before using `--enforce-baseline`.

## Corpus contract

Each manifest record identifies one PMC article and pins two immutable source bytes:
the native JATS/NXML article and the corresponding PDF. Paths are relative to
`artifact_root`, and every artifact is verified before any scores are calculated. A
missing file, an unexpected hash, a duplicate document ID, or an observation-set gap
is a hard input error; the runner never treats it as a zero score or silently skips it.

Each document has one or more of these domain-independent parser-stress categories:

- `multi-column`
- `scanned`
- `table-heavy`
- `figure-heavy`
- `malformed`

Normal development manifests may contain a few paired fixtures. Passing
`--enforce-baseline` additionally requires:

- 50 to 75 documents;
- a numeric `PMC...` identifier for every document;
- at least one document in every required category; and
- `reuse.reuse_allowed: true` and `reuse.verified: true` for every article.

The harness deliberately has no downloader. Build the corpus using approved PMC
retrieval APIs, preserve the acquired bytes, record the article's actual license, and
compute SHA-256 hashes out of band. This separation prevents an evaluation command
from changing its own test data.

## Observation contract

A parser adapter writes either a JSON array, `{"observations": [...]}`, a single JSON
observation, or one observation object per line in JSONL. Candidate and reference sets
must each contain exactly one object for every manifest document.

```json
{
  "document_id": "PMC1234567",
  "parser": {
    "name": "docling-grobid",
    "version": "docling-2.x_grobid-0.9.0",
    "configuration_hash": "64-lowercase-or-uppercase-hex-characters"
  },
  "source_artifact": "pdf",
  "outcome": "complete",
  "text": "Normalized full text in reading order...",
  "reading_order": ["Title", "Abstract", "Introduction", "Methods"],
  "headings": [
    {"text": "Introduction", "level": 1}
  ],
  "tables": [
    {
      "source_id": "table-1",
      "caption": "Cohort characteristics",
      "text": "column 1 | column 2",
      "content_hash": "optional-64-character-hash-of-normalized-table"
    }
  ],
  "figures": [
    {
      "source_id": "fig-1",
      "caption_id": "caption-1",
      "caption": "Study flow"
    }
  ],
  "references": [
    {"doi": "10.1000/example", "pmid": "12345678", "text": "..."}
  ],
  "textual_items": [
    {
      "id": "#/texts/0",
      "text": "Introduction",
      "locator": {"page": 1, "bbox": [72.0, 96.0, 315.0, 118.0]}
    },
    {
      "id": "sec-intro",
      "text": "Introduction",
      "locator": {"xml_id": "sec-intro", "xpath": "/article/body/sec[1]"}
    }
  ],
  "content_hash": "hash-of-the-current-normalized-output",
  "output_hashes": [
    "hash-of-the-current-normalized-output",
    "hash-from-an-identically-configured-repeat"
  ],
  "elapsed_seconds": 4.25,
  "peak_memory_bytes": 734003200
}
```

Candidate observations require `parser`, resource measurements, and a `content_hash`
for `complete` and `partial` outcomes. `configuration_hash` records the resolved parser
policy: Docling, GROBID, OCR, alignment, versions, model/container identifiers, and
the conditional-routing policy. It is deliberately **not** the list of stages a given
document happened to execute. Thus born-digital PDFs and scanned PDFs can share one
baseline identity while their executed composition remains in provenance. The first
entry in `output_hashes`, when present, must be the current `content_hash`. At least two
entries are required to measure determinism. All hashes must be actual SHA-256 values,
not the explanatory strings shown above. `source_artifact` is required and is either
`pdf` or `jats`; it determines which locator form is accepted.

Allowed outcomes are `complete`, `partial`, `quarantined`, and `failed`. The manifest
controls which outcomes pass operational checks. An empty `complete` or `partial`
candidate cannot pass when the reference contains text.

PDF observations require a one-based page number and a finite, non-zero-area
`[left, top, right, bottom]` bounding box. Source-native JATS locators may use a non-empty
`xml_id`, `xpath`, or `native` value. A JATS native ID cannot satisfy the PDF geometry
gate. Locator coverage counts only non-empty textual items. Text without item-level
locators receives zero coverage.

## Metrics

Scores are deterministic and range from zero to one:

- **Text fidelity:** multiset F1 over Unicode-normalized word tokens. Reading order is
  evaluated separately, so repeated words are still counted without requiring a
  quadratic edit-distance computation over full articles.
- **Reading order:** `SequenceMatcher` ratio over the normalized token stream.
  This ignores parser-specific block segmentation, tolerates local insertions and
  deletions, and still penalizes reordered content.
- **Headings:** multiset F1 over normalized `(level, text)` pairs.
- **Tables:** multiset F1 using normalized table hashes when supplied, otherwise
  normalized caption plus table text/Markdown/HTML.
- **Figure-caption association:** multiset F1 over ordinal and caption text.
  Parser-native figure/caption IDs remain lineage evidence but are not portable
  between JATS and PDF parses.
- **References:** multiset F1 keyed by DOI, then PMID, then normalized citation text.
- **Locator coverage:** located textual items divided by all non-empty textual items.
  The corpus aggregate is micro-averaged; the report also gives per-document values.
- **Determinism:** one when at least two `output_hashes` are identical and zero when
  they differ. It is reported as unmeasured when fewer than two runs are supplied.

When both candidate and reference contain no tables or no figures, that optional
metric is reported as not applicable and is excluded from corpus means. Mutual
absence therefore cannot inflate a parser's quality score. A missing candidate
structure when the reference contains one still scores zero.

The report also records outcomes, elapsed time, documents and characters per second,
mean/maximum heavy-parser-stage memory, measured-document counts, per-document
diagnostics, and hashes
of all three controlling inputs. It intentionally contains no generation timestamp or
absolute input path, so identical inputs produce byte-for-byte identical sorted JSON.

Quality thresholds are corpus-level. `locator_coverage: 0.95` applies to the
micro-average; other quality metrics use the reported aggregate mean. A determinism
threshold fails if repeats were not recorded. Optional performance gates are:
`min_documents_per_second`, `min_characters_per_second`, and
`max_peak_memory_bytes`. Establish baseline performance on declared hardware before
adding those gates.

## Generate candidates from the processing CAS

The repository includes a read-only adapter from persisted pipeline state to this
observation contract. It correlates each selected manifest artifact with a
`DocumentArtifact` by source SHA-256, selects the latest persisted `docling` run (or
an exact corpus-wide `--output-policy-hash`), verifies every referenced CAS blob,
and projects the serialized `DoclingDocument` plus `ContentSpan` locators without
calling a parser.
`--configuration-hash` remains available for single-invocation debugging, but it
includes the input hash and therefore is not a corpus-wide policy selector.

```console
uv run deepcritical-generate-document-observations \
  benchmarks/document_processing/manifest.json \
  --cas .document-processing-cas \
  --source-artifact pdf \
  --output-policy-hash <static-output-policy-sha256> \
  --output benchmarks/document_processing/observations/docling.json
```

Use `--source-artifact jats` to generate the native-JATS candidate set. The generation
step reads source bytes from CAS, so the manifest's relative corpus files do not have
to be present for generation alone. The comparison runner still verifies those pinned
files before scoring.

Selection and projection are intentionally strict:

- a missing or ambiguous source-hash match is an input error; matching `pmcid`
  identifiers may disambiguate duplicate source bytes;
- a `complete` or `partial` run must retain both `docling_document` and
  `content_spans` outputs;
- when no requested parser run exists, only an explicit persisted `quarantined` or
  `failed` terminal run can become an outcome observation;
- reading order follows the Docling body tree, with detached parser-native text items
  appended in collection order;
- tables and figure-caption links come directly from Docling item data and references;
- bibliography entries come from persisted GROBID `biblStruct` annotations when a
  matching alignment overlay exists, otherwise only items explicitly labelled
  `reference` by Docling are emitted. The adapter does not infer DOI, PMID, or missing
  citations; and
- repeat hashes are collected only from independently forced workflows with the same
  non-empty repetition group and the same static pipeline recipe. A single run leaves
  determinism unmeasured instead of pretending a repeat occurred. The selected Docling,
  GROBID, OCR-derivation, and scholarly-alignment records must all be in that workflow;
  unaligned cross-workflow records are rejected.

The execution-time measurement includes Docling, every GROBID attempt on the original
PDF (including an unsuccessful attempt before OCR), OCRmyPDF, the selected derivative
GROBID attempt, and scholarly alignment. It intentionally excludes bounded-input
preflight and content-integrity validation, which are separately persisted contract
checks rather than document conversion work. Missing peak-memory instrumentation on
any included stage leaves peak memory unmeasured; it is never converted to zero.

Current parser runs may omit peak-memory instrumentation. In that case
`peak_memory_bytes` is omitted and `provenance.peak_memory_bytes_recorded` is false.
`--enforce-baseline` rejects observation generation itself when any included stage
lacks comparable accounting or when measurement environments differ across the
corpus. Capture peak memory for every included stage before generating a baseline or
using a peak-memory gate.

For an enforced baseline, a scalar peak is also insufficient: every included
stage must preserve an exclusive invocation-cgroup `MemoryMeasurement` with
method `cgroup-v2-memory.peak`, start/finish timestamps, an explicit confirmation
that shared overhead was excluded, no `oom_kill` event, and one matching environment
hash for each boundary across the corpus. The normal shared Docling and GROBID
compose services are intentionally treated as unmeasured until a deployment supplies
task-bound isolation; neither client RSS nor Docker stats is acceptable evidence.

To measure determinism, process each source twice with distinct forced workflows and
the same group, then regenerate the observations. Give every independent repeat a
different `--workflow-attempt-id`. Reuse an attempt ID only when retrying or resuming
that same interrupted attempt; reusing it for another repeat invalidates independence:

```console
uv run deepcritical-process-document paper.pdf \
  --force-reprocess --benchmark-repetition-group p0-bakeoff-2026-07 \
  --workflow-attempt-id paper-attempt-01
uv run deepcritical-process-document paper.pdf \
  --force-reprocess --benchmark-repetition-group p0-bakeoff-2026-07 \
  --workflow-attempt-id paper-attempt-02
```

## Run it

With an explicit reference set:

```console
uv run python -m DeepResearch.scripts.run_document_processing_benchmark \
  benchmarks/document_processing/manifest.json \
  --candidate benchmarks/document_processing/observations/docling.jsonl \
  --reference benchmarks/document_processing/observations/reference.jsonl \
  --output benchmarks/document_processing/reports/docling.json \
  --enforce-baseline
```

If `--reference` is omitted, the runner uses and verifies
`manifest.observation_sets.reference`. Run once per parser/configuration; reports stay
comparable because every run uses the same pinned manifest and reference observations.

Exit code `0` means all configured gates passed, `1` means the report was produced but
one or more gates failed, and `2` means inputs were invalid or the report could not be
written. The JSON report is still produced for quality/performance failures (exit `1`).
