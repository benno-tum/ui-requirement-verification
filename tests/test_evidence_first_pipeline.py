from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from pydantic import ValidationError
import pytest

from ui_verifier.verification_pipeline.claim_verification import ClaimVerifier
from ui_verifier.verification_pipeline.evidence_retrieval import (
    EmbeddingEvidenceRetriever,
    LexicalEvidenceRetriever,
)
from ui_verifier.verification_pipeline.label_aggregation import LabelAggregator
from ui_verifier.verification_pipeline.pipeline import EvidenceFirstVerificationPipeline
from ui_verifier.verification_pipeline.requirement_understanding import RequirementUnderstanding
from ui_verifier.verification_pipeline.requirement_understanding import ClaimDecomposer
from ui_verifier.verification_pipeline.schemas import (
    ClaimStatus,
    ClaimVerificationResult,
    EvidenceItem,
    PipelineInput,
    RequirementClaim,
    RequirementInput,
    ScreenRepresentation,
    ScreenshotStep,
    UIEvaluability,
    VerificationLabel,
)
from ui_verifier.verification_pipeline.screen_understanding import ScreenUnderstanding


class FakeClaimDecomposer(ClaimDecomposer):
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def decompose_many(self, requirements: list[RequirementInput], *, max_claims: int) -> dict[str, list[str]]:
        self.calls.append([requirement.requirement_id for requirement in requirements])
        return {
            requirement.requirement_id: [
                "The page shows booking controls.",
                "The page shows payment controls.",
            ][:max_claims]
            for requirement in requirements
        }


def _requirement() -> RequirementInput:
    return RequirementInput(requirement_id="REQ-1", text="The page shows a confirmation banner.")


def _claim(
    *,
    claim_id: str = "REQ-1-C1",
    text: str = "The page shows a confirmation banner.",
    observable: bool = True,
) -> RequirementClaim:
    return RequirementClaim(
        claim_id=claim_id,
        requirement_id="REQ-1",
        claim_text=text,
        source_requirement_text=_requirement().text,
        claim_index=1,
        is_observable=observable,
    )


def _evidence(step_index: int = 1, confidence: float = 0.9) -> EvidenceItem:
    return EvidenceItem(
        step_index=step_index,
        screenshot_path=f"step_{step_index:02d}.png",
        visible_observation="Visible confirmation banner.",
        confidence=confidence,
        source="test",
    )


def _claim_result(
    status: ClaimStatus,
    *,
    claim_id: str = "REQ-1-C1",
    evidence: list[EvidenceItem] | None = None,
    observable: bool = True,
) -> ClaimVerificationResult:
    return ClaimVerificationResult(
        claim_id=claim_id,
        requirement_id="REQ-1",
        claim_text="The page shows a confirmation banner.",
        status=status,
        is_core=True,
        is_observable=observable,
        evidence=evidence or [],
        rationale="test rationale",
    )


def test_schema_validation_rejects_invalid_bbox() -> None:
    with pytest.raises(ValidationError):
        EvidenceItem(
            step_index=1,
            screenshot_path="step_01.png",
            visible_observation="Visible thing.",
            bbox=[0, 0, 10],
        )


def test_screen_understanding_preserves_step_index(tmp_path: Path) -> None:
    image_path = tmp_path / "step_07.png"
    Image.new("RGB", (12, 8), color="white").save(image_path)

    representation = ScreenUnderstanding().understand_step(
        ScreenshotStep(step_index=7, screenshot_path=str(image_path), metadata={"visible_text": "Checkout"})
    )

    assert representation.step_index == 7
    assert representation.image_width == 12
    assert representation.image_height == 8


def test_requirement_decomposition_creates_two_to_four_claims() -> None:
    requirement = RequirementInput(
        requirement_id="REQ-1",
        text="The system shall present an order summary including subtotal, fees, tax, and total.",
    )

    result = RequirementUnderstanding(max_claims=4).understand(requirement)

    assert 2 <= len(result.claims) <= 4
    assert all(claim.source_requirement_text == requirement.text for claim in result.claims)


def test_requirement_understanding_uses_batch_llm_fallback_for_failed_decomposition() -> None:
    fallback = FakeClaimDecomposer()
    requirements = [
        RequirementInput(requirement_id="REQ-1", text="The page supports booking and payment."),
        RequirementInput(requirement_id="REQ-2", text="The system shall present an order summary including subtotal, fees, tax, and total."),
    ]

    results = RequirementUnderstanding(fallback_decomposer=fallback).understand_many(requirements)

    assert fallback.calls == [["REQ-1"]]
    assert results[0].decomposition_source == "FakeClaimDecomposer"
    assert [claim.claim_text for claim in results[0].claims] == [
        "The page shows booking controls.",
        "The page shows payment controls.",
    ]
    assert results[1].decomposition_source == "heuristic"


