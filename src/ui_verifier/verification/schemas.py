from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
from typing import Any

from ui_verifier.requirement_inspection.schemas import VisibleSubtype
from ui_verifier.requirements.schemas import RequirementScope

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


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("optional text fields must be strings or None")
    value = value.strip()
    return value or None


def _normalize_optional_string_list(values: list[Any] | None) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise TypeError("expected a list")
    return [str(value).strip() for value in values if str(value).strip()]


def _validate_step_indices(step_indices: list[int]) -> list[int]:
    if not isinstance(step_indices, list):
        raise TypeError("step_indices must be a list[int]")
    if any(not isinstance(i, int) for i in step_indices):
        raise TypeError("step_indices must contain only integers")
    if any(i < 0 for i in step_indices):
        raise ValueError("step_indices must be >= 0")
    return sorted(set(step_indices))


class VerificationLabel(str, Enum):
    FULFILLED = "FULFILLED"
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"
    NOT_FULFILLED = "NOT_FULFILLED"
    ABSTAIN = "ABSTAIN"


VerdictLabel = VerificationLabel


class UIEvaluability(str, Enum):
    UI_VERIFIABLE = "UI_VERIFIABLE"
    PARTIALLY_UI_VERIFIABLE = "PARTIALLY_UI_VERIFIABLE"
    NOT_UI_VERIFIABLE = "NOT_UI_VERIFIABLE"


class UncertaintyReason(str, Enum):
    TEXTUAL_AMBIGUITY = "TEXTUAL_AMBIGUITY"
    SCOPE_OR_CONTEXT_AMBIGUITY = "SCOPE_OR_CONTEXT_AMBIGUITY"
    QUANTIFIER_OR_COMPLETENESS_AMBIGUITY = "QUANTIFIER_OR_COMPLETENESS_AMBIGUITY"
    EVIDENCE_INTERPRETATION_AMBIGUITY = "EVIDENCE_INTERPRETATION_AMBIGUITY"
    FLOW_COVERAGE_GAP = "FLOW_COVERAGE_GAP"
    UNVERIFIED_SYSTEM_OUTCOME = "UNVERIFIED_SYSTEM_OUTCOME"
    NONTRIVIAL_HIDDEN_PROPERTY = "NONTRIVIAL_HIDDEN_PROPERTY"


class VerificationNote(str, Enum):
    ROUTINE_SYSTEM_DEPENDENCY = "ROUTINE_SYSTEM_DEPENDENCY"
    VISIBLE_SUCCESS_PROXY = "VISIBLE_SUCCESS_PROXY"


class ClaimEvidenceStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    SUPPORTED_WITH_CAVEAT = "SUPPORTED_WITH_CAVEAT"
    CONTRADICTED = "CONTRADICTED"
    MISSING = "MISSING"
    HIDDEN = "HIDDEN"
    AMBIGUOUS = "AMBIGUOUS"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class ClaimType(str, Enum):
    OBSERVABLE = "OBSERVABLE"
    HIDDEN = "HIDDEN"


class ClaimImportance(str, Enum):
    CORE = "CORE"
    SUPPORTING = "SUPPORTING"


def _normalize_verification_label(value: VerificationLabel | str | None) -> VerificationLabel | None:
    if value is None:
        return None
    if isinstance(value, VerificationLabel):
        return value
    if not isinstance(value, str):
        raise TypeError("verification label must be a string or None")

    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "fulfilled": VerificationLabel.FULFILLED,
        "partially_fulfilled": VerificationLabel.PARTIALLY_FULFILLED,
        "partial": VerificationLabel.PARTIALLY_FULFILLED,
        "not_fulfilled": VerificationLabel.NOT_FULFILLED,
        "notfulfilled": VerificationLabel.NOT_FULFILLED,
        "abstain": VerificationLabel.ABSTAIN,
    }
    if normalized not in mapping:
        raise ValueError(
            "verification label must be one of: FULFILLED, PARTIALLY_FULFILLED, NOT_FULFILLED, ABSTAIN"
        )
    return mapping[normalized]


