from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from PIL import Image

from ui_verifier.localization.candidate_ranking import rank_candidates


BASE_DIR = Path(__file__).resolve().parents[1]
FLOW_ID = "02_gamestop_a2500e0b-9244-4f0e-b686-fa290c32b829"
DEFAULT_SOURCE_RUN = (
    BASE_DIR
    / "data/generated/verification_pipeline_runs/bbox_gemini31pro_singlecall_allimages_01_13_20260719"
    / f"{FLOW_ID}.json"
)
DEFAULT_CANDIDATES = BASE_DIR / "data/generated/omniparser_candidate_marks/flow02_20260720/candidates.json"
DEFAULT_OUTPUT_DIR = (
    BASE_DIR
    / "data/generated/verification_pipeline_runs/bbox_local_omniparser_florence_flow02_20260720"
)
RUN_ID = "bbox_local_omniparser_florence_flow02_20260720"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a reviewable local top-1 candidate-box run.")
    parser.add_argument("--source-run", type=Path, default=DEFAULT_SOURCE_RUN)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def image_for_evidence(evidence: dict[str, Any]) -> Path:
    metadata = evidence.get("bbox_metadata") or {}
    path = Path(str(evidence.get("screenshot_path") or metadata.get("image_path") or "")).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def semantic_description(candidate: dict[str, Any]) -> str:
    content = candidate.get("caption") or candidate.get("text") or candidate.get("associated_text")
    return f"Local rank #{candidate['rank']} {candidate['candidate_id']}{f': {content}' if content else ''}"


def main() -> None:
    args = parse_args()
    source = load_json(args.source_run)
    package = load_json(args.candidates)
    if package.get("flow_id") != source.get("flow_id"):
        raise ValueError("Candidate package and source run have different flow IDs.")
    steps = package.get("steps") or {}
    run = deepcopy(source)
    box_count = 0
    source_counts: Counter[str] = Counter()

    for result in run.get("results", []):
        requirement_text = str(result.get("requirement_text") or "")
        for claim in result.get("claims", []):
            claim_text = str(claim.get("claim_text") or "")
            evidence_by_step: dict[int, dict[str, Any]] = {}
            for evidence in claim.get("evidence", []):
                step = int(evidence.get("step_index") or 0)
                if step > 0:
                    evidence_by_step.setdefault(step, evidence)
            local_evidence: list[dict[str, Any]] = []
            for step, old_evidence in sorted(evidence_by_step.items()):
                candidates = steps.get(str(step))
                if not isinstance(candidates, list) or not candidates:
                    continue
                image_path = image_for_evidence(old_evidence)
                with Image.open(image_path) as image:
                    width, height = image.size
                ranked = rank_candidates(
                    candidates,
                    claim_text=claim_text,
                    requirement_text=requirement_text,
                    image_width=width,
                    image_height=height,
                )
                if not ranked:
                    continue
                selected = ranked[0]
                bbox = [float(value) for value in selected["bbox"]]
                score = float(selected.get("rank_score") or 0.0)
                description = semantic_description(selected)
                source_name = "local_omniparser_florence_ocr_ranked"
                local_evidence.append(
                    {
                        **old_evidence,
                        "bbox": bbox,
                        "visible_observation": description,
                        "confidence": score,
                        "bbox_metadata": {
                            "image_path": str(image_path),
                            "image_width": width,
                            "image_height": height,
                            "coordinate_space": "image_pixels",
                            "source": source_name,
                            "role": "SUPPORTING",
                            "localizability": "LOCAL_REGION",
                            "description": description,
                            "candidate_id": selected.get("candidate_id"),
                            "candidate_source": selected.get("source"),
                            "candidate_caption": selected.get("caption"),
                            "candidate_text": selected.get("text"),
                            "associated_ocr_text": selected.get("associated_text"),
                            "rank": selected.get("rank"),
                            "rank_score": score,
                            "rank_reasons": selected.get("rank_reasons") or [],
                            "ranking_method": "local_florence_caption_plus_ocr_tfidf_v1",
                            "caption_model": "microsoft/OmniParser-v2.0/icon_caption",
                            "caption_model_sha256": (package.get("local_captioning") or {}).get("model_sha256"),
                            "previous_bbox": old_evidence.get("bbox"),
                            "previous_bbox_metadata": old_evidence.get("bbox_metadata"),
                        },
                        "metadata": {
                            **(old_evidence.get("metadata") or {}),
                            "grounding_method": "local_omniparser_florence_ocr_ranked",
                            "grounding_hosted_api_calls": 0,
                        },
                    }
                )
                box_count += 1
                source_counts[source_name] += 1
            claim["evidence"] = local_evidence
        result["evidence"] = [
            evidence
            for claim in result.get("claims", [])
            for evidence in claim.get("evidence", [])
        ]

    created_at = utc_now()
    run["metadata"] = {
        **(run.get("metadata") or {}),
        "run_id": RUN_ID,
        "created_at": created_at,
        "source_run": str(args.source_run.resolve()),
        "grounding_method": "local_omniparser_florence_ocr_ranked",
        "hosted_grounding_api_calls": 0,
        "candidate_package": str(args.candidates.resolve()),
    }
    labels = Counter(str(result.get("final_label") or "UNKNOWN") for result in run.get("results", []))
    claims = [claim for result in run.get("results", []) for claim in result.get("claims", [])]
    summary = {
        "schema_version": "local_candidate_bbox_run_set_v1",
        "run_id": RUN_ID,
        "created_at": created_at,
        "configuration": {
            "model": "microsoft/OmniParser-v2.0/icon_caption + Tesseract + deterministic ranking",
            "requested_execution_mode": "offline-local-candidate-ranking",
            "image_variant": "preferred-original",
            "claim_decomposition_policy": "provided/preserved",
            "aggregation": "preserved from Gemini 3.1 Pro source run",
            "grounding": "Local OmniParser UI proposals and OCR lines, Florence captions, deterministic claim-specific top-1 ranking",
            "hosted_grounding_api_calls": 0,
        },
        "fallback_flows": [],
        "totals": {
            "flows": 1,
            "requirements": len(run.get("results", [])),
            "claims": len(claims),
            "evidence_records": box_count,
            "bounding_boxes": box_count,
            "bbox_sources": dict(source_counts),
            "estimated_cost_usd": 0.0,
        },
        "flows": [
            {
                "flow_id": FLOW_ID,
                "execution_mode": "offline-local-candidate-ranking",
                "requirements": len(run.get("results", [])),
                "claims": len(claims),
                "evidence_records": box_count,
                "bounding_boxes": box_count,
                "bbox_sources": dict(source_counts),
                "labels": dict(labels),
                "api_calls": 0,
                "fallbacks": 0,
                "prompt_version": None,
            }
        ],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / f"{FLOW_ID}.json").write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Built {RUN_ID}: {box_count} local top-ranked evidence boxes")


if __name__ == "__main__":
    main()
