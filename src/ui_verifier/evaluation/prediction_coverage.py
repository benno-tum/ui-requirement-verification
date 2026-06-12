from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class RequirementCoverage:
    total_reviewed: int
    total_predictions: int
    missing_prediction_ids: list[str]
    extra_prediction_ids: list[str]
    missing_by_prefix: dict[str, int]
    extra_by_prefix: dict[str, int]

    @property
    def prediction_coverage(self) -> float:
        return (self.total_reviewed - len(self.missing_prediction_ids)) / self.total_reviewed if self.total_reviewed else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_reviewed": self.total_reviewed,
            "total_predictions": self.total_predictions,
            "prediction_coverage": self.prediction_coverage,
            "missing_prediction_count": len(self.missing_prediction_ids),
            "extra_prediction_count": len(self.extra_prediction_ids),
            "missing_prediction_ids": self.missing_prediction_ids,
            "extra_prediction_ids": self.extra_prediction_ids,
            "missing_by_prefix": self.missing_by_prefix,
            "extra_by_prefix": self.extra_by_prefix,
        }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        raw_items = data
    elif isinstance(data, dict):
        raw_items = data.get("items") or data.get("requirements") or data.get("results") or data.get("verdicts") or []
    else:
        raw_items = []
    return [item for item in raw_items if isinstance(item, dict)]


def _requirement_ids(path: Path) -> list[str]:
    ids: list[str] = []
    for item in _items(_load_json(path)):
        requirement_id = str(item.get("requirement_id") or item.get("id") or "").strip()
        if requirement_id:
            ids.append(requirement_id)
    return ids


def _prefix(requirement_id: str) -> str:
    return requirement_id.split("-", 1)[0] if "-" in requirement_id else requirement_id


def coverage_from_ids(reviewed_ids: list[str], prediction_ids: list[str]) -> RequirementCoverage:
    reviewed_set = set(reviewed_ids)
    prediction_set = set(prediction_ids)
    missing = sorted(reviewed_set - prediction_set)
    extra = sorted(prediction_set - reviewed_set)
    return RequirementCoverage(
        total_reviewed=len(reviewed_ids),
        total_predictions=len(prediction_ids),
        missing_prediction_ids=missing,
        extra_prediction_ids=extra,
        missing_by_prefix=dict(Counter(_prefix(requirement_id) for requirement_id in missing)),
        extra_by_prefix=dict(Counter(_prefix(requirement_id) for requirement_id in extra)),
    )


def coverage_for_files(verification_gold_path: Path, prediction_path: Path) -> RequirementCoverage:
    return coverage_from_ids(
        _requirement_ids(verification_gold_path),
        _requirement_ids(prediction_path),
    )
