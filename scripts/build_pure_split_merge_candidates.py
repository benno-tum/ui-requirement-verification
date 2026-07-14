from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
FLOW_ID = "pure_2010_split_merge"
DOC_ID = "2010 - split merge"
SOURCE_PDF = "data/raw/pure/req/2010 - split merge.pdf"


CURATED_REQUIREMENTS: list[dict[str, Any]] = [
    {
        "requirement_id": "PURE-SM-UI-001",
        "text": "The main GUI shall expose the six basic plugins through the plugins tree.",
        "section": "3 System Features / 4.1 User Interfaces - GUI",
        "source_pages": [9, 26, 27, 28],
        "evidence_steps": [1, 23, 24, 25, 26, 27, 28],
        "claims": ["The plugins tree exposes Alternate Mix, Merge/Extract, Rotate, Split, Visual document composer, and Visual reorder."],
    },
    {
        "requirement_id": "PURE-SM-SPLIT-001",
        "text": "Selecting Split from the plugins tree shall display the Split panel.",
        "section": "3.1.2 Stimulus/Response Sequences",
        "source_pages": [9],
        "evidence_steps": [1, 3, 26],
        "claims": ["The plugins tree provides access to a Split panel."],
    },
    {
        "requirement_id": "PURE-SM-SPLIT-002",
        "text": "The Split panel shall provide an input-document table with file information and password entry for protected PDFs.",
        "section": "3.1.2 Stimulus/Response Sequences",
        "source_pages": [10],
        "evidence_steps": [3, 26],
        "claims": ["The Split panel contains an input-document table with file information.", "The table includes password entry for protected PDFs."],
    },
    {
        "requirement_id": "PURE-SM-SPLIT-003",
        "text": "The Split panel shall offer burst, every-n-pages, even-page, odd-page, specified-page, size, and bookmark-level split modes.",
        "section": "3.1.2 Stimulus/Response Sequences",
        "source_pages": [10],
        "evidence_steps": [3, 26],
        "claims": ["The Split panel exposes seven distinct split modes."],
    },
    {
        "requirement_id": "PURE-SM-SPLIT-004",
        "text": "The Split panel shall expose destination selection, compression, output PDF version, filename-prefix, and Run controls.",
        "section": "3.1.2 Stimulus/Response Sequences",
        "source_pages": [10, 11],
        "evidence_steps": [3, 26],
        "claims": ["The Split panel exposes destination selection.", "The Split panel exposes compression and output PDF version controls.", "The Split panel exposes filename-prefix and Run controls."],
    },
    {
        "requirement_id": "PURE-SM-MERGE-001",
        "text": "The Merge/Extract panel shall accept multiple PDF files and display file details, page selection, passwords, and ordering controls.",
        "section": "3.2.2 Stimulus/Response Sequences",
        "source_pages": [11, 12],
        "evidence_steps": [4, 24],
        "claims": ["The Merge/Extract panel accepts multiple PDF files.", "The file table displays details, page selection, and password columns.", "The panel exposes file-ordering controls."],
    },
    {
        "requirement_id": "PURE-SM-MERGE-002",
        "text": "The Merge/Extract panel shall expose an option indicating that input PDF documents contain forms.",
        "section": "3.2.2 Stimulus/Response Sequences",
        "source_pages": [12],
        "evidence_steps": [4, 24],
        "claims": ["The Merge/Extract panel contains a PDF-documents-contain-forms option."],
    },
    {
        "requirement_id": "PURE-SM-MERGE-003",
        "text": "The Merge/Extract panel shall expose output-file selection, compression, output PDF version, and Run controls.",
        "section": "3.2.2 Stimulus/Response Sequences",
        "source_pages": [12],
        "evidence_steps": [4, 24],
        "claims": ["The Merge/Extract panel exposes output-file selection.", "The panel exposes compression and output PDF version controls.", "The panel exposes a Run control."],
    },
    {
        "requirement_id": "PURE-SM-MIX-001",
        "text": "The Alternate Mix panel shall expose two-document selection, ordering, reversal, and pages-to-switch controls.",
        "section": "3.3.2 Stimulus/Response Sequences",
        "source_pages": [13],
        "evidence_steps": [5, 23],
        "claims": ["The Alternate Mix panel displays two input documents.", "The panel exposes document ordering and reversal controls.", "The panel exposes a pages-to-switch control."],
    },
    {
        "requirement_id": "PURE-SM-MIX-002",
        "text": "The Alternate Mix panel shall expose output-file selection, compression, output PDF version, and Run controls.",
        "section": "3.3.2 Stimulus/Response Sequences",
        "source_pages": [13],
        "evidence_steps": [5, 23],
        "claims": ["The Alternate Mix panel exposes output-file selection.", "The panel exposes compression and output PDF version controls.", "The panel exposes a Run control."],
    },
    {
        "requirement_id": "PURE-SM-ROTATE-001",
        "text": "The Rotate panel shall accept PDF documents and expose clockwise-angle and page-subset controls.",
        "section": "3.4.2 Stimulus/Response Sequences",
        "source_pages": [14],
        "evidence_steps": [6, 25],
        "claims": ["The Rotate panel contains an input-document table.", "The panel exposes clockwise-angle and All, Even, or Odd page controls."],
    },
    {
        "requirement_id": "PURE-SM-ROTATE-002",
        "text": "The Rotate panel shall expose destination, compression, output PDF version, filename-prefix, and Run controls.",
        "section": "3.4.2 Stimulus/Response Sequences",
        "source_pages": [15],
        "evidence_steps": [6, 25],
        "claims": ["The Rotate panel exposes destination selection.", "The panel exposes compression and output PDF version controls.", "The panel exposes filename-prefix and Run controls."],
    },
    {
        "requirement_id": "PURE-SM-REORDER-001",
        "text": "The Visual Reorder panel shall display page thumbnails for a selected PDF document.",
        "section": "3.5.2 Stimulus/Response Sequences",
        "source_pages": [15, 16],
        "evidence_steps": [8, 28],
        "claims": ["The Visual Reorder panel displays page thumbnails for a PDF document."],
    },
    {
        "requirement_id": "PURE-SM-REORDER-002",
        "text": "The Visual Reorder panel shall expose move, reverse, delete, undelete, rotate, zoom, and preview controls for selected pages.",
        "section": "3.5.2 Stimulus/Response Sequences",
        "source_pages": [15, 16],
        "evidence_steps": [7, 8, 20, 28],
        "claims": ["The Visual Reorder panel exposes page move and reverse controls.", "The panel exposes delete, undelete, rotate, and zoom controls.", "The panel supports previewing a page in the image viewer."],
    },
    {
        "requirement_id": "PURE-SM-REORDER-003",
        "text": "The Visual Reorder panel shall expose destination, compression, output PDF version, and Run controls.",
        "section": "3.5.2 Stimulus/Response Sequences",
        "source_pages": [17],
        "evidence_steps": [8, 28],
        "claims": ["The Visual Reorder panel exposes destination selection.", "The panel exposes compression and output PDF version controls.", "The panel exposes a Run control."],
    },
    {
        "requirement_id": "PURE-SM-COMPOSE-001",
        "text": "The Visual Document Composer shall provide source-document and output-composition thumbnail panels.",
        "section": "3.6.2 Stimulus/Response Sequences",
        "source_pages": [17, 18],
        "evidence_steps": [9, 27],
        "claims": ["The Visual Document Composer displays separate source and output thumbnail panels."],
    },
    {
        "requirement_id": "PURE-SM-COMPOSE-002",
        "text": "The Visual Document Composer shall expose add, move, delete, rotate, reverse, zoom, and preview controls for composing pages.",
        "section": "3.6.2 Stimulus/Response Sequences",
        "source_pages": [17, 18],
        "evidence_steps": [9, 27],
        "claims": ["The composer exposes controls for adding and moving pages.", "The composer exposes delete, rotate, reverse, and zoom controls.", "The composer exposes page-preview controls."],
    },
    {
        "requirement_id": "PURE-SM-ENV-001",
        "text": "The application shall expose Save Environment and Load Environment actions through the File menu and XML file dialogs.",
        "section": "3.7.2 Stimulus/Response Sequences",
        "source_pages": [18, 19, 22],
        "evidence_steps": [10, 11, 14, 15],
        "claims": ["The File menu exposes Save Environment and Load Environment actions.", "Environment selection uses an XML file dialog."],
    },
    {
        "requirement_id": "PURE-SM-LOG-001",
        "text": "The application shall provide a log panel that displays operational messages and exposes copy, clear, and save actions.",
        "section": "3.8.2 Stimulus/Response Sequences",
        "source_pages": [19, 20, 23],
        "evidence_steps": [12, 19],
        "claims": ["The application displays operational messages in a log panel.", "The log panel exposes copy, clear, and save actions."],
    },
    {
        "requirement_id": "PURE-SM-SETTINGS-001",
        "text": "The Settings panel shall expose language, look-and-feel, theme, log-level, thumbnail-library, update, alert, overwrite-confirmation, default-environment, and working-directory settings.",
        "section": "3.9.2 Stimulus/Response Sequences",
        "source_pages": [20, 21, 23],
        "evidence_steps": [13, 18],
        "claims": ["The Settings panel exposes language, look-and-feel, theme, and log-level controls.", "The panel exposes thumbnail-library, update, alert, and overwrite-confirmation controls.", "The panel exposes default-environment and working-directory controls."],
    },
    {
        "requirement_id": "PURE-SM-GUI-001",
        "text": "The GUI shall provide file dialogs that distinguish XML environment files from PDF document files.",
        "section": "4.1 User Interfaces - GUI",
        "source_pages": [22],
        "evidence_steps": [15, 16],
        "claims": ["The environment dialog filters XML files.", "The document dialog filters PDF files."],
    },
    {
        "requirement_id": "PURE-SM-GUI-002",
        "text": "The application shall provide an About panel with application, runtime, operating-system, and translation information.",
        "section": "4.1 User Interfaces - GUI",
        "source_pages": [23],
        "evidence_steps": [17],
        "claims": ["The About panel displays application and runtime information.", "The About panel displays operating-system and translation information."],
    },
    {
        "requirement_id": "PURE-SM-GUI-003",
        "text": "The loading screen shall report the PDFsam version and plugin-loading progress.",
        "section": "4.1 User Interfaces - GUI",
        "source_pages": [25],
        "evidence_steps": [22],
        "claims": ["The loading screen displays the PDFsam version.", "The loading screen reports plugin-loading progress."],
    },
]

