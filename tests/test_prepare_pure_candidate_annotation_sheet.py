import csv
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from ui_verifier.requirement_inspection.annotation_sheet import (
    PURE_CANDIDATE_ANNOTATION_SHEET_FIELDNAMES,
    load_pure_requirement_candidates_jsonl,
    write_blank_pure_candidate_annotation_sheet,
)
from ui_verifier.requirement_inspection.pure_schemas import (
    PureExtractionMode,
    PureRequirementCandidate,
    PureSourceFormat,
)


def _make_candidate(
    *,
    doc_id: str,
    candidate_id: str,
    requirement_text: str,
    source_node_id: str,
    extraction_mode: PureExtractionMode,
    breadcrumb: tuple[str, ...] = tuple(),
    context_text: str | None = None,
    local_label: str | None = None,
    supporting_node_ids: tuple[str, ...] = tuple(),
) -> PureRequirementCandidate:
    return PureRequirementCandidate(
        doc_id=doc_id,
        candidate_id=candidate_id,
        source_node_id=source_node_id,
        requirement_text=requirement_text,
        extraction_mode=extraction_mode,
        source_format=PureSourceFormat.UNKNOWN,
        breadcrumb=breadcrumb,
        local_label=local_label,
        context_required=extraction_mode == PureExtractionMode.STRUCTURAL_FALLBACK,
        context_text=context_text,
        supporting_node_ids=supporting_node_ids,
    )


def test_load_pure_requirement_candidates_jsonl(tmp_path: Path) -> None:
    input_path = tmp_path / "candidates.jsonl"
    expected = _make_candidate(
        doc_id="corpus/specs/order-flow.html",
        candidate_id="corpus/specs/order-flow.html::FALLBACK-00001",
        requirement_text="The system shall display the updated order total.",
        source_node_id="section.00001.text.001",
        extraction_mode=PureExtractionMode.STRUCTURAL_FALLBACK,
        breadcrumb=("Orders", "Totals"),
        context_text="Orders > Totals",
        local_label="2.1",
        supporting_node_ids=("section.00001.text.001", "section.00001"),
    )
    input_path.write_text(json.dumps(expected.to_dict(), ensure_ascii=False) + "\n", encoding="utf-8")

    candidates = load_pure_requirement_candidates_jsonl(input_path)

    assert candidates == [expected]
    assert candidates[0].doc_id == "corpus/specs/order-flow.html"
    assert candidates[0].supporting_node_ids == ("section.00001.text.001", "section.00001")


def test_write_blank_pure_candidate_annotation_sheet_preserves_context_columns(tmp_path: Path) -> None:
    candidates = [
        _make_candidate(
            doc_id="doc-a.xml",
            candidate_id="REQ-001",
            requirement_text="The system shall display a confirmation message after saving.",
            source_node_id="req.00001",
            extraction_mode=PureExtractionMode.EXPLICIT_REQ,
            supporting_node_ids=("req.00001",),
        ),
        _make_candidate(
            doc_id="doc-b.pdf",
            candidate_id="doc-b.pdf::FALLBACK-00001",
            requirement_text="The system shall show the updated order total.",
            source_node_id="section.00002.text.001",
            extraction_mode=PureExtractionMode.STRUCTURAL_FALLBACK,
            breadcrumb=("Orders", "Totals"),
            context_text="Orders > Totals [2.1]",
            local_label="2.1",
            supporting_node_ids=("section.00002.text.001", "section.00002.item.001"),
        ),
    ]

    output_path = tmp_path / "candidate_annotation_sheet.csv"
    write_blank_pure_candidate_annotation_sheet(candidates, output_path)

    with output_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert reader.fieldnames == PURE_CANDIDATE_ANNOTATION_SHEET_FIELDNAMES
    assert len(rows) == 2

    assert rows[0]["doc_id"] == "doc-a.xml"
    assert rows[0]["candidate_id"] == "REQ-001"
    assert rows[0]["context_text"] == ""
    assert rows[0]["breadcrumb"] == ""
    assert rows[0]["local_label"] == ""
    assert rows[0]["source_node_id"] == "req.00001"
    assert json.loads(rows[0]["supporting_node_ids"]) == ["req.00001"]
    assert rows[0]["requirement_type"] == ""
    assert rows[0]["ui_evaluability"] == ""
    assert rows[0]["notes"] == ""

    assert rows[1]["doc_id"] == "doc-b.pdf"
    assert rows[1]["candidate_id"] == "doc-b.pdf::FALLBACK-00001"
    assert rows[1]["context_text"] == "Orders > Totals [2.1]"
    assert json.loads(rows[1]["breadcrumb"]) == ["Orders", "Totals"]
    assert rows[1]["extraction_mode"] == PureExtractionMode.STRUCTURAL_FALLBACK.value
    assert rows[1]["local_label"] == "2.1"
    assert rows[1]["source_node_id"] == "section.00002.text.001"
    assert json.loads(rows[1]["supporting_node_ids"]) == [
        "section.00002.text.001",
        "section.00002.item.001",
    ]


