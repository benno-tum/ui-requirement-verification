from __future__ import annotations

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


FLOW_ID = "pure_2010_mashboot"
SOURCE_PDF = "data/raw/pure/req/2010 - mashboot.pdf"

LABELS = {
    "PURE-MB-NAV-001": "FULFILLED",
    "PURE-MB-DASHBOARD-001": "PARTIALLY_FULFILLED",
    "PURE-MB-DASHBOARD-002": "FULFILLED",
    "PURE-MB-CREATE-001": "PARTIALLY_FULFILLED",
    "PURE-MB-CREATE-002": "ABSTAIN",
    "PURE-MB-SCHEDULE-001": "PARTIALLY_FULFILLED",
    "PURE-MB-SCHEDULE-002": "PARTIALLY_FULFILLED",
    "PURE-MB-CAMPAIGN-001": "PARTIALLY_FULFILLED",
    "PURE-MB-CONTENT-001": "PARTIALLY_FULFILLED",
    "PURE-MB-EXPLORE-001": "ABSTAIN",
    "PURE-MB-SERVICE-001": "ABSTAIN",
}

# Claim index -> (manual status, evidence steps). Claims not listed are MISSING.
CLAIM_DECISIONS: dict[str, dict[int, tuple[str, list[int]]]] = {
    "PURE-MB-NAV-001": {index: ("SUPPORTED", [1, 2, 3]) for index in range(1, 5)},
    "PURE-MB-DASHBOARD-001": {
        1: ("SUPPORTED", [1]),
        2: ("SUPPORTED", [1]),
        3: ("SUPPORTED", [1]),
        4: ("SUPPORTED", [1]),
        5: ("SUPPORTED_WITH_CAVEAT", [1]),
        6: ("AMBIGUOUS", [1]),
    },
    "PURE-MB-DASHBOARD-002": {1: ("SUPPORTED", [1])},
    "PURE-MB-CREATE-001": {1: ("SUPPORTED", [2])},
    "PURE-MB-CREATE-002": {3: ("HIDDEN", [])},
    "PURE-MB-SCHEDULE-001": {1: ("SUPPORTED", [3])},
    "PURE-MB-SCHEDULE-002": {
        1: ("SUPPORTED", [3]),
        3: ("SUPPORTED", [3]),
        4: ("SUPPORTED", [3]),
    },
    "PURE-MB-CAMPAIGN-001": {
        1: ("SUPPORTED", [2]),
        2: ("SUPPORTED", [1, 3]),
        3: ("SUPPORTED", [1, 3]),
    },
    "PURE-MB-CONTENT-001": {
        1: ("SUPPORTED_WITH_CAVEAT", [1]),
        2: ("SUPPORTED", [1]),
        4: ("SUPPORTED", [1]),
    },
    "PURE-MB-EXPLORE-001": {
        1: ("MISSING", [1]),
        2: ("MISSING", [1]),
    },
    "PURE-MB-SERVICE-001": {
        1: ("HIDDEN", []),
        2: ("HIDDEN", []),
        3: ("HIDDEN", []),
    },
}


def _claim_text(claim: dict[str, Any]) -> str:
    return str(claim.get("claim") or claim.get("claim_text") or "").strip()


def _uncertainty_reasons(requirement_id: str) -> list[str]:
    if LABELS[requirement_id] == "FULFILLED":
        return []
    reasons = ["FLOW_COVERAGE_GAP"]
    if requirement_id in {"PURE-MB-DASHBOARD-001", "PURE-MB-CONTENT-001"}:
        reasons.append("EVIDENCE_INTERPRETATION_AMBIGUITY")
    if requirement_id in {"PURE-MB-CREATE-002", "PURE-MB-SERVICE-001"}:
        reasons.append("NONTRIVIAL_HIDDEN_PROPERTY")
    return reasons


def _evidence_note(requirement_id: str) -> str:
    notes = {
        "PURE-MB-NAV-001": "Steps 1-3 visibly show the Dashboard, Create, Schedule, and Explore tabs.",
        "PURE-MB-DASHBOARD-001": "Step 1 shows the graph and standard metrics; plugin provenance and selected-metric detail behavior are not directly established.",
        "PURE-MB-DASHBOARD-002": "Step 1 visibly associates a response/comment panel with the displayed campaign dashboard.",
        "PURE-MB-CREATE-001": "Step 2 directly supports new-campaign creation, but editing and filling an existing campaign are absent.",
        "PURE-MB-CREATE-002": "No screenshot shows the document-described Add Content view or its per-element edit and delete controls.",
        "PURE-MB-SCHEDULE-001": "Step 3 shows drag-and-drop calendar scheduling, but not the default midnight time or changing that time.",
        "PURE-MB-SCHEDULE-002": "Step 3 shows calendar scheduling and month navigation, but does not demonstrate deletion visualization.",
        "PURE-MB-CAMPAIGN-001": "Steps 1-3 show campaign names, content, and schedules; user or group permissions are not shown.",
        "PURE-MB-CONTENT-001": "Step 1 visibly exposes Blog/Status, Pictures, and Video content categories; audio is absent and text support is inferred from Blog/Status.",
        "PURE-MB-EXPLORE-001": "The Explore tab is visible, but no Explore-view screenshot demonstrates monitored searches or comment aggregation there.",
        "PURE-MB-SERVICE-001": "The screenshots do not show account association, external-service authentication, or the standardized interaction interface.",
    }
    return notes[requirement_id]


