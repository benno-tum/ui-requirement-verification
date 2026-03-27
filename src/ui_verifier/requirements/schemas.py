from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
from typing import Any

from ui_verifier.requirement_inspection.schemas import (
    AnnotationConfidence,
    NonEvaluableReason,
    RequirementInspectionType,
    UiEvaluability,
    VisibleSubtype,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _validate_step_indices(step_indices: list[int]) -> list[int]:
    if not isinstance(step_indices, list):
        raise TypeError("step_indices must be a list[int]")
    if any(not isinstance(i, int) for i in step_indices):
        raise TypeError("step_indices must contain only integers")
    if any(i < 0 for i in step_indices):
        raise ValueError("step_indices must be >= 0")
    return sorted(set(step_indices))


def _drop_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("optional text fields must be strings or None")
    value = value.strip()
    return value or None


def _validate_manual_verification_label(value: str | None) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError("manual_verification_label must be a string or None")

    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    allowed = {"fulfilled", "partially_fulfilled", "not_fulfilled", "abstain"}
    if normalized not in allowed:
        raise ValueError(
            "manual_verification_label must be one of: fulfilled, partially_fulfilled, not_fulfilled, abstain"
        )
    return normalized


class RequirementScope(str, Enum):
    SINGLE_SCREEN = "single_screen"
    MULTI_SCREEN = "multi_screen"
    LAYOUT = "layout"


class RequirementOrigin(str, Enum):
    MODEL = "model"
    HUMAN = "human"


class RequirementReviewStatus(str, Enum):
    CANDIDATE = "candidate"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class BenchmarkDecision(str, Enum):
    DIRECT_INCLUDE = "DIRECT_INCLUDE"
    REWRITE_TO_VISIBLE_CORE = "REWRITE_TO_VISIBLE_CORE"
    EXCLUDE_FROM_VERIFICATION_BENCHMARK = "EXCLUDE_FROM_VERIFICATION_BENCHMARK"


class CandidateOrigin(str, Enum):
    DIRECT_FROM_HARVEST = "DIRECT_FROM_HARVEST"
    VISIBLE_CORE_REWRITE = "VISIBLE_CORE_REWRITE"


class TaskRelevance(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(slots=True)
class RequirementBase:
    requirement_id: str
    flow_id: str
    text: str
    scope: RequirementScope = RequirementScope.SINGLE_SCREEN
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.requirement_id = _require_non_empty(self.requirement_id, "requirement_id")
        self.flow_id = _require_non_empty(self.flow_id, "flow_id")
        self.text = _require_non_empty(self.text, "text")
        self.tags = [t.strip() for t in self.tags if isinstance(t, str) and t.strip()]

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "flow_id": self.flow_id,
            "text": self.text,
            "scope": self.scope.value,
            "tags": self.tags,
        }


@dataclass(slots=True)
class HarvestedRequirement:
    harvest_id: str
    flow_id: str
    harvested_text: str
    requirement_type: RequirementInspectionType = RequirementInspectionType.UNCLEAR
    ui_evaluability: UiEvaluability = UiEvaluability.NOT_UI_VERIFIABLE
    non_evaluable_reason: NonEvaluableReason = NonEvaluableReason.NONE
    visible_subtype: VisibleSubtype = VisibleSubtype.NONE
    task_relevance: TaskRelevance = TaskRelevance.MEDIUM
    step_indices: list[int] = field(default_factory=list)
    rationale: str | None = None
    visible_core_candidate: str | None = None
    generation_model: str | None = None
    generation_prompt_path: str | None = None
    confidence: AnnotationConfidence = AnnotationConfidence.MEDIUM
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        self.harvest_id = _require_non_empty(self.harvest_id, "harvest_id")
        self.flow_id = _require_non_empty(self.flow_id, "flow_id")
        self.harvested_text = _require_non_empty(self.harvested_text, "harvested_text")
        self.step_indices = _validate_step_indices(self.step_indices)
        self.rationale = _normalize_optional_text(self.rationale)
        self.visible_core_candidate = _normalize_optional_text(self.visible_core_candidate)
        self.generation_model = _normalize_optional_text(self.generation_model)
        self.generation_prompt_path = _normalize_optional_text(self.generation_prompt_path)
        self.created_at = _require_non_empty(self.created_at, "created_at")

        if self.ui_evaluability == UiEvaluability.NOT_UI_VERIFIABLE:
            if self.visible_subtype != VisibleSubtype.NONE:
                raise ValueError("visible_subtype must be NONE for NOT_UI_VERIFIABLE harvested requirements")
            if self.non_evaluable_reason == NonEvaluableReason.NONE:
                raise ValueError("non_evaluable_reason must not be NONE for NOT_UI_VERIFIABLE harvested requirements")
        else:
            if self.visible_subtype == VisibleSubtype.NONE:
                raise ValueError(
                    "visible_subtype must be set for UI_VERIFIABLE or PARTIALLY_UI_VERIFIABLE harvested requirements"
                )
            if self.ui_evaluability == UiEvaluability.UI_VERIFIABLE and self.non_evaluable_reason != NonEvaluableReason.NONE:
                raise ValueError("non_evaluable_reason must be NONE for UI_VERIFIABLE harvested requirements")

    def to_dict(self) -> dict[str, Any]:
        return {
            "harvest_id": self.harvest_id,
            "flow_id": self.flow_id,
            "harvested_text": self.harvested_text,
            "requirement_type": self.requirement_type.value,
            "ui_evaluability": self.ui_evaluability.value,
            "non_evaluable_reason": self.non_evaluable_reason.value,
            "visible_subtype": self.visible_subtype.value,
            "task_relevance": self.task_relevance.value,
            "step_indices": self.step_indices,
            "rationale": self.rationale,
            "visible_core_candidate": self.visible_core_candidate,
            "generation_model": self.generation_model,
            "generation_prompt_path": self.generation_prompt_path,
            "confidence": self.confidence.value,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HarvestedRequirement":
        return cls(
            harvest_id=data["harvest_id"],
            flow_id=data["flow_id"],
            harvested_text=data["harvested_text"],
            requirement_type=RequirementInspectionType(
                data.get("requirement_type", RequirementInspectionType.UNCLEAR.value)
            ),
            ui_evaluability=UiEvaluability(
                data.get("ui_evaluability", UiEvaluability.NOT_UI_VERIFIABLE.value)
            ),
            non_evaluable_reason=NonEvaluableReason(
                data.get("non_evaluable_reason", NonEvaluableReason.NONE.value)
            ),
            visible_subtype=VisibleSubtype(
                data.get("visible_subtype", VisibleSubtype.NONE.value)
            ),
            task_relevance=TaskRelevance(data.get("task_relevance", TaskRelevance.MEDIUM.value)),
            step_indices=list(data.get("step_indices", [])),
            rationale=data.get("rationale"),
            visible_core_candidate=data.get("visible_core_candidate"),
            generation_model=data.get("generation_model"),
            generation_prompt_path=data.get("generation_prompt_path"),
            confidence=AnnotationConfidence(data.get("confidence", AnnotationConfidence.MEDIUM.value)),
            created_at=data.get("created_at", _utc_now_iso()),
        )


@dataclass(slots=True)
class CandidateRequirement(RequirementBase):
    origin: RequirementOrigin = RequirementOrigin.MODEL
    review_status: RequirementReviewStatus = RequirementReviewStatus.CANDIDATE
    step_indices: list[int] = field(default_factory=list)
    rationale: str | None = None
    generation_model: str | None = None
    generation_prompt_path: str | None = None
    confidence: AnnotationConfidence | None = None
    created_at: str = field(default_factory=_utc_now_iso)
    source_harvest_id: str | None = None
    candidate_origin: CandidateOrigin = CandidateOrigin.DIRECT_FROM_HARVEST
    benchmark_decision: BenchmarkDecision = BenchmarkDecision.DIRECT_INCLUDE
    parent_harvest_text: str | None = None
    requirement_type: RequirementInspectionType = RequirementInspectionType.UNCLEAR
    ui_evaluability: UiEvaluability = UiEvaluability.NOT_UI_VERIFIABLE
    non_evaluable_reason: NonEvaluableReason = NonEvaluableReason.NONE
    visible_subtype: VisibleSubtype = VisibleSubtype.NONE
    task_relevance: TaskRelevance = TaskRelevance.MEDIUM
    excluded_reason: NonEvaluableReason | None = None

    def __post_init__(self) -> None:
        RequirementBase.__post_init__(self)
        self.step_indices = _validate_step_indices(self.step_indices)
        self.rationale = _normalize_optional_text(self.rationale)
        self.generation_model = _normalize_optional_text(self.generation_model)
        self.generation_prompt_path = _normalize_optional_text(self.generation_prompt_path)
        self.source_harvest_id = _normalize_optional_text(self.source_harvest_id)
        self.parent_harvest_text = _normalize_optional_text(self.parent_harvest_text)
        self.created_at = _require_non_empty(self.created_at, "created_at")

        if self.confidence is not None and not isinstance(self.confidence, AnnotationConfidence):
            self.confidence = AnnotationConfidence(str(self.confidence).upper())

        if self.benchmark_decision == BenchmarkDecision.EXCLUDE_FROM_VERIFICATION_BENCHMARK:
            if self.excluded_reason is None:
                raise ValueError("excluded_reason must be set for excluded verification candidates")

    def to_dict(self) -> dict[str, Any]:
        base = RequirementBase.to_dict(self)
        extra = _drop_none(
            {
                "origin": self.origin.value,
                "review_status": self.review_status.value,
                "step_indices": self.step_indices,
                "rationale": self.rationale,
                "generation_model": self.generation_model,
                "generation_prompt_path": self.generation_prompt_path,
                "confidence": self.confidence.value if self.confidence else None,
                "created_at": self.created_at,
                "source_harvest_id": self.source_harvest_id,
                "candidate_origin": self.candidate_origin.value,
                "benchmark_decision": self.benchmark_decision.value,
                "parent_harvest_text": self.parent_harvest_text,
                "requirement_type": self.requirement_type.value,
                "ui_evaluability": self.ui_evaluability.value,
                "non_evaluable_reason": self.non_evaluable_reason.value,
                "visible_subtype": self.visible_subtype.value,
                "task_relevance": self.task_relevance.value,
                "excluded_reason": self.excluded_reason.value if self.excluded_reason else None,
            }
        )
        return {**base, **extra}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CandidateRequirement":
        confidence_value = data.get("confidence")
        return cls(
            requirement_id=data["requirement_id"],
            flow_id=data["flow_id"],
            text=data["text"],
            scope=RequirementScope(data.get("scope", RequirementScope.SINGLE_SCREEN.value)),
            tags=list(data.get("tags", [])),
            origin=RequirementOrigin(data.get("origin", RequirementOrigin.MODEL.value)),
            review_status=RequirementReviewStatus(
                data.get("review_status", RequirementReviewStatus.CANDIDATE.value)
            ),
            step_indices=list(data.get("step_indices", [])),
            rationale=data.get("rationale"),
            generation_model=data.get("generation_model"),
            generation_prompt_path=data.get("generation_prompt_path"),
            confidence=AnnotationConfidence(confidence_value) if confidence_value else None,
            created_at=data.get("created_at", _utc_now_iso()),
            source_harvest_id=data.get("source_harvest_id"),
            candidate_origin=CandidateOrigin(
                data.get("candidate_origin", CandidateOrigin.DIRECT_FROM_HARVEST.value)
            ),
            benchmark_decision=BenchmarkDecision(
                data.get("benchmark_decision", BenchmarkDecision.DIRECT_INCLUDE.value)
            ),
            parent_harvest_text=data.get("parent_harvest_text"),
            requirement_type=RequirementInspectionType(
                data.get("requirement_type", RequirementInspectionType.UNCLEAR.value)
            ),
            ui_evaluability=UiEvaluability(
                data.get("ui_evaluability", UiEvaluability.NOT_UI_VERIFIABLE.value)
            ),
            non_evaluable_reason=NonEvaluableReason(
                data.get("non_evaluable_reason", NonEvaluableReason.NONE.value)
            ),
            visible_subtype=VisibleSubtype(
                data.get("visible_subtype", VisibleSubtype.NONE.value)
            ),
            task_relevance=TaskRelevance(data.get("task_relevance", TaskRelevance.MEDIUM.value)),
            excluded_reason=NonEvaluableReason(data["excluded_reason"]) if data.get("excluded_reason") else None,
        )


@dataclass(slots=True)
class GoldRequirement(RequirementBase):
    origin: RequirementOrigin = RequirementOrigin.HUMAN
    review_status: RequirementReviewStatus = RequirementReviewStatus.ACCEPTED
    step_indices: list[int] = field(default_factory=list)
    source_candidate_id: str | None = None
    source_harvest_id: str | None = None
    annotation_notes: str | None = None
    annotated_by: str | None = None
    manual_verification_label: str | None = None
    manual_verification_notes: str | None = None
    requirement_type: RequirementInspectionType = RequirementInspectionType.UNCLEAR
    ui_evaluability: UiEvaluability = UiEvaluability.NOT_UI_VERIFIABLE
    visible_subtype: VisibleSubtype = VisibleSubtype.NONE
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        RequirementBase.__post_init__(self)
        self.step_indices = _validate_step_indices(self.step_indices)
        self.source_candidate_id = _normalize_optional_text(self.source_candidate_id)
        self.source_harvest_id = _normalize_optional_text(self.source_harvest_id)
        self.annotation_notes = _normalize_optional_text(self.annotation_notes)
        self.annotated_by = _normalize_optional_text(self.annotated_by)
        self.manual_verification_label = _validate_manual_verification_label(self.manual_verification_label)
        self.manual_verification_notes = _normalize_optional_text(self.manual_verification_notes)
        self.created_at = _require_non_empty(self.created_at, "created_at")

    def to_dict(self) -> dict[str, Any]:
        base = RequirementBase.to_dict(self)
        extra = _drop_none(
            {
                "origin": self.origin.value,
                "review_status": self.review_status.value,
                "step_indices": self.step_indices,
                "source_candidate_id": self.source_candidate_id,
                "source_harvest_id": self.source_harvest_id,
                "annotation_notes": self.annotation_notes,
                "annotated_by": self.annotated_by,
                "manual_verification_label": self.manual_verification_label,
                "manual_verification_notes": self.manual_verification_notes,
                "requirement_type": self.requirement_type.value,
                "ui_evaluability": self.ui_evaluability.value,
                "visible_subtype": self.visible_subtype.value,
                "created_at": self.created_at,
            }
        )
        return {**base, **extra}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoldRequirement":
        return cls(
            requirement_id=data["requirement_id"],
            flow_id=data["flow_id"],
            text=data["text"],
            scope=RequirementScope(data.get("scope", RequirementScope.SINGLE_SCREEN.value)),
            tags=list(data.get("tags", [])),
            origin=RequirementOrigin(data.get("origin", RequirementOrigin.HUMAN.value)),
            review_status=RequirementReviewStatus(
                data.get("review_status", RequirementReviewStatus.ACCEPTED.value)
            ),
            step_indices=list(data.get("step_indices", [])),
            source_candidate_id=data.get("source_candidate_id"),
            source_harvest_id=data.get("source_harvest_id"),
            annotation_notes=data.get("annotation_notes"),
            annotated_by=data.get("annotated_by"),
            manual_verification_label=data.get("manual_verification_label"),
            manual_verification_notes=data.get("manual_verification_notes"),
            requirement_type=RequirementInspectionType(
                data.get("requirement_type", RequirementInspectionType.UNCLEAR.value)
            ),
            ui_evaluability=UiEvaluability(
                data.get("ui_evaluability", UiEvaluability.NOT_UI_VERIFIABLE.value)
            ),
            visible_subtype=VisibleSubtype(
                data.get("visible_subtype", VisibleSubtype.NONE.value)
            ),
            created_at=data.get("created_at", _utc_now_iso()),
        )


@dataclass(slots=True)
class HarvestedRequirementFile:
    dataset: str
    flow_id: str
    requirements: list[HarvestedRequirement]

    def __post_init__(self) -> None:
        self.dataset = _require_non_empty(self.dataset, "dataset")
        self.flow_id = _require_non_empty(self.flow_id, "flow_id")

        for req in self.requirements:
            if req.flow_id != self.flow_id:
                raise ValueError(
                    f"Harvested requirement flow_id mismatch: {req.harvest_id} has flow_id={req.flow_id}, expected {self.flow_id}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "flow_id": self.flow_id,
            "requirements": [r.to_dict() for r in self.requirements],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HarvestedRequirementFile":
        return cls(
            dataset=data["dataset"],
            flow_id=data["flow_id"],
            requirements=[HarvestedRequirement.from_dict(x) for x in data.get("requirements", [])],
        )

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "HarvestedRequirementFile":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)


@dataclass(slots=True)
class CandidateRequirementFile:
    dataset: str
    flow_id: str
    requirements: list[CandidateRequirement]

    def __post_init__(self) -> None:
        self.dataset = _require_non_empty(self.dataset, "dataset")
        self.flow_id = _require_non_empty(self.flow_id, "flow_id")

        for req in self.requirements:
            if req.flow_id != self.flow_id:
                raise ValueError(
                    f"Candidate requirement flow_id mismatch: {req.requirement_id} has flow_id={req.flow_id}, "
                    f"expected {self.flow_id}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "flow_id": self.flow_id,
            "requirements": [r.to_dict() for r in self.requirements],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CandidateRequirementFile":
        return cls(
            dataset=data["dataset"],
            flow_id=data["flow_id"],
            requirements=[CandidateRequirement.from_dict(x) for x in data.get("requirements", [])],
        )

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "CandidateRequirementFile":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)


@dataclass(slots=True)
class GoldRequirementFile:
    dataset: str
    flow_id: str
    requirements: list[GoldRequirement]

    def __post_init__(self) -> None:
        self.dataset = _require_non_empty(self.dataset, "dataset")
        self.flow_id = _require_non_empty(self.flow_id, "flow_id")

        for req in self.requirements:
            if req.flow_id != self.flow_id:
                raise ValueError(
                    f"Gold requirement flow_id mismatch: {req.requirement_id} has flow_id={req.flow_id}, "
                    f"expected {self.flow_id}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "flow_id": self.flow_id,
            "requirements": [r.to_dict() for r in self.requirements],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoldRequirementFile":
        return cls(
            dataset=data["dataset"],
            flow_id=data["flow_id"],
            requirements=[GoldRequirement.from_dict(x) for x in data.get("requirements", [])],
        )

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "GoldRequirementFile":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)
