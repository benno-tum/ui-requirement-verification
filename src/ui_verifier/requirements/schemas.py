from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
from typing import Any


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
class CandidateRequirement(RequirementBase):
    origin: RequirementOrigin = RequirementOrigin.MODEL
    review_status: RequirementReviewStatus = RequirementReviewStatus.CANDIDATE
    step_indices: list[int] = field(default_factory=list)
    rationale: str | None = None
    generation_model: str | None = None
    generation_prompt_path: str | None = None
    confidence: float | None = None
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        RequirementBase.__post_init__(self)
        self.step_indices = _validate_step_indices(self.step_indices)

        if self.rationale is not None:
            self.rationale = self.rationale.strip() or None

        if self.generation_model is not None:
            self.generation_model = self.generation_model.strip() or None

        if self.generation_prompt_path is not None:
            self.generation_prompt_path = self.generation_prompt_path.strip() or None

        if self.confidence is not None:
            if not isinstance(self.confidence, (int, float)):
                raise TypeError("confidence must be a float in [0, 1]")
            self.confidence = float(self.confidence)
            if not (0.0 <= self.confidence <= 1.0):
                raise ValueError("confidence must be in [0, 1]")

        self.created_at = _require_non_empty(self.created_at, "created_at")

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
                "confidence": self.confidence,
                "created_at": self.created_at,
            }
        )
        return {**base, **extra}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CandidateRequirement":
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
            confidence=data.get("confidence"),
            created_at=data.get("created_at", _utc_now_iso()),
        )


@dataclass(slots=True)
class GoldRequirement(RequirementBase):
    origin: RequirementOrigin = RequirementOrigin.HUMAN
    review_status: RequirementReviewStatus = RequirementReviewStatus.ACCEPTED
    step_indices: list[int] = field(default_factory=list)
    source_candidate_id: str | None = None
    annotation_notes: str | None = None
    annotated_by: str | None = None
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        RequirementBase.__post_init__(self)
        self.step_indices = _validate_step_indices(self.step_indices)

        if self.source_candidate_id is not None:
            self.source_candidate_id = self.source_candidate_id.strip() or None

        if self.annotation_notes is not None:
            self.annotation_notes = self.annotation_notes.strip() or None

        if self.annotated_by is not None:
            self.annotated_by = self.annotated_by.strip() or None

        self.created_at = _require_non_empty(self.created_at, "created_at")

    def to_dict(self) -> dict[str, Any]:
        base = RequirementBase.to_dict(self)
        extra = _drop_none(
            {
                "origin": self.origin.value,
                "review_status": self.review_status.value,
                "step_indices": self.step_indices,
                "source_candidate_id": self.source_candidate_id,
                "annotation_notes": self.annotation_notes,
                "annotated_by": self.annotated_by,
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
            annotation_notes=data.get("annotation_notes"),
            annotated_by=data.get("annotated_by"),
            created_at=data.get("created_at", _utc_now_iso()),
        )


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
