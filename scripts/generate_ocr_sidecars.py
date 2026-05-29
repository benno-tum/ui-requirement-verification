from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys


BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ui_verifier.common.flow_utils import find_step_images, parse_step_number


@dataclass
class OcrRunSummary:
    requested: int = 0
    generated: int = 0
    reused: int = 0
    failed: int = 0
    skipped_no_tesseract: int = 0
    tesseract_path: str | None = None
    sidecars: list[str] = field(default_factory=list)
    failures: list[dict[str, str]] = field(default_factory=list)
    status: str = "not_started"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def normalize_ocr_text(text: str) -> str:
    return " ".join(text.split()).strip()


def sidecar_candidates(image_path: Path) -> list[Path]:
    return [
        image_path.with_suffix(".ocr.txt"),
        image_path.with_suffix(".ocr.json"),
        image_path.with_name(f"{image_path.stem}_ocr.txt"),
        image_path.with_name(f"{image_path.stem}_ocr.json"),
        image_path.parent / "ocr" / f"{image_path.stem}.txt",
        image_path.parent / "ocr" / f"{image_path.stem}.json",
    ]


def existing_sidecar(image_path: Path) -> Path | None:
    for candidate in sidecar_candidates(image_path):
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def default_sidecar_path(image_path: Path) -> Path:
    return image_path.parent / "ocr" / f"{image_path.stem}.json"


def run_tesseract(
    image_path: Path,
    *,
    tesseract_path: str,
    language: str = "eng",
    psm: int = 6,
    timeout_seconds: int = 60,
) -> str:
    result = subprocess.run(
        [
            tesseract_path,
            str(image_path),
            "stdout",
            "-l",
            language,
            "--psm",
            str(psm),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout_seconds,
    )
    if result.returncode != 0:
        stderr = normalize_ocr_text(result.stderr)
        raise RuntimeError(stderr or f"tesseract exited with status {result.returncode}")
    return normalize_ocr_text(result.stdout)


def write_ocr_sidecar(
    image_path: Path,
    *,
    text: str,
    sidecar_path: Path | None = None,
    engine_path: str | None = None,
    language: str = "eng",
    psm: int = 6,
) -> Path:
    target = sidecar_path or default_sidecar_path(image_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "text": text,
        "ocr_text": text,
        "engine": "tesseract",
        "engine_path": engine_path,
        "language": language,
        "psm": psm,
        "image_path": str(image_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def generate_ocr_sidecars(
    image_paths: list[Path],
    *,
    force: bool = False,
    tesseract_cmd: str = "tesseract",
    language: str = "eng",
    psm: int = 6,
    timeout_seconds: int = 60,
) -> OcrRunSummary:
    ordered_paths = sorted(image_paths, key=parse_step_number)
    summary = OcrRunSummary(requested=len(ordered_paths))

    for image_path in ordered_paths:
        if not force:
            current = existing_sidecar(image_path)
            if current is not None:
                summary.reused += 1
                summary.sidecars.append(str(current))

    missing_paths = [
        image_path
        for image_path in ordered_paths
        if force or existing_sidecar(image_path) is None
    ]
    if not missing_paths:
        summary.status = "reused"
        return summary

    tesseract_path = shutil.which(tesseract_cmd)
    summary.tesseract_path = tesseract_path
    if tesseract_path is None:
        summary.skipped_no_tesseract = len(missing_paths)
        summary.status = "tesseract_unavailable"
        return summary

    for image_path in missing_paths:
        try:
            text = run_tesseract(
                image_path,
                tesseract_path=tesseract_path,
                language=language,
                psm=psm,
                timeout_seconds=timeout_seconds,
            )
            sidecar = write_ocr_sidecar(
                image_path,
                text=text,
                engine_path=tesseract_path,
                language=language,
                psm=psm,
            )
            summary.generated += 1
            summary.sidecars.append(str(sidecar))
        except Exception as exc:
            summary.failed += 1
            summary.failures.append({"image_path": str(image_path), "error": str(exc)})

    if summary.failed and not summary.generated:
        summary.status = "failed"
    elif summary.failed:
        summary.status = "partial"
    elif summary.generated:
        summary.status = "generated"
    else:
        summary.status = "reused"
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Tesseract OCR sidecars for step_*.png screenshots.")
    parser.add_argument("--flow-dir", type=Path, required=True, help="Directory containing step_*.png screenshots")
    parser.add_argument("--force", action="store_true", help="Regenerate OCR even when sidecars already exist")
    parser.add_argument("--tesseract-cmd", default="tesseract", help="Tesseract executable name or path")
    parser.add_argument("--language", default="eng", help="Tesseract language code")
    parser.add_argument("--psm", type=int, default=6, help="Tesseract page segmentation mode")
    parser.add_argument("--timeout-seconds", type=int, default=60)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    image_paths = sorted(find_step_images(args.flow_dir), key=parse_step_number)
    if not image_paths:
        raise SystemExit(f"No step_*.png screenshots found in {args.flow_dir}")

    summary = generate_ocr_sidecars(
        image_paths,
        force=args.force,
        tesseract_cmd=args.tesseract_cmd,
        language=args.language,
        psm=args.psm,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(summary.as_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
