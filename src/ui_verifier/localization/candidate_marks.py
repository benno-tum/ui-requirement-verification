from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class CandidateRegion:
    candidate_id: str
    source: str
    bbox: tuple[float, float, float, float]
    text: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source": self.source,
            "bbox": list(self.bbox),
            "text": self.text,
            "confidence": self.confidence,
        }


def clamp_bbox(
    bbox: Iterable[float],
    *,
    image_width: int,
    image_height: int,
) -> tuple[float, float, float, float] | None:
    values = tuple(float(value) for value in bbox)
    if len(values) != 4 or image_width <= 0 or image_height <= 0:
        return None
    x1, y1, x2, y2 = values
    x1 = max(0.0, min(float(image_width), x1))
    y1 = max(0.0, min(float(image_height), y1))
    x2 = max(0.0, min(float(image_width), x2))
    y2 = max(0.0, min(float(image_height), y2))
    if x2 <= x1 or y2 <= y1:
        return None
    return x1, y1, x2, y2


def pad_bbox(
    bbox: Iterable[float],
    *,
    image_width: int,
    image_height: int,
    horizontal: float,
    vertical: float,
) -> tuple[float, float, float, float] | None:
    values = tuple(float(value) for value in bbox)
    if len(values) != 4:
        return None
    x1, y1, x2, y2 = values
    return clamp_bbox(
        (x1 - horizontal, y1 - vertical, x2 + horizontal, y2 + vertical),
        image_width=image_width,
        image_height=image_height,
    )


def resolve_candidate_ids(
    candidate_ids: Iterable[Any],
    candidates: Iterable[CandidateRegion],
    *,
    maximum: int = 4,
) -> list[CandidateRegion]:
    lookup = {candidate.candidate_id: candidate for candidate in candidates}
    resolved: list[CandidateRegion] = []
    seen: set[str] = set()
    for raw_id in candidate_ids:
        candidate_id = str(raw_id).strip().upper()
        if not candidate_id or candidate_id in seen or candidate_id not in lookup:
            continue
        seen.add(candidate_id)
        resolved.append(lookup[candidate_id])
        if len(resolved) >= maximum:
            break
    return resolved
