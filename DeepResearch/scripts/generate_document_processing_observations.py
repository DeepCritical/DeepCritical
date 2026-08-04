"""Generate benchmark candidate observations from persisted processing state."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from DeepResearch.src.document_processing.benchmark import (
    BenchmarkError,
    generate_candidate_observations,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Project immutable DocumentArtifact, ProcessingRun, DoclingDocument, and "
            "ContentSpan records from a local CAS into benchmark candidate "
            "observations. No component is called and no corpus is downloaded."
        )
    )
    parser.add_argument("manifest", help="Path to the benchmark manifest JSON")
    parser.add_argument(
        "--cas",
        required=True,
        help="Root of the document-processing content-addressed store",
    )
    parser.add_argument(
        "--output",
        default="-",
        help="Candidate observation JSON path, or '-' for stdout (default: '-')",
    )
    parser.add_argument(
        "--source-artifact",
        choices=("pdf", "jats"),
        default="pdf",
        help="Manifest artifact to correlate with CAS records (default: pdf)",
    )
    parser.add_argument(
        "--component-id",
        default="docling",
        help="Persisted primary processing component to select (default: docling)",
    )
    selectors = parser.add_mutually_exclusive_group()
    selectors.add_argument(
        "--configuration-hash",
        default=None,
        help=(
            "Select an exact per-invocation component configuration SHA-256; this "
            "usually differs for every source because it includes input identity"
        ),
    )
    selectors.add_argument(
        "--output-policy-hash",
        default=None,
        help=(
            "Select one exact static output-policy SHA-256 across the corpus "
            "(recommended for comparable benchmark runs)"
        ),
    )
    parser.add_argument(
        "--enforce-baseline",
        action="store_true",
        help=(
            "Require 50-75 verified reusable PMC pairs and coverage of every "
            "required document category"
        ),
    )
    return parser


def _write_observations(payload: dict[str, object], destination: str) -> None:
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if destination == "-":
        sys.stdout.write(serialized)
        return
    output_path = Path(destination).expanduser().resolve()
    try:
        output_path.write_text(serialized, encoding="utf-8")
    except OSError as exc:
        raise BenchmarkError(
            f"cannot write candidate observations {output_path}: {exc}"
        ) from exc


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        observations = generate_candidate_observations(
            args.manifest,
            args.cas,
            source_artifact=args.source_artifact,
            component_id=args.component_id,
            configuration_hash=args.configuration_hash,
            output_policy_hash=args.output_policy_hash,
            enforce_baseline=args.enforce_baseline,
        )
        _write_observations(observations, args.output)
    except BenchmarkError as exc:
        print(
            f"document-processing observation generation error: {exc}",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
