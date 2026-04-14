import json
import os
import subprocess
import sys
from pathlib import Path

from ui_verifier.requirement_inspection.pure_loader import (
    extract_pure_requirement_candidates_from_file,
    load_pure_document,
)
from ui_verifier.requirement_inspection.pure_schemas import (
    PureExtractionMode,
    PureNodeType,
)


def test_load_pure_document_preserves_structure_and_context(tmp_path: Path) -> None:
    xml_path = tmp_path / "sample.xml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<req_document>
  <title><title>Inventory 2.0</title><title>Requirements</title></title>
  <version>1.0</version>
  <p id="3.2">
    <title>Manage Departments</title>
    <p id="3.2.4">
      <title>Add Department</title>
      <text_body>The system shall ask for a department name.</text_body>
      <req id="REQ-ADD-1">
        <text_body>System displays the Add Department button.</text_body>
        <modifier>visible after opening department administration</modifier>
      </req>
    </p>
  </p>
</req_document>
""",
        encoding="utf-8",
    )

    document = load_pure_document(xml_path)

    assert document.meta.doc_id == "sample"
    assert document.meta.document_title == "Inventory 2.0 Requirements"
    assert len(document.nodes) >= 5

    sections = [node for node in document.nodes if node.node_type == PureNodeType.SECTION]
    reqs = [node for node in document.nodes if node.node_type == PureNodeType.REQUIREMENT]
    modifiers = [node for node in document.nodes if node.node_type == PureNodeType.MODIFIER]

    assert [node.title for node in sections] == ["Manage Departments", "Add Department"]
    assert reqs[0].local_label == "REQ-ADD-1"
    assert reqs[0].breadcrumb == ("Manage Departments", "Add Department")
    assert reqs[0].text == "System displays the Add Department button."
    assert reqs[0].modifier == "visible after opening department administration"
    assert modifiers[0].parent_node_id == reqs[0].node_id


def test_extract_pure_requirement_candidates_uses_explicit_and_fallback_modes(tmp_path: Path) -> None:
    xml_path = tmp_path / "sample.xml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<req_document>
  <title>Sample</title>
  <version>1.0</version>
  <p id="1">
    <title>User Management</title>
    <text_body>The system shall allow the administrator to create a new user.</text_body>
    <req id="REQ-LOGIN-1">
      <text_body>The system shall display a confirmation message after saving.</text_body>
    </req>
  </p>
</req_document>
""",
        encoding="utf-8",
    )

    candidates = extract_pure_requirement_candidates_from_file(xml_path)

    assert len(candidates) == 2
    assert candidates[0].candidate_id == "REQ-LOGIN-1"
    assert candidates[0].extraction_mode == PureExtractionMode.EXPLICIT_REQ
    assert candidates[0].context_required is False
    assert candidates[0].breadcrumb == ("User Management",)

    assert candidates[1].extraction_mode == PureExtractionMode.STRUCTURAL_FALLBACK
    assert candidates[1].context_required is True
    assert candidates[1].context_text == "User Management"
    assert candidates[1].requirement_text == "The system shall allow the administrator to create a new user."


def test_extract_pure_requirement_candidates_cli_jsonl(tmp_path: Path) -> None:
    input_dir = tmp_path / "xml"
    input_dir.mkdir()
    (input_dir / "doc.xml").write_text(
        """<req_document>
  <title>CLI Sample</title>
  <version>1.0</version>
  <p id="1">
    <title>Orders</title>
    <text_body>The system shall show the updated order total.</text_body>
  </p>
</req_document>
""",
        encoding="utf-8",
    )

    output_path = tmp_path / "candidates.jsonl"
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "extract_pure_requirement_candidates.py"),
            "--input-dir",
            str(input_dir),
            "--output",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=True,
        env=env,
        cwd=repo_root,
    )

    assert "Extracted 1 PURE requirement candidates" in result.stdout

    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["extraction_mode"] == PureExtractionMode.STRUCTURAL_FALLBACK.value
    assert rows[0]["context_text"] == "Orders"
