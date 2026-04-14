from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from ui_verifier.requirement_inspection.annotation_sheet import RequirementStatement
from ui_verifier.requirement_inspection.pure_schemas import (
    PureDocument,
    PureDocumentMeta,
    PureDocumentNode,
    PureExtractionMode,
    PureNodeType,
    PureRequirementCandidate,
    PureSourceFormat,
)

_MODAL_KEYWORDS = (" shall ", " should ", " must ", " will ")


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _normalize_text(text: str) -> str:
    return " ".join(text.split()).strip()


def _element_text(element: ET.Element) -> str:
    return _normalize_text(" ".join(part for part in element.itertext() if part))


def _direct_child(element: ET.Element, name: str) -> ET.Element | None:
    for child in list(element):
        if _local_name(child.tag) == name:
            return child
    return None


def _direct_children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(element) if _local_name(child.tag) == name]


def _get_attribute(element: ET.Element, *names: str) -> str | None:
    normalized_names = set(names)
    for key, value in element.attrib.items():
        local_key = _local_name(key)
        if local_key in normalized_names and value is not None:
            value = value.strip()
            if value:
                return value
    return None


def _make_req_id(element: ET.Element, index: int) -> str:
    explicit_id = _get_attribute(element, "id", "req_id", "identifier")
    if explicit_id:
        return explicit_id
    return f"REQ-{index:05d}"


def _title_text(element: ET.Element | None) -> str | None:
    if element is None:
        return None
    text = _element_text(element)
    return text or None


def _infer_source_format(path: Path) -> PureSourceFormat:
    suffix = path.suffix.lower().lstrip(".")
    try:
        return PureSourceFormat(suffix)
    except ValueError:
        return PureSourceFormat.UNKNOWN


def _looks_requirement_like(text: str) -> bool:
    normalized = f" {_normalize_text(text).lower()} "
    return any(keyword in normalized for keyword in _MODAL_KEYWORDS)


def _requires_context(text: str, extraction_mode: PureExtractionMode) -> bool:
    if extraction_mode == PureExtractionMode.STRUCTURAL_FALLBACK:
        return True
    normalized = f" {_normalize_text(text).lower()} "
    return not any(keyword in normalized for keyword in _MODAL_KEYWORDS)


def _context_text(breadcrumb: tuple[str, ...], local_label: str | None) -> str | None:
    parts = [part for part in breadcrumb if part]
    if local_label:
        parts.append(f"[{local_label}]")
    if not parts:
        return None
    return " > ".join(parts)


def _child_attributes(element: ET.Element) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for key, value in element.attrib.items():
        local_key = _local_name(key)
        if value is None:
            continue
        value = value.strip()
        if value:
            attrs[local_key] = value
    return attrs


def _append_list_item_nodes(
    *,
    items_parent: ET.Element,
    doc_id: str,
    parent_node_id: str,
    breadcrumb: tuple[str, ...],
    node_prefix: str,
    nodes: list[PureDocumentNode],
    counters: dict[str, int],
) -> None:
    for item in _direct_children(items_parent, "item"):
        text = _element_text(item)
        if not text:
            continue
        counters["list"] += 1
        item_node_id = f"{node_prefix}.item.{counters['list']:03d}"
        nodes.append(
            PureDocumentNode(
                doc_id=doc_id,
                node_id=item_node_id,
                parent_node_id=parent_node_id,
                node_type=PureNodeType.LIST_ITEM,
                xml_tag="item",
                breadcrumb=breadcrumb,
                text=text,
                attributes=_child_attributes(item),
            )
        )
        for list_container_name in ("itemize", "enum", "description"):
            for nested_list in _direct_children(item, list_container_name):
                _append_list_item_nodes(
                    items_parent=nested_list,
                    doc_id=doc_id,
                    parent_node_id=item_node_id,
                    breadcrumb=breadcrumb,
                    node_prefix=item_node_id,
                    nodes=nodes,
                    counters=counters,
                )


def _append_text_body_and_lists(
    *,
    text_element: ET.Element,
    doc_id: str,
    parent_node_id: str,
    breadcrumb: tuple[str, ...],
    node_prefix: str,
    nodes: list[PureDocumentNode],
    counters: dict[str, int],
) -> PureDocumentNode | None:
    text = _element_text(text_element)
    if not text:
        return None

    counters["text"] += 1
    text_node_id = f"{node_prefix}.text.{counters['text']:03d}"
    text_node = PureDocumentNode(
        doc_id=doc_id,
        node_id=text_node_id,
        parent_node_id=parent_node_id,
        node_type=PureNodeType.TEXT_BODY,
        xml_tag="text_body",
        breadcrumb=breadcrumb,
        text=text,
        attributes=_child_attributes(text_element),
    )
    nodes.append(text_node)

    for list_container_name in ("itemize", "enum", "description"):
        for list_container in _direct_children(text_element, list_container_name):
            _append_list_item_nodes(
                items_parent=list_container,
                doc_id=doc_id,
                parent_node_id=text_node_id,
                breadcrumb=breadcrumb,
                node_prefix=text_node_id,
                nodes=nodes,
                counters=counters,
            )

    return text_node


