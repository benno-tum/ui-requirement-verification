from pathlib import Path

from ui_verifier.verification.label_validation import validate_verification_gold_item
from ui_verifier.verification.schemas import VerificationGoldFile


def test_mashboot_draft_gold_is_complete_and_valid() -> None:
    path = Path("data/annotations/verification_gold/pure_2010_mashboot/verification_gold.json")
    gold = VerificationGoldFile.load(path)

    assert len(gold.items) == 11
    assert len({item.requirement_id for item in gold.items}) == 11
    assert sum(len(item.claims) for item in gold.items) == 40
    assert all(item.review_status == "needs_review" for item in gold.items)
    assert all(not validate_verification_gold_item(item).errors for item in gold.items)
    assert all(set(item.evidence_steps).issubset({1, 2, 3}) for item in gold.items)
