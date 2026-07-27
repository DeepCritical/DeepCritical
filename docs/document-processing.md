# Scientific document processing

DeepCritical uses established parsers and owns only routing, provenance,
quality enforcement, storage, and alignment. PDF parsing, OCR, layout analysis,
table extraction, and scholarly reference parsing are not reimplemented in the
application.

## Runtime stack

| Component | Pinned runtime | Purpose |
| --- | --- | --- |
| Docling Serve | `quay.io/docling-project/docling-serve-cpu:v1.21.0` | Primary conversion to a serialized `DoclingDocument` |
| GROBID | `deepcritical/grobid:0.9.0-full-p0-c2` (from `grobid/grobid:0.9.0-full`) | Scholarly metadata, bibliography, citation links, and TEI |
| Caddy | `caddy:2.11.4-alpine` | Authenticated loopback boundary in front of GROBID |
| Redis | `redis:7.2.14-alpine3.21` | Durable RQ queue and short-lived Docling results |
| OCRmyPDF | `jbarlow83/ocrmypdf:v17.4.1` | Searchable PDF derivative for image-only inputs |
| Tesseract | Version bundled by the pinned OCRmyPDF image | OCR engine; record its runtime version in every OCR processing run |
| pypdf | `6.14.2` in `uv.lock` | Bounded PDF structure, encryption, and page-count preflight; it is not a content extractor |

