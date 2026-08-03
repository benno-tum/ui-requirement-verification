from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from ui_verifier.common.json_utils import parse_json_response
from ui_verifier.localization.candidate_marks import CandidateRegion, pad_bbox, resolve_candidate_ids
from ui_verifier.localization.text_box_localizer import run_tesseract_boxes
from ui_verifier.requirements.gemini_client import run_gemini_with_usage


BASE_DIR = Path(__file__).resolve().parents[1]
FLOW_ID = "02_gamestop_a2500e0b-9244-4f0e-b686-fa290c32b829"
DEFAULT_SOURCE_RUN = (
    BASE_DIR
    / "data/generated/verification_pipeline_runs"
    / "bbox_gemini31pro_singlecall_allimages_01_13_20260719"
    / f"{FLOW_ID}.json"
)
DEFAULT_OUTPUT_DIR = (
    BASE_DIR
    / "data/generated/verification_pipeline_runs"
    / "bbox_omniparser_candidate_marks_flow02_20260720"
)
DEFAULT_WORK_DIR = BASE_DIR / "data/generated/omniparser_candidate_marks/flow02_20260720"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-ground an existing verification flow using screenshot-only OmniParser candidate marks."
    )
    parser.add_argument("--source-run", type=Path, default=DEFAULT_SOURCE_RUN)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--model", default="gemini-3.1-pro-preview")
    parser.add_argument("--omniparser-python", type=Path, default=Path("/private/tmp/omniparser-venv/bin/python"))
    parser.add_argument("--omniparser-root", type=Path, default=Path("/private/tmp/OmniParser"))
    parser.add_argument(
        "--omniparser-model",
        type=Path,
        default=Path("/private/tmp/OmniParser/weights/icon_detect_v3/model.pt"),
    )
    parser.add_argument(
        "--detector-output",
        type=Path,
        help="Reuse an existing omniparser_regions.json instead of rerunning OmniParser.",
    )
    parser.add_argument("--max-icons", type=int, default=70)
    parser.add_argument("--max-text", type=int, default=70)
    parser.add_argument("--cost-ceiling-usd", type=float, default=1.0)
    parser.add_argument("--skip-gemini", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def task_id(requirement_id: str, claim_id: str, evidence_index: int) -> str:
    return f"{requirement_id}::{claim_id}::E{evidence_index}"


def collect_tasks(run: dict[str, Any]) -> tuple[dict[int, list[dict[str, Any]]], dict[str, tuple[int, int, int]]]:
    by_step: dict[int, list[dict[str, Any]]] = defaultdict(list)
    pointers: dict[str, tuple[int, int, int]] = {}
    for result_index, result in enumerate(run.get("results", [])):
        for claim_index, claim in enumerate(result.get("claims", [])):
            for evidence_index, evidence in enumerate(claim.get("evidence", [])):
                step_index = int(evidence.get("step_index") or 0)
                if step_index <= 0:
                    continue
                identifier = task_id(
                    str(result.get("requirement_id") or "REQ"),
                    str(claim.get("claim_id") or "CLAIM"),
                    evidence_index + 1,
                )
                by_step[step_index].append(
                    {
                        "task_id": identifier,
                        "requirement_id": result.get("requirement_id"),
                        "requirement_text": result.get("requirement_text"),
                        "claim_id": claim.get("claim_id"),
                        "claim_text": claim.get("claim_text"),
                        "claim_status": claim.get("status"),
                        "existing_observation": evidence.get("visible_observation"),
                    }
                )
                pointers[identifier] = (result_index, claim_index, evidence_index)
    return dict(by_step), pointers


def original_images(run: dict[str, Any]) -> dict[int, Path]:
    images: dict[int, Path] = {}
    for result in run.get("results", []):
        for claim in result.get("claims", []):
            for evidence in claim.get("evidence", []):
                step_index = int(evidence.get("step_index") or 0)
                path = Path(str(evidence.get("screenshot_path") or ""))
                if step_index > 0 and path.is_file():
                    images.setdefault(step_index, path.resolve())
    if not images:
        raise ValueError("The source run contains no screenshot evidence paths.")
    return images


def run_omniparser(args: argparse.Namespace, images: dict[int, Path]) -> dict[str, Any]:
    detector_output = args.work_dir / "omniparser_regions.json"
    command = [
        str(args.omniparser_python),
        str(BASE_DIR / "scripts/omniparser_detect.py"),
        "--model",
        str(args.omniparser_model),
        "--output",
        str(detector_output),
    ]
    for image_path in images.values():
        command.extend(["--image", str(image_path)])
    env = os.environ.copy()
    env["PYTHONPATH"] = str(args.omniparser_root)
    subprocess.run(command, check=True, cwd=BASE_DIR, env=env)
    return load_json(detector_output)


def build_candidates(
    image_path: Path,
    detector_image: dict[str, Any],
    *,
    max_icons: int,
    max_text: int,
) -> list[CandidateRegion]:
    with Image.open(image_path) as image:
        width, height = image.size
    regions: list[CandidateRegion] = []
    icon_regions = sorted(
        detector_image.get("regions", []),
        key=lambda region: float(region.get("confidence") or 0.0),
        reverse=True,
    )[:max_icons]
    icon_number = 0
    for region in icon_regions:
        raw_box = region.get("bbox")
        if not isinstance(raw_box, list) or len(raw_box) != 4:
            continue
        x1, y1, x2, y2 = (float(value) for value in raw_box)
        if x2 - x1 < 6 or y2 - y1 < 6 or (x2 - x1) * (y2 - y1) > width * height * 0.45:
            continue
        icon_number += 1
        regions.append(
            CandidateRegion(
                candidate_id=f"U{icon_number:02d}",
                source="omniparser_ui",
                bbox=(x1, y1, x2, y2),
                confidence=float(region.get("confidence") or 0.0),
            )
        )

    tesseract = shutil.which("tesseract")
    if tesseract:
        text_boxes = run_tesseract_boxes(
            image_path,
            tesseract_path=tesseract,
            psm=11,
            timeout_seconds=120,
        )
        lines = [
            box for box in text_boxes
            if box.level == "line" and len(box.text.strip()) >= 2 and float(box.confidence or 0.0) >= 0.35
        ]
        lines.sort(key=lambda box: (box.bbox["y1"], box.bbox["x1"]))
        for text_number, box in enumerate(lines[:max_text], start=1):
            regions.append(
                CandidateRegion(
                    candidate_id=f"T{text_number:02d}",
                    source="tesseract_line",
                    bbox=(box.bbox["x1"], box.bbox["y1"], box.bbox["x2"], box.bbox["y2"]),
                    text=box.text,
                    confidence=float(box.confidence or 0.0),
                )
            )
    return regions


def font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                pass
    return ImageFont.load_default()


def draw_candidates(image_path: Path, candidates: list[CandidateRegion], output_path: Path) -> None:
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    label_font = font(max(13, int(image.width / 75)))
    for candidate in candidates:
        x1, y1, x2, y2 = candidate.bbox
        color = (0, 110, 255, 235) if candidate.source == "tesseract_line" else (215, 0, 140, 235)
        draw.rectangle((x1, y1, x2, y2), outline=color, width=max(2, image.width // 500))
        text_box = draw.textbbox((x1, y1), candidate.candidate_id, font=label_font, stroke_width=1)
        label_width = text_box[2] - text_box[0] + 8
        label_height = text_box[3] - text_box[1] + 6
        label_y = max(0, y1 - label_height)
        draw.rectangle((x1, label_y, x1 + label_width, label_y + label_height), fill=color)
        draw.text((x1 + 4, label_y + 2), candidate.candidate_id, fill="white", font=label_font, stroke_width=1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def selection_prompt(step_index: int, tasks: list[dict[str, Any]], candidates: list[CandidateRegion]) -> str:
    text_candidates = [
        {"id": candidate.candidate_id, "recognized_text": candidate.text}
        for candidate in candidates
        if candidate.text
    ]
    return f"""
You are performing screenshot-only evidence localization for screenshot step {step_index}.

Two images are attached: first the untouched original screenshot, then the same screenshot with numbered visual candidate regions. Blue T-candidates are OCR-derived text regions. Magenta U-candidates are UI regions detected by OmniParser from pixels only.

For each task, inspect the original screenshot and select the candidate IDs that together contain the smallest semantically sufficient visible evidence. You do not need to know the evidence appearance in advance: discover it from the requirement, claim, and screenshot. Select multiple IDs when the claim needs multiple indicators. Prefer the complete relevant UI component over a nearby keyword. Do not select a region merely because its text overlaps the claim. If no candidate actually covers sufficient visible evidence, return an empty list and applicability NO_CANDIDATE or NO_VISIBLE_REGION.

Tasks:
{json.dumps(tasks, indent=2, ensure_ascii=False)}

Recognized text candidates (image-derived OCR; verify visually):
{json.dumps(text_candidates, indent=2, ensure_ascii=False)}

Return JSON only:
{{
  "selections": [
    {{
      "task_id": "REQ::CLAIM::E1",
      "candidate_ids": ["U01", "T02"],
      "applicability": "LOCAL_REGION | MULTI_REGION | NO_CANDIDATE | NO_VISIBLE_REGION",
      "rationale": "short visual justification",
      "confidence": 0.0
    }}
  ]
}}
""".strip()


def render_contact_sheet(
    image_path: Path,
    tasks: list[dict[str, Any]],
    selections: dict[str, list[CandidateRegion]],
    output_path: Path,
) -> None:
    with Image.open(image_path) as source:
        original = source.convert("RGB")
    cards: list[Image.Image] = []
    title_font = font(18)
    for task in tasks:
        chosen = selections.get(task["task_id"], [])
        if not chosen:
            continue
        x1 = min(candidate.bbox[0] for candidate in chosen)
        y1 = min(candidate.bbox[1] for candidate in chosen)
        x2 = max(candidate.bbox[2] for candidate in chosen)
        y2 = max(candidate.bbox[3] for candidate in chosen)
        margin_x = max(30, int((x2 - x1) * 0.3))
        margin_y = max(30, int((y2 - y1) * 0.8))
        crop_box = (
            max(0, int(x1 - margin_x)),
            max(0, int(y1 - margin_y)),
            min(original.width, int(x2 + margin_x)),
            min(original.height, int(y2 + margin_y)),
        )
        crop = original.crop(crop_box)
        crop.thumbnail((1120, 360))
        card = Image.new("RGB", (1200, crop.height + 74), "white")
        draw = ImageDraw.Draw(card)
        label = f"{task['task_id']}  selected: {', '.join(c.candidate_id for c in chosen)}"
        draw.text((12, 8), label, fill="black", font=title_font)
        draw.text((12, 34), str(task.get("claim_text") or "")[:145], fill=(45, 45, 45), font=title_font)
        card.paste(crop, (12, 68))
        cards.append(card)
    if not cards:
        cards = [Image.new("RGB", (1200, 100), "white")]
    sheet = Image.new("RGB", (1200, sum(card.height for card in cards)), (235, 235, 235))
    y = 0
    for card in cards:
        sheet.paste(card, (0, y))
        y += card.height
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def validation_prompt(
    all_tasks: list[dict[str, Any]],
    current: dict[str, list[str]],
    attachment_steps: list[int],
) -> str:
    return f"""
Validate screenshot-only evidence regions selected in a previous pass. The attachments alternate between a full marked screenshot and a contact sheet of the selected evidence crops for that screenshot.

The attachment pairs are ordered by screenshot step: {attachment_steps}.

For every task, check whether the selected crop contains semantically sufficient visible evidence for the exact claim. If it is valid, keep the current IDs. If it is wrong or materially incomplete, choose replacement IDs from the corresponding marked screenshot. If no marked candidate is sufficient, return an empty replacement list. Do not validate a box merely because it contains a related word.

Tasks:
{json.dumps(all_tasks, indent=2, ensure_ascii=False)}

Current selections:
{json.dumps(current, indent=2, ensure_ascii=False)}

Return JSON only:
{{
  "validations": [
    {{
      "task_id": "REQ::CLAIM::E1",
      "valid": true,
      "replacement_candidate_ids": [],
      "reason": "short visual check"
    }}
  ]
}}
""".strip()


def call_gemini(
    *,
    prompt: str,
    images: list[Path],
    model: str,
    context: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    response = run_gemini_with_usage(
        prompt,
        [image.read_bytes() for image in images],
        model,
        temperature=0.0,
        usage_context=context,
    )
    parsed = parse_json_response(response.text)
    if not isinstance(parsed, dict):
        raise ValueError("Gemini response was not a JSON object.")
    return parsed, response.usage_record


def replace_evidence(
    run: dict[str, Any],
    pointers: dict[str, tuple[int, int, int]],
    selections: dict[str, list[CandidateRegion]],
    selection_details: dict[str, dict[str, Any]],
    images: dict[int, Path],
    model: str,
) -> None:
    # Replace higher evidence indices first so inserting multiple selected regions
    # cannot shift the still-to-be-processed indices within the same claim.
    ordered_pointers = sorted(pointers.items(), key=lambda item: item[1], reverse=True)
    for identifier, (result_index, claim_index, evidence_index) in ordered_pointers:
        claim = run["results"][result_index]["claims"][claim_index]
        old_evidence = claim["evidence"][evidence_index]
        selected = selections.get(identifier, [])
        new_evidence: list[dict[str, Any]] = []
        image_path = images[int(old_evidence["step_index"])]
        with Image.open(image_path) as image:
            width, height = image.size
        for candidate in selected:
            padded = pad_bbox(
                candidate.bbox,
                image_width=width,
                image_height=height,
                horizontal=8 if candidate.source == "tesseract_line" else 6,
                vertical=6,
            )
            if padded is None:
                continue
            detail = selection_details.get(identifier, {})
            new_evidence.append(
                {
                    **old_evidence,
                    "bbox": list(padded),
                    "visible_observation": detail.get("rationale") or old_evidence.get("visible_observation"),
                    "bbox_metadata": {
                        "image_path": str(image_path),
                        "image_width": width,
                        "image_height": height,
                        "coordinate_space": "image_pixels",
                        "source": "gemini_visual_grounding_omniparser_candidate_marks",
                        "candidate_id": candidate.candidate_id,
                        "candidate_source": candidate.source,
                        "candidate_confidence": candidate.confidence,
                        "candidate_text": candidate.text or None,
                        "raw_candidate_bbox": list(candidate.bbox),
                        "role": "SUPPORTING",
                        "localizability": "LOCAL_REGION",
                        "description": detail.get("rationale") or old_evidence.get("visible_observation"),
                        "selection_model": model,
                        "selection_applicability": detail.get("applicability"),
                        "visual_self_check": detail.get("visual_self_check"),
                        "previous_bbox": old_evidence.get("bbox"),
                        "previous_bbox_metadata": old_evidence.get("bbox_metadata"),
                    },
                    "confidence": float(detail.get("confidence") or old_evidence.get("confidence") or 0.0),
                    "metadata": {
                        **(old_evidence.get("metadata") or {}),
                        "model_name": model,
                        "grounding_method": "omniparser_candidate_mark_selection",
                    },
                }
            )
        claim["evidence"][evidence_index : evidence_index + 1] = new_evidence

    for result in run.get("results", []):
        result["evidence"] = [
            evidence
            for claim in result.get("claims", [])
            for evidence in claim.get("evidence", [])
        ]


def summary(run: dict[str, Any], *, model: str, usage_records: list[dict[str, Any]]) -> dict[str, Any]:
    claims = [claim for result in run.get("results", []) for claim in result.get("claims", [])]
    evidence = [item for claim in claims for item in claim.get("evidence", [])]
    boxes = [item for item in evidence if isinstance(item.get("bbox"), list)]
    labels: dict[str, int] = defaultdict(int)
    for result in run.get("results", []):
        labels[str(result.get("final_label") or "UNKNOWN")] += 1
    cost = sum(float(record.get("estimated_cost_usd") or 0.0) for record in usage_records)
    created_at = utc_now()
    return {
        "schema_version": "gemini_grounded_bbox_run_set_v1",
        "run_id": "bbox_omniparser_candidate_marks_flow02_20260720",
        "created_at": created_at,
        "configuration": {
            "model": model,
            "requested_execution_mode": "candidate-mark-regrounding",
            "retriever": "preserved from source run",
            "top_k": None,
            "max_images_per_group": 2,
            "image_variant": "preferred-original",
            "claim_decomposition_policy": "provided/preserved",
            "aggregation": "preserved from source run",
            "grounding": "Screenshot-only OmniParser UI candidates plus original-resolution Tesseract lines; Gemini selects numbered marks and performs a visual crop self-check",
            "estimated_cost_usd": cost,
        },
        "fallback_flows": [],
        "totals": {
            "flows": 1,
            "requirements": len(run.get("results", [])),
            "claims": len(claims),
            "evidence_records": len(evidence),
            "bounding_boxes": len(boxes),
            "bbox_sources": {"gemini_visual_grounding_omniparser_candidate_marks": len(boxes)},
            "estimated_cost_usd": cost,
        },
        "flows": [
            {
                "flow_id": FLOW_ID,
                "execution_mode": "candidate-mark-regrounding",
                "requirements": len(run.get("results", [])),
                "claims": len(claims),
                "evidence_records": len(evidence),
                "bounding_boxes": len(boxes),
                "bbox_sources": {"gemini_visual_grounding_omniparser_candidate_marks": len(boxes)},
                "labels": dict(labels),
                "api_calls": len(usage_records),
                "fallbacks": 0,
                "prompt_version": "OMNIPARSER_CANDIDATE_MARK_GROUNDING_V1",
            }
        ],
    }


def main() -> None:
    args = parse_args()
    required_paths = [args.source_run]
    if args.detector_output is not None:
        required_paths.append(args.detector_output)
    else:
        required_paths.extend((args.omniparser_python, args.omniparser_root, args.omniparser_model))
    for required in required_paths:
        if not required.exists():
            raise FileNotFoundError(required)
    args.work_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    source_run = load_json(args.source_run)
    flow_id = str(source_run.get("flow_id") or FLOW_ID)
    run = deepcopy(source_run)
    tasks_by_step, pointers = collect_tasks(run)
    images = original_images(run)
    detector = load_json(args.detector_output) if args.detector_output is not None else run_omniparser(args, images)

    candidates_by_step: dict[int, list[CandidateRegion]] = {}
    marked_by_step: dict[int, Path] = {}
    for step_index, image_path in sorted(images.items()):
        detector_image = detector["images"][str(image_path.resolve())]
        candidates = build_candidates(
            image_path,
            detector_image,
            max_icons=args.max_icons,
            max_text=args.max_text,
        )
        candidates_by_step[step_index] = candidates
        marked_path = args.work_dir / f"step_{step_index:02d}_omniparser_marks.png"
        draw_candidates(image_path, candidates, marked_path)
        marked_by_step[step_index] = marked_path
    (args.work_dir / "candidates.json").write_text(
        json.dumps(
            {
                "schema_version": "omniparser_candidate_marks_v1",
                "flow_id": flow_id,
                "steps": {
                    str(step): [candidate.to_dict() for candidate in candidates]
                    for step, candidates in candidates_by_step.items()
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    if args.skip_gemini:
        print(f"Generated candidate marks under {args.work_dir}; Gemini calls skipped.")
        return

    usage_records: list[dict[str, Any]] = []
    selections: dict[str, list[CandidateRegion]] = {}
    details: dict[str, dict[str, Any]] = {}
    selection_checkpoint = args.work_dir / "selection_responses.json"
    raw_selections: dict[str, Any] = (
        load_json(selection_checkpoint) if selection_checkpoint.is_file() else {}
    )
    for step_index, tasks in sorted(tasks_by_step.items()):
        checkpoint = raw_selections.get(str(step_index))
        if isinstance(checkpoint, dict) and isinstance(checkpoint.get("response"), dict):
            parsed = checkpoint["response"]
            usage = checkpoint.get("usage") or {}
        else:
            parsed, usage = call_gemini(
                prompt=selection_prompt(step_index, tasks, candidates_by_step[step_index]),
                images=[images[step_index], marked_by_step[step_index]],
                model=args.model,
                context={
                    "flow_id": FLOW_ID,
                    "step_index": step_index,
                    "prompt_version": "OMNIPARSER_CANDIDATE_MARK_GROUNDING_V1",
                    "task_count": len(tasks),
                },
            )
            raw_selections[str(step_index)] = {"response": parsed, "usage": usage}
            selection_checkpoint.write_text(
                json.dumps(raw_selections, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        if usage:
            usage_records.append(usage)
        for item in parsed.get("selections", []):
            if not isinstance(item, dict):
                continue
            identifier = str(item.get("task_id") or "")
            if identifier not in pointers:
                continue
            selected = resolve_candidate_ids(item.get("candidate_ids") or [], candidates_by_step[step_index])
            selections[identifier] = selected
            details[identifier] = item

    contact_sheets: dict[int, Path] = {}
    for step_index, tasks in sorted(tasks_by_step.items()):
        path = args.work_dir / f"step_{step_index:02d}_selection_check.png"
        render_contact_sheet(images[step_index], tasks, selections, path)
        contact_sheets[step_index] = path

    all_tasks = [task for step in sorted(tasks_by_step) for task in tasks_by_step[step]]
    current_ids = {
        identifier: [candidate.candidate_id for candidate in selected]
        for identifier, selected in selections.items()
    }
    validation_images = [
        path
        for step_index in sorted(tasks_by_step)
        for path in (marked_by_step[step_index], contact_sheets[step_index])
    ]
    validation_checkpoint = args.work_dir / "validation_response.json"
    saved_validation = load_json(validation_checkpoint) if validation_checkpoint.is_file() else {}
    if isinstance(saved_validation.get("response"), dict):
        validation = saved_validation["response"]
        usage = saved_validation.get("usage") or {}
    else:
        validation, usage = call_gemini(
            prompt=validation_prompt(all_tasks, current_ids, sorted(tasks_by_step)),
            images=validation_images,
            model=args.model,
            context={
                "flow_id": FLOW_ID,
                "prompt_version": "OMNIPARSER_CANDIDATE_MARK_VISUAL_CHECK_V1",
                "task_count": len(all_tasks),
            },
        )
        validation_checkpoint.write_text(
            json.dumps({"response": validation, "usage": usage}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    if usage:
        usage_records.append(usage)
    task_step = {task["task_id"]: step for step, tasks in tasks_by_step.items() for task in tasks}
    for item in validation.get("validations", []):
        if not isinstance(item, dict):
            continue
        identifier = str(item.get("task_id") or "")
        if identifier not in task_step:
            continue
        details.setdefault(identifier, {})["visual_self_check"] = item
        if item.get("valid") is False:
            step_index = task_step[identifier]
            selections[identifier] = resolve_candidate_ids(
                item.get("replacement_candidate_ids") or [],
                candidates_by_step[step_index],
            )

    replace_evidence(run, pointers, selections, details, images, args.model)
    run["metadata"] = {
        **(run.get("metadata") or {}),
        "source_run": str(args.source_run),
        "grounding_method": "omniparser_candidate_mark_selection",
        "grounding_model": args.model,
        "created_at": utc_now(),
    }
    output_run = args.output_dir / f"{FLOW_ID}.json"
    output_run.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
    run_summary = summary(run, model=args.model, usage_records=usage_records)
    actual_cost = float(run_summary["totals"].get("estimated_cost_usd") or 0.0)
    if actual_cost > args.cost_ceiling_usd:
        raise RuntimeError(
            f"Pilot cost ${actual_cost:.4f} exceeded the configured ceiling ${args.cost_ceiling_usd:.4f}."
        )
    (args.output_dir / "summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"Completed flow 02 candidate-mark grounding: {run_summary['totals']['bounding_boxes']} boxes, "
        f"{len(usage_records)} Gemini calls, estimated ${actual_cost:.4f}."
    )


if __name__ == "__main__":
    main()
