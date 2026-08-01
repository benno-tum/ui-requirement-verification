from scripts.build_local_candidate_bbox_run import semantic_description


def test_semantic_description_exposes_rank_candidate_and_caption() -> None:
    assert semantic_description({"rank": 1, "candidate_id": "U04", "caption": "Search button"}) == (
        "Local rank #1 U04: Search button"
    )


def test_semantic_description_falls_back_to_ocr_text() -> None:
    assert semantic_description({"rank": 1, "candidate_id": "T02", "text": "Find a Store"}) == (
        "Local rank #1 T02: Find a Store"
    )
