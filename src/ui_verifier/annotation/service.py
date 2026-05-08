from __future__ import annotations

from ui_verifier.annotation.storage import AnnotationStorage
from ui_verifier.requirements.candidate_generation import build_verification_candidates
from ui_verifier.requirements.schemas import (
    BenchmarkDecision,
    CandidateRequirement,
    CandidateOrigin,
    GoldRequirement,
    GoldRequirementFile,
    HarvestedRequirement,
    NonEvaluableReason,
    RequirementInspectionType,
    RequirementReviewStatus,
    RequirementScope,
    UiEvaluability,
    VisibleSubtype,
    CandidateRequirementFile,
)
from ui_verifier.verification.label_validation import validate_verification_gold_item
from ui_verifier.verification.schemas import (
    ClaimEvidence,
    UIEvaluability,
    VerificationGoldFile,
    VerificationGoldItem,
    VerificationLabel,
    _utc_now_iso,
)


def _infer_scope(step_indices: list[int]) -> RequirementScope:
    if len(step_indices) <= 1:
        return RequirementScope.SINGLE_SCREEN
    return RequirementScope.MULTI_SCREEN


def _extract_intended_label(tags: list[str]) -> VerificationLabel | None:
    for tag in tags:
        if not isinstance(tag, str):
            continue
        if not tag.startswith("intended_label:"):
            continue
        _, raw_value = tag.split(":", 1)
        try:
            return VerificationLabel(raw_value.strip().upper())
        except ValueError:
            normalized = raw_value.strip().lower().replace("-", "_").replace(" ", "_")
            mapping = {
                "fulfilled": VerificationLabel.FULFILLED,
                "partially_fulfilled": VerificationLabel.PARTIALLY_FULFILLED,
                "not_fulfilled": VerificationLabel.NOT_FULFILLED,
                "abstain": VerificationLabel.ABSTAIN,
            }
            return mapping.get(normalized)
    return None


def _map_ui_evaluability(value: UiEvaluability) -> UIEvaluability:
    return UIEvaluability(value.value)


def _map_verification_label(value: str | None) -> VerificationLabel | None:
    if value is None:
        return None
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "fulfilled": VerificationLabel.FULFILLED,
        "partially_fulfilled": VerificationLabel.PARTIALLY_FULFILLED,
        "not_fulfilled": VerificationLabel.NOT_FULFILLED,
        "abstain": VerificationLabel.ABSTAIN,
    }
    return mapping.get(normalized)


