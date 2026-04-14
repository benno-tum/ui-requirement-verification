from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("optional text fields must be strings or None")
    value = value.strip()
    return value or None


class PureSourceFormat(str, Enum):
    XML = "xml"
    PDF = "pdf"
    DOC = "doc"
    HTML = "html"
    HTM = "htm"
    RTF = "rtf"
    UNKNOWN = "unknown"


class PureNodeType(str, Enum):
    SECTION = "section"
    REQUIREMENT = "requirement"
    TEXT_BODY = "text_body"
    LIST_ITEM = "list_item"
    MODIFIER = "modifier"


class PureExtractionMode(str, Enum):
    EXPLICIT_REQ = "explicit_req"
    STRUCTURAL_FALLBACK = "structural_fallback"


@dataclass(slots=True, frozen=True)
class PureDocumentMeta:
    doc_id: str
    source_file: str
    source_format: PureSourceFormat
    document_title: str | None = None
    version: str | None = None
    issue_date: str | None = None
    file_number: str | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "doc_id", _require_non_empty(self.doc_id, "doc_id"))
        object.__setattr__(self, "source_file", _require_non_empty(self.source_file, "source_file"))
        object.__setattr__(self, "document_title", _normalize_optional_text(self.document_title))
        object.__setattr__(self, "version", _normalize_optional_text(self.version))
        object.__setattr__(self, "issue_date", _normalize_optional_text(self.issue_date))
        object.__setattr__(self, "file_number", _normalize_optional_text(self.file_number))
        object.__setattr__(self, "source", _normalize_optional_text(self.source))

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "source_file": self.source_file,
            "source_format": self.source_format.value,
            "document_title": self.document_title,
            "version": self.version,
            "issue_date": self.issue_date,
            "file_number": self.file_number,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PureDocumentMeta":
        return cls(
            doc_id=data["doc_id"],
            source_file=data["source_file"],
            source_format=PureSourceFormat(data.get("source_format", PureSourceFormat.UNKNOWN.value)),
            document_title=data.get("document_title"),
            version=data.get("version"),
            issue_date=data.get("issue_date"),
            file_number=data.get("file_number"),
            source=data.get("source"),
        )


