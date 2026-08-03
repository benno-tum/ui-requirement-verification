from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT = (
    BASE_DIR
    / "data/annotations/evaluation_audits/rq3_final_20260802"
    / "rq3_author_error_audit_form.json"
)
DEFAULT_BATCHES = (
    BASE_DIR
    / "outputs/019fbfa1-94d4-7bb1-9a8a-81dd427302cf"
    / "rq3_chatgpt_multimodal_batches_20260802"
)
DEFAULT_OUTPUT = DEFAULT_BATCHES / "rq3_llm_visual_draft_error_audit_form.json"

LABELS = {"FULFILLED", "PARTIALLY_FULFILLED", "NOT_FULFILLED", "ABSTAIN"}
PRIMARY_CATEGORIES = {
    "UNSAFE_OVER_FULFILLMENT",
    "UNSUPPORTED_CONCRETE_NEGATIVE",
    "EXCESSIVE_ABSTENTION",
    "EVIDENCE_SELECTION_MISS",
    "EVIDENCE_INTERPRETATION_ERROR",
    "LABEL_BOUNDARY_DISAGREEMENT",
    "GOLD_REVIEW_CANDIDATE",
    "APPROPRIATE_ABSTENTION",
    "TRACEABILITY_FAILURE",
    "PREDICTION_INSTABILITY",
}
REQUIREMENT_TAGS = {
    "UNIVERSAL_OR_COMPLETENESS",
    "COMPARATIVE_OR_DISTINCT",
    "HIDDEN_BACKEND_OR_EXTERNAL",
    "PERSISTENCE_OR_CROSS_STEP",
    "LATE_RESULT_OR_CART_STATE",
    "MULTI_SCREEN_COMPOSITION",
    "NEGATION_OR_CONTRASTIVE",
    "LABEL_SCHEMA_AMBIGUITY",
    "ORDINARY_LOCAL_UI",
}
EVIDENCE_TAGS = {
    "DECISIVE_STEP_SELECTED",
    "DECISIVE_STEP_NOT_SELECTED",
    "ONLY_ENTRY_POINT_VISIBLE",
    "ACTION_WITHOUT_RESULT",
    "PARTIAL_CLAIM_COVERAGE",
    "NO_OBSERVABLE_PROXY",
    "LATE_STEP",
    "CROSS_STEP_STATE",
    "EVIDENCE_CORRECT_BUT_RATIONALE_WRONG",
    "LABEL_CORRECT_BUT_TRACEABILITY_WRONG",
    "RUN_INSTABILITY",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate ChatGPT multimodal RQ3 batch results and merge them into a "
            "separate LLM-visual draft without changing author-review fields."
        )
    )
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--batches-dir", type=Path, default=DEFAULT_BATCHES)
    parser.add_argument("--results-dir", type=Path)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Merge valid available batches and report missing batches.",
    )
    return parser.parse_args()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_unique(values: list[str], label: str) -> None:
    duplicates = [value for value, count in Counter(values).items() if count > 1]
    require(not duplicates, f"duplicate {label}: {duplicates[:10]}")