def _normalize_ui_evaluability(value: UIEvaluability | str | None) -> UIEvaluability | None:
    if value is None:
        return None
    if isinstance(value, UIEvaluability):
        return value
    if not isinstance(value, str):
        raise TypeError("ui_evaluability must be a string or None")

    normalized = value.strip().upper()
    try:
        return UIEvaluability(normalized)
    except ValueError as exc:
        raise ValueError(
            "ui_evaluability must be one of: UI_VERIFIABLE, PARTIALLY_UI_VERIFIABLE, NOT_UI_VERIFIABLE"
        ) from exc


def _normalize_enum_list(
    values: list[Any] | None,
    enum_type: type[Enum],
    field_name: str,
) -> list[Enum]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise TypeError(f"{field_name} must be a list")

    normalized: list[Enum] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, enum_type):
            enum_value = value
        elif isinstance(value, str):
            try:
                enum_value = enum_type(value.strip().upper())
            except ValueError as exc:
                raise ValueError(f"Invalid {field_name} value: {value}") from exc
        else:
            raise TypeError(f"{field_name} entries must be strings")

        if enum_value.value in seen:
            continue
        seen.add(enum_value.value)
        normalized.append(enum_value)

    return normalized


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
    bbox_image_path: str | None = None
    bbox_image_width: int | None = None
    bbox_image_height: int | None = None
    bbox_coordinate_space: str | None = None
    bbox_source: str | None = None
    bbox_confidence: float | None = None

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

        self.bbox_image_path = _normalize_optional_text(self.bbox_image_path)
        self.bbox_coordinate_space = _normalize_optional_text(self.bbox_coordinate_space)
        self.bbox_source = _normalize_optional_text(self.bbox_source)
        if self.bbox_image_width is not None:
            self.bbox_image_width = int(self.bbox_image_width)
        if self.bbox_image_height is not None:
            self.bbox_image_height = int(self.bbox_image_height)
        if self.bbox_confidence is not None:
            self.bbox_confidence = float(self.bbox_confidence)

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
                "bbox_image_path": self.bbox_image_path,
                "bbox_image_width": self.bbox_image_width,
                "bbox_image_height": self.bbox_image_height,
                "bbox_coordinate_space": self.bbox_coordinate_space,
                "bbox_source": self.bbox_source,
                "bbox_confidence": self.bbox_confidence,
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
            bbox_image_path=data.get("bbox_image_path"),
            bbox_image_width=data.get("bbox_image_width"),
            bbox_image_height=data.get("bbox_image_height"),
            bbox_coordinate_space=data.get("bbox_coordinate_space"),
            bbox_source=data.get("bbox_source"),
            bbox_confidence=data.get("bbox_confidence"),
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

        self.label = _normalize_verification_label(self.label)

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
            label=_normalize_verification_label(data["label"]),
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