def test_lexical_evidence_retrieval_returns_top_k_steps() -> None:
    screens = [
        ScreenRepresentation(
            step_index=1,
            screenshot_path="step_01.png",
            visible_text="A confirmation banner is visible.",
            screen_summary="A confirmation banner is visible.",
        ),
        ScreenRepresentation(
            step_index=2,
            screenshot_path="step_02.png",
            visible_text="Confirmation details are shown.",
            screen_summary="Confirmation details are shown.",
        ),
        ScreenRepresentation(
            step_index=3,
            screenshot_path="step_03.png",
            visible_text="The homepage menu is visible.",
            screen_summary="The homepage menu is visible.",
        ),
    ]

    result = LexicalEvidenceRetriever(top_k=2).retrieve([_claim(text="Confirmation banner details are shown.")], screens)

    evidence = result["REQ-1-C1"]
    assert len(evidence) == 2
    assert {item.step_index for item in evidence} == {1, 2}


def test_embedding_retriever_falls_back_gracefully_without_local_model() -> None:
    screens = [
        ScreenRepresentation(
            step_index=1,
            screenshot_path="step_01.png",
            visible_text="A confirmation banner is visible.",
            screen_summary="A confirmation banner is visible.",
        )
    ]

    result = EmbeddingEvidenceRetriever(top_k=1).retrieve([_claim()], screens)

    assert result["REQ-1-C1"]
    assert result["REQ-1-C1"][0].source == "lexical"


def test_claim_verifier_marks_hidden_claims_as_hidden() -> None:
    claim = _claim(text="The backend securely stores the payment transaction.", observable=False)

    result = ClaimVerifier().verify(
        claim,
        [_evidence()],
        ui_evaluability=UIEvaluability.PARTIALLY_UI_VERIFIABLE,
    )

    assert result.status == ClaimStatus.HIDDEN
    assert result.evidence == []


def test_no_fulfilled_without_evidence() -> None:
    result = LabelAggregator().aggregate(
        requirement=_requirement(),
        ui_evaluability=UIEvaluability.UI_VERIFIABLE,
        claim_results=[_claim_result(ClaimStatus.SUPPORTED)],
    )

    assert result.final_label == VerificationLabel.ABSTAIN


def test_not_fulfilled_only_with_contradicted_claim() -> None:
    missing = LabelAggregator().aggregate(
        requirement=_requirement(),
        ui_evaluability=UIEvaluability.UI_VERIFIABLE,
        claim_results=[_claim_result(ClaimStatus.MISSING)],
    )
    contradicted = LabelAggregator().aggregate(
        requirement=_requirement(),
        ui_evaluability=UIEvaluability.UI_VERIFIABLE,
        claim_results=[_claim_result(ClaimStatus.CONTRADICTED, evidence=[_evidence()])],
    )

    assert missing.final_label != VerificationLabel.NOT_FULFILLED
    assert contradicted.final_label == VerificationLabel.NOT_FULFILLED


def test_not_ui_verifiable_leads_to_abstain() -> None:
    result = LabelAggregator().aggregate(
        requirement=_requirement(),
        ui_evaluability=UIEvaluability.NOT_UI_VERIFIABLE,
        claim_results=[_claim_result(ClaimStatus.SUPPORTED, evidence=[_evidence()])],
    )

    assert result.final_label == VerificationLabel.ABSTAIN


def test_missing_evidence_leads_to_abstain_or_partial_not_not_fulfilled() -> None:
    no_evidence = LabelAggregator().aggregate(
        requirement=_requirement(),
        ui_evaluability=UIEvaluability.UI_VERIFIABLE,
        claim_results=[_claim_result(ClaimStatus.MISSING)],
    )
    partial = LabelAggregator().aggregate(
        requirement=_requirement(),
        ui_evaluability=UIEvaluability.UI_VERIFIABLE,
        claim_results=[
            _claim_result(ClaimStatus.SUPPORTED, claim_id="REQ-1-C1", evidence=[_evidence()]),
            _claim_result(ClaimStatus.MISSING, claim_id="REQ-1-C2"),
        ],
    )

    assert no_evidence.final_label == VerificationLabel.ABSTAIN
    assert partial.final_label == VerificationLabel.PARTIALLY_FULFILLED


def test_pipeline_produces_valid_json_output(tmp_path: Path) -> None:
    image_path = tmp_path / "step_01.png"
    Image.new("RGB", (16, 16), color="white").save(image_path)
    pipeline = EvidenceFirstVerificationPipeline(evidence_retriever=LexicalEvidenceRetriever(top_k=1))

    output = pipeline.run(
        PipelineInput(
            flow_id="flow-1",
            screenshots=[
                ScreenshotStep(
                    step_index=1,
                    screenshot_path=str(image_path),
                    metadata={"visible_text": "Checkout summary with total is visible."},
                )
            ],
            requirements=[
                RequirementInput(
                    requirement_id="REQ-1",
                    text="The page displays a checkout summary.",
                    flow_id="flow-1",
                )
            ],
        )
    )

    data = json.loads(output.model_dump_json())
    result = data["results"][0]
    assert result["requirement_id"] == "REQ-1"
    assert result["final_label"] in {label.value for label in VerificationLabel}
    assert result["claims"][0]["status"] in {status.value for status in ClaimStatus}
    assert "uncertainty_reasons" in result
    assert "rationale" in result
