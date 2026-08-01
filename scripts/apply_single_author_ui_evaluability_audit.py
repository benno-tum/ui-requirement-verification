from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT = (
    BASE_DIR
    / "data/annotations/evaluation_audits/single_author_final_20260725"
    / "ui_evaluability_disagreement_audit_form.json"
)
DEFAULT_VERIFICATION_ROOT = BASE_DIR / "data/annotations/verification_gold"
DEFAULT_GOLD_ROOT = BASE_DIR / "data/annotations/requirements_gold"
DEFAULT_CANDIDATE_ROOT = BASE_DIR / "data/annotations/requirements_candidate"
UI_LABELS = {
    "UI_VERIFIABLE",
    "PARTIALLY_UI_VERIFIABLE",
    "NOT_UI_VERIFIABLE",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or apply completed single-author UI-evaluability reinspection "
            "decisions to verification gold and matching requirement records."
        )
    )
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--verification-root", type=Path, default=DEFAULT_VERIFICATION_ROOT)
    parser.add_argument("--gold-root", type=Path, default=DEFAULT_GOLD_ROOT)
    parser.add_argument("--candidate-root", type=Path, default=DEFAULT_CANDIDATE_ROOT)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_record(document: dict[str, Any], collection: str, requirement_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in document.get(collection, [])
            if item.get("requirement_id") == requirement_id
        ),
        None,
    )


def reviewed_evidence_steps(decision: dict[str, Any]) -> list[int]:
    steps = {int(step) for step in decision.get("step_indices") or []}
    for screenshot in decision.get("ordered_screenshots") or []:
        match = re.search(r"step_(\d+)\.png$", str(screenshot))
        if match:
            steps.add(int(match.group(1)))
    return sorted(steps)


def main() -> None:
    args = parse_args()
    audit = load_json(args.audit)
    items = audit.get("items") or []
    incomplete = [
        item.get("audit_item_id")
        for item in items
        if item.get("author_final_label") not in UI_LABELS
        or item.get("author_resolution") is None
    ]
    if incomplete:
        raise SystemExit(f"Incomplete audit items: {', '.join(map(str, incomplete))}")

    changes = [
        item
        for item in items
        if item.get("author_final_label") != item.get("reference_label")
    ]
    files: dict[Path, dict[str, Any]] = {}
    source_updates: Counter[str] = Counter()
    evidence_backfills = 0

    def editable(path: Path) -> dict[str, Any]:
        if path not in files:
            files[path] = deepcopy(load_json(path))
        return files[path]

    for decision in changes:
        flow_id = str(decision["flow_id"])
        requirement_id = str(decision["requirement_id"])
        original_label = str(decision["reference_label"])
        final_label = str(decision["author_final_label"])

        verification_path = args.verification_root / flow_id / "verification_gold.json"
        if not verification_path.exists():
            raise SystemExit(f"Verification-gold file not found: {verification_path}")
        verification_record = find_record(editable(verification_path), "items", requirement_id)
        if verification_record is None:
            raise SystemExit(f"Verification item not found: {flow_id} / {requirement_id}")
        current_label = verification_record.get("ui_evaluability")
        if current_label not in {original_label, final_label}:
            raise SystemExit(
                f"Unexpected current label for {flow_id} / {requirement_id}: "
                f"{current_label!r}; audit expected {original_label!r}"
            )
        verification_record["ui_evaluability"] = final_label
        if final_label != "NOT_UI_VERIFIABLE" and not verification_record.get("evidence_steps"):
            evidence_steps = reviewed_evidence_steps(decision)
            if not evidence_steps:
                raise SystemExit(
                    f"No reviewed screenshots available for newly UI-verifiable item: "
                    f"{flow_id} / {requirement_id}"
                )
            verification_record["evidence_steps"] = evidence_steps
            verification_record["evidence_units"] = [
                {"step_index": step, "evidence_type": "screen"}
                for step in evidence_steps
            ]
            evidence_backfills += 1
        verification_record["ui_evaluability_author_reinspection"] = {
            "audit_schema": audit.get("schema_version"),
            "audit_item_id": decision.get("audit_item_id"),
            "original_label": original_label,
            "final_label": final_label,
            "resolution": decision.get("author_resolution"),
            "confidence": decision.get("author_confidence"),
            "rationale": decision.get("author_rationale") or "",
            "note": decision.get("author_note") or "",
            "audit_completed_at": audit.get("created_at"),
        }

        for source_name, source_root, filename in (
            ("requirements_gold", args.gold_root, "gold_requirements.json"),
            ("requirements_candidate", args.candidate_root, "candidate_requirements.json"),
        ):
            source_path = source_root / flow_id / filename
            if not source_path.exists():
                continue
            source_record = find_record(editable(source_path), "requirements", requirement_id)
            if source_record is None:
                continue
            source_record["ui_evaluability"] = final_label
            source_updates[source_name] += 1

    summary = {
        "mode": "applied" if args.apply else "preview_only",
        "completed_audit_items": len(items),
        "unchanged_items": len(items) - len(changes),
        "changed_items": len(changes),
        "changed_by_dataset": dict(Counter(str(item.get("dataset")) for item in changes)),
        "source_record_updates": dict(source_updates),
        "reviewed_evidence_backfills": evidence_backfills,
        "files_touched": len(files),
    }
    if args.apply:
        for path, document in files.items():
            write_json(path, document)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
