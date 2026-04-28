#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from ui_verifier.requirement_inspection.annotation_sheet import (
    load_pure_requirement_candidates,
    write_blank_pure_candidate_annotation_sheet,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a blank annotation sheet from context-aware PURE requirement candidates in JSONL format."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to the PURE candidate JSONL file produced by extract_pure_requirement_candidates.py.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to the output CSV annotation sheet.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for the number of candidates to include.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidates = load_pure_requirement_candidates(args.input)
    write_blank_pure_candidate_annotation_sheet(candidates, args.output, limit=args.limit)

    with args.output.open("r", encoding="utf-8", newline="") as handle:
        row_count = sum(1 for _ in csv.DictReader(handle))
    print(f"Wrote PURE candidate annotation sheet with {row_count} rows to {args.output}")


if __name__ == "__main__":
    main()
