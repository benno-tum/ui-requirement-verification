from __future__ import annotations

from dataclasses import dataclass, field

from ui_verifier.verification.schemas import (
    ClaimEvidenceStatus,
    ClaimImportance,
    ClaimType,
    UIEvaluability,
    VerificationGoldItem,
    VerificationLabel,
)


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)


def validate_verification_gold_item(item: VerificationGoldItem) -> ValidationResult:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    if item.verification_label is None:
        errors.append(ValidationIssue("verification_label", "Verification label is required."))

    if item.ui_evaluability is None:
        errors.append(ValidationIssue("ui_evaluability", "UI evaluability is required."))

    if item.ui_evaluability != UIEvaluability.NOT_UI_VERIFIABLE and not item.evidence_steps:
        errors.append(ValidationIssue("evidence_steps", "UI-verifiable items must include evidence steps."))

    if item.verification_label in {VerificationLabel.FULFILLED, VerificationLabel.PARTIALLY_FULFILLED} and not item.claims:
        warnings.append(ValidationIssue("claims", "Fulfilled items should include claim-level evidence."))

    _validate_claims(item, errors, warnings)
    return ValidationResult(errors=errors, warnings=warnings)


def _validate_claims(
    item: VerificationGoldItem,
    errors: list[ValidationIssue],
    warnings: list[ValidationIssue],
) -> None:
    allowed_steps = set(item.evidence_steps)
    has_core_claim = False

    for index, claim in enumerate(item.claims, start=1):
        field_prefix = f"claims[{index}]"
        if claim.importance == ClaimImportance.CORE:
            has_core_claim = True

        if claim.claim_type == ClaimType.OBSERVABLE and claim.status in {
            ClaimEvidenceStatus.SUPPORTED,
            ClaimEvidenceStatus.CONTRADICTED,
            ClaimEvidenceStatus.MISSING,
        } and not claim.evidence_steps:
            errors.append(ValidationIssue(field_prefix, "Observable claim decisions must include evidence steps."))

        invalid_steps = [step for step in claim.evidence_steps if step not in allowed_steps]
        if invalid_steps:
            errors.append(
                ValidationIssue(
                    field_prefix,
                    f"Claim evidence steps must be included in item evidence_steps: {invalid_steps}.",
                )
            )

        if claim.claim_type == ClaimType.HIDDEN and claim.status not in {
            ClaimEvidenceStatus.HIDDEN,
            ClaimEvidenceStatus.AMBIGUOUS,
            ClaimEvidenceStatus.OUT_OF_SCOPE,
        }:
            warnings.append(ValidationIssue(field_prefix, "Hidden claims should usually use hidden or ambiguous status."))

    if item.claims and not has_core_claim:
        warnings.append(ValidationIssue("claims", "At least one claim should be marked CORE."))
