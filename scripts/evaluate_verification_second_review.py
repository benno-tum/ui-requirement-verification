from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
LABELS = (
    "FULFILLED",
    "PARTIALLY_FULFILLED",
    "ABSTAIN",
    "NOT_FULFILLED",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate a completed blinded verification-label second-review form "
            "against the frozen primary-author labels."
        )
    )
    parser.add_argument("review_form", type=Path)
    parser.add_argument(
        "--gold-root",
        type=Path,
        default=BASE_DIR / "data/annotations/verification_gold",
    )
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


def _gold_index(gold_root: Path) -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}
    for path in sorted(gold_root.glob("[0-9][0-9]_*/verification_gold.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload["items"]:
            result[(payload["flow_id"], item["requirement_id"])] = str(
                item["verification_label"]
            ).upper()
    return result


def _cohen_kappa(primary: list[str], secondary: list[str]) -> float:
    count = len(primary)
    observed = sum(left == right for left, right in zip(primary, secondary)) / count
    primary_counts = Counter(primary)
    secondary_counts = Counter(secondary)
    expected = sum(
        (primary_counts[label] / count) * (secondary_counts[label] / count)
        for label in LABELS
    )
    if expected == 1:
        return 1.0
    return (observed - expected) / (1 - expected)


def evaluate(
    *,
    review_form: Path,
    gold_root: Path,
) -> dict[str, Any]:
    payload = json.loads(review_form.read_text(encoding="utf-8"))
    items = payload["items"]
    missing = [
        item["audit_item_id"]
        for item in items
        if str(item.get("reviewer_label") or "").upper() not in LABELS
    ]
    if missing:
        raise ValueError(
            "review is incomplete or has invalid labels for: " + ", ".join(missing)
        )

    gold = _gold_index(gold_root)
    primary: list[str] = []
    secondary: list[str] = []
    disagreements: list[dict[str, Any]] = []
    confusion = {label: {candidate: 0 for candidate in LABELS} for label in LABELS}
    for item in items:
        key = (item["flow_id"], item["requirement_id"])
        if key not in gold:
            raise KeyError(f"review item is not in frozen gold: {key}")
        primary_label = gold[key]
        reviewer_label = str(item["reviewer_label"]).upper()
        primary.append(primary_label)
        secondary.append(reviewer_label)
        confusion[primary_label][reviewer_label] += 1
        if primary_label != reviewer_label:
            disagreements.append(
                {
                    "audit_item_id": item["audit_item_id"],
                    "flow_id": item["flow_id"],
                    "requirement_id": item["requirement_id"],
                    "requirement_text": item["requirement_text"],
                    "primary_label": primary_label,
                    "reviewer_label": reviewer_label,
                    "reviewer_evidence_steps": item.get(
                        "reviewer_evidence_steps", []
                    ),
                    "reviewer_notes": item.get("reviewer_notes", ""),
                    "adjudicated_label": None,
                    "adjudication_note": "",
                }
            )

    agreement = sum(left == right for left, right in zip(primary, secondary))
    return {
        "schema_version": "verification_second_review_report_v1",
        "review_form": str(review_form),
        "sample_size": len(items),
        "flow_count": len({item["flow_id"] for item in items}),
        "raw_agreement": agreement / len(items),
        "cohen_kappa": _cohen_kappa(primary, secondary),
        "primary_label_distribution": dict(Counter(primary)),
        "reviewer_label_distribution": dict(Counter(secondary)),
        "confusion_matrix_primary_rows": confusion,
        "disagreement_count": len(disagreements),
        "adjudication_queue": disagreements,
        "interpretation_note": (
            "The sample is label-stratified and oversamples rare labels. Report "
            "class-specific agreement and do not treat its raw agreement as a "
            "prevalence-weighted estimate for the full benchmark."
        ),
    }


def main() -> None:
    args = parse_args()
    result = evaluate(review_form=args.review_form, gold_root=args.gold_root)
    out = args.out or args.review_form.with_name("second_review_report.json")
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        f"out={out} sample={result['sample_size']} "
        f"agreement={result['raw_agreement']:.3f} "
        f"kappa={result['cohen_kappa']:.3f} "
        f"disagreements={result['disagreement_count']}"
    )


if __name__ == "__main__":
    main()
