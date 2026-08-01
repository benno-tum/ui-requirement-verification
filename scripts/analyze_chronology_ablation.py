from __future__ import annotations

import argparse
from collections import Counter
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


SEQUENCE_PATTERN = re.compile(
    r"\b("
    r"preserv(?:e|es|ed|ing)|retain(?:s|ed|ing)?|remain(?:s|ed|ing)?|"
    r"update(?:s|d|ing)?|synchroni[sz](?:e|es|ed|ing)|"
    r"while|continues?|later fields?|as the (?:shopper|user)|"
    r"before and after|after (?:entering|selecting|choosing|changing)|"
    r"cart|checkout|order summary|line items?|result state|results view|"
    r"confirmation|review step|review panel|before submitting"
    r")\b",
    re.IGNORECASE,
)
METRICS = (
    "accuracy",
    "macro_f1",
    "false_fulfillment_rate",
    "abstain_rate",
    "evidence_mrr",
    "label_flip_rate",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Paired analysis of ordered versus chronology-destroyed screenshot verification."
    )
    parser.add_argument(
        "--gold-root",
        type=Path,
        default=BASE_DIR / "data/annotations/verification_gold",
    )
    parser.add_argument(
        "--ordered",
        type=Path,
        default=BASE_DIR / "data/generated/thesis_final_experiments/fl_raw_all",
    )
    parser.add_argument(
        "--destroyed",
        type=Path,
        default=BASE_DIR
        / "data/generated/thesis_final_experiments/fl_raw_all_chronology_destroyed",
    )
    parser.add_argument("--samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260726)
    parser.add_argument("--model", default="gemini-3.1-flash-lite")
    parser.add_argument(
        "--out",
        type=Path,
        default=BASE_DIR
        / "data/generated/thesis_final_experiments/chronology_destroyed_analysis.json",
    )
    return parser.parse_args()


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _metrics(
    keys: list[str],
    gold: dict[str, RequirementRecord],
    predictions: dict[str, RequirementRecord],
    *,
    comparison: dict[str, RequirementRecord] | None = None,
) -> dict[str, float]:
    pairs = [(str(gold[key].label), str(predictions[key].label)) for key in keys]
    accuracy = _safe_div(sum(gold_label == pred for gold_label, pred in pairs), len(pairs))
    class_f1: list[float] = []
    for label in DEFAULT_LABELS:
        tp = sum(gold_label == label and pred == label for gold_label, pred in pairs)
        fp = sum(gold_label != label and pred == label for gold_label, pred in pairs)
        fn = sum(gold_label == label and pred != label for gold_label, pred in pairs)
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        class_f1.append(_safe_div(2 * precision * recall, precision + recall))

    predicted_fulfilled = sum(pred == "FULFILLED" for _, pred in pairs)
    false_fulfilled = sum(
        gold_label != "FULFILLED" and pred == "FULFILLED"
        for gold_label, pred in pairs
    )
    reciprocal_ranks: list[float] = []
    for key in keys:
        gold_steps = set(gold[key].evidence_steps)
        if not gold_steps:
            continue
        first_hit = next(
            (
                rank
                for rank, step in enumerate(predictions[key].evidence_steps, start=1)
                if step in gold_steps
            ),
            None,
        )
        reciprocal_ranks.append(1.0 / first_hit if first_hit else 0.0)

    flip_rate = 0.0
    if comparison is not None:
        flip_rate = _safe_div(
            sum(predictions[key].label != comparison[key].label for key in keys),
            len(keys),
        )
    return {
        "accuracy": accuracy,
        "macro_f1": _safe_div(sum(class_f1), len(DEFAULT_LABELS)),
        "false_fulfillment_rate": _safe_div(false_fulfilled, predicted_fulfilled),
        "abstain_rate": _safe_div(sum(pred == "ABSTAIN" for _, pred in pairs), len(pairs)),
        "evidence_mrr": _safe_div(sum(reciprocal_ranks), len(reciprocal_ranks)),
        "label_flip_rate": flip_rate,
    }


def _raw_gold_metadata(gold_root: Path) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for path in sorted(gold_root.glob("[0-9][0-9]_*/verification_gold.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        flow_id = str(payload.get("flow_id") or path.parent.name)
        for item in payload.get("items") or []:
            requirement_id = str(item.get("requirement_id") or "")
            metadata[f"{flow_id}::{requirement_id}"] = {
                "text": str(item.get("text") or ""),
                "scope": str(item.get("scope") or ""),
            }
    return metadata


def _run_diagnostics(path: Path) -> dict[str, Any]:
    totals = Counter()
    cost_usd = 0.0
    failures: list[dict[str, Any]] = []
    modes = Counter()
    permutation_ids: set[str] = set()
    flow_files = sorted(candidate for candidate in path.glob("*.json"))
    for candidate in flow_files:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
        diagnostics = payload.get("metadata", {}).get("gemini_image_verifier", {})
        totals["requirements"] += len(payload.get("results") or [])
        totals["api_calls"] += int(diagnostics.get("api_calls") or 0)
        totals["fallbacks"] += int(diagnostics.get("fallbacks") or 0)
        failures.extend(diagnostics.get("failures") or [])
        modes[str(diagnostics.get("chronology_mode") or "unknown")] += 1
        usage = diagnostics.get("usage") or {}
        for key in (
            "request_count",
            "input_tokens",
            "output_tokens",
            "thoughts_tokens",
            "total_tokens",
        ):
            totals[key] += int(usage.get(key) or 0)
        cost_usd += float(usage.get("estimated_cost_usd") or 0.0)
        for group in diagnostics.get("groups") or []:
            permutation_id = str(group.get("permutation_id") or "")
            if permutation_id:
                permutation_ids.add(permutation_id)
    return {
        "flow_files": len(flow_files),
        **dict(totals),
        "failures": len(failures),
        "estimated_cost_usd": cost_usd,
        "chronology_modes": dict(modes),
        "unique_permutation_ids": len(permutation_ids),
    }


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    if args.samples < 1:
        raise ValueError("samples must be positive")
    flow_pattern = re.compile(r"^[0-9]{2}_")
    gold = {
        key: record
        for key, record in load_gold_root(args.gold_root).items()
        if flow_pattern.match(record.flow_id)
    }
    ordered = load_prediction_root(args.ordered)
    destroyed = load_prediction_root(args.destroyed)
    for name, records in (("ordered", ordered), ("destroyed", destroyed)):
        missing = sorted(set(gold) - set(records))
        unexpected = sorted(set(records) - set(gold))
        if missing or unexpected:
            raise ValueError(
                f"{name} coverage mismatch: missing={len(missing)} unexpected={len(unexpected)}"
            )

    metadata = _raw_gold_metadata(args.gold_root)
    subsets = {
        "all": sorted(gold),
        "multi_screen": sorted(
            key for key in gold if metadata.get(key, {}).get("scope") == "multi_screen"
        ),
        "single_screen_negative_control": sorted(
            key for key in gold if metadata.get(key, {}).get("scope") == "single_screen"
        ),
        "multi_step_gold_evidence": sorted(
            key for key, record in gold.items() if len(set(record.evidence_steps)) > 1
        ),
        "sequence_sensitive_lexical": sorted(
            key
            for key in gold
            if SEQUENCE_PATTERN.search(str(metadata.get(key, {}).get("text") or ""))
        ),
    }
    flows = sorted({record.flow_id for record in gold.values()})
    keys_by_subset_flow = {
        subset: {
            flow_id: [key for key in keys if gold[key].flow_id == flow_id]
            for flow_id in flows
        }
        for subset, keys in subsets.items()
    }

    points: dict[str, Any] = {}
    for subset, keys in subsets.items():
        ordered_metrics = _metrics(keys, gold, ordered)
        destroyed_metrics = _metrics(keys, gold, destroyed, comparison=ordered)
        points[subset] = {
            "item_count": len(keys),
            "ordered": ordered_metrics,
            "chronology_destroyed": destroyed_metrics,
            "difference_destroyed_minus_ordered": {
                metric: destroyed_metrics[metric] - ordered_metrics[metric]
                for metric in METRICS
            },
        }

    rng = random.Random(args.seed)
    draws = {
        subset: {metric: [] for metric in METRICS}
        for subset in subsets
    }
    for _ in range(args.samples):
        sampled_flows = [rng.choice(flows) for _ in flows]
        for subset in subsets:
            sampled_keys = [
                key
                for flow_id in sampled_flows
                for key in keys_by_subset_flow[subset][flow_id]
            ]
            ordered_metrics = _metrics(sampled_keys, gold, ordered)
            destroyed_metrics = _metrics(
                sampled_keys,
                gold,
                destroyed,
                comparison=ordered,
            )
            for metric in METRICS:
                draws[subset][metric].append(
                    destroyed_metrics[metric] - ordered_metrics[metric]
                )

    for subset in subsets:
        points[subset]["difference_95_interval"] = {
            metric: {
                "lower": _percentile(draws[subset][metric], 0.025),
                "upper": _percentile(draws[subset][metric], 0.975),
            }
            for metric in METRICS
        }

    flip_matrix = Counter(
        (str(ordered[key].label), str(destroyed[key].label))
        for key in subsets["all"]
        if ordered[key].label != destroyed[key].label
    )
    return {
        "schema_version": "chronology_destroyed_ablation_analysis_v1",
        "method": (
            "Matched ordered-versus-order-unavailable comparison with a fixed per-flow "
            "permutation and paired percentile bootstrap over 13 complete flows."
        ),
        "model": args.model,
        "ordered_condition": str(args.ordered),
        "chronology_destroyed_condition": str(args.destroyed),
        "bootstrap_samples": args.samples,
        "bootstrap_seed": args.seed,
        "flow_count": len(flows),
        "destroyed_run_diagnostics": _run_diagnostics(args.destroyed),
        "subsets": points,
        "label_flip_matrix_nonzero_only": {
            f"{left}->{right}": count
            for (left, right), count in sorted(flip_matrix.items())
        },
        "interpretation_constraint": (
            "The destroyed condition explicitly tells the model that chronology is unavailable. "
            "It estimates the effect of withholding trustworthy temporal order, not the effect of "
            "deceiving the model with a false chronology."
        ),
    }


def main() -> None:
    args = parse_args()
    result = analyze(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    all_results = result["subsets"]["all"]
    print(
        "all: "
        f"ordered_accuracy={all_results['ordered']['accuracy']:.3f} "
        f"destroyed_accuracy={all_results['chronology_destroyed']['accuracy']:.3f} "
        f"accuracy_difference={all_results['difference_destroyed_minus_ordered']['accuracy']:+.3f} "
        f"label_flip_rate={all_results['chronology_destroyed']['label_flip_rate']:.3f}"
    )
    print(f"out={args.out}")


if __name__ == "__main__":
    main()
