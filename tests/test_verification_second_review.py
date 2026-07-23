from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_verification_second_review_sample import (
    BASE_DIR,
    build_review_form,
)
from scripts.evaluate_verification_second_review import (
    _cohen_kappa,
    evaluate,
)


def test_build_review_form_is_blinded_stratified_and_flow_complete() -> None:
    payload, distribution = build_review_form(
        gold_root=BASE_DIR / "data/annotations/verification_gold",
        flows_root=BASE_DIR / "data/processed/flows/mind2web",
        seed="thesis-second-review-v1",
    )

    assert len(payload["items"]) == 44
    assert len({item["flow_id"] for item in payload["items"]}) == 13
    assert distribution == {
        "FULFILLED": 12,
        "PARTIALLY_FULFILLED": 12,
        "ABSTAIN": 12,
        "NOT_FULFILLED": 8,
    }
    for item in payload["items"]:
        assert "gold_label" not in item
        assert "verification_label" not in item
        assert "prediction" not in item
        assert item["reviewer_label"] is None
        assert item["ordered_screenshots"]
        assert all(not Path(path).is_absolute() for path in item["ordered_screenshots"])


def test_incomplete_review_is_rejected(tmp_path: Path) -> None:
    review_form = tmp_path / "review.json"
    review_form.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "audit_item_id": "VSR-001",
                        "flow_id": "flow",
                        "requirement_id": "REQ-01",
                        "reviewer_label": None,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="review is incomplete"):
        evaluate(
            review_form=review_form,
            gold_root=BASE_DIR / "data/annotations/verification_gold",
        )


def test_kappa_is_one_for_identical_labels() -> None:
    labels = ["FULFILLED", "PARTIALLY_FULFILLED", "ABSTAIN", "NOT_FULFILLED"]
    assert _cohen_kappa(labels, labels) == 1.0
