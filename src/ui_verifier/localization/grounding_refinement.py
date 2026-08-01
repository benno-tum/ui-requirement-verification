from __future__ import annotations

from collections.abc import Sequence
import math
import re

from ui_verifier.localization.text_box_localizer import OcrTextBox


_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")
_GENERIC_TOKENS = {
    "displayed",
    "header",
    "indicator",
    "name",
    "page",
    "selected",
    "supporting",
    "text",
    "the",
    "visible",
}


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(text.lower())
        if len(token) > 1 and token not in _GENERIC_TOKENS
    }


def _same_text_line(left: OcrTextBox, right: OcrTextBox) -> bool:
    left_height = left.bbox["y2"] - left.bbox["y1"]
    right_height = right.bbox["y2"] - right.bbox["y1"]
    left_center = (left.bbox["y1"] + left.bbox["y2"]) / 2
    right_center = (right.bbox["y1"] + right.bbox["y2"]) / 2
    return abs(left_center - right_center) <= max(left_height, right_height) * 0.75


def refine_text_region(
    description: str,
    gemini_bbox: Sequence[float],
    ocr_boxes: Sequence[OcrTextBox],
    *,
    image_width: int,
    image_height: int,
) -> dict[str, object] | None:
    """Snap a semantic Gemini region to a nearby multi-token OCR phrase.

    The deliberately generous horizontal context preserves adjacent UI indicators
    such as a location pin or dropdown arrow that OCR does not recognize.
    """

    description_tokens = _tokens(description)
    if len(description_tokens) < 2 or len(gemini_bbox) != 4:
        return None

    matching_words = [
        box
        for box in ocr_boxes
        if box.level == "word" and _tokens(box.text).intersection(description_tokens)
    ]
    if len(matching_words) < 2:
        return None

    matching_words.sort(key=lambda box: (box.bbox["y1"], box.bbox["x1"]))
    components: list[list[OcrTextBox]] = []
    for word in matching_words:
        attached = False
        for component in components:
            rightmost = max(component, key=lambda box: box.bbox["x2"])
            max_height = max(
                rightmost.bbox["y2"] - rightmost.bbox["y1"],
                word.bbox["y2"] - word.bbox["y1"],
            )
            horizontal_gap = max(0.0, word.bbox["x1"] - rightmost.bbox["x2"])
            if _same_text_line(rightmost, word) and horizontal_gap <= max(24.0, max_height * 4):
                component.append(word)
                attached = True
                break
        if not attached:
            components.append([word])

    gemini_center_x = (float(gemini_bbox[0]) + float(gemini_bbox[2])) / 2
    gemini_center_y = (float(gemini_bbox[1]) + float(gemini_bbox[3])) / 2
    candidates: list[tuple[tuple[float, ...], list[OcrTextBox]]] = []
    header_constrained = bool(re.search(r"\b(header|top navigation|top bar)\b", description, re.IGNORECASE))
    for component in components:
        component_tokens = set().union(*(_tokens(word.text) for word in component))
        overlap = component_tokens.intersection(description_tokens)
        if len(overlap) < 2:
            continue
        x1 = min(word.bbox["x1"] for word in component)
        y1 = min(word.bbox["y1"] for word in component)
        x2 = max(word.bbox["x2"] for word in component)
        y2 = max(word.bbox["y2"] for word in component)
        if header_constrained and y2 > image_height * 0.15:
            continue
        distance = math.hypot((x1 + x2) / 2 - gemini_center_x, (y1 + y2) / 2 - gemini_center_y)
        confidence = sum(word.confidence or 0.0 for word in component) / len(component)
        candidates.append(((float(len(overlap)), confidence, -distance), component))
    if not candidates:
        return None

    _, best = max(candidates, key=lambda candidate: candidate[0])
    text_x1 = min(word.bbox["x1"] for word in best)
    text_y1 = min(word.bbox["y1"] for word in best)
    text_x2 = max(word.bbox["x2"] for word in best)
    text_y2 = max(word.bbox["y2"] for word in best)
    text_height = max(1.0, text_y2 - text_y1)
    horizontal_context = text_height * 3.4
    vertical_context = max(4.0, text_height * 0.6)
    refined = [
        max(0.0, text_x1 - horizontal_context),
        max(0.0, text_y1 - vertical_context),
        min(float(image_width), text_x2 + horizontal_context),
        min(float(image_height), text_y2 + vertical_context),
    ]
    return {
        "bbox": refined,
        "matched_text": " ".join(word.text for word in sorted(best, key=lambda box: box.bbox["x1"])),
        "ocr_word_boxes": [word.to_dict() for word in best],
    }