def _walk_section(
    element: ET.Element,
    *,
    doc_id: str,
    parent_section_node_id: str | None,
    parent_breadcrumb: tuple[str, ...],
    nodes: list[PureDocumentNode],
    counters: dict[str, int],
) -> None:
    local_label = _get_attribute(element, "id")
    title = _title_text(_direct_child(element, "title"))

    counters["section"] += 1
    section_node_id = f"section.{counters['section']:05d}"
    breadcrumb = parent_breadcrumb + ((title,) if title else ())
    section_node = PureDocumentNode(
        doc_id=doc_id,
        node_id=section_node_id,
        parent_node_id=parent_section_node_id,
        node_type=PureNodeType.SECTION,
        xml_tag="p",
        breadcrumb=breadcrumb,
        title=title,
        local_label=local_label,
        attributes=_child_attributes(element),
    )
    nodes.append(section_node)

    for child in list(element):
        child_name = _local_name(child.tag)
        if child_name in {"title", "glossary"}:
            continue
        if child_name == "text_body":
            _append_text_body_and_lists(
                text_element=child,
                doc_id=doc_id,
                parent_node_id=section_node_id,
                breadcrumb=breadcrumb,
                node_prefix=section_node_id,
                nodes=nodes,
                counters=counters,
            )
            continue
        if child_name == "req":
            _append_requirement(
                child,
                doc_id=doc_id,
                parent_node_id=section_node_id,
                breadcrumb=breadcrumb,
                nodes=nodes,
                counters=counters,
            )
            continue
        if child_name == "p":
            _walk_section(
                child,
                doc_id=doc_id,
                parent_section_node_id=section_node_id,
                parent_breadcrumb=breadcrumb,
                nodes=nodes,
                counters=counters,
            )


def _append_requirement(
    element: ET.Element,
    *,
    doc_id: str,
    parent_node_id: str | None,
    breadcrumb: tuple[str, ...],
    nodes: list[PureDocumentNode],
    counters: dict[str, int],
) -> None:
    counters["req"] += 1
    req_id = _make_req_id(element, counters["req"])
    text_body = _direct_child(element, "text_body")
    modifier_element = _direct_child(element, "modifier")
    text = _element_text(text_body) if text_body is not None else _element_text(element)
    modifier = _element_text(modifier_element) if modifier_element is not None else None

    req_node_id = f"req.{counters['req']:05d}"
    nodes.append(
        PureDocumentNode(
            doc_id=doc_id,
            node_id=req_node_id,
            parent_node_id=parent_node_id,
            node_type=PureNodeType.REQUIREMENT,
            xml_tag="req",
            breadcrumb=breadcrumb,
            local_label=req_id,
            text=text or None,
            modifier=modifier,
            attributes=_child_attributes(element),
        )
    )

    if text_body is not None:
        _append_text_body_and_lists(
            text_element=text_body,
            doc_id=doc_id,
            parent_node_id=req_node_id,
            breadcrumb=breadcrumb,
            node_prefix=req_node_id,
            nodes=nodes,
            counters=counters,
        )
    if modifier:
        counters["modifier"] += 1
        nodes.append(
            PureDocumentNode(
                doc_id=doc_id,
                node_id=f"{req_node_id}.modifier.{counters['modifier']:03d}",
                parent_node_id=req_node_id,
                node_type=PureNodeType.MODIFIER,
                xml_tag="modifier",
                breadcrumb=breadcrumb,
                local_label=req_id,
                text=modifier,
            )
        )


def load_pure_document(path: Path) -> PureDocument:
    tree = ET.parse(path)
    root = tree.getroot()
    doc_id = path.stem

    meta = PureDocumentMeta(
        doc_id=doc_id,
        source_file=path.name,
        source_format=_infer_source_format(path),
        document_title=_title_text(_direct_child(root, "title")),
        version=_title_text(_direct_child(root, "version")),
        issue_date=_title_text(_direct_child(root, "issue_date")),
        file_number=_title_text(_direct_child(root, "file_number")),
        source=_title_text(_direct_child(root, "source")),
    )

    nodes: list[PureDocumentNode] = []
    counters = {"section": 0, "req": 0, "text": 0, "list": 0, "modifier": 0}

    for child in list(root):
        child_name = _local_name(child.tag)
        if child_name == "p":
            _walk_section(
                child,
                doc_id=doc_id,
                parent_section_node_id=None,
                parent_breadcrumb=tuple(),
                nodes=nodes,
                counters=counters,
            )
        elif child_name == "req":
            _append_requirement(
                child,
                doc_id=doc_id,
                parent_node_id=None,
                breadcrumb=tuple(),
                nodes=nodes,
                counters=counters,
            )

    return PureDocument(meta=meta, nodes=tuple(nodes))


def load_pure_documents_from_dir(input_dir: Path) -> list[PureDocument]:
    documents: list[PureDocument] = []
    for xml_path in sorted(input_dir.rglob("*.xml")):
        documents.append(load_pure_document(xml_path))
    return documents


