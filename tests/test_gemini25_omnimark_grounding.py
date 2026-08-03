from scripts.run_gemini25_omnimark_grounding import (
    approximate_image_tokens,
    normalize_response,
    resolve_supplemental_box,
    selection_covers_required_facts,
    validate_normalized_box,
)


def test_validate_normalized_box() -> None:
    assert validate_normalized_box([10, 20, 300, 900]) == [10.0, 20.0, 300.0, 900.0]
    assert validate_normalized_box([10, 20, 10, 900]) is None
    assert validate_normalized_box([-1, 20, 300, 900]) is None


def test_resolve_supplemental_box_accepts_normalized_and_unambiguous_pixels() -> None:
    assert resolve_supplemental_box(
        [100, 50, 400, 900], image_width=1280, image_height=2000
    ) == ([64.0, 200.0, 1152.0, 800.0], "normalized_0_1000")
    assert resolve_supplemental_box(
        [230, 30, 1800, 970], image_width=1280, image_height=2000
    ) == ([30.0, 230.0, 970.0, 1800.0], "image_pixels_yxyx")
    assert resolve_supplemental_box(
        [230, 30, 2100, 970], image_width=1280, image_height=2000
    ) is None


def test_small_image_token_estimate(tmp_path) -> None:
    from PIL import Image

    path = tmp_path / "small.png"
    Image.new("RGB", (384, 384), "white").save(path)
    assert approximate_image_tokens(path) == 258


def test_normalize_response_accepts_supported_gemini_shapes() -> None:
    item = {"task_id": "R::C::S1"}
    assert normalize_response({"selections": [item]}) == {"selections": [item]}
    assert normalize_response(item) == {"selections": [item]}
    assert normalize_response([item]) == {"selections": [item]}


def test_selection_requires_coverage_for_every_named_fact() -> None:
    complete = {
        "required_visible_facts": ["left side", "right side"],
        "region_fact_coverage": {"T01": [1], "T02": [2]},
        "applicability": "MULTI_REGION",
    }
    incomplete = {
        **complete,
        "region_fact_coverage": {"T01": [2], "T02": [2]},
    }
    assert selection_covers_required_facts(complete)
    assert not selection_covers_required_facts(incomplete)
    assert selection_covers_required_facts({"applicability": "NO_VISIBLE_REGION"})
