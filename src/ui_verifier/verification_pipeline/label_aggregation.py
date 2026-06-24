from __future__ import annotations

from ui_verifier.verification_pipeline.schemas import (
    ClaimStatus,
    ClaimVerificationResult,
    EvidenceItem,
    RequirementInput,
    RequirementVerificationResult,
    UIEvaluability,
    UncertaintyReason,
    VerificationLabel,
)


_FULFILLED_STATUSES = {ClaimStatus.SUPPORTED, ClaimStatus.SUPPORTED_WITH_CAVEAT}
_PROBLEM_STATUSES = {
    ClaimStatus.PARTIALLY_SUPPORTED,
    ClaimStatus.MISSING,
    ClaimStatus.HIDDEN,
    ClaimStatus.AMBIGUOUS,
    ClaimStatus.OUT_OF_SCOPE,
}
_FULFILLED_BLOCKING_REASONS = {
    UncertaintyReason.FLOW_COVERAGE_GAP,
    UncertaintyReason.UNVERIFIED_SYSTEM_OUTCOME,
    UncertaintyReason.NONTRIVIAL_HIDDEN_PROPERTY,
    UncertaintyReason.EVIDENCE_INTERPRETATION_AMBIGUITY,
}


def _dedupe_reasons(reasons: list[UncertaintyReason]) -> list[UncertaintyReason]:
    return list(dict.fromkeys(reasons))


def _dedupe_evidence(claim_results: list[ClaimVerificationResult]) -> list[EvidenceItem]:
    evidence: list[EvidenceItem] = []
    seen: set[tuple[int, str, str | None, str]] = set()
    for result in claim_results:
        for item in result.evidence:
            key = (item.step_index, item.screenshot_path, item.source, item.visible_observation)
            if key in seen:
                continue
            seen.add(key)
            evidence.append(item)
    evidence.sort(key=lambda item: (item.step_index, item.screenshot_path, item.source or ""))
    return evidence


class LabelAggregator:
    def aggregate(
        self,
        *,
        requirement: RequirementInput,
        ui_evaluability: UIEvaluability,
        claim_results: list[ClaimVerificationResult],
        requirement_uncertainty_reasons: list[UncertaintyReason] | None = None,
        screens_available: bool = True,
        metadata: dict[str, object] | None = None,
    ) -> RequirementVerificationResult:
        evidence = _dedupe_evidence(claim_results)
        uncertainty_reasons = self._collect_uncertainty_reasons(
            claim_results,
            requirement_uncertainty_reasons or [],
            evidence=evidence,
            screens_available=screens_available,
        )
        label, rationale = self._label_and_rationale(
            ui_evaluability=ui_evaluability,
            claim_results=claim_results,
            evidence=evidence,
            uncertainty_reasons=uncertainty_reasons,
            screens_available=screens_available,
        )

        return RequirementVerificationResult(
            requirement_id=requirement.requirement_id,
            requirement_text=requirement.text,
            ui_evaluability=ui_evaluability,
            final_label=label,
            claims=claim_results,
            evidence=evidence,
            uncertainty_reasons=uncertainty_reasons,
            rationale=rationale,
            metadata=dict(metadata or {}),
        )

    def _label_and_rationale(
        self,
        *,
        ui_evaluability: UIEvaluability,
        claim_results: list[ClaimVerificationResult],
        evidence: list[EvidenceItem],
        uncertainty_reasons: list[UncertaintyReason],
        screens_available: bool,
    ) -> tuple[VerificationLabel, str]:
        if not screens_available:
            return VerificationLabel.ABSTAIN, "No screenshots were available, so the requirement cannot be verified."

        if ui_evaluability == UIEvaluability.NOT_UI_VERIFIABLE:
            return (
                VerificationLabel.ABSTAIN,
                "The requirement is not UI-verifiable from screenshots, so the pipeline abstains.",
            )

        important_claims = [result for result in claim_results if result.is_core]
        central_contradiction = any(result.status == ClaimStatus.CONTRADICTED for result in important_claims)
        if central_contradiction:
            return (
                VerificationLabel.NOT_FULFILLED,
                "A central claim is contradicted by evidence.",
            )

        if not evidence:
            return (
                VerificationLabel.ABSTAIN,
                "No useful visible evidence was retrieved; missing evidence alone is not a negative verdict.",
            )

        all_core_supported = bool(important_claims) and all(
            result.status in _FULFILLED_STATUSES for result in important_claims
        )
        any_important_supported = any(result.status in _FULFILLED_STATUSES for result in important_claims)
        any_important_partially_supported = any(
            result.status == ClaimStatus.PARTIALLY_SUPPORTED and bool(result.evidence) for result in important_claims
        )
        any_important_problem = any(result.status in _PROBLEM_STATUSES for result in important_claims)
        has_fulfilled_blocking_reason = any(reason in _FULFILLED_BLOCKING_REASONS for reason in uncertainty_reasons)

        if all_core_supported and not has_fulfilled_blocking_reason:
            if any(result.status == ClaimStatus.SUPPORTED_WITH_CAVEAT for result in important_claims):
                return (
                    VerificationLabel.FULFILLED,
                    "All central claims are supported, with at least one accepted caveat that does not block fulfillment.",
                )
            return (
                VerificationLabel.FULFILLED,
                "All central claims are supported by visible evidence and no material uncertainty blocks fulfillment.",
            )

        if any_important_supported and any_important_problem:
            return (
                VerificationLabel.PARTIALLY_FULFILLED,
                "At least one important claim is supported, but another important claim is partial, missing, hidden, ambiguous, or out of scope.",
            )

        if any_important_partially_supported:
            return (
                VerificationLabel.PARTIALLY_FULFILLED,
                "At least one important claim has partial visible support, but the fulfilled gate was not met.",
            )

        if any_important_supported and has_fulfilled_blocking_reason:
            return (
                VerificationLabel.PARTIALLY_FULFILLED,
                "Important visible support exists, but material uncertainty blocks a fulfilled verdict.",
            )

        if any_important_supported:
            return (
                VerificationLabel.PARTIALLY_FULFILLED,
                "Some important visible evidence was found, but the strict fulfilled gate was not met.",
            )

        return (
            VerificationLabel.ABSTAIN,
            "The available evidence is insufficient for a positive or negative requirement-level verdict.",
        )

    @staticmethod
    def _collect_uncertainty_reasons(
        claim_results: list[ClaimVerificationResult],
        requirement_reasons: list[UncertaintyReason],
        *,
        evidence: list[EvidenceItem],
        screens_available: bool,
    ) -> list[UncertaintyReason]:
        reasons = list(requirement_reasons)
        for result in claim_results:
            reasons.extend(result.uncertainty_reasons)
            if result.status == ClaimStatus.HIDDEN:
                reasons.append(UncertaintyReason.NONTRIVIAL_HIDDEN_PROPERTY)
            if result.status == ClaimStatus.MISSING:
                reasons.append(UncertaintyReason.FLOW_COVERAGE_GAP)
            if result.status in {ClaimStatus.AMBIGUOUS, ClaimStatus.PARTIALLY_SUPPORTED}:
                reasons.append(UncertaintyReason.EVIDENCE_INTERPRETATION_AMBIGUITY)

        if not screens_available or not evidence:
            reasons.append(UncertaintyReason.FLOW_COVERAGE_GAP)

        return _dedupe_reasons(reasons)
