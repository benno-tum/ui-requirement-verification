from __future__ import annotations

from pathlib import Path
from typing import List
import re


def parse_step_number(path: Path) -> int:
    m = re.search(r"step_(\d+)\.png$", path.name)
    if not m:
        raise ValueError(f"Cannot parse step number from {path.name}")
    return int(m.group(1))


def find_flow_dirs(input_dir: Path) -> List[Path]:
    return sorted([p for p in input_dir.iterdir() if p.is_dir()])


def find_step_images(flow_dir: Path) -> List[Path]:
    return sorted(flow_dir.glob("step_*.png"))


def choose_evenly_spaced(items: List[Path], k: int) -> List[Path]:
    if k >= len(items):
        return items
    if k <= 1:
        return [items[0]]

    idxs = []
    for i in range(k):
        pos = round(i * (len(items) - 1) / (k - 1))
        idxs.append(pos)

    idxs = sorted(set(idxs))
    return [items[i] for i in idxs]


def select_images(
    step_paths: List[Path],
    steps_arg: str | None,
    max_images: int | None,
) -> List[Path]:
    if steps_arg:
        wanted = []
        for part in steps_arg.split(","):
            part = part.strip()
            if not part:
                continue
            wanted.append(int(part))

        selected = []
        by_num = {parse_step_number(p): p for p in step_paths}
        for s in wanted:
            if s in by_num:
                selected.append(by_num[s])
        return selected

    if max_images is not None:
        return choose_evenly_spaced(step_paths, max_images)

    return step_paths


def select_requirement_harvest_images(
    step_paths: List[Path],
    steps_arg: str | None,
    max_images: int | None,
) -> List[Path]:
    if steps_arg:
        return select_images(step_paths, steps_arg=steps_arg, max_images=max_images)

    if not step_paths:
        return []

    if max_images is None or max_images >= len(step_paths):
        return step_paths

    if max_images <= 1:
        return [step_paths[0]]

    selected: list[Path] = [step_paths[0], step_paths[-1]]
    remaining = [p for p in step_paths[1:-1] if p not in selected]

    slots_left = max_images - len(selected)
    if slots_left > 0 and remaining:
        selected.extend(choose_evenly_spaced(remaining, slots_left))

    selected = sorted(set(selected), key=parse_step_number)
    return selected[:max_images]
