from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = BASE_DIR / "artifacts/thesis_evaluation"
TEXT_SUFFIXES = {".csv", ".json", ".jsonl", ".md", ".txt", ".yaml", ".yml"}
ABSOLUTE_PATH_PATTERNS = (
    re.compile(r"/Users/[^\s\"']+"),
    re.compile(r"/home/[^\s\"']+"),
    re.compile(r"[A-Za-z]:\\\\Users\\\\[^\s\"']+"),
)
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?:api[_-]?key|authorization|bearer[_-]?token|access[_-]?token)[\"']?"
    r"\s*[=:]\s*[\"']?(?!your_|redacted|<)[A-Za-z0-9._/+:-]{8,}"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reject secrets and personal absolute paths in the curated thesis package."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--manifest-name", default="artifact_manifest.json")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit(root: Path, *, manifest_name: str) -> dict[str, Any]:
    if not root.is_dir():
        raise FileNotFoundError(root)
    findings: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root)
        if relative.as_posix() == manifest_name:
            continue
        files.append(
            {
                "path": relative.as_posix(),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
        )
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in ABSOLUTE_PATH_PATTERNS:
            match = pattern.search(text)
            if match:
                findings.append(
                    {
                        "path": relative.as_posix(),
                        "kind": "absolute_personal_path",
                        "example": match.group(0)[:160],
                    }
                )
        if SECRET_ASSIGNMENT.search(text):
            findings.append(
                {
                    "path": relative.as_posix(),
                    "kind": "possible_secret_assignment",
                    "example": "redacted",
                }
            )
    return {
        "schema_version": "thesis_replication_artifact_manifest_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root": root.name,
        "files": files,
        "findings": findings,
        "release_gate_passed": not findings,
    }


def main() -> None:
    args = parse_args()
    result = audit(args.root, manifest_name=args.manifest_name)
    if not args.check_only:
        output = args.root / args.manifest_name
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"manifest={output}")
    print(f"files={len(result['files'])} findings={len(result['findings'])}")
    if result["findings"]:
        raise SystemExit("Replication package release gate failed.")


if __name__ == "__main__":
    main()
