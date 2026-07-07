from __future__ import annotations

from dataclasses import dataclass
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

from PIL import Image


_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "for",
    "from",
    "has",
    "have",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "page",
    "screen",
    "shall",
    "should",
    "system",
    "that",
    "the",
    "their",
    "this",
    "to",
    "ui",
    "user",
    "users",
    "with",
}


@dataclass(frozen=True)
class OcrTextBox:
    text: str
    bbox: dict[str, float]
    confidence: float | None = None
    level: str = "line"
    source: str = "tesseract"

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "level": self.level,
            "source": self.source,
        }


def image_size(image_path: Path) -> tuple[int, int]:
    try:
        with Image.open(image_path) as image:
            return int(image.width), int(image.height)
    except Exception:
        return 0, 0


def normalize_ocr_text(text: str) -> str:
    return " ".join(text.split()).strip()


def ocr_sidecar_candidates(image_path: Path) -> list[Path]:
    return [
        image_path.with_suffix(".ocr.json"),
        image_path.with_name(f"{image_path.stem}_ocr.json"),
        image_path.parent / "ocr" / f"{image_path.stem}.json",
    ]


def existing_ocr_sidecar(image_path: Path) -> Path | None:
    for candidate in ocr_sidecar_candidates(image_path):
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def default_ocr_sidecar_path(image_path: Path) -> Path:
    return image_path.parent / "ocr" / f"{image_path.stem}.json"


def _tokens(text: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOPWORDS and len(token) > 1}


