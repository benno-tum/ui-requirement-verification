from __future__ import annotations

from pathlib import Path

from PIL import Image
import pytest

from scripts.generate_ocr_sidecars import generate_ocr_sidecars, write_ocr_sidecar
from scripts.run_demo_verification import DemoDataError, resolve_screenshot_dir


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
