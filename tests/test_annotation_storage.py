from pathlib import Path

from ui_verifier.annotation.storage import AnnotationStorage
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
    RequirementReviewStatus,
    RequirementScope,
    TaskRelevance,
)


def _candidate_file(flow_id: str, text: str) -> CandidateRequirementFile:
    return CandidateRequirementFile(
        dataset="mind2web",
        flow_id=flow_id,
        requirements=[
            CandidateRequirement(
                requirement_id="REQ-01",
                flow_id=flow_id,
                text=text,
                scope=RequirementScope.SINGLE_SCREEN,
                step_indices=[1],
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


def test_load_candidate_file_prefers_versioned_snapshot(tmp_path: Path) -> None:
    storage = AnnotationStorage(
        candidate_root=tmp_path / "generated" / "candidate_requirements",
        versioned_candidate_root=tmp_path / "annotations" / "requirements_candidate",
        gold_root=tmp_path / "annotations" / "requirements_gold",
    )
    flow_id = "flow-1"

    generated = _candidate_file(flow_id, "generated candidate")
    versioned = _candidate_file(flow_id, "versioned candidate")
    generated.save(storage.generated_candidate_dir(flow_id) / "candidate_requirements.json")
    versioned.save(storage.versioned_candidate_dir(flow_id) / "candidate_requirements.json")

    loaded = storage.load_candidate_file(flow_id)

    assert loaded.requirements[0].text == "versioned candidate"


def test_save_candidate_file_writes_versioned_snapshot(tmp_path: Path) -> None:
    storage = AnnotationStorage(
        candidate_root=tmp_path / "generated" / "candidate_requirements",
        versioned_candidate_root=tmp_path / "annotations" / "requirements_candidate",
        gold_root=tmp_path / "annotations" / "requirements_gold",
    )
    flow_id = "flow-1"
    candidate_file = _candidate_file(flow_id, "saved candidate")

    saved_path = storage.save_candidate_file(candidate_file)

    assert saved_path == storage.versioned_candidate_dir(flow_id) / "candidate_requirements.json"
    assert saved_path.exists()
    assert not (storage.generated_candidate_dir(flow_id) / "candidate_requirements.json").exists()
