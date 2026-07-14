from __future__ import annotations

from pathlib import Path

import pytest

from ui_verifier.requirement_inspection.pure_pdf_loader import (
    PurePdfPage,
    extract_pure_pdf_requirement_candidates_from_file,
    extract_pure_pdf_requirement_candidates_from_pages,
)
from ui_verifier.requirement_inspection.pure_schemas import PureExtractionMode, PureSourceFormat


def test_pdf_extraction_scopes_repeated_requirement_ids_and_keeps_pages() -> None:
    pages = [
        PurePdfPage(
            page_number=7,
            text="""
            3.1 System Feature 1 - Split
            3.1.2 Stimulus/Response Sequences
            The user can select a PDF and display the split panel.
            3.1.3 Functional Requirements
            REQ-1: The user can split only one document at a time.
            REQ-2: Compression requires PDF version 1.5 or above.
            """,
        ),
        PurePdfPage(
            page_number=9,
            text="""
            3.2 System Feature 2 - Merge/Extract
            3.2.2 Stimulus/Response Sequences
            The user can select more than one file to merge.
            3.2.3 Functional Requirements
            REQ-1: Page numbers in the page selection must be comprehended.
            """,
        ),
    ]

    candidates = extract_pure_pdf_requirement_candidates_from_pages(
        pages,
        doc_id="split-merge",
        source_file="split-merge.pdf",
    )
    explicit = [item for item in candidates if item.extraction_mode == PureExtractionMode.EXPLICIT_REQ]
    fallback = [item for item in candidates if item.extraction_mode == PureExtractionMode.STRUCTURAL_FALLBACK]

    assert len(explicit) == 3
    assert len({item.candidate_id for item in explicit}) == 3
    assert explicit[0].candidate_id == "split-merge::3.1::3.1.3/req-1"
    assert explicit[2].candidate_id == "split-merge::3.2::3.2.3/req-1"
    assert explicit[0].source_format == PureSourceFormat.PDF
    assert "PDF page 7" in (explicit[0].context_text or "")
    assert fallback
    assert any("display the split panel" in item.requirement_text for item in fallback)


def test_pdf_extraction_can_disable_structural_fallback() -> None:
    pages = [
        PurePdfPage(
            page_number=1,
            text="""
            3.1 System Feature 1 - Split
            3.1.2 Stimulus/Response Sequences
            The user can display the split panel.
            3.1.3 Functional Requirements
            REQ-1: The user can split one document.
            """,
        )
    ]
    candidates = extract_pure_pdf_requirement_candidates_from_pages(
        pages,
        doc_id="doc",
        source_file="doc.pdf",
        include_structural_fallback=False,
    )
    assert len(candidates) == 1
    assert candidates[0].extraction_mode == PureExtractionMode.EXPLICIT_REQ


def test_pdf_extraction_scopes_four_digit_srs_requirements_with_context() -> None:
    pages = [
        PurePdfPage(
            page_number=7,
            text="""
            3 Specific Requirements
            3.2 Functional Requirements
            3.2.1 User Accounts
            0240 User Account Creation - New user accounts can be created. Priority 1
            0260 Certain pieces of information are required to create new accounts. Priority 1
            3.2.2 Marketing Campaigns
            0480 A campaign has the following components:
            0490 Name Priority 1
            """,
        )
    ]

    candidates = extract_pure_pdf_requirement_candidates_from_pages(
        pages,
        doc_id="mashboot",
        source_file="mashboot.pdf",
        include_structural_fallback=False,
    )

    assert [item.candidate_id for item in candidates] == [
        "mashboot::3.2::3.2.1/req-0240",
        "mashboot::3.2::3.2.1/req-0260",
        "mashboot::3.2::3.2.2/req-0480",
        "mashboot::3.2::3.2.2/req-0490",
    ]
    assert candidates[0].requirement_text == "User Account Creation - New user accounts can be created."
    assert candidates[2].section_title == "3.2.2 Marketing Campaigns"
    assert "PDF page 7" in (candidates[2].context_text or "")


def test_pdf_extraction_includes_gui_interface_section_fallbacks() -> None:
    pages = [
        PurePdfPage(
            page_number=20,
            text="""
            4.1 User Interfaces - GUI
            The PDFsam GUI provides a browsing window for PDF and XML files.
            The system displays a log panel.
            4.2 Hardware Interfaces
            The hardware can be any computer.
            """,
        )
    ]
    candidates = extract_pure_pdf_requirement_candidates_from_pages(
        pages,
        doc_id="doc",
        source_file="doc.pdf",
    )
    gui_candidates = [item for item in candidates if item.parent_section_title == "4.1 User Interfaces - GUI"]
    assert len(gui_candidates) == 1
    assert "browsing window" in gui_candidates[0].requirement_text
    assert "hardware" not in gui_candidates[0].requirement_text.lower()


def test_real_split_merge_pdf_contains_all_explicit_functional_requirements() -> None:
    pdf_path = Path("data/raw/pure/req/2010 - split merge.pdf")
    if not pdf_path.exists():
        pytest.skip("PURE Split/Merge PDF is not available")
    pytest.importorskip("pypdf")

    candidates = extract_pure_pdf_requirement_candidates_from_file(
        pdf_path,
        include_structural_fallback=False,
    )

    assert len(candidates) == 13
    assert {item.parent_section_title for item in candidates} == {
        "3.1 System Feature 1 - Split",
        "3.2 System Feature 2 - Merge/Extract",
        "3.3 System Feature 3 - Alternate Mix",
        "3.4 System Feature 4 - Rotate",
        "3.5 System Feature 5 - Visually reorder",
        "3.7 System Feature 7 - Working Environment",
        "3.8 System Feature 8 - Log Panel",
        "3.9 System Feature 9 - Settings",
    }
