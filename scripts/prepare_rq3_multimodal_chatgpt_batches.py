from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
from typing import Any

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT = (
    BASE_DIR
    / "data/annotations/evaluation_audits/rq3_final_20260802"
    / "rq3_author_error_audit_form.json"
)
DEFAULT_OUTPUT = (
    BASE_DIR
    / "outputs/019fbfa1-94d4-7bb1-9a8a-81dd427302cf"
    / "rq3_chatgpt_multimodal_batches_20260802"
)

LABELS = ["FULFILLED", "PARTIALLY_FULFILLED", "NOT_FULFILLED", "ABSTAIN"]
PRIMARY_CATEGORIES = {
    "UNSAFE_OVER_FULFILLMENT": (
        "Prediction is FULFILLED although a core obligation is partial, absent, "
        "contradicted, hidden, or outside the screenshots."
    ),
    "UNSUPPORTED_CONCRETE_NEGATIVE": (
        "Prediction is NOT_FULFILLED without a visible contradiction; missing "
        "evidence alone requires ABSTAIN."
    ),
    "EXCESSIVE_ABSTENTION": (
        "The supplied screenshots contain decisive visible evidence for a "
        "non-ABSTAIN decision, but the prediction is ABSTAIN."
    ),
    "EVIDENCE_SELECTION_MISS": (
        "Decisive evidence exists in the complete flow but is absent from the "
        "screenshots supplied in this condition."
    ),
    "EVIDENCE_INTERPRETATION_ERROR": (
        "Decisive evidence is supplied, but it is misread or not combined correctly."
    ),
    "LABEL_BOUNDARY_DISAGREEMENT": (
        "Visible support is genuinely near an operational boundary between the "
        "four labels and no more specific evidence failure explains the disagreement."
    ),
    "GOLD_REVIEW_CANDIDATE": (
        "Direct visual inspection indicates that the frozen label or reviewed "
        "evidence may itself require an author amendment."
    ),
    "APPROPRIATE_ABSTENTION": (
        "Prediction and reference both ABSTAIN because the screenshots do not "
        "establish a defensible concrete outcome. This is a non-error outcome."
    ),
    "TRACEABILITY_FAILURE": (
        "The non-ABSTAIN requirement label is correct, but the cited evidence does "
        "not visually support it or does not overlap the reviewed decisive evidence."
    ),
    "PREDICTION_INSTABILITY": (
        "The current prediction is correct and is not a traceability failure, but "
        "repeated runs disagree on the same stored input."
    ),
}
REQUIREMENT_TAGS = {
    "UNIVERSAL_OR_COMPLETENESS": "all, every, any, complete, comprehensive, or equivalent scope",
    "COMPARATIVE_OR_DISTINCT": "comparison, differentiation, ranking, or alternatives",
    "HIDDEN_BACKEND_OR_EXTERNAL": "backend truth, enforcement, delivery, availability, validity, external effect, or security",
    "PERSISTENCE_OR_CROSS_STEP": "state must persist across pages, sessions, or later visits",
    "LATE_RESULT_OR_CART_STATE": "result, review, cart, checkout, confirmation, or final state occurs late",
    "MULTI_SCREEN_COMPOSITION": "decision requires combining multiple screens",
    "NEGATION_OR_CONTRASTIVE": "requirement is negated or deliberately contrastive",
    "LABEL_SCHEMA_AMBIGUITY": "wording does not map cleanly to one label",
    "ORDINARY_LOCAL_UI": "none of the preceding requirement patterns applies",
}
EVIDENCE_TAGS = {
    "DECISIVE_STEP_SELECTED": "the supplied subset contains the decisive visible step",
    "DECISIVE_STEP_NOT_SELECTED": "the supplied subset omits a decisive visible step",
    "ONLY_ENTRY_POINT_VISIBLE": "only a control or entry point is visible, not its outcome",
    "ACTION_WITHOUT_RESULT": "an action is visible but its result is not",
    "PARTIAL_CLAIM_COVERAGE": "visible evidence covers only part of the obligation",
    "NO_OBSERVABLE_PROXY": "the requested property has no defensible visible proxy",
    "LATE_STEP": "decisive evidence occurs late in the flow",
    "CROSS_STEP_STATE": "evidence depends on state across steps",
    "EVIDENCE_CORRECT_BUT_RATIONALE_WRONG": "cited evidence is suitable but the stated reasoning is materially wrong",
    "LABEL_CORRECT_BUT_TRACEABILITY_WRONG": "label is correct but cited evidence is not",
    "RUN_INSTABILITY": "repeated labels differ; use as a tag when a more specific current-run outcome remains primary",
}

