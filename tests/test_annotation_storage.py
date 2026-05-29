from pathlib import Path

from ui_verifier.annotation.service import AnnotationService
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
    GoldRequirement,
    GoldRequirementFile,
    RequirementReviewStatus,
    RequirementScope,
    TaskRelevance,
)
from ui_verifier.verification.schemas import VerificationGoldFile, VerificationGoldItem, VerificationLabel
from scripts.backfill_verification_claim_suggestions import backfill_verification_claim_suggestions


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


def test_save_and_load_verification_gold_file(tmp_path: Path) -> None:
    storage = AnnotationStorage(
        candidate_root=tmp_path / "generated" / "candidate_requirements",
        versioned_candidate_root=tmp_path / "annotations" / "requirements_candidate",
        gold_root=tmp_path / "annotations" / "requirements_gold",
        verification_gold_root=tmp_path / "annotations" / "verification_gold",
    )
    verification_gold_file = VerificationGoldFile(
        dataset="mind2web",
        flow_id="flow-1",
        items=[
            VerificationGoldItem(
                requirement_id="REQ-01",
                flow_id="flow-1",
                text="The system shall show a confirmation banner.",
                step_indices=[1],
                verification_label="FULFILLED",
                ui_evaluability="UI_VERIFIABLE",
                evidence_steps=[1],
                claims=[
                    {
                        "claim": "A confirmation banner is visible.",
                        "status": "SUPPORTED",
                        "evidence_steps": [1],
                    }
                ],
            )
        ],
    )

    saved_path = storage.save_verification_gold_file(verification_gold_file)
    loaded = storage.load_verification_gold_file("flow-1")

    assert saved_path == storage.verification_gold_dir("flow-1") / "verification_gold.json"
    assert loaded is not None
    assert loaded.to_dict() == verification_gold_file.to_dict()


def test_backfill_verification_claim_suggestions_materializes_gold_claims(tmp_path: Path) -> None:
    storage = AnnotationStorage(
        candidate_root=tmp_path / "generated" / "candidate_requirements",
        versioned_candidate_root=tmp_path / "annotations" / "requirements_candidate",
        gold_root=tmp_path / "annotations" / "requirements_gold",
        verification_gold_root=tmp_path / "annotations" / "verification_gold",
    )
    flow_id = "flow-1"
    gold_file = GoldRequirementFile(
        dataset="mind2web",
        flow_id=flow_id,
        requirements=[
            GoldRequirement(
                requirement_id="REQ-01",
                flow_id=flow_id,
                text="The system shall allow shoppers to filter products by size and color.",
                scope=RequirementScope.SINGLE_SCREEN,
                step_indices=[1],
                manual_verification_label="fulfilled",
            )
        ],
    )
    storage.save_gold_file(gold_file)
    service = AnnotationService(storage=storage)

    summary = backfill_verification_claim_suggestions(service, flow_id, include_candidates=False)
    loaded = storage.load_verification_gold_file(flow_id)

    assert summary.items_updated == 1
    assert summary.claims_written == 1
    assert loaded is not None
    assert loaded.items[0].claims[0].claim == "The system allows shoppers to filter products by size and color."
    assert loaded.items[0].claims[0].status.value == "MISSING"
    assert loaded.items[0].review_status == "needs_review"


def test_backfill_verification_claim_suggestions_keeps_existing_claims(tmp_path: Path) -> None:
    storage = AnnotationStorage(
        candidate_root=tmp_path / "generated" / "candidate_requirements",
        versioned_candidate_root=tmp_path / "annotations" / "requirements_candidate",
        gold_root=tmp_path / "annotations" / "requirements_gold",
        verification_gold_root=tmp_path / "annotations" / "verification_gold",
    )
    flow_id = "flow-1"
    gold_file = GoldRequirementFile(
        dataset="mind2web",
        flow_id=flow_id,
        requirements=[
            GoldRequirement(
                requirement_id="REQ-01",
                flow_id=flow_id,
                text="The system shall show a confirmation banner.",
                scope=RequirementScope.SINGLE_SCREEN,
                step_indices=[1],
                manual_verification_label="fulfilled",
            )
        ],
    )
    existing = VerificationGoldFile(
        dataset="mind2web",
        flow_id=flow_id,
        items=[
            VerificationGoldItem(
                requirement_id="REQ-01",
                flow_id=flow_id,
                text="The system shall show a confirmation banner.",
                step_indices=[1],
                verification_label="FULFILLED",
                ui_evaluability="UI_VERIFIABLE",
                evidence_steps=[1],
                claims=[
                    {
                        "claim": "A reviewed confirmation banner claim.",
                        "status": "SUPPORTED",
                        "evidence_steps": [1],
                    }
                ],
            )
        ],
    )
    storage.save_gold_file(gold_file)
    storage.save_verification_gold_file(existing)
    service = AnnotationService(storage=storage)

    summary = backfill_verification_claim_suggestions(service, flow_id, include_candidates=False)
    loaded = storage.load_verification_gold_file(flow_id)

    assert summary.items_updated == 0
    assert summary.claims_written == 0
    assert loaded is not None
    assert loaded.items[0].claims[0].claim == "A reviewed confirmation banner claim."


