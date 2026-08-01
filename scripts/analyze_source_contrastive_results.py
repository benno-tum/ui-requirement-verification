from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from analyze_thesis_final_matrix import _metrics  # noqa: E402
from ui_verifier.evaluation.verification_metrics import (  # noqa: E402
    RequirementRecord,
    load_gold_root,
    load_prediction_root,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Report primary verification results separately for ordinary source "
            "requirements and deliberately generated contrastive requirements."
        )
    )
    parser.add_argument(
        "--gold-root",
        type=Path,
        default=BASE_DIR / "data/annotations/verification_gold",
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        default=BASE_DIR / "data/generated/thesis_final_experiments/fl_raw_all",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=BASE_DIR
        / "data/generated/thesis_final_experiments/source_contrastive_results.json",
    )
    return parser.parse_args()


def semantic_groups(gold_root: Path) -> dict[str, str]:
    groups: dict[str, str] = {}
    for path in sorted(gold_root.glob("[0-9][0-9]_*/verification_gold.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        flow_id = str(payload.get("flow_id") or path.parent.name)
        for item in payload.get("items") or []:
            requirement_id = str(item.get("requirement_id") or "")
            tags = {str(tag).strip().lower() for tag in item.get("tags") or []}
            key = f"{flow_id}::{requirement_id}"
            groups[key] = "contrastive" if "contrastive" in tags else "source"
    return groups


def grouped_metrics(
    keys: list[str],
    gold: dict[str, RequirementRecord],
    predictions: dict[str, RequirementRecord],
) -> dict[str, Any]:
    gold_by_flow: dict[str, list[RequirementRecord]] = {}
    for key in keys:
        record = gold[key]
        gold_by_flow.setdefault(record.flow_id, []).append(record)
    flows = sorted(gold_by_flow)
    metrics = _metrics(flows, gold_by_flow, predictions)
    gold_labels = Counter(str(gold[key].label) for key in keys)
    predicted_labels = Counter(str(predictions[key].label) for key in keys)
    return {
        "item_count": len(keys),
        "gold_label_distribution": dict(sorted(gold_labels.items())),
        "predicted_label_distribution": dict(sorted(predicted_labels.items())),
        **metrics,
    }


def main() -> None:
    args = parse_args()
    # Keep the filtering expression explicit so exploratory PURE records cannot
    # enter the main benchmark table.
    flow_pattern = re.compile(r"^[0-9][0-9]_")
    gold = {
        key: record
        for key, record in load_gold_root(args.gold_root).items()
        if flow_pattern.match(record.flow_id)
    }
    predictions = load_prediction_root(args.predictions)
    groups = semantic_groups(args.gold_root)
    if set(groups) != set(gold):
        raise ValueError(
            f"Semantic grouping mismatch: grouped={len(groups)} gold={len(gold)}"
        )
    missing = sorted(set(gold) - set(predictions))
    if missing:
        raise ValueError(f"Predictions are missing {len(missing)} benchmark items")

    keys_by_group = {
        name: sorted(key for key, group in groups.items() if group == name)
        for name in ("source", "contrastive")
    }
    if len(keys_by_group["source"]) != 187 or len(keys_by_group["contrastive"]) != 71:
        raise ValueError(
            "Expected the reviewed 187/71 semantic split, found "
            f"{len(keys_by_group['source'])}/{len(keys_by_group['contrastive'])}"
        )

    report = {
        "schema_version": "source_contrastive_results_v1",
        "grouping_rule": (
            "Items carrying the explicit 'contrastive' tag are contrastive; "
            "all other Mind2Web verification-gold items are source requirements."
        ),
        "condition": str(args.predictions),
        "groups": {
            name: grouped_metrics(keys, gold, predictions)
            for name, keys in keys_by_group.items()
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"out={args.out}")


if __name__ == "__main__":
    main()
