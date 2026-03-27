from pathlib import Path

from ui_verifier.requirement_inspection.schemas import (
    AnnotationConfidence,
    NonEvaluableReason,
    RequirementInspectionType,
    UiEvaluability,
    VisibleSubtype,
)
from ui_verifier.requirements.schemas import (
    BenchmarkDecision,
    CandidateOrigin,
    CandidateRequirement,
    CandidateRequirementFile,
    HarvestedRequirement,
    HarvestedRequirementFile,
    RequirementReviewStatus,
    RequirementScope,
    TaskRelevance,
)


def test_harvested_requirement_file_roundtrip(tmp_path: Path) -> None:
    harvest_file = HarvestedRequirementFile(
        dataset="mind2web",
        flow_id="flow-1",
        requirements=[
            HarvestedRequirement(
                harvest_id="HARV-01",
                flow_id="flow-1",
                harvested_text="The system shall show a confirmation banner.",
                requirement_type=RequirementInspectionType.FR,
                ui_evaluability=UiEvaluability.UI_VERIFIABLE,
                non_evaluable_reason=NonEvaluableReason.NONE,
                visible_subtype=VisibleSubtype.VALIDATION_OR_FEEDBACK,
                task_relevance=TaskRelevance.HIGH,
                step_indices=[3],
                confidence=AnnotationConfidence.HIGH,
            )
        ],
    )

    path = tmp_path / "harvested_requirements.json"
    harvest_file.save(path)
    loaded = HarvestedRequirementFile.load(path)

    assert loaded.to_dict() == harvest_file.to_dict()


def test_candidate_requirement_file_roundtrip_with_new_fields(tmp_path: Path) -> None:
    candidate_file = CandidateRequirementFile(
        dataset="mind2web",
        flow_id="flow-1",
        requirements=[
            CandidateRequirement(
                requirement_id="REQ-01",
                flow_id="flow-1",
                text="The system shall show a confirmation banner.",
                scope=RequirementScope.SINGLE_SCREEN,
                step_indices=[3],
                confidence=AnnotationConfidence.MEDIUM,
                source_harvest_id="HARV-01",
                candidate_origin=CandidateOrigin.DIRECT_FROM_HARVEST,
                benchmark_decision=BenchmarkDecision.DIRECT_INCLUDE,
                requirement_type=RequirementInspectionType.FR,
                ui_evaluability=UiEvaluability.UI_VERIFIABLE,
                non_evaluable_reason=NonEvaluableReason.NONE,
                visible_subtype=VisibleSubtype.VALIDATION_OR_FEEDBACK,
                task_relevance=TaskRelevance.HIGH,
                review_status=RequirementReviewStatus.CANDIDATE,
            )
        ],
    )

    path = tmp_path / "candidate_requirements.json"
    candidate_file.save(path)
    loaded = CandidateRequirementFile.load(path)

    assert loaded.to_dict() == candidate_file.to_dict()
