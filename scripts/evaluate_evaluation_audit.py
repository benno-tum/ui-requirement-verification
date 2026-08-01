from __future__ import annotations

import argparse
from pathlib import Path

from ui_verifier.evaluation.review_audit import (
    EvaluationAuditStore,
    bbox_metrics,
    classification_metrics,
    image_asset_metadata_errors,
    write_json,
)


BASE_DIR = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate completed audit responses.")
    parser.add_argument("--audit-id", default="ui_bbox_focused_20260717")
    parser.add_argument("--reviewer-id", required=True)
    parser.add_argument(
        "--audit-root",
        type=Path,
        default=BASE_DIR / "data" / "annotations" / "evaluation_audits",
    )
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    store = EvaluationAuditStore(args.audit_root)
    ui_reference = store.load_private_reference(args.audit_id, "ui")["items"]
    ui_reviews = store.load_reviews(args.audit_id, args.reviewer_id, "ui")["items"]
    pairs = [
        (ui_reference[item_id]["gold_label"], review["label"])
        for item_id, review in ui_reviews.items()
        if item_id in ui_reference and review.get("label")
    ]
    bbox_manifest = store.load_public_manifest(args.audit_id, "bbox")
    bbox_reference = store.load_private_reference(args.audit_id, "bbox")["items"]
    bbox_reviews = store.load_reviews(args.audit_id, args.reviewer_id, "bbox")["items"]
    asset_errors = {
        item["audit_item_id"]: errors
        for item in bbox_manifest["items"]
        if (errors := image_asset_metadata_errors(item))
    }
    disagreements = [
        {
            "audit_item_id": item_id,
            "flow_id": ui_reference[item_id]["flow_id"],
            "requirement_id": ui_reference[item_id]["requirement_id"],
            "original_label": ui_reference[item_id]["gold_label"],
            "reviewer_label": review["label"],
            "reviewer_rationale": review.get("rationale", ""),
            "reviewer_confidence": review.get("confidence"),
            "reviewer_ambiguous": review.get("ambiguous", False),
            "adjudicated_label": None,
            "adjudication_note": "",
        }
        for item_id, review in sorted(ui_reviews.items())
        if item_id in ui_reference
        and review.get("label")
        and review["label"] != ui_reference[item_id]["gold_label"]
    ]
    report = {
        "audit_id": args.audit_id,
        "reviewer_id": args.reviewer_id,
        "completion": {
            "ui_reviewed": len(pairs),
            "ui_required": len(ui_reference),
            "bbox_gold_locked": sum(bool(review.get("gold_locked")) for review in bbox_reviews.values()),
            "bbox_required": len(bbox_manifest["items"]),
            "bbox_quality_rated": sum(
                review.get("relevance") in {"YES", "NO"} and review.get("sufficiency") in {"YES", "NO"}
                for review in bbox_reviews.values()
            ),
        },
        "ui_evaluability_agreement": classification_metrics(pairs),
        "ui_disagreement_count": len(disagreements),
        "bounding_box_localization": bbox_metrics(bbox_manifest["items"], bbox_reference, bbox_reviews),
        "asset_metadata": {
            "valid": not asset_errors,
            "invalid_item_count": len(asset_errors),
            "errors": asset_errors,
        },
    }
    output = args.out or store.audit_dir(args.audit_id) / "reports" / f"{args.reviewer_id}.json"
    write_json(output, report)
    queue_output = output.with_name(f"{args.reviewer_id}_ui_adjudication_queue.json")
    write_json(
        queue_output,
        {
            "audit_id": args.audit_id,
            "reviewer_id": args.reviewer_id,
            "instructions": "Fill adjudicated_label and adjudication_note for every disagreement, then run apply_ui_evaluability_adjudication.py without --apply to preview metrics.",
            "items": disagreements,
        },
    )
    print(output)
    print(queue_output)


if __name__ == "__main__":
    main()
