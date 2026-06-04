from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ui_verifier.evaluation.verification_metrics import evaluate_predictions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate UI verification predictions against verification_gold annotations.")
    parser.add_argument(
        "--gold-root",
        type=Path,
        default=BASE_DIR / "data" / "annotations" / "verification_gold",
        help="Directory containing */verification_gold.json files, or one gold JSON file.",
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        required=True,
        help="Prediction JSON file or directory containing pipeline outputs / verification_run.json files.",
    )
    parser.add_argument("--out", type=Path, default=None, help="Optional output JSON path for full metrics.")
    parser.add_argument("--k", type=int, action="append", default=None, help="Evidence top-k value. Can be repeated.")
    parser.add_argument("--no-claims", action="store_true", help="Skip claim-status metrics.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metrics = evaluate_predictions(
        args.gold_root,
        args.predictions,
        include_claims=not args.no_claims,
        k_values=args.k,
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    label = metrics["label_metrics"]
    evidence = metrics["evidence_metrics"]
    print(f"gold_count={metrics['gold_count']} prediction_count={metrics['prediction_count']}")
    print(
        "labels: "
        f"accuracy={label['accuracy']:.3f} "
        f"macro_f1={label['macro_f1']:.3f} "
        f"abstain_rate={label['abstain_rate']:.3f} "
        f"false_fulfillment_rate={label['false_fulfillment_rate']:.3f} "
        f"coverage={label['prediction_coverage']:.3f}"
    )
    evidence_parts = [f"mrr={evidence['mrr']:.3f}"]
    for key, value in evidence.items():
        if key.startswith("recall_at_"):
            evidence_parts.append(f"{key}={value:.3f}")
    print("evidence: " + " ".join(evidence_parts))
    if "claim_status_metrics" in metrics:
        claim = metrics["claim_status_metrics"]
        print(
            "claims: "
            f"macro_f1={claim['macro_f1']:.3f} "
            f"match_recall={claim['claim_match_recall']:.3f} "
            f"gold_claims={claim['gold_claim_count']} "
            f"pred_claims={claim['prediction_claim_count']}"
        )
    if args.out:
        print(f"out={args.out}")


if __name__ == "__main__":
    main()
