from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RequirementInspectionType(str, Enum):
    FR = "FR"
    NFR = "NFR"
    UNCLEAR = "UNCLEAR"


class UiEvaluability(str, Enum):
    UI_VERIFIABLE = "UI_VERIFIABLE"
    PARTIALLY_UI_VERIFIABLE = "PARTIALLY_UI_VERIFIABLE"
    NOT_UI_VERIFIABLE = "NOT_UI_VERIFIABLE"


class NonEvaluableReason(str, Enum):
    NONE = "NONE"
    BACKEND_HIDDEN_STATE = "BACKEND_HIDDEN_STATE"
    PERFORMANCE_TIMING = "PERFORMANCE_TIMING"
    SECURITY_PRIVACY = "SECURITY_PRIVACY"
    EXTERNAL_INTEGRATION = "EXTERNAL_INTEGRATION"
    TOO_ABSTRACT = "TOO_ABSTRACT"
    BUSINESS_RULE_NOT_VISIBLE = "BUSINESS_RULE_NOT_VISIBLE"
    DATA_CORRECTNESS_NOT_VISIBLE = "DATA_CORRECTNESS_NOT_VISIBLE"


class VisibleSubtype(str, Enum):
    NONE = "NONE"
    TEXT_OR_ELEMENT_PRESENCE = "TEXT_OR_ELEMENT_PRESENCE"
    NAVIGATION_OUTCOME = "NAVIGATION_OUTCOME"
    STATE_CHANGE_ACROSS_SCREENS = "STATE_CHANGE_ACROSS_SCREENS"
    VALIDATION_OR_FEEDBACK = "VALIDATION_OR_FEEDBACK"
    CONTENT_UPDATE = "CONTENT_UPDATE"
    LAYOUT_POSITION = "LAYOUT_POSITION"


class AnnotationConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("optional text fields must be strings or None")
    value = value.strip()
    return value or None


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


@dataclass(slots=True)
class RequirementInspectionRecord:
    doc_id: str
    req_id: str
    requirement_text: str
    requirement_type: RequirementInspectionType = RequirementInspectionType.UNCLEAR
    ui_evaluability: UiEvaluability = UiEvaluability.NOT_UI_VERIFIABLE
    non_evaluable_reason: NonEvaluableReason = NonEvaluableReason.NONE
    visible_subtype: VisibleSubtype = VisibleSubtype.NONE
    confidence: AnnotationConfidence = AnnotationConfidence.MEDIUM
    notes: str | None = None

    def __post_init__(self) -> None:
        self.doc_id = _require_non_empty(self.doc_id, "doc_id")
        self.req_id = _require_non_empty(self.req_id, "req_id")
        self.requirement_text = _require_non_empty(self.requirement_text, "requirement_text")
        self.notes = _normalize_optional_text(self.notes)

        if self.ui_evaluability == UiEvaluability.NOT_UI_VERIFIABLE:
            if self.visible_subtype != VisibleSubtype.NONE:
                raise ValueError("visible_subtype must be NONE when ui_evaluability is NOT_UI_VERIFIABLE")
            if self.non_evaluable_reason == NonEvaluableReason.NONE:
                raise ValueError(
                    "non_evaluable_reason must not be NONE when ui_evaluability is NOT_UI_VERIFIABLE"
                )
        else:
            if self.non_evaluable_reason != NonEvaluableReason.NONE:
                raise ValueError(
                    "non_evaluable_reason must be NONE unless ui_evaluability is NOT_UI_VERIFIABLE"
                )
            if self.visible_subtype == VisibleSubtype.NONE:
                raise ValueError(
                    "visible_subtype must not be NONE when ui_evaluability is UI_VERIFIABLE or PARTIALLY_UI_VERIFIABLE"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "req_id": self.req_id,
            "requirement_text": self.requirement_text,
            "requirement_type": self.requirement_type.value,
            "ui_evaluability": self.ui_evaluability.value,
            "non_evaluable_reason": self.non_evaluable_reason.value,
            "visible_subtype": self.visible_subtype.value,
            "confidence": self.confidence.value,
            "notes": self.notes or "",
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RequirementInspectionRecord":
        return cls(
            doc_id=data["doc_id"],
            req_id=data["req_id"],
            requirement_text=data["requirement_text"],
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
            confidence=AnnotationConfidence(
                data.get("confidence", AnnotationConfidence.MEDIUM.value)
            ),
            notes=data.get("notes"),
        )
