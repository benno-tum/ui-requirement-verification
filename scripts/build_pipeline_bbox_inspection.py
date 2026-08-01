from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image

from ui_verifier.evaluation.review_audit import utc_now, write_json


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = (
    BASE_DIR
    / "data/generated/verification_pipeline_runs"
    / "bbox_gemini_grounded_regions_topk4_01_13_20260719"
)
DEFAULT_AUDIT_ROOT = BASE_DIR / "data/annotations/evaluation_audits"
DEFAULT_AUDIT_ID = "gemini_grounded_bbox_01_13_20260719"
DEFAULT_UI_AUDIT_ID = "ui_bbox_focused_20260717"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Expose a completed pipeline run package in the evidence-inspection gallery."
    )
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--audit-root", type=Path, default=DEFAULT_AUDIT_ROOT)
    parser.add_argument("--audit-id", default=DEFAULT_AUDIT_ID)
    parser.add_argument("--ui-audit-id", default=DEFAULT_UI_AUDIT_ID)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def image_size(image_path: Path) -> tuple[int, int]:
    with Image.open(image_path) as image:
        return int(image.width), int(image.height)


def preferred_inspection_image(image_path: Path) -> Path:
    source_width, source_height = image_size(image_path)
    candidates = [
        image_path.parent / "original" / image_path.name,
        image_path.parent / "originals" / image_path.name,
        image_path.parent / "full" / image_path.name,
        image_path.parent / "fullres" / image_path.name,
        image_path.parent / "hires" / image_path.name,
    ]
    valid = [candidate for candidate in candidates if candidate.is_file()]
    if not valid:
        return image_path
    return max(
        [image_path, *valid],
        key=lambda candidate: image_size(candidate)[0] * image_size(candidate)[1],
    )


def image_url(image_path: Path, flow_id: str) -> tuple[str, str]:
    parts = image_path.parts
    try:
        flows_index = parts.index("flows")
        dataset = parts[flows_index + 1]
        flow_index = parts.index(flow_id, flows_index + 2)
    except (ValueError, IndexError) as exc:
        raise ValueError(f"Cannot derive dataset from image path: {image_path}") from exc
    relative_asset = "/".join(parts[flow_index + 1 :])
    return dataset, f"/static/flows/{dataset}/{flow_id}/{relative_asset}"


def bbox_object(value: Any) -> dict[str, float] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    x1, y1, x2, y2 = (float(item) for item in value)
    if x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1:
        return None
    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}


def scale_bbox(
    bbox: dict[str, float],
    source_size: tuple[int, int],
    target_size: tuple[int, int],
) -> dict[str, float]:
    source_width, source_height = source_size
    target_width, target_height = target_size
    if source_width <= 0 or source_height <= 0:
        raise ValueError(f"Invalid source image size: {source_size}")
    scale_x = target_width / source_width
    scale_y = target_height / source_height
    return {
        "x1": max(0.0, min(float(target_width), bbox["x1"] * scale_x)),
        "y1": max(0.0, min(float(target_height), bbox["y1"] * scale_y)),
        "x2": max(0.0, min(float(target_width), bbox["x2"] * scale_x)),
        "y2": max(0.0, min(float(target_height), bbox["y2"] * scale_y)),
    }


