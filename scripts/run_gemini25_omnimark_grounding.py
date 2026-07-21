from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

from ui_verifier.common.json_utils import parse_json_response
from ui_verifier.requirements.gemini_client import run_gemini_with_usage


BASE_DIR = Path(__file__).resolve().parents[1]
FLOW_ID = "02_gamestop_a2500e0b-9244-4f0e-b686-fa290c32b829"
RUN_ID = "bbox_gemini25flash_omnimark_atlas_flow02_20260720"
DEFAULT_SOURCE_RUN = (
    BASE_DIR
    / "data/generated/verification_pipeline_runs/bbox_gemini31pro_singlecall_allimages_01_13_20260719"
    / f"{FLOW_ID}.json"
)
DEFAULT_CANDIDATES = BASE_DIR / "data/generated/omniparser_candidate_marks/flow02_20260720/candidates.json"
DEFAULT_OUTPUT_DIR = BASE_DIR / "data/generated/verification_pipeline_runs" / RUN_ID
DEFAULT_WORK_DIR = BASE_DIR / "data/generated/gemini25_omnimark_grounding/flow02_atlas_20260720"
PROMPT_VERSION = "GEMINI25_OMNIMARK_SELECTION_V7_CLAIM_FACT_COVERAGE_MAX2"
MAX_REGIONS_PER_TASK = 2
RECOVERY_TASKS_PER_CALL = 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select OmniParser/OCR marks semantically with Gemini 2.5 Flash.")
    parser.add_argument("--source-run", type=Path, default=DEFAULT_SOURCE_RUN)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--cost-ceiling-usd", type=float, default=0.10)
    parser.add_argument("--prepare-only", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ):
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def collect_tasks(run: dict[str, Any]) -> tuple[dict[int, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    by_step: dict[int, list[dict[str, Any]]] = defaultdict(list)
    metadata: dict[str, dict[str, Any]] = {}
    for result_index, result in enumerate(run.get("results", [])):
        for claim_index, claim in enumerate(result.get("claims", [])):
            first_by_step: dict[int, dict[str, Any]] = {}
            for evidence in claim.get("evidence", []):
                step = int(evidence.get("step_index") or 0)
                if step > 0:
                    first_by_step.setdefault(step, evidence)
            for step, evidence in sorted(first_by_step.items()):
                identifier = f"{result.get('requirement_id')}::{claim.get('claim_id')}::S{step}"
                task = {
                    "task_id": identifier,
                    "requirement_id": result.get("requirement_id"),
                    "requirement_text": result.get("requirement_text"),
                    "claim_id": claim.get("claim_id"),
                    "claim_text": claim.get("claim_text"),
                    "claim_status": claim.get("status"),
                }
                by_step[step].append(task)
                metadata[identifier] = {
                    "result_index": result_index,
                    "claim_index": claim_index,
                    "step": step,
                    "evidence": evidence,
                }
    return dict(by_step), metadata


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
        raise ValueError("Source run contains no screenshot paths.")
    return images


def draw_mark_layer(
    image_path: Path,
    candidates: list[dict[str, Any]],
    *,
    source: str,
    output_path: Path,
) -> None:
    with Image.open(image_path) as source_image:
        image = source_image.convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    color = (192, 38, 211, 240) if source == "omniparser_ui" else (37, 99, 235, 240)
    label_font = font(max(16, image.width // 65))
    line_width = max(2, image.width // 420)
    for candidate in candidates:
        if candidate.get("source") != source:
            continue
        box = candidate.get("bbox")
        if not isinstance(box, list) or len(box) != 4:
            continue
        x1, y1, x2, y2 = (float(value) for value in box)
        draw.rectangle((x1, y1, x2, y2), outline=color, width=line_width)
        label = str(candidate.get("candidate_id") or "?")
        text_box = draw.textbbox((x1, y1), label, font=label_font, stroke_width=1)
        label_width = text_box[2] - text_box[0] + 8
        label_height = text_box[3] - text_box[1] + 6
        label_y = max(0.0, y1 - label_height)
        draw.rectangle((x1, label_y, x1 + label_width, label_y + label_height), fill=color)
        draw.text((x1 + 4, label_y + 2), label, fill="white", font=label_font, stroke_width=1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def build_context_sheet(images: dict[int, Path], output_path: Path) -> None:
    cell_size = (520, 520)
    sheet = Image.new("RGB", (cell_size[0] * 2, cell_size[1] * 2), (232, 235, 240))
    label_font = font(24)
    for index, (step, path) in enumerate(sorted(images.items())):
        with Image.open(path) as source:
            thumb = source.convert("RGB")
        thumb.thumbnail((cell_size[0] - 24, cell_size[1] - 54))
        cell = Image.new("RGB", cell_size, "white")
        cell.paste(thumb, ((cell_size[0] - thumb.width) // 2, 44))
        ImageDraw.Draw(cell).text((12, 10), f"Flow context — step {step}", fill="black", font=label_font)
        x = (index % 2) * cell_size[0]
        y = (index // 2) * cell_size[1]
        sheet.paste(cell, (x, y))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def build_candidate_atlas(
    image_path: Path,
    candidates: list[dict[str, Any]],
    output_path: Path,
) -> None:
    ui_candidates = [candidate for candidate in candidates if candidate.get("source") == "omniparser_ui"]
    columns, tile_width, tile_height = 5, 240, 164
    rows = max(1, math.ceil(len(ui_candidates) / columns))
    atlas = Image.new("RGB", (columns * tile_width, rows * tile_height), (241, 243, 246))
    title_font = font(19)
    caption_font = font(12)
    with Image.open(image_path) as source:
        clean = source.convert("RGB")
    for index, candidate in enumerate(ui_candidates):
        box = candidate.get("bbox")
        if not isinstance(box, list) or len(box) != 4:
            continue
        x1, y1, x2, y2 = (int(round(float(value))) for value in box)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(clean.width, x2), min(clean.height, y2)
        if x2 <= x1 or y2 <= y1:
            continue
        crop = clean.crop((x1, y1, x2, y2))
        crop.thumbnail((tile_width - 12, 112))
        tile = Image.new("RGB", (tile_width - 4, tile_height - 4), "white")
        tile.paste(crop, ((tile.width - crop.width) // 2, 30 + (112 - crop.height) // 2))
        draw = ImageDraw.Draw(tile)
        candidate_id = str(candidate.get("candidate_id") or "?")
        draw.rectangle((0, 0, tile.width, 28), fill=(147, 51, 234))
        draw.text((7, 4), candidate_id, fill="white", font=title_font)
        caption = str(candidate.get("caption") or "").strip()
        if caption:
            draw.text((6, 145), caption[:36], fill=(55, 65, 81), font=caption_font)
        x = (index % columns) * tile_width + 2
        y = (index // columns) * tile_height + 2
        atlas.paste(tile, (x, y))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(output_path)


def approximate_image_tokens(path: Path) -> int:
    with Image.open(path) as image:
        width, height = image.size
    if width <= 384 and height <= 384:
        return 258
    crop = max(1, math.floor(min(width, height) / 1.5))
    return math.ceil(width / crop) * math.ceil(height / crop) * 258


def prompt_for_step(step: int, tasks: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> str:
    candidate_catalog = [
        {
            "id": candidate.get("candidate_id"),
            "source": candidate.get("source"),
            "ocr_text": candidate.get("text") or None,
            "bbox_xyxy": candidate.get("bbox"),
            "local_caption": candidate.get("caption") or None,
        }
        for candidate in candidates
    ]
    return f"""
You are grounding already-verified UI claims in target screenshot step {step}. Use screenshot pixels only; do not infer HTML or hidden state.

Images after this prompt are ordered as follows:
1. Clean target screenshot step {step}. Use it to understand the UI without mark obstruction.
2. The same target screenshot with magenta OmniParser UI-region IDs U##.
3. The same target screenshot with blue OCR text-line IDs T##.
4. A candidate crop atlas: every magenta U-region is isolated and enlarged beneath its ID. Use it to verify that a selected U-ID actually contains the evidence you name. Captions are noisy local-model hints, not ground truth.
5. A downscaled overview of all flow screenshots for sequence context only. Never return an ID from the overview.

For every task, select the smallest semantically sufficient set of target-image IDs, with a strict maximum of {MAX_REGIONS_PER_TASK} total regions. A correct region must visibly support the exact claim, not merely contain lexically related text. Return exactly ONE best region by default. Return TWO only when the claim is genuinely conjunctive and neither region alone can visibly support it. Never add a second region merely because it is relevant, repeated, corroborating, or another view of evidence already captured by the first.

Use the supplied claim_status as a constraint. For every claim whose status is neither MISSING nor HIDDEN, return at least one box containing the visible evidence for that status. This rule also applies to partial, caveated, uncertain, contradicted, or any future non-missing status. For CONTRADICTED claims, localize the visible absence indicator, conflicting value, disabled state, error, or other concrete UI evidence on which the contradiction is based. If no candidate ID covers the evidence well, draw one supplemental box; uncertainty about the proposals is not a reason to return no box.

Return NO_VISIBLE_REGION with no IDs only when the claim_status is MISSING or HIDDEN, or when the claim genuinely depends on a whole-screen transition with no honest local indicator. Do not fabricate a weak box for a missing or hidden claim.

Prefer one enclosing semantic component over several nearby child regions. Never select both a parent container and its descendants when the parent already contains the required evidence. If several close fragments belong to one visual component and no proposed container covers them, return one tight supplemental union box around that component instead of many fragment IDs. Do not combine spatially separate or semantically different components merely to reduce the count.

Before returning each task, perform this merge check: if you selected two or more regions, ask whether they are adjacent fragments of the same visual component or continuous text block. If yes, remove those candidate IDs and replace them with one tight supplemental region covering their combined visible extent. If they are separate controls, separate list entries, or distinct pieces of evidence, keep them separate.

Prefer OmniParser U-regions when they cover the meaningful component or container. Use T-regions for precise textual evidence. Inspect both the clean and marked versions before deciding.

First derive a short list called required_visible_facts from the requirement text, claim text, and claim_status. Include every distinct visible fact needed to justify that status; do not weaken or paraphrase away conjunctions, comparisons, relationships, state, or context in the claim. Base localization on those texts and screenshot pixels, not on assumptions about what an earlier verifier may have noticed.

Apply two independent checks before selecting an ID:
1. CONTAINMENT: the exact visible indicator named in the rationale must be inside the region. Semantic proximity or partial overlap is insufficient. Reject a candidate that crosses substantially into unrelated content or omits a relevant part of the component.
2. SUFFICIENCY: the pixels inside the returned region must, by themselves, provide enough visible information to justify the supplied claim_status for the claim. A heading, keyword, icon, or isolated value is insufficient when the claim depends on its surrounding options, context, relationship, or state.

If a candidate passes containment but fails sufficiency, prefer one enclosing candidate that includes the necessary context. If none exists, draw a tight supplemental box around the complete relevant component. Use a second spatially separate region only when no single rectangle can honestly contain the jointly required evidence. The union of the returned regions must visibly cover every required_visible_fact. For each returned region, report which fact numbers it covers. If any required fact remains uncovered, revise the selection before responding. Your rationale must name only content actually enclosed by the returned region. Do not use website-, domain-, or flow-specific assumptions; apply these criteria uniformly to every task.

If no listed ID covers necessary visible evidence, return a supplemental region using [ymin, xmin, ymax, xmax] normalized to 0–1000 relative to the CLEAN TARGET screenshot. Supplemental regions are a fallback, not a replacement for a suitable ID.

Applicability values:
- SINGLE_REGION: one ID or supplemental box is sufficient.
- MULTI_REGION: multiple regions are jointly required.
- WHOLE_SCREEN_OR_TRANSITION: the claim concerns a page-wide state or change across screenshots; return any useful target indicators but do not pretend one small box proves the whole claim.
- NO_VISIBLE_REGION: no honest visible local evidence exists; normally reserved for MISSING or HIDDEN claims.

Tasks:
{json.dumps(tasks, indent=2, ensure_ascii=False)}

Candidate catalog (OCR text is a hint and must be verified visually):
{json.dumps(candidate_catalog, indent=2, ensure_ascii=False)}

Return JSON only:
{{
  "selections": [
    {{
      "task_id": "REQ::CLAIM::S1",
      "selected_candidate_ids": ["U17", "T28"],
      "supplemental_regions": [
        {{"box_2d": [100, 50, 400, 950], "description": "visible region not covered by any mark"}}
      ],
      "required_visible_facts": ["fact 1", "fact 2"],
      "region_fact_coverage": {{"U17": [1], "T28": [2]}},
      "applicability": "SINGLE_REGION | MULTI_REGION | WHOLE_SCREEN_OR_TRANSITION | NO_VISIBLE_REGION",
      "rationale": "short explanation tied to visible evidence",
      "confidence": 0.0
    }}
  ]
}}
""".strip()


def prepare_assets(
    work_dir: Path,
    images: dict[int, Path],
    candidates_by_step: dict[str, list[dict[str, Any]]],
) -> tuple[dict[int, dict[str, Path]], Path]:
    assets: dict[int, dict[str, Path]] = {}
    context_path = work_dir / "flow_context.png"
    build_context_sheet(images, context_path)
    for step, image_path in sorted(images.items()):
        ui_path = work_dir / f"step_{step:02d}_ui_marks.png"
        ocr_path = work_dir / f"step_{step:02d}_ocr_marks.png"
        atlas_path = work_dir / f"step_{step:02d}_candidate_atlas.png"
        candidates = candidates_by_step[str(step)]
        draw_mark_layer(image_path, candidates, source="omniparser_ui", output_path=ui_path)
        draw_mark_layer(image_path, candidates, source="tesseract_line", output_path=ocr_path)
        build_candidate_atlas(image_path, candidates, atlas_path)
        assets[step] = {"clean": image_path, "ui": ui_path, "ocr": ocr_path, "atlas": atlas_path}
    return assets, context_path


def validate_normalized_box(value: Any) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    ymin, xmin, ymax, xmax = (float(item) for item in value)
    if not (0 <= ymin < ymax <= 1000 and 0 <= xmin < xmax <= 1000):
        return None
    return [ymin, xmin, ymax, xmax]


def resolve_supplemental_box(
    value: Any, *, image_width: int, image_height: int
) -> tuple[list[float], str] | None:
    """Resolve Gemini's requested normalized box, tolerating explicit pixel output.

    Gemini occasionally returns an otherwise valid [ymin, xmin, ymax, xmax]
    rectangle in source-image pixels despite the normalized-coordinate prompt.
    Values above 1000 make that mistake unambiguous for the current assets.
    """
    normalized = validate_normalized_box(value)
    if normalized is not None:
        ymin, xmin, ymax, xmax = normalized
        return (
            [xmin / 1000 * image_width, ymin / 1000 * image_height, xmax / 1000 * image_width, ymax / 1000 * image_height],
            "normalized_0_1000",
        )
    if not isinstance(value, list) or len(value) != 4:
        return None
    ymin, xmin, ymax, xmax = (float(item) for item in value)
    if max(ymin, xmin, ymax, xmax) <= 1000:
        return None
    if not (0 <= ymin < ymax <= image_height and 0 <= xmin < xmax <= image_width):
        return None
    return [xmin, ymin, xmax, ymax], "image_pixels_yxyx"


def normalize_response(value: Any) -> dict[str, list[dict[str, Any]]]:
    """Accept the equivalent top-level shapes Gemini emits in JSON mode."""
    if isinstance(value, list):
        items = value
    elif isinstance(value, dict) and isinstance(value.get("selections"), list):
        items = value["selections"]
    elif isinstance(value, dict) and value.get("task_id"):
        items = [value]
    else:
        raise ValueError("Gemini response has no recognizable selections.")
    return {"selections": [item for item in items if isinstance(item, dict)]}


def main() -> None:
    args = parse_args()
    source_run = load_json(args.source_run)
    flow_id = str(source_run.get("flow_id") or FLOW_ID)
    run_id = args.output_dir.name
    package = load_json(args.candidates)
    if package.get("flow_id") != source_run.get("flow_id"):
        raise ValueError("Candidate package and source run flow IDs differ.")
    candidates_by_step = package.get("steps") or {}
    run = deepcopy(source_run)
    tasks_by_step, task_metadata = collect_tasks(run)
    images = source_images(run)
    args.work_dir.mkdir(parents=True, exist_ok=True)
    assets, context_path = prepare_assets(args.work_dir, images, candidates_by_step)

    prompt_characters = 0
    estimated_image_tokens = 0
    for step, tasks in sorted(tasks_by_step.items()):
        prompt_characters += len(prompt_for_step(step, tasks, candidates_by_step[str(step)]))
        estimated_image_tokens += sum(
            approximate_image_tokens(path)
            for path in (
                assets[step]["clean"],
                assets[step]["ui"],
                assets[step]["ocr"],
                assets[step]["atlas"],
                context_path,
            )
        )
    estimated_text_tokens = math.ceil(prompt_characters / 4)
    max_output_tokens = int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", "4096"))
    maximum_output_tokens = max_output_tokens * len(tasks_by_step)
    estimated_max_cost = (estimated_image_tokens + estimated_text_tokens) * 0.30 / 1_000_000 + maximum_output_tokens * 2.50 / 1_000_000
    estimate = {
        "model": args.model,
        "calls": len(tasks_by_step),
        "images_per_call": 5,
        "estimated_image_tokens": estimated_image_tokens,
        "estimated_text_tokens": estimated_text_tokens,
        "configured_max_output_tokens_per_call": max_output_tokens,
        "estimated_upper_cost_usd": round(estimated_max_cost, 6),
        "cost_ceiling_usd": args.cost_ceiling_usd,
    }
    (args.work_dir / "cost_estimate.json").write_text(json.dumps(estimate, indent=2), encoding="utf-8")
    print(json.dumps(estimate, indent=2))
    if args.prepare_only:
        return
    if estimated_max_cost > args.cost_ceiling_usd:
        raise RuntimeError("Preflight estimate exceeds cost ceiling.")

    checkpoint_path = args.work_dir / "responses.json"
    checkpoints = load_json(checkpoint_path) if checkpoint_path.is_file() else {}
    usage_records: list[dict[str, Any]] = []
    selections: dict[str, dict[str, Any]] = {}
    cumulative_cost = 0.0
    for step, tasks in sorted(tasks_by_step.items()):
        saved = checkpoints.get(str(step))
        saved_response = saved.get("response") if isinstance(saved, dict) else None
        try:
            response_data = normalize_response(saved_response)
        except ValueError:
            response_data = {"selections": []}
        requested_ids = {str(task["task_id"]) for task in tasks}
        returned_ids = {
            str(item.get("task_id") or "")
            for item in response_data["selections"]
            if str(item.get("task_id") or "") in requested_ids
        }
        missing_tasks = [task for task in tasks if str(task["task_id"]) not in returned_ids]
        saved_usage = saved.get("usage") if isinstance(saved, dict) else None
        step_usage = saved_usage if isinstance(saved_usage, list) else ([saved_usage] if saved_usage else [])
        if missing_tasks:
            paths = [
                assets[step]["clean"],
                assets[step]["ui"],
                assets[step]["ocr"],
                assets[step]["atlas"],
                context_path,
            ]
            for start in range(0, len(missing_tasks), RECOVERY_TASKS_PER_CALL):
                recovery_tasks = missing_tasks[start : start + RECOVERY_TASKS_PER_CALL]
                result = run_gemini_with_usage(
                    prompt_for_step(step, recovery_tasks, candidates_by_step[str(step)]),
                    [path.read_bytes() for path in paths],
                    args.model,
                    temperature=0.0,
                    usage_context={
                        "flow_id": flow_id,
                        "step_index": step,
                        "prompt_version": PROMPT_VERSION,
                        "task_count": len(recovery_tasks),
                        "grounding_only": True,
                        "recovery_batch": True,
                    },
                )
                parsed = parse_json_response(result.text)
                new_response = normalize_response(parsed)
                response_data["selections"].extend(new_response["selections"])
                step_usage.append(result.usage_record)
                checkpoints[str(step)] = {"response": response_data, "usage": step_usage}
                checkpoint_path.write_text(json.dumps(checkpoints, indent=2, ensure_ascii=False), encoding="utf-8")

            recovered_ids = {
                str(item.get("task_id") or "")
                for item in response_data["selections"]
                if str(item.get("task_id") or "") in requested_ids
            }
            still_missing = sorted(requested_ids - recovered_ids)
            if still_missing:
                raise RuntimeError(
                    f"Gemini omitted {len(still_missing)} tasks after bounded recovery for step {step}: "
                    + ", ".join(still_missing)
                )
        for usage in step_usage:
            usage_records.append(usage)
            cumulative_cost += float(usage.get("estimated_cost_usd") or 0.0)
        if cumulative_cost > args.cost_ceiling_usd:
            raise RuntimeError(f"Recorded cost ${cumulative_cost:.4f} exceeds ceiling ${args.cost_ceiling_usd:.4f}.")
        for item in response_data.get("selections", []):
            if isinstance(item, dict) and str(item.get("task_id") or "") in task_metadata:
                selections[str(item["task_id"])] = item

    recorded_prompt_versions = {
        str(record.get("context", {}).get("prompt_version"))
        for record in usage_records
        if isinstance(record.get("context"), dict) and record.get("context", {}).get("prompt_version")
    }
    effective_prompt_version = (
        next(iter(recorded_prompt_versions))
        if len(recorded_prompt_versions) == 1
        else PROMPT_VERSION
    )
    if effective_prompt_version != PROMPT_VERSION:
        effective_prompt_version = f"{effective_prompt_version}_CAPPED4_POSTPROCESS"

    candidate_lookup = {
        int(step): {str(candidate.get("candidate_id") or "").upper(): candidate for candidate in candidates}
        for step, candidates in candidates_by_step.items()
    }
    evidence_by_claim: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    source_counts: Counter[str] = Counter()
    for identifier, meta in task_metadata.items():
        selection = selections.get(identifier) or {}
        step = int(meta["step"])
        template = meta["evidence"]
        image_path = images[step]
        with Image.open(image_path) as image:
            width, height = image.size
        seen: set[str] = set()
        selected_candidate_ids = list(selection.get("selected_candidate_ids") or [])[:MAX_REGIONS_PER_TASK]
        for raw_id in selected_candidate_ids:
            candidate_id = str(raw_id).strip().upper()
            candidate = candidate_lookup[step].get(candidate_id)
            if candidate is None or candidate_id in seen:
                continue
            seen.add(candidate_id)
            bbox = candidate.get("bbox")
            if not isinstance(bbox, list) or len(bbox) != 4:
                continue
            source_name = "gemini_visual_grounding_omnimark_selection"
            description = f"Gemini 2.5 selected {candidate_id}: {selection.get('rationale') or 'supporting marked region'}"
            evidence_by_claim[(meta["result_index"], meta["claim_index"])].append(
                {
                    **template,
                    "bbox": [float(value) for value in bbox],
                    "visible_observation": description,
                    "confidence": float(selection.get("confidence") or 0.0),
                    "bbox_metadata": {
                        "image_path": str(image_path),
                        "image_width": width,
                        "image_height": height,
                        "coordinate_space": "image_pixels",
                        "source": source_name,
                        "role": "SUPPORTING",
                        "localizability": selection.get("applicability") or "LOCAL_REGION",
                        "description": description,
                        "candidate_id": candidate_id,
                        "candidate_source": candidate.get("source"),
                        "candidate_text": candidate.get("text"),
                        "selection_model": args.model,
                        "selection_rationale": selection.get("rationale"),
                        "selection_applicability": selection.get("applicability"),
                        "prompt_version": effective_prompt_version,
                    },
                    "metadata": {
                        **(template.get("metadata") or {}),
                        "grounding_method": "gemini25_omnimark_selection",
                    },
                }
            )
            source_counts[source_name] += 1
        remaining_region_budget = max(0, MAX_REGIONS_PER_TASK - len(seen))
        for supplemental in list(selection.get("supplemental_regions") or [])[:remaining_region_budget]:
            if not isinstance(supplemental, dict):
                continue
            resolved = resolve_supplemental_box(
                supplemental.get("box_2d"), image_width=width, image_height=height
            )
            if resolved is None:
                continue
            bbox, supplemental_coordinate_space = resolved
            source_name = "gemini_visual_grounding_omnimark_supplemental"
            description = str(supplemental.get("description") or selection.get("rationale") or "Gemini supplemental region")
            evidence_by_claim[(meta["result_index"], meta["claim_index"])].append(
                {
                    **template,
                    "bbox": bbox,
                    "visible_observation": description,
                    "confidence": float(selection.get("confidence") or 0.0),
                    "bbox_metadata": {
                        "image_path": str(image_path),
                        "image_width": width,
                        "image_height": height,
                        "coordinate_space": "image_pixels",
                        "source": source_name,
                        "role": "SUPPORTING",
                        "localizability": selection.get("applicability") or "LOCAL_REGION",
                        "description": description,
                        "raw_supplemental_box_2d": supplemental.get("box_2d"),
                        "supplemental_coordinate_space": supplemental_coordinate_space,
                        "selection_model": args.model,
                        "selection_rationale": selection.get("rationale"),
                        "selection_applicability": selection.get("applicability"),
                        "prompt_version": effective_prompt_version,
                    },
                    "metadata": {
                        **(template.get("metadata") or {}),
                        "grounding_method": "gemini25_omnimark_supplemental",
                    },
                }
            )
            source_counts[source_name] += 1

    for result_index, result in enumerate(run.get("results", [])):
        for claim_index, claim in enumerate(result.get("claims", [])):
            claim["evidence"] = evidence_by_claim.get((result_index, claim_index), [])
        result["evidence"] = [evidence for claim in result.get("claims", []) for evidence in claim.get("evidence", [])]

    created_at = utc_now()
    run["metadata"] = {
        **(run.get("metadata") or {}),
        "run_id": run_id,
        "created_at": created_at,
        "source_run": str(args.source_run.resolve()),
        "grounding_method": "gemini25_omnimark_selection",
        "grounding_model": args.model,
        "candidate_package": str(args.candidates.resolve()),
    }
    claims = [claim for result in run.get("results", []) for claim in result.get("claims", [])]
    box_count = sum(len(claim.get("evidence", [])) for claim in claims)
    labels = Counter(str(result.get("final_label") or "UNKNOWN") for result in run.get("results", []))
    summary = {
        "schema_version": "gemini_candidate_mark_bbox_run_set_v1",
        "run_id": run_id,
        "created_at": created_at,
        "configuration": {
            "model": args.model,
            "requested_execution_mode": "grouped-candidate-mark-grounding",
            "image_variant": "preferred-original",
            "claim_decomposition_policy": "provided/preserved",
            "aggregation": "preserved from Gemini 3.1 Pro source run",
            "grounding": "Gemini 2.5 Flash selects OmniParser UI and OCR IDs from clean plus separately marked target screenshots, with normalized supplemental fallback",
            "estimated_cost_usd": cumulative_cost,
            "prompt_version": effective_prompt_version,
        },
        "fallback_flows": [],
        "totals": {
            "flows": 1,
            "requirements": len(run.get("results", [])),
            "claims": len(claims),
            "evidence_records": box_count,
            "bounding_boxes": box_count,
            "bbox_sources": dict(source_counts),
            "estimated_cost_usd": cumulative_cost,
        },
        "flows": [
            {
                "flow_id": flow_id,
                "execution_mode": "grouped-candidate-mark-grounding",
                "requirements": len(run.get("results", [])),
                "claims": len(claims),
                "evidence_records": box_count,
                "bounding_boxes": box_count,
                "bbox_sources": dict(source_counts),
                "labels": dict(labels),
                "api_calls": len(usage_records),
                "fallbacks": source_counts.get("gemini_visual_grounding_omnimark_supplemental", 0),
                "prompt_version": effective_prompt_version,
            }
        ],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / f"{flow_id}.json").write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Completed {run_id}: {box_count} boxes, {len(usage_records)} calls, ${cumulative_cost:.4f}")


if __name__ == "__main__":
    main()
