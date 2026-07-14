from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ui_verifier.verification.label_validation import validate_verification_gold_item
from ui_verifier.verification.schemas import VerificationGoldFile, VerificationGoldItem


FLOW_ID = "pure_2010_split_merge"
SOURCE_PDF = "data/raw/pure/req/2010 - split merge.pdf"

LEGACY_PAGE_SECTION = {
    "PURE-REQ-001": ([7], "2.5 Design and Implementation Constraints"),
    "PURE-REQ-002": ([12], "3.2.2 Stimulus/Response Sequences"),
    "PURE-REQ-003": ([12], "3.2.3 Functional Requirements"),
    "PURE-REQ-004": ([13], "3.3.2 Stimulus/Response Sequences"),
    "PURE-REQ-005": ([31], "5.2 Safety Requirements"),
    "PURE-REQ-006": ([31], "5.4 Software Quality Attributes"),
}

LEGACY_EVIDENCE_STEPS = {
    "PURE-REQ-002": [4, 24],
    "PURE-REQ-003": [4, 24],
    "PURE-REQ-004": [5, 23],
    "PURE-REQ-005": [19],
    "PURE-REQ-006": [1, 3, 4, 5, 6, 9, 12, 24],
}

PURE_REQ_006_CLAIMS = [
    "The application provides a graphical interface.",
    "The graphical interface is pleasant and user friendly.",
    "The application provides relatively simple functions.",
    "Any user can operate PDFsam without specific knowledge or experience.",
    "The user manuals or embedded help messages enable inexperienced users to operate PDFsam.",
    "Users can provide PDF documents as inputs.",
    "Users can perform every action in only a few clicks.",
]

FULFILLED_IDS = {
    "PURE-REQ-002",
    "PURE-REQ-004",
    "PURE-SM-FR-3_8-REQ-1",
    "PURE-SM-UI-001",
    "PURE-SM-SPLIT-001",
    "PURE-SM-SPLIT-002",
    "PURE-SM-SPLIT-003",
    "PURE-SM-SPLIT-004",
    "PURE-SM-MERGE-001",
    "PURE-SM-MERGE-002",
    "PURE-SM-MERGE-003",
    "PURE-SM-MIX-001",
    "PURE-SM-MIX-002",
    "PURE-SM-ROTATE-001",
    "PURE-SM-ROTATE-002",
    "PURE-SM-REORDER-001",
    "PURE-SM-REORDER-002",
    "PURE-SM-REORDER-003",
    "PURE-SM-COMPOSE-001",
    "PURE-SM-COMPOSE-002",
    "PURE-SM-ENV-001",
    "PURE-SM-LOG-001",
    "PURE-SM-SETTINGS-001",
    "PURE-SM-GUI-001",
    "PURE-SM-GUI-002",
    "PURE-SM-GUI-003",
}

PARTIALLY_FULFILLED_IDS = {"PURE-REQ-006"}

NOT_UI_IDS = {
    "PURE-REQ-001",
    "PURE-SM-FR-3_7-REQ-1",
}

PARTIAL_UI_IDS = {
    "PURE-REQ-005",
    "PURE-REQ-006",
    "PURE-SM-FR-3_1-REQ-2",
    "PURE-SM-FR-3_2-REQ-2",
    "PURE-SM-FR-3_4-REQ-1",
    "PURE-SM-FR-3_5-REQ-1",
    "PURE-SM-FR-3_9-REQ-1",
}

AMBIGUOUS_IDS = {
    "PURE-REQ-003",
    "PURE-SM-FR-3_2-REQ-1",
    "PURE-SM-FR-3_7-REQ-1",
}

QUANTIFIED_IDS = {
    "PURE-SM-FR-3_1-REQ-1",
    "PURE-SM-FR-3_3-REQ-1",
    "PURE-SM-FR-3_5-REQ-2",
}

