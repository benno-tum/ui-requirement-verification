from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import resource
import time
from typing import Any

from PIL import Image, ImageOps


BASE_DIR = Path(__file__).resolve().parents[1]
FLOW_ID = "02_gamestop_a2500e0b-9244-4f0e-b686-fa290c32b829"
PROCESSOR_REVISION = "5ca5edf5bd017b9919c05d08aebef5e4c7ac3bac"
MODEL_CODE_REVISION = "f6c1a25888ffc1d945ee8a1a77ac833c7303d46e"
DEFAULT_CANDIDATES = BASE_DIR / "data/generated/omniparser_candidate_marks/flow02_20260720/candidates.json"
DEFAULT_SOURCE_RUN = (
    BASE_DIR
    / "data/generated/verification_pipeline_runs/bbox_gemini31pro_singlecall_allimages_01_13_20260719"
    / f"{FLOW_ID}.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Caption OmniParser candidate crops locally with Florence-2.")
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--source-run", type=Path, default=DEFAULT_SOURCE_RUN)
    parser.add_argument("--model", type=Path, default=Path("/private/tmp/OmniParser/weights/icon_caption"))
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--context-ratio", type=float, default=0.12)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_images(run: dict[str, Any]) -> dict[int, Path]:
    images: dict[int, Path] = {}
    for result in run.get("results", []):
        for claim in result.get("claims", []):
            for evidence in claim.get("evidence", []):
                step = int(evidence.get("step_index") or 0)
                path = Path(str(evidence.get("screenshot_path") or ""))
                if step > 0 and path.is_file():
                    images.setdefault(step, path.resolve())
    if not images:
        raise ValueError("Source run contains no usable screenshot paths.")
    return images


def crop_with_context(image: Image.Image, bbox: list[float], ratio: float) -> Image.Image:
    x1, y1, x2, y2 = (float(value) for value in bbox)
    pad_x = max(4.0, (x2 - x1) * ratio)
    pad_y = max(4.0, (y2 - y1) * ratio)
    crop = image.crop((max(0, int(x1 - pad_x)), max(0, int(y1 - pad_y)), min(image.width, int(x2 + pad_x)), min(image.height, int(y2 + pad_y))))
    # OmniParser's own caption path uses 64x64 icon crops. Keeping aspect ratio
    # here retains more information for broader web regions.
    crop.thumbnail((128, 128))
    return ImageOps.pad(crop.convert("RGB"), (128, 128), color="white")


def main() -> None:
    args = parse_args()
    if args.batch_size < 1 or args.batch_size > 16:
        raise ValueError("batch-size must be between 1 and 16 for memory-safe local execution")

    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor

    payload = load_json(args.candidates)
    images = source_images(load_json(args.source_run))
    started = time.monotonic()
    processor = AutoProcessor.from_pretrained(
        "microsoft/Florence-2-base",
        revision=PROCESSOR_REVISION,
        trust_remote_code=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch.float32,
        trust_remote_code=True,
        code_revision=MODEL_CODE_REVISION,
    )
    model.eval().to("cpu")

    captioned_this_run = 0
    for step_value, candidates in sorted((payload.get("steps") or {}).items(), key=lambda item: int(item[0])):
        step = int(step_value)
        image_path = images.get(step)
        if image_path is None:
            continue
        with Image.open(image_path) as source:
            image = source.convert("RGB")
        ui_candidates = [
            candidate
            for candidate in candidates
            if candidate.get("source") == "omniparser_ui" and not candidate.get("caption")
        ]
        for offset in range(0, len(ui_candidates), args.batch_size):
            batch_candidates = ui_candidates[offset : offset + args.batch_size]
            crops = [crop_with_context(image, candidate["bbox"], args.context_ratio) for candidate in batch_candidates]
            inputs = processor(
                images=crops,
                text=["<CAPTION>"] * len(crops),
                return_tensors="pt",
                do_resize=False,
            )
            with torch.inference_mode():
                generated = model.generate(
                    input_ids=inputs["input_ids"],
                    pixel_values=inputs["pixel_values"],
                    max_new_tokens=24,
                    num_beams=1,
                    do_sample=False,
                )
            captions = processor.batch_decode(generated, skip_special_tokens=True)
            for candidate, caption in zip(batch_candidates, captions, strict=True):
                candidate["caption"] = caption.strip()
                candidate["caption_model"] = "microsoft/OmniParser-v2.0/icon_caption"
                candidate["caption_context_ratio"] = args.context_ratio
                captioned_this_run += 1
            args.candidates.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    elapsed = time.monotonic() - started
    peak_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    captioned_total = sum(
        bool(candidate.get("caption"))
        for candidates in (payload.get("steps") or {}).values()
        for candidate in candidates
        if candidate.get("source") == "omniparser_ui"
    )
    payload["local_captioning"] = {
        "model": "microsoft/OmniParser-v2.0/icon_caption",
        "model_sha256": sha256_file(args.model / "model.safetensors"),
        "processor_revision": PROCESSOR_REVISION,
        "model_code_revision": MODEL_CODE_REVISION,
        "device": "cpu",
        "batch_size": args.batch_size,
        "context_ratio": args.context_ratio,
        "captioned_candidates": captioned_total,
        "captioned_this_run": captioned_this_run,
        "elapsed_seconds": round(elapsed, 3),
        "peak_rss_mib": round(peak_kib / 1024 / 1024, 1),
        "clean_image_crops": True,
    }
    args.candidates.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload["local_captioning"], indent=2))


if __name__ == "__main__":
    main()