@dataclass(slots=True)
class EvidenceUnit:
    step_index: int
    evidence_type: EvidenceType = EvidenceType.SCREEN
    bbox: BoundingBox | None = None
    matched_text: str | None = None
    ui_element_id: str | None = None
    note: str | None = None
    bbox_image_path: str | None = None
    bbox_image_width: int | None = None
    bbox_image_height: int | None = None
    bbox_coordinate_space: str | None = None
    bbox_source: str | None = None
    bbox_confidence: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.step_index, int):
            raise TypeError("step_index must be an int")
        if self.step_index < 0:
            raise ValueError("step_index must be >= 0")

        self.matched_text = _normalize_optional_text(self.matched_text)
        self.ui_element_id = _normalize_optional_text(self.ui_element_id)
        self.note = _normalize_optional_text(self.note)
        self.bbox_image_path = _normalize_optional_text(self.bbox_image_path)
        self.bbox_coordinate_space = _normalize_optional_text(self.bbox_coordinate_space)
        self.bbox_source = _normalize_optional_text(self.bbox_source)
        if self.bbox_image_width is not None:
            self.bbox_image_width = int(self.bbox_image_width)
        if self.bbox_image_height is not None:
            self.bbox_image_height = int(self.bbox_image_height)
        if self.bbox_confidence is not None:
            self.bbox_confidence = float(self.bbox_confidence)

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
                "note": self.note,
                "bbox_image_path": self.bbox_image_path,
                "bbox_image_width": self.bbox_image_width,
                "bbox_image_height": self.bbox_image_height,
                "bbox_coordinate_space": self.bbox_coordinate_space,
                "bbox_source": self.bbox_source,
                "bbox_confidence": self.bbox_confidence,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceUnit":
        bbox_data = data.get("bbox")
        return cls(
            step_index=int(data["step_index"]),
            evidence_type=EvidenceType(data.get("evidence_type", EvidenceType.SCREEN.value)),
            bbox=BoundingBox.from_dict(bbox_data) if bbox_data else None,
            matched_text=data.get("matched_text"),
            ui_element_id=data.get("ui_element_id"),
            note=data.get("note") or data.get("reason"),
            bbox_image_path=data.get("bbox_image_path"),
            bbox_image_width=data.get("bbox_image_width"),
            bbox_image_height=data.get("bbox_image_height"),
            bbox_coordinate_space=data.get("bbox_coordinate_space"),
            bbox_source=data.get("bbox_source"),
            bbox_confidence=data.get("bbox_confidence"),
        )


