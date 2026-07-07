from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ui_verifier.verification.schemas import UIEvaluability, UncertaintyReason, VerificationLabel


def _strip_required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _strip_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("optional text fields must be strings or None")
    value = value.strip()
    return value or None


class ClaimStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    SUPPORTED_WITH_CAVEAT = "SUPPORTED_WITH_CAVEAT"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    MISSING = "MISSING"
    CONTRADICTED = "CONTRADICTED"
    HIDDEN = "HIDDEN"
    AMBIGUOUS = "AMBIGUOUS"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ScreenshotStep(StrictModel):
    step_index: int = Field(ge=0)
    screenshot_path: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("screenshot_path", mode="before")
    @classmethod
    def _normalize_path(cls, value: str | Path) -> str:
        return _strip_required_text(str(value), "screenshot_path")


class ScreenRepresentation(StrictModel):
    step_index: int = Field(ge=0)
    screenshot_path: str
    image_width: int | None = Field(default=None, gt=0)
    image_height: int | None = Field(default=None, gt=0)
    visible_text: str = ""
    ocr_text: str | None = None
    screen_summary: str = ""
    sources: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("screenshot_path", mode="before")
    @classmethod
    def _normalize_path(cls, value: str | Path) -> str:
        return _strip_required_text(str(value), "screenshot_path")

    @field_validator("visible_text", "screen_summary")
    @classmethod
    def _normalize_text(cls, value: str) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("ocr_text")
    @classmethod
    def _normalize_ocr_text(cls, value: str | None) -> str | None:
        return _strip_optional_text(value)


class RequirementInput(StrictModel):
    requirement_id: str
    text: str
    flow_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("requirement_id", "text")
    @classmethod
    def _normalize_required_text(cls, value: str, info: Any) -> str:
        return _strip_required_text(value, info.field_name)

    @field_validator("flow_id")
    @classmethod
    def _normalize_flow_id(cls, value: str | None) -> str | None:
        return _strip_optional_text(value)


class RequirementClaim(StrictModel):
    claim_id: str
    requirement_id: str
    claim_text: str
    source_requirement_text: str
    claim_index: int = Field(ge=1)
    is_core: bool = True
    is_observable: bool = True
    hidden_indicators: list[str] = Field(default_factory=list)
    uncertainty_reasons: list[UncertaintyReason] = Field(default_factory=list)

    @field_validator("claim_id", "requirement_id", "claim_text", "source_requirement_text")
    @classmethod
    def _normalize_required_text(cls, value: str, info: Any) -> str:
        return _strip_required_text(value, info.field_name)


class EvidenceItem(StrictModel):
    step_index: int = Field(ge=0)
    screenshot_path: str
    visible_observation: str
    bbox: list[float] | None = None
    bbox_metadata: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("screenshot_path", mode="before")
    @classmethod
    def _normalize_path(cls, value: str | Path) -> str:
        return _strip_required_text(str(value), "screenshot_path")

    @field_validator("visible_observation")
    @classmethod
    def _normalize_observation(cls, value: str) -> str:
        return _strip_required_text(value, "visible_observation")

    @field_validator("source")
    @classmethod
    def _normalize_source(cls, value: str | None) -> str | None:
        return _strip_optional_text(value)

    @field_validator("bbox")
    @classmethod
    def _validate_bbox(cls, value: list[float] | None) -> list[float] | None:
        if value is None:
            return None
        if len(value) != 4:
            raise ValueError("bbox must be [x1, y1, x2, y2]")
        bbox = [float(v) for v in value]
        if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            raise ValueError("bbox must satisfy x2 > x1 and y2 > y1")
        return bbox


class ClaimVerificationResult(StrictModel):
    claim_id: str
    requirement_id: str
    claim_text: str
    status: ClaimStatus
    is_core: bool = True
    is_observable: bool = True
    evidence: list[EvidenceItem] = Field(default_factory=list)
    uncertainty_reasons: list[UncertaintyReason] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    rationale: str

    @field_validator("claim_id", "requirement_id", "claim_text", "rationale")
    @classmethod
    def _normalize_required_text(cls, value: str, info: Any) -> str:
        return _strip_required_text(value, info.field_name)


class RequirementVerificationResult(StrictModel):
    requirement_id: str
    requirement_text: str
    ui_evaluability: UIEvaluability
    final_label: VerificationLabel
    claims: list[ClaimVerificationResult] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    uncertainty_reasons: list[UncertaintyReason] = Field(default_factory=list)
    rationale: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("requirement_id", "requirement_text", "rationale")
    @classmethod
    def _normalize_required_text(cls, value: str, info: Any) -> str:
        return _strip_required_text(value, info.field_name)


class PipelineInput(StrictModel):
    flow_id: str
    screenshots: list[ScreenshotStep]
    requirements: list[RequirementInput]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("flow_id")
    @classmethod
    def _normalize_flow_id(cls, value: str) -> str:
        return _strip_required_text(value, "flow_id")


class PipelineOutput(StrictModel):
    flow_id: str
    screen_representations: list[ScreenRepresentation] = Field(default_factory=list)
    results: list[RequirementVerificationResult] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("flow_id")
    @classmethod
    def _normalize_flow_id(cls, value: str) -> str:
        return _strip_required_text(value, "flow_id")
