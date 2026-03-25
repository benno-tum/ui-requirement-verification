from datasets import load_dataset
from pathlib import Path
from collections import OrderedDict
from PIL import Image
import io
import json
import re
import argparse


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUT = BASE_DIR / "data" / "mind2web_export"


def safe_name(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", str(s))[:120]


def json_safe(value):
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def downscale_image(img: Image.Image, max_side: int) -> Image.Image:
    img = img.convert("RGB")
    w, h = img.size
    longest = max(w, h)

    if longest <= max_side:
        return img

    scale = max_side / float(longest)
    new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
    return img.resize(new_size, Image.LANCZOS)


def load_pil_image(obj) -> Image.Image:
    if hasattr(obj, "save"):
        return obj
    if isinstance(obj, dict) and obj.get("bytes") is not None:
        return Image.open(io.BytesIO(obj["bytes"]))
    if isinstance(obj, str):
        return Image.open(obj)
    raise TypeError(f"Unknown image type: {type(obj)}")


def save_img(obj, path: Path, max_side: int):
    img = load_pil_image(obj)
    img = downscale_image(img, max_side=max_side)
    img.save(path, format="PNG", optimize=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="test_task")
    parser.add_argument("--max-flows", type=int, default=10)
    parser.add_argument("--max-side", type=int, default=1280)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading split={args.split} ...")
    ds = load_dataset("osunlp/Multimodal-Mind2Web", split=args.split)

    flows = OrderedDict()
    for row in ds:
        ann = row["annotation_id"]
        if ann not in flows:
            if len(flows) >= args.max_flows:
                break
            flows[ann] = []
        flows[ann].append(row)

    for i, (ann, rows) in enumerate(flows.items(), start=1):
        first = rows[0]
        folder = out_dir / f"{i:02d}_{safe_name(first.get('website'))}_{safe_name(ann)}"
        folder.mkdir(parents=True, exist_ok=True)

        task_meta = {
            "annotation_id": ann,
            "confirmed_task": first.get("confirmed_task"),
            "website": first.get("website"),
            "domain": first.get("domain"),
            "num_steps": len(rows),
            "split": args.split,
            "max_side": args.max_side,
        }
        (folder / "task.json").write_text(
            json.dumps(task_meta, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        step_metas = []
        for j, row in enumerate(rows, start=1):
            img_path = folder / f"step_{j:02d}.png"
            save_img(row["screenshot"], img_path, max_side=args.max_side)

            meta = {}
            for k, v in row.items():
                if k == "screenshot":
                    continue
                meta[k] = json_safe(v)

            meta["step_index"] = j
            meta["image_file"] = img_path.name
            step_metas.append(meta)

        (folder / "steps.json").write_text(
            json.dumps(step_metas, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        print(f"[OK] {folder.name} with {len(rows)} steps")

    print(f"\nDone. Export folder: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