These tags are intentionally explicit. Do not replace them with `latest` or
`main`. Compose additionally requires approved registry digests, runs with
`pull_policy: never`, and defaults to `linux/amd64`; a tag alone is not a
production pin. The source references are the official [Docling Serve deployment and
configuration documentation](https://docling-project.github.io/docling/usage/api_server/deployment/),
[GROBID container documentation](https://grobid.readthedocs.io/en/latest/Grobid-docker/),
[Caddy request-matcher and reverse-proxy documentation](https://caddyserver.com/docs/caddyfile/matchers),
[Redis official image](https://hub.docker.com/_/redis), and [OCRmyPDF container
documentation](https://ocrmypdf.readthedocs.io/en/latest/docker.html).
The exact releases/tags can be checked at [Docling Serve
v1.21.0](https://github.com/docling-project/docling-serve/tree/v1.21.0),
[GROBID 0.9.0](https://github.com/grobidOrg/grobid/releases/tag/0.9.0),
[Redis `7.2.14-alpine3.21`](https://hub.docker.com/_/redis/tags?name=7.2.14-alpine3.21),
and [OCRmyPDF v17.4.1](https://github.com/ocrmypdf/OCRmyPDF/releases/tag/v17.4.1).

The compose file does not invent registry digests. Operators must mirror or
pre-pull the approved images, verify their registry digests, and supply those
digests explicitly. Configuration values are expectations only: they never
count as observed runtime identity.

## Data flow and representation

1. Run bounded preflight before parser submission. Oversized, encrypted,
   malformed, symlinked, and over-page-limit inputs become explicit quarantine
   outcomes with machine-readable diagnostics. Paths rejected before safe
   ingestion get a durable, bounded `IntakeQuarantineRecord`; their source bytes
   are not copied into the artifact store or read into application memory.
2. Store the exact acquired bytes in content-addressed storage before parsing.
3. Prefer native JATS/NXML. Preserve it unchanged and convert it with Docling.
4. Preserve native BioC XML/JSON unchanged and import it through the BioC
   adapter. BioC document/passage indexes and character ranges are aligned to
   Docling items as stable `ContentSpan` locators. BioC remains an
   interchange/annotation representation, not the archive.
5. Submit other supported formats to Docling and preserve the lossless
   `DoclingDocument` JSON returned by the pinned service. HTML, Office, and
   image text receives a `docling_item` locator into that immutable tree. This
   is intentionally labelled parser-native rather than pretending it is a
   source XPath, Office object ID, or image coordinate.
6. For every PDF, run Docling on the original and GROBID for scholarly TEI.
   Page-level provenance-backed text counts identify image-only inputs; those
   inputs get a recorded OCRmyPDF derivative even if raw GROBID text appears
   usable. Submit the derivative to GROBID, but never replace or edit the source
   PDF.
7. Store GROBID TEI unchanged. Alignment produces a separate overlay referring
   to Docling item references, including person-name author identities and
   affiliations; an unaligned item remains an explicit diagnostic.
8. Persist a second integrity overlay with one outcome for every Docling table
   and figure and every GROBID bibliographic citation. Caption/citation targets
   must resolve to existing Docling items or remain explicitly unaligned.
9. Treat every supplement as its own artifact, linked to its parent and routed
   according to its detected media type.

Every transformation creates a new `ProcessingRun`. `complete`, `partial`,
`quarantined`, and `failed` are the only terminal outcomes. A process exit code
of zero is not enough: empty output, missing lineage, or geometry below the
configured threshold must be diagnosed and cannot become a silent success.

Docling output is an immutable native product, not DeepCritical's permanent
canonical representation. Every evidence span uses a `RepresentationAnchor`
that identifies the exact representation product, native node, and character
range. The project-owned `CanonicalDocumentView` described in
[ADR 0001](adr/0001-project-owned-canonical-document-view.md) will be introduced
separately through native-output adapters.

Durable records use descriptive `schema_version` values and every stage output
is a typed `DataProductRef`. A product reference carries its content hash, CAS
URI, byte size, media and payload schema, producer run, and source-artifact
lineage. Record loading dispatches on the schema version before model
validation. Stores containing the old unversioned `records/parser_runs`
prototype layout are rejected explicitly rather than guessed into the new
contract.

The default configuration is in
`configs/document_processing/default.yaml`. In particular, at least 95% of
PDF-derived textual items must have valid page/bounding-box provenance.

Process or resume one artifact from the repository root:

```bash
uv run deepcritical-process-document path/to/paper.pdf --check-services
uv run deepcritical-process-document --artifact-id artifact-...
```

The command prints a JSON summary. Raw inputs, parser-native outputs, evidence
spans, explicit unaligned overlays, diagnostics, and terminal runs remain in the
configured content-addressed store. Async Docling task IDs are checkpointed
before polling, so an interrupted command resumes the submitted remote task
instead of silently submitting it again. Docling results remain re-readable
until their four-hour RQ TTL expires, covering a crash after the result is fetched
but before its raw response, normalized output, and `ProcessingRun` are durable.

## Start the local services

Linux containers are the production target. Docker Desktop on Windows must be
configured for Linux containers. From the repository root:

```bash
export DOCLING_API_KEY="replace-with-a-random-local-secret"
export GROBID_API_KEY="replace-with-a-different-random-local-secret"
export REDIS_PASSWORD="replace-with-a-different-random-local-secret"
export DOCLING_IMAGE_DIGEST="sha256:replace-with-approved-registry-digest"
export REDIS_IMAGE_DIGEST="sha256:replace-with-approved-registry-digest"
export CADDY_IMAGE_DIGEST="sha256:replace-with-approved-registry-digest"
export OCRMYPDF_IMAGE_DIGEST="sha256:replace-with-approved-registry-digest"
export GROBID_BASE_DIGEST="sha256:replace-with-approved-registry-digest"
export GROBID_IMAGE_DIGEST="sha256:replace-with-approved-derived-image-digest"
export GROBID_IMAGE_REPOSITORY="your-approved-registry.example/deepcritical/grobid"

# Pull exact immutable references before compose enforces pull_policy: never.
docker pull "quay.io/docling-project/docling-serve-cpu:v1.21.0@${DOCLING_IMAGE_DIGEST}"
docker pull "redis:7.2.14-alpine3.21@${REDIS_IMAGE_DIGEST}"
docker pull "caddy:2.11.4-alpine@${CADDY_IMAGE_DIGEST}"
docker pull "jbarlow83/ocrmypdf:v17.4.1@${OCRMYPDF_IMAGE_DIGEST}"
docker pull "grobid/grobid:0.9.0-full@${GROBID_BASE_DIGEST}"
docker compose -f docker/document-processing/compose.yaml config
# Build, scan, and publish the fixed c2 derivative first. Record the published
# manifest digest as GROBID_IMAGE_DIGEST; the runtime service never uses its tag alone.
docker compose -f docker/document-processing/compose.yaml --profile build build grobid-build
docker push "${GROBID_IMAGE_REPOSITORY}:0.9.0-full-p0-c2"
docker pull "${GROBID_IMAGE_REPOSITORY}:0.9.0-full-p0-c2@${GROBID_IMAGE_DIGEST}"
docker compose -f docker/document-processing/compose.yaml up -d
docker compose -f docker/document-processing/compose.yaml ps
```

Set the matching GROBID repository/tag and `sha256:` digest in the application
configuration as well. Compose's digest environment variables pin what runs;
the application values are independent expectations checked against the
task-bound runtime attestation.

Use independently generated 32-byte-or-longer URL-safe values for these
variables (for example, values produced by a secrets manager). Placeholder,
short, missing, or whitespace-containing parser API keys fail before intake.

The images are large. The default budget is one Docling worker with 4 CPUs and
8 GiB RAM, GROBID with 4 CPUs and 8 GiB RAM, a small API process, and Redis.
Override the `*_CPUS` and `*_MEMORY` variables only after running the benchmark.
Scale conversion workers explicitly:

```bash
docker compose -f docker/document-processing/compose.yaml up -d --scale docling-worker=2
```

Docling model files come only from the digest-addressed image. No model-cache
volume is mounted, so stale or mutable volume bytes cannot shadow the image-baked
inventory independently of the image digest. Redis uses an AOF-backed named
volume so queued state survives an ordinary restart. `docker compose down`
retains that volume; `down -v` destroys it and must not be used during incident
recovery.

## Local endpoints and health

Only the authenticated Docling and GROBID-proxy APIs are published, and both
bind to host loopback. The GROBID JVM and Redis are not published. The parser
network is marked internal, so a parser cannot reach publisher URLs or managed
APIs. DeepCritical uploads already-acquired bytes; it does not ask a parser to
fetch arbitrary URLs. Compose refuses to start until all three non-default
secrets are supplied. The reusable clients and CLI refuse missing, short, or known
placeholder API keys before opening a parser connection.

| Endpoint | Use |
| --- | --- |
| `http://127.0.0.1:5001/ready` | Docling readiness; requires `X-Api-Key` |
| `http://127.0.0.1:5001/version` | Docling component versions; requires `X-Api-Key` |
| `POST http://127.0.0.1:5001/v1/convert/file/async` | Submit an uploaded document |
| `GET http://127.0.0.1:5001/v1/status/poll/{task_id}` | Poll an asynchronous conversion |
| `http://127.0.0.1:8070/api/version` | GROBID health and runtime version; requires `X-API-Key` at the proxy |
| `POST http://127.0.0.1:8070/api/processFulltextDocument` | Parse a PDF to TEI; requires `X-API-Key` at the proxy |

Smoke-test the services without sending a document:

```bash
curl --fail -H "X-Api-Key: ${DOCLING_API_KEY}" http://127.0.0.1:5001/ready
curl --fail -H "X-Api-Key: ${DOCLING_API_KEY}" http://127.0.0.1:5001/version
curl --fail -H "X-API-Key: ${GROBID_API_KEY}" http://127.0.0.1:8070/api/version
docker compose -f docker/document-processing/compose.yaml logs --tail=100 docling-api docling-worker grobid grobid-proxy
```

All Docling JSON responses, including asynchronous status/result responses, and
all GROBID TEI responses are read under configurable byte ceilings. The checked-in
defaults are 256 MiB (`services.docling.max_response_bytes`) and 128 MiB
(`services.grobid.max_response_bytes`). A declared or streamed body above its
ceiling becomes an explicit `*_RESPONSE_TOO_LARGE` failed processing run; operators
may raise the limit in a reviewed deployment override for unusually large papers.

## Opt-in live compatibility contracts

The normal pytest suite never contacts parser services or starts containers.
`test_live_stack_contract.py` is marked `document_processing_live` and is
skipped unless `DEEPCRITICAL_RUN_LIVE_DOCUMENT_PROCESSING=1` is present before
pytest starts. It generates small synthetic PDFs in memory; no PMC, licensed,
or benchmark document is uploaded.

With the digest-pinned compose stack already healthy, run the Docling and
GROBID contracts explicitly:

```bash
export DEEPCRITICAL_RUN_LIVE_DOCUMENT_PROCESSING=1
export DEEPCRITICAL_LIVE_DOCLING_API_KEY="${DOCLING_API_KEY}"
export DEEPCRITICAL_LIVE_GROBID_API_KEY="${GROBID_API_KEY}"
# These default to the compose loopback ports and are only needed for overrides.
export DEEPCRITICAL_LIVE_DOCLING_URL="http://127.0.0.1:5001"
export DEEPCRITICAL_LIVE_GROBID_URL="http://127.0.0.1:8070"
# Version expectations default to the checked-in pins and may be set explicitly:
export DEEPCRITICAL_LIVE_EXPECTED_DOCLING_VERSION="2.113.0"
export DEEPCRITICAL_LIVE_EXPECTED_DOCLING_SERVE_VERSION="1.21.0"
export DEEPCRITICAL_LIVE_EXPECTED_GROBID_VERSION="0.9.0"

uv run pytest tests/test_document_processing/test_live_stack_contract.py \
  -m document_processing_live -q
```

This calls Docling readiness/version endpoints, submits and polls a real async
conversion, validates the returned serialized `DoclingDocument`, calls GROBID
alive/version endpoints, and validates a real `processFulltextDocument` TEI
response. Missing credentials, unreachable services, incompatible response
shapes, and service errors fail the opted-in lane rather than becoming skips.

OCR is a separate opt-in because it requires a local Linux-container runtime
and the approved image to have been pre-pulled. Enable it with the exact
digest-addressed reference used by the deployment:

```bash
export DEEPCRITICAL_RUN_LIVE_DOCUMENT_PROCESSING_OCR=1
export DEEPCRITICAL_LIVE_OCR_IMAGE="jbarlow83/ocrmypdf:v17.4.1@${OCRMYPDF_IMAGE_DIGEST}"
export DEEPCRITICAL_LIVE_CONTAINER_RUNTIME="docker"

uv run pytest tests/test_document_processing/test_live_stack_contract.py \
  -m document_processing_live -q
```

When requested, the OCR contract fails closed if the runtime or exact
`image@sha256:...` reference is missing. The runner uses `--pull=never`, probes
the OCRmyPDF and Tesseract versions inside the pinned image, processes a
generated raster-only PDF, and validates the searchable derivative and local
runtime attestation. Until this OCR opt-in passes on the approved Linux target,
container/OCR compatibility remains an explicit deployment acceptance gate.

These are compatibility contracts, not the 50–75-document quality bake-off;
they do not replace corpus accuracy, resource-accounting, or task-bound service
attestation acceptance.

Docling's UI, custom VLM configuration, external plugins, remote model services,
and detailed internal errors are disabled. The API and worker use the official
Redis-backed RQ engine. The API alone cannot process a job; at least one healthy
`docling-worker` is required.

## OCR derivative operation

OCRmyPDF is an ephemeral, network-isolated CLI. Its own documentation warns
that the bundled example web wrapper is a demonstration without production
security or load controls, so this deployment does not expose it as a service.
The application should stream an immutable original to stdin and capture a new
derivative from stdout. A manual Linux/WSL smoke test is:

```bash
docker compose -f docker/document-processing/compose.yaml --profile tools run --rm -T \
  ocrmypdf --skip-text --rotate-pages --deskew --jobs 2 --output-type pdf --optimize 1 - - \
  < original.pdf > searchable-derivative.pdf
```

Never use the same path for input and output. Hash and store the derivative,
create a child `DocumentArtifact` that points to the original, and record both
the OCRmyPDF and Tesseract versions:

```bash
docker compose -f docker/document-processing/compose.yaml --profile tools run --rm ocrmypdf --version
docker compose -f docker/document-processing/compose.yaml --profile tools run --rm --entrypoint tesseract ocrmypdf --version
```

## Provenance and recovery

For every processing run, retain ordered typed inputs and outputs, the source
artifact lineage, exact configuration and policy hashes, component descriptor,
container image reference and observed image digest, component/model versions,
timestamps, warnings, resource usage, and transformation lineage. Component
scratch files and RQ results are staging data only; copy raw outputs to
content-addressed storage before acknowledging completion.

The persisted static output policy also records the effective GROBID coordinates
and consolidation flags, OCR languages/rotation/deskew/jobs/optimization, and
parser execution limits. Changing an injected client setting therefore changes
the corpus-wide policy hash even when `DocumentProcessingConfig` itself is unchanged.

### Peak-memory provenance

`peak_memory_bytes` is scoped to the maximum heavy parser stage (Docling, GROBID,
or OCRmyPDF), not the full coordinating Python process. Alignment wall time remains
included, while the alignment run and its memory-exclusion reason are recorded in
resource provenance. A value is benchmark-comparable only when its accompanying
`MemoryMeasurement` records an exclusive invocation-owned or fresh single-job
service Linux cgroup-v2 boundary using `cgroup-v2-memory.peak`, a positive peak,
a non-PII environment hash, and no `oom_kill` event. The record must include start/finish
timestamps and explicitly confirm that shared-service overhead was excluded. A
numeric legacy field without this evidence remains readable for historical
reporting but cannot satisfy an enforced bake-off baseline.

The CLI can wire two kinds of trustworthy accounting from
`configs/document_processing/default.yaml`:

- Docling and GROBID each accept an authenticated `memory_reporter` adapter. It
  resolves `GET /v1/measurements/{component_id}/{task_or_request_id}` after the
  parser result is available. Docling uses the durable RQ task ID. GROBID sends
  a fresh `X-DeepCritical-Invocation-ID` through its proxy and resolves that
  exact request ID. The client rejects a report whose `measurement_id` differs.
- OCRmyPDF accepts a `memory_meter` backed by a pre-delegated Linux cgroup-v2
  subtree. Local OCR starts through a minimal bootstrap that joins the fresh
  cgroup and only then `exec`s OCRmyPDF, avoiding a post-spawn accounting race.
  Container OCR passes the fresh child boundary to Docker with
  `--cgroup-parent`; it does not incorrectly measure the short-lived Docker CLI.

Do not substitute client RSS, `docker stats`, or a shared service cgroup. The
remote reporter is a contract for a separately instrumented, trusted deployment
supervisor; the standard compose stack does not pretend to implement that
privileged host function. The supervisor must create/reset a fresh exclusive
boundary for the named task/request, persist `memory.peak` plus `memory.events`,
and return the strict `MemoryMeasurement` JSON only after the work has ended.
The endpoint must require a non-default `X-API-Key`, and remains loopback-only
unless external parser endpoints have been explicitly approved.

OCR metering requires Linux cgroup v2, a writable delegated child below
`/sys/fs/cgroup` (never the root), the memory controller, and an OCI runtime
using a cgroupfs-compatible `--cgroup-parent` value for container mode. Configure
`services.ocr.memory_meter.cgroup_v2_parent` with the host filesystem path and
`environment_sha256` with a reviewed non-PII hash of the measurement environment
(kernel, runtime/cgroup driver, CPU and memory limits, and image identity). Do
not grant the application broad write access to the host cgroup root.

Missing accounting is optional when a development override sets
`quality.memory_measurement_required: false`. Setting it to `true` makes startup fail unless both
remote reporters and the OCR meter are enabled and fully configured. A runtime
report that is missing, invalid, late, or bound to another task remains an
explicit parser failure/partial outcome; it is never converted to zero.

Docling's single-use result mode is disabled deliberately. The application
persists a remote task checkpoint before polling and removes it only after the
parser-native response, normalized output, hashes, and `ProcessingRun` have been
committed to the content-addressed store. If the process stops after fetching a
result but before that commit, the next invocation must be able to fetch the
same result again instead of submitting duplicate parser work.

### Task-bound runtime attestation

The checked-in parser-policy digest and model-hash values are deliberately
`null`/empty: they depend on the approved deployment registry and exact model
cache and must not be invented in source control. Compose independently requires
deployment digest environment variables before it will render. With
`quality.require_runtime_identity: true`, the
CLI fails at startup until all expected digests/model inventories and both
`runtime_attestation_reporter` adapters are configured. Set the flag to `false`
only for an explicitly non-baseline developer run.

Configured values remain expectations. Docling and GROBID runtime identity must
come from an authenticated deployment supervisor at
`GET /v1/attestations/{component_id}/{invocation_id}`. Docling uses its durable
task ID; GROBID uses the same `X-DeepCritical-Invocation-ID` that binds optional
memory evidence. The supervisor must independently inspect the workload image,
installed component versions, and actual model files. It must not echo expected
values supplied by the application. Hash model directories using a sorted
relative-path/file-hash manifest so the result is deterministic.
The reporter also exposes an authenticated `/health` endpoint used by
`process_document.py --check-services`; a healthy reporter is not a substitute
for invocation-bound evidence.

The strict `RuntimeAttestation` and its canonical JSON hash are preserved in
CAS. `ProcessingRun` validates the component, version, invocation ID, container
reference/digest, component versions, model inventory, and observation time
against that evidence. Missing, stale, malformed, or mismatched evidence keeps
the valid parser output but marks the run partial with an explicit diagnostic;
an enforced benchmark rejects it. Non-loopback parser and reporter endpoints
must use HTTPS, and authenticated clients do not follow redirects.

Capture expected identities after pulling/building the approved images, then
place them in a deployment-specific override:

```bash
docker image inspect --format '{{index .RepoDigests 0}}' quay.io/docling-project/docling-serve-cpu:v1.21.0
docker image inspect --format '{{.Id}}' deepcritical/grobid:0.9.0-full-p0-c2
docker image inspect --format '{{index .RepoDigests 0}}' jbarlow83/ocrmypdf:v17.4.1
```

When runtime identity is required, the OCR runner rejects tag-only images and
invokes the exact configured `tag@digest` with `--pull=never`. It records the
actual invocation ID, container name, digest-addressed reference, and OCRmyPDF
and Tesseract versions as a local OCI attestation. A conflicting embedded and
configured digest is rejected before execution. Service-side Docling/GROBID
identity still requires the deployment supervisor because an HTTP client cannot
inspect the remote host container runtime.

An interrupted workflow resumes from persisted artifact and processing-run state.
The Docling task ID is durably checkpointed before polling and is reused until
the parser output, terminal `ProcessingRun`, and its diagnostic manifest are all
durable. A retry therefore reconciles an incomplete local commit without
submitting the heavy parser job again. Re-reading an uncommitted Docling result
is bounded by `DOCLING_SERVE_ENG_RQ_RESULTS_TTL=14400` (four hours). Once that
TTL has expired, the remote result is unavailable and the attempt fails
explicitly; a later invocation may then submit replacement work only after the
terminal remote-task checkpoint has been cleared.
After a restart, inspect the application run state and queue before retrying:

```bash
docker compose -f docker/document-processing/compose.yaml ps
docker compose -f docker/document-processing/compose.yaml logs --since=30m redis docling-worker
```

The four-hour window is a recovery bound, not a records-retention policy.
Completed component outputs and lineage live in the content-addressed store, while
Redis results expire independently. Redis AOF files and host snapshots may still
contain document-derived data after logical expiry, so set backup and deletion
rules appropriate to the source license and data classification.

## Bake-off baseline

The offline harness and manifest contract live in
`benchmarks/document_processing/README.md`. It enforces 50–75 verified,
reusable PMC JATS/PDF pairs, category coverage, source hashes, determinism,
quality metrics, locator coverage, throughput, and memory reporting. The
checked-in manifest is intentionally a schema example; the real baseline cannot
be declared complete until article-specific reuse rights and the corpus bytes
have been reviewed and pinned.

## Security, retention, and licensing gates

- Treat PDFs, XML, Office files, images, and supplements as hostile inputs.
  Enforce byte/page/time limits before submission and quarantine encrypted,
  malformed, oversized, or repeatedly crashing artifacts.
- Keep the services on loopback behind an authenticated application boundary.
  The compose defaults are for one trusted host, not a shared or Internet-facing
  deployment. TLS and a real secret manager are required before remote access.
- Do not put source text, API keys, Redis URLs, or full parser payloads in logs.
  Encrypt the artifact store and backups according to project policy; compose
  does not provide host-level encryption.
- Preserve originals according to acquisition and reuse rights. Scratch data,
  queue results, and failed derivatives need explicit retention periods and
  auditable deletion. Legal deletion of an original must also traverse its
  derivatives, outputs, queue backups, and benchmark copies.
- Docling and Docling Serve code are MIT, but each downloaded/bundled model has
  its own license. Produce an inventory containing model name, source, version,
  hash, license, and redistribution decision before release.
- GROBID code is Apache-2.0 and its image bundles models and a deep-learning
  runtime. OCRmyPDF is MPL-2.0 and bundles components with other licenses,
  including Ghostscript; Tesseract is Apache-2.0. pypdf is BSD-3-Clause.
  Generate an SBOM and complete a dependency/model license review for the exact
  packages and images actually mirrored.
- The repository's conflicting MIT/GPL licensing signals are a release blocker.
  The team must select the authoritative project license before distributing
  DeepCritical or derivative parser images.

## Managed-provider policy

Managed parser adapters may exist for later benchmarks, but all providers are
disabled in the default configuration. There is no implicit external fallback.
P0 exposes only a provider-neutral adapter protocol and result contract; it
ships no managed-provider implementation and never invokes that interface.
No document may be uploaded to Mathpix, Azure Document Intelligence, or another
provider until the team has approved source-license compatibility, data
classification, region, retention, training-use, deletion, incident-response,
and vendor-contract requirements. Enabling a provider must be an explicit,
audited configuration change that creates its own processing run.

The self-hosted parser URLs are also restricted to host-loopback addresses by
default. Setting `security.allow_external_parser_endpoints: true` is an explicit
document-upload policy decision and requires the same licensing, retention, and
data-handling review; changing a URL alone never enables an implicit fallback.

## Open team decisions

- Approve whether any licensed full text may be sent to a managed parser and,
  if so, which providers, regions, retention terms, and deletion guarantees are
  acceptable.
- Select the languages that beta must evaluate beyond the initial English
  baseline, including required OCR language packs and accuracy targets.
- Enumerate non-paper supplement formats beta must support (for example CSV,
  source data archives, videos, or domain-specific instrument output).
- Decide whether beta requires semantic interpretation of scientific figures
  and charts, or only faithful extraction of images, captions, geometry, and
  relationships.
- Resolve the repository's conflicting license signals and approve the exact
  parser-container/model license inventory before distribution.
