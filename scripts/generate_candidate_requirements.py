from pathlib import Path
from PIL import Image
from typing import List
import argparse
import io
import json
import os
import re
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = BASE_DIR / "data" / "processed" / "flows" / "mind2web"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_step_number(path: Path) -> int:
    m = re.search(r"step_(\d+)\.png$", path.name)
    if not m:
        raise ValueError(f"Cannot parse step number from {path.name}")
    return int(m.group(1))


def find_flow_dirs(input_dir: Path) -> List[Path]:
    return sorted([p for p in input_dir.iterdir() if p.is_dir()])


def find_step_images(flow_dir: Path) -> List[Path]:
    return sorted(flow_dir.glob("step_*.png"))


def choose_evenly_spaced(items: List[Path], k: int) -> List[Path]:
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
            if not part:
                continue
            wanted.append(int(part))

        selected = []
        by_num = {parse_step_number(p): p for p in step_paths}
        for s in wanted:
            if s in by_num:
                selected.append(by_num[s])
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


def build_prompt(task: dict, selected_steps: List[int]) -> str:
    confirmed_task = task.get("confirmed_task", "")
    website = task.get("website", "")
    domain = task.get("domain", "")

    return f"""
You are given an ordered screenshot sequence of a web UI flow.

Task description:
{confirmed_task}

Website:
{website}

Domain:
{domain}

Visible screenshots correspond to these step indices:
{selected_steps}

Your job:
Generate candidate SOFTWARE REQUIREMENTS for the UI.

Important:
- Generate UI software requirements, not user goals, not test steps, and not business objectives.
- Only use requirements that are supported by the visible screenshots.
- Focus on observable UI behavior and UI state.
- Use the form: "The system shall ..."
- Keep each requirement singular and concrete.
- Do not invent hidden backend behavior.
- If evidence is weak, either omit the requirement or lower confidence.

Good examples:
- The system shall provide an input field for pickup location.
- The system shall display available truck options with price information after search.
- The system shall allow the user to choose a pickup location from a list of available locations.
- If the same return location option is selected, the system shall allow the user to continue without entering a separate return location before results are shown.

Bad examples:
- The user shall rent the cheapest truck.
- The system shall maximize business revenue.
- The system shall use an efficient database.

Return ONLY valid JSON in this format:
{{
  "requirements": [
    {{
      "id": "REQ-01",
      "type": "ui_element_value | workflow_transition | conditional_behavior",
      "text": "The system shall ...",
      "evidence_steps": [1, 2],
      "confidence": "high | medium | low"
    }}
  ]
}}

Return 5 to 12 requirements if possible.
""".strip()


def parse_json_response(text: str):
    text = text.strip()

    # direct JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # fenced JSON
    m = re.search(r"```json\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if m:
        return json.loads(m.group(1))

    # fallback: first {...} block
    m = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if m:
        return json.loads(m.group(1))

    raise ValueError("Model response could not be parsed as JSON.")


def run_gemini(prompt: str, image_bytes_list: List[bytes], model_name: str):
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


def process_flow(flow_dir: Path, steps_arg: str | None, max_images: int | None, image_max_side: int, dry_run: bool, model_name: str):
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
        encoding="utf-8"
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
        encoding="utf-8"
    )

    print(f"[OK] {flow_dir.name} -> requirements_gemini.json")


def main():
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
