from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ui_verifier.evaluation.review_audit import (
    UI_LABELS,
    classifier_metrics_for_gold,
    load_verification_gold,
    write_json,
)


BASE_DIR = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate an adjudication queue, preview updated classifier metrics, and optionally apply it to verification gold."
    )
    parser.add_argument("adjudication_file", type=Path)
    parser.add_argument(
        "--gold-root",
        type=Path,
        default=BASE_DIR / "data" / "annotations" / "verification_gold",
    )
    parser.add_argument("--apply", action="store_true", help="Write adjudicated labels to verification-gold files.")
    return parser.parse_args()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    args = parse_args()
    queue = _load(args.adjudication_file)
    decisions = queue.get("items") or []
    incomplete = [item.get("audit_item_id") for item in decisions if item.get("adjudicated_label") not in UI_LABELS]
    if incomplete:
        raise SystemExit(f"Missing or invalid adjudicated_label for: {', '.join(str(value) for value in incomplete)}")

    files: dict[Path, dict[str, Any]] = {}
    all_items = load_verification_gold(args.gold_root)
    item_index = {(item["flow_id"], item["requirement_id"]): item for item in all_items}
    for decision in decisions:
        key = (decision["flow_id"], decision["requirement_id"])
        if key not in item_index:
            raise SystemExit(f"Gold item not found: {key[0]} / {key[1]}")
        item_index[key]["ui_evaluability"] = decision["adjudicated_label"]

        path = args.gold_root / key[0] / "verification_gold.json"
        document = files.setdefault(path, deepcopy(_load(path)))
        target = next((item for item in document.get("items", []) if item.get("requirement_id") == key[1]), None)
        if target is None:
            raise SystemExit(f"Gold file has no matching item: {key[0]} / {key[1]}")
        target["ui_evaluability"] = decision["adjudicated_label"]
        target["ui_evaluability_adjudication"] = {
            "audit_id": queue.get("audit_id"),
            "reviewer_id": queue.get("reviewer_id"),
            "original_label": decision.get("original_label"),
            "reviewer_label": decision.get("reviewer_label"),
            "note": decision.get("adjudication_note", ""),
            "adjudicated_at": datetime.now(timezone.utc).isoformat(),
        }

    preview = {
        "mode": "applied" if args.apply else "preview_only",
        "decision_count": len(decisions),
        "classifier_metrics_after_adjudication": classifier_metrics_for_gold(all_items),
    }
    preview_path = args.adjudication_file.with_name(args.adjudication_file.stem + "_metrics_preview.json")
    write_json(preview_path, preview)
    if args.apply:
        for path, document in files.items():
            write_json(path, document)
    print(preview_path)
    print(f"Updated {len(files)} gold files." if args.apply else "Preview only; verification gold was not changed.")


if __name__ == "__main__":
    main()
