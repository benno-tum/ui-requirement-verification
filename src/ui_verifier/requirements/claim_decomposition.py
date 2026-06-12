from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ui_verifier.model_config import model_name_for, provider_for, temperature_for


CLAIM_DECOMPOSITION_PROMPT_VERSION = "CLAIM_DECOMPOSITION_RULE_GUIDED_V1"
DEFAULT_LLM_CACHE_DIR = Path("data/generated/cache/claim_decomposition_llm")


class ClaimKind(str, Enum):
    OBSERVABLE_UI = "OBSERVABLE_UI"
    HIDDEN_SYSTEM = "HIDDEN_SYSTEM"
    MIXED = "MIXED"
    NON_UI = "NON_UI"
    UNKNOWN = "UNKNOWN"


class ClaimUIEvaluability(str, Enum):
    UI_VERIFIABLE = "UI_VERIFIABLE"
    PARTIALLY_UI_VERIFIABLE = "PARTIALLY_UI_VERIFIABLE"
    NOT_UI_VERIFIABLE = "NOT_UI_VERIFIABLE"
    UNKNOWN = "UNKNOWN"


class ClaimImportance(str, Enum):
    CORE = "CORE"
    SUPPORTING = "SUPPORTING"
    CONTEXT = "CONTEXT"


class DecompositionSource(str, Enum):
    RULE_BASED = "rule_based"
    RULE_GUIDED_LLM = "rule_guided_llm"


class DecompositionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class RequirementClaim(DecompositionModel):
    claim_text: str
    claim_kind: ClaimKind = ClaimKind.UNKNOWN
    ui_evaluability: ClaimUIEvaluability = ClaimUIEvaluability.UNKNOWN
    importance: ClaimImportance = ClaimImportance.CORE
    rationale: str | None = None

    @field_validator("claim_text")
    @classmethod
    def _normalize_claim_text_field(cls, value: str) -> str:
        value = _normalize_whitespace(value)
        if not value:
            raise ValueError("claim_text must not be empty")
        return value

    @field_validator("rationale")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = _normalize_whitespace(value)
        return value or None


class DecompositionResult(DecompositionModel):
    original_text: str
    cleaned_text: str | None = None
    claims: list[RequirementClaim] = Field(default_factory=list)
    source: DecompositionSource
    rule_based_claims: list[str] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)
    detected_patterns: list[str] = Field(default_factory=list)
    prompt_version: str | None = None
    provider: str | None = None
    model_name: str | None = None
    cache_key: str | None = None
    raw_response_path: str | None = None
    notes: str | None = None


class _LLMDecompositionOutput(DecompositionModel):
    claims: list[RequirementClaim] = Field(min_length=1, max_length=5)
    notes: str | None = None


class LLMClient(Protocol):
    def generate_json(self, prompt: str) -> str:
        ...


class DecompositionLLMError(RuntimeError):
    """Raised when strict rule-guided LLM decomposition cannot produce valid JSON."""


_ABBREVIATIONS = {
    "e.g.": "eg_PLACEHOLDER",
    "i.e.": "ie_PLACEHOLDER",
    "etc.": "etc_PLACEHOLDER",
    "Fig.": "Fig_PLACEHOLDER",
    "fig.": "fig_PLACEHOLDER",
    "No.": "No_PLACEHOLDER",
    "no.": "no_PLACEHOLDER",
    "Std.": "Std_PLACEHOLDER",
    "Mr.": "Mr_PLACEHOLDER",
    "Mrs.": "Mrs_PLACEHOLDER",
    "Dr.": "Dr_PLACEHOLDER",
}

_HIDDEN_PATTERNS = re.compile(
    r"\b("
    r"store|stored|storage|persist|persistent|database|record diagnostic|long term|"
    r"encrypt|secure|security|privacy|authenticate|authorize|permission|role|"
    r"email|sms|alert|notification|send|external|integrat|"
    r"guarantee|interoperability|runs on|available|availability|uptime|"
    r"performance|response time|accuracy|correct|audit|management"
    r")\b",
    re.IGNORECASE,
)

_SUPPORTING_PATTERNS = re.compile(
    r"^(such data includes|for example|e\.g\.|i\.e\.|including)\b",
    re.IGNORECASE,
)


def _normalize_whitespace(text: str) -> str:
    return " ".join(str(text).split()).strip()


def _strip_leading_section_label(text: str) -> str:
    text = _normalize_whitespace(text)
    text = re.sub(r"^\d+(?:\.\d+)*\s*[-.)]?\s*", "", text)

    # Many PURE excerpts start with a heading copied into the same text node,
    # e.g. "3.22 Information Clicking on Info ..." or
    # "5.4 Software Quality Attributes The application ...".
    heading_split = re.search(
        r"\b("
        r"The|A|An|Clicking|Selecting|Pressing|Users?|System|Application|"
        r"Tool|It|This|That|In|On|When|If|No"
        r")\b",
        text,
    )
    if heading_split and 0 < heading_split.start() <= 80:
        prefix = text[: heading_split.start()].strip()
        if prefix and not re.search(r"\b(shall|should|must|will|can|could|may)\b", prefix, re.IGNORECASE):
            text = text[heading_split.start() :]

    return text.strip()


def _protect_abbreviations(text: str) -> str:
    for abbreviation, placeholder in _ABBREVIATIONS.items():
        text = text.replace(abbreviation, placeholder)
    return text


