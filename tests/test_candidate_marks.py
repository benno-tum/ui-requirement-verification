from ui_verifier.localization.candidate_marks import CandidateRegion, clamp_bbox, pad_bbox, resolve_candidate_ids


def test_clamp_and_pad_bbox() -> None:
    assert clamp_bbox((-3, 2, 105, 80), image_width=100, image_height=60) == (0.0, 2.0, 100.0, 60.0)
    assert pad_bbox((10, 10, 20, 20), image_width=100, image_height=100, horizontal=4, vertical=2) == (
        6.0,
        8.0,
        24.0,
        22.0,
    )
    assert clamp_bbox((10, 10, 10, 20), image_width=100, image_height=100) is None


def test_resolve_candidate_ids_is_bounded_deduplicated_and_case_insensitive() -> None:
    candidates = [
        CandidateRegion("U01", "omniparser_ui", (0, 0, 10, 10)),
        CandidateRegion("T01", "tesseract_line", (10, 0, 20, 10), text="Search"),
        CandidateRegion("U02", "omniparser_ui", (20, 0, 30, 10)),
    ]
    resolved = resolve_candidate_ids(["u01", "bad", "U01", "t01", "u02"], candidates, maximum=2)
    assert [candidate.candidate_id for candidate in resolved] == ["U01", "T01"]
