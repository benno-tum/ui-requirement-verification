from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from ui_verifier.requirement_inspection.annotation_sheet import RequirementStatement


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _normalize_text(text: str) -> str:
    return " ".join(text.split()).strip()


def _element_text(element: ET.Element) -> str:
    return _normalize_text(" ".join(part for part in element.itertext() if part))


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
