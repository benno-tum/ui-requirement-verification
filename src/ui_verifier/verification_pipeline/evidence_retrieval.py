from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import math
import re
from typing import Any

from ui_verifier.verification_pipeline.schemas import (
    EvidenceItem,
    RequirementClaim,
    ScreenRepresentation,
)


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


def _tokens(text: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOPWORDS and len(token) > 1}


def _screen_document(screen: ScreenRepresentation) -> str:
    parts = [screen.visible_text, screen.ocr_text or ""]
    summary = screen.screen_summary
    if summary and not summary.lower().startswith("no extracted screen representation"):
        parts.append(summary)
    return " ".join(part.strip() for part in parts if part and part.strip())


def _truncate(text: str, max_chars: int = 240) -> str:
    text = " ".join(text.split()).strip()
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3].rstrip()}..."


def _evidence_observation(
    claim: RequirementClaim,
    screen: ScreenRepresentation,
    *,
    score: float,
    source: str,
) -> str:
    document = _screen_document(screen) or screen.screen_summary
    claim_tokens = _tokens(claim.claim_text)
    matched = sorted(claim_tokens.intersection(_tokens(document)))
    matched_text = ", ".join(matched[:8])
    prefix = f"{source} matched score {score:.3f}"
    if matched_text:
        prefix = f"{prefix} on visible terms: {matched_text}"
    snippet = _truncate(document)
    return f"{prefix}. {snippet}" if snippet else prefix


def _make_evidence(
    claim: RequirementClaim,
    screen: ScreenRepresentation,
    *,
    score: float,
    source: str,
) -> EvidenceItem:
    return EvidenceItem(
        step_index=screen.step_index,
        screenshot_path=screen.screenshot_path,
        visible_observation=_evidence_observation(claim, screen, score=score, source=source),
        confidence=max(0.0, min(1.0, float(score))),
        source=source,
        metadata={"score": float(score)},
    )


class EvidenceRetriever(ABC):
    def __init__(self, *, top_k: int = 3) -> None:
        if top_k < 1:
            raise ValueError("top_k must be >= 1")
        self.top_k = top_k

    @abstractmethod
    def retrieve(
        self,
        claims: list[RequirementClaim],
        screens: list[ScreenRepresentation],
    ) -> dict[str, list[EvidenceItem]]:
        raise NotImplementedError


class LexicalEvidenceRetriever(EvidenceRetriever):
    def retrieve(
        self,
        claims: list[RequirementClaim],
        screens: list[ScreenRepresentation],
    ) -> dict[str, list[EvidenceItem]]:
        results: dict[str, list[EvidenceItem]] = {}
        screen_docs = [(screen, _screen_document(screen), _tokens(_screen_document(screen))) for screen in screens]

        for claim in claims:
            claim_tokens = _tokens(claim.claim_text)
            scored: list[tuple[float, ScreenRepresentation]] = []
            if claim_tokens:
                for screen, document, screen_tokens in screen_docs:
                    if not document or not screen_tokens:
                        continue
                    overlap = claim_tokens.intersection(screen_tokens)
                    if not overlap:
                        continue
                    score = len(overlap) / max(len(claim_tokens), 1)
                    if claim.claim_text.lower() in document.lower():
                        score = max(score, 0.95)
                    scored.append((score, screen))

            scored.sort(key=lambda item: (-item[0], item[1].step_index))
            results[claim.claim_id] = [
                _make_evidence(claim, screen, score=score, source="lexical")
                for score, screen in scored[: self.top_k]
                if score > 0.0
            ]

        return results


