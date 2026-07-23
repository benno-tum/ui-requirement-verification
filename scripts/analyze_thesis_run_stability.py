from __future__ import annotations

import argparse
from itertools import combinations
import json
from pathlib import Path
import re
from statistics import mean, stdev
import sys
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from analyze_thesis_final_matrix import _agreement, _metrics  # noqa: E402
from ui_verifier.evaluation.verification_metrics import (  # noqa: E402
    RequirementRecord,
    load_gold_root,
    load_prediction_root,
)


DEFAULT_FAMILIES = {
    "fl_raw_all": [
        "fl_raw_all",
        "fl_raw_all_r2",
        "fl_raw_all_r3",
    ],
    "fl_gated_top4": [
        "fl_gated_top4",
        "fl_gated_top4_r2",
        "fl_gated_top4_r3",
    ],
    "qwen_raw_top4": [
        "qwen3vl8b_openrouter_raw_top4",
        "qwen_raw_top4_r2",
        "qwen_raw_top4_r3",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Describe metric and label stability across the prepared three-run families."
    )
    parser.add_argument(
        "--gold-root",
        type=Path,
        default=BASE_DIR / "data/annotations/verification_gold",
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=BASE_DIR / "data/generated/thesis_final_experiments",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=BASE_DIR
        / "data/generated/thesis_final_experiments/stability_summary.json",
    )
    return parser.parse_args()


def _descriptive(values: list[float]) -> dict[str, float]:
    if not values:
        raise ValueError("cannot summarize an empty value list")
    return {
        "mean": mean(values),
        "sample_standard_deviation": stdev(values) if len(values) > 1 else 0.0,
        "minimum": min(values),
        "maximum": max(values),
    }


def analyze(*, gold_root: Path, runs_root: Path) -> dict[str, Any]:
    flow_pattern = re.compile(r"^[0-9]{2}_")
    gold = {
        key: record
        for key, record in load_gold_root(gold_root).items()
        if flow_pattern.match(record.flow_id)
    }
    gold_by_flow: dict[str, list[RequirementRecord]] = {}
    for record in gold.values():
        gold_by_flow.setdefault(record.flow_id, []).append(record)
    flow_ids = sorted(gold_by_flow)
    if len(flow_ids) != 13 or len(gold) != 258:
        raise ValueError(
            f"expected the frozen 13-flow/258-item benchmark, found {len(flow_ids)} flows and {len(gold)} items"
        )

    families: dict[str, Any] = {}
    for family, run_ids in DEFAULT_FAMILIES.items():
        predictions: dict[str, dict[str, RequirementRecord]] = {}
        metrics: dict[str, dict[str, float]] = {}
        for run_id in run_ids:
            path = runs_root / run_id
            records = load_prediction_root(path)
            missing = sorted(set(gold) - set(records))
            extras = sorted(set(records) - set(gold))
            if missing or extras:
                raise ValueError(
                    f"{run_id} coverage mismatch: missing={len(missing)} extras={len(extras)}"
                )
            predictions[run_id] = records
            metrics[run_id] = _metrics(flow_ids, gold_by_flow, records)

        metric_names = tuple(next(iter(metrics.values())))
        pairwise = {
            f"{left}__{right}": _agreement(
                flow_ids,
                gold_by_flow,
                predictions[left],
                predictions[right],
            )
            for left, right in combinations(run_ids, 2)
        }
        families[family] = {
            "run_ids": run_ids,
            "per_run_metrics": metrics,
            "metric_distribution": {
                metric: _descriptive([metrics[run_id][metric] for run_id in run_ids])
                for metric in metric_names
            },
            "pairwise_label_agreement": pairwise,
        }

    return {
        "schema_version": "thesis_run_stability_v1",
        "method": (
            "Descriptive three-run stability analysis. Runs share the same fixed benchmark and "
            "configuration; repetitions are not treated as independent benchmark samples."
        ),
        "flow_count": len(flow_ids),
        "item_count": len(gold),
        "families": families,
    }


def main() -> None:
    args = parse_args()
    result = analyze(gold_root=args.gold_root, runs_root=args.runs_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    for family, values in result["families"].items():
        accuracy = values["metric_distribution"]["accuracy"]
        print(
            f"{family}: accuracy_mean={accuracy['mean']:.3f} "
            f"sd={accuracy['sample_standard_deviation']:.3f} "
            f"range=[{accuracy['minimum']:.3f}, {accuracy['maximum']:.3f}]"
        )
    print(f"out={args.out}")


if __name__ == "__main__":
    main()
