from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ui_verifier.requirement_inspection.pure_schemas import PureRequirementCandidate


ANNOTATION_LABEL_FIELDNAMES = [
    "requirement_type",
    "ui_evaluability",
    "non_evaluable_reason",
    "visible_subtype",
    "confidence",
    "notes",
]

ANNOTATION_SHEET_FIELDNAMES = [
    "doc_id",
    "req_id",
    "requirement_text",
    *ANNOTATION_LABEL_FIELDNAMES,
]

PURE_CANDIDATE_ANNOTATION_SHEET_FIELDNAMES = [
    "doc_id",
    "candidate_id",
    "requirement_text",
    "context_text",
    "breadcrumb",
    "extraction_mode",
    "local_label",
    "source_node_id",
    "supporting_node_ids",
    *ANNOTATION_LABEL_FIELDNAMES,
]


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _blank_annotation_labels() -> dict[str, str]:
    return {field_name: "" for field_name in ANNOTATION_LABEL_FIELDNAMES}


def _serialize_sequence(items: tuple[str, ...]) -> str:
    if not items:
        return ""
    return json.dumps(list(items), ensure_ascii=False)


@dataclass(slots=True, frozen=True)
class RequirementStatement:
    doc_id: str
    req_id: str
    requirement_text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "doc_id", _require_non_empty(self.doc_id, "doc_id"))
        object.__setattr__(self, "req_id", _require_non_empty(self.req_id, "req_id"))
        object.__setattr__(
            self,
            "requirement_text",
            _require_non_empty(self.requirement_text, "requirement_text"),
        )

    def to_annotation_row(self) -> dict[str, str]:
        return {
            "doc_id": self.doc_id,
            "req_id": self.req_id,
            "requirement_text": self.requirement_text,
            **_blank_annotation_labels(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "RequirementStatement":
        return cls(
            doc_id=str(data["doc_id"]),
            req_id=str(data["req_id"]),
            requirement_text=str(data["requirement_text"]),
        )


def load_requirement_statements_csv(path: Path) -> list[RequirementStatement]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [RequirementStatement.from_dict(row) for row in reader]


def load_requirement_statements_jsonl(path: Path) -> list[RequirementStatement]:
    statements: list[RequirementStatement] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            statements.append(RequirementStatement.from_dict(json.loads(line)))
    return statements


def load_requirement_statements(path: Path) -> list[RequirementStatement]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return load_requirement_statements_csv(path)
    if suffix == ".jsonl":
        return load_requirement_statements_jsonl(path)
    raise ValueError(f"Unsupported input format: {path}")


def load_pure_requirement_candidates_jsonl(path: Path) -> list[PureRequirementCandidate]:
    candidates: list[PureRequirementCandidate] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            candidates.append(PureRequirementCandidate.from_dict(json.loads(line)))
    return candidates


def load_pure_requirement_candidates(path: Path) -> list[PureRequirementCandidate]:
    if path.suffix.lower() != ".jsonl":
        raise ValueError(f"Unsupported PURE candidate input format: {path}")
    return load_pure_requirement_candidates_jsonl(path)


def _ensure_unique_ids(statements: Iterable[RequirementStatement]) -> None:
    seen: set[tuple[str, str]] = set()
    for statement in statements:
        key = (statement.doc_id, statement.req_id)
        if key in seen:
            raise ValueError(f"Duplicate requirement identifier found: doc_id={statement.doc_id}, req_id={statement.req_id}")
        seen.add(key)


def _dedupe_pure_requirement_candidates(
    candidates: Iterable[PureRequirementCandidate],
) -> list[PureRequirementCandidate]:
    deduped: list[PureRequirementCandidate] = []
    seen: dict[tuple[str, str], PureRequirementCandidate] = {}
    for candidate in candidates:
        key = (candidate.doc_id, candidate.candidate_id)
        existing = seen.get(key)
        if existing is None:
            seen[key] = candidate
            deduped.append(candidate)
            continue
        if existing == candidate:
            continue
        raise ValueError(
            "Conflicting duplicate PURE candidate found: "
            f"doc_id={candidate.doc_id}, candidate_id={candidate.candidate_id}"
        )
    return deduped


def write_blank_annotation_sheet(
    statements: list[RequirementStatement],
    path: Path,
    *,
    limit: int | None = None,
) -> None:
    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be positive when provided")
        statements = statements[:limit]

    _ensure_unique_ids(statements)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ANNOTATION_SHEET_FIELDNAMES)
        writer.writeheader()
        for statement in statements:
            writer.writerow(statement.to_annotation_row())


def _pure_candidate_to_annotation_row(candidate: PureRequirementCandidate) -> dict[str, str]:
    return {
        "doc_id": candidate.doc_id,
        "candidate_id": candidate.candidate_id,
        "requirement_text": candidate.requirement_text,
        "context_text": candidate.context_text or "",
        "breadcrumb": _serialize_sequence(candidate.breadcrumb),
        "extraction_mode": candidate.extraction_mode.value,
        "local_label": candidate.local_label or "",
        "source_node_id": candidate.source_node_id,
        "supporting_node_ids": _serialize_sequence(candidate.supporting_node_ids),
        **_blank_annotation_labels(),
    }


def write_blank_pure_candidate_annotation_sheet(
    candidates: list[PureRequirementCandidate],
    path: Path,
    *,
    limit: int | None = None,
) -> None:
    candidates = _dedupe_pure_requirement_candidates(candidates)

    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be positive when provided")
        candidates = candidates[:limit]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PURE_CANDIDATE_ANNOTATION_SHEET_FIELDNAMES)
        writer.writeheader()
        for candidate in candidates:
            writer.writerow(_pure_candidate_to_annotation_row(candidate))
