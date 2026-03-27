#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from ui_verifier.requirement_inspection.pure_loader import (
    extract_pure_requirement_statements_from_dir,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract requirement statements from PURE XML files."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing PURE XML files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output path. Supported: .csv or .jsonl",
    )
    return parser.parse_args()


def write_csv(output_path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = ["doc_id", "req_id", "requirement_text"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(output_path: Path, rows: list[dict[str, str]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    args = parse_args()

    statements = extract_pure_requirement_statements_from_dir(args.input_dir)
    rows = [
        {
            "doc_id": statement.doc_id,
            "req_id": statement.req_id,
            "requirement_text": statement.requirement_text,
        }
        for statement in statements
    ]

    suffix = args.output.suffix.lower()
    if suffix == ".csv":
        write_csv(args.output, rows)
    elif suffix == ".jsonl":
        write_jsonl(args.output, rows)
    else:
        raise ValueError(f"Unsupported output format: {args.output}")

    print(f"Extracted {len(rows)} requirement statements to {args.output}")


if __name__ == "__main__":
    main()