def _restore_abbreviations(text: str) -> str:
    for abbreviation, placeholder in _ABBREVIATIONS.items():
        text = text.replace(placeholder, abbreviation)
    return text


def _split_sentences(text: str) -> list[str]:
    protected = _protect_abbreviations(_strip_leading_section_label(text))
    protected = re.sub(r"\s+", " ", protected)
    protected = re.sub(r"\s*;\s*(?=(?:and\s+)?(?:the|this|that|users?|system|tool|application)\b)", ". ", protected, flags=re.IGNORECASE)
    protected = re.sub(r"\s*;\s*(?=\(\d+\)\s+)", ". ", protected)

    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", protected)
    sentences = [_restore_abbreviations(part).strip(" .") for part in parts]
    return [sentence for sentence in sentences if sentence]


def _split_modal_compounds(sentence: str) -> list[str]:
    parts = re.split(
        r"\s+(?:and|but)\s+(?=(?:the\s+\w+\s+|this\s+\w+\s+|that\s+\w+\s+)?(?:shall|should|must|will|can|could|may)\b)",
        sentence,
        flags=re.IGNORECASE,
    )
    if len(parts) <= 1:
        return [sentence]

    expanded: list[str] = []
    current_subject: str | None = None
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if re.match(r"^(shall|should|must|will|can|could|may)\b", part, flags=re.IGNORECASE) and current_subject:
            part = f"{current_subject} {part}"
        subject_match = re.match(
            r"^((?:the|this|that|a|an)\s+[^,.;]{0,60}?|users?|[A-Z][A-Za-z0-9_-]+)\s+"
            r"(?:shall|should|must|will|can|could|may|is|are|provides|allows|supports|prints?|records?)\b",
            part,
            flags=re.IGNORECASE,
        )
        if subject_match:
            current_subject = subject_match.group(1)
        expanded.append(part)
    return expanded


def _split_option_objects(sentence: str) -> list[str]:
    match = re.match(
        r"(?P<prefix>.+?\b(?:select|choose|open|display|show|provide|support)\s+)"
        r"(?P<first>(?:the\s+)?[^.]+?)\s+(?:or|and)\s+"
        r"(?P<second>(?:the\s+)?[A-Z][^.]+)$",
        sentence,
        flags=re.IGNORECASE,
    )
    if not match:
        return [sentence]

    first = match.group("first").strip(" ,")
    second = match.group("second").strip(" ,")
    if "," in first or len(first.split()) > 8 or len(second.split()) > 8:
        return [sentence]

    prefix = match.group("prefix")
    return [f"{prefix}{first}", f"{prefix}{second}"]


def _split_infinitive_verb_pair(sentence: str) -> list[str]:
    match = re.match(
        r"(?P<prefix>.+?\bto\s+(?:manually\s+)?)"
        r"(?P<first>[a-z]+)\s+(?:and|or)\s+"
        r"(?P<second>[a-z]+)\s+"
        r"(?P<object>.+)$",
        sentence,
        flags=re.IGNORECASE,
    )
    if not match:
        return [sentence]

    first = match.group("first")
    second = match.group("second")
    obj = match.group("object")
    if first.lower() in {"be", "have", "do"} or second.lower() in {"be", "have", "do"}:
        return [sentence]
    if len(obj.split()) > 12:
        return [sentence]

    prefix = match.group("prefix")
    return [f"{prefix}{first} {obj}", f"{prefix}{second} {obj}"]


def _split_shared_subject_verb_pair(sentence: str) -> list[str]:
    match = re.match(
        r"(?P<subject>^(?:The|This|That|Users?|A|An)\s+[^.]{0,80}?)\s+"
        r"(?P<modal>shall|should|must|will|can|could|may)?\s*"
        r"(?P<first_verb>records?|stores?|prints?|provides?|provide|permits?|permit|allows?|supports?|sends?|opens?|presents?|requires?)\s+"
        r"(?P<first_obj>.+?)\s+(?:and|but)\s+"
        r"(?P<second_verb>records?|stores?|prints?|provides?|provide|permits?|permit|allows?|supports?|sends?|opens?|presents?|requires?)\s+"
        r"(?P<second_obj>.+)$",
        sentence,
        flags=re.IGNORECASE,
    )
    if not match:
        return [sentence]

    first_obj = match.group("first_obj").strip(" ,")
    second_obj = match.group("second_obj").strip(" ,")
    if len(first_obj.split()) > 30 or len(second_obj.split()) > 30:
        return [sentence]

    subject = match.group("subject")
    modal = f"{match.group('modal')} " if match.group("modal") else ""
    return [
        f"{subject} {modal}{match.group('first_verb')} {first_obj}",
        f"{subject} {modal}{match.group('second_verb')} {second_obj}",
    ]


def _split_purpose_clause(sentence: str) -> list[str]:
    match = re.match(
        r"(?P<obligation>.+?)\s+"
        r"(?P<link>so\s+that|so\s+(?:users?|the\s+user|customers?|shoppers?|applicants?|travelers?|visitors?|reviewers?)\s+can)\s+"
        r"(?P<purpose>.+)$",
        sentence,
        flags=re.IGNORECASE,
    )
    if not match:
        return [sentence]

    obligation = match.group("obligation").strip(" ,")
    link = match.group("link").lower()
    purpose = match.group("purpose").strip(" ,")
    if not obligation or not purpose:
        return [sentence]

    if link == "so that":
        purpose_claim = purpose
    else:
        actor_match = re.match(
            r"so\s+(?P<actor>users?|the\s+user|customers?|shoppers?|applicants?|travelers?|visitors?|reviewers?)\s+can",
            link,
        )
        actor = actor_match.group("actor") if actor_match else "users"
        purpose_claim = f"{actor.capitalize()} can {purpose}"

    return [obligation, purpose_claim]


