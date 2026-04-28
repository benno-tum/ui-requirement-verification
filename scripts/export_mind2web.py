from datasets import load_dataset
from pathlib import Path
from collections import OrderedDict
from PIL import Image, UnidentifiedImageError
import io
import json
import re
import argparse
import warnings
from typing import Optional


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUT = BASE_DIR / "data" / "processed" / "flows" / "mind2web"


def safe_name(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", str(s))[:120]


def json_safe(value):
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def path_for_metadata(path: Path | None) -> str | None:
    if path is None:
        return None
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(BASE_DIR))
    except ValueError:
        return str(resolved)


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
    if obj is None:
        raise TypeError("Screenshot is None")
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


def save_original_img(obj, path: Path):
    img = load_pil_image(obj).convert("RGB")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)


def read_allowed_ids(path: Optional[Path]) -> Optional[set[str]]:
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"Allowed IDs file not found: {path}")
    ids = {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    return ids


def flow_has_exportable_screens(rows: list[dict]) -> tuple[bool, str | None]:
    for row in rows:
        screenshot = row.get("screenshot")
        if screenshot is None:
            return False, "missing_screenshot"
        try:
            img = load_pil_image(screenshot)
            _ = img.size
        except (TypeError, OSError, UnidentifiedImageError, ValueError) as exc:
            return False, f"unreadable_screenshot: {exc}"
    return True, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="test_task")
    parser.add_argument("--max-flows", type=int, default=10)
    parser.add_argument("--max-side", type=int, default=1280)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--save-original-screenshots",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also save each screenshot without downscaling under flow_dir/original/. Enabled by default.",
    )
    parser.add_argument(
        "--allowed-flows-file",
        type=Path,
        default=None,
        help="Optional text file with one annotation_id per line. Only these flows are exported.",
    )
    parser.add_argument(
        "--allowed-websites-file",
        type=Path,
        default=None,
        help="Optional text file with one website per line. Only flows from these websites are exported.",
    )
    args = parser.parse_args()

    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    # Mind2Web screenshots are trusted inputs and can exceed Pillow's conservative warning threshold.
    warnings.simplefilter("ignore", Image.DecompressionBombWarning)

    allowed_flows = read_allowed_ids(args.allowed_flows_file)
    allowed_websites = read_allowed_ids(args.allowed_websites_file)

    print(f"Loading split={args.split} ...")
    ds = load_dataset("osunlp/Multimodal-Mind2Web", split=args.split)

    grouped = OrderedDict()
    for row in ds:
        ann = row["annotation_id"]
        grouped.setdefault(ann, []).append(row)

    selected_flows = OrderedDict()
    skipped_by_filter = 0
    for ann, rows in grouped.items():
        first = rows[0]
        website = str(first.get("website") or "")

        if allowed_flows is not None and ann not in allowed_flows:
            skipped_by_filter += 1
            continue
        if allowed_websites is not None and website not in allowed_websites:
            skipped_by_filter += 1
            continue

        selected_flows[ann] = rows
        if args.max_flows and len(selected_flows) >= args.max_flows:
            break

    skipped_bad_screens = 0
    exported = 0
    skipped_manifest = []

    for i, (ann, rows) in enumerate(selected_flows.items(), start=1):
        ok, reason = flow_has_exportable_screens(rows)
        if not ok:
            skipped_bad_screens += 1
            skipped_manifest.append(
                {
                    "annotation_id": ann,
                    "website": rows[0].get("website"),
                    "domain": rows[0].get("domain"),
                    "reason": reason,
                }
            )
            print(f"[SKIP] {ann} ({rows[0].get('website')}): {reason}")
            continue

        first = rows[0]
        folder = out_dir / f"{exported + 1:02d}_{safe_name(first.get('website'))}_{safe_name(ann)}"
        folder.mkdir(parents=True, exist_ok=True)

        task_meta = {
            "annotation_id": ann,
            "confirmed_task": first.get("confirmed_task"),
            "website": first.get("website"),
            "domain": first.get("domain"),
            "num_steps": len(rows),
            "split": args.split,
            "max_side": args.max_side,
            "allowed_flows_file": path_for_metadata(args.allowed_flows_file),
            "allowed_websites_file": path_for_metadata(args.allowed_websites_file),
        }
        (folder / "task.json").write_text(
            json.dumps(task_meta, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        step_metas = []
        for j, row in enumerate(rows, start=1):
            img_path = folder / f"step_{j:02d}.png"
            save_img(row["screenshot"], img_path, max_side=args.max_side)
            if args.save_original_screenshots:
                original_img_path = folder / "original" / img_path.name
                save_original_img(row["screenshot"], original_img_path)

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

        exported += 1
        print(f"[OK] {folder.name} with {len(rows)} steps")

    export_summary = {
        "split": args.split,
        "max_flows": args.max_flows,
        "max_side": args.max_side,
        "allowed_flows_file": path_for_metadata(args.allowed_flows_file),
        "allowed_websites_file": path_for_metadata(args.allowed_websites_file),
        "num_grouped_flows": len(grouped),
        "num_selected_flows": len(selected_flows),
        "num_exported_flows": exported,
        "num_skipped_by_filter": skipped_by_filter,
        "num_skipped_bad_screens": skipped_bad_screens,
        "skipped_bad_screen_flows": skipped_manifest,
    }
    (out_dir / "export_summary.json").write_text(
        json.dumps(export_summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nDone. Export folder: {out_dir.resolve()}")
    print(f"  Grouped flows:         {len(grouped)}")
    print(f"  Selected after filter: {len(selected_flows)}")
    print(f"  Exported flows:        {exported}")
    print(f"  Skipped by filter:     {skipped_by_filter}")
    print(f"  Skipped bad screens:   {skipped_bad_screens}")


if __name__ == "__main__":
    main()
