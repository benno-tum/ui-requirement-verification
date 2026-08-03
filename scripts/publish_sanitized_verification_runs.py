from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
PRIVATE_FIELDS = {"ocr_text", "ocr_word_boxes", "visible_text", "matched_text"}
PRIVATE_SCREEN_FIELDS = {"metadata", "screen_summary", "sources", *PRIVATE_FIELDS}
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


def _sanitize(value: Any, *, in_screen_representation: bool = False) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, child in value.items():
            if key in PRIVATE_FIELDS:
                continue
            if in_screen_representation and key in PRIVATE_SCREEN_FIELDS:
                continue
            cleaned[key] = _sanitize(child)
        return cleaned
    if isinstance(value, list):
        return [_sanitize(item, in_screen_representation=in_screen_representation) for item in value]
    if isinstance(value, str):
        value = EMAIL_RE.sub("[redacted-email]", value)
        if value.startswith("/"):
            path = Path(value)
            try:
                return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()
            except ValueError:
                return path.name
    return value


def sanitize_run(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned = _sanitize(payload)
    representations = payload.get("screen_representations")
    if isinstance(representations, list):
        cleaned["screen_representations"] = [
            _sanitize(item, in_screen_representation=True) for item in representations
        ]
    return cleaned


def publish_directory(source: Path, destination: Path) -> int:
    files = sorted(source.glob("[0-9][0-9]_*.json"))
    if len(files) != 13:
        raise ValueError(f"Expected 13 flow files in {source}, found {len(files)}")
    destination.mkdir(parents=True, exist_ok=True)
    total_results = 0
    for source_file in files:
        payload = json.loads(source_file.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise ValueError(f"Invalid verification run: {source_file}")
        if payload.get("metadata", {}).get("run_valid") is False:
            raise ValueError(f"Refusing to publish invalid run: {source_file}")
        total_results += len(payload["results"])
        destination_file = destination / source_file.name
        destination_file.write_text(
            json.dumps(sanitize_run(payload), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    if total_results != 258:
        raise ValueError(f"Expected 258 results in {source}, found {total_results}")
    return total_results


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish a sanitized, complete 13-flow verification run set.")
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    count = publish_directory(args.source, args.destination)
    print(f"published: {args.destination} ({count} results)")


if __name__ == "__main__":
    main()
