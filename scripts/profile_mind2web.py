from __future__ import annotations

import argparse
import csv
import io
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from datasets import load_dataset
import warnings

from PIL import Image, UnidentifiedImageError


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = BASE_DIR / "data" / "generated" / "mind2web_profiles"
DEFAULT_DATASET = "osunlp/Multimodal-Mind2Web"
DEFAULT_MAX_SIDE = 1280


warnings.simplefilter("ignore", Image.DecompressionBombWarning)


def load_pil_image(obj: Any) -> Image.Image | None:
    if obj is None:
        return None
    if hasattr(obj, "save"):
        return obj
    if isinstance(obj, dict) and obj.get("bytes") is not None:
        return Image.open(io.BytesIO(obj["bytes"]))
    if isinstance(obj, str):
        return Image.open(obj)
    return None


def percentile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("percentile() requires at least one value")
    if len(values) == 1:
        return float(values[0])

    ordered = sorted(float(v) for v in values)
    idx = (len(ordered) - 1) * q
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return ordered[lo]
    weight = idx - lo
    return ordered[lo] * (1.0 - weight) + ordered[hi] * weight


def scaled_width_for_max_side(width: int, height: int, max_side: int) -> int:
    longest = max(width, height)
    if longest <= max_side:
        return width
    scale = max_side / float(longest)
    return max(1, int(width * scale))


def orientation(width: int, height: int) -> str:
    if width > height:
        return "landscape"
    if height > width:
        return "portrait"
    return "square"


def safe_float(value: float) -> float:
    return round(float(value), 6)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize_website_stats(
    website: str,
    flows: list[dict[str, Any]],
    website_median_ratio_threshold: float,
) -> dict[str, Any]:
    flow_ratios = [float(f["flow_median_ratio"]) for f in flows]
    flow_min_ratios = [float(f["flow_min_ratio"]) for f in flows]
    flow_scaled_widths = [float(f["flow_median_scaled_width_1280"]) for f in flows]
    num_steps = [int(f["num_steps"]) for f in flows]

    allowed_by_website = statistics.median(flow_ratios) >= website_median_ratio_threshold

    return {
        "website": website,
        "num_flows": len(flows),
        "total_steps": sum(num_steps),
        "website_median_flow_ratio": safe_float(statistics.median(flow_ratios)),
        "website_p25_flow_ratio": safe_float(percentile(flow_ratios, 0.25)),
        "website_min_flow_ratio": safe_float(min(flow_min_ratios)),
        "website_median_scaled_width_1280": safe_float(statistics.median(flow_scaled_widths)),
        "share_flows_ratio_ge_0_30": safe_float(sum(r >= 0.30 for r in flow_ratios) / len(flow_ratios)),
        "share_flows_ratio_ge_0_35": safe_float(sum(r >= 0.35 for r in flow_ratios) / len(flow_ratios)),
        "share_flows_ratio_ge_0_40": safe_float(sum(r >= 0.40 for r in flow_ratios) / len(flow_ratios)),
        "allowed_by_website_filter": allowed_by_website,
    }