def validate_result(
    result: dict[str, Any],
    expected_batch: dict[str, Any],
    expected_items: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    batch_id = expected_batch["batch_id"]
    prefix = f"{batch_id}: "
    require(result.get("schema_version") == "rq3_multimodal_llm_visual_review_v1", prefix + "wrong schema_version")
    require(result.get("batch_id") == batch_id, prefix + "wrong batch_id")
    require(result.get("flow_id") == expected_batch["flow_id"], prefix + "wrong flow_id")

    attestation = result.get("visual_inspection_attestation")
    require(isinstance(attestation, dict), prefix + "missing visual_inspection_attestation")
    require(attestation.get("inspected_all_attached_screenshots") is True, prefix + "visual inspection is not attested")
    unreadable = attestation.get("unreadable_or_uninspected_steps")
    require(isinstance(unreadable, list), prefix + "unreadable steps must be a list")
    require(not unreadable, prefix + f"contains unreadable or uninspected steps: {unreadable}")

    expected_requirement_ids = sorted({str(item["requirement_id"]) for item in expected_items})
    assessments = result.get("requirement_assessments")
    require(isinstance(assessments, list), prefix + "missing requirement_assessments")
    assessment_ids = [str(value.get("requirement_id")) for value in assessments if isinstance(value, dict)]
    require(len(assessment_ids) == len(assessments), prefix + "malformed requirement assessment")
    require_unique(assessment_ids, prefix + "requirement assessment IDs")
    require(sorted(assessment_ids) == expected_requirement_ids, prefix + "requirement IDs do not match batch")
    assessment_by_id: dict[str, dict[str, Any]] = {}
    for assessment in assessments:
        requirement_id = str(assessment["requirement_id"])
        require(str(assessment.get("visible_observations") or "").strip(), prefix + f"empty visual observation for {requirement_id}")
        require(assessment.get("visually_supported_label") in LABELS, prefix + f"invalid visual label for {requirement_id}")
        require(isinstance(assessment.get("relevant_steps"), list), prefix + f"missing relevant steps for {requirement_id}")
        require(isinstance(assessment.get("unobservable_or_missing_aspects"), list), prefix + f"missing unobservable list for {requirement_id}")
        confidence = assessment.get("confidence")
        require(isinstance(confidence, (int, float)) and 0 <= confidence <= 1, prefix + f"invalid confidence for {requirement_id}")
        assessment_by_id[requirement_id] = assessment

    expected_audit_ids = [str(item["audit_item_id"]) for item in expected_items]
    reviews = result.get("row_reviews")
    require(isinstance(reviews, list), prefix + "missing row_reviews")
    review_ids = [str(value.get("audit_item_id")) for value in reviews if isinstance(value, dict)]
    require(len(review_ids) == len(reviews), prefix + "malformed row review")
    require_unique(review_ids, prefix + "row review IDs")
    require(set(review_ids) == set(expected_audit_ids), prefix + "audit item IDs do not match batch")
    review_by_id: dict[str, dict[str, Any]] = {}
    for review in reviews:
        audit_id = str(review["audit_item_id"])
        require(isinstance(review.get("decisive_evidence_supplied"), bool), prefix + f"invalid decisive evidence flag for {audit_id}")
        require(review.get("primary_category") in PRIMARY_CATEGORIES, prefix + f"invalid primary category for {audit_id}")
        requirement_tags = review.get("requirement_tags")
        evidence_tags = review.get("evidence_tags")
        require(isinstance(requirement_tags, list) and requirement_tags, prefix + f"missing requirement tags for {audit_id}")
        require(isinstance(evidence_tags, list) and evidence_tags, prefix + f"missing evidence tags for {audit_id}")
        require(set(requirement_tags) <= REQUIREMENT_TAGS, prefix + f"invalid requirement tag for {audit_id}")
        require(set(evidence_tags) <= EVIDENCE_TAGS, prefix + f"invalid evidence tag for {audit_id}")
        require(str(review.get("visible_evidence_rationale") or "").strip(), prefix + f"empty rationale for {audit_id}")
        require(isinstance(review.get("gold_review_candidate"), bool), prefix + f"invalid gold flag for {audit_id}")
        confidence = review.get("confidence")
        require(isinstance(confidence, (int, float)) and 0 <= confidence <= 1, prefix + f"invalid confidence for {audit_id}")
        require(review.get("review_status") == "LLM_VISUAL_DRAFT_COMPLETE", prefix + f"wrong review status for {audit_id}")
        review_by_id[audit_id] = review
    return assessment_by_id, review_by_id


def main() -> None:
    args = parse_args()
    batches_dir = args.batches_dir.resolve()
    results_dir = (args.results_dir or (batches_dir / "results_inbox")).resolve()
    manifest = load_object(batches_dir / "batch_manifest.json")
    audit = load_object(args.audit.resolve())
    items = audit.get("items")
    require(isinstance(items, list), "audit has no items list")
    expected_by_flow: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        expected_by_flow.setdefault(str(item["flow_id"]), []).append(item)

    merged = deepcopy(audit)
    merged_item_by_id = {str(item["audit_item_id"]): item for item in merged["items"]}
    all_assessments: dict[tuple[str, str], dict[str, Any]] = {}
    completed_batches: list[str] = []
    missing_batches: list[str] = []
    result_files: list[str] = []

    for batch in manifest["batches"]:
        result_path = results_dir / batch["result_filename"]
        if not result_path.is_file():
            missing_batches.append(str(batch["batch_id"]))
            continue
        result = load_object(result_path)
        assessments, reviews = validate_result(
            result,
            batch,
            expected_by_flow[str(batch["flow_id"])],
        )
        for requirement_id, assessment in assessments.items():
            all_assessments[(str(batch["flow_id"]), requirement_id)] = assessment
        for audit_id, review in reviews.items():
            merged_item_by_id[audit_id]["llm_visual_review"] = review
        completed_batches.append(str(batch["batch_id"]))
        result_files.append(str(result_path.relative_to(BASE_DIR)))

    if missing_batches and not args.allow_incomplete:
        raise SystemExit(
            f"missing {len(missing_batches)} result batches: {', '.join(missing_batches)}; "
            "use --allow-incomplete only for a progress draft"
        )

    merged["schema_version"] = "rq3_llm_visual_draft_v1"
    merged["llm_visual_review_metadata"] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "COMPLETE" if not missing_batches else "INCOMPLETE",
        "review_surface": "ChatGPT web",
        "requested_model": "GPT-5.6 Sol High",
        "author_review_fields_modified": False,
        "completed_batches": completed_batches,
        "missing_batches": missing_batches,
        "result_files": result_files,
        "requirement_assessments": [
            {
                "flow_id": flow_id,
                **assessment,
            }
            for (flow_id, _), assessment in sorted(all_assessments.items())
        ],
        "caution": (
            "This is an LLM-assisted visual draft. It must not be described as "
            "completed author coding until the author confirms or corrects it."
        ),
    }
    output = args.out.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"status={merged['llm_visual_review_metadata']['status']} "
        f"batches={len(completed_batches)}/{len(manifest['batches'])} "
        f"rows={sum('llm_visual_review' in item for item in merged['items'])}/{len(merged['items'])} "
        f"out={output}"
    )


if __name__ == "__main__":
    main()
