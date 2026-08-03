from __future__ import annotations

import json
from pathlib import Path

import pytest

from ui_verifier.verification.label_validation import validate_verification_gold_item
from ui_verifier.verification.schemas import VerificationGoldFile


FLOW_ID = "pure_2010_split_merge"


def test_split_merge_accepted_requirements_round_trip_through_schema() -> None:
    gold_path = Path(f"data/annotations/verification_gold/{FLOW_ID}/verification_gold.json")
    gold = VerificationGoldFile.load(gold_path)
    assert len(gold.items) == 31
    assert len({item.requirement_id for item in gold.items}) == 31
    assert sum(len(item.claims) > 1 for item in gold.items) == 22
    assert {
        item.requirement_id
        for item in gold.items
        if item.requirement_id.startswith("PURE-SM-FR-")
    } == {
        "PURE-SM-FR-3_1-REQ-1",
        "PURE-SM-FR-3_3-REQ-1",
        "PURE-SM-FR-3_9-REQ-1",
    }
    accepted = {item.requirement_id: item for item in gold.items}
    repaired = accepted["PURE-REQ-004"]
    assert repaired.text.startswith("Mix options:")
    assert "The default behavior is to take one page from the first document" in repaired.text
    assert len(repaired.claims) == 5
    repaired_merge = accepted["PURE-REQ-003"]
    assert repaired_merge.text.startswith("In the Page Selection column")
    assert len(repaired_merge.claims) == 6
    assert "PURE-SM-MERGE-002" not in accepted


def test_split_merge_review_inventory_and_gold_are_complete() -> None:
    review_path = Path(f"data/annotations/requirement_inspection/pure/{FLOW_ID}_extraction_review.jsonl")
    gold_path = Path(f"data/annotations/verification_gold/{FLOW_ID}/verification_gold.json")
    review_rows = [json.loads(line) for line in review_path.read_text(encoding="utf-8").splitlines() if line]
    gold = VerificationGoldFile.load(gold_path)

    assert len(review_rows) == 51
    assert sum(row["record_type"] == "legacy_extraction" for row in review_rows) == 6
    assert sum(row.get("extraction_mode") == "explicit_req" for row in review_rows) == 13
    assert len(gold.items) == 31
    assert len({item.requirement_id for item in gold.items}) == 31
    explicit_rows = [
        row for row in review_rows
        if row.get("extraction_mode") == "explicit_req"
    ]
    assert sum(row["review_decision"] == "include_after_source_contextualization" for row in explicit_rows) == 3
    assert sum(row["review_decision"] == "exclude_from_runtime_contextual_fragment" for row in explicit_rows) == 10
    assert all(row["benchmark_requirement_ids"] for row in explicit_rows)

    pending_path = Path(f"data/annotations/requirements_candidate/{FLOW_ID}/candidate_requirements.json")
    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    assert pending["requirements"] == []

    for item in gold.items:
        assert item.review_status in {"needs_review", "accepted"}
        assert item.annotated_by in {"codex_draft", "benno"}
        assert any(tag.startswith("pure_pdf_page:") for tag in item.tags)
        assert 2 not in item.evidence_steps  # Decorative use-case diagram is not UI evidence.
        assert not validate_verification_gold_item(item).errors

    repaired_gold = next(item for item in gold.items if item.requirement_id == "PURE-REQ-004")
    assert repaired_gold.verification_label.value == "PARTIALLY_FULFILLED"
    assert [claim.status.value for claim in repaired_gold.claims] == [
        "SUPPORTED_WITH_CAVEAT",
        "SUPPORTED_WITH_CAVEAT",
        "SUPPORTED",
        "MISSING",
        "SUPPORTED",
    ]


def test_split_merge_baseline_covers_every_gold_requirement() -> None:
    gold_path = Path(f"data/annotations/verification_gold/{FLOW_ID}/verification_gold.json")
    prediction_path = Path(
        f"data/generated/verification_pipeline_runs/{FLOW_ID}_prelabel_gemini25_per_claim.json"
    )
    if not prediction_path.exists():
        pytest.skip("optional generated PURE baseline is not installed")
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