def test_backfill_verification_claim_suggestions_replaces_trivial_copied_claim(tmp_path: Path) -> None:
    storage = AnnotationStorage(
        candidate_root=tmp_path / "generated" / "candidate_requirements",
        versioned_candidate_root=tmp_path / "annotations" / "requirements_candidate",
        gold_root=tmp_path / "annotations" / "requirements_gold",
        verification_gold_root=tmp_path / "annotations" / "verification_gold",
    )
    flow_id = "flow-1"
    requirement_text = (
        "The system shall retain the selected park context in later purchase and checkout screens "
        "so users can verify that they are still completing a pass purchase for the intended park."
    )
    gold_file = GoldRequirementFile(
        dataset="mind2web",
        flow_id=flow_id,
        requirements=[
            GoldRequirement(
                requirement_id="CONTR-01",
                flow_id=flow_id,
                text=requirement_text,
                scope=RequirementScope.MULTI_SCREEN,
                step_indices=[1, 2],
                manual_verification_label="partially_fulfilled",
            )
        ],
    )
    existing = VerificationGoldFile(
        dataset="mind2web",
        flow_id=flow_id,
        items=[
            VerificationGoldItem(
                requirement_id="CONTR-01",
                flow_id=flow_id,
                text=requirement_text,
                step_indices=[1, 2],
                verification_label="PARTIALLY_FULFILLED",
                ui_evaluability="UI_VERIFIABLE",
                evidence_steps=[1, 2],
                claims=[
                    {
                        "claim": requirement_text,
                        "status": "MISSING",
                    }
                ],
            )
        ],
    )
    storage.save_gold_file(gold_file)
    storage.save_verification_gold_file(existing)
    service = AnnotationService(storage=storage)

    summary = backfill_verification_claim_suggestions(
        service,
        flow_id,
        include_candidates=False,
        replace_trivial_copied=True,
    )
    loaded = storage.load_verification_gold_file(flow_id)

    assert summary.items_updated == 1
    assert summary.claims_written == 3
    assert loaded is not None
    assert [claim.claim for claim in loaded.items[0].claims] == [
        "The system retains the selected park context in later purchase screens.",
        "The system retains the selected park context in checkout screens.",
        "Users can verify that they are still completing a pass purchase for the intended park.",
    ]


def test_delete_materialized_candidate_verification_item_rejects_candidate(tmp_path: Path) -> None:
    storage = AnnotationStorage(
        candidate_root=tmp_path / "generated" / "candidate_requirements",
        versioned_candidate_root=tmp_path / "annotations" / "requirements_candidate",
        gold_root=tmp_path / "annotations" / "requirements_gold",
        verification_gold_root=tmp_path / "annotations" / "verification_gold",
    )
    flow_id = "flow-1"
    candidate_file = _candidate_file(flow_id, "The system shall show a candidate-only benchmark item.")
    candidate_file.requirements[0].requirement_id = "CONTR-01"
    storage.save_candidate_file(candidate_file)
    service = AnnotationService(storage=storage)

    listed = service.list_verification_gold(flow_id)
    assert [item.requirement_id for item in listed] == ["CONTR-01"]

    deleted_item, deleted_gold = service.delete_verification_gold_item(flow_id, "CONTR-01")

    assert deleted_item.requirement_id == "CONTR-01"
    assert deleted_gold is False
    assert service.list_verification_gold(flow_id) == []
    saved_candidate = storage.load_candidate_file(flow_id).requirements[0]
    assert saved_candidate.review_status == RequirementReviewStatus.REJECTED


def test_deleted_gold_requirement_does_not_reappear_from_accepted_candidate(tmp_path: Path) -> None:
    storage = AnnotationStorage(
        candidate_root=tmp_path / "generated" / "candidate_requirements",
        versioned_candidate_root=tmp_path / "annotations" / "requirements_candidate",
        gold_root=tmp_path / "annotations" / "requirements_gold",
        verification_gold_root=tmp_path / "annotations" / "verification_gold",
    )
    flow_id = "flow-1"
    storage.save_candidate_file(_candidate_file(flow_id, "The system shall show an accepted gold item."))
    service = AnnotationService(storage=storage)

    service.accept_candidate(flow_id, "REQ-01", verification_label=VerificationLabel.FULFILLED)
    assert [item.requirement_id for item in service.list_verification_gold(flow_id)] == ["REQ-01"]

    deleted_item, deleted_gold = service.delete_verification_gold_item(flow_id, "REQ-01")

    assert deleted_item.requirement_id == "REQ-01"
    assert deleted_gold is True
    assert service.list_gold_requirements(flow_id) == []
    assert service.list_verification_gold(flow_id) == []
