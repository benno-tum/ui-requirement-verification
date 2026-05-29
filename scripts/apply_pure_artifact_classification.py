#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_ROOT = BASE_DIR / "data" / "generated" / "pure_ui_dataset"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply GUI/non-GUI classifications to generated PURE artifact manifests."
    )
    parser.add_argument(
        "--classification",
        type=Path,
        required=True,
        help="JSONL file with artifact_id, label, confidence, rationale, and usable_for_requirement_evidence.",
    )
    parser.add_argument(
        "--manifest-root",
        type=Path,
        default=DEFAULT_MANIFEST_ROOT,
        help="Root directory containing PURE artifact_manifest.json files.",
    )
    return parser.parse_args()


def load_classifications(path: Path) -> dict[str, dict[str, Any]]:
    classifications: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            artifact_id = item.get("artifact_id")
            if not isinstance(artifact_id, str) or not artifact_id.strip():
                raise ValueError(f"Missing artifact_id in {path}:{line_number}")
            if artifact_id in classifications:
                raise ValueError(f"Duplicate artifact_id in classification file: {artifact_id}")
            classifications[artifact_id] = item
    return classifications


def artifact_classification_id(flow_id: str, index: int) -> str:
    return f"{flow_id}__artifact_{index:04d}"


def apply_to_manifest(
    path: Path,
    classifications: dict[str, dict[str, Any]],
    *,
    classification_path: Path,
) -> tuple[int, int, int]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    flow_id = manifest["flow_id"]
    artifacts = manifest.get("artifacts", [])
    matched = 0
    gui = 0
    non_gui = 0

    for index, artifact in enumerate(artifacts, start=1):
        classification_id = artifact_classification_id(flow_id, index)
        classification = classifications.get(classification_id)
        if classification is None:
            continue

        usable = bool(classification.get("usable_for_requirement_evidence", False))
        matched += 1
        gui += int(usable)
        non_gui += int(not usable)

        artifact["classification_id"] = classification_id
        artifact["classification_label"] = classification.get("label")
        artifact["classification_confidence"] = classification.get("confidence")
        artifact["classification_rationale"] = classification.get("rationale")
        artifact["visible_ui_elements"] = classification.get("visible_ui_elements", [])
        artifact["usable_for_requirement_evidence"] = usable
        artifact["classification_notes"] = classification.get("notes") or None

    manifest["artifact_classification"] = {
        "source_file": str(path_for_metadata(classification_path)),
        "matched_artifacts": matched,
        "gui_artifacts": gui,
        "non_gui_artifacts": non_gui,
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return matched, gui, non_gui


def path_for_metadata(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except ValueError:
        return str(path)


def main() -> None:
    args = parse_args()
    classifications = load_classifications(args.classification)

    manifest_paths = sorted(args.manifest_root.glob("*/artifact_manifest.json"))
    total_matched = 0
    total_gui = 0
    total_non_gui = 0
    for manifest_path in manifest_paths:
        matched, gui, non_gui = apply_to_manifest(
            manifest_path,
            classifications,
            classification_path=args.classification,
        )
        total_matched += matched
        total_gui += gui
        total_non_gui += non_gui

    print(
        "Applied PURE artifact classification to "
        f"{len(manifest_paths)} manifests: {total_matched} matched, "
        f"{total_gui} GUI, {total_non_gui} non-GUI."
    )


if __name__ == "__main__":
    main()
