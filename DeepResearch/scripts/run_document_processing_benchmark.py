"""Run the reusable scientific document-processing bake-off offline."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from DeepResearch.src.document_processing.benchmark import (
    BenchmarkError,
    run_benchmark,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare parser observations with a pinned JATS/PDF reference corpus. "
            "No documents are downloaded and no parser service is called."
        )
    )
    parser.add_argument("manifest", help="Path to the benchmark manifest JSON")
    parser.add_argument(
        "--candidate",
        required=True,
        help="Candidate parser observations in JSON or JSONL format",
    )
    parser.add_argument(
        "--reference",
        default=None,
        help=(
            "Reference observations in JSON or JSONL format. If omitted, use the "
            "hashed manifest observation_sets.reference artifact."
        ),
    )
    parser.add_argument(
        "--output",
        default="-",
        help="Machine-readable report path, or '-' for stdout (default: '-')",
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


def _write_report(report: dict[str, object], destination: str) -> None:
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if destination == "-":
        sys.stdout.write(serialized)
        return
    output_path = Path(destination).expanduser().resolve()
    try:
        output_path.write_text(serialized, encoding="utf-8")
    except OSError as exc:
        raise BenchmarkError(f"cannot write report {output_path}: {exc}") from exc


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        report = run_benchmark(
            args.manifest,
            args.candidate,
            args.reference,
            enforce_baseline=args.enforce_baseline,
        )
        _write_report(report, args.output)
    except BenchmarkError as exc:
        print(f"document-processing benchmark error: {exc}", file=sys.stderr)
        return 2
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