def _split_without_requiring_clause(sentence: str) -> list[str]:
    match = re.match(
        r"(?P<obligation>.+?)\s+without\s+requiring\s+"
        r"(?P<actor>users?|the\s+user|customers?|shoppers?|applicants?|travelers?|visitors?)\s+to\s+"
        r"(?P<forbidden>.+)$",
        sentence,
        flags=re.IGNORECASE,
    )
    if not match:
        return [sentence]

    obligation = match.group("obligation").strip(" ,")
    actor = match.group("actor")
    forbidden = match.group("forbidden").strip(" ,")
    if not obligation or not forbidden:
        return [sentence]

    copula = "is" if actor.lower() == "the user" else "are"
    return [obligation, f"{actor.capitalize()} {copula} not required to {forbidden}"]


def _split_including_list(sentence: str) -> list[str]:
    match = re.match(
        r"(?P<main>.+?)\s*,?\s+including\s+(?P<items>[^.]+)$",
        sentence,
        flags=re.IGNORECASE,
    )
    if not match:
        return [sentence]

    main = match.group("main").strip(" ,")
    items_raw = match.group("items").strip(" ,")
    items = [
        re.sub(r"^(?:and|or)\s+", "", item.strip(" ,"), flags=re.IGNORECASE)
        for item in re.split(r",\s*|\s+and\s+", items_raw)
        if item.strip(" ,")
    ]
    if len(items) < 2 or len(items) > 8:
        return [sentence]

    object_match = re.search(
        r"\b(?:present|provide|display|show|expose|surface)\s+(?P<object>.+)$",
        main,
        flags=re.IGNORECASE,
    )
    if not object_match:
        return [sentence]

    object_text = object_match.group("object").strip(" ,")
    if len(object_text.split()) > 12:
        object_text = "The presented information"
    else:
        object_text = re.sub(r"^(?:a|an|the)\s+", "", object_text, flags=re.IGNORECASE)
        object_text = f"The presented {object_text}"

    return [main, *[f"{object_text} includes {item}" for item in items]]


def _split_shared_preposition_targets(sentence: str) -> list[str]:
    match = re.match(
        r"(?P<prefix>.+?\b(?:in|on|across|through|throughout)\s+)"
        r"(?P<first>(?:later\s+)?[a-z][a-z -]{1,40}?)\s+and\s+"
        r"(?P<second>[a-z][a-z -]{1,40}?)\s+"
        r"(?P<suffix>(?:screens?|pages?|views?|flows?|states?|steps?)\b.*)$",
        sentence,
        flags=re.IGNORECASE,
    )
    if not match:
        return [sentence]

    first = match.group("first").strip()
    second = match.group("second").strip()
    suffix = match.group("suffix").strip()
    if len(first.split()) > 5 or len(second.split()) > 5:
        return [sentence]

    prefix = match.group("prefix")
    return [f"{prefix}{first} {suffix}", f"{prefix}{second} {suffix}"]


def _split_sentence_into_claims(sentence: str) -> list[str]:
    queue = [sentence]
    for splitter in (
        _split_purpose_clause,
        _split_without_requiring_clause,
        _split_including_list,
        _split_modal_compounds,
        _split_infinitive_verb_pair,
        _split_shared_subject_verb_pair,
        _split_option_objects,
        _split_shared_preposition_targets,
    ):
        next_queue: list[str] = []
        for item in queue:
            next_queue.extend(splitter(item))
        queue = next_queue
    return [_normalize_whitespace(item) for item in queue if _normalize_whitespace(item)]


