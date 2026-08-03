from __future__ import annotations

import json
from pathlib import Path

from ui_verifier.requirements.schemas import CandidateRequirementFile


FLOW_ID = "pure_2010_mashboot"


def test_mashboot_candidates_are_document_contextualized() -> None:
    candidate_path = Path(f"data/annotations/requirements_candidate/{FLOW_ID}/candidate_requirements.json")
    candidates = CandidateRequirementFile.load(candidate_path)

    assert len(candidates.requirements) == 11
    assert len({item.requirement_id for item in candidates.requirements}) == 11
    assert sum(len(item.claims) > 1 for item in candidates.requirements) == 10
    assert sum(len(item.claims) for item in candidates.requirements) == 42
    assert all(item.candidate_origin.value == "VISIBLE_CORE_REWRITE" for item in candidates.requirements)
    assert all(item.benchmark_decision.value == "REWRITE_TO_VISIBLE_CORE" for item in candidates.requirements)
    assert all(item.parent_harvest_text for item in candidates.requirements)


def test_mashboot_review_retains_raw_requirements_without_promoting_them() -> None:
    review_path = Path(f"data/annotations/requirement_inspection/pure/{FLOW_ID}_extraction_review.jsonl")
    rows = [json.loads(line) for line in review_path.read_text(encoding="utf-8").splitlines() if line]

    raw = [row for row in rows if row.get("record_type") == "pdf_extraction"]
    sections = [row for row in rows if row.get("record_type") == "document_section"]
    legacy = [row for row in rows if row.get("record_type") == "legacy_extraction"]
    assert len(raw) == 59
    assert len(sections) == 6
    assert len(legacy) == 1
    assert legacy[0]["review_decision"] == "retire_concatenated_use_cases"
    assert all(row["review_decision"] != "include_verbatim" for row in raw)
    assert any(row["benchmark_requirement_ids"] for row in raw)
    assert all(row.get("source_document") == "data/raw/pure/req/2010 - mashboot.pdf" for row in rows)
