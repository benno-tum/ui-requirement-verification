from __future__ import annotations

import json
from pathlib import Path

from ui_verifier.requirements.schemas import CandidateRequirementFile
from ui_verifier.verification.label_validation import validate_verification_gold_item
from ui_verifier.verification.schemas import VerificationGoldFile


FLOW_ID = "pure_2010_split_merge"


def test_split_merge_runtime_candidates_round_trip_through_schema() -> None:
    candidate_path = Path(f"data/generated/candidate_requirements/{FLOW_ID}/candidate_requirements.json")
    candidate_file = CandidateRequirementFile.load(candidate_path)
    assert len(candidate_file.requirements) == 29
    assert len({item.requirement_id for item in candidate_file.requirements}) == 29
    assert sum(len(item.claims) > 1 for item in candidate_file.requirements) == 21
    assert not any(item.requirement_id.startswith("PURE-SM-FR-") for item in candidate_file.requirements)
    contextualized = {item.requirement_id: item for item in candidate_file.requirements}
    assert "3.5.3/req-2" in (contextualized["PURE-SM-REORDER-001"].parent_harvest_text or "")
    assert "3.8.3/req-1" in (contextualized["PURE-SM-LOG-001"].parent_harvest_text or "")


def test_split_merge_review_inventory_and_gold_are_complete() -> None:
    review_path = Path(f"data/annotations/requirement_inspection/pure/{FLOW_ID}_extraction_review.jsonl")
    gold_path = Path(f"data/annotations/verification_gold/{FLOW_ID}/verification_gold.json")
    review_rows = [json.loads(line) for line in review_path.read_text(encoding="utf-8").splitlines() if line]
    gold = VerificationGoldFile.load(gold_path)

    assert len(review_rows) == 51
    assert sum(row["record_type"] == "legacy_extraction" for row in review_rows) == 6
    assert sum(row.get("extraction_mode") == "explicit_req" for row in review_rows) == 13
    assert len(gold.items) == 29
    assert len({item.requirement_id for item in gold.items}) == 29
    assert not any(item.requirement_id.startswith("PURE-SM-FR-") for item in gold.items)
    explicit_rows = [
        row for row in review_rows
        if row.get("extraction_mode") == "explicit_req"
    ]
    assert all(row["review_decision"] == "exclude_from_runtime_contextual_fragment" for row in explicit_rows)
    assert all(row["benchmark_requirement_ids"] for row in explicit_rows)

    for item in gold.items:
        assert item.review_status in {"needs_review", "accepted"}
        assert item.annotated_by in {"codex_draft", "benno"}
        assert any(tag.startswith("pure_pdf_page:") for tag in item.tags)
        assert 2 not in item.evidence_steps  # Decorative use-case diagram is not UI evidence.
        assert not validate_verification_gold_item(item).errors


def test_split_merge_baseline_covers_every_gold_requirement() -> None:
    gold_path = Path(f"data/annotations/verification_gold/{FLOW_ID}/verification_gold.json")
    prediction_path = Path(
        f"data/generated/verification_pipeline_runs/{FLOW_ID}_prelabel_gemini25_per_claim.json"
    )
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    predictions = json.loads(prediction_path.read_text(encoding="utf-8"))
    gold_ids = {item["requirement_id"] for item in gold["items"]}
    prediction_ids = {item["requirement_id"] for item in predictions["results"]}
    # The pre-label baseline predates contextualization, so it contains retired
    # raw fragments as well as every retained requirement.
    assert gold_ids.issubset(prediction_ids)
    diagnostics = predictions["metadata"]["gemini_image_verifier"]
    assert diagnostics["api_calls"] > 0
    assert diagnostics["fallbacks"] == 0
