from pathlib import Path

from ui_verifier.api import app as api_app


def test_omniparser_endpoint_returns_claim_specific_ranked_candidates(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        api_app,
        "_bbox_audit_item",
        lambda audit_id, item_id: {
            "flow_id": "02_gamestop_test",
            "step_index": 2,
            "image_width": 100,
            "image_height": 100,
            "claim_text": "The store locator provides city search.",
            "requirement_text": "Users shall find a store by city.",
        },
    )
    candidates = [
        {"candidate_id": "U01", "source": "omniparser_ui", "bbox": [0, 0, 90, 30], "caption": "city store search field"},
        {"candidate_id": "U02", "source": "omniparser_ui", "bbox": [0, 40, 30, 70], "caption": "shopping cart"},
    ]
    monkeypatch.setattr(api_app, "_omniparser_candidates", lambda flow_id, step_index: (tmp_path / "candidates.json", candidates))

    response = api_app.get_omniparser_bbox_candidates("audit", "item")

    assert response["ranking_method"] == "local_florence_caption_plus_ocr_tfidf_v1"
    assert response["candidates"][0]["candidate_id"] == "U01"
    assert response["candidates"][0]["rank"] == 1
    assert response["candidates"][0]["bbox"] == {"x1": 0.0, "y1": 0.0, "x2": 90.0, "y2": 30.0}
