from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

from datasets import load_dataset
from PIL import Image, UnidentifiedImageError

from ui_verifier.common.flow_utils import find_step_images


DATASET_NAME = "osunlp/Multimodal-Mind2Web"
_ORIGINAL_DIR_NAME = "original"
_DATASET_BY_SPLIT: dict[str, Any] = {}
_ROWS_BY_FLOW: dict[tuple[str, str], list[dict[str, Any]]] = {}


def _load_pil_image(obj: Any) -> Image.Image:
    if obj is None:
        raise TypeError("Screenshot is None")
    if hasattr(obj, "save"):
        return obj
    if isinstance(obj, dict) and obj.get("bytes") is not None:
        return Image.open(io.BytesIO(obj["bytes"]))
    if isinstance(obj, str):
        return Image.open(obj)
    raise TypeError(f"Unknown screenshot type: {type(obj)}")


def _load_task_meta(flow_dir: Path) -> dict[str, Any]:
    task_path = flow_dir / "task.json"
    if not task_path.exists():
        return {}
    try:
        return json.loads(task_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _load_split(split: str):
    dataset = _DATASET_BY_SPLIT.get(split)
    if dataset is None:
        dataset = load_dataset(DATASET_NAME, split=split)
        _DATASET_BY_SPLIT[split] = dataset
    return dataset


def _rows_for_flow(annotation_id: str, split: str) -> list[dict[str, Any]]:
    cache_key = (split, annotation_id)
    cached = _ROWS_BY_FLOW.get(cache_key)
    if cached is not None:
        return cached

    dataset = _load_split(split)
    rows: list[dict[str, Any]] = []
    for row in dataset:
        if str(row.get("annotation_id") or "") == annotation_id:
            rows.append(row)
    _ROWS_BY_FLOW[cache_key] = rows
    return rows


def _save_original_png(screenshot: Any, path: Path) -> tuple[int, int]:
    image = _load_pil_image(screenshot).convert("RGB")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)
    return int(image.width), int(image.height)


def ensure_flow_original_images(flow_dir: Path) -> list[Path]:
    step_paths = find_step_images(flow_dir)
    if not step_paths:
        return []

    original_dir = flow_dir / _ORIGINAL_DIR_NAME
    target_paths = [original_dir / step_path.name for step_path in step_paths]
    if all(path.exists() for path in target_paths):
        return target_paths

    task_meta = _load_task_meta(flow_dir)
    annotation_id = str(task_meta.get("annotation_id") or "").strip()
    split = str(task_meta.get("split") or "test_task").strip()
    if not annotation_id:
        return [path for path in target_paths if path.exists()]

    rows = _rows_for_flow(annotation_id, split)
    if not rows:
        return [path for path in target_paths if path.exists()]

    manifest: list[dict[str, Any]] = []
    for step_path, row in zip(step_paths, rows, strict=False):
        target_path = original_dir / step_path.name
        if target_path.exists():
            with Image.open(target_path) as image:
                manifest.append(
                    {
                        "step_index": int(step_path.stem.split("_")[-1]),
                        "file": target_path.name,
                        "width": int(image.width),
                        "height": int(image.height),
                        "source": "cached",
                    }
                )
            continue

        screenshot = row.get("screenshot")
        if screenshot is None:
            continue
        try:
            width, height = _save_original_png(screenshot, target_path)
        except (TypeError, OSError, UnidentifiedImageError, ValueError):
            continue
        manifest.append(
            {
                "step_index": int(step_path.stem.split("_")[-1]),
                "file": target_path.name,
                "width": width,
                "height": height,
                "source": "downloaded",
            }
        )

    if manifest:
        (original_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return [path for path in target_paths if path.exists()]
