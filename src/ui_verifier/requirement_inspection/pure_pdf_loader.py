from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

from ui_verifier.requirement_inspection.pure_schemas import (
    PureExtractionMode,
    PureRequirementCandidate,
    PureSourceFormat,
)


_FEATURE_RE = re.compile(r"^(3\.[1-9])\s+(System Feature\s+\d+\s*-\s*.+)$", re.IGNORECASE)
_GUI_SECTION_RE = re.compile(r"^(4\.1)\s+(User Interfaces\s*-\s*GUI)$", re.IGNORECASE)
_SUBSECTION_RE = re.compile(r"^(3\.[1-9]\.[1-3])\s+(.+)$")
_EXPLICIT_REQ_RE = re.compile(r"^REQ-(\d+)\s*:\s*(.*)$", re.IGNORECASE)
_SRS_NUMBERED_REQ_RE = re.compile(r"^(\d{4})\s+(.+)$")
_GENERIC_SECTION_RE = re.compile(r"^([1-6](?:\.\d+){0,2})\s+(.+)$")
_NUMBERED_SECTION_RE = re.compile(r"^(\d+(?:\.\d+){1,2})\s+(.+)$")
_TOP_LEVEL_SECTION_RE = re.compile(r"^([4-6]\.\d+)\s+(.+)$")
_PAGE_HEADER_RE = re.compile(
    r"^Software Requirements Specification for PDF Split and Merge(?:\s+Page\s+\d+)?$",
    re.IGNORECASE,
)
_CAPABILITY_RE = re.compile(
    r"\b("
    r"users? (?:can|may|must|should|has to|have to|selects?|presses?|sets?|writes?|is allowed to)|"
    r"allows? (?:the )?user|provides?|displays?|shows?|enables?|supports?|loads?|includes?|"
    r"has the ability|have the ability|can be accessed|consists of the following"
    r")\b",
    re.IGNORECASE,
)
_BULLET_RE = re.compile(r"^[\u2022\u2212\u00d8\u27a2\-]+\s*")


@dataclass(frozen=True)
class PurePdfPage:
    page_number: int
    text: str


def _normalize_text(text: str) -> str:
    return " ".join(text.split()).strip()


def _clean_line(line: str) -> str:
    line = _normalize_text(line)
    if _PAGE_HEADER_RE.match(line):
        return ""
    if re.fullmatch(r"Page\s+\d+", line, flags=re.IGNORECASE):
        return ""
    return line


