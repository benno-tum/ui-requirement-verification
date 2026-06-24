from __future__ import annotations

from ui_verifier.verification_pipeline.requirement_understanding import has_hidden_indicator
from ui_verifier.verification_pipeline.schemas import (
    ClaimStatus,
    ClaimVerificationResult,
    EvidenceItem,
    RequirementClaim,
    UIEvaluability,
    UncertaintyReason,
)


class ClaimVerifier:
    """Rule-based placeholder for an eventual MLLM claim verifier.

    TODO: A Gemini/MLLM implementation can replace this component while
    preserving the same ClaimVerificationResult contract.
    """

    def __init__(self, *, strong_threshold: float = 0.45, weak_threshold: float = 0.12) -> None:
        self.strong_threshold = strong_threshold
        self.weak_threshold = weak_threshold

    def verify(
        self,
        claim: RequirementClaim,
        evidence: list[EvidenceItem],
        *,
        ui_evaluability: UIEvaluability,
    ) -> ClaimVerificationResult:
        if not claim.is_observable or has_hidden_indicator(claim.claim_text):
            reasons = list(dict.fromkeys([*claim.uncertainty_reasons, UncertaintyReason.NONTRIVIAL_HIDDEN_PROPERTY]))
            return ClaimVerificationResult(
                claim_id=claim.claim_id,
                requirement_id=claim.requirement_id,
                claim_text=claim.claim_text,
                status=ClaimStatus.HIDDEN,
                is_core=claim.is_core,
                is_observable=False,
                evidence=[],
                uncertainty_reasons=reasons,
                confidence=None,
                rationale="The claim references a hidden or non-visual property that screenshots cannot verify directly.",
            )

        if not evidence:
            reasons = list(dict.fromkeys([*claim.uncertainty_reasons, UncertaintyReason.FLOW_COVERAGE_GAP]))
            return ClaimVerificationResult(
                claim_id=claim.claim_id,
                requirement_id=claim.requirement_id,
                claim_text=claim.claim_text,
                status=ClaimStatus.MISSING,
                is_core=claim.is_core,
                is_observable=claim.is_observable,
                evidence=[],
                uncertainty_reasons=reasons,
                confidence=0.0,
                rationale="No visible evidence candidate was retrieved for this UI-verifiable claim.",
            )

        max_confidence = max((item.confidence or 0.0) for item in evidence)
        if max_confidence >= self.strong_threshold:
            status = ClaimStatus.SUPPORTED
            rationale = "Retrieved visible evidence is strong enough for this placeholder verifier."
        elif max_confidence >= self.weak_threshold:
            status = ClaimStatus.PARTIALLY_SUPPORTED
            rationale = "Retrieved visible evidence is weak or incomplete, so the claim is only partially supported."
        else:
            status = ClaimStatus.MISSING
            rationale = "Retrieved candidates were below the evidence threshold for support."

        reasons = list(claim.uncertainty_reasons)
        if status not in {ClaimStatus.SUPPORTED, ClaimStatus.SUPPORTED_WITH_CAVEAT}:
            reasons = list(dict.fromkeys([*reasons, UncertaintyReason.EVIDENCE_INTERPRETATION_AMBIGUITY]))

        return ClaimVerificationResult(
            claim_id=claim.claim_id,
            requirement_id=claim.requirement_id,
            claim_text=claim.claim_text,
            status=status,
            is_core=claim.is_core,
            is_observable=claim.is_observable,
            evidence=evidence if status in {ClaimStatus.SUPPORTED, ClaimStatus.SUPPORTED_WITH_CAVEAT, ClaimStatus.PARTIALLY_SUPPORTED} else [],
            uncertainty_reasons=reasons,
            confidence=max_confidence,
            rationale=rationale,
        )