@dataclass(slots=True)
class ClaimEvidence:
    claim: str
    status: ClaimEvidenceStatus
    claim_type: ClaimType = ClaimType.OBSERVABLE
    importance: ClaimImportance = ClaimImportance.CORE
    evidence_steps: list[int] = field(default_factory=list)
    evidence_units: list[EvidenceUnit] = field(default_factory=list)
    note: str | None = None

    def __post_init__(self) -> None:
        self.claim = _require_non_empty(self.claim, "claim")
        if not isinstance(self.status, ClaimEvidenceStatus):
            self.status = ClaimEvidenceStatus(str(self.status).strip().upper())
        if not isinstance(self.claim_type, ClaimType):
            self.claim_type = ClaimType(str(self.claim_type).strip().upper())
        if not isinstance(self.importance, ClaimImportance):
            self.importance = ClaimImportance(str(self.importance).strip().upper())

        self.evidence_steps = _validate_step_indices(self.evidence_steps)
        self.evidence_units = [unit if isinstance(unit, EvidenceUnit) else EvidenceUnit.from_dict(unit) for unit in self.evidence_units]
        self.note = _normalize_optional_text(self.note)

        if not self.evidence_units and self.evidence_steps:
            self.evidence_units = [EvidenceUnit(step_index=step_index) for step_index in self.evidence_steps]
        if self.evidence_units and not self.evidence_steps:
            self.evidence_steps = _validate_step_indices([unit.step_index for unit in self.evidence_units])

    def to_dict(self) -> dict[str, Any]:
        return _drop_none(
            {
                "claim": self.claim,
                "status": self.status.value,
                "claim_type": self.claim_type.value,
                "importance": self.importance.value,
                "evidence_steps": self.evidence_steps,
                "evidence_units": [unit.to_dict() for unit in self.evidence_units],
                "note": self.note,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClaimEvidence":
        return cls(
            claim=data["claim"],
            status=ClaimEvidenceStatus(str(data["status"]).strip().upper()),
            claim_type=ClaimType(str(data.get("claim_type", ClaimType.OBSERVABLE.value)).strip().upper()),
            importance=ClaimImportance(str(data.get("importance", ClaimImportance.CORE.value)).strip().upper()),
            evidence_steps=list(data.get("evidence_steps", [])),
            evidence_units=[EvidenceUnit.from_dict(unit) for unit in data.get("evidence_units", [])],
            note=data.get("note"),
        )


@dataclass(slots=True)
class VerificationGoldItem:
    requirement_id: str
    flow_id: str
    text: str
    scope: RequirementScope = RequirementScope.SINGLE_SCREEN
    tags: list[str] = field(default_factory=list)
    source_type: str | None = None
    source_id: str | None = None
    source_candidate_id: str | None = None
    source_harvest_id: str | None = None
    step_indices: list[int] = field(default_factory=list)
    requirement_type: str | None = None
    ui_evaluability: UIEvaluability | None = None
    visible_subtype: VisibleSubtype = VisibleSubtype.NONE
    annotation_notes: str | None = None
    annotated_by: str | None = None
    manual_verification_label: str | None = None
    manual_verification_notes: str | None = None
    intended_label: VerificationLabel | None = None
    verification_label: VerificationLabel | None = None
    uncertainty_reasons: list[UncertaintyReason] = field(default_factory=list)
    notes: list[VerificationNote] = field(default_factory=list)
    claims: list[ClaimEvidence] = field(default_factory=list)
    evidence_steps: list[int] = field(default_factory=list)
    evidence_units: list[EvidenceUnit] = field(default_factory=list)
    evidence_note: str | None = None
    rationale: str | None = None
    review_status: str = "needs_review"
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str | None = None

    def __post_init__(self) -> None:
        self.requirement_id = _require_non_empty(self.requirement_id, "requirement_id")
        self.flow_id = _require_non_empty(self.flow_id, "flow_id")
        self.text = _require_non_empty(self.text, "text")
        if not isinstance(self.scope, RequirementScope):
            self.scope = RequirementScope(str(self.scope).strip().lower())
        self.tags = _normalize_optional_string_list(self.tags)
        self.source_type = _normalize_optional_text(self.source_type)
        self.source_id = _normalize_optional_text(self.source_id)
        self.source_candidate_id = _normalize_optional_text(self.source_candidate_id)
        self.source_harvest_id = _normalize_optional_text(self.source_harvest_id)
        self.step_indices = _validate_step_indices(self.step_indices)
        self.requirement_type = _normalize_optional_text(self.requirement_type)
        self.ui_evaluability = _normalize_ui_evaluability(self.ui_evaluability)
        if not isinstance(self.visible_subtype, VisibleSubtype):
            self.visible_subtype = VisibleSubtype(str(self.visible_subtype).strip().upper())
        self.annotation_notes = _normalize_optional_text(self.annotation_notes)
        self.annotated_by = _normalize_optional_text(self.annotated_by)
        self.manual_verification_label = _normalize_optional_text(self.manual_verification_label)
        self.manual_verification_notes = _normalize_optional_text(self.manual_verification_notes)
        self.intended_label = _normalize_verification_label(self.intended_label)
        self.verification_label = _normalize_verification_label(self.verification_label)
        self.uncertainty_reasons = _normalize_enum_list(
            self.uncertainty_reasons,
            UncertaintyReason,
            "uncertainty_reasons",
        )
        self.notes = _normalize_enum_list(self.notes, VerificationNote, "notes")
        self.claims = [claim if isinstance(claim, ClaimEvidence) else ClaimEvidence.from_dict(claim) for claim in self.claims]
        self.evidence_steps = _validate_step_indices(self.evidence_steps)
        self.evidence_units = [unit if isinstance(unit, EvidenceUnit) else EvidenceUnit.from_dict(unit) for unit in self.evidence_units]
        if not self.evidence_units and self.evidence_steps:
            self.evidence_units = [EvidenceUnit(step_index=step_index) for step_index in self.evidence_steps]
        self.evidence_note = _normalize_optional_text(self.evidence_note)
        self.rationale = _normalize_optional_text(self.rationale)
        self.review_status = _require_non_empty(self.review_status, "review_status").lower()
        self.created_at = _require_non_empty(self.created_at, "created_at")
        self.updated_at = _normalize_optional_text(self.updated_at)

    def to_dict(self) -> dict[str, Any]:
        return _drop_none(
            {
                "requirement_id": self.requirement_id,
                "flow_id": self.flow_id,
                "text": self.text,
                "scope": self.scope.value,
                "tags": self.tags,
                "source_type": self.source_type,
                "source_id": self.source_id,
                "source_candidate_id": self.source_candidate_id,
                "source_harvest_id": self.source_harvest_id,
                "step_indices": self.step_indices,
                "requirement_type": self.requirement_type,
                "ui_evaluability": self.ui_evaluability.value if self.ui_evaluability else None,
                "visible_subtype": self.visible_subtype.value,
                "annotation_notes": self.annotation_notes,
                "annotated_by": self.annotated_by,
                "manual_verification_label": self.manual_verification_label,
                "manual_verification_notes": self.manual_verification_notes,
                "intended_label": self.intended_label.value if self.intended_label else None,
                "verification_label": self.verification_label.value if self.verification_label else None,
                "uncertainty_reasons": [reason.value for reason in self.uncertainty_reasons],
                "notes": [note.value for note in self.notes],
                "claims": [claim.to_dict() for claim in self.claims],
                "evidence_steps": self.evidence_steps,
                "evidence_units": [unit.to_dict() for unit in self.evidence_units],
                "evidence_note": self.evidence_note,
                "rationale": self.rationale,
                "review_status": self.review_status,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerificationGoldItem":
        return cls(
            requirement_id=data["requirement_id"],
            flow_id=data["flow_id"],
            text=data["text"],
            scope=RequirementScope(data.get("scope", RequirementScope.SINGLE_SCREEN.value)),
            tags=list(data.get("tags", [])),
            source_type=data.get("source_type"),
            source_id=data.get("source_id"),
            source_candidate_id=data.get("source_candidate_id"),
            source_harvest_id=data.get("source_harvest_id"),
            step_indices=list(data.get("step_indices", [])),
            requirement_type=data.get("requirement_type"),
            ui_evaluability=data.get("ui_evaluability"),
            visible_subtype=VisibleSubtype(data.get("visible_subtype", VisibleSubtype.NONE.value)),
            annotation_notes=data.get("annotation_notes"),
            annotated_by=data.get("annotated_by"),
            manual_verification_label=data.get("manual_verification_label"),
            manual_verification_notes=data.get("manual_verification_notes"),
            intended_label=data.get("intended_label"),
            verification_label=data.get("verification_label"),
            uncertainty_reasons=list(data.get("uncertainty_reasons", [])),
            notes=list(data.get("notes", [])),
            claims=[ClaimEvidence.from_dict(item) for item in data.get("claims", [])],
            evidence_steps=list(data.get("evidence_steps", [])),
            evidence_units=[EvidenceUnit.from_dict(item) for item in data.get("evidence_units", [])],
            evidence_note=data.get("evidence_note"),
            rationale=data.get("rationale"),
            review_status=data.get("review_status", "needs_review"),
            created_at=data.get("created_at", _utc_now_iso()),
            updated_at=data.get("updated_at"),
        )


@dataclass(slots=True)
class VerificationGoldFile:
    dataset: str
    flow_id: str
    items: list[VerificationGoldItem]

    def __post_init__(self) -> None:
        self.dataset = _require_non_empty(self.dataset, "dataset")
        self.flow_id = _require_non_empty(self.flow_id, "flow_id")
        for item in self.items:
            if item.flow_id != self.flow_id:
                raise ValueError(
                    f"Verification gold flow_id mismatch: {item.requirement_id} has flow_id={item.flow_id}, expected {self.flow_id}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "flow_id": self.flow_id,
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerificationGoldFile":
        items_raw = data.get("items")
        if items_raw is None:
            items_raw = data.get("requirements", [])
        return cls(
            dataset=data.get("dataset", "mind2web"),
            flow_id=data["flow_id"],
            items=[VerificationGoldItem.from_dict(item) for item in items_raw],
        )

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "VerificationGoldFile":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)
