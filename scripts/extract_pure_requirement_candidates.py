#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ui_verifier.requirement_inspection.pure_loader import (
    extract_pure_requirement_candidates_from_dir,
)
from ui_verifier.requirement_inspection.pure_pdf_loader import (
    extract_pure_pdf_requirement_candidates_from_dir,
    extract_pure_pdf_requirement_candidates_from_file,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract context-aware PURE requirement candidates from XML or PDF files."
    )
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument(
        "--input",
        type=Path,
        help="PURE PDF file, XML directory, or PDF directory.",
    )
    inputs.add_argument(
        "--input-dir",
        type=Path,
        help="Legacy alias for a directory containing PURE XML files.",
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
    input_path = args.input or args.input_dir
    assert input_path is not None
    extraction_kwargs = {
        "include_structural_fallback": not args.no_structural_fallback,
        "minimum_text_length": args.minimum_text_length,
    }
    if input_path.is_file():
        if input_path.suffix.lower() != ".pdf":
            raise ValueError("--input file must be a PDF; use a directory for PURE XML input.")
        candidates = extract_pure_pdf_requirement_candidates_from_file(input_path, **extraction_kwargs)
    elif args.input_dir is not None:
        candidates = extract_pure_requirement_candidates_from_dir(input_path, **extraction_kwargs)
    else:
        pdf_files = sorted(input_path.rglob("*.pdf"))
        xml_files = sorted(input_path.rglob("*.xml"))
        if pdf_files and xml_files:
            raise ValueError("Mixed PDF/XML directories are ambiguous; pass a format-specific subdirectory.")
        if pdf_files:
            candidates = extract_pure_pdf_requirement_candidates_from_dir(input_path, **extraction_kwargs)
        else:
            candidates = extract_pure_requirement_candidates_from_dir(input_path, **extraction_kwargs)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for candidate in candidates:
            handle.write(json.dumps(candidate.to_dict(), ensure_ascii=False) + "\n")

    print(f"Extracted {len(candidates)} PURE requirement candidates to {args.output}")


if __name__ == "__main__":
    main()
