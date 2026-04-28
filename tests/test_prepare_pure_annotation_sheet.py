import csv
import subprocess
import sys
from pathlib import Path

from ui_verifier.requirement_inspection.annotation_sheet import (
    ANNOTATION_SHEET_FIELDNAMES,
    RequirementStatement,
    write_blank_annotation_sheet,
)


def test_write_blank_annotation_sheet(tmp_path: Path) -> None:
    statements = [
        RequirementStatement(
            doc_id="pure_doc_001",
            req_id="REQ-001",
            requirement_text="The system shall display a confirmation message after saving.",
        ),
        RequirementStatement(
            doc_id="pure_doc_001",
            req_id="REQ-002",
            requirement_text="After adding an item, it shall appear in the shopping cart.",
        ),
    ]

    output_path = tmp_path / "annotation_sheet.csv"
    write_blank_annotation_sheet(statements, output_path, limit=1)

    with output_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert reader.fieldnames == ANNOTATION_SHEET_FIELDNAMES
    assert len(rows) == 1
    assert rows[0]["doc_id"] == "pure_doc_001"
    assert rows[0]["req_id"] == "REQ-001"
    assert rows[0]["requirement_type"] == ""
    assert rows[0]["ui_evaluability"] == ""
    assert rows[0]["notes"] == ""


def test_prepare_pure_annotation_sheet_cli(tmp_path: Path) -> None:
    input_path = tmp_path / "statements.csv"
    output_path = tmp_path / "annotation_sheet.csv"

    with input_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["doc_id", "req_id", "requirement_text"])
        writer.writeheader()
        writer.writerow(
            {
                "doc_id": "pure_doc_001",
                "req_id": "REQ-001",
                "requirement_text": "The system shall display a confirmation message after saving.",
            }
        )
        writer.writerow(
            {
                "doc_id": "pure_doc_001",
                "req_id": "REQ-002",
                "requirement_text": "The system shall encrypt user data at rest.",
            }
        )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_pure_annotation_sheet.py",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--limit",
            "2",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Wrote annotation sheet with 2 rows" in result.stdout

    with output_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert len(rows) == 2
    assert rows[1]["req_id"] == "REQ-002"
    assert rows[1]["ui_evaluability"] == ""
