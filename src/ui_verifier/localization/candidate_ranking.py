from __future__ import annotations

from collections import Counter
import math
import re
from typing import Any


_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a", "all", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "is", "it", "of", "on", "or", "shall", "should", "system", "that",
    "the", "their", "this", "to", "user", "users", "with", "within",
}
_SYNONYM_GROUPS = (
    {"locator", "location", "find", "finder", "search"},
    {"geographic", "city", "state", "zip", "postal", "location"},
    {"result", "results", "list", "listed", "locations"},
    {"homepage", "home"},
    {"map", "mapped"},
    {"search", "find", "query"},
)


def _tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in _TOKEN_RE.findall(text.lower()):
        if raw in _STOPWORDS or len(raw) < 2:
            continue
        tokens.append(raw)
        # A deliberately small normalizer helps match plurals and common UI wording
        # without introducing another model dependency.
        if len(raw) > 4 and raw.endswith("ies"):
            tokens.append(raw[:-3] + "y")
        elif len(raw) > 4 and raw.endswith("s"):
            tokens.append(raw[:-1])
        if len(raw) > 6 and raw.endswith("ing"):
            tokens.append(raw[:-3])
    present = set(tokens)
    for group in _SYNONYM_GROUPS:
        if present & group:
            tokens.extend(sorted(group))
    return tokens


def _intersection_fraction(inner: list[float], outer: list[float]) -> float:
    ix1 = max(float(inner[0]), float(outer[0]))
    iy1 = max(float(inner[1]), float(outer[1]))
    ix2 = min(float(inner[2]), float(outer[2]))
    iy2 = min(float(inner[3]), float(outer[3]))
    intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area = max(1.0, (float(inner[2]) - float(inner[0])) * (float(inner[3]) - float(inner[1])))
    return intersection / area


def _associated_ocr(candidate: dict[str, Any], all_candidates: list[dict[str, Any]]) -> str:
    if candidate.get("source") != "omniparser_ui":
        return ""
    box = candidate.get("bbox")
    if not isinstance(box, list) or len(box) != 4:
        return ""
    texts: list[str] = []
    for text_candidate in all_candidates:
        if text_candidate.get("source") != "tesseract_line" or not text_candidate.get("text"):
            continue
        text_box = text_candidate.get("bbox")
        if not isinstance(text_box, list) or len(text_box) != 4:
            continue
        center_x = (float(text_box[0]) + float(text_box[2])) / 2
        center_y = (float(text_box[1]) + float(text_box[3])) / 2
        center_inside = float(box[0]) <= center_x <= float(box[2]) and float(box[1]) <= center_y <= float(box[3])
        if center_inside or _intersection_fraction(text_box, box) >= 0.55:
            texts.append(str(text_candidate["text"]).strip())
    return " ".join(dict.fromkeys(texts))


def rank_candidates(
    candidates: list[dict[str, Any]],
    *,
    claim_text: str,
    requirement_text: str = "",
    image_width: float,
    image_height: float,
) -> list[dict[str, Any]]:
    """Rank screenshot-derived regions for a claim without any hosted model calls."""
    enriched: list[dict[str, Any]] = []
    documents: list[list[str]] = []
    for candidate in candidates:
        associated_text = _associated_ocr(candidate, candidates)
        semantic_text = " ".join(
            part for part in (
                str(candidate.get("caption") or ""),
                str(candidate.get("text") or ""),
                associated_text,
            ) if part
        )
        item = {**candidate, "associated_text": associated_text, "semantic_text": semantic_text}
        enriched.append(item)
        documents.append(_tokens(semantic_text))

    document_frequency: Counter[str] = Counter()
    for document in documents:
        document_frequency.update(set(document))
    count = max(1, len(documents))
    idf = {token: math.log((count + 1) / (frequency + 1)) + 1 for token, frequency in document_frequency.items()}
    query_tokens = _tokens(f"{claim_text} {requirement_text}")
    query_counts = Counter(query_tokens)

    def cosine(document: list[str]) -> float:
        if not document or not query_counts:
            return 0.0
        doc_counts = Counter(document)
        vocabulary = set(doc_counts) | set(query_counts)
        dot = sum(doc_counts[token] * query_counts[token] * idf.get(token, 1.0) ** 2 for token in vocabulary)
        doc_norm = math.sqrt(sum((doc_counts[token] * idf.get(token, 1.0)) ** 2 for token in vocabulary))
        query_norm = math.sqrt(sum((query_counts[token] * idf.get(token, 1.0)) ** 2 for token in vocabulary))
        return dot / (doc_norm * query_norm) if doc_norm and query_norm else 0.0

    ranked: list[dict[str, Any]] = []
    image_area = max(1.0, image_width * image_height)
    for item, document in zip(enriched, documents, strict=True):
        lexical = cosine(document)
        box = item.get("bbox") or [0, 0, image_width, image_height]
        area_ratio = max(0.0, (float(box[2]) - float(box[0])) * (float(box[3]) - float(box[1]))) / image_area
        size_penalty = max(0.0, area_ratio - 0.35) * 0.45
        source_bonus = 0.015 if item.get("source") == "omniparser_ui" and item.get("caption") else 0.0
        score = max(0.0, lexical + source_bonus - size_penalty)
        reasons: list[str] = []
        if item.get("caption"):
            reasons.append(f"caption: {item['caption']}")
        if item.get("text"):
            reasons.append(f"OCR: {item['text']}")
        elif item.get("associated_text"):
            reasons.append(f"contained OCR: {item['associated_text']}")
        ranked.append({**item, "rank_score": round(score, 6), "rank_reasons": reasons})
    ranked.sort(key=lambda item: (-float(item["rank_score"]), str(item.get("candidate_id") or "")))
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return ranked
