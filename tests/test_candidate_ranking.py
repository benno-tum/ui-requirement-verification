from ui_verifier.localization.candidate_ranking import rank_candidates


def test_rank_candidates_uses_caption_ocr_and_claim() -> None:
    candidates = [
        {"candidate_id": "U01", "source": "omniparser_ui", "bbox": [0, 0, 100, 50], "caption": "search location form"},
        {"candidate_id": "U02", "source": "omniparser_ui", "bbox": [0, 50, 100, 100], "caption": "shopping cart button"},
        {"candidate_id": "T01", "source": "tesseract_line", "bbox": [10, 10, 90, 30], "text": "Search by city state or ZIP code"},
    ]
    ranked = rank_candidates(
        candidates,
        claim_text="The store finder accepts a city, state, or ZIP location.",
        requirement_text="A location search shall be available.",
        image_width=200,
        image_height=200,
    )
    assert ranked[0]["candidate_id"] in {"U01", "T01"}
    assert ranked[0]["rank"] == 1
    assert ranked[-1]["candidate_id"] == "U02"


def test_rank_candidates_penalizes_uninformative_whole_screen_region() -> None:
    candidates = [
        {"candidate_id": "U01", "source": "omniparser_ui", "bbox": [0, 0, 1000, 1000], "caption": "search page"},
        {"candidate_id": "T01", "source": "tesseract_line", "bbox": [10, 10, 160, 40], "text": "Search stores"},
    ]
    ranked = rank_candidates(
        candidates,
        claim_text="Search stores",
        image_width=1000,
        image_height=1000,
    )
    assert ranked[0]["candidate_id"] == "T01"


def test_rank_candidates_expands_store_locator_wording() -> None:
    ranked = rank_candidates(
        [
            {"candidate_id": "T01", "source": "tesseract_line", "bbox": [0, 0, 80, 20], "text": "Find a Store"},
            {"candidate_id": "U01", "source": "omniparser_ui", "bbox": [0, 30, 80, 60], "caption": "promotional banner"},
        ],
        claim_text="The homepage provides access to the store locator.",
        image_width=100,
        image_height=100,
    )
    assert ranked[0]["candidate_id"] == "T01"
