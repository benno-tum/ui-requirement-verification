from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any


CLASSES = ["UI_VERIFIABLE", "PARTIALLY_UI_VERIFIABLE", "NOT_UI_VERIFIABLE"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare pipeline and manual UI-evaluability labels.")
    parser.add_argument("--gold-root", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def main() -> None:
    args = parse_args()
    confusion = {gold: {prediction: 0 for prediction in CLASSES} for gold in CLASSES}
    pairs: list[tuple[str, str]] = []
    flow_accuracy: list[dict[str, Any]] = []
    missing_predictions: list[str] = []

    for gold_path in sorted(args.gold_root.glob("[0-1][0-9]_*/verification_gold.json")):
        gold_data = json.loads(gold_path.read_text(encoding="utf-8"))
        flow_id = str(gold_data["flow_id"])
        prediction_path = args.predictions / f"{flow_id}.json"
        prediction_data = json.loads(prediction_path.read_text(encoding="utf-8"))
        predictions = {
            str(item["requirement_id"]): str(item.get("ui_evaluability") or "")
            for item in prediction_data.get("results", [])
        }
        correct = total = 0
        for item in gold_data.get("items", []):
            requirement_id = str(item["requirement_id"])
            gold = str(item.get("ui_evaluability") or "")
            prediction = predictions.get(requirement_id, "")
            if gold not in CLASSES:
                continue
            if prediction not in CLASSES:
                missing_predictions.append(f"{flow_id}:{requirement_id}")
                continue
            confusion[gold][prediction] += 1
            pairs.append((gold, prediction))
            correct += int(gold == prediction)
            total += 1
        flow_accuracy.append(
            {
                "flow_id": flow_id,
                "correct": correct,
                "total": total,
                "accuracy": safe_divide(correct, total),
            }
        )

    total = len(pairs)
    correct = sum(gold == prediction for gold, prediction in pairs)
    per_class: dict[str, dict[str, float | int]] = {}
    f1_values: list[float] = []
    for label in CLASSES:
        true_positive = confusion[label][label]
        support = sum(confusion[label].values())
        predicted = sum(confusion[gold][label] for gold in CLASSES)
        precision = safe_divide(true_positive, predicted)
        recall = safe_divide(true_positive, support)
        f1 = safe_divide(2 * precision * recall, precision + recall)
        f1_values.append(f1)
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
            "predicted": predicted,
        }

    gold_counts = Counter(gold for gold, _ in pairs)
    prediction_counts = Counter(prediction for _, prediction in pairs)
    observed_agreement = safe_divide(correct, total)
    expected_agreement = safe_divide(
        sum(gold_counts[label] * prediction_counts[label] for label in CLASSES),
        total * total,
    )
    kappa = safe_divide(observed_agreement - expected_agreement, 1 - expected_agreement)
    ordinal_distance = {
        (gold, prediction): abs(CLASSES.index(gold) - CLASSES.index(prediction)) / (len(CLASSES) - 1)
        for gold in CLASSES
        for prediction in CLASSES
    }
    observed_weighted_disagreement = safe_divide(
        sum(ordinal_distance[pair] for pair in pairs), total
    )
    expected_weighted_disagreement = safe_divide(
        sum(
            ordinal_distance[(gold, prediction)] * gold_counts[gold] * prediction_counts[prediction]
            for gold in CLASSES
            for prediction in CLASSES
        ),
        total * total,
    )
    weighted_kappa = 1 - safe_divide(
        observed_weighted_disagreement,
        expected_weighted_disagreement,
    )
    report = {
        "schema_version": "ui_evaluability_alignment_v1",
        "total": total,
        "raw_agreement": observed_agreement,
        "macro_f1": safe_divide(sum(f1_values), len(f1_values)),
        "cohen_kappa": kappa,
        "linear_weighted_cohen_kappa": weighted_kappa,
        "classes": CLASSES,
        "confusion_matrix": confusion,
        "per_class": per_class,
        "flow_accuracy": flow_accuracy,
        "missing_predictions": missing_predictions,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"total={total} agreement={observed_agreement:.3f} macro_f1={report['macro_f1']:.3f} "
        f"kappa={kappa:.3f} weighted_kappa={weighted_kappa:.3f}"
    )
    print(f"out={args.out}")


if __name__ == "__main__":
    main()
