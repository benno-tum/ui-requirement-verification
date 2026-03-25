from __future__ import annotations

from pathlib import Path
import argparse
import json

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


load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[3]
DEFAULT_INPUT_DIR = BASE_DIR / "data" / "processed" / "flows" / "mind2web"


def process_flow(
    flow_dir: Path,
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

    out_prompt = flow_dir / "gemini_prompt.txt"
    out_prompt.write_text(prompt, encoding="utf-8")

    selection_info = {
        "selected_steps": selected_steps,
        "selected_files": [p.name for p in selected_paths],
        "image_max_side": image_max_side,
        "model": model_name,
    }
    (flow_dir / "gemini_selection.json").write_text(
        json.dumps(selection_info, indent=2),
        encoding="utf-8",
    )

    if dry_run:
        print(f"[DRY RUN] {flow_dir.name}")
        print("Selected steps:", selected_steps)
        return

    image_bytes_list = [downscale_to_png_bytes(p, max_side=image_max_side) for p in selected_paths]
    raw_text = run_gemini(prompt, image_bytes_list, model_name=model_name)

    (flow_dir / "requirements_gemini_raw.txt").write_text(raw_text, encoding="utf-8")

    parsed = parse_json_response(raw_text)
    (flow_dir / "requirements_gemini.json").write_text(
        json.dumps(parsed, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"[OK] {flow_dir.name} -> requirements_gemini.json")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
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
            steps_arg=args.steps,
            max_images=args.max_images,
            image_max_side=args.image_max_side,
            dry_run=args.dry_run,
            model_name=args.model,
        )


if __name__ == "__main__":
    main()
