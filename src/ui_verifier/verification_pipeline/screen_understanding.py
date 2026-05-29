from __future__ import annotations

from html import unescape
import json
from pathlib import Path
import re
from typing import Any

from PIL import Image, UnidentifiedImageError

from ui_verifier.verification_pipeline.schemas import ScreenRepresentation, ScreenshotStep


_TEXT_TAG_RE = re.compile(r"<text\b[^>]*>(.*?)</text>", flags=re.IGNORECASE | re.DOTALL)
_ATTR_TEXT_RE = re.compile(
    r"\b(?:aria_label|aria-label|alt|placeholder|title|value)\s*=\s*['\"]([^'\"]+)['\"]",
    flags=re.IGNORECASE,
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _normalize_text(text: Any) -> str:
    if text is None:
        return ""
    text = _HTML_TAG_RE.sub(" ", str(text))
    text = unescape(text)
    return " ".join(text.split()).strip()


def _dedupe_texts(texts: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for text in texts:
        normalized = _normalize_text(text)
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def extract_visible_text_from_html(raw_html: str) -> str:
    """Best-effort text extraction from Mind2Web step metadata.

    This is intentionally lightweight. It is not an OCR substitute; it only
    reuses already exported UI text-like fields when they are present.
    """
    texts: list[str] = []
    texts.extend(match.group(1) for match in _TEXT_TAG_RE.finditer(raw_html))
    texts.extend(match.group(1) for match in _ATTR_TEXT_RE.finditer(raw_html))
    return " ".join(_dedupe_texts(texts))


def _text_from_json_sidecar(data: Any) -> str:
    texts: list[str] = []
    if isinstance(data, str):
        return _normalize_text(data)

    if isinstance(data, dict):
        for key in (
            "text",
            "ocr_text",
            "visible_text",
            "description",
            "screen_summary",
            "overall_summary",
        ):
            if key in data:
                texts.append(_normalize_text(data[key]))
        for key in ("visible_ui_elements", "visible_values", "uncertainties"):
            value = data.get(key)
            if isinstance(value, list):
                texts.extend(_normalize_text(item) for item in value)
        images = data.get("images")
        if isinstance(images, list):
            for item in images:
                texts.append(_text_from_json_sidecar(item))
    elif isinstance(data, list):
        for item in data:
            texts.append(_text_from_json_sidecar(item))

    return " ".join(_dedupe_texts(texts))


def _sidecar_candidates(path: Path) -> list[Path]:
    return [
        path.with_suffix(".ocr.txt"),
        path.with_suffix(".ocr.json"),
        path.with_name(f"{path.stem}_ocr.txt"),
        path.with_name(f"{path.stem}_ocr.json"),
        path.with_suffix(".txt"),
        path.with_suffix(".json"),
        path.parent / "ocr" / f"{path.stem}.txt",
        path.parent / "ocr" / f"{path.stem}.json",
    ]


def _read_sidecar_text(path: Path) -> tuple[str | None, str | None]:
    for candidate in _sidecar_candidates(path):
        if not candidate.exists() or not candidate.is_file():
            continue
        if candidate.suffix.lower() == ".json":
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            text = _text_from_json_sidecar(data)
        else:
            try:
                text = _normalize_text(candidate.read_text(encoding="utf-8"))
            except OSError:
                continue
        if text:
            return text, str(candidate)
    return None, None


def _truncate(text: str, max_chars: int = 600) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3].rstrip()}..."


class ScreenUnderstanding:
    def __init__(self, *, enable_placeholder_ocr: bool = False) -> None:
        self.enable_placeholder_ocr = enable_placeholder_ocr

    def understand(self, steps: list[ScreenshotStep]) -> list[ScreenRepresentation]:
        return [self.understand_step(step) for step in steps]

    def understand_step(self, step: ScreenshotStep) -> ScreenRepresentation:
        path = Path(step.screenshot_path)
        width: int | None = None
        height: int | None = None
        sources: list[str] = []

        if path.exists():
            try:
                with Image.open(path) as image:
                    width, height = image.size
                sources.append("image_metadata")
            except (OSError, UnidentifiedImageError):
                pass

        metadata_texts: list[str] = []
        for key in ("visible_text", "ocr_text", "screen_summary", "description"):
            if key in step.metadata:
                metadata_texts.append(_normalize_text(step.metadata.get(key)))
        raw_html = step.metadata.get("raw_html")
        if isinstance(raw_html, str) and raw_html.strip():
            html_text = extract_visible_text_from_html(raw_html)
            if html_text:
                metadata_texts.append(html_text)
                sources.append("raw_html")

        sidecar_text, sidecar_source = _read_sidecar_text(path)
        if sidecar_text:
            sources.append("sidecar")
        if sidecar_source:
            sources.append(sidecar_source)

        ocr_text = sidecar_text
        if ocr_text is None and self.enable_placeholder_ocr:
            ocr_text = self.placeholder_ocr(path)
            if ocr_text:
                sources.append("placeholder_ocr")

        visible_text = " ".join(_dedupe_texts([*metadata_texts, ocr_text or ""]))
        screen_summary = _normalize_text(step.metadata.get("screen_summary"))
        if not screen_summary:
            if visible_text:
                screen_summary = f"Visible text includes: {_truncate(visible_text)}"
            else:
                screen_summary = "No extracted screen representation is available yet."

        output_metadata = {
            key: value
            for key, value in step.metadata.items()
            if key not in {"raw_html", "pos_candidates"}
        }
        if "raw_html" in step.metadata:
            output_metadata["raw_html_present"] = True
        if "pos_candidates" in step.metadata:
            output_metadata["pos_candidate_count"] = (
                len(step.metadata["pos_candidates"]) if isinstance(step.metadata["pos_candidates"], list) else None
            )

        return ScreenRepresentation(
            step_index=step.step_index,
            screenshot_path=str(path),
            image_width=width,
            image_height=height,
            visible_text=visible_text,
            ocr_text=ocr_text,
            screen_summary=screen_summary,
            sources=_dedupe_texts(sources),
            metadata=output_metadata,
        )

    def placeholder_ocr(self, path: Path) -> str | None:
        return None
