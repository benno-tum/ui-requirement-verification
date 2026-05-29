from scripts.prepare_claim_review_bundles import item_needs_claim_review


def test_item_needs_claim_review_selects_placeholder_claims() -> None:
    include, flags = item_needs_claim_review(
        {
            "review_status": "needs_review",
            "claims": [
                {
                    "claim": "The system shows a confirmation.",
                    "status": "MISSING",
                    "claim_type": "OBSERVABLE",
                    "importance": "CORE",
                    "evidence_steps": [],
                }
            ],
        }
    )

    assert include is True
    assert "placeholder_status" in flags
    assert "missing_note" in flags


def test_item_needs_claim_review_skips_completed_claims() -> None:
    include, flags = item_needs_claim_review(
        {
            "review_status": "needs_review",
            "claims": [
                {
                    "claim": "The system shows a confirmation.",
                    "status": "SUPPORTED",
                    "claim_type": "OBSERVABLE",
                    "importance": "CORE",
                    "evidence_steps": [1],
                    "note": "Step 1 shows the confirmation.",
                }
            ],
        }
    )

    assert include is False
    assert flags == []


def test_item_needs_claim_review_ignores_non_review_items() -> None:
    include, flags = item_needs_claim_review(
        {
            "review_status": "accepted",
            "claims": [],
        }
    )

    assert include is False
    assert flags == []
