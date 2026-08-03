from __future__ import annotations

from scripts.draft_rq3_author_review import classify_primary, suspicious_gold


def item(gold: str, predicted: str, *, missing: list[int] | None = None) -> dict:
    return {
        "gold_label": gold,
        "predicted_label": predicted,
        "gold_evidence_steps": [4],
        "supplied_step_indices": [] if missing else [4],
        "missing_gold_evidence_steps": missing or [],
        "eligibility_reasons": ["LABEL_MISMATCH"] if gold != predicted else [],
        "gold_rationale": "Visible evidence supports the reference label.",
    }


def test_correct_abstention_is_not_misreported_as_failure() -> None:
    value = item("ABSTAIN", "ABSTAIN")
    value["eligibility_reasons"] = ["MODEL_ABSTAIN"]
    assert classify_primary(value)[0] == "APPROPRIATE_ABSTENTION"


def test_missing_topk_evidence_is_selection_miss() -> None:
    assert classify_primary(item("FULFILLED", "ABSTAIN", missing=[4]))[0] == "EVIDENCE_SELECTION_MISS"


def test_unsafe_fulfilled_has_priority_over_interpretation() -> None:
    assert classify_primary(item("PARTIALLY_FULFILLED", "FULFILLED"))[0] == "UNSAFE_OVER_FULFILLMENT"


def test_suspicious_fulfilled_rationale_becomes_gold_candidate() -> None:
    value = item("FULFILLED", "ABSTAIN")
    value["gold_rationale"] = "The downstream workflow is missing from the flow."
    assert suspicious_gold(value)[0] is True
