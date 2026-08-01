from __future__ import annotations

import argparse
from pathlib import Path

from ui_verifier.common.flow_utils import find_step_images
from ui_verifier.evaluation.review_audit import (
    EvaluationAuditStore,
    build_bbox_review_bundle,
    build_ui_review_bundle,
    classifier_metrics_for_gold,
    image_asset_metadata_errors,
    load_verification_gold,
    utc_now,
    write_json,
)
from ui_verifier.localization import ensure_ocr_sidecar, load_ocr_text_boxes


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_ID = "ui_bbox_focused_20260717"
DEFAULT_BBOX_FLOWS = (
    "02_gamestop_a2500e0b-9244-4f0e-b686-fa290c32b829",
    "03_mbta_c094948f-afc6-415c-968a-9e105e2db118",
    "04_underarmour_18fc60d7-aa69-4c07-9bf1-64543eae52c9",
    "08_amtrak_845fbfa9-1b98-4df4-b7c5-4c71ef3e5b1b",
    "pure_2010_split_merge",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build blinded UI-evaluability and bounding-box review bundles.")
    parser.add_argument("--audit-id", default=DEFAULT_AUDIT_ID)
    parser.add_argument("--seed", type=int, default=20260717)
    parser.add_argument("--ui-sample-size", type=int, default=72)
    parser.add_argument("--bbox-per-flow", type=int, default=15)
    parser.add_argument("--bbox-flow", action="append", dest="bbox_flows")
    parser.add_argument(
        "--ensure-ocr-boxes",
        action="store_true",
        help="Use local Tesseract to add missing word/line coordinates before sampling.",
    )
    parser.add_argument(
        "--audit-root",
        type=Path,
        default=BASE_DIR / "data" / "annotations" / "evaluation_audits",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    gold_root = BASE_DIR / "data" / "annotations" / "verification_gold"
    flows_root = BASE_DIR / "data" / "processed" / "flows"
    items = load_verification_gold(gold_root)
    bbox_flows = args.bbox_flows or DEFAULT_BBOX_FLOWS
    if args.ensure_ocr_boxes:
        for flow_id in bbox_flows:
            matches = [path for path in flows_root.glob(f"*/{flow_id}") if path.is_dir()]
            if len(matches) != 1:
                raise FileNotFoundError(f"Expected one flow directory for {flow_id}, found {len(matches)}.")
            for image_path in find_step_images(matches[0]):
                if not load_ocr_text_boxes(image_path):
                    if ensure_ocr_sidecar(image_path, force=True) is None:
                        raise RuntimeError("Tesseract is required by --ensure-ocr-boxes but was not found.")
    ui_manifest, ui_reference = build_ui_review_bundle(
        items,
        sample_size=args.ui_sample_size,
        seed=args.seed,
    )
    bbox_manifest, bbox_reference = build_bbox_review_bundle(
        items,
        flows_root=flows_root,
        flow_ids=bbox_flows,
        per_flow=args.bbox_per_flow,
        seed=args.seed,
    )
    asset_errors = {
        item["audit_item_id"]: errors
        for item in bbox_manifest["items"]
        if (errors := image_asset_metadata_errors(item))
    }
    if asset_errors:
        raise RuntimeError(f"Bounding-box manifest contains invalid asset metadata: {asset_errors}")

    store = EvaluationAuditStore(args.audit_root)
    audit_dir = store.audit_dir(args.audit_id)
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit = {
        "audit_id": args.audit_id,
        "title": "Focused UI-verifiability and OCR bounding-box audit",
        "created_at": utc_now(),
        "seed": args.seed,
        "ui_item_count": len(ui_manifest["items"]),
        "bbox_item_count": len(bbox_manifest["items"]),
        "blind_review": True,
        "status": "ready_for_review",
    }
    write_json(audit_dir / "audit.json", audit)
    write_json(audit_dir / "ui_manifest.json", ui_manifest)
    write_json(audit_dir / "ui_reference.json", ui_reference)
    write_json(audit_dir / "bbox_manifest.json", bbox_manifest)
    write_json(audit_dir / "bbox_reference.json", bbox_reference)
    write_json(
        audit_dir / "baseline_classifier_metrics.json",
        {
            "scope": "Current deterministic classifier versus all current verification-gold labels.",
            "item_count": len(items),
            "metrics": classifier_metrics_for_gold(items),
        },
    )
    print(f"Built {args.audit_id}: {len(ui_manifest['items'])} UI items, {len(bbox_manifest['items'])} bbox items")


if __name__ == "__main__":
    main()