def test_write_blank_pure_candidate_annotation_sheet_dedupes_within_doc_only(tmp_path: Path) -> None:
    candidate = _make_candidate(
        doc_id="doc-a.html",
        candidate_id="doc-a.html::FALLBACK-00001",
        requirement_text="The system shall display the active cart total.",
        source_node_id="section.00001.text.001",
        extraction_mode=PureExtractionMode.STRUCTURAL_FALLBACK,
        breadcrumb=("Cart",),
        context_text="Cart",
        supporting_node_ids=("section.00001.text.001",),
    )
    duplicate = PureRequirementCandidate.from_dict(candidate.to_dict())
    same_text_other_doc = _make_candidate(
        doc_id="doc-b.html",
        candidate_id="doc-a.html::FALLBACK-00001",
        requirement_text="The system shall display the active cart total.",
        source_node_id="section.00001.text.001",
        extraction_mode=PureExtractionMode.STRUCTURAL_FALLBACK,
        breadcrumb=("Cart",),
        context_text="Cart",
        supporting_node_ids=("section.00001.text.001",),
    )

    output_path = tmp_path / "candidate_annotation_sheet.csv"
    write_blank_pure_candidate_annotation_sheet(
        [candidate, duplicate, same_text_other_doc],
        output_path,
    )

    with output_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert len(rows) == 2
    assert [row["doc_id"] for row in rows] == ["doc-a.html", "doc-b.html"]


def test_write_blank_pure_candidate_annotation_sheet_rejects_conflicting_duplicate_ids(
    tmp_path: Path,
) -> None:
    candidate = _make_candidate(
        doc_id="doc-a.html",
        candidate_id="doc-a.html::FALLBACK-00001",
        requirement_text="The system shall display the active cart total.",
        source_node_id="section.00001.text.001",
        extraction_mode=PureExtractionMode.STRUCTURAL_FALLBACK,
        breadcrumb=("Cart",),
        context_text="Cart",
        supporting_node_ids=("section.00001.text.001",),
    )
    conflicting_duplicate = replace(candidate, source_node_id="section.00002.text.001")

    with pytest.raises(ValueError, match="Conflicting duplicate PURE candidate"):
        write_blank_pure_candidate_annotation_sheet(
            [candidate, conflicting_duplicate],
            tmp_path / "candidate_annotation_sheet.csv",
        )


def test_prepare_pure_candidate_annotation_sheet_cli(tmp_path: Path) -> None:
    input_path = tmp_path / "candidates.jsonl"
    output_path = tmp_path / "candidate_annotation_sheet.csv"
    candidate = _make_candidate(
        doc_id="docs/checkout.rtf",
        candidate_id="docs/checkout.rtf::FALLBACK-00001",
        requirement_text="The system shall show the payment confirmation page.",
        source_node_id="section.00003.text.001",
        extraction_mode=PureExtractionMode.STRUCTURAL_FALLBACK,
        breadcrumb=("Checkout", "Payment"),
        context_text="Checkout > Payment",
        local_label="4.3",
        supporting_node_ids=("section.00003.text.001",),
    )
    input_path.write_text(json.dumps(candidate.to_dict(), ensure_ascii=False) + "\n", encoding="utf-8")

    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "prepare_pure_candidate_annotation_sheet.py"),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=True,
        env=env,
        cwd=repo_root,
    )

    assert "Wrote PURE candidate annotation sheet with 1 rows" in result.stdout

    with output_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["doc_id"] == "docs/checkout.rtf"
    assert rows[0]["candidate_id"] == "docs/checkout.rtf::FALLBACK-00001"
    assert rows[0]["context_text"] == "Checkout > Payment"