# The larger flows benefit from a genuinely evidence-first first message. The
# remaining flows fit a single request without making the output unwieldy.
TWO_PHASE_FLOWS = {
    "01_sixflags_a52fcf7a-50aa-4256-8796-654b3dc3adac",
    "03_mbta_c094948f-afc6-415c-968a-9e105e2db118",
    "04_underarmour_18fc60d7-aa69-4c07-9bf1-64543eae52c9",
    "10_sixflags_ee1e95ab-4c5d-44c6-b302-783fd13a471e",
}

# Starts with two small calibration flows, keeps the first upload wave below
# the documented 80-files-per-three-hours upper bound, and leaves the three
# largest two-phase flows for a second wave.
RECOMMENDED_RUN_ORDER = [2, 8, 7, 9, 12, 13, 6, 5, 11, 4, 1, 3, 10]
WAVE_2_START = 11
GENERIC_CHATGPT_MESSAGE = (
    "Read 00_INSTRUCTIONS.txt first and follow it exactly. Use every attached "
    "PNG and JSON file, perform the requested visual review, and return the "
    "requested downloadable JSON result plus the short validation summary."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare flow-wise ChatGPT multimodal review ZIPs for the RQ3 audit."
    )
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace an existing generated output directory.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("items"), list):
        raise ValueError(f"expected audit object with items: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def step_from_path(path: str) -> int:
    match = re.search(r"step_(\d+)\.png$", path)
    if not match:
        raise ValueError(f"cannot parse step index: {path}")
    return int(match.group(1))


def flow_number(flow_id: str) -> int:
    return int(flow_id.split("_", 1)[0])


def flow_short_name(flow_id: str) -> str:
    parts = flow_id.split("_")
    return parts[1] if len(parts) > 1 else flow_id


def choose_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def prepare_labeled_screenshot(source: Path, destination: Path, flow_id: str, step: int) -> dict[str, Any]:
    with Image.open(source) as opened:
        image = opened.convert("RGB")
    header_height = max(72, round(image.width * 0.065))
    canvas = Image.new("RGB", (image.width, image.height + header_height), "white")
    canvas.paste(image, (0, header_height))
    draw = ImageDraw.Draw(canvas)
    font = choose_font(max(24, round(image.width * 0.027)))
    label = (
        f"FLOW {flow_number(flow_id):02d} {flow_short_name(flow_id).upper()}  |  "
        f"STEP {step:02d}  |  ORIGINAL SCREENSHOT BELOW"
    )
    bbox = draw.textbbox((0, 0), label, font=font)
    text_height = bbox[3] - bbox[1]
    draw.text((24, (header_height - text_height) // 2 - bbox[1]), label, fill="black", font=font)
    draw.rectangle((0, header_height - 5, image.width, header_height - 1), fill=(0, 101, 189))
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="PNG", compress_level=6)
    return {
        "step_index": step,
        "prepared_filename": destination.name,
        "source_path": str(source.relative_to(BASE_DIR)),
        "source_sha256": sha256(source),
        "prepared_sha256": sha256(destination),
        "source_width": image.width,
        "source_height": image.height,
        "prepared_width": canvas.width,
        "prepared_height": canvas.height,
        "prepared_bytes": destination.stat().st_size,
    }


def requirement_record(rows: list[dict[str, Any]]) -> dict[str, Any]:
    first = rows[0]
    stable_fields = [
        "requirement_text",
        "gold_label",
        "gold_evidence_steps",
        "gold_rationale",
        "full_flow_step_indices",
    ]
    for field in stable_fields:
        values = {json.dumps(row.get(field), sort_keys=True) for row in rows}
        if len(values) != 1:
            raise ValueError(
                f"inconsistent {field} for {first['flow_id']} {first['requirement_id']}"
            )
    return {
        "requirement_id": first["requirement_id"],
        "requirement_text": first["requirement_text"],
    }


def reference_record(rows: list[dict[str, Any]]) -> dict[str, Any]:
    first = rows[0]
    return {
        "requirement_id": first["requirement_id"],
        "gold_label": first["gold_label"],
        "gold_evidence_steps": first["gold_evidence_steps"],
        "gold_rationale": first["gold_rationale"],
    }


def condition_record(item: dict[str, Any]) -> dict[str, Any]:
    fields = [
        "audit_item_id",
        "condition_code",
        "claim_policy",
        "screenshot_policy",
        "requirement_id",
        "predicted_label",
        "repetition_labels",
        "eligibility_reasons",
        "predicted_evidence_steps",
        "supplied_step_indices",
        "missing_gold_evidence_steps",
        "prediction_rationale",
        "prediction_uncertainty_reasons",
    ]
    return {field: item.get(field) for field in fields}


def taxonomy() -> dict[str, Any]:
    return {
        "labels": LABELS,
        "primary_categories": PRIMARY_CATEGORIES,
        "requirement_tags": REQUIREMENT_TAGS,
        "evidence_tags": EVIDENCE_TAGS,
        "precedence_rules": [
            "Use GOLD_REVIEW_CANDIDATE only when direct visual inspection makes the stored reference genuinely questionable; never change gold automatically.",
            "Gold ABSTAIN plus predicted ABSTAIN is APPROPRIATE_ABSTENTION, not TRACEABILITY_FAILURE merely because evidence-step overlap is zero.",
            "For a current label error, assign the most specific present-run cause. If repetitions differ, add RUN_INSTABILITY instead of replacing that cause.",
            "Use TRACEABILITY_FAILURE only for a current correct non-ABSTAIN label whose cited evidence is visually wrong or does not support the decision.",
            "Use PREDICTION_INSTABILITY only when the current label is correct, traceability is not the primary failure, and repetitions disagree.",
            "Missing decisive evidence from a top-k subset is EVIDENCE_SELECTION_MISS; supplied but misread decisive evidence is EVIDENCE_INTERPRETATION_ERROR.",
            "Use LABEL_BOUNDARY_DISAGREEMENT only after excluding a clearer selection, interpretation, unsupported-negative, over-fulfillment, or abstention cause.",
        ],
    }


def result_schema(batch_id: str, flow_id: str, requirement_count: int, row_count: int, steps: list[int]) -> dict[str, Any]:
    return {
        "schema_version": "rq3_multimodal_llm_visual_review_v1",
        "batch_id": batch_id,
        "flow_id": flow_id,
        "review_surface": "ChatGPT web",
        "requested_model": "GPT-5.6 Sol High",
        "visual_inspection_attestation": {
            "inspected_all_attached_screenshots": True,
            "expected_step_indices": steps,
            "inspected_step_indices": steps,
            "unreadable_or_uninspected_steps": [],
            "notes": "",
        },
        "requirement_assessments": [
            {
                "requirement_id": "exact input ID",
                "visible_observations": "one or two sentences grounded only in attached screenshots",
                "visually_supported_label": "one of the four labels",
                "relevant_steps": [1],
                "unobservable_or_missing_aspects": ["short phrase"],
                "confidence": 0.0,
            }
        ],
        "row_reviews": [
            {
                "audit_item_id": "exact input ID",
                "decisive_evidence_supplied": True,
                "primary_category": "one allowed primary category",
                "requirement_tags": ["one or more allowed requirement tags"],
                "evidence_tags": ["one or more allowed evidence tags"],
                "visible_evidence_rationale": "one concise sentence citing visible step numbers",
                "gold_review_candidate": False,
                "confidence": 0.0,
                "review_status": "LLM_VISUAL_DRAFT_COMPLETE",
            }
        ],
        "validation": {
            "expected_requirement_count": requirement_count,
            "actual_requirement_count": requirement_count,
            "expected_row_count": row_count,
            "actual_row_count": row_count,
            "all_input_requirement_ids_present_once": True,
            "all_input_audit_item_ids_present_once": True,
            "allowed_values_only": True,
            "nonempty_visual_rationales": True,
        },
    }


def common_quality_rules(batch_id: str, requirement_count: int, row_count: int) -> str:
    return f"""Quality rules:
- You are producing an LLM-assisted visual draft, not claiming to be the thesis author.
- Inspect every attached PNG directly. Do not treat screenshot paths, gold rationales, prediction rationales, OCR, or filenames as substitutes for pixels.
- The blue header added above each screenshot identifies its flow and step; screenshot content below the line is unchanged.
- Never infer backend execution, persistence beyond the shown flow, external delivery, completeness beyond the visible list, or a successful result merely from an entry control.
- Judge each condition using exactly its supplied_step_indices. The complete flow is available only to distinguish selection misses from interpretation failures.
- First form one visual assessment per requirement; only then compare gold and predictions and assign row categories.
- Gold and prediction fields are evidence to classify disagreement, not authority over what the screenshots show.
- Return exactly {requirement_count} requirement assessments and exactly {row_count} row reviews for batch {batch_id}.
- Preserve every input ID exactly once and preserve input order.
- Use only taxonomy values supplied in the packet.
- A rationale must name the decisive visible step(s) and what is or is not visible there.
- If a screenshot is unreadable, record the step in unreadable_or_uninspected_steps and lower confidence; never pretend it was inspected.
- If page text is too small at the default view, use Python/data analysis to create lossless crops from the attached full-resolution PNG and inspect those crops visually. Do not rely on OCR alone.
- Do not set review_status to COMPLETE. Use LLM_VISUAL_DRAFT_COMPLETE so the author can confirm it later.
- Apart from lossless zoom crops, use Python/data analysis only to parse and validate JSON and to write the result file; visual judgments must come from direct image inspection.
"""


def single_turn_prompt(batch_id: str, flow_id: str, packet_name: str, requirement_count: int, row_count: int, result_name: str) -> str:
    return f"""You are conducting a structured multimodal RQ3 error-analysis draft for a bachelor thesis.

I selected GPT-5.6 Sol with High reasoning in the ChatGPT web interface. The attached files contain:
1. every ordered screenshot for flow {flow_id}; and
2. {packet_name}, containing {requirement_count} distinct requirements, {row_count} condition rows, the frozen references, and the permitted taxonomy.

{common_quality_rules(batch_id, requirement_count, row_count)}
Workflow:
1. Load the packet and verify batch_id and flow_id.
2. Inspect all screenshots in step order.
3. Make an evidence-first visual assessment for every requirement before assigning any condition-row category.
4. Compare each condition's exact supplied screenshot subset, prediction, reference, and repetitions.
5. Validate the result counts and allowed values programmatically.
6. Write the final JSON object to a downloadable UTF-8 file named {result_name}. Do not place the JSON inside Markdown unless file creation is unavailable.

In the chat response, provide only the download link plus a short validation summary: inspected steps, requirement count, row count, number of unreadable steps, low-confidence row count, and gold-review-candidate count.
"""


def phase1_prompt(batch_id: str, flow_id: str, requirements: list[dict[str, Any]], memo_name: str) -> str:
    requirement_count = len(requirements)
    requirements_json = json.dumps(requirements, indent=2, ensure_ascii=False)
    return f"""This is phase 1 of a two-phase, evidence-first multimodal RQ3 review for a bachelor thesis.

I selected GPT-5.6 Sol with High reasoning in the ChatGPT web interface. The attached files contain every ordered screenshot for flow {flow_id}. The {requirement_count} requirement texts are embedded below; this phase deliberately contains no gold labels or model predictions.

Inspect every PNG directly and in step order. The blue header identifies the flow and step; content below the line is unchanged. For each requirement, record only:
- what the screenshots visibly establish;
- the most defensible label among FULFILLED, PARTIALLY_FULFILLED, NOT_FULFILLED, and ABSTAIN;
- relevant step indices;
- obligations that remain unobservable or missing; and
- confidence from 0.0 to 1.0.

Do not infer backend behavior, persistence outside the shown flow, external effects, universal completeness beyond the visible list, or successful outcomes from entry controls. Do not ask for the predictions yet. If page text is too small, create lossless crops from the attached full-resolution PNG and inspect those crops visually; do not rely on OCR alone. If any image remains unreadable, say so explicitly.

Create a JSON object with schema_version rq3_visual_memo_v1, batch_id {batch_id}, flow_id {flow_id}, a visual_inspection_attestation, and exactly {requirement_count} requirement_assessments. Preserve requirement order and IDs. Validate the counts with Python/data analysis and write a downloadable UTF-8 file named {memo_name}. Also keep the memo available in this same conversation for phase 2.

Respond only with the download link and a short validation summary. Do not continue to phase 2 until I upload the second packet.

Requirements to assess:
```json
{requirements_json}
```
"""


def phase2_prompt(batch_id: str, flow_id: str, packet_name: str, requirement_count: int, row_count: int, result_name: str) -> str:
    return f"""This is phase 2 of the same RQ3 review. Continue in this conversation and use the visual memo you created in phase 1.

The newly attached {packet_name} contains the frozen reference information, {row_count} condition rows, and the allowed taxonomy for flow {flow_id}. Do not redo or silently change the phase-1 visual observations merely to match a gold label or model prediction.

{common_quality_rules(batch_id, requirement_count, row_count)}
For each condition row:
1. Decide whether that condition's supplied_step_indices contain the visually decisive evidence.
2. Assign exactly one allowed primary category using the supplied precedence rules.
3. Assign every applicable allowed requirement and evidence tag.
4. Write one concise rationale citing visible step numbers.
5. Mark gold_review_candidate only when the phase-1 visual assessment makes the stored reference genuinely questionable.
6. Record confidence from 0.0 to 1.0.

Combine the unchanged phase-1 requirement_assessments with the new row_reviews in the result schema. Validate all IDs, counts, enum values, and nonempty rationales programmatically. Write the final JSON object to a downloadable UTF-8 file named {result_name}. Do not place the JSON inside Markdown unless file creation is unavailable.

Respond only with the download link plus a short validation summary: inspected steps, requirement count, row count, unreadable steps, low-confidence row count, and gold-review-candidate count.
"""


def batch_readme(batch: dict[str, Any]) -> str:
    mode = batch["mode"]
    upload_instruction = (
        "Open a new ChatGPT conversation, manually select GPT-5.6 Sol and High, "
        "drag every file from `UPLOAD/` into the message, paste `PASTE_PROMPT.txt`, and send."
        if mode == "single_turn"
        else "Open a new ChatGPT conversation and manually select GPT-5.6 Sol and High. "
        "First drag every screenshot from `PHASE1_UPLOAD/`, paste `PASTE_PHASE1_PROMPT.txt` (which already contains the requirement texts), and send. "
        "After the visual memo completes, stay in the same conversation, attach the sole file from "
        "`PHASE2_UPLOAD/`, paste `PASTE_PHASE2_PROMPT.txt`, and send."
    )
    return f"""# {batch['batch_id']} — {batch['flow_id']}

Recommended mode: **{mode.replace('_', ' ')}**

- Requirements: {batch['requirements']}
- Condition rows: {batch['rows']}
- Screenshots: {batch['screenshots']}
- ChatGPT messages: {batch['messages']}
- File uploads: {batch['upload_files']}
- Recommended upload wave: {batch['wave']}

## Run

{upload_instruction}

For the easiest workflow, use this batch's matching folder under the master `READY_TO_UPLOAD/` directory. It already places the instructions, screenshots, and JSON needed for each message together.

Download the final `{batch['result_filename']}` and place it in the master `results_inbox/` directory without renaming it. Verify that ChatGPT reports the expected requirement and row counts. Stop and rerun the affected batch if it reports an unreadable screenshot, an incomplete output, or a fallback away from GPT-5.6 Sol High.
"""


def place_ready_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".png":
        destination.hardlink_to(source)
    else:
        shutil.copy2(source, destination)


def master_runbook(batch_rows: list[dict[str, Any]]) -> str:
    ordered = sorted(batch_rows, key=lambda value: value["run_order"])
    lines = [
        "# ChatGPT Web Runbook — Screenshot-Aware RQ3 Coding",
        "",
        "These packages create an LLM-assisted visual draft of the 653-row RQ3 audit. They do not overwrite the author-review fields.",
        "",
        "## Recommended procedure",
        "",
        "1. Use the folders in `READY_TO_UPLOAD/`; no ZIP extraction is required.",
        "2. Start a fresh ChatGPT conversation for that batch and manually choose **GPT-5.6 Sol — High**.",
        "3. Drag every file from the next ready folder into the message and paste the same one-line text from `00_GENERIC_CHATGPT_MESSAGE.txt`. Single-turn batches use one folder. Two-phase batches use their `a_phase1` and `b_phase2` folders consecutively in the same conversation.",
        "4. Download the final result JSON and put it in `results_inbox/` without changing its filename.",
        "5. Check the response summary against the expected counts in the table below. Stop if the interface reports a fallback model, missing images, truncation, or unreadable screenshots.",
        "6. Run the two calibration batches sequentially. Once their output is valid, running three or four independent batch conversations in parallel is reasonable. Parallelism saves wall-clock time, not allowance.",
        "",
        "## Upload waves",
        "",
        "The recommended order keeps each wave below the documented upper bound of 80 uploaded files per three hours. OpenAI may lower the limit at peak times, so pause if the interface rejects uploads.",
        "",
        "| Order | Batch | Flow | Mode | Screens | Requirements | Rows | Messages | Uploads | Wave |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in ordered:
        lines.append(
            f"| {row['run_order']} | {row['batch_id']} | {row['flow_short']} | "
            f"{row['mode']} | {row['screenshots']} | {row['requirements']} | "
            f"{row['rows']} | {row['messages']} | {row['ready_upload_files']} | {row['wave']} |"
        )
    wave_uploads: dict[int, int] = defaultdict(int)
    for row in ordered:
        wave_uploads[row["wave"]] += row["ready_upload_files"]
    lines.extend(
        [
            "",
            f"Wave 1 contains {wave_uploads[1]} uploads; wave 2 contains {wave_uploads[2]} uploads.",
            "",
            "## Why four batches use two phases",
            "",
            "Flows 01, 03, 04, and 10 have the largest combination of requirements and condition rows. Their first message contains only requirement wording and screenshots. Gold labels and predictions appear only in the second message, reducing anchoring and keeping the final output manageable. The other nine flows use one evidence-first prompt.",
            "",
            "## Taxonomy note",
            "",
            "The packets use the seven frozen error categories plus `APPROPRIATE_ABSTENTION`, `TRACEABILITY_FAILURE`, and `PREDICTION_INSTABILITY`. These added outcomes are necessary because the frozen queue contains correct abstentions, label-correct trace failures, and current-correct unstable rows. `APPROPRIATE_ABSTENTION` is a non-error and must be excluded from error-rate denominators.",
            "",
            "## After all results are downloaded",
            "",
            "Run:",
            "",
            "```bash",
            "python scripts/merge_rq3_multimodal_chatgpt_results.py \\",
            f"  --batches-dir {DEFAULT_OUTPUT.relative_to(BASE_DIR)} \\",
            f"  --results-dir {DEFAULT_OUTPUT.relative_to(BASE_DIR)}/results_inbox",
            "```",
            "",
            "The merger validates every ID and enum and writes a separate LLM-visual draft. It does not overwrite the canonical author audit.",
            "",
            "Current product references:",
            "- https://help.openai.com/en/articles/20001354-gpt-5-6-in-chatgpt",
            "- https://help.openai.com/en/articles/8555545-uploading-files-in-chatgpt",
            "- https://help.openai.com/en/articles/8400551-image-inputs-for-chatgpt-faq",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    audit_path = args.audit.resolve()
    out_dir = args.out_dir.resolve()
    if out_dir.exists():
        if not args.replace:
            raise SystemExit(f"output already exists; pass --replace: {out_dir}")
        if BASE_DIR not in out_dir.parents:
            raise SystemExit(f"refusing to replace output outside repository: {out_dir}")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    (out_dir / "results_inbox").mkdir()
    ready_root = out_dir / "READY_TO_UPLOAD"
    ready_root.mkdir()
    (ready_root / "00_GENERIC_CHATGPT_MESSAGE.txt").write_text(
        GENERIC_CHATGPT_MESSAGE + "\n", encoding="utf-8"
    )

    audit = load_json(audit_path)
    by_flow: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in audit["items"]:
        by_flow[str(item["flow_id"])].append(item)
    if len(by_flow) != 13:
        raise ValueError(f"expected 13 flows, found {len(by_flow)}")

    order_lookup = {flow_number_: order for order, flow_number_ in enumerate(RECOMMENDED_RUN_ORDER, 1)}
    batch_rows: list[dict[str, Any]] = []

    for flow_id, items in sorted(by_flow.items(), key=lambda pair: flow_number(pair[0])):
        number = flow_number(flow_id)
        batch_id = f"B{number:02d}"
        short = flow_short_name(flow_id)
        mode = "two_phase" if flow_id in TWO_PHASE_FLOWS else "single_turn"
        batch_dir = out_dir / f"{batch_id}_{short}"
        screenshot_dir = batch_dir / ("PHASE1_UPLOAD" if mode == "two_phase" else "UPLOAD")
        screenshot_dir.mkdir(parents=True)

        requirement_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in items:
            requirement_groups[str(item["requirement_id"])].append(item)
        requirements = [
            requirement_record(requirement_groups[key])
            for key in sorted(requirement_groups)
        ]
        references = [
            reference_record(requirement_groups[key])
            for key in sorted(requirement_groups)
        ]
        condition_rows = [condition_record(item) for item in items]

        screenshot_paths = sorted(
            {Path(path) for item in items for path in item["full_flow_screenshot_paths"]},
            key=lambda path: step_from_path(str(path)),
        )
        screenshots = []
        for source in screenshot_paths:
            absolute_source = source if source.is_absolute() else BASE_DIR / source
            if not absolute_source.is_file():
                raise FileNotFoundError(absolute_source)
            step = step_from_path(str(source))
            destination = screenshot_dir / f"step_{step:02d}.png"
            screenshot = prepare_labeled_screenshot(absolute_source, destination, flow_id, step)
            if screenshot["prepared_bytes"] > 20 * 1024 * 1024:
                raise ValueError(f"prepared image exceeds 20 MB: {destination}")
            screenshots.append(screenshot)

        steps = [value["step_index"] for value in screenshots]
        result_name = f"RESULT_{batch_id}_{short}.json"
        schema = result_schema(batch_id, flow_id, len(requirements), len(items), steps)
        write_json(batch_dir / "EXPECTED_RESULT_SCHEMA.json", schema)
        write_json(batch_dir / "SCREENSHOT_MANIFEST.json", screenshots)

        packet_base = {
            "schema_version": "rq3_chatgpt_visual_batch_v1",
            "batch_id": batch_id,
            "flow_id": flow_id,
            "screenshot_files": [
                {"step_index": value["step_index"], "filename": value["prepared_filename"]}
                for value in screenshots
            ],
            "requirements": requirements,
        }
        if mode == "single_turn":
            packet_name = f"{batch_id}_single_turn_packet.json"
            packet = {
                **packet_base,
                "reference_by_requirement": references,
                "condition_rows": condition_rows,
                "taxonomy": taxonomy(),
                "expected_result_schema": schema,
            }
            write_json(screenshot_dir / packet_name, packet)
            prompt = single_turn_prompt(
                batch_id, flow_id, packet_name, len(requirements), len(items), result_name
            )
            (batch_dir / "PASTE_PROMPT.txt").write_text(prompt, encoding="utf-8")
            messages = 1
            upload_files = len(screenshots) + 1
        else:
            write_json(batch_dir / "PHASE1_REQUIREMENTS_REFERENCE.json", packet_base)
            phase2_dir = batch_dir / "PHASE2_UPLOAD"
            phase2_dir.mkdir()
            phase2_name = f"{batch_id}_condition_rows.json"
            write_json(
                phase2_dir / phase2_name,
                {
                    "schema_version": "rq3_chatgpt_visual_phase2_v1",
                    "batch_id": batch_id,
                    "flow_id": flow_id,
                    "reference_by_requirement": references,
                    "condition_rows": condition_rows,
                    "taxonomy": taxonomy(),
                    "expected_result_schema": schema,
                },
            )
            memo_name = f"VISUAL_MEMO_{batch_id}_{short}.json"
            (batch_dir / "PASTE_PHASE1_PROMPT.txt").write_text(
                phase1_prompt(batch_id, flow_id, requirements, memo_name),
                encoding="utf-8",
            )
            (batch_dir / "PASTE_PHASE2_PROMPT.txt").write_text(
                phase2_prompt(
                    batch_id,
                    flow_id,
                    phase2_name,
                    len(requirements),
                    len(items),
                    result_name,
                ),
                encoding="utf-8",
            )
            messages = 2
            upload_files = len(screenshots) + 1

        run_order = order_lookup[number]
        wave = 1 if run_order < WAVE_2_START else 2
        ready_prefix = f"{run_order:02d}_{batch_id}_{short}"
        if mode == "single_turn":
            ready_dir = ready_root / ready_prefix
            for source in sorted((batch_dir / "UPLOAD").iterdir()):
                place_ready_file(source, ready_dir / source.name)
            place_ready_file(
                batch_dir / "PASTE_PROMPT.txt",
                ready_dir / "00_INSTRUCTIONS.txt",
            )
            ready_folders = [str(ready_dir.relative_to(out_dir))]
            ready_upload_files = upload_files + 1
        else:
            phase1_ready = ready_root / f"{ready_prefix}_a_phase1"
            phase2_ready = ready_root / f"{ready_prefix}_b_phase2"
            for source in sorted((batch_dir / "PHASE1_UPLOAD").iterdir()):
                place_ready_file(source, phase1_ready / source.name)
            place_ready_file(
                batch_dir / "PASTE_PHASE1_PROMPT.txt",
                phase1_ready / "00_INSTRUCTIONS.txt",
            )
            for source in sorted((batch_dir / "PHASE2_UPLOAD").iterdir()):
                place_ready_file(source, phase2_ready / source.name)
            place_ready_file(
                batch_dir / "PASTE_PHASE2_PROMPT.txt",
                phase2_ready / "00_INSTRUCTIONS.txt",
            )
            ready_folders = [
                str(phase1_ready.relative_to(out_dir)),
                str(phase2_ready.relative_to(out_dir)),
            ]
            ready_upload_files = upload_files + 2
        batch = {
            "batch_id": batch_id,
            "flow_id": flow_id,
            "flow_short": short,
            "mode": mode,
            "requirements": len(requirements),
            "rows": len(items),
            "screenshots": len(screenshots),
            "messages": messages,
            "upload_files": upload_files,
            "ready_upload_files": ready_upload_files,
            "ready_folders": ready_folders,
            "run_order": run_order,
            "wave": wave,
            "result_filename": result_name,
        }
        (batch_dir / "README.md").write_text(batch_readme(batch), encoding="utf-8")
        batch_rows.append(batch)

    batch_rows.sort(key=lambda row: row["run_order"])
    write_json(
        out_dir / "batch_manifest.json",
        {
            "schema_version": "rq3_chatgpt_batch_manifest_v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_audit": str(audit_path.relative_to(BASE_DIR)),
            "batch_count": len(batch_rows),
            "total_requirements": sum(row["requirements"] for row in batch_rows),
            "total_condition_rows": sum(row["rows"] for row in batch_rows),
            "total_screenshots": sum(row["screenshots"] for row in batch_rows),
            "estimated_chatgpt_messages": sum(row["messages"] for row in batch_rows),
            "total_upload_files": sum(row["upload_files"] for row in batch_rows),
            "batches": batch_rows,
        },
    )
    with (out_dir / "batch_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(batch_rows[0]))
        writer.writeheader()
        writer.writerows(batch_rows)
    (out_dir / "CHATGPT_WEB_RUNBOOK.md").write_text(master_runbook(batch_rows), encoding="utf-8")
    (out_dir / "results_inbox" / "README.md").write_text(
        "Place the 13 downloaded RESULT_Bxx_*.json files here. Keep their generated filenames.\n",
        encoding="utf-8",
    )

    print(
        f"batches={len(batch_rows)} requirements={sum(row['requirements'] for row in batch_rows)} "
        f"rows={sum(row['rows'] for row in batch_rows)} screenshots={sum(row['screenshots'] for row in batch_rows)} "
        f"messages={sum(row['messages'] for row in batch_rows)} out={out_dir}"
    )


if __name__ == "__main__":
    main()