def main() -> None:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    summary = load_json(run_dir / "summary.json")
    flow_summaries = summary.get("flows") if isinstance(summary.get("flows"), list) else []
    if not flow_summaries:
        raise ValueError("The run package summary contains no completed flows.")

    manifest_items: list[dict[str, Any]] = []
    reference_items: dict[str, dict[str, Any]] = {}
    item_number = 0
    for flow_summary in flow_summaries:
        flow_id = str(flow_summary.get("flow_id") or "")
        run_path = run_dir / f"{flow_id}.json"
        run = load_json(run_path)
        for result in run.get("results", []):
            if not isinstance(result, dict):
                continue
            for claim in result.get("claims", []):
                if not isinstance(claim, dict):
                    continue
                for evidence_number, evidence in enumerate(claim.get("evidence", []), start=1):
                    if not isinstance(evidence, dict):
                        continue
                    bbox = bbox_object(evidence.get("bbox"))
                    metadata = evidence.get("bbox_metadata")
                    if bbox is None or not isinstance(metadata, dict):
                        continue
                    source = str(metadata.get("source") or "")
                    if not (
                        source.startswith("gemini_visual_grounding")
                        or source.startswith("local_omniparser")
                    ):
                        continue
                    path_value = metadata.get("image_path") or evidence.get("screenshot_path")
                    source_image_path = Path(str(path_value)).resolve()
                    if not source_image_path.is_file():
                        raise FileNotFoundError(source_image_path)
                    source_width = int(metadata.get("image_width") or 0)
                    source_height = int(metadata.get("image_height") or 0)
                    if source_width <= 0 or source_height <= 0 or bbox["x2"] > source_width or bbox["y2"] > source_height:
                        raise ValueError(f"Invalid bounding-box metadata for {flow_id} {claim.get('claim_id')}")
                    image_path = preferred_inspection_image(source_image_path)
                    width, height = image_size(image_path)
                    display_bbox = scale_bbox(
                        bbox,
                        (source_width, source_height),
                        (width, height),
                    )
                    dataset, asset_url = image_url(image_path, flow_id)
                    item_number += 1
                    item_id = f"GBBOX-{item_number:04d}"
                    description = str(
                        metadata.get("description")
                        or evidence.get("visible_observation")
                        or "Selected supporting region"
                    )
                    confidence = float(evidence.get("confidence") or claim.get("confidence") or 0.0)
                    manifest_items.append(
                        {
                            "audit_item_id": item_id,
                            "dataset": dataset,
                            "flow_id": flow_id,
                            "requirement_id": result.get("requirement_id"),
                            "requirement_text": result.get("requirement_text"),
                            "claim_id": claim.get("claim_id"),
                            "claim_text": claim.get("claim_text"),
                            "step_index": int(evidence.get("step_index") or 0),
                            "evidence_region_index": evidence_number,
                            "image_url": asset_url,
                            "image_path": str(image_path),
                            "image_width": width,
                            "image_height": height,
                            "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                            "coordinate_space": str(metadata.get("coordinate_space") or "image_pixels"),
                        }
                    )
                    reference_items[item_id] = {
                        "prediction": {
                            "bbox": display_bbox,
                            "matched_text": description,
                            "score": confidence,
                            "confidence": confidence,
                            "source": source,
                            "level": str(metadata.get("localizability") or metadata.get("role") or "region"),
                            "image_path": str(image_path),
                            "image_width": width,
                            "image_height": height,
                            "coordinate_space": str(metadata.get("coordinate_space") or "image_pixels"),
                            "source_image_path": str(source_image_path),
                            "source_image_width": source_width,
                            "source_image_height": source_height,
                            "scale_x": width / source_width,
                            "scale_y": height / source_height,
                            "raw_gemini_pixel_bbox": metadata.get("raw_gemini_pixel_bbox"),
                            "ocr_refinement": metadata.get("ocr_refinement"),
                            "candidate_id": metadata.get("candidate_id"),
                            "candidate_source": metadata.get("candidate_source"),
                        },
                        "all_suggestions": [],
                        "claim_status": claim.get("status"),
                        "claim_type": "OBSERVABLE" if claim.get("is_observable") else "HIDDEN",
                        "source_group": "pipeline_verification",
                        "run_id": summary.get("run_id"),
                        "execution_mode": flow_summary.get("execution_mode"),
                    }

    if item_number != int(summary.get("totals", {}).get("bounding_boxes") or -1):
        raise ValueError(
            f"Converted {item_number} boxes, but the package summary reports "
            f"{summary.get('totals', {}).get('bounding_boxes')}."
        )

    audit_dir = args.audit_root / args.audit_id
    audit_dir.mkdir(parents=True, exist_ok=True)
    source_ui_dir = args.audit_root / args.ui_audit_id
    ui_manifest = load_json(source_ui_dir / "ui_manifest.json")
    ui_reference = load_json(source_ui_dir / "ui_reference.json")
    created_at = utc_now()
    configuration = summary.get("configuration", {})
    flow_count = len(flow_summaries)
    image_variant = str(configuration.get("image_variant") or "unspecified")
    flow_label = "flow" if flow_count == 1 else "flows"
    bbox_sources = summary.get("totals", {}).get("bbox_sources", {})
    prompt_version = str(configuration.get("prompt_version") or "")
    if configuration.get("claim_decomposition_policy") == "disabled" and configuration.get("top_k") == 4:
        grounding_label = "REALISTIC TOP-K: Gemini 3.1 Flash-Lite, raw requirements, no claim decomposition, joint UI/fulfillment/grounding"
    elif str(configuration.get("model") or "") == "gemini-3.1-flash-lite" and "CANDIDATE_MARKS" in prompt_version:
        grounding_label = "JOINT RUN: Gemini 3.1 Flash-Lite verifies claims and selects OmniParser/OCR regions in one prompt"
    elif prompt_version == "GEMINI25_OMNIMARK_SELECTION_V7_CLAIM_FACT_COVERAGE_MAX2":
        grounding_label = "PILOT V7 FACT COVERAGE: Gemini 2.5 Flash + OmniParser/OCR, claim-derived evidence coverage, max 2"
    elif prompt_version == "GEMINI25_OMNIMARK_SELECTION_V6_GENERAL_SUFFICIENCY_MAX2":
        grounding_label = "PILOT V6 GENERAL: Gemini 2.5 Flash + OmniParser/OCR, containment and sufficiency, max 2"
    elif prompt_version == "GEMINI25_OMNIMARK_SELECTION_V5_CONTAINMENT_MAX2":
        grounding_label = "RECOMMENDED V5 CONTAINMENT: Gemini 2.5 Flash + OmniParser/OCR, verified containment, max 2"
    elif prompt_version == "GEMINI25_OMNIMARK_SELECTION_V4_SPARSE_MAX2":
        grounding_label = "RECOMMENDED V4 SPARSE: Gemini 2.5 Flash + OmniParser/OCR, one region by default, max 2"
    elif prompt_version == "GEMINI25_OMNIMARK_SELECTION_V3_ATLAS_MAX4":
        grounding_label = "RECOMMENDED V3: Gemini 2.5 Flash + OmniParser atlas, semantic merge, max 4"
    elif prompt_version == "GEMINI25_OMNIMARK_SELECTION_V2_ATLAS":
        grounding_label = "PILOT V2: Gemini 2.5 Flash + isolated OmniParser crop atlas"
    elif isinstance(bbox_sources, dict) and "local_omniparser_florence_ocr_ranked" in bbox_sources:
        grounding_label = "LOCAL PILOT: OmniParser + Florence + OCR top-ranked boxes"
    elif isinstance(bbox_sources, dict) and "gemini_visual_grounding_omnimark_selection" in bbox_sources:
        grounding_label = "PILOT: Gemini 2.5 Flash selects OmniParser/OCR marks"
    elif isinstance(bbox_sources, dict) and "gemini_visual_grounding_omniparser_candidate_marks" in bbox_sources:
        grounding_label = "Gemini + OmniParser candidate-mark grounding"
    elif isinstance(bbox_sources, dict) and "gemini_visual_grounding_ocr_refined" in bbox_sources:
        grounding_label = "Gemini + OCR-refined grounding"
    else:
        grounding_label = "Gemini grounding rerun"
    write_json(
        audit_dir / "audit.json",
        {
            "audit_id": args.audit_id,
            "title": (
                f"{grounding_label} — {flow_count} {flow_label} "
                f"({image_variant} input, high-resolution review)"
            ),
            "created_at": created_at,
            "seed": 20260719,
            "ui_item_count": len(ui_manifest.get("items", [])),
            "bbox_item_count": item_number,
            "blind_review": False,
            "status": "completed_pipeline_inspection",
            "run_id": summary.get("run_id"),
            "bbox_source": next(iter(bbox_sources), "unknown") if isinstance(bbox_sources, dict) else "unknown",
        },
    )
    write_json(audit_dir / "ui_manifest.json", ui_manifest)
    write_json(audit_dir / "ui_reference.json", ui_reference)
    write_json(
        audit_dir / "bbox_manifest.json",
        {
            "schema_version": "bbox_inspection_manifest_v1",
            "created_at": created_at,
            "source_run_id": summary.get("run_id"),
            "source_run_created_at": summary.get("created_at"),
            "source_run_configuration": summary.get("configuration", {}),
            "items": manifest_items,
        },
    )
    write_json(
        audit_dir / "bbox_reference.json",
        {
            "schema_version": "bbox_inspection_reference_v1",
            "created_at": created_at,
            "source_run_id": summary.get("run_id"),
            "items": reference_items,
        },
    )
    print(f"Built {args.audit_id}: {item_number} evidence regions")


if __name__ == "__main__":
    main()
