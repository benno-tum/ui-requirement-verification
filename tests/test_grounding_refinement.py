from ui_verifier.localization.grounding_refinement import refine_text_region
from ui_verifier.localization.text_box_localizer import OcrTextBox


def test_header_description_prefers_header_phrase_and_preserves_ui_context() -> None:
    boxes = [
        OcrTextBox("Great", {"x1": 264, "y1": 32, "x2": 310, "y2": 46}, 0.97, "word"),
        OcrTextBox("Escape", {"x1": 318, "y1": 32, "x2": 376, "y2": 51}, 0.97, "word"),
        OcrTextBox("Six", {"x1": 1103, "y1": 1879, "x2": 1127, "y2": 1893}, 0.96, "word"),
        OcrTextBox("Flags", {"x1": 1133, "y1": 1878, "x2": 1174, "y2": 1898}, 0.96, "word"),
        OcrTextBox("Great", {"x1": 1181, "y1": 1879, "x2": 1225, "y2": 1893}, 0.97, "word"),
    ]

    result = refine_text_region(
        "The park name 'Six Flags Great Escape' displayed in the header.",
        [220.66, 470.1, 493.24, 611.13],
        boxes,
        image_width=1298,
        image_height=4701,
    )

    assert result is not None
    assert result["matched_text"] == "Great Escape"
    assert result["bbox"] == [199.4, 20.6, 440.6, 62.4]


def test_refinement_requires_multiple_matching_words() -> None:
    result = refine_text_region(
        "The purchase button is visible.",
        [100, 100, 200, 150],
        [OcrTextBox("purchase", {"x1": 110, "y1": 105, "x2": 170, "y2": 125}, 0.9, "word")],
        image_width=500,
        image_height=500,
    )

    assert result is None
