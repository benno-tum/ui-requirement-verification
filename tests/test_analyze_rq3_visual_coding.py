from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.analyze_rq3_visual_coding import apply_author_boundary_review


def _audit() -> dict:
    return {
        "items": [
            {
                "audit_item_id": "RQ3-0001",
                "flow_id": "flow-a",
                "requirement_id": "REQ-01",
                "gold_label": "PARTIALLY_FULFILLED",
                "predicted_label": "ABSTAIN",
                "llm_visual_review": {
                    "primary_category": "LABEL_BOUNDARY_DISAGREEMENT",
                    "visible_evidence_rationale": "Original visual rationale A.",
                },
            },
            {
                "audit_item_id": "RQ3-0002",
                "flow_id": "flow-b",
                "requirement_id": "REQ-02",
                "gold_label": "PARTIALLY_FULFILLED",
                "predicted_label": "ABSTAIN",
                "llm_visual_review": {
                    "primary_category": "LABEL_BOUNDARY_DISAGREEMENT",
                    "visible_evidence_rationale": "Original visual rationale B.",
                },
            },
        ]
    }


def _boundary_review() -> dict:
    return {
        "schema_version": "rq3_author_boundary_consistency_review_v1",
        "review_date": "2026-08-02",
        "review_role": "primary_author",
        "status": "COMPLETE",
        "scope": {
            "reviewed_rows": 2,
            "reclassified_rows": 1,
            "retained_rows": 1,
            "distinct_requirements": 2,
        },
        "decision_rule": "Apply the frozen category precedence rule.",
        "requirement_decisions": [
            {
                "flow_id": "flow-a",
                "requirement_id": "REQ-01",
                "audit_item_ids": ["RQ3-0001"],
                "initial_category": "LABEL_BOUNDARY_DISAGREEMENT",
                "reviewed_category": "EXCESSIVE_ABSTENTION",
                "reviewed_rationale": "The accepted partial support is supplied.",
            },
            {
                "flow_id": "flow-b",
                "requirement_id": "REQ-02",
                "audit_item_ids": ["RQ3-0002"],
                "initial_category": "LABEL_BOUNDARY_DISAGREEMENT",
                "reviewed_category": "LABEL_BOUNDARY_DISAGREEMENT",
                "reviewed_rationale": "The importance of visible support is contestable.",
            },
        ],
    }


def test_author_review_is_complete_and_does_not_mutate_source_audit() -> None:
    audit = _audit()
    original = deepcopy(audit)

    reviewed, metadata = apply_author_boundary_review(audit, _boundary_review())

    assert audit == original
    assert metadata["reviewed_rows"] == 2
    assert metadata["reclassified_rows"] == 1
    assert metadata["retained_rows"] == 1
    assert reviewed["items"][0]["llm_visual_review"]["primary_category"] == (
        "EXCESSIVE_ABSTENTION"
    )
    assert reviewed["items"][0]["gold_label"] == original["items"][0]["gold_label"]
    assert reviewed["items"][0]["predicted_label"] == original["items"][0][
        "predicted_label"
    ]
    assert reviewed["items"][0]["llm_visual_review"]["visible_evidence_rationale"] == (
        "Original visual rationale A."
    )
    assert reviewed["items"][0]["llm_visual_review"]["author_boundary_review"][
        "reviewed_rationale"
    ] == "The accepted partial support is supplied."


def test_author_review_must_cover_every_original_boundary_row() -> None:
    boundary_review = _boundary_review()
    boundary_review["requirement_decisions"] = boundary_review[
        "requirement_decisions"
    ][:1]
    boundary_review["scope"] = {
        "reviewed_rows": 1,
        "reclassified_rows": 1,
        "retained_rows": 0,
        "distinct_requirements": 1,
    }

    with pytest.raises(ValueError, match="does not cover exactly"):
        apply_author_boundary_review(_audit(), boundary_review)
