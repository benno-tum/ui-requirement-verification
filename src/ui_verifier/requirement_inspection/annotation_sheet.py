from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ANNOTATION_SHEET_FIELDNAMES = [
    "doc_id",
    "req_id",
    "requirement_text",
    "requirement_type",
    "ui_evaluability",
    "non_evaluable_reason",
    "visible_subtype",
    "confidence",
    "notes",
]


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


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
            "requirement_type": "",
            "ui_evaluability": "",
            "non_evaluable_reason": "",
            "visible_subtype": "",
            "confidence": "",
            "notes": "",
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


def _ensure_unique_ids(statements: Iterable[RequirementStatement]) -> None:
    seen: set[tuple[str, str]] = set()
    for statement in statements:
        key = (statement.doc_id, statement.req_id)
        if key in seen:
            raise ValueError(f"Duplicate requirement identifier found: doc_id={statement.doc_id}, req_id={statement.req_id}")
        seen.add(key)


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