def _bbox_from_tsv_row(row: dict[str, str]) -> dict[str, float] | None:
    try:
        left = float(row["left"])
        top = float(row["top"])
        width = float(row["width"])
        height = float(row["height"])
    except (KeyError, TypeError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    return {"x1": left, "y1": top, "x2": left + width, "y2": top + height}


def _merge_bboxes(boxes: list[dict[str, float]]) -> dict[str, float]:
    return {
        "x1": min(box["x1"] for box in boxes),
        "y1": min(box["y1"] for box in boxes),
        "x2": max(box["x2"] for box in boxes),
        "y2": max(box["y2"] for box in boxes),
    }


def parse_tesseract_tsv(tsv_text: str) -> list[OcrTextBox]:
    rows = [
        row
        for row in csv.DictReader(io.StringIO(tsv_text), delimiter="\t")
        if isinstance(row, dict)
    ]
    word_rows: list[dict[str, str]] = []
    for row in rows:
        text = normalize_ocr_text(str(row.get("text") or ""))
        if not text:
            continue
        bbox = _bbox_from_tsv_row(row)
        if bbox is None:
            continue
        row["_normalized_text"] = text
        row["_bbox"] = json.dumps(bbox)
        word_rows.append(row)

    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    for row in word_rows:
        key = (
            str(row.get("block_num") or "0"),
            str(row.get("par_num") or "0"),
            str(row.get("line_num") or "0"),
            str(row.get("page_num") or "0"),
        )
        grouped.setdefault(key, []).append(row)

    boxes: list[OcrTextBox] = []
    for line_rows in grouped.values():
        texts = [str(row["_normalized_text"]) for row in line_rows]
        bboxes = [json.loads(str(row["_bbox"])) for row in line_rows]
        confidences = []
        for row in line_rows:
            try:
                confidence = float(row.get("conf") or -1)
            except ValueError:
                confidence = -1
            if confidence >= 0:
                confidences.append(confidence / 100.0)
        boxes.append(
            OcrTextBox(
                text=normalize_ocr_text(" ".join(texts)),
                bbox=_merge_bboxes(bboxes),
                confidence=(sum(confidences) / len(confidences)) if confidences else None,
                level="line",
            )
        )

    for row in word_rows:
        boxes.append(
            OcrTextBox(
                text=str(row["_normalized_text"]),
                bbox=json.loads(str(row["_bbox"])),
                confidence=_confidence_from_row(row),
                level="word",
            )
        )

    return boxes


def _confidence_from_row(row: dict[str, str]) -> float | None:
    try:
        confidence = float(row.get("conf") or -1)
    except ValueError:
        return None
    return confidence / 100.0 if confidence >= 0 else None


def run_tesseract_text(
    image_path: Path,
    *,
    tesseract_path: str,
    language: str = "eng",
    psm: int = 6,
    timeout_seconds: int = 60,
) -> str:
    result = subprocess.run(
        [tesseract_path, str(image_path), "stdout", "-l", language, "--psm", str(psm)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout_seconds,
    )
    if result.returncode != 0:
        stderr = normalize_ocr_text(result.stderr)
        raise RuntimeError(stderr or f"tesseract exited with status {result.returncode}")
    return normalize_ocr_text(result.stdout)


def run_tesseract_boxes(
    image_path: Path,
    *,
    tesseract_path: str,
    language: str = "eng",
    psm: int = 6,
    timeout_seconds: int = 60,
) -> list[OcrTextBox]:
    result = subprocess.run(
        [tesseract_path, str(image_path), "stdout", "-l", language, "--psm", str(psm), "tsv"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout_seconds,
    )
    if result.returncode != 0:
        stderr = normalize_ocr_text(result.stderr)
        raise RuntimeError(stderr or f"tesseract tsv exited with status {result.returncode}")
    return parse_tesseract_tsv(result.stdout)


def write_ocr_sidecar(
    image_path: Path,
    *,
    text: str,
    text_boxes: list[OcrTextBox] | None = None,
    sidecar_path: Path | None = None,
    engine_path: str | None = None,
    language: str = "eng",
    psm: int = 6,
) -> Path:
    target = sidecar_path or default_ocr_sidecar_path(image_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    image_width, image_height = image_size(image_path)
    payload = {
        "text": text,
        "ocr_text": text,
        "text_boxes": [box.to_dict() for box in text_boxes or []],
        "engine": "tesseract",
        "engine_path": engine_path,
        "language": language,
        "psm": psm,
        "image_path": str(image_path),
        "image_width": image_width,
        "image_height": image_height,
        "coordinate_space": "image_pixels",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def ensure_ocr_sidecar(
    image_path: Path,
    *,
    force: bool = False,
    tesseract_cmd: str = "tesseract",
    language: str = "eng",
    psm: int = 6,
    timeout_seconds: int = 60,
) -> Path | None:
    if not force:
        current = existing_ocr_sidecar(image_path)
        if current is not None:
            return current
    tesseract_path = shutil.which(tesseract_cmd)
    if tesseract_path is None:
        return None
    text = run_tesseract_text(
        image_path,
        tesseract_path=tesseract_path,
        language=language,
        psm=psm,
        timeout_seconds=timeout_seconds,
    )
    boxes = run_tesseract_boxes(
        image_path,
        tesseract_path=tesseract_path,
        language=language,
        psm=psm,
        timeout_seconds=timeout_seconds,
    )
    return write_ocr_sidecar(
        image_path,
        text=text,
        text_boxes=boxes,
        engine_path=tesseract_path,
        language=language,
        psm=psm,
    )


def load_ocr_text_boxes(image_path: Path) -> list[OcrTextBox]:
    sidecar = existing_ocr_sidecar(image_path)
    if sidecar is None:
        return []
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw_boxes = data.get("text_boxes")
    if not isinstance(raw_boxes, list):
        return []
    boxes: list[OcrTextBox] = []
    for raw_box in raw_boxes:
        if not isinstance(raw_box, dict):
            continue
        text = normalize_ocr_text(str(raw_box.get("text") or ""))
        bbox = raw_box.get("bbox")
        if not text or not isinstance(bbox, dict):
            continue
        try:
            normalized_bbox = {
                "x1": float(bbox["x1"]),
                "y1": float(bbox["y1"]),
                "x2": float(bbox["x2"]),
                "y2": float(bbox["y2"]),
            }
        except (KeyError, TypeError, ValueError):
            continue
        if normalized_bbox["x2"] <= normalized_bbox["x1"] or normalized_bbox["y2"] <= normalized_bbox["y1"]:
            continue
        confidence = raw_box.get("confidence")
        boxes.append(
            OcrTextBox(
                text=text,
                bbox=normalized_bbox,
                confidence=float(confidence) if isinstance(confidence, (int, float)) else None,
                level=str(raw_box.get("level") or "line"),
                source=str(raw_box.get("source") or data.get("engine") or "tesseract"),
            )
        )
    return boxes


class TextBoxLocalizer:
    def __init__(self, *, min_score: float = 0.12) -> None:
        self.min_score = min_score

    def suggest(self, claim_text: str, image_path: Path, *, max_candidates: int = 5) -> list[dict[str, Any]]:
        claim_tokens = _tokens(claim_text)
        if not claim_tokens:
            return []
        image_width, image_height = image_size(image_path)
        candidates: list[dict[str, Any]] = []
        for box in load_ocr_text_boxes(image_path):
            box_tokens = _tokens(box.text)
            if not box_tokens:
                continue
            overlap = claim_tokens.intersection(box_tokens)
            if not overlap:
                continue
            precision = len(overlap) / len(box_tokens)
            recall = len(overlap) / len(claim_tokens)
            score = (2 * precision * recall) / (precision + recall) if precision + recall else 0.0
            if box.level == "line":
                score *= 1.1
            if score < self.min_score:
                continue
            candidates.append(
                {
                    "bbox": box.bbox,
                    "matched_text": box.text,
                    "score": min(1.0, score),
                    "confidence": box.confidence,
                    "source": box.source,
                    "level": box.level,
                    "image_path": str(image_path),
                    "image_width": image_width,
                    "image_height": image_height,
                    "coordinate_space": "image_pixels",
                }
            )
        candidates.sort(key=lambda item: (-float(item["score"]), str(item["level"]) != "line"))
        return candidates[:max_candidates]