# Most raw REQ-n fragments inherit their feature context directly. The log-level
# fragment explicitly crosses the Log Panel and Settings feature boundaries.
EXPLICIT_CONTEXT_TARGETS = {
    "2010 - split merge::3.8::3.8.3/req-1": [
        "PURE-SM-LOG-001",
        "PURE-SM-SETTINGS-001",
    ],
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _page_from_candidate(candidate: dict[str, Any]) -> int:
    match = re.search(r"page\.(\d+)", str(candidate.get("source_node_id", "")))
    return int(match.group(1)) if match else 0


def _feature_from_source(value: str) -> str | None:
    match = re.search(r"(?:^|::|\s)([34]\.\d)(?=\.\d|::|\s|$)", value)
    return match.group(1) if match else None


def _claim_entries(requirement_id: str, claims: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "claim_id": f"{requirement_id}-C{index}",
            "claim": claim,
            "claim_text": claim,
            "claim_kind": "OBSERVABLE_CORE",
            "claim_type": "OBSERVABLE",
            "importance": "CORE",
            "status": "MISSING",
            "source": "manual_candidate_decomposition",
            "evidence_steps": [],
        }
        for index, claim in enumerate(claims, start=1)
    ]


def _runtime_requirement(
    *,
    requirement_id: str,
    text: str,
    source_id: str,
    section: str,
    source_pages: list[int],
    evidence_steps: list[int],
    claims: list[str],
    origin: str,
    extraction_mode: str,
    parent_harvest_text: str | None = None,
) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "flow_id": FLOW_ID,
        "text": text,
        "scope": "multi_screen" if len(evidence_steps) > 1 else "single_screen",
        "tags": [
            "pure",
            f"pure_doc:{DOC_ID}",
            f"pure_section:{section}",
            f"pure_extraction:{extraction_mode}",
            *(["pure_requirement:contextualized_feature"] if extraction_mode == "manual_grouping" else []),
        ],
        "origin": origin,
        "review_status": "candidate",
        "step_indices": sorted(set(evidence_steps)),
        "rationale": "Frozen pre-label candidate with document and screenshot provenance; manual verification is pending.",
        "confidence": "MEDIUM",
        "source_harvest_id": source_id,
        "parent_harvest_text": parent_harvest_text,
        "source_document": SOURCE_PDF,
        "source_pages": source_pages,
        "source_section": section,
        "candidate_origin": "VISIBLE_CORE_REWRITE" if extraction_mode == "manual_grouping" else "DIRECT_FROM_HARVEST",
        "benchmark_decision": "REWRITE_TO_VISIBLE_CORE" if extraction_mode == "manual_grouping" else "DIRECT_INCLUDE",
        "grounding_scope": "DIRECT_FLOW_GROUNDED",
        "requirement_type": "FR",
        "ui_evaluability": "UI_VERIFIABLE",
        "non_evaluable_reason": "NONE",
        "visible_subtype": "TEXT_OR_ELEMENT_PRESENCE",
        "task_relevance": "HIGH",
        "claims": _claim_entries(requirement_id, claims),
        "evidence_steps": sorted(set(evidence_steps)),
        "uncertainty_reasons": [],
        "evidence_note": "Candidate evidence hints only; not a manual verification decision.",
    }


