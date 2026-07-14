from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ui_verifier.requirement_inspection.pure_pdf_loader import (
    extract_pure_pdf_requirement_candidates_from_file,
)


FLOW_ID = "pure_2010_mashboot"
DOC_ID = "2010 - mashboot"
SOURCE_PDF = "data/raw/pure/req/2010 - mashboot.pdf"


DOCUMENT_SECTIONS = [
    {
        "source_id": "mashboot::2.1.2",
        "section": "2.1.2 User Interface",
        "pages": [5],
        "text": (
            "The user interface consists of a web front end with tabs to separate the various workflow areas. "
            "To create content, the user is provided with a calendar scheduling tool and a content editor. "
            "Additionally, there is a monitoring dashboard which gives the user a view on responses to the "
            "content in any given campaign. Finally, there is an explore view that gives the user a portal with "
            "which they can keep tabs on topics of interest in social media."
        ),
    },
    {
        "source_id": "mashboot::4",
        "section": "4 User Interface",
        "pages": [9],
        "text": (
            "The user interface will consist of a tabbed navigation bar that unifies the sitewide navigation, "
            "as well as module specific navigation as needed. Tabs: Dashboard, Create, Schedule, Explore."
        ),
    },
    {
        "source_id": "mashboot::4.1",
        "section": "4.1 Dashboard",
        "pages": [10, 11],
        "text": (
            "The dashboard consists of graphs and charts to give the user a quick view on how their campaigns "
            "are performing. Metrics include clickthrough rate, page views, and number of comments. Service "
            "plugins can define additional specialized metrics to track. A panel is available to give more "
            "information on each metric as it is selected."
        ),
    },
    {
        "source_id": "mashboot::4.1.1",
        "section": "4.1.1 Create",
        "pages": [10, 12],
        "text": (
            "This view allows users to create campaigns and fill them with content. This view is also used when "
            "users need to edit an existing campaign. A user can add content via the add content button near the "
            "top of the view. This prompts the user to select the content type, populated by services the user "
            "currently has access to. It creates a section that allows the user to add individual elements of "
            "that content type, each individually scheduled. Each row allows the user to schedule, edit, or delete "
            "that content type."
        ),
    },
    {
        "source_id": "mashboot::4.1.2",
        "section": "4.1.2 Schedule",
        "pages": [10, 13],
        "text": (
            "Users can drag items from the left hand bucket of content to the calendar to schedule content. The "
            "content receives a default go-live time of 12am on the day it is dragged. The user may click scheduled "
            "content and assign a different time. The calendar manages when content goes live and visually "
            "represents actions taken on content, including when it is deleted. The user can page month to month "
            "to schedule content to any desired day."
        ),
    },
    {
        "source_id": "mashboot::4.1.3",
        "section": "4.1.3 Explore",
        "pages": [10],
        "text": (
            "The Explore view allows users to get a pulse on social-media information, set up monitored searches "
            "for services supporting keyword search through an API, and aggregate comments on content published "
            "as part of a campaign."
        ),
    },
]


