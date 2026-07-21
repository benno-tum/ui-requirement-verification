#!/usr/bin/env python3
"""Rank pipeline bounding boxes by how little visible content their crops contain."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("audit_dir", type=Path)
    parser.add_argument("--start-flow", type=int, default=2)
    parser.add_argument("--end-flow", type=int, default=13)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    manifest = json.loads((args.audit_dir / "bbox_manifest.json").read_text())["items"]
    references = json.loads((args.audit_dir / "bbox_reference.json").read_text())["items"]
    judgment_path = args.audit_dir / "bbox_inspection_judgments.json"
    judgments = json.loads(judgment_path.read_text()).get("items", {}) if judgment_path.exists() else {}

    ranked = []
    for item in manifest:
        flow_number = int(item["flow_id"].split("_", 1)[0])
        if not args.start_flow <= flow_number <= args.end_flow or item["audit_item_id"] in judgments:
            continue
        prediction = references[item["audit_item_id"]]["prediction"]
        box = prediction["bbox"]
        with Image.open(item["image_path"]) as image:
            x1 = max(0, int(box["x1"])); y1 = max(0, int(box["y1"]))
            x2 = min(image.width, max(x1 + 1, int(np.ceil(box["x2"]))))
            y2 = min(image.height, max(y1 + 1, int(np.ceil(box["y2"]))))
            crop = np.asarray(image.convert("RGB").crop((x1, y1, x2, y2)), dtype=np.float32)
        gray = crop.mean(axis=2)
        std = float(gray.std())
        dx = np.abs(np.diff(gray, axis=1)) if gray.shape[1] > 1 else np.zeros((1, 1))
        dy = np.abs(np.diff(gray, axis=0)) if gray.shape[0] > 1 else np.zeros((1, 1))
        edge_density = float((dx > 12).mean() + (dy > 12).mean()) / 2
        ranked.append({
            "audit_item_id": item["audit_item_id"], "flow_id": item["flow_id"],
            "requirement_id": item["requirement_id"], "claim_id": item["claim_id"],
            "step_index": item["step_index"], "claim_text": item["claim_text"],
            "description": prediction.get("matched_text"), "source": prediction.get("source"),
            "bbox": box, "gray_std": round(std, 3), "edge_density": round(edge_density, 5),
        })
    ranked.sort(key=lambda row: (row["edge_density"], row["gray_std"]))
    print(json.dumps(ranked[: args.limit], indent=2))


if __name__ == "__main__":
    main()