def build_item(candidate: dict[str, Any], timestamp: str, *, created_at: str | None = None) -> VerificationGoldItem:
    requirement_id = str(candidate["requirement_id"])
    label = LABELS[requirement_id]
    decisions = CLAIM_DECISIONS.get(requirement_id, {})
    claims: list[dict[str, Any]] = []
    evidence_steps: set[int] = set()
    for index, source_claim in enumerate(candidate.get("claims", []), start=1):
        status, steps = decisions.get(index, ("MISSING", list(candidate.get("step_indices", []))))
        evidence_steps.update(steps)
        claim_type = "HIDDEN" if status == "HIDDEN" else "OBSERVABLE"
        claims.append({
            "claim": _claim_text(source_claim),
            "status": status,
            "claim_type": claim_type,
            "importance": "CORE",
            "evidence_steps": steps,
            "evidence_units": [{"step_index": step, "evidence_type": "screen"} for step in steps],
        })

    ui_evaluability = (
        "NOT_UI_VERIFIABLE"
        if requirement_id == "PURE-MB-SERVICE-001"
        else "PARTIALLY_UI_VERIFIABLE"
        if requirement_id == "PURE-MB-CREATE-002"
        else "UI_VERIFIABLE"
    )
    pages = [int(page) for page in candidate.get("source_pages", [])]
    section = str(candidate.get("source_section") or "Unknown")
    tags = sorted(set([
        *candidate.get("tags", []),
        *(f"pure_pdf_page:{page}" for page in pages),
        f"pure_source_section:{section}",
    ]))
    item = VerificationGoldItem.from_dict({
        "requirement_id": requirement_id,
        "flow_id": FLOW_ID,
        "text": candidate["text"],
        "scope": candidate.get("scope", "multi_screen"),
        "tags": tags,
        "source_type": "requirements_candidate",
        "source_id": candidate.get("source_harvest_id") or requirement_id,
        "source_candidate_id": requirement_id,
        "source_harvest_id": candidate.get("source_harvest_id") or requirement_id,
        "step_indices": candidate.get("step_indices", []),
        "requirement_type": candidate.get("requirement_type", "FR"),
        "ui_evaluability": ui_evaluability,
        "visible_subtype": candidate.get("visible_subtype", "TEXT_OR_ELEMENT_PRESENCE"),
        "annotation_notes": (
            f"Draft manual annotation from {SOURCE_PDF}, section {section}, PDF page(s) {pages}. "
            "Prepared after the pipeline run was inspected; use as a post-hoc review draft, not blinded gold."
        ),
        "annotated_by": "codex_draft",
        "manual_verification_label": label.lower(),
        "manual_verification_notes": "Post-run manual suggestion for independent human review.",
        "verification_label": label,
        "uncertainty_reasons": _uncertainty_reasons(requirement_id),
        "notes": [],
        "claims": claims,
        "evidence_steps": sorted(evidence_steps),
        "evidence_units": [
            {"step_index": step, "evidence_type": "screen"}
            for step in sorted(evidence_steps)
        ],
        "evidence_note": _evidence_note(requirement_id),
        "rationale": _evidence_note(requirement_id),
        "review_status": "needs_review",
        "created_at": created_at or timestamp,
        "updated_at": timestamp,
    })
    validation = validate_verification_gold_item(item)
    if validation.errors:
        messages = "; ".join(f"{issue.field}: {issue.message}" for issue in validation.errors)
        raise ValueError(f"{requirement_id}: {messages}")
    return item


_REVIEW_FIELDS = {
    "ui_evaluability",
    "annotation_notes",
    "annotated_by",
    "manual_verification_label",
    "manual_verification_notes",
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


def preserve_accepted_review(
    generated: VerificationGoldItem,
    existing: VerificationGoldItem | None,
) -> VerificationGoldItem:
    """Never overwrite a human-accepted annotation during regeneration."""
    if existing is None or existing.review_status != "accepted":
        return generated
    merged = generated.to_dict()
    previous = existing.to_dict()
    for field in _REVIEW_FIELDS:
        if field in previous:
            merged[field] = previous[field]
    return VerificationGoldItem.from_dict(merged)


def main() -> None:
    candidate_path = BASE_DIR / "data/generated/candidate_requirements" / FLOW_ID / "candidate_requirements.json"
    out_path = BASE_DIR / "data/annotations/verification_gold" / FLOW_ID / "verification_gold.json"
    candidates = json.loads(candidate_path.read_text(encoding="utf-8"))
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    existing_by_id = (
        {item.requirement_id: item for item in VerificationGoldFile.load(out_path).items}
        if out_path.exists()
        else {}
    )
    items = []
    for candidate in candidates["requirements"]:
        existing = existing_by_id.get(candidate["requirement_id"])
        generated = build_item(
            candidate,
            timestamp,
            created_at=existing.created_at if existing else None,
        )
        items.append(preserve_accepted_review(generated, existing))
    VerificationGoldFile(dataset="pure", flow_id=FLOW_ID, items=items).save(out_path)
    distribution = {label: sum(item.verification_label.value == label for item in items) for label in sorted(set(LABELS.values()))}
    print(f"items={len(items)} labels={distribution}")
    print(f"out={out_path}")


if __name__ == "__main__":
    main()