COMPOSED_REQUIREMENTS: list[dict[str, Any]] = [
    {
        "requirement_id": "PURE-MB-NAV-001",
        "text": "The Mashbot web interface shall provide tabbed navigation for Dashboard, Create, Schedule, and Explore workflows.",
        "section_ids": ["mashboot::2.1.2", "mashboot::4"],
        "source_ids": [],
        "evidence_steps": [1, 2, 3],
        "claims": [
            "The web interface exposes a Dashboard tab.",
            "The web interface exposes a Create tab.",
            "The web interface exposes a Schedule tab.",
            "The web interface exposes an Explore tab.",
        ],
    },
    {
        "requirement_id": "PURE-MB-DASHBOARD-001",
        "text": "The Dashboard shall summarize campaign performance through graphs, standard metrics, plugin-defined metrics, and metric-detail information.",
        "section_ids": ["mashboot::4.1"],
        "source_ids": [],
        "evidence_steps": [1],
        "claims": [
            "The Dashboard displays campaign-performance graphs or charts.",
            "The Dashboard includes a clickthrough-rate metric.",
            "The Dashboard includes a page-views metric.",
            "The Dashboard includes a number-of-comments metric.",
            "The Dashboard supports plugin-defined metrics.",
            "The Dashboard provides additional information for a selected metric.",
        ],
    },
    {
        "requirement_id": "PURE-MB-DASHBOARD-002",
        "text": "The monitoring Dashboard shall give users a view of responses to content in a campaign.",
        "section_ids": ["mashboot::2.1.2", "mashboot::4.1"],
        "source_ids": [],
        "evidence_steps": [1],
        "claims": ["The Dashboard displays responses associated with campaign content."],
    },
    {
        "requirement_id": "PURE-MB-CREATE-001",
        "text": "The Create view shall allow users to create campaigns, edit existing campaigns, and fill campaigns with content.",
        "section_ids": ["mashboot::4.1.1"],
        "source_ids": ["2010 - mashboot::3.2::3.2.2/req-0480", "2010 - mashboot::3.2::3.2.2/req-0490"],
        "evidence_steps": [2],
        "claims": [
            "The Create view allows a user to create a campaign.",
            "The Create view allows a user to edit an existing campaign.",
            "The Create view allows a user to fill a campaign with content.",
        ],
    },
    {
        "requirement_id": "PURE-MB-CREATE-002",
        "text": "The Create view shall let users add service-supported content elements and schedule, edit, or delete each element.",
        "section_ids": ["mashboot::4.1.1"],
        "source_ids": ["2010 - mashboot::3.2::3.2.1/req-0210"],
        "evidence_steps": [2],
        "claims": [
            "The Create view provides an Add Content action.",
            "The available content types depend on services accessible to the user.",
            "Adding a content type creates a section for individually scheduled content elements.",
            "Each content element can be scheduled.",
            "Each content element can be edited.",
            "Each content element can be deleted.",
        ],
    },
    {
        "requirement_id": "PURE-MB-SCHEDULE-001",
        "text": "The Schedule view shall support dragging content to a calendar, assigning a default midnight go-live time, and changing that time.",
        "section_ids": ["mashboot::4.1.2"],
        "source_ids": ["2010 - mashboot::3.2::3.2.2/req-0530"],
        "evidence_steps": [3],
        "claims": [
            "Users can drag content from a content bucket to the calendar to schedule it.",
            "Dragged content receives a default go-live time of 12am on the selected day.",
            "Users can select scheduled content and assign a different go-live time.",
        ],
    },
    {
        "requirement_id": "PURE-MB-SCHEDULE-002",
        "text": "The calendar shall visualize content go-live and deletion actions and allow month-to-month scheduling.",
        "section_ids": ["mashboot::4.1.2"],
        "source_ids": [],
        "evidence_steps": [3],
        "claims": [
            "The calendar visually represents when content goes live.",
            "The calendar visually represents when content is deleted.",
            "Users can page between calendar months.",
            "Users can schedule content on a desired day.",
        ],
    },
    {
        "requirement_id": "PURE-MB-CAMPAIGN-001",
        "text": "A Mashbot campaign shall contain a name, pieces of content, a schedule, and user or group permissions.",
        "section_ids": [],
        "source_ids": [
            "2010 - mashboot::3.2::3.2.2/req-0480",
            "2010 - mashboot::3.2::3.2.2/req-0490",
            "2010 - mashboot::3.2::3.2.2/req-0500",
            "2010 - mashboot::3.2::3.2.2/req-0510",
            "2010 - mashboot::3.2::3.2.2/req-0520",
        ],
        "evidence_steps": [1, 2, 3],
        "claims": [
            "A campaign includes a name.",
            "A campaign includes pieces of content.",
            "A campaign includes a schedule.",
            "A campaign includes user or group permissions.",
        ],
    },
    {
        "requirement_id": "PURE-MB-CONTENT-001",
        "text": "Mashbot campaign content shall support text, image, audio, and video forms.",
        "section_ids": [],
        "source_ids": [
            "2010 - mashboot::3.2::3.2.2/req-0540",
            "2010 - mashboot::3.2::3.2.2/req-0550",
            "2010 - mashboot::3.2::3.2.2/req-0560",
            "2010 - mashboot::3.2::3.2.2/req-0570",
            "2010 - mashboot::3.2::3.2.2/req-0580",
        ],
        "evidence_steps": [1, 2],
        "claims": [
            "Campaign content supports text.",
            "Campaign content supports images.",
            "Campaign content supports audio.",
            "Campaign content supports video.",
        ],
    },
    {
        "requirement_id": "PURE-MB-EXPLORE-001",
        "text": "The Explore view shall support monitored keyword searches and aggregate comments from campaign content.",
        "section_ids": ["mashboot::2.1.2", "mashboot::4.1.3"],
        "source_ids": [],
        "evidence_steps": [],
        "claims": [
            "The Explore view supports monitored keyword searches for compatible services.",
            "The Explore view aggregates comments from content published within a campaign.",
        ],
    },
    {
        "requirement_id": "PURE-MB-SERVICE-001",
        "text": "Mashbot shall associate Mashbot accounts with external service accounts and provide authentication and standardized interaction interfaces.",
        "section_ids": [],
        "source_ids": [
            "2010 - mashboot::3.2::3.2.3/req-0590",
            "2010 - mashboot::3.2::3.2.3/req-0600",
            "2010 - mashboot::3.2::3.2.3/req-0610",
        ],
        "evidence_steps": [],
        "claims": [
            "Mashbot accounts can be associated with external service accounts.",
            "Mashbot provides an interface for authenticating to an external service account.",
            "Mashbot provides a standardized method for interacting with external service accounts.",
        ],
    },
]


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
            "source": "document_contextualization",
            "evidence_steps": [],
        }
        for index, claim in enumerate(claims, start=1)
    ]


def _source_page(candidate: dict[str, Any]) -> int | None:
    match = re.search(r"PDF page (\d+)", str(candidate.get("context_text") or ""))
    return int(match.group(1)) if match else None


def build_outputs(pdf_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    extracted = [
        candidate.to_dict()
        for candidate in extract_pure_pdf_requirement_candidates_from_file(
            pdf_path,
            include_structural_fallback=False,
        )
    ]
    extracted_by_id = {item["candidate_id"]: item for item in extracted}
    sections_by_id = {item["source_id"]: item for item in DOCUMENT_SECTIONS}

    source_to_requirements: dict[str, list[str]] = {}
    for requirement in COMPOSED_REQUIREMENTS:
        for source_id in [*requirement["source_ids"], *requirement["section_ids"]]:
            source_to_requirements.setdefault(source_id, []).append(requirement["requirement_id"])

    runtime = []
    for requirement in COMPOSED_REQUIREMENTS:
        source_records = [
            *(extracted_by_id[source_id] for source_id in requirement["source_ids"]),
            *(sections_by_id[source_id] for source_id in requirement["section_ids"]),
        ]
        source_ids = [
            str(record.get("candidate_id") or record.get("source_id"))
            for record in source_records
        ]
        source_text = "\n\n".join(
            str(record.get("requirement_text") or record.get("text"))
            for record in source_records
        )
        pages = sorted({
            page
            for record in source_records
            for page in (
                record.get("pages", [])
                if "pages" in record
                else [_source_page(record)]
            )
            if page is not None
        })
        runtime.append({
            "requirement_id": requirement["requirement_id"],
            "flow_id": FLOW_ID,
            "text": requirement["text"],
            "scope": "multi_screen" if len(requirement["evidence_steps"]) > 1 else "single_screen",
            "tags": [
                "pure",
                f"pure_doc:{DOC_ID}",
                "pure_extraction:document_contextualization",
                "pure_requirement:contextualized_feature",
            ],
            "origin": "human",
            "review_status": "candidate",
            "step_indices": sorted(set(requirement["evidence_steps"])),
            "rationale": "Composed only from cited Mashboot PDF sections and numbered requirements; requires manual verification review.",
            "confidence": "MEDIUM",
            "source_harvest_id": "composed:" + "+".join(source_ids),
            "parent_harvest_text": (
                f"Contextual source records: {', '.join(source_ids)}\n\n{source_text}"
            ),
            "source_document": SOURCE_PDF,
            "source_pages": pages,
            "source_section": "; ".join(sorted({
                str(record.get("section_title") or record.get("section"))
                for record in source_records
            })),
            "candidate_origin": "VISIBLE_CORE_REWRITE",
            "benchmark_decision": "REWRITE_TO_VISIBLE_CORE",
            "grounding_scope": "DIRECT_FLOW_GROUNDED",
            "requirement_type": "FR",
            "ui_evaluability": "UI_VERIFIABLE",
            "non_evaluable_reason": "NONE",
            "visible_subtype": "TEXT_OR_ELEMENT_PRESENCE",
            "task_relevance": "HIGH",
            "claims": _claim_entries(requirement["requirement_id"], requirement["claims"]),
            "evidence_steps": sorted(set(requirement["evidence_steps"])),
            "uncertainty_reasons": [],
            "evidence_note": "Candidate evidence hints only; not a manual verification decision.",
        })

    review_rows: list[dict[str, Any]] = [{
        "record_type": "legacy_extraction",
        "doc_id": DOC_ID,
        "candidate_id": "PURE-REQ-001",
        "requirement_text": (
            "13. A member should be able to see responses to blog posts related to the campaign. "
            "14. An admin should be able to perform user account actions in bulk 15. An admin should be able to see all campaigns"
        ),
        "review_decision": "retire_concatenated_use_cases",
        "benchmark_requirement_ids": [],
        "review_reason": "The seed merged three unrelated use cases and lost their numbering context.",
        "source_document": SOURCE_PDF,
    }]
    for item in extracted:
        source_id = item["candidate_id"]
        benchmark_ids = source_to_requirements.get(source_id, [])
        review_rows.append({
            "record_type": "pdf_extraction",
            **item,
            "source_page": _source_page(item),
            "review_decision": (
                "source_for_contextualized_requirement"
                if benchmark_ids
                else "exclude_from_runtime_no_matching_ui_flow"
            ),
            "benchmark_requirement_ids": benchmark_ids,
            "source_document": SOURCE_PDF,
        })
    for section in DOCUMENT_SECTIONS:
        review_rows.append({
            "record_type": "document_section",
            "doc_id": DOC_ID,
            "candidate_id": section["source_id"],
            "requirement_text": section["text"],
            "section_title": section["section"],
            "source_pages": section["pages"],
            "extraction_mode": "document_section_context",
            "source_format": "pdf",
            "review_decision": "source_for_contextualized_requirement",
            "benchmark_requirement_ids": source_to_requirements.get(section["source_id"], []),
            "source_document": SOURCE_PDF,
        })

    payload = {
        "dataset": "pure",
        "flow_id": FLOW_ID,
        "flow_overview": "Document-contextualized Mashboot requirements grounded only in the 2010 Mashboot SRS.",
        "source_document": SOURCE_PDF,
        "frozen_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "requirements": runtime,
    }
    return payload, review_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build document-contextualized PURE Mashboot candidates.")
    parser.add_argument("--pdf", type=Path, default=BASE_DIR / SOURCE_PDF)
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
    payload, review_rows = build_outputs(args.pdf)
    args.candidate_out.parent.mkdir(parents=True, exist_ok=True)
    args.candidate_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    args.review_out.parent.mkdir(parents=True, exist_ok=True)
    args.review_out.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in review_rows),
        encoding="utf-8",
    )
    print(f"requirements={len(payload['requirements'])} review_rows={len(review_rows)}")
    print(f"candidate_out={args.candidate_out}")
    print(f"review_out={args.review_out}")


if __name__ == "__main__":
    main()