COMPRESSION_IDS = {
    "PURE-SM-FR-3_1-REQ-2",
    "PURE-SM-FR-3_2-REQ-2",
    "PURE-SM-FR-3_4-REQ-1",
    "PURE-SM-FR-3_5-REQ-1",
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _claim_text(claim: dict[str, Any]) -> str:
    return str(claim.get("claim") or claim.get("claim_text") or "").strip()


def _source_pages(item: dict[str, Any]) -> list[int]:
    pages = [int(page) for page in item.get("source_pages", []) if int(page) > 0]
    if pages:
        return sorted(set(pages))
    return LEGACY_PAGE_SECTION.get(item["requirement_id"], ([], ""))[0]


def _source_section(item: dict[str, Any]) -> str:
    return str(item.get("source_section") or LEGACY_PAGE_SECTION.get(item["requirement_id"], ([], "Unknown"))[1])


def _uncertainty_reasons(requirement_id: str) -> list[str]:
    if requirement_id in FULFILLED_IDS:
        return []
    if requirement_id in AMBIGUOUS_IDS:
        return ["TEXTUAL_AMBIGUITY", "FLOW_COVERAGE_GAP"]
    if requirement_id in QUANTIFIED_IDS:
        return ["QUANTIFIER_OR_COMPLETENESS_AMBIGUITY", "FLOW_COVERAGE_GAP"]
    if requirement_id in COMPRESSION_IDS:
        return ["FLOW_COVERAGE_GAP", "UNVERIFIED_SYSTEM_OUTCOME"]
    if requirement_id == "PURE-REQ-001":
        return ["NONTRIVIAL_HIDDEN_PROPERTY"]
    if requirement_id == "PURE-REQ-005":
        return ["FLOW_COVERAGE_GAP", "NONTRIVIAL_HIDDEN_PROPERTY"]
    if requirement_id == "PURE-REQ-006":
        return [
            "TEXTUAL_AMBIGUITY",
            "QUANTIFIER_OR_COMPLETENESS_AMBIGUITY",
            "FLOW_COVERAGE_GAP",
            "NONTRIVIAL_HIDDEN_PROPERTY",
        ]
    if requirement_id == "PURE-SM-FR-3_9-REQ-1":
        return ["FLOW_COVERAGE_GAP", "UNVERIFIED_SYSTEM_OUTCOME"]
    return ["FLOW_COVERAGE_GAP"]


def _claim_status_and_type(requirement_id: str, claim_index: int) -> tuple[str, str]:
    if requirement_id in FULFILLED_IDS:
        return "SUPPORTED", "OBSERVABLE"
    if requirement_id == "PURE-REQ-006":
        if claim_index in {1, 6}:
            return "SUPPORTED", "OBSERVABLE"
        if claim_index in {2, 3}:
            return "AMBIGUOUS", "OBSERVABLE"
        if claim_index == 4:
            return "HIDDEN", "HIDDEN"
        return "MISSING", "OBSERVABLE"
    if requirement_id in {"PURE-REQ-001", "PURE-SM-FR-3_7-REQ-1"}:
        return ("AMBIGUOUS", "HIDDEN") if requirement_id == "PURE-SM-FR-3_7-REQ-1" else ("HIDDEN", "HIDDEN")
    if requirement_id == "PURE-REQ-005" and claim_index <= 2:
        return "HIDDEN", "HIDDEN"
    if requirement_id in AMBIGUOUS_IDS:
        return "AMBIGUOUS", "OBSERVABLE"
    return "MISSING", "OBSERVABLE"


def _claim_evidence_steps(
    requirement_id: str,
    claim_index: int,
    status: str,
    claim_type: str,
    item_steps: list[int],
) -> list[int]:
    if requirement_id == "PURE-REQ-006":
        return {
            1: [1, 12],
            2: [1, 4, 9, 12],
            3: [1, 4, 9, 12],
            4: [],
            5: [1, 4, 9],
            6: [3, 4, 5, 6, 9, 24],
            7: [3, 4, 5, 6, 9],
        }.get(claim_index, [])
    if claim_type == "HIDDEN":
        return []
    if status == "SUPPORTED":
        return item_steps
    if requirement_id == "PURE-REQ-005":
        return [19]
    return item_steps


def _evidence_note(requirement_id: str, steps: list[int], label: str) -> str:
    if label == "FULFILLED":
        return f"Steps {', '.join(map(str, steps))} visibly show the required controls or information."
    if requirement_id in NOT_UI_IDS:
        return "The requirement concerns implementation, licensing, platform, or abstract usability properties that screenshots cannot establish."
    if requirement_id == "PURE-REQ-005":
        return "Step 19 shows ordinary log output, but the flow contains no invalid-input, error-help, or input-file-integrity demonstration."
    if requirement_id == "PURE-REQ-006":
        return (
            "The screenshots directly show a graphical interface and PDF input controls. They do not establish "
            "subjective usability, inexperienced-user success, or the universal 'every action in a few clicks' claim."
        )
    return f"Steps {', '.join(map(str, steps))} show the relevant UI surface, but not the required constraint, validation, or post-action behavior."


def _rationale(requirement_id: str, label: str) -> str:
    if label == "FULFILLED":
        return "All UI-observable core claims are directly supported by the cited screenshots."
    if requirement_id in NOT_UI_IDS:
        return "A reliable positive or negative decision cannot be made from static UI evidence for this non-visual or ill-defined requirement."
    if requirement_id == "PURE-REQ-006":
        return (
            "The graphical interface and PDF-input capabilities are visibly supported, while subjective usability, "
            "manual-assisted operation, universal-user, and few-click claims remain ambiguous, hidden, or missing."
        )
    return "The relevant screen is present, but the screenshot set does not demonstrate the stated behavioral constraint or outcome; missing evidence is not counter-evidence."


def build_gold_item(item: dict[str, Any], timestamp: str) -> VerificationGoldItem:
    requirement_id = item["requirement_id"]
    label = (
        "FULFILLED" if requirement_id in FULFILLED_IDS
        else "PARTIALLY_FULFILLED" if requirement_id in PARTIALLY_FULFILLED_IDS
        else "ABSTAIN"
    )
    ui_evaluability = (
        "NOT_UI_VERIFIABLE" if requirement_id in NOT_UI_IDS
        else "PARTIALLY_UI_VERIFIABLE" if requirement_id in PARTIAL_UI_IDS
        else "UI_VERIFIABLE"
    )
    steps = (
        [] if ui_evaluability == "NOT_UI_VERIFIABLE"
        else LEGACY_EVIDENCE_STEPS.get(requirement_id, sorted(set(item.get("evidence_steps", []))))
    )
    claims = []
    source_claims = (
        [{"claim": claim} for claim in PURE_REQ_006_CLAIMS]
        if requirement_id == "PURE-REQ-006"
        else item.get("claims", [])
    )
    for index, claim in enumerate(source_claims, start=1):
        text = _claim_text(claim)
        if not text:
            continue
        status, claim_type = _claim_status_and_type(requirement_id, index)
        claim_steps = _claim_evidence_steps(requirement_id, index, status, claim_type, steps)
        claims.append({
            "claim": text,
            "status": status,
            "claim_type": claim_type,
            "importance": "CORE",
            "evidence_steps": claim_steps,
            "evidence_units": [{"step_index": step, "evidence_type": "screen"} for step in claim_steps],
            "note": (
                "Visible screenshot support." if status == "SUPPORTED"
                else "Not demonstrable from the available static screenshot set."
            ),
        })

    pages = _source_pages(item)
    section = _source_section(item)
    tags = list(item.get("tags", []))
    tags.extend([f"pure_pdf_page:{page}" for page in pages])
    tags.append(f"pure_source_section:{section}")
    annotation_notes = (
        f"Draft manual annotation from {SOURCE_PDF}, section {section}, PDF page(s) {pages or ['unknown']}. "
        + (
            "Revised after manual reassessment of the cited screenshots."
            if requirement_id == "PURE-REQ-006"
            else "The pre-label model verdict was not inspected."
        )
    )
    gold_dict = {
        "requirement_id": requirement_id,
        "flow_id": FLOW_ID,
        "text": item["text"],
        "scope": item.get("scope", "multi_screen"),
        "tags": sorted(set(tags)),
        "source_type": "requirements_candidate",
        "source_id": item.get("source_harvest_id") or requirement_id,
        "source_candidate_id": requirement_id,
        "source_harvest_id": item.get("source_harvest_id") or requirement_id,
        "step_indices": sorted(set(item.get("step_indices", []))),
        "requirement_type": item.get("requirement_type", "FR"),
        "ui_evaluability": ui_evaluability,
        "visible_subtype": item.get("visible_subtype", "NONE"),
        "annotation_notes": annotation_notes,
        "annotated_by": "codex_draft",
        "manual_verification_label": label.lower(),
        "manual_verification_notes": "Independent draft for human review; generated after the blinded baseline completed.",
        "verification_label": label,
        "uncertainty_reasons": _uncertainty_reasons(requirement_id),
        "notes": [],
        "claims": claims,
        "evidence_steps": steps,
        "evidence_units": [{"step_index": step, "evidence_type": "screen"} for step in steps],
        "evidence_note": _evidence_note(requirement_id, steps, label),
        "rationale": _rationale(requirement_id, label),
        "review_status": "needs_review",
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    return VerificationGoldItem.from_dict(gold_dict)


_ANNOTATION_FIELDS = {
    "ui_evaluability",
    "annotation_notes",
    "annotated_by",
    "manual_verification_label",
    "manual_verification_notes",
    "intended_label",
    "verification_label",
    "uncertainty_reasons",
    "notes",
    "claims",
    "evidence_steps",
    "evidence_units",
    "evidence_note",
    "rationale",
    "review_status",
    "created_at",
    "updated_at",
}


def _preserve_existing_annotation(
    generated: VerificationGoldItem,
    existing: VerificationGoldItem | None,
) -> VerificationGoldItem:
    """Keep reviewed human labels while refreshing candidate provenance and scope."""
    if existing is None:
        return generated
    merged = generated.to_dict()
    previous = existing.to_dict()
    for field in _ANNOTATION_FIELDS:
        if field in previous:
            merged[field] = previous[field]
    return VerificationGoldItem.from_dict(merged)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the independent draft gold for PURE Split/Merge.")
    parser.add_argument(
        "--candidates",
        type=Path,
        default=BASE_DIR / "data/generated/candidate_requirements" / FLOW_ID / "candidate_requirements.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=BASE_DIR / "data/annotations/verification_gold" / FLOW_ID / "verification_gold.json",
    )
    parser.add_argument(
        "--no-preserve-existing-annotations",
        action="store_true",
        help="Rebuild all annotation fields instead of preserving reviewed items already present at --out.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = _load_json(args.candidates)
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    existing_by_id: dict[str, VerificationGoldItem] = {}
    if args.out.exists() and not args.no_preserve_existing_annotations:
        existing_by_id = {
            item.requirement_id: item
            for item in VerificationGoldFile.load(args.out).items
        }
    items = [
        _preserve_existing_annotation(
            build_gold_item(item, timestamp),
            existing_by_id.get(item["requirement_id"]),
        )
        for item in data["requirements"]
    ]
    errors = []
    for item in items:
        result = validate_verification_gold_item(item)
        errors.extend(f"{item.requirement_id}:{issue.field}:{issue.message}" for issue in result.errors)
    if errors:
        raise ValueError("Invalid verification gold:\n" + "\n".join(errors))
    gold = VerificationGoldFile(dataset="pure", flow_id=FLOW_ID, items=items)
    gold.save(args.out)
    print(f"items={len(items)} fulfilled={sum(item.verification_label.value == 'FULFILLED' for item in items)} abstain={sum(item.verification_label.value == 'ABSTAIN' for item in items)}")
    print(f"out={args.out}")


if __name__ == "__main__":
    main()
