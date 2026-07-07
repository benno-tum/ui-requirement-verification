from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import re
from typing import Any

from ui_verifier.common.json_utils import parse_json_response
from ui_verifier.model_config import model_name_for, provider_for, temperature_for
from ui_verifier.requirements.claim_decomposition import (
    decompose_requirement_claim_texts,
    decompose_requirement_with_diagnostics,
)
from ui_verifier.verification_pipeline.schemas import (
    RequirementClaim,
    RequirementInput,
    UIEvaluability,
    UncertaintyReason,
)


_HIDDEN_INDICATORS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "security",
        re.compile(
            r"\b(security|secure|encrypt|privacy|permission|"
            r"(?:user|account|access|admin(?:istrative)?) roles?|role[- ]based access)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "authentication correctness",
        re.compile(r"\b(authenticat|authori[sz]e|login correctness|access control)\b", re.IGNORECASE),
    ),
    ("backend", re.compile(r"\b(backend|server|api|service layer|integration)\b", re.IGNORECASE)),
    ("database", re.compile(r"\b(database|stored|storage|persist(?:s|ed|ing)?|persistence|retention)\b", re.IGNORECASE)),
    ("email delivery", re.compile(r"\b(email|sms|message delivery|notification delivery)\b", re.IGNORECASE)),
    ("payment processing", re.compile(r"\b(payment|charge|refund|transaction|billing)\b", re.IGNORECASE)),
    ("ranking correctness", re.compile(r"\b(rank(?:ing)? correctness|sorted correctly|relevance ranking)\b", re.IGNORECASE)),
    (
        "uptime",
        re.compile(
            r"\b(uptime|high availability|availability target|"
            r"available (?:24/7|at all times|without interruption))\b",
            re.IGNORECASE,
        ),
    ),
    ("performance target", re.compile(r"\b(performance|response time|latency|load time|throughput)\b", re.IGNORECASE)),
    (
        "long-term data correctness",
        re.compile(r"\b(long[- ]term|historical correctness|subsequent use|later visit|future session)\b", re.IGNORECASE),
    ),
    (
        "real-world external effects",
        re.compile(r"\b(real[- ]world|external effect|ship|deliver|booked|reservation completed)\b", re.IGNORECASE),
    ),
)

_VISIBLE_INDICATOR_RE = re.compile(
    r"\b("
    r"show|shows|display|displays|visible|present|presents|expose|exposes|"
    r"page|screen|button|link|field|input|dropdown|menu|navigation|banner|dialog|"
    r"table|list|card|summary|message|confirmation|error|warning|label|text"
    r")\b",
    re.IGNORECASE,
)

_TEXTUAL_AMBIGUITY_RE = re.compile(
    r"\b(appropriate|correct|proper|reasonable|relevant|intuitive|clear|easy|simple|valid)\b",
    re.IGNORECASE,
)

_QUANTIFIER_RE = re.compile(r"\b(all|every|any|each|complete|comprehensive|always|never)\b", re.IGNORECASE)


@dataclass(frozen=True)
class RequirementUnderstandingResult:
    requirement: RequirementInput
    ui_evaluability: UIEvaluability
    claims: list[RequirementClaim]
    uncertainty_reasons: list[UncertaintyReason]
    rationale: str
    decomposition_source: str = "heuristic"


def find_hidden_indicators(text: str) -> list[str]:
    found: list[str] = []
    for label, pattern in _HIDDEN_INDICATORS:
        if pattern.search(text):
            found.append(label)
    return found


def has_hidden_indicator(text: str) -> bool:
    return bool(find_hidden_indicators(text))


def _uncertainty_reasons_for(text: str) -> list[UncertaintyReason]:
    reasons: list[UncertaintyReason] = []
    hidden_indicators = find_hidden_indicators(text)
    if hidden_indicators:
        reasons.append(UncertaintyReason.NONTRIVIAL_HIDDEN_PROPERTY)
    if any(
        indicator
        in {
            "backend",
            "database",
            "email delivery",
            "payment processing",
            "ranking correctness",
            "long-term data correctness",
            "real-world external effects",
        }
        for indicator in hidden_indicators
    ):
        reasons.append(UncertaintyReason.UNVERIFIED_SYSTEM_OUTCOME)
    if _TEXTUAL_AMBIGUITY_RE.search(text):
        reasons.append(UncertaintyReason.TEXTUAL_AMBIGUITY)
    if _QUANTIFIER_RE.search(text):
        reasons.append(UncertaintyReason.QUANTIFIER_OR_COMPLETENESS_AMBIGUITY)
    return list(dict.fromkeys(reasons))


class ClaimDecomposer(ABC):
    @abstractmethod
    def decompose_many(self, requirements: list[RequirementInput], *, max_claims: int) -> dict[str, list[str]]:
        raise NotImplementedError


