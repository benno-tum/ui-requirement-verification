from __future__ import annotations

from pathlib import Path
import argparse
import json
from typing import Any

from dotenv import load_dotenv

from ui_verifier.common.flow_utils import (
    find_flow_dirs,
    find_step_images,
    parse_step_number,
    select_images,
)
from ui_verifier.common.image_utils import downscale_to_png_bytes
from ui_verifier.common.json_utils import load_json, parse_json_response
from ui_verifier.requirements.prompting import build_prompt
from ui_verifier.requirements.gemini_client import run_gemini
from ui_verifier.requirements.schemas import (
    CandidateRequirement,
    CandidateRequirementFile,
    RequirementScope,
)


load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[3]
DEFAULT_INPUT_DIR = BASE_DIR / "data" / "processed" / "flows" / "mind2web"
DEFAULT_OUTPUT_ROOT = BASE_DIR / "data" / "generated" / "candidate_requirements"


def confidence_label_to_float(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        value = float(value)
        if 0.0 <= value <= 1.0:
            return value
        return None

    if not isinstance(value, str):
        return None

    normalized = value.strip().lower()
    mapping = {
        "high": 0.9,
        "medium": 0.6,
        "low": 0.3,
    }
    return mapping.get(normalized)


def infer_scope(step_indices: list[int]) -> RequirementScope:
    if len(step_indices) <= 1:
        return RequirementScope.SINGLE_SCREEN
    return RequirementScope.MULTI_SCREEN


def normalize_model_requirements(
    parsed: dict[str, Any],
    flow_id: str,
    model_name: str,
    prompt_path: Path,
    allowed_steps: list[int],
) -> CandidateRequirementFile:
    raw_requirements = parsed.get("requirements", [])
    if not isinstance(raw_requirements, list):
        raise ValueError("Parsed model output must contain a list under 'requirements'.")

    requirements: list[CandidateRequirement] = []

    for i, item in enumerate(raw_requirements, start=1):
        if not isinstance(item, dict):
            continue

        req_id = str(item.get("id") or f"REQ-{i:02d}").strip()
        text = str(item.get("text") or "").strip()
        if not text:
            continue

        evidence_steps_raw = item.get("evidence_steps", [])
        if not isinstance(evidence_steps_raw, list):
            evidence_steps_raw = []

        allowed_step_set = set(allowed_steps)

        step_indices = []
        for step in evidence_steps_raw:
            try:
                step_int = int(step)
            except (TypeError, ValueError):
                continue
            if step_int in allowed_step_set:
                step_indices.append(step_int)

        step_indices = sorted(set(step_indices))

        req_type = item.get("type")
        tags = [str(req_type).strip()] if isinstance(req_type, str) and str(req_type).strip() else []

        confidence = confidence_label_to_float(item.get("confidence"))

        requirement = CandidateRequirement(
            requirement_id=req_id,
            flow_id=flow_id,
            text=text,
            scope=infer_scope(step_indices),
            tags=tags,
            step_indices=step_indices,
            generation_model=model_name,
            generation_prompt_path=str(prompt_path),
            confidence=confidence,
        )
        requirements.append(requirement)

    return CandidateRequirementFile(
        dataset="mind2web",
        flow_id=flow_id,
        requirements=requirements,
    )


def process_flow(
    flow_dir: Path,
    output_root: Path,
    steps_arg: str | None,
    max_images: int | None,
    image_max_side: int,
    dry_run: bool,
    model_name: str,
) -> None:
    task_path = flow_dir / "task.json"
    if not task_path.exists():
        print(f"[SKIP] No task.json in {flow_dir}")
        return

    task = load_json(task_path)
    step_paths = find_step_images(flow_dir)
    if not step_paths:
        print(f"[SKIP] No step images in {flow_dir}")
        return

    selected_paths = select_images(step_paths, steps_arg=steps_arg, max_images=max_images)
    selected_steps = [parse_step_number(p) for p in selected_paths]

    prompt = build_prompt(task, selected_steps)

    out_dir = output_root / flow_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)

    out_prompt = out_dir / "gemini_prompt.txt"
    out_prompt.write_text(prompt, encoding="utf-8")

    selection_info = {
        "flow_id": flow_dir.name,
        "selected_steps": selected_steps,
        "selected_files": [p.name for p in selected_paths],
        "image_max_side": image_max_side,
        "model": model_name,
    }
    (out_dir / "gemini_selection.json").write_text(
        json.dumps(selection_info, indent=2),
        encoding="utf-8",
    )

    if dry_run:
        print(f"[DRY RUN] {flow_dir.name}")
        print("Selected steps:", selected_steps)
        print("Output dir:", out_dir)
        return

    image_bytes_list = [downscale_to_png_bytes(p, max_side=image_max_side) for p in selected_paths]
    raw_text = run_gemini(prompt, image_bytes_list, model_name=model_name)

    (out_dir / "requirements_gemini_raw.txt").write_text(raw_text, encoding="utf-8")

    parsed = parse_json_response(raw_text)
    (out_dir / "requirements_gemini.json").write_text(
        json.dumps(parsed, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    candidate_file = normalize_model_requirements(
        parsed=parsed,
        flow_id=flow_dir.name,
        model_name=model_name,
        prompt_path=out_prompt,
        allowed_steps=selected_steps,
    )
    candidate_file.save(out_dir / "candidate_requirements.json")

    print(f"[OK] {flow_dir.name} -> {out_dir / 'candidate_requirements.json'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--flow-dir", type=Path, default=None, help="Process exactly one flow folder")
    parser.add_argument("--max-flows", type=int, default=3)
    parser.add_argument("--steps", type=str, default=None, help="Manual step selection, e.g. 1,4,7,10")
    parser.add_argument("--max-images", type=int, default=4, help="Used if --steps is not given")
    parser.add_argument("--image-max-side", type=int, default=1024)
    parser.add_argument("--model", type=str, default="gemini-2.5-flash")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.flow_dir is not None:
        flow_dirs = [args.flow_dir]
    else:
        flow_dirs = find_flow_dirs(args.input_dir)[: args.max_flows]

    if not flow_dirs:
        print("No flow directories found.")
        return

    for flow_dir in flow_dirs:
        process_flow(
            flow_dir=flow_dir,
            output_root=args.output_root,
            steps_arg=args.steps,
            max_images=args.max_images,
            image_max_side=args.image_max_side,
            dry_run=args.dry_run,
            model_name=args.model,
        )


if __name__ == "__main__":
    main()