def summarize_flow_stats(
    annotation_id: str,
    rows: list[dict[str, Any]],
    max_side: int,
    flow_median_ratio_threshold: float,
    flow_p25_ratio_threshold: float,
    flow_median_scaled_width_threshold: int,
) -> dict[str, Any]:
    website = rows[0]["website"]
    domain = rows[0]["domain"]

    ratios = [float(r["ratio"]) for r in rows]
    scaled_widths = [float(r["scaled_width"]) for r in rows]
    portrait_steps = sum(r["orientation"] == "portrait" for r in rows)
    landscape_steps = sum(r["orientation"] == "landscape" for r in rows)
    square_steps = sum(r["orientation"] == "square" for r in rows)

    flow_median_ratio = statistics.median(ratios)
    flow_p25_ratio = percentile(ratios, 0.25)
    flow_median_scaled_width = statistics.median(scaled_widths)

    allowed_by_flow = (
        flow_median_ratio >= flow_median_ratio_threshold
        and flow_p25_ratio >= flow_p25_ratio_threshold
        and flow_median_scaled_width >= flow_median_scaled_width_threshold
    )

    return {
        "annotation_id": annotation_id,
        "website": website,
        "domain": domain,
        "num_steps": len(rows),
        "flow_median_ratio": safe_float(flow_median_ratio),
        "flow_p25_ratio": safe_float(flow_p25_ratio),
        "flow_min_ratio": safe_float(min(ratios)),
        f"flow_median_scaled_width_{max_side}": safe_float(flow_median_scaled_width),
        "portrait_steps": portrait_steps,
        "landscape_steps": landscape_steps,
        "square_steps": square_steps,
        "allowed_by_flow_filter": allowed_by_flow,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Profile screenshot aspect ratios in Multimodal-Mind2Web and emit "
            "flow-level and website-level summaries that can later be used to "
            "sample only less extreme high-portrait websites/flows."
        )
    )
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--split", default="test_task")
    parser.add_argument("--max-side", type=int, default=DEFAULT_MAX_SIDE)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Directory where CSV/JSON reports and allow-lists are written.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Optional cap for quick inspection runs.",
    )
    parser.add_argument("--website-median-ratio-threshold", type=float, default=0.30)
    parser.add_argument("--flow-median-ratio-threshold", type=float, default=0.35)
    parser.add_argument("--flow-p25-ratio-threshold", type=float, default=0.25)
    parser.add_argument("--flow-median-scaled-width-threshold", type=int, default=450)
    args = parser.parse_args()

    out_dir = args.out_dir / args.split
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading dataset={args.dataset!r}, split={args.split!r} ...")
    ds = load_dataset(args.dataset, split=args.split)

    flow_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    skipped_missing_screenshot = 0
    skipped_unreadable_screenshot = 0
    skipped_rows: list[dict[str, Any]] = []

    for row_idx, row in enumerate(ds):
        if args.max_rows is not None and row_idx >= args.max_rows:
            break

        ann = str(row["annotation_id"])
        website = str(row.get("website") or "unknown")
        domain = str(row.get("domain") or "unknown")

        screenshot_obj = row.get("screenshot")
        img = load_pil_image(screenshot_obj)
        if img is None:
            skipped_missing_screenshot += 1
            skipped_rows.append(
                {
                    "row_idx": row_idx,
                    "annotation_id": ann,
                    "website": website,
                    "domain": domain,
                    "reason": "missing_screenshot",
                }
            )
            continue

        try:
            width, height = img.size
        except (OSError, UnidentifiedImageError, ValueError) as exc:
            skipped_unreadable_screenshot += 1
            skipped_rows.append(
                {
                    "row_idx": row_idx,
                    "annotation_id": ann,
                    "website": website,
                    "domain": domain,
                    "reason": f"unreadable_screenshot: {exc}",
                }
            )
            continue

        ratio = width / height if height else 0.0

        flow_rows[ann].append(
            {
                "row_idx": row_idx,
                "website": website,
                "domain": domain,
                "width": width,
                "height": height,
                "ratio": ratio,
                "scaled_width": scaled_width_for_max_side(width, height, args.max_side),
                "orientation": orientation(width, height),
            }
        )

        if (row_idx + 1) % 250 == 0:
            print(f"  processed {row_idx + 1} rows ...")

    print(f"Collected {len(flow_rows)} flows")

    flow_stats: list[dict[str, Any]] = []
    website_to_flows: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for annotation_id, rows in flow_rows.items():
        flow_stat = summarize_flow_stats(
            annotation_id=annotation_id,
            rows=rows,
            max_side=args.max_side,
            flow_median_ratio_threshold=args.flow_median_ratio_threshold,
            flow_p25_ratio_threshold=args.flow_p25_ratio_threshold,
            flow_median_scaled_width_threshold=args.flow_median_scaled_width_threshold,
        )
        flow_stats.append(flow_stat)
        website_to_flows[flow_stat["website"]].append(flow_stat)

    flow_stats.sort(key=lambda x: (x["flow_median_ratio"], x["flow_p25_ratio"], x["annotation_id"]))

    website_stats = [
        summarize_website_stats(
            website=website,
            flows=flows,
            website_median_ratio_threshold=args.website_median_ratio_threshold,
        )
        for website, flows in website_to_flows.items()
    ]
    website_stats.sort(key=lambda x: (x["website_median_flow_ratio"], x["website"]))

    allowed_websites = [
        row["website"]
        for row in website_stats
        if row["allowed_by_website_filter"]
    ]
    allowed_websites_set = set(allowed_websites)

    allowed_flows = [
        row["annotation_id"]
        for row in flow_stats
        if row["allowed_by_flow_filter"] and row["website"] in allowed_websites_set
    ]

    flow_csv = out_dir / "flow_stats.csv"
    website_csv = out_dir / "website_stats.csv"
    flow_json = out_dir / "flow_stats.json"
    website_json = out_dir / "website_stats.json"
    allowed_websites_txt = out_dir / "allowed_websites.txt"
    allowed_flows_txt = out_dir / "allowed_flows.txt"
    skipped_rows_json = out_dir / "skipped_rows.json"
    summary_json = out_dir / "summary.json"

    write_csv(flow_csv, flow_stats)
    write_csv(website_csv, website_stats)
    flow_json.write_text(json.dumps(flow_stats, indent=2, ensure_ascii=False), encoding="utf-8")
    website_json.write_text(json.dumps(website_stats, indent=2, ensure_ascii=False), encoding="utf-8")
    allowed_websites_txt.write_text("\n".join(allowed_websites) + ("\n" if allowed_websites else ""), encoding="utf-8")
    allowed_flows_txt.write_text("\n".join(allowed_flows) + ("\n" if allowed_flows else ""), encoding="utf-8")
    skipped_rows_json.write_text(json.dumps(skipped_rows, indent=2, ensure_ascii=False), encoding="utf-8")

    summary = {
        "dataset": args.dataset,
        "split": args.split,
        "max_rows": args.max_rows,
        "max_side": args.max_side,
        "num_rows_processed": sum(len(v) for v in flow_rows.values()),
        "num_flows": len(flow_stats),
        "num_websites": len(website_stats),
        "num_skipped_missing_screenshot": skipped_missing_screenshot,
        "num_skipped_unreadable_screenshot": skipped_unreadable_screenshot,
        "website_median_ratio_threshold": args.website_median_ratio_threshold,
        "flow_median_ratio_threshold": args.flow_median_ratio_threshold,
        "flow_p25_ratio_threshold": args.flow_p25_ratio_threshold,
        "flow_median_scaled_width_threshold": args.flow_median_scaled_width_threshold,
        "num_allowed_websites": len(allowed_websites),
        "num_allowed_flows": len(allowed_flows),
        "outputs": {
            "flow_csv": str(flow_csv.relative_to(BASE_DIR)),
            "website_csv": str(website_csv.relative_to(BASE_DIR)),
            "flow_json": str(flow_json.relative_to(BASE_DIR)),
            "website_json": str(website_json.relative_to(BASE_DIR)),
            "allowed_websites_txt": str(allowed_websites_txt.relative_to(BASE_DIR)),
            "allowed_flows_txt": str(allowed_flows_txt.relative_to(BASE_DIR)),
            "skipped_rows_json": str(skipped_rows_json.relative_to(BASE_DIR)),
        },
        "worst_websites_by_median_ratio": website_stats[:10],
        "best_websites_by_median_ratio": website_stats[-10:],
        "worst_flows_by_median_ratio": flow_stats[:10],
        "best_flows_by_median_ratio": flow_stats[-10:],
    }
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\nDone.")
    print(f"  Flow stats:      {flow_csv}")
    print(f"  Website stats:   {website_csv}")
    print(f"  Allowed websites {len(allowed_websites)} -> {allowed_websites_txt}")
    print(f"  Allowed flows    {len(allowed_flows)} -> {allowed_flows_txt}")
    print(f"  Skipped missing screenshots:    {skipped_missing_screenshot}")
    print(f"  Skipped unreadable screenshots: {skipped_unreadable_screenshot}")
    print("\nWorst websites by median flow ratio:")
    for row in website_stats[:10]:
        print(
            "  "
            f"{row['website']}: median_ratio={row['website_median_flow_ratio']:.3f}, "
            f"flows={row['num_flows']}, allowed={row['allowed_by_website_filter']}"
        )


if __name__ == "__main__":
    main()
