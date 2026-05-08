from __future__ import annotations

import re
from typing import Any


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


def _split_sentence_into_claims(sentence: str) -> list[str]:
    queue = [sentence]
    for splitter in (
        _split_modal_compounds,
        _split_infinitive_verb_pair,
        _split_shared_subject_verb_pair,
        _split_option_objects,
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
