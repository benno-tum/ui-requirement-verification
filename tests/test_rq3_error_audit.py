from __future__ import annotations

from scripts.analyze_rq3_error_audit import review_complete, summarize
from scripts.prepare_rq3_error_audit import (
    CONDITIONS,
    suggest_requirement_tags,
    suggested_primary_candidates,
)


def test_six_prespecified_conditions_are_condition_blinded() -> None:
    assert len(CONDITIONS) == 6
    assert [item["condition_code"] for item in CONDITIONS] == [
        "C01",
        "C02",
        "C03",
        "C04",
        "C05",
        "C06",
    ]


def test_unsafe_fulfillment_is_a_deterministic_candidate() -> None:
    candidates = suggested_primary_candidates(
        gold_label="ABSTAIN",
        predicted_label="FULFILLED",
        gold_evidence=[],
        supplied_steps=[1, 2],
        screenshot_policy="all",
    )
    assert candidates == ["UNSAFE_OVER_FULFILLMENT"]


def test_requirement_tag_suggestions_are_multivalued() -> None:
    tags = suggest_requirement_tags(
        "CONTR-01",
        "All selected filters shall persist across subsequent pages.",
        [2, 4],
    )
    assert "UNIVERSAL_OR_COMPLETENESS" in tags
    assert "PERSISTENCE_OR_CROSS_STEP" in tags
    assert "MULTI_SCREEN_COMPOSITION" in tags
    assert "NEGATION_OR_CONTRASTIVE" in tags


def test_incomplete_audit_withholds_category_counts() -> None:
    data = {
        "items": [
            {
                "audit_item_id": "RQ3-0001",
                "author_review": {
                    "review_status": "PENDING",
                    "primary_category": None,
                },
            }
        ]
    }
    result = summarize(data)
    assert result["complete"] is False
    assert "primary_categories_among_all_coded_rows" not in result


def test_complete_review_requires_visible_evidence_rationale() -> None:
    item = {
        "author_review": {
            "review_status": "COMPLETE",
            "decisive_evidence_supplied": True,
            "primary_category": "EXCESSIVE_ABSTENTION",
            "requirement_tags": ["ORDINARY_LOCAL_UI"],
            "evidence_tags": ["DECISIVE_STEP_SELECTED"],
            "visible_evidence_rationale": "Step 4 visibly contains the result.",
            "gold_review_candidate": False,
        }
    }
    assert review_complete(item)