class HeuristicClaimDecomposer(ClaimDecomposer):
    def decompose_many(self, requirements: list[RequirementInput], *, max_claims: int) -> dict[str, list[str]]:
        return {
            requirement.requirement_id: decompose_requirement_claim_texts(
                requirement.text,
                max_claims=max_claims,
            )
            for requirement in requirements
        }


def _build_llm_decomposition_prompt(requirements: list[RequirementInput], *, max_claims: int) -> str:
    payload = [
        {
            "requirement_id": requirement.requirement_id,
            "text": requirement.text,
        }
        for requirement in requirements
    ]
    return f"""
Decompose UI verification requirements into atomic claims.

Rules:
- Return ONLY valid JSON.
- Do not use screenshots or invent details.
- Claims must come only from each requirement text.
- Separate claims are interpreted conjunctively: every returned claim is expected to hold.
- Do not split disjunctive alternatives joined by "or" into separate claims unless the requirement explicitly requires both alternatives independently.
- Preserve "or" wording inside one claim for alternative channels, destinations, compose surfaces, or modes.
- Create 2 to {max_claims} claims when the requirement is compound.
- Use 1 claim only when the requirement is truly atomic.
- Keep each claim a short English sentence.
- Preserve hidden/non-UI properties as claims when they are present.
- Do not include evidence, labels, rationales, markdown, or explanations.

Input:
{payload}

Return this JSON shape:
{{
  "requirements": [
    {{
      "requirement_id": "REQ-1",
      "claims": ["Claim sentence one.", "Claim sentence two."]
    }}
  ]
}}
""".strip()


class GeminiClaimDecomposer(ClaimDecomposer):
    """Provider-aware text LLM fallback using the shared rule-guided claim decomposer."""

    def __init__(
        self,
        *,
        provider: str | None = None,
        model_name: str = model_name_for("claim_decomposition"),
        temperature: float = temperature_for("claim_decomposition"),
    ) -> None:
        self.provider = provider or provider_for("claim_decomposition")
        self.model_name = model_name
        self.temperature = temperature

    def decompose_many(self, requirements: list[RequirementInput], *, max_claims: int) -> dict[str, list[str]]:
        if not requirements:
            return {}

        results: dict[str, list[str]] = {}
        for requirement in requirements:
            result = decompose_requirement_with_diagnostics(
                requirement.text,
                strategy="rule_guided_llm",
                provider=self.provider,
                model_name=self.model_name,
                use_cache=True,
                max_claims=max_claims,
            )
            claims = [claim.claim_text for claim in result.claims[:max_claims] if claim.claim_text.strip()]
            if claims:
                results[requirement.requirement_id] = claims
        return results