def extract_pdf_pages(path: Path) -> list[PurePdfPage]:
    """Extract page-aware text lazily so XML-only users do not need PDF dependencies."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - depends on the runtime installation.
        raise RuntimeError(
            "PURE PDF extraction requires pypdf. Install the project's PDF dependencies first."
        ) from exc

    reader = PdfReader(str(path))
    return [
        PurePdfPage(page_number=index, text=page.extract_text() or "")
        for index, page in enumerate(reader.pages, start=1)
    ]


def _iter_lines(pages: Iterable[PurePdfPage]) -> Iterable[tuple[int, str]]:
    for page in pages:
        for raw_line in page.text.splitlines():
            line = _clean_line(raw_line)
            if line:
                yield page.page_number, line


def _candidate(
    *,
    doc_id: str,
    source_file: str,
    feature_number: str,
    feature_title: str,
    subsection_number: str,
    subsection_title: str,
    page_number: int,
    local_label: str,
    requirement_text: str,
    extraction_mode: PureExtractionMode,
    ordinal: int,
) -> PureRequirementCandidate:
    mode_token = "req" if extraction_mode == PureExtractionMode.EXPLICIT_REQ else "fallback"
    scoped_label = local_label.lower().replace(" ", "-")
    node_id = f"page.{page_number:03d}.section.{feature_number}.{mode_token}.{ordinal:03d}"
    candidate_id = f"{doc_id}::{feature_number}::{scoped_label}"
    breadcrumb = (
        f"{feature_number} {feature_title}",
        f"{subsection_number} {subsection_title}",
    )
    return PureRequirementCandidate(
        doc_id=doc_id,
        candidate_id=candidate_id,
        source_node_id=node_id,
        requirement_text=_normalize_text(requirement_text),
        extraction_mode=extraction_mode,
        source_format=PureSourceFormat.PDF,
        breadcrumb=breadcrumb,
        section_title=f"{subsection_number} {subsection_title}",
        parent_section_title=f"{feature_number} {feature_title}",
        local_label=local_label,
        context_required=True,
        context_scope="pdf_page_and_section",
        context_text=(
            f"{source_file}, PDF page {page_number}; "
            f"{feature_number} {feature_title} > {subsection_number} {subsection_title}"
        ),
        supporting_node_ids=(node_id, f"page.{page_number:03d}", f"section.{feature_number}"),
    )


def _explicit_candidates(
    *,
    pages: list[PurePdfPage],
    doc_id: str,
    source_file: str,
) -> list[PureRequirementCandidate]:
    lines = list(_iter_lines(pages))
    candidates: list[PureRequirementCandidate] = []
    feature_number = ""
    feature_title = ""
    subsection_number = ""
    subsection_title = ""
    index = 0

    while index < len(lines):
        page_number, line = lines[index]
        feature_match = _FEATURE_RE.match(line)
        if feature_match:
            feature_number, feature_title = feature_match.groups()
            subsection_number = ""
            subsection_title = ""
            index += 1
            continue

        if _GUI_SECTION_RE.match(line):
            feature_number = ""
            feature_title = ""
            subsection_number = ""
            subsection_title = ""
            index += 1
            continue

        subsection_match = _SUBSECTION_RE.match(line)
        if subsection_match:
            subsection_number, subsection_title = subsection_match.groups()
            index += 1
            continue

        req_match = _EXPLICIT_REQ_RE.match(line)
        if not req_match or not feature_number or not subsection_number.endswith(".3"):
            index += 1
            continue

        req_number, first_text = req_match.groups()
        parts = [first_text] if first_text else []
        cursor = index + 1
        while cursor < len(lines):
            _, next_line = lines[cursor]
            if _EXPLICIT_REQ_RE.match(next_line) or _NUMBERED_SECTION_RE.match(next_line):
                break
            parts.append(next_line)
            cursor += 1
        requirement_text = _normalize_text(" ".join(parts))
        if requirement_text and requirement_text.upper() != "N/A":
            candidates.append(
                _candidate(
                    doc_id=doc_id,
                    source_file=source_file,
                    feature_number=feature_number,
                    feature_title=feature_title,
                    subsection_number=subsection_number,
                    subsection_title=subsection_title,
                    page_number=page_number,
                    local_label=f"{subsection_number}/REQ-{req_number}",
                    requirement_text=requirement_text,
                    extraction_mode=PureExtractionMode.EXPLICIT_REQ,
                    ordinal=int(req_number),
                )
            )
        index = cursor

    return candidates


def _normalize_wrapped_requirement(parts: list[str]) -> str:
    text = " ".join(parts)
    text = re.sub(r"(?<=\w)-\s+(?=\w)", "", text)
    text = re.sub(r"\s+Priority\s+[1-4]\s*$", "", text, flags=re.IGNORECASE)
    return _normalize_text(text)


def _numbered_srs_candidates(
    *,
    pages: list[PurePdfPage],
    doc_id: str,
    source_file: str,
) -> list[PureRequirementCandidate]:
    """Extract four-digit SRS statements such as Mashboot's 0100-0680 records."""
    lines = list(_iter_lines(pages))
    section_titles: dict[str, str] = {}
    current_section = ""
    candidates: list[PureRequirementCandidate] = []
    index = 0

    while index < len(lines):
        page_number, line = lines[index]
        section_match = _GENERIC_SECTION_RE.match(line)
        if section_match and not _SRS_NUMBERED_REQ_RE.match(line):
            current_section, title = section_match.groups()
            section_titles[current_section] = title
            index += 1
            continue

        requirement_match = _SRS_NUMBERED_REQ_RE.match(line)
        if not requirement_match or not current_section.startswith("3"):
            index += 1
            continue

        requirement_number, first_text = requirement_match.groups()
        parts = [first_text]
        cursor = index + 1
        while cursor < len(lines):
            _, next_line = lines[cursor]
            if _SRS_NUMBERED_REQ_RE.match(next_line) or _GENERIC_SECTION_RE.match(next_line):
                break
            if re.fullmatch(r"\d{1,2}", next_line):
                cursor += 1
                continue
            parts.append(next_line)
            cursor += 1

        requirement_text = _normalize_wrapped_requirement(parts)
        if requirement_text:
            section_parts = current_section.split(".")
            if len(section_parts) >= 3:
                feature_number = ".".join(section_parts[:2])
                subsection_number = current_section
            else:
                feature_number = current_section
                subsection_number = current_section
            feature_title = section_titles.get(feature_number, section_titles.get(current_section, "Requirements"))
            subsection_title = section_titles.get(subsection_number, feature_title)
            candidates.append(
                _candidate(
                    doc_id=doc_id,
                    source_file=source_file,
                    feature_number=feature_number,
                    feature_title=feature_title,
                    subsection_number=subsection_number,
                    subsection_title=subsection_title,
                    page_number=page_number,
                    local_label=f"{subsection_number}/REQ-{requirement_number}",
                    requirement_text=requirement_text,
                    extraction_mode=PureExtractionMode.EXPLICIT_REQ,
                    ordinal=int(requirement_number),
                )
            )
        index = cursor

    return candidates


