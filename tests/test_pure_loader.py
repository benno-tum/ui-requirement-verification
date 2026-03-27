import csv
import os
import subprocess
import sys
from pathlib import Path

from ui_verifier.requirement_inspection.pure_loader import (
    extract_pure_requirement_statements_from_dir,
    extract_pure_requirement_statements_from_file,
)


def test_extract_pure_requirement_statements_from_file(tmp_path: Path) -> None:
    xml_path = tmp_path / "sample.xml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<req_document>
  <title>Sample Document</title>
  <p>This paragraph should be ignored for now.</p>
  <req id="REQ-ALPHA">The system shall display a confirmation message after saving.</req>
  <section>
    <req>The user shall be able to log in.</req>
  </section>
</req_document>
""",
        encoding="utf-8",
    )

    statements = extract_pure_requirement_statements_from_file(xml_path)

    assert len(statements) == 2
    assert statements[0].doc_id == "sample"
    assert statements[0].req_id == "REQ-ALPHA"
    assert statements[0].requirement_text == "The system shall display a confirmation message after saving."
    assert statements[1].req_id == "REQ-00002"
    assert statements[1].requirement_text == "The user shall be able to log in."


def test_extract_pure_requirement_statements_from_dir_and_cli(tmp_path: Path) -> None:
    input_dir = tmp_path / "pure_xml"
    input_dir.mkdir()

    (input_dir / "doc_one.xml").write_text(
        """<req_document>
  <req id="R1">The cart shall show the added item.</req>
</req_document>
""",
        encoding="utf-8",
    )

    nested_dir = input_dir / "nested"
    nested_dir.mkdir()
    (nested_dir / "doc_two.xml").write_text(
        """<req_document>
  <p>Ignored paragraph.</p>
  <req>The system shall display an error message for invalid input.</req>
</req_document>
""",
        encoding="utf-8",
    )

    statements = extract_pure_requirement_statements_from_dir(input_dir)
    assert len(statements) == 2

    output_path = tmp_path / "statements.csv"
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "extract_pure_requirements.py"),
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

    assert "Extracted 2 requirement statements" in result.stdout

    with output_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert len(rows) == 2
    assert rows[0]["doc_id"] == "doc_one"
    assert rows[0]["req_id"] == "R1"
    assert rows[1]["doc_id"] == "doc_two"
    assert rows[1]["req_id"] == "REQ-00001"