def _parse_llm_decomposition_response(
    parsed: Any,
    requirements: list[RequirementInput],
    *,
    max_claims: int,
) -> dict[str, list[str]]:
    allowed_ids = {requirement.requirement_id for requirement in requirements}
    items = parsed.get("requirements") if isinstance(parsed, dict) else parsed
    if not isinstance(items, list):
        return {}

    results: dict[str, list[str]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        requirement_id = item.get("requirement_id")
        if requirement_id not in allowed_ids:
            continue
        claims = item.get("claims")
        if not isinstance(claims, list):
            continue
        normalized = [_normalize_claim_candidate(claim) for claim in claims]
        normalized = [claim for claim in normalized if claim]
        if normalized:
            results[str(requirement_id)] = normalized[:max_claims]
    return results


def _normalize_claim_candidate(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = " ".join(value.split()).strip(" ;,")
    if len(value) < 8:
        return None
    return value if re.search(r"[.!?]$", value) else f"{value}."


_COMPOUND_HINT_RE = re.compile(r"\b(including|and|or|with|without|so that)\b|[,;:]", re.IGNORECASE)


def _heuristic_decomposition_failed(requirement_text: str, claim_texts: list[str], *, min_claims: int) -> bool:
    if len(claim_texts) < min_claims:
        return True
    if len(claim_texts) == 1 and _COMPOUND_HINT_RE.search(requirement_text):
        return True
    if any(claim.strip().lower() == requirement_text.strip().lower() for claim in claim_texts):
        return bool(_COMPOUND_HINT_RE.search(requirement_text))
    return False


class RequirementUnderstanding:
    """Heuristic requirement analyzer with an LLM-swappable interface.

    TODO: Fine-tuning targets can later include UI evaluability classification
    and claim decomposition, while preserving this output contract.
    """

    def __init__(
        self,
        *,
        min_claims: int = 1,
        max_claims: int = 4,
        fallback_decomposer: ClaimDecomposer | None = None,
        decompose_claims: bool = True,
    ) -> None:
        if min_claims < 1:
            raise ValueError("min_claims must be >= 1")
        if max_claims < min_claims:
            raise ValueError("max_claims must be >= min_claims")
        self.min_claims = min_claims
        self.max_claims = max_claims
        self.heuristic_decomposer = HeuristicClaimDecomposer()
        self.fallback_decomposer = fallback_decomposer
        self.decompose_claims = decompose_claims

    def understand(self, requirement: RequirementInput) -> RequirementUnderstandingResult:
        return self.understand_many([requirement])[0]

    def understand_many(self, requirements: list[RequirementInput]) -> list[RequirementUnderstandingResult]:
        if not self.decompose_claims:
            return [
                self._build_result(
                    requirement,
                    [requirement.text],
                    decomposition_source="disabled",
                )
                for requirement in requirements
            ]

        heuristic_claims_by_id = self.heuristic_decomposer.decompose_many(requirements, max_claims=self.max_claims)
        claim_texts_by_id = dict(heuristic_claims_by_id)
        decomposition_source_by_id = {requirement.requirement_id: "heuristic" for requirement in requirements}

        failed_requirements = [
            requirement
            for requirement in requirements
            if _heuristic_decomposition_failed(
                requirement.text,
                heuristic_claims_by_id.get(requirement.requirement_id, []),
                min_claims=self.min_claims,
            )
        ]
        if failed_requirements and self.fallback_decomposer is not None:
            try:
                fallback_claims_by_id = self.fallback_decomposer.decompose_many(
                    failed_requirements,
                    max_claims=self.max_claims,
                )
            except Exception:
                fallback_claims_by_id = {}

            for requirement in failed_requirements:
                fallback_claims = fallback_claims_by_id.get(requirement.requirement_id, [])
                if not fallback_claims:
                    continue
                if len(fallback_claims) >= len(heuristic_claims_by_id.get(requirement.requirement_id, [])):
                    claim_texts_by_id[requirement.requirement_id] = fallback_claims
                    decomposition_source_by_id[requirement.requirement_id] = (
                        self.fallback_decomposer.__class__.__name__
                    )

        return [
            self._build_result(
                requirement,
                claim_texts_by_id.get(requirement.requirement_id, []),
                decomposition_source=decomposition_source_by_id.get(requirement.requirement_id, "heuristic"),
            )
            for requirement in requirements
        ]

    def _build_result(
        self,
        requirement: RequirementInput,
        claim_texts: list[str],
        *,
        decomposition_source: str,
    ) -> RequirementUnderstandingResult:
        ui_evaluability = self.classify_ui_evaluability(requirement.text)
        if not claim_texts:
            claim_texts = [requirement.text]

        claims: list[RequirementClaim] = []
        for index, claim_text in enumerate(claim_texts[: self.max_claims], start=1):
            hidden_indicators = find_hidden_indicators(claim_text)
            claim_reasons = _uncertainty_reasons_for(claim_text)
            claims.append(
                RequirementClaim(
                    claim_id=f"{requirement.requirement_id}-C{index}",
                    requirement_id=requirement.requirement_id,
                    claim_text=claim_text,
                    source_requirement_text=requirement.text,
                    claim_index=index,
                    is_core=True,
                    is_observable=not hidden_indicators,
                    hidden_indicators=hidden_indicators,
                    uncertainty_reasons=claim_reasons,
                )
            )

        reasons = _uncertainty_reasons_for(requirement.text)
        rationale = self._rationale(ui_evaluability, requirement.text)
        return RequirementUnderstandingResult(
            requirement=requirement,
            ui_evaluability=ui_evaluability,
            claims=claims,
            uncertainty_reasons=reasons,
            rationale=rationale,
            decomposition_source=decomposition_source,
        )

    def classify_ui_evaluability(self, text: str) -> UIEvaluability:
        hidden_indicators = find_hidden_indicators(text)
        has_visible_indicator = bool(_VISIBLE_INDICATOR_RE.search(text))
        if hidden_indicators and not has_visible_indicator:
            return UIEvaluability.NOT_UI_VERIFIABLE
        if hidden_indicators:
            return UIEvaluability.PARTIALLY_UI_VERIFIABLE
        return UIEvaluability.UI_VERIFIABLE

    @staticmethod
    def _rationale(ui_evaluability: UIEvaluability, text: str) -> str:
        hidden_indicators = find_hidden_indicators(text)
        if ui_evaluability == UIEvaluability.NOT_UI_VERIFIABLE:
            return (
                "The requirement is dominated by non-visual or hidden system properties: "
                f"{', '.join(hidden_indicators)}."
            )
        if ui_evaluability == UIEvaluability.PARTIALLY_UI_VERIFIABLE:
            return (
                "The requirement has a visible UI component, but also references hidden properties: "
                f"{', '.join(hidden_indicators)}."
            )
        return "The requirement appears checkable from visible UI evidence in the screenshot flow."
