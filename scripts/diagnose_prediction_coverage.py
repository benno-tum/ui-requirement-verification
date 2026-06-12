from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ui_verifier.evaluation.prediction_coverage import coverage_for_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare verification benchmark item ids with ids predicted by a pipeline run."
    )
    parser.add_argument("--verification-gold", type=Path, required=True, help="verification_gold.json path")
    parser.add_argument("--predictions", type=Path, required=True, help="Pipeline output JSON path")
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON output path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    coverage = coverage_for_files(args.verification_gold, args.predictions).to_dict()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(coverage, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"total_reviewed={coverage['total_reviewed']}")
    print(f"total_predictions={coverage['total_predictions']}")
    print(f"prediction_coverage={coverage['prediction_coverage']:.3f}")
    print(f"missing_prediction_count={coverage['missing_prediction_count']}")
    print(f"extra_prediction_count={coverage['extra_prediction_count']}")
    print(f"missing_by_prefix={coverage['missing_by_prefix']}")
    print(f"extra_by_prefix={coverage['extra_by_prefix']}")
    if coverage["missing_prediction_ids"]:
        print("missing_prediction_ids=" + ",".join(coverage["missing_prediction_ids"]))
    if coverage["extra_prediction_ids"]:
        print("extra_prediction_ids=" + ",".join(coverage["extra_prediction_ids"]))
    if args.out:
        print(f"out={args.out}")


if __name__ == "__main__":
    main()