class TfidfEvidenceRetriever(EvidenceRetriever):
    def __init__(self, *, top_k: int = 3, fallback: EvidenceRetriever | None = None) -> None:
        super().__init__(top_k=top_k)
        self.fallback = fallback or LexicalEvidenceRetriever(top_k=top_k)

    def retrieve(
        self,
        claims: list[RequirementClaim],
        screens: list[ScreenRepresentation],
    ) -> dict[str, list[EvidenceItem]]:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError:
            return self.fallback.retrieve(claims, screens)

        screen_docs = [_screen_document(screen) for screen in screens]
        if not claims or not any(screen_docs):
            return self.fallback.retrieve(claims, screens)

        claim_docs = [claim.claim_text for claim in claims]
        try:
            vectorizer = TfidfVectorizer(stop_words="english")
            matrix = vectorizer.fit_transform([*claim_docs, *screen_docs])
        except ValueError:
            return self.fallback.retrieve(claims, screens)

        claim_matrix = matrix[: len(claims)]
        screen_matrix = matrix[len(claims) :]
        results: dict[str, list[EvidenceItem]] = {}

        for claim_index, claim in enumerate(claims):
            scores = (claim_matrix[claim_index] @ screen_matrix.T).toarray()[0]
            scored = [
                (float(score), screen)
                for score, screen in zip(scores, screens, strict=False)
                if float(score) > 0.0
            ]
            scored.sort(key=lambda item: (-item[0], item[1].step_index))
            results[claim.claim_id] = [
                _make_evidence(claim, screen, score=score, source="tfidf")
                for score, screen in scored[: self.top_k]
            ]

        if not any(results.values()):
            return self.fallback.retrieve(claims, screens)
        return results


def _as_float_vector(vector: Any) -> list[float]:
    if hasattr(vector, "tolist"):
        vector = vector.tolist()
    return [float(value) for value in vector]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


class EmbeddingEvidenceRetriever(EvidenceRetriever):
    def __init__(
        self,
        *,
        top_k: int = 3,
        embedding_model: Any | None = None,
        model_name_or_path: str | None = None,
        fallback: EvidenceRetriever | None = None,
    ) -> None:
        super().__init__(top_k=top_k)
        self.embedding_model = embedding_model
        self.model_name_or_path = model_name_or_path
        self.fallback = fallback or LexicalEvidenceRetriever(top_k=top_k)

    def retrieve(
        self,
        claims: list[RequirementClaim],
        screens: list[ScreenRepresentation],
    ) -> dict[str, list[EvidenceItem]]:
        model = self._load_model()
        if model is None:
            return self.fallback.retrieve(claims, screens)

        screen_docs = [_screen_document(screen) for screen in screens]
        if not claims or not any(screen_docs):
            return self.fallback.retrieve(claims, screens)

        texts = [claim.claim_text for claim in claims] + screen_docs
        try:
            vectors = self._encode(model, texts)
        except Exception:
            return self.fallback.retrieve(claims, screens)

        claim_vectors = vectors[: len(claims)]
        screen_vectors = vectors[len(claims) :]
        results: dict[str, list[EvidenceItem]] = {}
        for claim, claim_vector in zip(claims, claim_vectors, strict=False):
            scored = [
                (_cosine_similarity(claim_vector, screen_vector), screen)
                for screen_vector, screen in zip(screen_vectors, screens, strict=False)
            ]
            scored = [(score, screen) for score, screen in scored if score > 0.0]
            scored.sort(key=lambda item: (-item[0], item[1].step_index))
            results[claim.claim_id] = [
                _make_evidence(claim, screen, score=score, source="embedding")
                for score, screen in scored[: self.top_k]
            ]

        if not any(results.values()):
            return self.fallback.retrieve(claims, screens)
        return results

    def _load_model(self) -> Any | None:
        if self.embedding_model is not None:
            return self.embedding_model
        if not self.model_name_or_path:
            return None

        model_path = Path(self.model_name_or_path).expanduser()
        if not model_path.exists():
            return None
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            return None

        try:
            self.embedding_model = SentenceTransformer(str(model_path), local_files_only=True)
        except TypeError:
            self.embedding_model = SentenceTransformer(str(model_path))
        except Exception:
            return None
        return self.embedding_model

    @staticmethod
    def _encode(model: Any, texts: list[str]) -> list[list[float]]:
        try:
            vectors = model.encode(texts, convert_to_numpy=False, show_progress_bar=False)
        except TypeError:
            vectors = model.encode(texts)
        return [_as_float_vector(vector) for vector in vectors]


def build_evidence_retriever(
    retriever: str,
    *,
    top_k: int = 3,
    embedding_model_path: str | None = None,
) -> EvidenceRetriever:
    normalized = retriever.strip().lower()
    if normalized == "lexical":
        return LexicalEvidenceRetriever(top_k=top_k)
    if normalized == "tfidf":
        return TfidfEvidenceRetriever(top_k=top_k)
    if normalized == "embedding":
        return EmbeddingEvidenceRetriever(top_k=top_k, model_name_or_path=embedding_model_path)
    raise ValueError("retriever must be one of: lexical, tfidf, embedding")
