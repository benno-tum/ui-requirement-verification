from __future__ import annotations

from scripts.publish_sanitized_verification_runs import sanitize_run


def test_sanitize_run_removes_screen_text_and_localizes_paths() -> None:
    payload = {
        "flow_id": "01_demo",
        "metadata": {"flow_dir": "/repo/data/processed/flow"},
        "results": [{"visible_observation": "Account buckeye.foobar@gmail.com is shown.", "ocr_word_boxes": [1]}],
        "screen_representations": [
            {
                "step_index": 1,
                "screenshot_path": "/repo/data/processed/flow/step_01.png",
                "ocr_text": "private visible text",
                "visible_text": ["private"],
                "screen_summary": "private summary",
            }
        ],
    }

    cleaned = sanitize_run(payload)

    screen = cleaned["screen_representations"][0]
    assert "ocr_text" not in screen
    assert "visible_text" not in screen
    assert "screen_summary" not in screen
    assert screen["screenshot_path"] == "step_01.png"
    assert cleaned["results"][0]["visible_observation"] == "Account [redacted-email] is shown."
    assert "ocr_word_boxes" not in cleaned["results"][0]
