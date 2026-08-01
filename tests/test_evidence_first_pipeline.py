from __future__ import annotations

import json
from pathlib import Path
import threading
import time

from PIL import Image
from pydantic import ValidationError
import pytest

from ui_verifier.verification_pipeline.claim_verification import ClaimVerifier
from ui_verifier.verification_pipeline.batched_gemini_image_claim_verifier import BatchedGeminiImageClaimVerifier
from ui_verifier.verification_pipeline.evidence_retrieval import (
    EmbeddingEvidenceRetriever,
    EvidenceRetriever,
    LexicalEvidenceRetriever,
)
from ui_verifier.verification_pipeline.gemini_image_claim_verifier import GeminiImageClaimVerifier
from ui_verifier.verification_pipeline.label_aggregation import LabelAggregator
from ui_verifier.verification_pipeline.pipeline import EvidenceFirstVerificationPipeline
from ui_verifier.verification_pipeline import requirement_understanding as requirement_understanding_module
from ui_verifier.verification_pipeline.requirement_understanding import GeminiClaimDecomposer, RequirementUnderstanding
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


def test_localizer_uses_visible_observation_only_when_claim_text_has_no_match() -> None:
    class RecordingLocalizer:
        def __init__(self) -> None:
            self.queries: list[str] = []

        def suggest(self, query: str, image_path: Path, *, max_candidates: int) -> list[dict]:
            self.queries.append(query)
            if query == "Visible confirmation banner.":
                return [
                    {
                        "bbox": {"x1": 1, "y1": 2, "x2": 10, "y2": 12},
                        "source": "tesseract",
                        "level": "line",
                        "score": 0.8,
                        "matched_text": "Confirmation",
                        "image_path": str(image_path),
                        "image_width": 20,
                        "image_height": 20,
                        "coordinate_space": "image_pixels",
                    }
                ]
            return []

    localizer = RecordingLocalizer()
    pipeline = EvidenceFirstVerificationPipeline(evidence_localizer=localizer)
    localized = pipeline._localize_evidence_item("A differently worded requirement.", _evidence())

    assert localizer.queries == ["A differently worded requirement.", "Visible confirmation banner."]
    assert localized.bbox == [1.0, 2.0, 10.0, 12.0]
    assert localized.bbox_metadata["query_source"] == "visible_observation"


