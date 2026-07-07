from __future__ import annotations

from pathlib import Path

from PIL import Image
import pytest

from scripts.generate_ocr_sidecars import generate_ocr_sidecars, write_ocr_sidecar
from scripts.run_demo_verification import DemoDataError, resolve_screenshot_dir
from ui_verifier.localization import TextBoxLocalizer, load_ocr_text_boxes, parse_tesseract_tsv


def _write_step_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), color="white").save(path)


def test_resolve_screenshot_dir_prefers_processed_flow_dir(tmp_path: Path) -> None:
    flow_id = "03_demo_flow"
    processed = tmp_path / "data" / "processed" / "flows" / "mind2web" / flow_id
    generated = (
        tmp_path
        / "data"
        / "generated"
        / "candidate_requirements"
        / flow_id
        / "manual_harvest_bundle"
        / "images"
    )
    _write_step_image(processed / "step_01.png")
    _write_step_image(generated / "step_01.png")

    selection = resolve_screenshot_dir(flow_id, base_dir=tmp_path)

    assert selection.screenshot_dir == processed
    assert selection.metadata_dir == processed


def test_resolve_screenshot_dir_uses_manual_harvest_fallback(tmp_path: Path) -> None:
    flow_id = "03_demo_flow"
    generated = (
        tmp_path
        / "data"
        / "generated"
        / "candidate_requirements"
        / flow_id
        / "manual_harvest_bundle"
        / "images"
    )
    _write_step_image(generated / "step_02.png")

    selection = resolve_screenshot_dir(flow_id, base_dir=tmp_path)

    assert selection.screenshot_dir == generated


def test_resolve_screenshot_dir_error_lists_checked_paths(tmp_path: Path) -> None:
    with pytest.raises(DemoDataError) as exc_info:
        resolve_screenshot_dir("missing_flow", base_dir=tmp_path)

    message = str(exc_info.value)
    assert "No step_*.png screenshots found" in message
    assert "data/processed/flows/mind2web/missing_flow" in message
    assert "manual_harvest_bundle/images" in message


def test_generate_ocr_sidecars_reuses_existing_without_tesseract(tmp_path: Path) -> None:
    image_path = tmp_path / "step_01.png"
    _write_step_image(image_path)
    sidecar = write_ocr_sidecar(image_path, text="Existing text")

    summary = generate_ocr_sidecars([image_path], tesseract_cmd="definitely-not-installed-tesseract")

    assert summary.status == "reused"
    assert summary.reused == 1
    assert summary.generated == 0
    assert str(sidecar) in summary.sidecars


def test_generate_ocr_sidecars_skips_missing_when_tesseract_unavailable(tmp_path: Path) -> None:
    image_path = tmp_path / "step_01.png"
    _write_step_image(image_path)

    summary = generate_ocr_sidecars([image_path], tesseract_cmd="definitely-not-installed-tesseract")

    assert summary.status == "tesseract_unavailable"
    assert summary.skipped_no_tesseract == 1
    assert summary.generated == 0


def test_tesseract_tsv_boxes_are_normalized() -> None:
    boxes = parse_tesseract_tsv(
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t10\t20\t30\t12\t96\tCheckout\n"
        "5\t1\t1\t1\t1\t2\t45\t20\t25\t12\t90\tTotal\n"
    )

    line = next(box for box in boxes if box.level == "line")
    assert line.text == "Checkout Total"
    assert line.bbox == {"x1": 10.0, "y1": 20.0, "x2": 70.0, "y2": 32.0}
    assert line.confidence == pytest.approx(0.93)


def test_text_box_localizer_matches_claim_to_sidecar_box(tmp_path: Path) -> None:
    image_path = tmp_path / "step_01.png"
    _write_step_image(image_path)
    write_ocr_sidecar(
        image_path,
        text="Checkout Total",
        text_boxes=parse_tesseract_tsv(
            "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
            "5\t1\t1\t1\t1\t1\t10\t20\t30\t12\t96\tCheckout\n"
            "5\t1\t1\t1\t1\t2\t45\t20\t25\t12\t90\tTotal\n"
        ),
    )

    assert load_ocr_text_boxes(image_path)
    suggestions = TextBoxLocalizer().suggest("The checkout page shows the total.", image_path)

    assert suggestions
    assert suggestions[0]["bbox"] == {"x1": 10.0, "y1": 20.0, "x2": 70.0, "y2": 32.0}
    assert suggestions[0]["matched_text"] == "Checkout Total"
    assert suggestions[0]["image_width"] == 8
    assert suggestions[0]["image_height"] == 8
    assert suggestions[0]["coordinate_space"] == "image_pixels"
