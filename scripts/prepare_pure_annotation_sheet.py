#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from ui_verifier.requirement_inspection.annotation_sheet import (
    load_requirement_statements,
    write_blank_annotation_sheet,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a blank annotation sheet from requirement statements in CSV or JSONL format."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to a CSV or JSONL file with doc_id, req_id, requirement_text.",
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
        help="Optional limit for the number of statements to include.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    statements = load_requirement_statements(args.input)
    write_blank_annotation_sheet(statements, args.output, limit=args.limit)
    print(f"Wrote annotation sheet with {min(len(statements), args.limit) if args.limit else len(statements)} rows to {args.output}")


if __name__ == "__main__":
    main()