def _normalize_claim_text(text: str) -> str:
    claim = _normalize_whitespace(text).strip(" .,;")
    claim = re.sub(r"^[A-Za-z][A-Za-z0-9 _/-]{0,50}\s+[—-]\s+(?=\(\d+\))", "", claim)
    replacements = [
        (r"\b[Ss]hall allow users to\b", "allows users to"),
        (r"\b[Ss]hall allow the user to\b", "allows the user to"),
        (r"\b[Ss]hall allow ([a-z][a-z -]{1,40}) to\b", r"allows \1 to"),
        (r"\b[Mm]ust allow users to\b", "allows users to"),
        (r"\b[Mm]ust allow the user to\b", "allows the user to"),
        (r"\b[Mm]ust allow ([a-z][a-z -]{1,40}) to\b", r"allows \1 to"),
        (r"\b[Ss]hould allow users to\b", "allows users to"),
        (r"\b[Ss]hould allow the user to\b", "allows the user to"),
        (r"\b[Ss]hould allow ([a-z][a-z -]{1,40}) to\b", r"allows \1 to"),
        (r"\b[Ss]hall provide\b", "provides"),
        (r"\b[Mm]ust provide\b", "provides"),
        (r"\b[Ss]hould provide\b", "provides"),
        (r"\b[Ss]hall permit\b", "permits"),
        (r"\b[Mm]ust permit\b", "permits"),
        (r"\b[Ss]hould permit\b", "permits"),
        (r"\b[Ss]hall support\b", "supports"),
        (r"\b[Mm]ust support\b", "supports"),
        (r"\b[Ss]hould support\b", "supports"),
        (r"\b[Ss]hall retain\b", "retains"),
        (r"\b[Mm]ust retain\b", "retains"),
        (r"\b[Ss]hould retain\b", "retains"),
        (r"\b[Ss]hall preserve\b", "preserves"),
        (r"\b[Mm]ust preserve\b", "preserves"),
        (r"\b[Ss]hould preserve\b", "preserves"),
        (r"\b[Ss]hall maintain\b", "maintains"),
        (r"\b[Mm]ust maintain\b", "maintains"),
        (r"\b[Ss]hould maintain\b", "maintains"),
        (r"\b[Ss]hall keep\b", "keeps"),
        (r"\b[Mm]ust keep\b", "keeps"),
        (r"\b[Ss]hould keep\b", "keeps"),
        (r"\b[Ss]hall carry\b", "carries"),
        (r"\b[Mm]ust carry\b", "carries"),
        (r"\b[Ss]hould carry\b", "carries"),
        (r"\b[Ss]hall organize\b", "organizes"),
        (r"\b[Mm]ust organize\b", "organizes"),
        (r"\b[Ss]hould organize\b", "organizes"),
        (r"\b[Ss]hall expose\b", "exposes"),
        (r"\b[Mm]ust expose\b", "exposes"),
        (r"\b[Ss]hould expose\b", "exposes"),
        (r"\b[Ss]hall present\b", "presents"),
        (r"\b[Mm]ust present\b", "presents"),
        (r"\b[Ss]hould present\b", "presents"),
        (r"\b[Ss]hall surface\b", "surfaces"),
        (r"\b[Mm]ust surface\b", "surfaces"),
        (r"\b[Ss]hould surface\b", "surfaces"),
        (r"\b[Ss]hall make\b", "makes"),
        (r"\b[Mm]ust make\b", "makes"),
        (r"\b[Ss]hould make\b", "makes"),
        (r"\b[Ss]hall display\b", "displays"),
        (r"\b[Mm]ust display\b", "displays"),
        (r"\b[Ss]hould display\b", "displays"),
        (r"\b[Ss]hall be able to\b", "is able to"),
        (r"\b[Mm]ust be able to\b", "is able to"),
        (r"\b[Ss]hould be able to\b", "is able to"),
        (r"\b[Ss]hall have the capability to\b", "has the capability to"),
        (r"\b[Mm]ust have the capability to\b", "has the capability to"),
        (r"\b[Ss]hould have the capability to\b", "has the capability to"),
        (r"\b[Ss]hall be stored\b", "is stored"),
        (r"\b[Mm]ust be stored\b", "is stored"),
        (r"\b[Ss]hould be stored\b", "is stored"),
        (r"\b[Ss]hall require\b", "requires"),
        (r"\b[Mm]ust require\b", "requires"),
        (r"\b[Ss]hould require\b", "requires"),
        (r"\b[Ss]hall print\b", "prints"),
        (r"\b[Mm]ust print\b", "prints"),
        (r"\b[Ss]hould print\b", "prints"),
        (r"\b[Ww]ill record\b", "records"),
        (r"\b[Ww]ill provide\b", "provides"),
        (r"\b[Yy]ou quit\b", "Users can quit"),
        (r"\byou with\b", "users with"),
    ]
    for pattern, replacement in replacements:
        claim = re.sub(pattern, replacement, claim)
    claim = claim[:1].upper() + claim[1:] if claim else claim
    return claim if re.search(r"[.!?]$", claim) else f"{claim}."


def _claim_type_for(text: str) -> tuple[str, str, str]:
    if _HIDDEN_PATTERNS.search(text):
        return "HIDDEN", "HIDDEN_CORE", "HIDDEN"
    if _SUPPORTING_PATTERNS.search(text):
        return "OBSERVABLE", "SUPPORTING_CONTEXT", "MISSING"
    return "OBSERVABLE", "OBSERVABLE_CORE", "MISSING"


