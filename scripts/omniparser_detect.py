from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OmniParser's screenshot-only UI detector.")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", type=Path, action="append", required=True)
    parser.add_argument("--confidence", type=float, default=0.05)
    parser.add_argument("--image-size", type=int, default=1024)
    parser.add_argument("--max-detections", type=int, default=160)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    from util.yolov9 import YOLOv9Detector

    detector = YOLOv9Detector(args.model, device="cpu")
    output: dict[str, object] = {"model": str(args.model), "images": {}}
    for image_path in args.image:
        with Image.open(image_path) as image:
            width, height = image.size
            result = detector.predict(
                image.convert("RGB"),
                conf=args.confidence,
                imgsz=args.image_size,
                iou=0.1,
                max_det=args.max_detections,
            )[0]
        boxes = result.boxes.xyxy.detach().cpu().tolist()
        scores = result.boxes.conf.detach().cpu().tolist()
        output["images"][str(image_path.resolve())] = {
            "width": width,
            "height": height,
            "regions": [
                {"bbox": box, "confidence": score}
                for box, score in zip(boxes, scores)
            ],
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
