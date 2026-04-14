from pathlib import Path

from ui_verifier.requirement_inspection.schemas import (
    AnnotationConfidence,
    NonEvaluableReason,
    RequirementInspectionType,
    UiEvaluability,
    VisibleSubtype,
)
from ui_verifier.requirements.candidate_generation import (
    build_verification_candidates,
    normalize_model_candidates,
    normalize_model_harvest,
)
from ui_verifier.requirements.schemas import (
    BenchmarkDecision,
    CandidateOrigin,
    RequirementReviewStatus,
)


def test_normalize_model_harvest_and_build_candidates(tmp_path: Path) -> None:
    prompt_path = tmp_path / "gemini_prompt.txt"
    prompt_path.write_text("prompt", encoding="utf-8")

    parsed = {
        "requirements": [
            {
                "id": "HARV-01",
                "harvested_text": "The system shall provide a pickup location input field.",
                "requirement_type": "FR",
                "ui_evaluability": "UI_VERIFIABLE",
                "non_evaluable_reason": "NONE",
                "visible_subtype": "TEXT_OR_ELEMENT_PRESENCE",
                "task_relevance": "HIGH",
                "evidence_steps": [1],
                "confidence": "HIGH",
                "rationale": "The field is clearly visible.",
                "visible_core_candidate": None,
            },
            {
                "id": "HARV-02",
                "harvested_text": "The system shall send an email confirmation after booking.",
                "requirement_type": "FR",
                "ui_evaluability": "PARTIALLY_UI_VERIFIABLE",
                "non_evaluable_reason": "EXTERNAL_INTEGRATION",
                "visible_subtype": "VALIDATION_OR_FEEDBACK",
                "task_relevance": "MEDIUM",
                "evidence_steps": [4],
                "confidence": "MEDIUM",
                "rationale": "A confirmation state is visible, but email delivery is external.",
                "visible_core_candidate": "The system shall display a booking confirmation message after submission.",
            },
            {
                "id": "HARV-03",
                "harvested_text": "The system shall keep an unalterable audit trail.",
                "requirement_type": "NFR",
                "ui_evaluability": "NOT_UI_VERIFIABLE",
                "non_evaluable_reason": "BACKEND_HIDDEN_STATE",
                "visible_subtype": "NONE",
                "task_relevance": "LOW",
                "evidence_steps": [4],
                "confidence": "HIGH",
                "rationale": "This is not visible from screenshots.",
                "visible_core_candidate": None,
            },
        ]
    }

    harvest_file = normalize_model_harvest(
        parsed=parsed,
        flow_id="flow-1",
        model_name="gemini-test",
        prompt_path=prompt_path,
        allowed_steps=[1, 4],
    )

    assert len(harvest_file.requirements) == 3
    assert harvest_file.requirements[0].confidence == AnnotationConfidence.HIGH
    assert harvest_file.requirements[1].ui_evaluability == UiEvaluability.PARTIALLY_UI_VERIFIABLE
    assert harvest_file.requirements[2].non_evaluable_reason == NonEvaluableReason.BACKEND_HIDDEN_STATE

    candidate_file = build_verification_candidates(harvest_file)
    assert len(candidate_file.requirements) == 3

    direct = candidate_file.requirements[0]
    assert direct.benchmark_decision == BenchmarkDecision.DIRECT_INCLUDE
    assert direct.candidate_origin == CandidateOrigin.DIRECT_FROM_HARVEST
    assert direct.review_status == RequirementReviewStatus.CANDIDATE
    assert direct.ui_evaluability == UiEvaluability.UI_VERIFIABLE
    assert direct.requirement_type == RequirementInspectionType.FR
    assert direct.visible_subtype == VisibleSubtype.TEXT_OR_ELEMENT_PRESENCE

    partial = candidate_file.requirements[1]
    assert partial.benchmark_decision == BenchmarkDecision.DIRECT_INCLUDE
    assert partial.candidate_origin == CandidateOrigin.DIRECT_FROM_HARVEST
    assert partial.text == "The system shall send an email confirmation after booking."
    assert partial.parent_harvest_text is None
    assert partial.ui_evaluability == UiEvaluability.PARTIALLY_UI_VERIFIABLE
    assert partial.non_evaluable_reason == NonEvaluableReason.EXTERNAL_INTEGRATION

    excluded = candidate_file.requirements[2]
    assert excluded.benchmark_decision == BenchmarkDecision.EXCLUDE_FROM_VERIFICATION_BENCHMARK
    assert excluded.review_status == RequirementReviewStatus.REJECTED
    assert excluded.excluded_reason == NonEvaluableReason.BACKEND_HIDDEN_STATE



def test_normalize_model_candidates_preserves_partial_direct_include(tmp_path: Path) -> None:
    prompt_path = tmp_path / "gemini_prompt.txt"
    prompt_path.write_text("prompt", encoding="utf-8")

    harvest_file = normalize_model_harvest(
        parsed={
            "requirements": [
                {
                    "id": "HARV-01",
                    "harvested_text": "The system shall allow users to set a preferred home store.",
                    "requirement_type": "FR",
                    "ui_evaluability": "PARTIALLY_UI_VERIFIABLE",
                    "non_evaluable_reason": "BACKEND_HIDDEN_STATE",
                    "visible_subtype": "TEXT_OR_ELEMENT_PRESENCE",
                    "task_relevance": "HIGH",
                    "evidence_steps": [4],
                    "confidence": "HIGH",
                    "rationale": "The UI shows the action but not whether the preference persists.",
                    "visible_core_candidate": "The system shall display a control to set a preferred home store.",
                }
            ]
        },
        flow_id="flow-2",
        model_name="gemini-test",
        prompt_path=prompt_path,
        allowed_steps=[4],
    )

    parsed_candidates = {
        "requirements": [
            {
                "id": "REQ-01",
                "source_harvest_id": "HARV-01",
                "candidate_text": "The system shall allow users to set a preferred home store.",
                "requirement_type": "FR",
                "ui_evaluability": "PARTIALLY_UI_VERIFIABLE",
                "non_evaluable_reason": "BACKEND_HIDDEN_STATE",
                "visible_subtype": "TEXT_OR_ELEMENT_PRESENCE",
                "benchmark_decision": "DIRECT_INCLUDE",
                "candidate_origin": "DIRECT_FROM_HARVEST",
                "normalization_notes": "Kept the broader feature because the persistence aspect is intentionally only partially visible.",
            }
        ]
    }

    candidate_file = normalize_model_candidates(
        parsed=parsed_candidates,
        harvest_file=harvest_file,
        model_name="gemini-rewrite",
        prompt_path=tmp_path / "candidate_rewrite_prompt.txt",
    )

    assert len(candidate_file.requirements) == 1
    requirement = candidate_file.requirements[0]
    assert requirement.benchmark_decision == BenchmarkDecision.DIRECT_INCLUDE
    assert requirement.candidate_origin == CandidateOrigin.DIRECT_FROM_HARVEST
    assert requirement.ui_evaluability == UiEvaluability.PARTIALLY_UI_VERIFIABLE
    assert requirement.non_evaluable_reason == NonEvaluableReason.BACKEND_HIDDEN_STATE
    assert requirement.parent_harvest_text is None
    assert "intentionally only partially visible" in (requirement.rationale or "")