class AnnotationService:
    def __init__(self, storage: AnnotationStorage | None = None) -> None:
        self.storage = storage or AnnotationStorage()

    def list_harvested(self, flow_id: str) -> list[HarvestedRequirement]:
        harvest_file = self.storage.load_harvested_file(flow_id)
        return harvest_file.requirements

    def rebuild_candidates_from_harvested(
        self,
        flow_id: str,
        *,
        candidate_model_name: str = "gemini-2.5-flash-lite",
        allow_overwrite_with_gold: bool = False,
    ) -> CandidateRequirementFile:
        gold_file = self.storage.load_gold_file(flow_id)
        if gold_file is not None and gold_file.requirements and not allow_overwrite_with_gold:
            raise ValueError(
                f"Gold requirements already exist for flow {flow_id}. Rebuilding candidates may desynchronize candidate and gold sets."
            )

        harvest_file = self.storage.load_harvested_file(flow_id)
        candidate_file = build_verification_candidates(harvest_file)
        self.storage.save_candidate_file(candidate_file)
        return candidate_file

    def list_candidates(self, flow_id: str, only_pending: bool = False) -> list[CandidateRequirement]:
        candidate_file = self.storage.load_candidate_file(flow_id)
        if not only_pending:
            return candidate_file.requirements

        pending_statuses = {
            RequirementReviewStatus.CANDIDATE,
            RequirementReviewStatus.NEEDS_REVIEW,
        }
        return [r for r in candidate_file.requirements if r.review_status in pending_statuses]

    def get_candidate(self, flow_id: str, requirement_id: str) -> CandidateRequirement:
        candidate_file = self.storage.load_candidate_file(flow_id)
        for req in candidate_file.requirements:
            if req.requirement_id == requirement_id:
                return req
        raise KeyError(f"Candidate requirement not found: {flow_id}/{requirement_id}")

    def mark_needs_review(self, flow_id: str, requirement_id: str) -> CandidateRequirement:
        candidate_file = self.storage.load_candidate_file(flow_id)
        candidate = self._find_candidate(candidate_file.requirements, requirement_id)
        candidate.review_status = RequirementReviewStatus.NEEDS_REVIEW
        self.storage.save_candidate_file(candidate_file)
        return candidate

    def update_candidate(
        self,
        flow_id: str,
        requirement_id: str,
        *,
        edited_text: str | None = None,
        edited_step_indices: list[int] | None = None,
        edited_tags: list[str] | None = None,
        annotation_notes: str | None = None,
        annotated_by: str | None = None,
        review_status: RequirementReviewStatus | None = None,
        benchmark_decision: BenchmarkDecision | None = None,
        ui_evaluability: UiEvaluability | None = None,
        visible_subtype: VisibleSubtype | None = None,
        requirement_type: RequirementInspectionType | None = None,
        verification_label: str | None = None,
        uncertainty_reasons: list[str] | None = None,
        claims: list[dict[str, object]] | None = None,
        evidence_steps: list[int] | None = None,
        evidence_note: str | None = None,
        rationale: str | None = None,
    ) -> CandidateRequirement:
        candidate_file = self.storage.load_candidate_file(flow_id)
        candidate = self._find_candidate(candidate_file.requirements, requirement_id)

        if edited_text is not None:
            candidate.text = edited_text.strip()
        if edited_step_indices is not None:
            candidate.step_indices = sorted(set(int(x) for x in edited_step_indices))
            candidate.scope = _infer_scope(candidate.step_indices)
        if edited_tags is not None:
            candidate.tags = [tag.strip() for tag in edited_tags if isinstance(tag, str) and tag.strip()]
        if annotation_notes is not None:
            candidate.rationale = annotation_notes.strip() or None
        if annotated_by is not None:
            candidate.origin = candidate.origin
        if review_status is not None:
            candidate.review_status = review_status
        if benchmark_decision is not None:
            candidate.benchmark_decision = benchmark_decision
        if ui_evaluability is not None:
            candidate.ui_evaluability = ui_evaluability
        if visible_subtype is not None:
            candidate.visible_subtype = visible_subtype
        if requirement_type is not None:
            candidate.requirement_type = requirement_type
        if verification_label is not None:
            candidate.verification_label = verification_label
        if uncertainty_reasons is not None:
            candidate.uncertainty_reasons = [
                str(reason).strip().upper()
                for reason in uncertainty_reasons
                if str(reason).strip()
            ]
        if claims is not None:
            candidate.claims = [dict(claim) for claim in claims]
        if evidence_steps is not None:
            candidate.evidence_steps = sorted(set(int(index) for index in evidence_steps))
            candidate.step_indices = list(candidate.evidence_steps)
            candidate.scope = _infer_scope(candidate.step_indices)
            allowed_steps = set(candidate.evidence_steps)
            candidate.claims = [
                {
                    **claim,
                    "evidence_steps": [
                        int(step)
                        for step in claim.get("evidence_steps", [])
                        if int(step) in allowed_steps
                    ],
                }
                for claim in candidate.claims
            ]
        if evidence_note is not None:
            candidate.evidence_note = evidence_note.strip() or None
        if rationale is not None:
            candidate.rationale = rationale.strip() or None

        candidate.__post_init__()
        self.storage.save_candidate_file(candidate_file)
        return candidate

    def reject_candidate(self, flow_id: str, requirement_id: str) -> CandidateRequirement:
        candidate_file = self.storage.load_candidate_file(flow_id)
        candidate = self._find_candidate(candidate_file.requirements, requirement_id)
        candidate.review_status = RequirementReviewStatus.REJECTED
        self.storage.save_candidate_file(candidate_file)
        return candidate

    def accept_candidate(
        self,
        flow_id: str,
        requirement_id: str,
        *,
        edited_text: str | None = None,
        edited_step_indices: list[int] | None = None,
        edited_tags: list[str] | None = None,
        annotation_notes: str | None = None,
        annotated_by: str | None = None,
        review_status: str | None = None,
        verification_label: VerificationLabel | None = None,
        ui_evaluability: UiEvaluability | None = None,
        uncertainty_reasons: list[str] | None = None,
        claims: list[dict[str, object]] | None = None,
        evidence_steps: list[int] | None = None,
        evidence_note: str | None = None,
        rationale: str | None = None,
        manual_verification_label: str | None = None,
        manual_verification_notes: str | None = None,
    ) -> GoldRequirement:
        candidate_file = self.storage.load_candidate_file(flow_id)
        candidate = self._find_candidate(candidate_file.requirements, requirement_id)

        if candidate.benchmark_decision == BenchmarkDecision.EXCLUDE_FROM_VERIFICATION_BENCHMARK:
            raise ValueError(f"Candidate {requirement_id} is excluded from the verification benchmark")

        final_text = (edited_text or candidate.text).strip()
        final_step_indices = (
            evidence_steps
            if evidence_steps is not None
            else edited_step_indices
            if edited_step_indices is not None
            else list(candidate.step_indices)
        )
        final_step_indices = sorted(set(int(x) for x in final_step_indices))
        final_tags = edited_tags if edited_tags is not None else list(candidate.tags)
        final_ui_evaluability = ui_evaluability if ui_evaluability is not None else candidate.ui_evaluability

        if candidate.visible_subtype != VisibleSubtype.NONE and not final_step_indices:
            raise ValueError("Gold requirements with visible evidence must keep at least one linked step")

        gold_requirement = GoldRequirement(
            requirement_id=candidate.requirement_id,
            flow_id=candidate.flow_id,
            text=final_text,
            scope=_infer_scope(final_step_indices),
            tags=final_tags,
            step_indices=final_step_indices,
            source_candidate_id=candidate.requirement_id,
            source_harvest_id=candidate.source_harvest_id,
            annotation_notes=annotation_notes,
            annotated_by=annotated_by,
            manual_verification_label=manual_verification_label or "fulfilled",
            manual_verification_notes=manual_verification_notes,
            requirement_type=candidate.requirement_type,
            ui_evaluability=final_ui_evaluability,
            visible_subtype=candidate.visible_subtype,
        )

        gold_file = self.storage.load_gold_file(flow_id)
        if gold_file is None:
            gold_file = GoldRequirementFile(
                dataset=candidate_file.dataset,
                flow_id=flow_id,
                requirements=[],
            )

        self._upsert_gold_requirement(gold_file, gold_requirement)

        verification_gold_file = self.storage.load_verification_gold_file(flow_id)
        if verification_gold_file is None:
            verification_gold_file = VerificationGoldFile(
                dataset=candidate_file.dataset,
                flow_id=flow_id,
                items=[],
            )
        verification_item = self._build_verification_item_from_gold(
            gold_requirement,
            existing_item=self._find_verification_item_or_none(verification_gold_file.items, gold_requirement.requirement_id),
        )
        if verification_label is not None:
            verification_item.verification_label = verification_label
        if ui_evaluability is not None:
            verification_item.ui_evaluability = UIEvaluability(ui_evaluability.value)
        if uncertainty_reasons is not None:
            verification_item.uncertainty_reasons = list(uncertainty_reasons)
        if claims is not None:
            verification_item.claims = [ClaimEvidence.from_dict(claim) for claim in claims]
        if evidence_steps is not None:
            verification_item.evidence_steps = sorted(set(int(index) for index in evidence_steps))
            verification_item.step_indices = list(verification_item.evidence_steps)
            verification_item.scope = _infer_scope(verification_item.step_indices)
        if evidence_note is not None:
            verification_item.evidence_note = evidence_note.strip() or None
        if rationale is not None:
            verification_item.rationale = rationale.strip() or None
        if review_status is not None:
            verification_item.review_status = review_status.strip().lower()
        verification_item.updated_at = _utc_now_iso()
        verification_item.__post_init__()
        validation = validate_verification_gold_item(verification_item)
        if verification_item.review_status == RequirementReviewStatus.ACCEPTED.value and validation.errors:
            messages = "; ".join(issue.message for issue in validation.errors)
            raise ValueError(f"Cannot accept verification item while validation errors remain: {messages}")

        self._upsert_verification_item(verification_gold_file, verification_item)
        self.storage.save_gold_file(gold_file)
        self.storage.save_verification_gold_file(verification_gold_file)

        candidate.review_status = RequirementReviewStatus.ACCEPTED
        self.storage.save_candidate_file(candidate_file)

        return gold_requirement

    def list_gold_requirements(self, flow_id: str) -> list[GoldRequirement]:
        gold_file = self.storage.load_gold_file(flow_id)
        if gold_file is None:
            return []
        return gold_file.requirements

    def list_verification_gold(self, flow_id: str) -> list[VerificationGoldItem]:
        verification_gold_file = self.storage.load_verification_gold_file(flow_id)
        if verification_gold_file is None:
            verification_gold_file = self.build_verification_gold_file(flow_id, include_candidates=True)
        return verification_gold_file.items

    def update_gold_requirement(
        self,
        flow_id: str,
        requirement_id: str,
        *,
        edited_text: str | None = None,
        edited_step_indices: list[int] | None = None,
        edited_tags: list[str] | None = None,
        annotation_notes: str | None = None,
        annotated_by: str | None = None,
        manual_verification_label: str | None = None,
        manual_verification_notes: str | None = None,
    ) -> GoldRequirement:
        gold_file = self.storage.load_gold_file(flow_id)
        if gold_file is None:
            raise FileNotFoundError(f"Gold requirements not found for flow {flow_id}")

        gold_requirement = self._find_gold(gold_file.requirements, requirement_id)

        if edited_text is not None:
            gold_requirement.text = edited_text.strip()
        if edited_step_indices is not None:
            gold_requirement.step_indices = sorted(set(int(x) for x in edited_step_indices))
            gold_requirement.scope = _infer_scope(gold_requirement.step_indices)
        if edited_tags is not None:
            gold_requirement.tags = [tag.strip() for tag in edited_tags if isinstance(tag, str) and tag.strip()]
        if annotation_notes is not None:
            gold_requirement.annotation_notes = annotation_notes.strip() or None
        if annotated_by is not None:
            gold_requirement.annotated_by = annotated_by.strip() or None
        if manual_verification_label is not None or manual_verification_notes is not None:
            gold_requirement.manual_verification_label = manual_verification_label
            gold_requirement.manual_verification_notes = manual_verification_notes.strip() if manual_verification_notes else None

        gold_requirement.__post_init__()
        self.storage.save_gold_file(gold_file)

        verification_gold_file = self.storage.load_verification_gold_file(flow_id)
        if verification_gold_file is not None:
            existing_item = self._find_verification_item_or_none(verification_gold_file.items, requirement_id)
            if existing_item is not None:
                synced_item = self._build_verification_item_from_gold(gold_requirement, existing_item=existing_item)
                self._upsert_verification_item(verification_gold_file, synced_item)
                self.storage.save_verification_gold_file(verification_gold_file)
        return gold_requirement

    def update_verification_gold_item(
        self,
        flow_id: str,
        requirement_id: str,
        *,
        edited_text: str | None = None,
        edited_step_indices: list[int] | None = None,
        edited_tags: list[str] | None = None,
        annotation_notes: str | None = None,
        annotated_by: str | None = None,
        review_status: str | None = None,
        verification_label: VerificationLabel | None = None,
        ui_evaluability: UIEvaluability | None = None,
        uncertainty_reasons: list[str] | None = None,
        claims: list[dict[str, object]] | None = None,
        evidence_steps: list[int] | None = None,
        evidence_note: str | None = None,
        rationale: str | None = None,
    ) -> VerificationGoldItem:
        verification_gold_file = self.storage.load_verification_gold_file(flow_id)
        if verification_gold_file is None:
            verification_gold_file = VerificationGoldFile(dataset="mind2web", flow_id=flow_id, items=[])

        verification_item = self._find_verification_item_or_none(verification_gold_file.items, requirement_id)
        if verification_item is None:
            verification_item = self._build_missing_verification_item(flow_id, requirement_id)

        if edited_text is not None:
            verification_item.text = edited_text.strip()
        if edited_step_indices is not None:
            verification_item.step_indices = sorted(set(int(index) for index in edited_step_indices))
            verification_item.scope = _infer_scope(verification_item.step_indices)
        if edited_tags is not None:
            verification_item.tags = [tag.strip() for tag in edited_tags if isinstance(tag, str) and tag.strip()]
        if annotation_notes is not None:
            verification_item.annotation_notes = annotation_notes.strip() or None
        if annotated_by is not None:
            verification_item.annotated_by = annotated_by.strip() or None
        if review_status is not None:
            verification_item.review_status = review_status.strip().lower()
        if verification_label is not None:
            verification_item.verification_label = verification_label
        if ui_evaluability is not None:
            verification_item.ui_evaluability = ui_evaluability
        if uncertainty_reasons is not None:
            verification_item.uncertainty_reasons = list(uncertainty_reasons)
        if claims is not None:
            verification_item.claims = [ClaimEvidence.from_dict(claim) for claim in claims]
        if evidence_steps is not None:
            verification_item.evidence_steps = sorted(set(int(index) for index in evidence_steps))
            verification_item.step_indices = list(verification_item.evidence_steps)
            verification_item.scope = _infer_scope(verification_item.step_indices)
        self._validate_claim_evidence_step_scope(verification_item)
        if evidence_note is not None:
            verification_item.evidence_note = evidence_note.strip() or None
        if rationale is not None:
            verification_item.rationale = rationale.strip() or None

        verification_item.updated_at = _utc_now_iso()
        verification_item.__post_init__()
        validation = validate_verification_gold_item(verification_item)
        if verification_item.review_status == RequirementReviewStatus.ACCEPTED.value and validation.errors:
            messages = "; ".join(issue.message for issue in validation.errors)
            raise ValueError(f"Cannot accept verification item while validation errors remain: {messages}")

        self._upsert_verification_item(verification_gold_file, verification_item)
        self.storage.save_verification_gold_file(verification_gold_file)
        return verification_item

    def delete_gold_requirement(self, flow_id: str, requirement_id: str) -> GoldRequirement:
        gold_file = self.storage.load_gold_file(flow_id)
        if gold_file is None:
            raise FileNotFoundError(f"Gold requirements not found for flow {flow_id}")

        for idx, gold_requirement in enumerate(gold_file.requirements):
            if gold_requirement.requirement_id == requirement_id:
                del gold_file.requirements[idx]
                self.storage.save_gold_file(gold_file)
                return gold_requirement

        raise KeyError(f"Gold requirement not found: {requirement_id}")

    def delete_verification_gold_item(self, flow_id: str, requirement_id: str) -> tuple[VerificationGoldItem, bool]:
        verification_gold_file = self.storage.load_verification_gold_file(flow_id)
        if verification_gold_file is None:
            verification_gold_file = self.build_verification_gold_file(flow_id, include_candidates=True)

        deleted_item: VerificationGoldItem | None = None
        for idx, item in enumerate(verification_gold_file.items):
            if item.requirement_id == requirement_id:
                deleted_item = item
                del verification_gold_file.items[idx]
                break

        if deleted_item is None:
            raise KeyError(f"Verification gold item not found: {requirement_id}")

        self.storage.save_verification_gold_file(verification_gold_file)

        deleted_gold = False
        gold_file = self.storage.load_gold_file(flow_id)
        if gold_file is not None:
            for idx, gold_requirement in enumerate(gold_file.requirements):
                if gold_requirement.requirement_id == requirement_id:
                    del gold_file.requirements[idx]
                    self.storage.save_gold_file(gold_file)
                    deleted_gold = True
                    break

        try:
            candidate_file = self.storage.load_candidate_file(flow_id)
        except FileNotFoundError:
            candidate_file = None

        if candidate_file is not None:
            for candidate in candidate_file.requirements:
                if candidate.requirement_id == requirement_id:
                    candidate.review_status = RequirementReviewStatus.REJECTED
                    self.storage.save_candidate_file(candidate_file)
                    break

        return deleted_item, deleted_gold

    def build_verification_gold_file(
        self,
        flow_id: str,
        *,
        include_candidates: bool = True,
        existing_file: VerificationGoldFile | None = None,
    ) -> VerificationGoldFile:
        gold_file = self.storage.load_gold_file(flow_id)
        candidate_file = None
        if include_candidates:
            try:
                candidate_file = self.storage.load_candidate_file(flow_id)
            except FileNotFoundError:
                candidate_file = None

        dataset = "mind2web"
        if gold_file is not None:
            dataset = gold_file.dataset
        elif candidate_file is not None:
            dataset = candidate_file.dataset

        verification_gold_file = existing_file or self.storage.load_verification_gold_file(flow_id)
        if verification_gold_file is None:
            verification_gold_file = VerificationGoldFile(dataset=dataset, flow_id=flow_id, items=[])
        else:
            verification_gold_file.dataset = dataset

        existing_by_id = {item.requirement_id: item for item in verification_gold_file.items}
        merged_items: list[VerificationGoldItem] = []

        if gold_file is not None:
            for requirement in gold_file.requirements:
                merged_items.append(
                    self._build_verification_item_from_gold(
                        requirement,
                        existing_item=existing_by_id.get(requirement.requirement_id),
                    )
                )

        if candidate_file is not None:
            existing_gold_ids = {item.requirement_id for item in merged_items}
            for candidate in candidate_file.requirements:
                if candidate.requirement_id in existing_gold_ids:
                    continue
                if candidate.review_status in {RequirementReviewStatus.ACCEPTED, RequirementReviewStatus.REJECTED}:
                    continue
                merged_items.append(
                    self._build_verification_item_from_candidate(
                        candidate,
                        existing_item=existing_by_id.get(candidate.requirement_id),
                    )
                )

        verification_gold_file.items = merged_items
        verification_gold_file.__post_init__()
        return verification_gold_file

    @staticmethod
    def _find_candidate(requirements: list[CandidateRequirement], requirement_id: str) -> CandidateRequirement:
        for req in requirements:
            if req.requirement_id == requirement_id:
                return req
        raise KeyError(f"Candidate requirement not found: {requirement_id}")

    @staticmethod
    def _find_gold(requirements: list[GoldRequirement], requirement_id: str) -> GoldRequirement:
        for req in requirements:
            if req.requirement_id == requirement_id:
                return req
        raise KeyError(f"Gold requirement not found: {requirement_id}")

    @staticmethod
    def _find_verification_item_or_none(
        items: list[VerificationGoldItem],
        requirement_id: str,
    ) -> VerificationGoldItem | None:
        for item in items:
            if item.requirement_id == requirement_id:
                return item
        return None

    @staticmethod
    def _upsert_gold_requirement(gold_file: GoldRequirementFile, gold_requirement: GoldRequirement) -> None:
        for idx, req in enumerate(gold_file.requirements):
            if req.requirement_id == gold_requirement.requirement_id:
                gold_file.requirements[idx] = gold_requirement
                return
        gold_file.requirements.append(gold_requirement)

    @staticmethod
    def _upsert_verification_item(
        verification_gold_file: VerificationGoldFile,
        verification_item: VerificationGoldItem,
    ) -> None:
        for idx, item in enumerate(verification_gold_file.items):
            if item.requirement_id == verification_item.requirement_id:
                verification_gold_file.items[idx] = verification_item
                return
        verification_gold_file.items.append(verification_item)

    def _build_missing_verification_item(self, flow_id: str, requirement_id: str) -> VerificationGoldItem:
        gold_file = self.storage.load_gold_file(flow_id)
        if gold_file is not None:
            gold_requirement = self._find_gold(gold_file.requirements, requirement_id)
            return self._build_verification_item_from_gold(gold_requirement, existing_item=None)

        candidate_file = self.storage.load_candidate_file(flow_id)
        candidate = self._find_candidate(candidate_file.requirements, requirement_id)
        return self._build_verification_item_from_candidate(candidate, existing_item=None)

    def _build_verification_item_from_gold(
        self,
        requirement: GoldRequirement,
        *,
        existing_item: VerificationGoldItem | None,
    ) -> VerificationGoldItem:
        base = existing_item.to_dict() if existing_item is not None else {}
        verification_label = base.get("verification_label") or _map_verification_label(requirement.manual_verification_label)
        intended_label = base.get("intended_label")
        if intended_label is None and requirement.tags:
            intended_label = _extract_intended_label(requirement.tags)

        item = VerificationGoldItem(
            requirement_id=requirement.requirement_id,
            flow_id=requirement.flow_id,
            text=requirement.text,
            scope=requirement.scope,
            tags=list(requirement.tags),
            source_type="requirements_gold",
            source_id=requirement.requirement_id,
            source_candidate_id=requirement.source_candidate_id,
            source_harvest_id=requirement.source_harvest_id,
            step_indices=list(requirement.step_indices),
            requirement_type=requirement.requirement_type.value,
            ui_evaluability=base.get("ui_evaluability") or _map_ui_evaluability(requirement.ui_evaluability),
            visible_subtype=requirement.visible_subtype,
            annotation_notes=requirement.annotation_notes,
            annotated_by=requirement.annotated_by,
            manual_verification_label=requirement.manual_verification_label,
            manual_verification_notes=requirement.manual_verification_notes,
            intended_label=intended_label,
            verification_label=verification_label,
            uncertainty_reasons=base.get("uncertainty_reasons", []),
            notes=base.get("notes", []),
            claims=base.get("claims", []),
            evidence_steps=base.get("evidence_steps") or list(requirement.step_indices),
            evidence_units=base.get("evidence_units", []),
            evidence_note=base.get("evidence_note") or requirement.annotation_notes,
            rationale=base.get("rationale") or requirement.annotation_notes,
            review_status=base.get("review_status", RequirementReviewStatus.NEEDS_REVIEW.value),
            created_at=base.get("created_at", requirement.created_at),
            updated_at=base.get("updated_at"),
        )
        return self._finalize_review_status(item)

    def _build_verification_item_from_candidate(
        self,
        candidate: CandidateRequirement,
        *,
        existing_item: VerificationGoldItem | None,
    ) -> VerificationGoldItem:
        base = existing_item.to_dict() if existing_item is not None else {}
        candidate_claims = [
            {
                "claim": claim.get("claim") or claim.get("claim_text"),
                "status": claim.get("status"),
                "claim_type": claim.get("claim_type", "OBSERVABLE"),
                "importance": claim.get("importance", "CORE"),
                "evidence_steps": claim.get("evidence_steps", []),
                "note": claim.get("note"),
            }
            for claim in candidate.claims
            if (claim.get("claim") or claim.get("claim_text")) and claim.get("status")
        ]
        item = VerificationGoldItem(
            requirement_id=candidate.requirement_id,
            flow_id=candidate.flow_id,
            text=candidate.text,
            scope=candidate.scope,
            tags=list(candidate.tags),
            source_type="requirements_candidate",
            source_id=candidate.requirement_id,
            source_candidate_id=candidate.requirement_id,
            source_harvest_id=candidate.source_harvest_id,
            step_indices=list(candidate.step_indices),
            requirement_type=candidate.requirement_type.value,
            ui_evaluability=base.get("ui_evaluability") or _map_ui_evaluability(candidate.ui_evaluability),
            visible_subtype=candidate.visible_subtype,
            annotation_notes=base.get("annotation_notes"),
            annotated_by=base.get("annotated_by"),
            manual_verification_label=base.get("manual_verification_label"),
            manual_verification_notes=base.get("manual_verification_notes"),
            intended_label=base.get("intended_label") or _extract_intended_label(candidate.tags),
            verification_label=base.get("verification_label") or candidate.verification_label,
            uncertainty_reasons=base.get("uncertainty_reasons") or candidate.uncertainty_reasons,
            notes=base.get("notes", []),
            claims=base.get("claims") or candidate_claims,
            evidence_steps=base.get("evidence_steps") or candidate.evidence_steps,
            evidence_units=base.get("evidence_units", []),
            evidence_note=base.get("evidence_note") or candidate.evidence_note,
            rationale=base.get("rationale") or candidate.rationale,
            review_status=base.get("review_status", RequirementReviewStatus.NEEDS_REVIEW.value),
            created_at=base.get("created_at", candidate.created_at),
            updated_at=base.get("updated_at"),
        )
        return self._finalize_review_status(item)

    @staticmethod
    def _finalize_review_status(item: VerificationGoldItem) -> VerificationGoldItem:
        validation = validate_verification_gold_item(item)
        if validation.errors or item.verification_label is None or item.ui_evaluability is None:
            item.review_status = RequirementReviewStatus.NEEDS_REVIEW.value
        return item

    @staticmethod
    def _validate_claim_evidence_step_scope(item: VerificationGoldItem) -> None:
        allowed_steps = set(item.evidence_steps)
        invalid_references: list[str] = []
        for claim_index, claim in enumerate(item.claims, start=1):
            invalid_steps = [step for step in claim.evidence_steps if step not in allowed_steps]
            if invalid_steps:
                invalid_references.append(f"claim {claim_index}: {invalid_steps}")

        if invalid_references:
            details = "; ".join(invalid_references)
            raise ValueError(
                "Claim evidence_steps must be a subset of item evidence_steps. "
                f"Invalid references: {details}"
            )