def _paragraphs_by_section(
    pages: list[PurePdfPage],
) -> Iterable[tuple[int, str, str, str, str, str]]:
    feature_number = ""
    feature_title = ""
    subsection_number = ""
    subsection_title = ""
    current_page = 0
    parts: list[str] = []

    def flush() -> tuple[int, str, str, str, str, str] | None:
        nonlocal parts
        paragraph = _normalize_text(" ".join(parts))
        parts = []
        if not paragraph or not feature_number or not subsection_number:
            return None
        return (
            current_page,
            feature_number,
            feature_title,
            subsection_number,
            subsection_title,
            paragraph,
        )

    for page_number, line in _iter_lines(pages):
        feature_match = _FEATURE_RE.match(line)
        gui_match = _GUI_SECTION_RE.match(line)
        subsection_match = _SUBSECTION_RE.match(line)
        top_level_match = _TOP_LEVEL_SECTION_RE.match(line)
        starts_new_block = bool(_BULLET_RE.match(line)) or line.startswith("REQ-")

        if feature_match or gui_match or subsection_match or top_level_match:
            pending = flush()
            if pending:
                yield pending
        if feature_match:
            feature_number, feature_title = feature_match.groups()
            subsection_number = ""
            subsection_title = ""
            current_page = page_number
            continue
        if gui_match:
            feature_number, feature_title = gui_match.groups()
            subsection_number, subsection_title = gui_match.groups()
            current_page = page_number
            continue
        if subsection_match:
            subsection_number, subsection_title = subsection_match.groups()
            current_page = page_number
            continue
        if top_level_match:
            feature_number = ""
            feature_title = ""
            subsection_number = ""
            subsection_title = ""
            continue
        if not feature_number or not subsection_number or subsection_number.endswith(".3"):
            continue
        if starts_new_block and parts:
            pending = flush()
            if pending:
                yield pending
        if not parts:
            current_page = page_number
        parts.append(_BULLET_RE.sub("", line))

    pending = flush()
    if pending:
        yield pending


def _fallback_candidates(
    *,
    pages: list[PurePdfPage],
    doc_id: str,
    source_file: str,
    minimum_text_length: int,
    explicit_texts: set[str],
) -> list[PureRequirementCandidate]:
    candidates: list[PureRequirementCandidate] = []
    seen: set[tuple[str, str]] = set()
    ordinal_by_feature: dict[str, int] = {}
    for (
        page_number,
        feature_number,
        feature_title,
        subsection_number,
        subsection_title,
        paragraph,
    ) in _paragraphs_by_section(pages):
        normalized = _normalize_text(paragraph)
        normalized_key = normalized.casefold()
        if len(normalized) < minimum_text_length or normalized_key in explicit_texts:
            continue
        if not _CAPABILITY_RE.search(normalized):
            continue
        dedupe_key = (feature_number, normalized_key)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        ordinal_by_feature[feature_number] = ordinal_by_feature.get(feature_number, 0) + 1
        ordinal = ordinal_by_feature[feature_number]
        candidates.append(
            _candidate(
                doc_id=doc_id,
                source_file=source_file,
                feature_number=feature_number,
                feature_title=feature_title,
                subsection_number=subsection_number,
                subsection_title=subsection_title,
                page_number=page_number,
                local_label=f"{subsection_number}/TEXT-{ordinal:03d}",
                requirement_text=normalized,
                extraction_mode=PureExtractionMode.STRUCTURAL_FALLBACK,
                ordinal=ordinal,
            )
        )
    return candidates


def extract_pure_pdf_requirement_candidates_from_pages(
    pages: list[PurePdfPage],
    *,
    doc_id: str,
    source_file: str,
    include_structural_fallback: bool = True,
    minimum_text_length: int = 20,
) -> list[PureRequirementCandidate]:
    explicit = [
        *_explicit_candidates(pages=pages, doc_id=doc_id, source_file=source_file),
        *_numbered_srs_candidates(pages=pages, doc_id=doc_id, source_file=source_file),
    ]
    if not include_structural_fallback:
        return explicit
    explicit_texts = {candidate.requirement_text.casefold() for candidate in explicit}
    fallback = _fallback_candidates(
        pages=pages,
        doc_id=doc_id,
        source_file=source_file,
        minimum_text_length=minimum_text_length,
        explicit_texts=explicit_texts,
    )
    return [*explicit, *fallback]


def extract_pure_pdf_requirement_candidates_from_file(
    path: Path,
    *,
    include_structural_fallback: bool = True,
    minimum_text_length: int = 20,
) -> list[PureRequirementCandidate]:
    pages = extract_pdf_pages(path)
    return extract_pure_pdf_requirement_candidates_from_pages(
        pages,
        doc_id=path.stem,
        source_file=path.name,
        include_structural_fallback=include_structural_fallback,
        minimum_text_length=minimum_text_length,
    )


def extract_pure_pdf_requirement_candidates_from_dir(
    input_dir: Path,
    *,
    include_structural_fallback: bool = True,
    minimum_text_length: int = 20,
) -> list[PureRequirementCandidate]:
    candidates: list[PureRequirementCandidate] = []
    for path in sorted(input_dir.rglob("*.pdf")):
        candidates.extend(
            extract_pure_pdf_requirement_candidates_from_file(
                path,
                include_structural_fallback=include_structural_fallback,
                minimum_text_length=minimum_text_length,
            )
        )
    return candidates
