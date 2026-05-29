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


_POSITIVE_STATUSES = {ClaimStatus.SUPPORTED, ClaimStatus.PARTIALLY_SUPPORTED}
_PROBLEM_STATUSES = {ClaimStatus.MISSING, ClaimStatus.HIDDEN, ClaimStatus.AMBIGUOUS}


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
        screens_available: bool,
    ) -> tuple[VerificationLabel, str]:
        if not screens_available:
            return VerificationLabel.ABSTAIN, "No screenshots were available, so the requirement cannot be verified."

        if ui_evaluability == UIEvaluability.NOT_UI_VERIFIABLE:
            return (
                VerificationLabel.ABSTAIN,
                "The requirement is not UI-verifiable from screenshots, so the pipeline abstains.",
            )

        central_visible_contradiction = any(
            result.is_core
            and result.is_observable
            and result.status == ClaimStatus.CONTRADICTED
            and bool(result.evidence)
            for result in claim_results
        )
        if central_visible_contradiction:
            return (
                VerificationLabel.NOT_FULFILLED,
                "A central observable claim is contradicted by visible evidence.",
            )

        if not evidence:
            return (
                VerificationLabel.ABSTAIN,
                "No useful visible evidence was retrieved; missing evidence alone is not a negative verdict.",
            )

        important_claims = [result for result in claim_results if result.is_core]
        core_observable_claims = [result for result in important_claims if result.is_observable]
        central_hidden_unresolved = any(
            result.is_core and result.status == ClaimStatus.HIDDEN for result in claim_results
        )
        all_core_observable_supported = bool(core_observable_claims) and all(
            result.status in _POSITIVE_STATUSES for result in core_observable_claims
        )
        any_important_supported = any(result.status in _POSITIVE_STATUSES for result in important_claims)
        any_important_problem = any(result.status in _PROBLEM_STATUSES for result in important_claims)

        if all_core_observable_supported and not central_hidden_unresolved:
            return (
                VerificationLabel.FULFILLED,
                "All central observable claims have visible evidence and no central hidden claim remains unresolved.",
            )

        if any_important_supported and any_important_problem:
            return (
                VerificationLabel.PARTIALLY_FULFILLED,
                "At least one important claim has visible support, but another important claim is missing, hidden, or ambiguous.",
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