def _dedupe_claims(claims: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for claim in claims:
        key = re.sub(r"[^a-z0-9]+", " ", claim.lower()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(claim)
    return deduped


def decompose_requirement_claim_texts(requirement_text: str, *, max_claims: int = 8) -> list[str]:
    """Create draft atomic claim texts from a requirement without using evidence."""
    sentences = _split_sentences(requirement_text)
    raw_claims: list[str] = []
    for sentence in sentences:
        raw_claims.extend(_split_sentence_into_claims(sentence))

    claims = [_normalize_claim_text(claim) for claim in raw_claims]
    claims = [claim for claim in claims if len(claim) >= 12]
    claims = _dedupe_claims(claims)
    if not claims:
        claims = [_normalize_claim_text(_strip_leading_section_label(requirement_text))]
    return claims[:max_claims]


def build_requirement_claims(
    requirement_text: str,
    requirement_id: str,
    *,
    max_claims: int = 8,
    include_evidence_steps: bool = False,
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for idx, claim_text in enumerate(
        decompose_requirement_claim_texts(requirement_text, max_claims=max_claims),
        start=1,
    ):
        claim_type, claim_kind, status = _claim_type_for(claim_text)
        claim: dict[str, Any] = {
            "claim_id": f"{requirement_id}-C{idx}",
            "claim": claim_text,
            "claim_text": claim_text,
            "claim_kind": claim_kind,
            "claim_type": claim_type,
            "importance": "SUPPORTING" if claim_kind == "SUPPORTING_CONTEXT" else "CORE",
            "status": status,
            "source": "requirement_decomposition",
        }
        if include_evidence_steps:
            claim["evidence_steps"] = []
        claims.append(claim)
    return claims


def decompose_requirement(requirement_text: str, *, max_claims: int = 8) -> list[str]:
    """Backward-compatible alias for draft claim decomposition."""
    return decompose_requirement_claim_texts(requirement_text, max_claims=max_claims)


_QUALITY_FLAGS = {
    "COPIED_ORIGINAL",
    "LONG_SINGLE_CLAIM",
    "BAD_GRAMMAR_FRAGMENT",
    "UNSPLIT_MARKER",
    "HIDDEN_VISIBLE_MIX",
    "DOCUMENT_HEADING_PREFIX",
    "NON_UI_CONSTRAINT",
    "TABLE_OR_LIST_LIKE_TEXT",
    "RULE_OUTPUT_USED",
    "LLM_USED",
    "LLM_PARSE_ERROR",
    "LLM_UNAVAILABLE",
    "LLM_SCHEMA_INVALID",
}

_PATTERN_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("WHILE_REQUIRING", re.compile(r"\bwhile\s+requiring\b", re.IGNORECASE)),
    ("AND_IMMEDIATELY_REFRESH", re.compile(r"\band\s+immediately\s+refresh", re.IGNORECASE)),
    ("PERFORM_AND_PRESENT", re.compile(r"\bperform\b.+\band\s+present\b", re.IGNORECASE)),
    (
        "SEND_CONFIRMATION_THAT_SUMMARIZES",
        re.compile(r"\bsend\s+a?\s*confirmation\b.+\bthat\s+summari[sz]es\b", re.IGNORECASE),
    ),
    ("INCLUDING_LIST", re.compile(r"\bincluding\s+[^.]+(?:,|\band\b)", re.IGNORECASE)),
    ("REVIEW_AND_CONSENT", re.compile(r"\breview\s+and\s+consent\b", re.IGNORECASE)),
    (
        "HIDDEN_SYSTEM_VERB",
        re.compile(
            r"\b(send|email|confirmation delivery|payment processing|approval check|financing check|"
            r"enforce|eligibility|database|backend|security|encryption|persistence|long-term correctness)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "VISIBLE_UI_VERB",
        re.compile(
            r"\b(show|display|present|indicate|visible|feedback|message|page|view|screen|selected|active state)\b",
            re.IGNORECASE,
        ),
    ),
    ("DOCUMENT_HEADING", re.compile(r"^\s*\d+(?:\.\d+)*\s+[A-Z][A-Za-z ]{2,60}\s+(?=The|A|An|Users?|System|Application|Clicking|Selecting)", re.IGNORECASE)),
    ("TABLE_LIKE_LIST", re.compile(r"(?:\|\s*\w|\t|^\s*(?:[-*]|\d+[.)])\s+)", re.IGNORECASE | re.MULTILINE)),
]

_BAD_GRAMMAR_PATTERNS: list[re.Pattern[str]] = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bshall\s+presents\b",
        r"\bshall\s+allows\b",
        r"\busers\s+is\s+able\b",
        r"\breview\s+to\b",
        r"\bdisplay\s+information\s+about\s+monthly\b",
    )
]

_UNSPLIT_MARKERS = [
    "while requiring",
    "so that",
    "so users can",
    "including",
    "and immediately",
    "and present",
    "and provide",
    "and display",
    "and show",
]

_HIDDEN_INDICATORS = [
    "send",
    "email",
    "confirmation delivery",
    "payment processing",
    "approval check",
    "financing check",
    "enforce",
    "eligibility",
    "database",
    "backend",
    "security",
    "encryption",
    "persistence",
    "long-term correctness",
]

_VISIBLE_UI_INDICATORS = [
    "show",
    "display",
    "present",
    "indicate",
    "visible",
    "feedback",
    "message",
    "page",
    "view",
    "screen",
    "selected",
    "active state",
]

_NON_UI_INDICATORS = [
    "legal",
    "license",
    "architecture",
    "security",
    "database",
    "performance",
    "backend",
    "encryption",
]


def detect_textual_patterns(requirement_text: str) -> list[str]:
    text = _normalize_whitespace(requirement_text)
    return [name for name, pattern in _PATTERN_RULES if pattern.search(text)]


def analyze_rule_decomposition(
    original_text: str,
    rule_based_claims: list[str],
    *,
    cleaned_text: str | None = None,
) -> tuple[list[str], list[str]]:
    flags: list[str] = ["RULE_OUTPUT_USED"]
    detected_patterns = detect_textual_patterns(original_text)
    original_norm = _normalized_cache_text(original_text)
    cleaned_norm = _normalized_cache_text(cleaned_text or original_text)

    if cleaned_norm and cleaned_norm != original_norm:
        flags.append("DOCUMENT_HEADING_PREFIX")
    if "TABLE_LIKE_LIST" in detected_patterns:
        flags.append("TABLE_OR_LIST_LIKE_TEXT")
    if len(rule_based_claims) == 1:
        claim_norm = _normalized_cache_text(rule_based_claims[0])
        if claim_norm == original_norm or claim_norm == cleaned_norm:
            flags.append("COPIED_ORIGINAL")
        if len(original_text.split()) >= 22:
            flags.append("LONG_SINGLE_CLAIM")

    joined_claims = " ".join(rule_based_claims)
    if any(pattern.search(joined_claims) for pattern in _BAD_GRAMMAR_PATTERNS):
        flags.append("BAD_GRAMMAR_FRAGMENT")

    original_l = f" {original_text.lower()} "
    if any(marker in original_l for marker in _UNSPLIT_MARKERS) and len(rule_based_claims) <= 1:
        flags.append("UNSPLIT_MARKER")

    has_hidden = _contains_any(original_text, _HIDDEN_INDICATORS)
    has_visible = _contains_any(original_text, _VISIBLE_UI_INDICATORS)
    if has_hidden and has_visible:
        flags.append("HIDDEN_VISIBLE_MIX")
    if _contains_any(original_text, _NON_UI_INDICATORS):
        flags.append("NON_UI_CONSTRAINT")

    return _dedupe_strings(flags), _dedupe_strings(detected_patterns)


def classify_claim_for_ui(claim_text: str) -> RequirementClaim:
    has_hidden = _contains_any(claim_text, _HIDDEN_INDICATORS)
    has_visible = _contains_any(claim_text, _VISIBLE_UI_INDICATORS)
    has_non_ui = _contains_any(claim_text, _NON_UI_INDICATORS)
    if has_hidden and has_visible:
        kind = ClaimKind.MIXED
        evaluability = ClaimUIEvaluability.PARTIALLY_UI_VERIFIABLE
    elif has_visible:
        kind = ClaimKind.OBSERVABLE_UI
        evaluability = ClaimUIEvaluability.UI_VERIFIABLE
    elif has_non_ui:
        kind = ClaimKind.NON_UI
        evaluability = ClaimUIEvaluability.NOT_UI_VERIFIABLE
    elif has_hidden:
        kind = ClaimKind.HIDDEN_SYSTEM
        evaluability = ClaimUIEvaluability.NOT_UI_VERIFIABLE
    else:
        kind = ClaimKind.UNKNOWN
        evaluability = ClaimUIEvaluability.UNKNOWN
    importance = ClaimImportance.SUPPORTING if _SUPPORTING_PATTERNS.search(claim_text) else ClaimImportance.CORE
    return RequirementClaim(
        claim_text=claim_text,
        claim_kind=kind,
        ui_evaluability=evaluability,
        importance=importance,
    )


class ConfiguredTextLLMClient:
    def __init__(
        self,
        *,
        role: str = "claim_decomposition",
        provider: str | None = None,
        model_name: str = model_name_for("claim_decomposition"),
        temperature: float = temperature_for("claim_decomposition"),
    ) -> None:
        self.role = role
        self.provider = provider or provider_for(role)
        self.model_name = model_name
        self.temperature = temperature

    def generate_json(self, prompt: str) -> str:
        from ui_verifier.requirements.llm_client import run_text_json_llm

        return run_text_json_llm(
            prompt,
            role=self.role,
            provider=self.provider,
            model_name=self.model_name,
            temperature=self.temperature,
        )


GeminiLLMClient = ConfiguredTextLLMClient


class FakeLLMClient:
    def __init__(self, responses: list[str] | str, *, model_name: str = "fake-llm") -> None:
        self.responses = [responses] if isinstance(responses, str) else list(responses)
        self.model_name = model_name
        self.prompts: list[str] = []

    def generate_json(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.responses:
            raise RuntimeError("FakeLLMClient has no remaining responses")
        if len(self.responses) == 1:
            return self.responses[0]
        return self.responses.pop(0)


class RuleGuidedLLMClaimDecomposer:
    def __init__(
        self,
        llm_client: LLMClient | None = None,
        *,
        model_name: str | None = None,
        provider: str | None = None,
        cache_dir: Path | str = DEFAULT_LLM_CACHE_DIR,
        use_cache: bool = True,
        strict: bool = False,
        max_claims: int = 8,
    ) -> None:
        self.model_name = model_name or getattr(llm_client, "model_name", None) or model_name_for("claim_decomposition")
        self.provider = provider or getattr(llm_client, "provider", None) or provider_for("claim_decomposition")
        self.llm_client = llm_client or ConfiguredTextLLMClient(provider=self.provider, model_name=self.model_name)
        self.cache_dir = Path(cache_dir)
        self.use_cache = use_cache
        self.strict = strict
        self.max_claims = max_claims

    def decompose(self, requirement_text: str) -> DecompositionResult:
        original_text = _normalize_whitespace(requirement_text)
        cleaned_text = _strip_leading_section_label(original_text)
        rule_based_claims = decompose_requirement_claim_texts(original_text, max_claims=self.max_claims)
        quality_flags, detected_patterns = analyze_rule_decomposition(
            original_text,
            rule_based_claims,
            cleaned_text=cleaned_text,
        )
        cache_key = _cache_key(
            prompt_version=CLAIM_DECOMPOSITION_PROMPT_VERSION,
            model_name=self.model_name,
            original_text=original_text,
            rule_based_claims=rule_based_claims,
            quality_flags=quality_flags,
            detected_patterns=detected_patterns,
        )
        cache_path = self.cache_dir / f"{cache_key}.json"
        if self.use_cache and cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            parsed_result = cached.get("parsed_result")
            if isinstance(parsed_result, dict):
                result = DecompositionResult.model_validate(parsed_result)
                result.raw_response_path = str(cache_path)
                return result

        input_payload = {
            "original_text": original_text,
            "cleaned_text": cleaned_text,
            "rule_based_claims": rule_based_claims,
            "quality_flags": quality_flags,
            "detected_patterns": detected_patterns,
        }
        prompt = _build_rule_guided_prompt(input_payload)
        try:
            raw_response = self.llm_client.generate_json(prompt)
        except Exception as exc:
            if self.strict:
                raise DecompositionLLMError(f"LLM decomposition unavailable: {exc}") from exc
            return _fallback_decomposition_result(
                original_text=original_text,
                cleaned_text=cleaned_text,
                rule_based_claims=rule_based_claims,
                quality_flags=[*quality_flags, "LLM_UNAVAILABLE"],
                detected_patterns=detected_patterns,
                model_name=self.model_name,
                provider=self.provider,
                cache_key=cache_key,
                notes=str(exc),
            )

        try:
            parsed = _parse_llm_decomposition(raw_response)
        except Exception as first_exc:
            repair_prompt = _build_repair_prompt(prompt, raw_response, first_exc)
            try:
                raw_response = self.llm_client.generate_json(repair_prompt)
                parsed = _parse_llm_decomposition(raw_response)
            except Exception as second_exc:
                if self.strict:
                    raise DecompositionLLMError(f"LLM decomposition returned invalid JSON: {second_exc}") from second_exc
                error_flag = "LLM_SCHEMA_INVALID" if isinstance(second_exc, ValidationError) else "LLM_PARSE_ERROR"
                return _fallback_decomposition_result(
                    original_text=original_text,
                    cleaned_text=cleaned_text,
                    rule_based_claims=rule_based_claims,
                    quality_flags=[*quality_flags, error_flag],
                    detected_patterns=detected_patterns,
                    model_name=self.model_name,
                    provider=self.provider,
                    cache_key=cache_key,
                    notes=str(second_exc),
                )

        result = DecompositionResult(
            original_text=original_text,
            cleaned_text=cleaned_text,
            claims=parsed.claims,
            source=DecompositionSource.RULE_GUIDED_LLM,
            rule_based_claims=rule_based_claims,
            quality_flags=_dedupe_strings([*quality_flags, "LLM_USED"]),
            detected_patterns=detected_patterns,
            prompt_version=CLAIM_DECOMPOSITION_PROMPT_VERSION,
            provider=self.provider,
            model_name=self.model_name,
            cache_key=cache_key,
            raw_response_path=str(cache_path) if self.use_cache else None,
            notes=parsed.notes,
        )
        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_content = {
                "original_text": original_text,
                "cleaned_text": cleaned_text,
                "rule_based_claims": rule_based_claims,
                "quality_flags": result.quality_flags,
                "detected_patterns": detected_patterns,
                "prompt_version": CLAIM_DECOMPOSITION_PROMPT_VERSION,
                "provider": self.provider,
                "model_name": self.model_name,
                "raw_response": raw_response,
                "parsed_result": result.model_dump(mode="json"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            cache_path.write_text(json.dumps(cache_content, indent=2, ensure_ascii=False), encoding="utf-8")
        return result


def decompose_requirement_with_diagnostics(
    requirement_text: str,
    *,
    strategy: str = "rule_guided_llm",
    llm_client: LLMClient | None = None,
    model_name: str | None = None,
    provider: str | None = None,
    use_cache: bool = True,
    cache_dir: Path | str = DEFAULT_LLM_CACHE_DIR,
    strict: bool = False,
    max_claims: int = 8,
) -> DecompositionResult:
    if strategy == "rule_based":
        original_text = _normalize_whitespace(requirement_text)
        cleaned_text = _strip_leading_section_label(original_text)
        rule_based_claims = decompose_requirement_claim_texts(original_text, max_claims=max_claims)
        quality_flags, detected_patterns = analyze_rule_decomposition(
            original_text,
            rule_based_claims,
            cleaned_text=cleaned_text,
        )
        return DecompositionResult(
            original_text=original_text,
            cleaned_text=cleaned_text,
            claims=[classify_claim_for_ui(claim) for claim in rule_based_claims],
            source=DecompositionSource.RULE_BASED,
            rule_based_claims=rule_based_claims,
            quality_flags=quality_flags,
            detected_patterns=detected_patterns,
        )
    if strategy != "rule_guided_llm":
        raise ValueError(f"Unsupported claim decomposition strategy: {strategy}")
    return RuleGuidedLLMClaimDecomposer(
        llm_client,
        model_name=model_name,
        provider=provider,
        cache_dir=cache_dir,
        use_cache=use_cache,
        strict=strict,
        max_claims=max_claims,
    ).decompose(requirement_text)


def _fallback_decomposition_result(
    *,
    original_text: str,
    cleaned_text: str | None,
    rule_based_claims: list[str],
    quality_flags: list[str],
    detected_patterns: list[str],
    model_name: str,
    cache_key: str,
    notes: str | None,
    provider: str | None = None,
) -> DecompositionResult:
    return DecompositionResult(
        original_text=original_text,
        cleaned_text=cleaned_text,
        claims=[classify_claim_for_ui(claim) for claim in rule_based_claims],
        source=DecompositionSource.RULE_GUIDED_LLM,
        rule_based_claims=rule_based_claims,
        quality_flags=_dedupe_strings(quality_flags),
        detected_patterns=detected_patterns,
        prompt_version=CLAIM_DECOMPOSITION_PROMPT_VERSION,
        provider=provider,
        model_name=model_name,
        cache_key=cache_key,
        notes=notes,
    )


def _parse_llm_decomposition(raw_response: str) -> _LLMDecompositionOutput:
    text = raw_response.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("LLM response did not contain a JSON object")
    data = json.loads(text[start : end + 1])
    return _LLMDecompositionOutput.model_validate(data)


def _build_rule_guided_prompt(input_payload: dict[str, Any]) -> str:
    input_json = json.dumps(input_payload, indent=2, ensure_ascii=False)
    return f"""You are decomposing UI requirements into atomic verification claims.
Prompt version: {CLAIM_DECOMPOSITION_PROMPT_VERSION}

Return JSON only. The response must match:
{{
  "claims": [
    {{
      "claim_text": "...",
      "claim_kind": "OBSERVABLE_UI | HIDDEN_SYSTEM | MIXED | NON_UI | UNKNOWN",
      "ui_evaluability": "UI_VERIFIABLE | PARTIALLY_UI_VERIFIABLE | NOT_UI_VERIFIABLE | UNKNOWN",
      "importance": "CORE | SUPPORTING | CONTEXT",
      "rationale": "optional short reason"
    }}
  ],
  "notes": "optional short note"
}}

Instructions:
- Decompose the requirement into 1 to 5 atomic claims.
- Use only information contained in the requirement text.
- Do not invent UI behavior.
- Do not add screenshot evidence.
- Do not decide final verification labels.
- Make every claim grammatical and self-contained.
- Separate claims are conjunctive: every returned claim is expected to hold.
- Do not split alternatives joined by "or" into separate core claims unless the requirement explicitly requires both alternatives independently.
- Preserve "or" wording inside one claim for alternative channels, destinations, compose surfaces, or modes.
- Separate observable UI claims from hidden/backend/system/policy claims.
- Preserve hidden claims but mark them correctly.
- Split mixed visible/hidden requirements when possible.
- Avoid over-splitting simple atomic requirements.
- Remove document heading prefixes from claim text when they are only headings.
- Mark non-UI implementation, legal, architecture, security, database, performance, or license constraints as NON_UI or HIDDEN_SYSTEM and NOT_UI_VERIFIABLE.

Examples:
Input: "The system shall perform any required financing or approval check before finalizing a flexible payment agreement and present the resulting status to the user."
Output claims:
- The system performs any required financing or approval check before finalizing a flexible payment agreement. | HIDDEN_SYSTEM | NOT_UI_VERIFIABLE | CORE
- The UI presents the resulting financing or approval status to the user. | OBSERVABLE_UI | UI_VERIFIABLE | CORE

Input: "The system shall allow public browsing of job listings and posting details, while requiring applicant authentication before entering the application workflow."
Output claims:
- The UI allows public browsing of job listings and posting details. | OBSERVABLE_UI | UI_VERIFIABLE | CORE
- The system requires applicant authentication before entering the application workflow. | MIXED | PARTIALLY_UI_VERIFIABLE | CORE

Input: "The system shall let users remove individual active search or filter criteria directly from the results view and immediately refresh the matching job set."
Output claims:
- The UI lets users remove individual active search or filter criteria directly from the results view. | OBSERVABLE_UI | UI_VERIFIABLE | CORE
- The matching job set refreshes after an active search or filter criterion is removed. | OBSERVABLE_UI | UI_VERIFIABLE | CORE

Input: "The system shall send a confirmation to the purchaser's contact address after checkout that summarizes the selected park, pass tier, add-ons, and payment arrangement."
Output claims:
- The system sends a confirmation to the purchaser's contact address after checkout. | HIDDEN_SYSTEM | NOT_UI_VERIFIABLE | CORE
- The confirmation summarizes the selected park, pass tier, add-ons, and payment arrangement. | HIDDEN_SYSTEM | NOT_UI_VERIFIABLE | CORE

Input: "The system shall show complete store detail coverage for each returned location, including address, phone contact, and operating hours."
Output claims:
- The UI shows address information for each returned location. | OBSERVABLE_UI | UI_VERIFIABLE | CORE
- The UI shows phone contact information for each returned location. | OBSERVABLE_UI | UI_VERIFIABLE | CORE
- The UI shows operating hours for each returned location. | OBSERVABLE_UI | UI_VERIFIABLE | CORE

Rule-guided input:
{input_json}
"""


def _build_repair_prompt(original_prompt: str, raw_response: str, error: Exception) -> str:
    return (
        f"{original_prompt}\n\n"
        "The previous response was invalid. Return only one valid JSON object matching the schema. "
        f"Validation/parsing error: {error}\n"
        f"Previous response:\n{raw_response}"
    )


def _cache_key(
    *,
    prompt_version: str,
    model_name: str,
    original_text: str,
    rule_based_claims: list[str],
    quality_flags: list[str],
    detected_patterns: list[str],
) -> str:
    payload = {
        "prompt_version": prompt_version,
        "model_name": model_name,
        "original_text": _normalized_cache_text(original_text),
        "rule_based_claims_hash": _hash_json(rule_based_claims),
        "quality_flags_hash": _hash_json(sorted(quality_flags)),
        "detected_patterns_hash": _hash_json(sorted(detected_patterns)),
    }
    return _hash_json(payload)


def _hash_json(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalized_cache_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _normalize_whitespace(text).lower()).strip()


def _contains_any(text: str, indicators: list[str]) -> bool:
    text_l = text.lower()
    return any(indicator in text_l for indicator in indicators)


def _dedupe_strings(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in _QUALITY_FLAGS and value not in {name for name, _ in _PATTERN_RULES}:
            pass
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped
