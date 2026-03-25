from pathlib import Path
from PIL import Image
import argparse
import io
import json
import os
import re
from typing import List


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_FLOW_ROOT = BASE_DIR / "data" / "processed" / "flows" / "mind2web"
DEFAULT_OUT_ROOT = BASE_DIR / "data" / "generated" / "screen_descriptions"


def parse_step_number(path: Path) -> int:
    m = re.search(r"step_(\d+)\.png$", path.name)
    if not m:
        raise ValueError(f"Cannot parse step number from {path.name}")
    return int(m.group(1))


def find_step_images(flow_dir: Path) -> List[Path]:
    return sorted(flow_dir.glob("step_*.png"))


def choose_evenly_spaced(items: List[Path], k: int) -> List[Path]:
    if not items:
        return []
    if k >= len(items):
        return items
    if k <= 1:
        return [items[0]]

    idxs = []
    for i in range(k):
        pos = round(i * (len(items) - 1) / (k - 1))
        idxs.append(pos)

    idxs = sorted(set(idxs))
    return [items[i] for i in idxs]


def select_images(step_paths: List[Path], steps_arg: str | None, max_images: int | None) -> List[Path]:
    if steps_arg:
        wanted = []
        for part in steps_arg.split(","):
            part = part.strip()
            if part:
                wanted.append(int(part))

        by_num = {parse_step_number(p): p for p in step_paths}
        selected = [by_num[s] for s in wanted if s in by_num]
        return selected

    if max_images is not None:
        return choose_evenly_spaced(step_paths, max_images)

    return step_paths


def downscale_to_png_bytes(path: Path, max_side: int) -> bytes:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    longest = max(w, h)

    if longest > max_side:
        scale = max_side / float(longest)
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        img = img.resize(new_size, Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def parse_json_response(text: str):
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    m = re.search(r"```json\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if m:
        return json.loads(m.group(1))

    m = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if m:
        return json.loads(m.group(1))

    raise ValueError("Model response could not be parsed as JSON.")


def build_prompt(
    image_labels: List[str],
    mode: str,
    task_text: str | None = None,
) -> str:
    task_block = ""
    if task_text:
        task_block = f"""
Optional task context:
{task_text}
""".rstrip()

    mode_instructions = {
        "per_image": """
Focus only on describing each screenshot individually.
Do not describe transitions unless they are obvious from one screenshot alone.
""".strip(),
        "changes": """
Focus on differences and transitions between consecutive screenshots.
Also provide a short overall summary of what changes across the sequence.
""".strip(),
        "both": """
Describe each screenshot individually and also describe the changes between consecutive screenshots.
Also provide a short overall summary of the sequence.
""".strip(),
    }[mode]

    return f"""
You are given one or more screenshots from a web UI flow.

{task_block}

The screenshots are ordered as follows:
{json.dumps(image_labels, indent=2)}

Your job is to produce a structured textual description of the visible UI.

Important rules:
- Only describe what is visible in the screenshots.
- Do not invent hidden backend behavior.
- Do not generate software requirements.
- Do not generate test steps.
- Be concrete and UI-focused.
- Mention visible text inputs, dropdowns, buttons, menus, selected values, popups, overlays, validation messages, tables, result lists, progress indicators, and other important controls.
- If something is uncertain, state that in "uncertainties".
- When describing changes, focus on visible differences and likely user-triggered UI updates.

{mode_instructions}

Return ONLY valid JSON in this format:
{{
  "images": [
    {{
      "image_id": "step_01",
      "description": "Short UI description of this screenshot.",
      "visible_ui_elements": ["input field for ...", "button ..."],
      "visible_values": ["zip code 08817", "selected option ..."],
      "uncertainties": ["optional uncertain point"]
    }}
  ],
  "pairwise_changes": [
    {{
      "from_image_id": "step_01",
      "to_image_id": "step_02",
      "changes": [
        "Visible change 1",
        "Visible change 2"
      ],
      "likely_user_action": "Short guess such as opening a dropdown or entering text"
    }}
  ],
  "overall_summary": "Short summary of the sequence as a whole."
}}

Additional constraints:
- If only one screenshot is provided, return an empty list for "pairwise_changes".
- If mode is "per_image", keep "pairwise_changes" empty.
- If mode is "changes", still include "images", but keep each image description short.
""".strip()


def run_gemini(prompt: str, image_bytes_list: List[bytes], model_name: str) -> str:
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)

    parts = [prompt]
    for img_bytes in image_bytes_list:
        parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))

    response = client.models.generate_content(
        model=model_name,
        contents=parts,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )

    return response.text


def ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", nargs="*", default=None, help="One or more image paths")
    parser.add_argument("--flow-dir", type=Path, default=None, help="Flow directory containing step_XX.png files")
    parser.add_argument("--steps", type=str, default=None, help="Comma-separated step numbers, e.g. 1,3,5")
    parser.add_argument("--max-images", type=int, default=None, help="Only used with --flow-dir if --steps is not given")
    parser.add_argument("--mode", choices=["per_image", "changes", "both"], default="both")
    parser.add_argument("--image-max-side", type=int, default=1024)
    parser.add_argument("--model", type=str, default="gemini-2.5-flash")
    parser.add_argument("--task", type=str, default=None, help="Optional task text")
    parser.add_argument("--out-file", type=Path, default=None, help="Explicit output JSON path")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    image_paths: List[Path] = []
    image_labels: List[str] = []

    if args.flow_dir is not None:
        step_paths = find_step_images(args.flow_dir)
        if not step_paths:
            raise FileNotFoundError(f"No step_*.png files found in {args.flow_dir}")

        selected = select_images(step_paths, steps_arg=args.steps, max_images=args.max_images)
        if not selected:
            raise ValueError("No images selected.")

        image_paths = selected
        image_labels = [f"step_{parse_step_number(p):02d}" for p in selected]

        task_text = args.task
        task_json = args.flow_dir / "task.json"
        if task_text is None and task_json.exists():
            try:
                task_data = json.loads(task_json.read_text(encoding="utf-8"))
                task_text = task_data.get("confirmed_task")
            except Exception:
                task_text = None

        if args.out_file is None:
            out_dir = DEFAULT_OUT_ROOT / args.flow_dir.name
            out_file = out_dir / "screen_descriptions.json"
        else:
            out_file = args.out_file

    elif args.image:
        image_paths = [Path(p) for p in args.image]
        for p in image_paths:
            if not p.exists():
                raise FileNotFoundError(f"Image not found: {p}")

        image_labels = [p.stem for p in image_paths]
        task_text = args.task

        if args.out_file is None:
            out_file = Path.cwd() / "screen_descriptions.json"
        else:
            out_file = args.out_file
    else:
        raise ValueError("Provide either --flow-dir or --image.")

    prompt = build_prompt(
        image_labels=image_labels,
        mode=args.mode,
        task_text=task_text,
    )

    ensure_parent(out_file)
    prompt_file = out_file.with_name(out_file.stem + "_prompt.txt")
    raw_file = out_file.with_name(out_file.stem + "_raw.txt")
    meta_file = out_file.with_name(out_file.stem + "_meta.json")

    selection_meta = {
        "mode": args.mode,
        "model": args.model,
        "image_max_side": args.image_max_side,
        "images": [str(p) for p in image_paths],
        "image_labels": image_labels,
        "task": task_text,
    }

    prompt_file.write_text(prompt, encoding="utf-8")
    meta_file.write_text(json.dumps(selection_meta, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.dry_run:
        print("[DRY RUN]")
        print("Output:", out_file)
        print("Images:", [str(p) for p in image_paths])
        return

    image_bytes_list = [downscale_to_png_bytes(p, max_side=args.image_max_side) for p in image_paths]
    raw_text = run_gemini(prompt, image_bytes_list, model_name=args.model)
    raw_file.write_text(raw_text, encoding="utf-8")

    parsed = parse_json_response(raw_text)
    out_file.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[OK] Wrote {out_file}")


if __name__ == "__main__":
    main()
