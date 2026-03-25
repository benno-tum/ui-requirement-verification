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


def _drop_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


class VerdictLabel(str, Enum):
    FULFILLED = "fulfilled"
    PARTIALLY_FULFILLED = "partially_fulfilled"
    NOT_FULFILLED = "not_fulfilled"
    ABSTAIN = "abstain"


class EvidenceType(str, Enum):
    SCREEN = "screen"
    REGION = "region"
    TEXT = "text"
    METADATA = "metadata"


@dataclass(slots=True)
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        for name in ("x1", "y1", "x2", "y2"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be numeric")
            setattr(self, name, float(value))

        if self.x2 <= self.x1:
            raise ValueError("x2 must be greater than x1")
        if self.y2 <= self.y1:
            raise ValueError("y2 must be greater than y1")

    def to_dict(self) -> dict[str, float]:
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BoundingBox":
        return cls(
            x1=data["x1"],
            y1=data["y1"],
            x2=data["x2"],
            y2=data["y2"],
        )


@dataclass(slots=True)
class EvidenceRef:
    step_index: int
    evidence_type: EvidenceType = EvidenceType.SCREEN
    bbox: BoundingBox | None = None
    matched_text: str | None = None
    ui_element_id: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.step_index, int):
            raise TypeError("step_index must be an int")
        if self.step_index < 0:
            raise ValueError("step_index must be >= 0")

        if self.matched_text is not None:
            self.matched_text = self.matched_text.strip() or None

        if self.ui_element_id is not None:
            self.ui_element_id = self.ui_element_id.strip() or None

        if self.reason is not None:
            self.reason = self.reason.strip() or None

        if self.evidence_type == EvidenceType.REGION and self.bbox is None:
            raise ValueError("bbox is required when evidence_type='region'")

    def to_dict(self) -> dict[str, Any]:
        return _drop_none(
            {
                "step_index": self.step_index,
                "evidence_type": self.evidence_type.value,
                "bbox": self.bbox.to_dict() if self.bbox else None,
                "matched_text": self.matched_text,
                "ui_element_id": self.ui_element_id,
                "reason": self.reason,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceRef":
        bbox_data = data.get("bbox")
        return cls(
            step_index=data["step_index"],
            evidence_type=EvidenceType(data.get("evidence_type", EvidenceType.SCREEN.value)),
            bbox=BoundingBox.from_dict(bbox_data) if bbox_data else None,
            matched_text=data.get("matched_text"),
            ui_element_id=data.get("ui_element_id"),
            reason=data.get("reason"),
        )


@dataclass(slots=True)
class RequirementVerdict:
    requirement_id: str
    label: VerdictLabel
    evidence: list[EvidenceRef] = field(default_factory=list)
    confidence: float | None = None
    explanation: str | None = None

    def __post_init__(self) -> None:
        self.requirement_id = _require_non_empty(self.requirement_id, "requirement_id")

        if self.confidence is not None:
            if not isinstance(self.confidence, (int, float)):
                raise TypeError("confidence must be a float in [0, 1]")
            self.confidence = float(self.confidence)
            if not (0.0 <= self.confidence <= 1.0):
                raise ValueError("confidence must be in [0, 1]")

        if self.explanation is not None:
            self.explanation = self.explanation.strip() or None

        if self.label == VerdictLabel.FULFILLED and not self.evidence:
            raise ValueError("fulfilled verdicts must include at least one evidence item")

        if self.label == VerdictLabel.PARTIALLY_FULFILLED and not self.evidence:
            raise ValueError("partially_fulfilled verdicts should include at least one evidence item")

    def to_dict(self) -> dict[str, Any]:
        return _drop_none(
            {
                "requirement_id": self.requirement_id,
                "label": self.label.value,
                "evidence": [e.to_dict() for e in self.evidence],
                "confidence": self.confidence,
                "explanation": self.explanation,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RequirementVerdict":
        return cls(
            requirement_id=data["requirement_id"],
            label=VerdictLabel(data["label"]),
            evidence=[EvidenceRef.from_dict(x) for x in data.get("evidence", [])],
            confidence=data.get("confidence"),
            explanation=data.get("explanation"),
        )


@dataclass(slots=True)
class VerificationRun:
    dataset: str
    flow_id: str
    verifier_name: str
    created_at: str = field(default_factory=_utc_now_iso)
    verdicts: list[RequirementVerdict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.dataset = _require_non_empty(self.dataset, "dataset")
        self.flow_id = _require_non_empty(self.flow_id, "flow_id")
        self.verifier_name = _require_non_empty(self.verifier_name, "verifier_name")
        self.created_at = _require_non_empty(self.created_at, "created_at")

        seen: set[str] = set()
        for verdict in self.verdicts:
            if verdict.requirement_id in seen:
                raise ValueError(f"duplicate requirement_id in verdicts: {verdict.requirement_id}")
            seen.add(verdict.requirement_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "flow_id": self.flow_id,
            "verifier_name": self.verifier_name,
            "created_at": self.created_at,
            "verdicts": [v.to_dict() for v in self.verdicts],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerificationRun":
        return cls(
            dataset=data["dataset"],
            flow_id=data["flow_id"],
            verifier_name=data["verifier_name"],
            created_at=data.get("created_at", _utc_now_iso()),
            verdicts=[RequirementVerdict.from_dict(x) for x in data.get("verdicts", [])],
        )

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "VerificationRun":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)