@dataclass(slots=True, frozen=True)
class PureDocumentNode:
    doc_id: str
    node_id: str
    parent_node_id: str | None
    node_type: PureNodeType
    xml_tag: str
    breadcrumb: tuple[str, ...] = field(default_factory=tuple)
    title: str | None = None
    local_label: str | None = None
    text: str | None = None
    modifier: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "doc_id", _require_non_empty(self.doc_id, "doc_id"))
        object.__setattr__(self, "node_id", _require_non_empty(self.node_id, "node_id"))
        object.__setattr__(self, "parent_node_id", _normalize_optional_text(self.parent_node_id))
        object.__setattr__(self, "xml_tag", _require_non_empty(self.xml_tag, "xml_tag"))
        object.__setattr__(self, "title", _normalize_optional_text(self.title))
        object.__setattr__(self, "local_label", _normalize_optional_text(self.local_label))
        object.__setattr__(self, "text", _normalize_optional_text(self.text))
        object.__setattr__(self, "modifier", _normalize_optional_text(self.modifier))
        breadcrumb = tuple(part.strip() for part in self.breadcrumb if isinstance(part, str) and part.strip())
        object.__setattr__(self, "breadcrumb", breadcrumb)
        object.__setattr__(
            self,
            "attributes",
            {str(k): str(v) for k, v in self.attributes.items() if str(k).strip() and str(v).strip()},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "node_id": self.node_id,
            "parent_node_id": self.parent_node_id,
            "node_type": self.node_type.value,
            "xml_tag": self.xml_tag,
            "breadcrumb": list(self.breadcrumb),
            "title": self.title,
            "local_label": self.local_label,
            "text": self.text,
            "modifier": self.modifier,
            "attributes": dict(self.attributes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PureDocumentNode":
        return cls(
            doc_id=data["doc_id"],
            node_id=data["node_id"],
            parent_node_id=data.get("parent_node_id"),
            node_type=PureNodeType(data["node_type"]),
            xml_tag=data["xml_tag"],
            breadcrumb=tuple(data.get("breadcrumb", [])),
            title=data.get("title"),
            local_label=data.get("local_label"),
            text=data.get("text"),
            modifier=data.get("modifier"),
            attributes=dict(data.get("attributes", {})),
        )


@dataclass(slots=True, frozen=True)
class PureDocument:
    meta: PureDocumentMeta
    nodes: tuple[PureDocumentNode, ...]

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for node in self.nodes:
            if node.doc_id != self.meta.doc_id:
                raise ValueError("All nodes in a PureDocument must match meta.doc_id")
            if node.node_id in seen:
                raise ValueError(f"Duplicate node_id in document: {node.node_id}")
            seen.add(node.node_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta": self.meta.to_dict(),
            "nodes": [node.to_dict() for node in self.nodes],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PureDocument":
        return cls(
            meta=PureDocumentMeta.from_dict(data["meta"]),
            nodes=tuple(PureDocumentNode.from_dict(item) for item in data.get("nodes", [])),
        )

    def node_by_id(self, node_id: str) -> PureDocumentNode | None:
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None


@dataclass(slots=True, frozen=True)
class PureRequirementCandidate:
    doc_id: str
    candidate_id: str
    source_node_id: str
    requirement_text: str
    extraction_mode: PureExtractionMode
    source_format: PureSourceFormat
    breadcrumb: tuple[str, ...] = field(default_factory=tuple)
    section_title: str | None = None
    parent_section_title: str | None = None
    local_label: str | None = None
    context_required: bool = True
    context_scope: str | None = None
    context_text: str | None = None
    supporting_node_ids: tuple[str, ...] = field(default_factory=tuple)
    modifier: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "doc_id", _require_non_empty(self.doc_id, "doc_id"))
        object.__setattr__(self, "candidate_id", _require_non_empty(self.candidate_id, "candidate_id"))
        object.__setattr__(self, "source_node_id", _require_non_empty(self.source_node_id, "source_node_id"))
        object.__setattr__(self, "requirement_text", _require_non_empty(self.requirement_text, "requirement_text"))
        object.__setattr__(self, "section_title", _normalize_optional_text(self.section_title))
        object.__setattr__(self, "parent_section_title", _normalize_optional_text(self.parent_section_title))
        object.__setattr__(self, "local_label", _normalize_optional_text(self.local_label))
        object.__setattr__(self, "context_scope", _normalize_optional_text(self.context_scope))
        object.__setattr__(self, "context_text", _normalize_optional_text(self.context_text))
        object.__setattr__(self, "modifier", _normalize_optional_text(self.modifier))
        breadcrumb = tuple(part.strip() for part in self.breadcrumb if isinstance(part, str) and part.strip())
        object.__setattr__(self, "breadcrumb", breadcrumb)
        supporting_node_ids = tuple(
            item.strip() for item in self.supporting_node_ids if isinstance(item, str) and item.strip()
        )
        object.__setattr__(self, "supporting_node_ids", supporting_node_ids)
        if self.context_required and not self.context_scope:
            object.__setattr__(self, "context_scope", "section_path")

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "candidate_id": self.candidate_id,
            "source_node_id": self.source_node_id,
            "requirement_text": self.requirement_text,
            "extraction_mode": self.extraction_mode.value,
            "source_format": self.source_format.value,
            "breadcrumb": list(self.breadcrumb),
            "section_title": self.section_title,
            "parent_section_title": self.parent_section_title,
            "local_label": self.local_label,
            "context_required": self.context_required,
            "context_scope": self.context_scope,
            "context_text": self.context_text,
            "supporting_node_ids": list(self.supporting_node_ids),
            "modifier": self.modifier,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PureRequirementCandidate":
        return cls(
            doc_id=data["doc_id"],
            candidate_id=data["candidate_id"],
            source_node_id=data["source_node_id"],
            requirement_text=data["requirement_text"],
            extraction_mode=PureExtractionMode(data["extraction_mode"]),
            source_format=PureSourceFormat(data.get("source_format", PureSourceFormat.UNKNOWN.value)),
            breadcrumb=tuple(data.get("breadcrumb", [])),
            section_title=data.get("section_title"),
            parent_section_title=data.get("parent_section_title"),
            local_label=data.get("local_label"),
            context_required=bool(data.get("context_required", True)),
            context_scope=data.get("context_scope"),
            context_text=data.get("context_text"),
            supporting_node_ids=tuple(data.get("supporting_node_ids", [])),
            modifier=data.get("modifier"),
        )
