#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ui_verifier.requirement_inspection.pure_loader import (
    extract_pure_requirement_candidates_from_dir,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract context-aware PURE requirement candidates from XML files."
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
        help="Output .jsonl path for extracted requirement candidates.",
    )
    parser.add_argument(
        "--no-structural-fallback",
        action="store_true",
        help="Only emit explicit <req> requirements.",
    )
    parser.add_argument(
        "--minimum-text-length",
        type=int,
        default=20,
        help="Minimum normalized text length for structural fallback candidates.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidates = extract_pure_requirement_candidates_from_dir(
        args.input_dir,
        include_structural_fallback=not args.no_structural_fallback,
        minimum_text_length=args.minimum_text_length,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for candidate in candidates:
            handle.write(json.dumps(candidate.to_dict(), ensure_ascii=False) + "\n")

    print(f"Extracted {len(candidates)} PURE requirement candidates to {args.output}")


if __name__ == "__main__":
    main()