def extract_pure_requirement_candidates_from_document(
    document: PureDocument,
    *,
    include_structural_fallback: bool = True,
    minimum_text_length: int = 20,
) -> list[PureRequirementCandidate]:
    explicit_candidates: list[PureRequirementCandidate] = []
    fallback_candidates: list[PureRequirementCandidate] = []
    nodes_by_id = {node.node_id: node for node in document.nodes}

    def has_requirement_ancestor(node: PureDocumentNode) -> bool:
        current = node
        while current.parent_node_id is not None:
            parent = nodes_by_id.get(current.parent_node_id)
            if parent is None:
                break
            if parent.node_type == PureNodeType.REQUIREMENT:
                return True
            current = parent
        return False

    for node in document.nodes:
        if node.node_type == PureNodeType.REQUIREMENT and node.text:
            explicit_candidates.append(
                PureRequirementCandidate(
                    doc_id=document.meta.doc_id,
                    candidate_id=node.local_label or node.node_id,
                    source_node_id=node.node_id,
                    requirement_text=node.text,
                    extraction_mode=PureExtractionMode.EXPLICIT_REQ,
                    source_format=document.meta.source_format,
                    breadcrumb=node.breadcrumb,
                    section_title=node.breadcrumb[-1] if node.breadcrumb else None,
                    parent_section_title=node.breadcrumb[-2] if len(node.breadcrumb) >= 2 else None,
                    local_label=node.local_label,
                    context_required=_requires_context(node.text, PureExtractionMode.EXPLICIT_REQ),
                    context_scope="section_path" if node.breadcrumb else None,
                    context_text=_context_text(node.breadcrumb, node.local_label),
                    supporting_node_ids=(node.node_id,),
                    modifier=node.modifier,
                )
            )

    if not include_structural_fallback:
        return explicit_candidates

    fallback_index = 0
    for node in document.nodes:
        if node.node_type not in {PureNodeType.TEXT_BODY, PureNodeType.LIST_ITEM}:
            continue
        if not node.text or len(node.text) < minimum_text_length:
            continue
        if has_requirement_ancestor(node):
            continue
        if not _looks_requirement_like(node.text):
            continue

        fallback_index += 1
        candidate_id = f"{document.meta.doc_id}::FALLBACK-{fallback_index:05d}"
        fallback_candidates.append(
            PureRequirementCandidate(
                doc_id=document.meta.doc_id,
                candidate_id=candidate_id,
                source_node_id=node.node_id,
                requirement_text=node.text,
                extraction_mode=PureExtractionMode.STRUCTURAL_FALLBACK,
                source_format=document.meta.source_format,
                breadcrumb=node.breadcrumb,
                section_title=node.breadcrumb[-1] if node.breadcrumb else None,
                parent_section_title=node.breadcrumb[-2] if len(node.breadcrumb) >= 2 else None,
                local_label=node.local_label,
                context_required=True,
                context_scope="section_path",
                context_text=_context_text(node.breadcrumb, node.local_label),
                supporting_node_ids=(node.node_id,),
            )
        )

    return explicit_candidates + fallback_candidates


def extract_pure_requirement_candidates_from_file(
    path: Path,
    *,
    include_structural_fallback: bool = True,
    minimum_text_length: int = 20,
) -> list[PureRequirementCandidate]:
    document = load_pure_document(path)
    return extract_pure_requirement_candidates_from_document(
        document,
        include_structural_fallback=include_structural_fallback,
        minimum_text_length=minimum_text_length,
    )


def extract_pure_requirement_candidates_from_dir(
    input_dir: Path,
    *,
    include_structural_fallback: bool = True,
    minimum_text_length: int = 20,
) -> list[PureRequirementCandidate]:
    candidates: list[PureRequirementCandidate] = []
    for document in load_pure_documents_from_dir(input_dir):
        candidates.extend(
            extract_pure_requirement_candidates_from_document(
                document,
                include_structural_fallback=include_structural_fallback,
                minimum_text_length=minimum_text_length,
            )
        )
    return candidates


def extract_pure_requirement_statements_from_file(path: Path) -> list[RequirementStatement]:
    tree = ET.parse(path)
    root = tree.getroot()
    doc_id = path.stem

    statements: list[RequirementStatement] = []
    seen_ids: set[str] = set()

    req_index = 0
    for element in root.iter():
        if _local_name(element.tag) != "req":
            continue

        text = _element_text(element)
        if not text:
            continue

        req_index += 1
        req_id = _make_req_id(element, req_index)

        if req_id in seen_ids:
            req_id = f"{req_id}__{req_index:05d}"
        seen_ids.add(req_id)

        statements.append(
            RequirementStatement(
                doc_id=doc_id,
                req_id=req_id,
                requirement_text=text,
            )
        )

    return statements


def extract_pure_requirement_statements_from_dir(input_dir: Path) -> list[RequirementStatement]:
    statements: list[RequirementStatement] = []
    for xml_path in sorted(input_dir.rglob("*.xml")):
        statements.extend(extract_pure_requirement_statements_from_file(xml_path))
    return statements
