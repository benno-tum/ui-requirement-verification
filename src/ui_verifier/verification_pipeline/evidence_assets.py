from __future__ import annotations

from dataclasses import dataclass
import hashlib
import mimetypes
from pathlib import Path
from typing import Any

from PIL import Image

from ui_verifier.verification_pipeline.gemini_image_claim_verifier import _load_image_derived_ocr
from ui_verifier.verification_pipeline.schemas import ScreenshotStep


@dataclass(frozen=True)
class ScreenshotAsset:
    step_index: int
    screenshot_path: str
    sha256: str
    byte_size: int
    mime_type: str
    image_width: int | None = None
    image_height: int | None = None
    ocr_text: str | None = None

    def to_prompt_hint(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "sha256": self.sha256,
            "byte_size": self.byte_size,
            "mime_type": self.mime_type,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "ocr_text": self.ocr_text or "",
        }

    def to_metadata(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "screenshot_path": self.screenshot_path,
            "sha256": self.sha256,
            "byte_size": self.byte_size,
            "mime_type": self.mime_type,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "has_ocr_text": bool(self.ocr_text),
        }


def build_screenshot_assets(screenshot_steps: list[ScreenshotStep]) -> dict[int, ScreenshotAsset]:
    assets: dict[int, ScreenshotAsset] = {}
    for step in screenshot_steps:
        path = Path(step.screenshot_path)
        raw = path.read_bytes()
        width: int | None = None
        height: int | None = None
        try:
            with Image.open(path) as image:
                width, height = image.size
        except Exception:
            width = None
            height = None
        mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
        assets[step.step_index] = ScreenshotAsset(
            step_index=step.step_index,
            screenshot_path=str(path),
            sha256=hashlib.sha256(raw).hexdigest(),
            byte_size=len(raw),
            mime_type=mime_type,
            image_width=width,
            image_height=height,
            ocr_text=_load_image_derived_ocr(path),
        )
    return assets
