from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import re
import sys
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ui_verifier.evaluation.verification_metrics import (  # noqa: E402
    DEFAULT_LABELS,
    RequirementRecord,
    load_gold_root,
    load_prediction_root,
)


DEFAULT_CONDITIONS = {
    "fl_raw_all": BASE_DIR / "data/generated/thesis_final_experiments/fl_raw_all",
    "fl_gated_all": BASE_DIR / "data/generated/thesis_final_experiments/fl_gated_all",
    "fl_raw_top4": BASE_DIR / "data/generated/thesis_final_experiments/fl_raw_top4",
    "fl_gated_top4": BASE_DIR / "data/generated/thesis_final_experiments/fl_gated_top4",
    "g25_raw_all": BASE_DIR / "data/generated/thesis_final_experiments/g25_raw_all",
    "qwen_raw_top4": BASE_DIR
    / "data/generated/thesis_final_experiments/qwen3vl8b_openrouter_raw_top4",
}
DEFAULT_CONTRASTS = [
    ("decomposition_all", "fl_gated_all", "fl_raw_all"),
    ("decomposition_top4", "fl_gated_top4", "fl_raw_top4"),
    ("selection_raw", "fl_raw_top4", "fl_raw_all"),
    ("selection_gated", "fl_gated_top4", "fl_gated_all"),
    ("model_raw_all", "fl_raw_all", "g25_raw_all"),
    ("open_model_raw_top4", "qwen_raw_top4", "fl_raw_top4"),
]
DEFAULT_AGREEMENTS = [
    ("commercial_raw_all", "fl_raw_all", "g25_raw_all"),
    ("open_model_raw_top4", "qwen_raw_top4", "fl_raw_top4"),
]
METRIC_NAMES = ("accuracy", "macro_f1", "false_fulfillment_rate", "abstain_rate", "evidence_mrr")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Flow-cluster bootstrap analysis for the controlled thesis experiment matrix."
    )
    parser.add_argument(
        "--gold-root",
        type=Path,
        default=BASE_DIR / "data/annotations/verification_gold",
    )
    parser.add_argument("--samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260723)
    parser.add_argument(
        "--out",
        type=Path,
        default=BASE_DIR / "data/generated/thesis_final_experiments/controlled_matrix_cluster_bootstrap.json",
    )
    return parser.parse_args()


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _metrics(
    flow_sequence: list[str],
    gold_by_flow: dict[str, list[RequirementRecord]],
    predictions: dict[str, RequirementRecord],
) -> dict[str, float]:
    pairs: list[tuple[str, str]] = []
    reciprocal_ranks: list[float] = []
    for flow_id in flow_sequence:
        for gold in gold_by_flow[flow_id]:
            prediction = predictions[gold.key]
            pairs.append((str(gold.label), str(prediction.label)))
            gold_steps = set(gold.evidence_steps)
            if not gold_steps:
                continue
            first_hit = next(
                (rank for rank, step in enumerate(prediction.evidence_steps, start=1) if step in gold_steps),
                None,
            )
            reciprocal_ranks.append(1.0 / first_hit if first_hit else 0.0)

    accuracy = _safe_div(sum(gold == pred for gold, pred in pairs), len(pairs))
    class_f1: list[float] = []
    for label in DEFAULT_LABELS:
        tp = sum(gold == label and pred == label for gold, pred in pairs)
        fp = sum(gold != label and pred == label for gold, pred in pairs)
        fn = sum(gold == label and pred != label for gold, pred in pairs)
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        class_f1.append(_safe_div(2 * precision * recall, precision + recall))

    predicted_fulfilled = sum(pred == "FULFILLED" for _, pred in pairs)
    false_fulfilled = sum(gold != "FULFILLED" and pred == "FULFILLED" for gold, pred in pairs)
    return {
        "accuracy": accuracy,
        "macro_f1": sum(class_f1) / len(DEFAULT_LABELS),
        "false_fulfillment_rate": _safe_div(false_fulfilled, predicted_fulfilled),
        "abstain_rate": _safe_div(sum(pred == "ABSTAIN" for _, pred in pairs), len(pairs)),
        "evidence_mrr": _safe_div(sum(reciprocal_ranks), len(reciprocal_ranks)),
    }


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _agreement(
    flow_sequence: list[str],
    gold_by_flow: dict[str, list[RequirementRecord]],
    left: dict[str, RequirementRecord],
    right: dict[str, RequirementRecord],
) -> dict[str, float]:
    pairs: list[tuple[str, str]] = []
    for flow_id in flow_sequence:
        for gold in gold_by_flow[flow_id]:
            pairs.append((str(left[gold.key].label), str(right[gold.key].label)))
    observed = _safe_div(sum(a == b for a, b in pairs), len(pairs))
    expected = sum(
        _safe_div(sum(a == label for a, _ in pairs), len(pairs))
        * _safe_div(sum(b == label for _, b in pairs), len(pairs))
        for label in DEFAULT_LABELS
    )
    return {
        "raw_agreement": observed,
        "cohen_kappa": _safe_div(observed - expected, 1 - expected),
    }


def _interval(values: list[float]) -> dict[str, float]:
    return {
        "lower_95": _percentile(values, 0.025),
        "upper_95": _percentile(values, 0.975),
    }


def analyze(*, gold_root: Path, samples: int, seed: int) -> dict[str, Any]:
    if samples < 1:
        raise ValueError("samples must be positive")
    flow_pattern = re.compile(r"^[0-9]{2}_")
    gold = {key: record for key, record in load_gold_root(gold_root).items() if flow_pattern.match(record.flow_id)}
    gold_by_flow: dict[str, list[RequirementRecord]] = {}
    for record in gold.values():
        gold_by_flow.setdefault(record.flow_id, []).append(record)
    flow_ids = sorted(gold_by_flow)
    if len(flow_ids) != 13:
        raise ValueError(f"expected 13 Mind2Web flows, found {len(flow_ids)}")

    predictions: dict[str, dict[str, RequirementRecord]] = {}
    for condition, path in DEFAULT_CONDITIONS.items():
        records = load_prediction_root(path)
        missing = sorted(set(gold) - set(records))
        if missing:
            raise ValueError(f"{condition} is missing {len(missing)} predictions")
        predictions[condition] = records

    points = {
        condition: _metrics(flow_ids, gold_by_flow, records)
        for condition, records in predictions.items()
    }
    agreement_points = {
        name: _agreement(flow_ids, gold_by_flow, predictions[left], predictions[right])
        for name, left, right in DEFAULT_AGREEMENTS
    }
    agreement_draws = {
        name: {"raw_agreement": [], "cohen_kappa": []}
        for name, _, _ in DEFAULT_AGREEMENTS
    }
    draws: dict[str, dict[str, list[float]]] = {
        condition: {metric: [] for metric in METRIC_NAMES} for condition in predictions
    }
    contrast_draws: dict[str, dict[str, list[float]]] = {
        name: {metric: [] for metric in METRIC_NAMES} for name, _, _ in DEFAULT_CONTRASTS
    }
    rng = random.Random(seed)
    for _ in range(samples):
        sampled_flows = [rng.choice(flow_ids) for _ in flow_ids]
        sampled_metrics = {
            condition: _metrics(sampled_flows, gold_by_flow, records)
            for condition, records in predictions.items()
        }
        for condition, metrics in sampled_metrics.items():
            for metric in METRIC_NAMES:
                draws[condition][metric].append(metrics[metric])
        for name, left, right in DEFAULT_CONTRASTS:
            for metric in METRIC_NAMES:
                contrast_draws[name][metric].append(sampled_metrics[left][metric] - sampled_metrics[right][metric])
        for name, left, right in DEFAULT_AGREEMENTS:
            sampled_agreement = _agreement(
                sampled_flows,
                gold_by_flow,
                predictions[left],
                predictions[right],
            )
            for metric, value in sampled_agreement.items():
                agreement_draws[name][metric].append(value)

    condition_results = {
        condition: {
            metric: {"estimate": points[condition][metric], **_interval(draws[condition][metric])}
            for metric in METRIC_NAMES
        }
        for condition in predictions
    }
    contrast_results: dict[str, Any] = {}
    for name, left, right in DEFAULT_CONTRASTS:
        contrast_results[name] = {
            "left": left,
            "right": right,
            "difference": {
                metric: {
                    "estimate": points[left][metric] - points[right][metric],
                    **_interval(contrast_draws[name][metric]),
                }
                for metric in METRIC_NAMES
            },
        }

    return {
        "method": "paired nonparametric percentile bootstrap over complete flows",
        "confidence_level": 0.95,
        "samples": samples,
        "seed": seed,
        "flow_count": len(flow_ids),
        "item_count": len(gold),
        "conditions": condition_results,
        "contrasts": contrast_results,
        "model_agreements": {
            name: {
                "left": left,
                "right": right,
                "metrics": {
                    metric: {
                        "estimate": agreement_points[name][metric],
                        **_interval(agreement_draws[name][metric]),
                    }
                    for metric in agreement_points[name]
                },
            }
            for name, left, right in DEFAULT_AGREEMENTS
        },
    }


def main() -> None:
    args = parse_args()
    result = analyze(gold_root=args.gold_root, samples=args.samples, seed=args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"flows={result['flow_count']} items={result['item_count']} samples={result['samples']}")
    for name, contrast in result["contrasts"].items():
        accuracy = contrast["difference"]["accuracy"]
        macro_f1 = contrast["difference"]["macro_f1"]
        print(
            f"{name}: accuracy={accuracy['estimate']:+.3f} "
            f"[{accuracy['lower_95']:+.3f}, {accuracy['upper_95']:+.3f}] "
            f"macro_f1={macro_f1['estimate']:+.3f} "
            f"[{macro_f1['lower_95']:+.3f}, {macro_f1['upper_95']:+.3f}]"
        )
    print(f"out={args.out}")


if __name__ == "__main__":
    main()