def build_outputs(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    extracted = [
        row
        for row in _load_jsonl(args.extracted)
        if row.get("record_type", "pdf_extraction") == "pdf_extraction"
    ]
    legacy_data = _load_json(args.legacy)
    legacy = [
        item for item in legacy_data.get("requirements", [])
        if item.get("requirement_id") in {f"PURE-REQ-{index:03d}" for index in range(1, 7)}
    ]

    runtime = []
    for item in legacy:
        cloned = dict(item)
        cloned["legacy_extraction"] = True
        cloned["source_document"] = SOURCE_PDF
        cloned.setdefault("source_pages", [])
        runtime.append(cloned)

    feature_steps = {
        "3.1": [3, 26], "3.2": [4, 24], "3.3": [5, 23], "3.4": [6, 25],
        "3.5": [8, 28], "3.7": [10, 11, 14, 15], "3.8": [12, 19], "3.9": [13, 18],
    }
    for requirement in CURATED_REQUIREMENTS:
        feature = _feature_from_source(requirement["section"])
        contextual_sources = [
            candidate for candidate in extracted
            if _feature_from_source(candidate["candidate_id"]) == feature
        ]
        source_ids = [str(candidate["candidate_id"]) for candidate in contextual_sources]
        parent_text = "\n\n".join(str(candidate["requirement_text"]) for candidate in contextual_sources)
        runtime.append(
            _runtime_requirement(
                requirement_id=requirement["requirement_id"],
                text=requirement["text"],
                source_id=f"composed:{feature}" if feature else requirement["requirement_id"],
                section=requirement["section"],
                source_pages=requirement["source_pages"],
                evidence_steps=requirement["evidence_steps"],
                claims=requirement["claims"],
                origin="human",
                extraction_mode="manual_grouping",
                parent_harvest_text=(
                    f"Contextual source records: {', '.join(source_ids)}\n\n{parent_text}"
                    if contextual_sources
                    else None
                ),
            )
        )

    review_rows: list[dict[str, Any]] = []
    for item in legacy:
        review_rows.append({
            "record_type": "legacy_extraction",
            "doc_id": DOC_ID,
            "candidate_id": item["requirement_id"],
            "requirement_text": item["text"],
            "review_decision": "preserve_for_provenance",
            "benchmark_requirement_ids": [item["requirement_id"]],
            "source_document": SOURCE_PDF,
        })
    for candidate in extracted:
        is_explicit = candidate["extraction_mode"] == "explicit_req"
        feature = _feature_from_source(candidate["candidate_id"])
        contextualized_ids = [
            item["requirement_id"]
            for item in CURATED_REQUIREMENTS
            if _feature_from_source(item["section"]) == feature
        ]
        contextualized_ids = EXPLICIT_CONTEXT_TARGETS.get(
            candidate["candidate_id"],
            contextualized_ids,
        )
        review_rows.append({
            "record_type": "pdf_extraction",
            **candidate,
            "source_page": _page_from_candidate(candidate),
            "review_decision": (
                "exclude_from_runtime_contextual_fragment"
                if is_explicit
                else "source_for_grouped_ui_requirement"
            ),
            "benchmark_requirement_ids": (
                contextualized_ids
                if is_explicit
                else contextualized_ids
            ),
            "contextualization_note": (
                "Retained verbatim for source provenance only. It is not a standalone runtime requirement; "
                "its feature-level context is represented by the listed composed requirements."
                if is_explicit
                else None
            ),
            "source_document": SOURCE_PDF,
        })

    return runtime, review_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze PURE Split/Merge extraction review and candidates.")
    parser.add_argument("--extracted", type=Path, required=True)
    parser.add_argument(
        "--legacy",
        type=Path,
        default=BASE_DIR / "data/generated/candidate_requirements" / FLOW_ID / "candidate_requirements.json",
    )
    parser.add_argument(
        "--candidate-out",
        type=Path,
        default=BASE_DIR / "data/generated/candidate_requirements" / FLOW_ID / "candidate_requirements.json",
    )
    parser.add_argument(
        "--review-out",
        type=Path,
        default=BASE_DIR / "data/annotations/requirement_inspection/pure" / f"{FLOW_ID}_extraction_review.jsonl",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runtime, review_rows = build_outputs(args)
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    payload = {
        "dataset": "pure",
        "flow_id": FLOW_ID,
        "flow_overview": "PURE PDF Split and Merge requirements frozen before manual verification.",
        "source_document": SOURCE_PDF,
        "frozen_at": timestamp,
        "requirements": runtime,
    }
    args.candidate_out.parent.mkdir(parents=True, exist_ok=True)
    args.candidate_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    args.review_out.parent.mkdir(parents=True, exist_ok=True)
    args.review_out.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in review_rows),
        encoding="utf-8",
    )
    print(f"requirements={len(runtime)} review_rows={len(review_rows)}")
    print(f"candidate_out={args.candidate_out}")
    print(f"review_out={args.review_out}")


if __name__ == "__main__":
    main()
