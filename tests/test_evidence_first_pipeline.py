from __future__ import annotations

import json
from pathlib import Path
import threading
import time

from PIL import Image
from pydantic import ValidationError
import pytest

from ui_verifier.verification_pipeline.claim_verification import ClaimVerifier
from ui_verifier.verification_pipeline.evidence_retrieval import (
    EmbeddingEvidenceRetriever,
    EvidenceRetriever,
    LexicalEvidenceRetriever,
)
from ui_verifier.verification_pipeline.label_aggregation import LabelAggregator
from ui_verifier.verification_pipeline.pipeline import EvidenceFirstVerificationPipeline
from ui_verifier.verification_pipeline.requirement_understanding import RequirementUnderstanding
from ui_verifier.verification_pipeline.requirement_understanding import ClaimDecomposer
from ui_verifier.verification_pipeline.requirement_understanding import find_hidden_indicators
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
    UncertaintyReason,
    VerificationLabel,
)
from ui_verifier.verification_pipeline.screen_understanding import ScreenUnderstanding
from scripts.run_verification_pipeline import load_requirements


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
    uncertainty_reasons: list[UncertaintyReason] | None = None,
) -> ClaimVerificationResult:
    return ClaimVerificationResult(
        claim_id=claim_id,
        requirement_id="REQ-1",
        claim_text="The page shows a confirmation banner.",
        status=status,
        is_core=True,
        is_observable=observable,
        evidence=evidence or [],
        uncertainty_reasons=uncertainty_reasons or [],
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


def test_requirement_understanding_can_disable_claim_decomposition() -> None:
    requirement = RequirementInput(
        requirement_id="REQ-1",
        text="The page shows a product title and lets users choose a size.",
        flow_id="flow-1",
    )

    result = RequirementUnderstanding(decompose_claims=False).understand(requirement)

    assert [claim.claim_text for claim in result.claims] == [requirement.text]
    assert result.decomposition_source == "disabled"


def test_benchmark_input_loader_includes_contrastive_requirements(tmp_path: Path) -> None:
    requirements_path = tmp_path / "verification_gold.json"
    requirements_path.write_text(
        json.dumps(
            {
                "flow_id": "flow-1",
                "items": [
                    {"requirement_id": "REQ-01", "text": "The page shows search."},
                    {"requirement_id": "CONTR-01", "text": "The page preserves search state."},
                ],
            }
        ),
        encoding="utf-8",
    )

    requirements = load_requirements(requirements_path, default_flow_id="flow-1")

    assert [requirement.requirement_id for requirement in requirements] == ["REQ-01", "CONTR-01"]


def test_llm_decomposition_prompt_preserves_or_alternatives() -> None:
    from ui_verifier.verification_pipeline.requirement_understanding import _build_llm_decomposition_prompt

    prompt = _build_llm_decomposition_prompt(
        [
            RequirementInput(
                requirement_id="REQ-1",
                text=(
                    "The system shall provide visible confirmation that a selected job posting has been handed off "
                    "to the chosen external sharing channel or compose surface."
                ),
            )
        ],
        max_claims=4,
    )

    assert "Separate claims are interpreted conjunctively" in prompt
    assert 'Preserve "or" wording inside one claim' in prompt


def test_store_locator_text_is_not_marked_as_database_hidden() -> None:
    assert find_hidden_indicators("The system shall provide store locator functionality.") == []
    assert find_hidden_indicators("The system shall display operating hours for each listed store.") == []
    assert find_hidden_indicators("The system shall keep stored preferences for later visits.") == ["database"]


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


def test_aggregator_fulfilled_requires_all_core_claims_supported() -> None:
    result = LabelAggregator().aggregate(
        requirement=_requirement(),
        ui_evaluability=UIEvaluability.UI_VERIFIABLE,
        claim_results=[
            _claim_result(ClaimStatus.SUPPORTED, claim_id="REQ-1-C1", evidence=[_evidence(1)]),
            _claim_result(ClaimStatus.SUPPORTED, claim_id="REQ-1-C2", evidence=[_evidence(2)]),
        ],
    )

    assert result.final_label == VerificationLabel.FULFILLED


def test_aggregator_fulfilled_allows_supported_with_caveat() -> None:
    result = LabelAggregator().aggregate(
        requirement=_requirement(),
        ui_evaluability=UIEvaluability.UI_VERIFIABLE,
        claim_results=[
            _claim_result(ClaimStatus.SUPPORTED, claim_id="REQ-1-C1", evidence=[_evidence(1)]),
            _claim_result(ClaimStatus.SUPPORTED_WITH_CAVEAT, claim_id="REQ-1-C2", evidence=[_evidence(2)]),
        ],
    )

    assert result.final_label == VerificationLabel.FULFILLED
    assert "caveat" in result.rationale.lower()


@pytest.mark.parametrize(
    "problem_status",
    [
        ClaimStatus.PARTIALLY_SUPPORTED,
        ClaimStatus.MISSING,
        ClaimStatus.HIDDEN,
        ClaimStatus.AMBIGUOUS,
        ClaimStatus.OUT_OF_SCOPE,
    ],
)
def test_aggregator_partial_when_supported_claim_has_problem_core_claim(problem_status: ClaimStatus) -> None:
    result = LabelAggregator().aggregate(
        requirement=_requirement(),
        ui_evaluability=UIEvaluability.UI_VERIFIABLE,
        claim_results=[
            _claim_result(ClaimStatus.SUPPORTED, claim_id="REQ-1-C1", evidence=[_evidence(1)]),
            _claim_result(problem_status, claim_id="REQ-1-C2", evidence=[_evidence(2)]),
        ],
    )

    assert result.final_label == VerificationLabel.PARTIALLY_FULFILLED


def test_aggregator_partially_supported_with_evidence_is_partially_fulfilled() -> None:
    result = LabelAggregator().aggregate(
        requirement=_requirement(),
        ui_evaluability=UIEvaluability.UI_VERIFIABLE,
        claim_results=[
            _claim_result(ClaimStatus.PARTIALLY_SUPPORTED, evidence=[_evidence()]),
        ],
    )

    assert result.final_label == VerificationLabel.PARTIALLY_FULFILLED


@pytest.mark.parametrize(
    "unsupported_status",
    [
        ClaimStatus.MISSING,
        ClaimStatus.HIDDEN,
        ClaimStatus.AMBIGUOUS,
        ClaimStatus.OUT_OF_SCOPE,
    ],
)
def test_aggregator_abstains_when_no_core_claim_is_supported(unsupported_status: ClaimStatus) -> None:
    result = LabelAggregator().aggregate(
        requirement=_requirement(),
        ui_evaluability=UIEvaluability.UI_VERIFIABLE,
        claim_results=[
            _claim_result(unsupported_status, claim_id="REQ-1-C1", evidence=[_evidence()]),
        ],
    )

    assert result.final_label == VerificationLabel.ABSTAIN


@pytest.mark.parametrize(
    "reason",
    [
        UncertaintyReason.FLOW_COVERAGE_GAP,
        UncertaintyReason.UNVERIFIED_SYSTEM_OUTCOME,
        UncertaintyReason.NONTRIVIAL_HIDDEN_PROPERTY,
        UncertaintyReason.EVIDENCE_INTERPRETATION_AMBIGUITY,
    ],
)
def test_aggregator_material_uncertainty_blocks_fulfilled(reason: UncertaintyReason) -> None:
    result = LabelAggregator().aggregate(
        requirement=_requirement(),
        ui_evaluability=UIEvaluability.UI_VERIFIABLE,
        claim_results=[
            _claim_result(
                ClaimStatus.SUPPORTED,
                evidence=[_evidence()],
                uncertainty_reasons=[reason],
            )
        ],
    )

    assert result.final_label == VerificationLabel.PARTIALLY_FULFILLED


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


def test_pipeline_retrieves_evidence_for_all_claims_in_one_batch(tmp_path: Path) -> None:
    class TrackingRetriever(EvidenceRetriever):
        def __init__(self) -> None:
            super().__init__(top_k=1)
            self.calls: list[list[str]] = []
            self.fallback = LexicalEvidenceRetriever(top_k=1)

        def retrieve(self, claims, screens):
            self.calls.append([claim.claim_id for claim in claims])
            return self.fallback.retrieve(claims, screens)

    image_path = tmp_path / "step_01.png"
    Image.new("RGB", (16, 16), color="white").save(image_path)
    retriever = TrackingRetriever()
    pipeline = EvidenceFirstVerificationPipeline(evidence_retriever=retriever)

    output = pipeline.run(
        PipelineInput(
            flow_id="flow-1",
            screenshots=[
                ScreenshotStep(
                    step_index=1,
                    screenshot_path=str(image_path),
                    metadata={"visible_text": "A confirmation banner is visible."},
                )
            ],
            requirements=[
                RequirementInput(
                    requirement_id=requirement_id,
                    text="The page shows a confirmation banner.",
                    flow_id="flow-1",
                )
                for requirement_id in ("REQ-1", "REQ-2", "REQ-3")
            ],
        )
    )

    assert len(retriever.calls) == 1
    assert retriever.calls[0] == ["REQ-1-C1", "REQ-2-C1", "REQ-3-C1"]
    assert output.metadata["retrieval_batch_claims"] == 3


def test_pipeline_verifies_independent_claims_concurrently_and_preserves_order(tmp_path: Path) -> None:
    class TrackingVerifier(ClaimVerifier):
        def __init__(self) -> None:
            super().__init__()
            self.active = 0
            self.max_active = 0
            self.lock = threading.Lock()

        def verify(self, claim, evidence, *, ui_evaluability):
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            try:
                time.sleep(0.03)
                return super().verify(claim, evidence, ui_evaluability=ui_evaluability)
            finally:
                with self.lock:
                    self.active -= 1

    image_path = tmp_path / "step_01.png"
    Image.new("RGB", (16, 16), color="white").save(image_path)
    verifier = TrackingVerifier()
    pipeline = EvidenceFirstVerificationPipeline(
        evidence_retriever=LexicalEvidenceRetriever(top_k=1),
        claim_verifier=verifier,
        max_claim_workers=3,
    )
    requirement_ids = ["REQ-1", "REQ-2", "REQ-3"]

    output = pipeline.run(
        PipelineInput(
            flow_id="flow-1",
            screenshots=[
                ScreenshotStep(
                    step_index=1,
                    screenshot_path=str(image_path),
                    metadata={"visible_text": "A confirmation banner is visible."},
                )
            ],
            requirements=[
                RequirementInput(
                    requirement_id=requirement_id,
                    text="The page shows a confirmation banner.",
                    flow_id="flow-1",
                )
                for requirement_id in requirement_ids
            ],
        )
    )

    assert verifier.max_active > 1
    assert [result.requirement_id for result in output.results] == requirement_ids
    assert output.metadata["max_claim_workers"] == 3
