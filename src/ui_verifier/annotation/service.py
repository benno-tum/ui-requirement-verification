from __future__ import annotations

from ui_verifier.annotation.storage import AnnotationStorage
from ui_verifier.requirements.schemas import (
    CandidateRequirement,
    GoldRequirement,
    GoldRequirementFile,
    RequirementReviewStatus,
    RequirementScope,
)


def _infer_scope(step_indices: list[int]) -> RequirementScope:
    if len(step_indices) <= 1:
        return RequirementScope.SINGLE_SCREEN
    return RequirementScope.MULTI_SCREEN


class AnnotationService:
    def __init__(self, storage: AnnotationStorage | None = None) -> None:
        self.storage = storage or AnnotationStorage()

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
    ) -> GoldRequirement:
        candidate_file = self.storage.load_candidate_file(flow_id)
        candidate = self._find_candidate(candidate_file.requirements, requirement_id)

        final_text = (edited_text or candidate.text).strip()
        final_step_indices = edited_step_indices if edited_step_indices is not None else list(candidate.step_indices)
        final_step_indices = sorted(set(int(x) for x in final_step_indices))
        final_tags = edited_tags if edited_tags is not None else list(candidate.tags)

        gold_requirement = GoldRequirement(
            requirement_id=candidate.requirement_id,
            flow_id=candidate.flow_id,
            text=final_text,
            scope=_infer_scope(final_step_indices),
            tags=final_tags,
            step_indices=final_step_indices,
            source_candidate_id=candidate.requirement_id,
            annotation_notes=annotation_notes,
            annotated_by=annotated_by,
        )

        gold_file = self.storage.load_gold_file(flow_id)
        if gold_file is None:
            gold_file = GoldRequirementFile(
                dataset=candidate_file.dataset,
                flow_id=flow_id,
                requirements=[],
            )

        self._upsert_gold_requirement(gold_file, gold_requirement)
        self.storage.save_gold_file(gold_file)

        candidate.review_status = RequirementReviewStatus.ACCEPTED
        self.storage.save_candidate_file(candidate_file)

        return gold_requirement

    def list_gold_requirements(self, flow_id: str) -> list[GoldRequirement]:
        gold_file = self.storage.load_gold_file(flow_id)
        if gold_file is None:
            return []
        return gold_file.requirements

    @staticmethod
    def _find_candidate(requirements: list[CandidateRequirement], requirement_id: str) -> CandidateRequirement:
        for req in requirements:
            if req.requirement_id == requirement_id:
                return req
        raise KeyError(f"Candidate requirement not found: {requirement_id}")

    @staticmethod
    def _upsert_gold_requirement(gold_file: GoldRequirementFile, gold_requirement: GoldRequirement) -> None:
        for idx, req in enumerate(gold_file.requirements):
            if req.requirement_id == gold_requirement.requirement_id:
                gold_file.requirements[idx] = gold_requirement
                return
        gold_file.requirements.append(gold_requirement)