def test_provided_claim_decomposition_uses_only_frozen_claim_texts(tmp_path: Path) -> None:
    requirements_path = tmp_path / "requirements.json"
    requirements_path.write_text(
        json.dumps(
            {
                "requirements": [
                    {
                        "requirement_id": "REQ-1",
                        "text": "The system supports splitting and merging.",
                        "verification_label": "FULFILLED",
                        "claims": [
                            {"claim": "The system supports splitting.", "status": "SUPPORTED"},
                            {"claim_text": "The system supports merging.", "evidence_steps": [9]},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    requirement = load_requirements(requirements_path, default_flow_id="flow-1")[0]
    assert requirement.metadata["provided_claim_texts"] == [
        "The system supports splitting.",
        "The system supports merging.",
    ]
    assert "verification_label" not in requirement.metadata
    assert "claims" not in requirement.metadata

    result = RequirementUnderstanding(
        decomposition_policy="provided",
        max_claims=4,
    ).understand(requirement)
    assert [claim.claim_text for claim in result.claims] == requirement.metadata["provided_claim_texts"]
    assert result.decomposition_source == "provided_claims"


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

    result = RequirementUnderstanding(max_claims=4, decomposition_policy="always").understand(requirement)

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


def test_campaign_performance_graph_is_not_misclassified_as_hidden_performance_target() -> None:
    visible = RequirementInput(
        requirement_id="REQ-VISIBLE",
        text="The Dashboard shall display campaign performance graphs.",
    )
    hidden = RequirementInput(
        requirement_id="REQ-HIDDEN",
        text="The application has a response time below 200 ms.",
    )

    understanding = RequirementUnderstanding(decompose_claims=False)

    assert understanding.understand(visible).ui_evaluability == UIEvaluability.UI_VERIFIABLE
    assert understanding.understand(hidden).ui_evaluability == UIEvaluability.NOT_UI_VERIFIABLE


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
    assert "Do not improve, generalize, strengthen, or reinterpret" in prompt
    assert "authenticated users can" in prompt


def test_store_locator_text_is_not_marked_as_database_hidden() -> None:
    assert find_hidden_indicators("The system shall provide store locator functionality.") == []
    assert find_hidden_indicators("The system shall display operating hours for each listed store.") == []
    assert find_hidden_indicators("The page displays the role title and role responsibilities.") == []
    assert find_hidden_indicators("The café page explains service availability.") == []
    assert find_hidden_indicators("Only administrators with the correct user role may access the page.") == ["security"]
    assert find_hidden_indicators("The service must meet a high availability target.") == ["uptime"]
    assert find_hidden_indicators("The system shall keep stored preferences for later visits.") == ["database"]


def test_requirement_understanding_uses_batch_llm_fallback_for_failed_decomposition() -> None:
    fallback = FakeClaimDecomposer()
    requirements = [
        RequirementInput(requirement_id="REQ-1", text="The page supports booking and payment."),
        RequirementInput(requirement_id="REQ-2", text="The system shall present an order summary including subtotal, fees, tax, and total."),
    ]

    results = RequirementUnderstanding(
        fallback_decomposer=fallback,
        decomposition_policy="always",
    ).understand_many(requirements)

    assert fallback.calls == [["REQ-1"]]
    assert results[0].decomposition_source == "FakeClaimDecomposer"
    assert [claim.claim_text for claim in results[0].claims] == [
        "The page shows booking controls.",
        "The page shows payment controls.",
    ]
    assert results[1].decomposition_source == "heuristic"


def test_gated_decomposition_keeps_atomic_requirement_as_single_claim() -> None:
    requirement = RequirementInput(
        requirement_id="REQ-1",
        text="The system shall allow authenticated users to access editable profile settings.",
    )

    result = RequirementUnderstanding(decomposition_policy="gated").understand(requirement)

    assert [claim.claim_text for claim in result.claims] == [requirement.text]
    assert result.decomposition_source == "single_requirement"


def test_semantic_guard_rejects_added_only_term() -> None:
    class ExclusiveFallback(ClaimDecomposer):
        def decompose_many(self, requirements: list[RequirementInput], *, max_claims: int) -> dict[str, list[str]]:
            return {
                requirement.requirement_id: ["Only authenticated users can access editable profile settings."]
                for requirement in requirements
            }

    requirement = RequirementInput(
        requirement_id="REQ-1",
        text="The system shall allow authenticated users to access editable profile settings while editing a profile.",
    )

    result = RequirementUnderstanding(
        fallback_decomposer=ExclusiveFallback(),
        decomposition_policy="always",
    ).understand(requirement)

    assert all("Only authenticated users" not in claim.claim_text for claim in result.claims)


def test_pipeline_llm_fallback_uses_shared_rule_guided_decomposer(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeClaim:
        def __init__(self, claim_text: str) -> None:
            self.claim_text = claim_text

    class FakeResult:
        claims = [
            FakeClaim("The page shows booking controls."),
            FakeClaim("The page shows payment controls."),
        ]

    def fake_decompose_requirement_with_diagnostics(requirement_text: str, **kwargs: object) -> FakeResult:
        calls.append((requirement_text, kwargs))
        return FakeResult()

    monkeypatch.setattr(
        requirement_understanding_module,
        "decompose_requirement_with_diagnostics",
        fake_decompose_requirement_with_diagnostics,
    )

    decomposer = GeminiClaimDecomposer(provider="deepseek", model_name="deepseek-chat")
    result = decomposer.decompose_many(
        [RequirementInput(requirement_id="REQ-1", text="The page supports booking and payment.")],
        max_claims=4,
    )

    assert result == {
        "REQ-1": [
            "The page shows booking controls.",
            "The page shows payment controls.",
        ]
    }
    assert calls == [
        (
            "The page supports booking and payment.",
            {
                "strategy": "rule_guided_llm",
                "provider": "deepseek",
                "model_name": "deepseek-chat",
                "use_cache": True,
                "max_claims": 4,
            },
        )
    ]


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


def test_retriever_includes_late_cart_state_for_cart_claims() -> None:
    screens = [
        ScreenRepresentation(
            step_index=1,
            screenshot_path="step_01.png",
            visible_text="Season add-ons are listed with buy buttons.",
            screen_summary="Season add-ons are listed with buy buttons.",
        ),
        ScreenRepresentation(
            step_index=2,
            screenshot_path="step_02.png",
            visible_text="The Go-Kart Pass configuration shows quantity 2.",
            screen_summary="The Go-Kart Pass configuration shows quantity 2.",
        ),
        ScreenRepresentation(
            step_index=3,
            screenshot_path="step_03.png",
            visible_text="The add-on detail remains open.",
            screen_summary="The add-on detail remains open.",
        ),
        ScreenRepresentation(
            step_index=4,
            screenshot_path="step_04.png",
            visible_text="Shopping Cart contains One-Day Ticket and Go-Kart Pass Qty 2. Subtotal, Tax, Total.",
            screen_summary="Shopping Cart contains One-Day Ticket and Go-Kart Pass Qty 2. Subtotal, Tax, Total.",
        ),
    ]

    result = LexicalEvidenceRetriever(top_k=2).retrieve(
        [_claim(text="The system reflects the selected quantity in cart line items.")],
        screens,
    )

    assert {item.step_index for item in result["REQ-1-C1"]} == {2, 4}


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


def test_aggregator_accepts_interpretation_uncertainty_embodied_by_supported_caveat() -> None:
    result = LabelAggregator().aggregate(
        requirement=_requirement(),
        ui_evaluability=UIEvaluability.UI_VERIFIABLE,
        claim_results=[
            _claim_result(
                ClaimStatus.SUPPORTED_WITH_CAVEAT,
                evidence=[_evidence()],
                uncertainty_reasons=[UncertaintyReason.EVIDENCE_INTERPRETATION_AMBIGUITY],
            ),
        ],
    )

    assert result.final_label == VerificationLabel.FULFILLED


def test_aggregator_does_not_accept_flow_gap_as_supported_caveat() -> None:
    result = LabelAggregator().aggregate(
        requirement=_requirement(),
        ui_evaluability=UIEvaluability.UI_VERIFIABLE,
        claim_results=[
            _claim_result(
                ClaimStatus.SUPPORTED_WITH_CAVEAT,
                evidence=[_evidence()],
                uncertainty_reasons=[UncertaintyReason.FLOW_COVERAGE_GAP],
            ),
        ],
    )

    assert result.final_label == VerificationLabel.PARTIALLY_FULFILLED


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


def test_image_verifier_adds_late_screen_for_sequence_claims(tmp_path: Path) -> None:
    verifier = GeminiImageClaimVerifier(
        flow_id="flow-1",
        screenshot_steps=[
            ScreenshotStep(step_index=index, screenshot_path=f"step_{index:02d}.png")
            for index in range(1, 10)
        ],
        cache_path=tmp_path / "cache.json",
        max_images_per_claim=4,
    )

    selected = verifier._selected_steps(
        _claim(text="The system preserves entered values while the shopper completes later fields."),
        [_evidence(3), _evidence(4)],
    )

    assert selected == [1, 3, 4, 9]


def test_image_verifier_fills_sparse_retrieval_with_flow_coverage(tmp_path: Path) -> None:
    verifier = GeminiImageClaimVerifier(
        flow_id="flow-1",
        screenshot_steps=[
            ScreenshotStep(step_index=index, screenshot_path=f"step_{index:02d}.png")
            for index in range(1, 7)
        ],
        cache_path=tmp_path / "cache.json",
        max_images_per_claim=4,
    )

    selected = verifier._selected_steps(
        _claim(text="The page allows browsing by department."),
        [_evidence(6)],
    )

    assert selected == [1, 3, 6]


def test_image_verifier_adds_final_screen_for_cart_claim(tmp_path: Path) -> None:
    verifier = GeminiImageClaimVerifier(
        flow_id="flow-1",
        screenshot_steps=[
            ScreenshotStep(step_index=index, screenshot_path=f"step_{index:02d}.png")
            for index in range(1, 11)
        ],
        cache_path=tmp_path / "cache.json",
        max_images_per_claim=6,
    )

    selected = verifier._selected_steps(
        _claim(text="The cart shows an itemized pre-checkout order summary."),
        [_evidence(index) for index in range(1, 7)],
    )

    assert selected[-1] == 10
    assert len(selected) == 6


def test_image_verifier_prompt_distinguishes_forms_from_summaries(tmp_path: Path) -> None:
    verifier = GeminiImageClaimVerifier(
        flow_id="flow-1",
        screenshot_steps=[ScreenshotStep(step_index=1, screenshot_path="step_01.png")],
        cache_path=tmp_path / "cache.json",
    )
    payload = verifier._request_payload(
        _claim(text="The page displays a synchronized purchase summary."),
        [1],
        ui_evaluability=UIEvaluability.UI_VERIFIABLE,
    )

    prompt = verifier._prompt(payload)

    assert "Do not treat editable input fields as a separate review state" in prompt
    assert "Mere absence of a required feature is MISSING" in prompt
    assert "do not infer a downstream result" in prompt
    assert "do not prove preservation of a digital ticket fulfillment choice" in prompt
    assert "Generic ticket/cart/checkout evidence is not enough" in prompt
    assert "every material clause as conjunctive" in prompt
    assert "Strong frontend text, controls, selected states, summaries, or helper copy" in prompt
    assert "a bounded or closed UI set can support the quantifier" in prompt
    assert "Result, confirmation, or lookup-complete claims require a distinct post-action state" in prompt
    assert "Direct transition or direct return claims require a visible affordance" in prompt
    assert "smallest semantically sufficient visible region" in prompt
    assert '"evidence_regions"' in prompt


def test_image_verifier_converts_grounded_regions_to_original_image_pixels(tmp_path: Path) -> None:
    image_path = tmp_path / "step_01.png"
    Image.new("RGB", (1000, 500), color="white").save(image_path)
    verifier = GeminiImageClaimVerifier(
        flow_id="flow-1",
        screenshot_steps=[ScreenshotStep(step_index=1, screenshot_path=str(image_path))],
        cache_path=tmp_path / "cache.json",
    )

    result = verifier._result_from_gemini(
        _claim(),
        {
            "claim_status": "SUPPORTED",
            "evidence_step_indices": [1],
            "visible_observations": ["The displayed range supports the claim."],
            "uncertainty_reasons": [],
            "evidence_regions": [
                {
                    "step_index": 1,
                    "box_2d": [100, 200, 300, 600],
                    "description": "Displayed amount range.",
                    "role": "SUPPORTING",
                    "localizability": "LOCAL_REGION",
                }
            ],
            "rationale": "The range is visible.",
        },
        [1],
    )

    assert result.evidence[0].bbox == [200.0, 50.0, 600.0, 150.0]
    assert result.evidence[0].bbox_metadata["source"] == "gemini_visual_grounding"
    assert result.evidence[0].bbox_metadata["normalized_coordinate_space"] == "0_1000_yxyx"


def test_image_verifier_refines_text_region_with_ocr_phrase(tmp_path: Path, monkeypatch) -> None:
    from ui_verifier.localization.text_box_localizer import OcrTextBox

    image_path = tmp_path / "step_01.png"
    Image.new("RGB", (1298, 4701), color="white").save(image_path)
    verifier = GeminiImageClaimVerifier(
        flow_id="flow-1",
        screenshot_steps=[ScreenshotStep(step_index=1, screenshot_path=str(image_path))],
        cache_path=tmp_path / "cache.json",
    )
    monkeypatch.setattr(
        verifier,
        "_ocr_boxes_for_grounding",
        lambda _: [
            OcrTextBox("Great", {"x1": 264, "y1": 32, "x2": 310, "y2": 46}, 0.97, "word"),
            OcrTextBox("Escape", {"x1": 318, "y1": 32, "x2": 376, "y2": 51}, 0.97, "word"),
            OcrTextBox("calendar", {"x1": 278, "y1": 111, "x2": 344, "y2": 124}, 0.59, "word"),
            OcrTextBox("Six", {"x1": 1103, "y1": 1879, "x2": 1127, "y2": 1893}, 0.96, "word"),
            OcrTextBox("Flags", {"x1": 1133, "y1": 1878, "x2": 1174, "y2": 1898}, 0.96, "word"),
            OcrTextBox("Great", {"x1": 1181, "y1": 1879, "x2": 1225, "y2": 1893}, 0.97, "word"),
        ],
    )

    result = verifier._result_from_gemini(
        _claim(),
        {
            "claim_status": "SUPPORTED",
            "evidence_step_indices": [1],
            "visible_observations": ["Great Escape is selected."],
            "uncertainty_reasons": [],
            "evidence_regions": [
                {
                    "step_index": 1,
                    "box_2d": [20, 200, 40, 300],
                    "description": "The selected park 'Great Escape' displayed in the header.",
                    "role": "SUPPORTING",
                    "localizability": "LOCAL_REGION",
                }
            ],
            "rationale": "The selected park is visible.",
        },
        [1],
    )

    bbox = result.evidence[0].bbox
    assert bbox is not None
    assert 195 <= bbox[0] <= 205
    assert bbox[1] < 32
    assert bbox[2] > 376
    assert bbox[3] > 51
    assert result.evidence[0].bbox_metadata["source"] == "gemini_visual_grounding_ocr_refined"
    assert result.evidence[0].bbox_metadata["raw_gemini_pixel_bbox"] == [259.6, 94.02, 389.4, 188.04]


def test_pipeline_does_not_replace_missing_gemini_region_with_ocr_box(tmp_path: Path) -> None:
    image_path = tmp_path / "step_01.png"
    Image.new("RGB", (100, 80), color="white").save(image_path)
    pipeline = EvidenceFirstVerificationPipeline()
    item = EvidenceItem(
        step_index=1,
        screenshot_path=str(image_path),
        visible_observation="A relevant indicator is visible.",
        source="gemini_image",
    )

    localized = pipeline._localize_evidence_item("The claim", item)

    assert localized.bbox is None


def test_image_verifier_recovers_explicit_screenshot_references_when_indices_are_omitted(tmp_path: Path) -> None:
    image_paths = []
    for index in range(1, 5):
        image_path = tmp_path / f"step_{index:02d}.png"
        Image.new("RGB", (16, 16), color="white").save(image_path)
        image_paths.append(image_path)
    verifier = GeminiImageClaimVerifier(
        flow_id="flow-1",
        screenshot_steps=[
            ScreenshotStep(step_index=index, screenshot_path=str(path))
            for index, path in enumerate(image_paths, start=1)
        ],
        cache_path=tmp_path / "cache.json",
    )

    result = verifier._result_from_gemini(
        _claim(text="The page shows a Jobs entry point."),
        {
            "claim_status": "SUPPORTED",
            "visible_observations": [
                "Screenshot 1 shows Jobs in the header.",
                "Screenshots 2, 3, and 4 also show the entry point.",
            ],
            "rationale": "The explicitly cited screenshots support the claim.",
        },
        [1, 2, 3, 4],
    )

    assert [item.step_index for item in result.evidence] == [1, 2, 3, 4]
    assert result.metadata["evidence_step_indices_inferred_from_observation"] is True


def test_batched_verifier_groups_overlapping_evidence_and_preserves_metadata(tmp_path: Path, monkeypatch) -> None:
    image_paths = []
    for index in range(1, 5):
        image_path = tmp_path / f"step_{index:02d}.png"
        Image.new("RGB", (16, 16), color="white").save(image_path)
        image_paths.append(image_path)

    verifier = BatchedGeminiImageClaimVerifier(
        flow_id="flow-1",
        screenshot_steps=[
            ScreenshotStep(step_index=index, screenshot_path=str(path))
            for index, path in enumerate(image_paths, start=1)
        ],
        cache_path=tmp_path / "cache.json",
        max_images_per_claim=2,
        max_api_calls=None,
        include_sequence_context=False,
    )

    calls: list[tuple[str, list[int]]] = []

    def fake_call(payload, selected_steps):
        calls.append((payload["group_id"], selected_steps))
        return (
            {
                "claims": [
                    {
                        "claim_id": claim["claim_id"],
                        "claim_status": "SUPPORTED",
                        "evidence_step_indices": [selected_steps[0]],
                        "uncertainty_reasons": [],
                        "visible_observations": ["The requested element is visible."],
                        "rationale": "Visible evidence supports the claim.",
                    }
                    for claim in payload["claims"]
                ]
            },
            "{}",
            {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15, "cached_content_tokens": 0},
        )

    monkeypatch.setattr(verifier, "_call_gemini_group", fake_call)

    jobs = [
        (_claim(claim_id="REQ-1-C1", text="The page shows order details."), [_evidence(1), _evidence(2)], UIEvaluability.UI_VERIFIABLE),
        (_claim(claim_id="REQ-1-C2", text="The page shows order total."), [_evidence(2), _evidence(3)], UIEvaluability.UI_VERIFIABLE),
        (_claim(claim_id="REQ-1-C3", text="The page shows help text."), [_evidence(4)], UIEvaluability.UI_VERIFIABLE),
    ]

    results = verifier.verify_many(jobs)

    assert [call[1] for call in calls] == [[1, 2, 3, 4]]
    assert [result.status for result in results] == [ClaimStatus.SUPPORTED] * 3
    assert results[0].metadata["prompt_group_id"] == "G1"
    assert results[2].metadata["prompt_group_id"] == "G1"
    assert verifier.diagnostics["group_count"] == 1
    assert verifier.diagnostics["unique_images_attached"] == 4


def test_batched_verifier_caps_claims_per_group(tmp_path: Path, monkeypatch) -> None:
    image_paths = []
    for index in range(1, 4):
        image_path = tmp_path / f"step_{index:02d}.png"
        Image.new("RGB", (16, 16), color="white").save(image_path)
        image_paths.append(image_path)

    verifier = BatchedGeminiImageClaimVerifier(
        flow_id="flow-1",
        screenshot_steps=[
            ScreenshotStep(step_index=index, screenshot_path=str(path))
            for index, path in enumerate(image_paths, start=1)
        ],
        cache_path=tmp_path / "cache.json",
        max_claims_per_group=2,
        max_api_calls=None,
    )
    calls: list[list[str]] = []

    def fake_call(payload, selected_steps):
        calls.append([claim["claim_id"] for claim in payload["claims"]])
        return (
            {
                "claims": [
                    {
                        "claim_id": claim["claim_id"],
                        "claim_status": "SUPPORTED",
                        "evidence_step_indices": [selected_steps[0]],
                        "uncertainty_reasons": [],
                        "visible_observations": ["Visible."],
                        "rationale": "Visible evidence supports the claim.",
                    }
                    for claim in payload["claims"]
                ]
            },
            "{}",
            {},
        )

    monkeypatch.setattr(verifier, "_call_gemini_group", fake_call)
    jobs = [
        (_claim(claim_id=f"REQ-1-C{index}", text=f"Claim {index}."), [_evidence(1)], UIEvaluability.UI_VERIFIABLE)
        for index in range(1, 6)
    ]

    verifier.verify_many(jobs)

    assert [len(group) for group in calls] == [2, 2, 1]
    assert verifier.diagnostics["group_count"] == 3


def test_batched_verifier_single_call_uses_all_screenshots(tmp_path: Path, monkeypatch) -> None:
    image_paths = []
    for index in range(1, 4):
        image_path = tmp_path / f"step_{index:02d}.png"
        Image.new("RGB", (16, 16), color="white").save(image_path)
        image_paths.append(image_path)

    verifier = BatchedGeminiImageClaimVerifier(
        flow_id="flow-1",
        screenshot_steps=[
            ScreenshotStep(step_index=index, screenshot_path=str(path))
            for index, path in enumerate(image_paths, start=1)
        ],
        cache_path=tmp_path / "cache.json",
        grouping_strategy="single-call",
    )
    seen_steps: list[list[int]] = []

    def fake_call(payload, selected_steps):
        seen_steps.append(selected_steps)
        return (
            {
                "claims": [
                    {
                        "claim_id": payload["claims"][0]["claim_id"],
                        "claim_status": "MISSING",
                        "evidence_step_indices": [],
                        "uncertainty_reasons": ["FLOW_COVERAGE_GAP"],
                        "visible_observations": [],
                        "rationale": "Not visible.",
                    }
                ]
            },
            "{}",
            {},
        )

    monkeypatch.setattr(verifier, "_call_gemini_group", fake_call)

    results = verifier.verify_many(
        [(_claim(claim_id="REQ-1-C1", text="The page shows a confirmation banner."), [_evidence(2)], UIEvaluability.UI_VERIFIABLE)]
    )

    assert seen_steps == [[1, 2, 3]]
    assert results[0].metadata["grouping_strategy"] == "single-call"
    assert results[0].status == ClaimStatus.MISSING


def test_destroyed_chronology_hides_original_order_and_maps_evidence_back(
    tmp_path: Path,
    monkeypatch,
) -> None:
    image_paths = []
    for index in range(1, 5):
        image_path = tmp_path / f"step_{index:02d}.png"
        Image.new("RGB", (16, 16), color=(index * 20, 0, 0)).save(image_path)
        image_paths.append(image_path)

    verifier = BatchedGeminiImageClaimVerifier(
        flow_id="flow-1",
        screenshot_steps=[
            ScreenshotStep(step_index=index, screenshot_path=str(path))
            for index, path in enumerate(image_paths, start=1)
        ],
        cache_path=tmp_path / "cache.json",
        grouping_strategy="single-call",
        chronology_mode="destroyed",
        order_seed=20260726,
    )
    observed: dict = {}

    def fake_call(payload, selected_steps):
        observed["payload"] = payload
        observed["selected_steps"] = selected_steps
        return (
            {
                "claims": [
                    {
                        "claim_id": payload["claims"][0]["claim_id"],
                        "claim_status": "SUPPORTED",
                        "evidence_step_indices": [1],
                        "uncertainty_reasons": [],
                        "visible_observations": ["Apparent step 1 contains the visible control."],
                        "rationale": "The visible control is present without relying on chronology.",
                    }
                ]
            },
            "{}",
            {},
        )

    monkeypatch.setattr(verifier, "_call_gemini_group", fake_call)
    results = verifier.verify_many(
        [
            (
                _claim(claim_id="REQ-1-C1", text="The page shows a help control."),
                [_evidence(2)],
                UIEvaluability.UI_VERIFIABLE,
            )
        ]
    )

    payload = observed["payload"]
    assert payload["chronology_mode"] == "destroyed"
    assert payload["attached_step_indices"] == [1, 2, 3, 4]
    assert observed["selected_steps"] != [1, 2, 3, 4]
    assert [asset["step_index"] for asset in payload["screenshot_assets"]] == [1, 2, 3, 4]
    assert "original chronology was deliberately removed" in verifier._prompt(payload)
    expected_original = verifier.diagnostics["groups"][0]["model_to_original_step"][1]
    assert [item.step_index for item in results[0].evidence] == [expected_original]
    assert results[0].metadata["chronology_mode"] == "destroyed"


def test_single_call_claim_chunks_each_keep_all_screenshots(tmp_path: Path) -> None:
    image_paths = []
    for index in range(1, 4):
        image_path = tmp_path / f"step_{index:02d}.png"
        Image.new("RGB", (16, 16), color="white").save(image_path)
        image_paths.append(image_path)

    verifier = BatchedGeminiImageClaimVerifier(
        flow_id="flow-1",
        screenshot_steps=[
            ScreenshotStep(step_index=index, screenshot_path=str(path))
            for index, path in enumerate(image_paths, start=1)
        ],
        cache_path=tmp_path / "cache.json",
        grouping_strategy="single-call",
        max_claims_per_group=2,
    )
    jobs = [
        {
            "index": index,
            "claim": _claim(claim_id=f"REQ-1-C{index}", text=f"Claim {index}."),
            "evidence": [_evidence(1)],
            "ui_evaluability": UIEvaluability.UI_VERIFIABLE,
            "selected_steps": [1],
        }
        for index in range(1, 6)
    ]

    groups = verifier._build_groups(jobs)

    assert [len(group["payload"]["claims"]) for group in groups] == [2, 2, 1]
    assert [group["step_indices"] for group in groups] == [[1, 2, 3], [1, 2, 3], [1, 2, 3]]


def test_batched_candidate_grounding_resolves_ids_and_allows_clean_only_steps(tmp_path: Path) -> None:
    image_paths = []
    for index in range(1, 3):
        image_path = tmp_path / f"step_{index:02d}.png"
        Image.new("RGB", (100, 80), color="white").save(image_path)
        image_paths.append(image_path)
    assets = tmp_path / "marks"
    assets.mkdir()
    for suffix in ("ui_marks", "ocr_marks", "candidate_atlas"):
        Image.new("RGB", (100, 80), color="white").save(assets / f"step_01_{suffix}.png")
    candidates = tmp_path / "candidates.json"
    candidates.write_text(
        json.dumps(
            {
                "flow_id": "flow-1",
                "steps": {
                    "1": [
                        {
                            "candidate_id": "U01",
                            "source": "omniparser_ui",
                            "bbox": [10, 20, 50, 60],
                            "text": "Search",
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    verifier = BatchedGeminiImageClaimVerifier(
        flow_id="flow-1",
        screenshot_steps=[
            ScreenshotStep(step_index=index, screenshot_path=str(path))
            for index, path in enumerate(image_paths, start=1)
        ],
        cache_path=tmp_path / "cache.json",
        grouping_strategy="single-call",
        candidate_package=candidates,
        marked_assets_dir=assets,
        predict_ui_evaluability=True,
    )

    group = verifier._group_payload(
        group_id="G1",
        jobs=[
            {
                "claim": _claim(claim_id="REQ-1-C1", text="The page has search."),
                "ui_evaluability": UIEvaluability.UI_VERIFIABLE,
                "selected_steps": [1],
            }
        ],
        step_indices=[1, 2],
    )
    regions = verifier._normalized_evidence_regions(
        {
            "evidence_regions": [
                {
                    "step_index": 1,
                    "candidate_ids": ["U01"],
                    "description": "Search control",
                }
            ]
        },
        [1, 2],
    )

    assert group["payload"]["attachment_order"] == [
        {"step_index": 1, "images": ["clean", "ui_marks", "ocr_marks", "candidate_atlas"]},
        {"step_index": 2, "images": ["clean"]},
    ]
    assert regions[0]["bbox"] == [10.0, 20.0, 50.0, 60.0]
    assert regions[0]["bbox_metadata"]["candidate_id"] == "U01"
    assert "ui_evaluability" not in group["payload"]["claims"][0]
    result = verifier._result_from_batched_gemini(
        verifier._group_payload(
            group_id="G2",
            jobs=[
                {
                    "claim": _claim(claim_id="REQ-1-C1", text="The page has search."),
                    "ui_evaluability": UIEvaluability.UI_VERIFIABLE,
                    "selected_steps": [1],
                }
            ],
            step_indices=[1],
        )["jobs"][0]["claim"],
        {
            "claim_status": "MISSING",
            "ui_evaluability": "PARTIALLY_UI_VERIFIABLE",
            "evidence_step_indices": [],
            "rationale": "The visible portion is incomplete.",
        },
        group,
    )
    assert result.metadata["model_ui_evaluability"] == "PARTIALLY_UI_VERIFIABLE"


def test_image_verifier_retries_invalid_json_response(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "step_01.png"
    Image.new("RGB", (16, 16), color="white").save(image_path)
    verifier = GeminiImageClaimVerifier(
        flow_id="flow-1",
        screenshot_steps=[ScreenshotStep(step_index=1, screenshot_path=str(image_path))],
        cache_path=tmp_path / "cache.json",
        max_retries=1,
    )
    responses = iter(
        [
            "not json",
            json.dumps(
                {
                    "claim_id": "REQ-1-C1",
                    "claim_status": "SUPPORTED",
                    "evidence_step_indices": [1],
                    "uncertainty_reasons": [],
                    "visible_observations": ["A confirmation banner is visible."],
                    "rationale": "Visible evidence supports the claim.",
                }
            ),
        ]
    )

    monkeypatch.setattr("ui_verifier.requirements.gemini_client.run_gemini", lambda *args, **kwargs: next(responses))
    monkeypatch.setattr("ui_verifier.verification_pipeline.gemini_image_claim_verifier.time.sleep", lambda _: None)

    parsed, _ = verifier._call_gemini(
        verifier._request_payload(_claim(), [1], ui_evaluability=UIEvaluability.UI_VERIFIABLE),
        [1],
    )

    assert parsed["claim_status"] == "SUPPORTED"
    assert verifier.diagnostics["api_calls"] == 1


def test_image_verifier_downgrades_supported_result_with_unattached_evidence(tmp_path: Path) -> None:
    verifier = GeminiImageClaimVerifier(
        flow_id="flow-1",
        screenshot_steps=[
            ScreenshotStep(step_index=1, screenshot_path="step_01.png"),
            ScreenshotStep(step_index=8, screenshot_path="step_08.png"),
        ],
        cache_path=tmp_path / "cache.json",
    )

    result = verifier._result_from_gemini(
        _claim(),
        {
            "claim_status": "SUPPORTED",
            "evidence_step_indices": [5, 6],
            "visible_observations": ["The requested element is visible."],
            "uncertainty_reasons": [],
            "rationale": "The claim is supported.",
        },
        [1, 8],
    )

    assert result.status == ClaimStatus.MISSING
    assert result.evidence == []
    assert UncertaintyReason.FLOW_COVERAGE_GAP in result.uncertainty_reasons


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
