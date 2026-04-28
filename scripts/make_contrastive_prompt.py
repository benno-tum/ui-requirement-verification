#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

from ui_verifier.requirements.prompting import build_contrastive_from_gold_prompt


GOLD_ROOT = Path("data/annotations/requirements_gold")
FLOW_ROOT = Path("data/processed/flows/mind2web")
OUT_ROOT = Path("data/generated/contrastive_candidates")


def flow_prefix(flow_id: str) -> int | None:
    m = re.match(r"^(\d+)_", flow_id)
    if not m:
        return None
    return int(m.group(1))


def parse_flow_range(value: str) -> tuple[int, int]:
    m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", value)
    if not m:
        raise argparse.ArgumentTypeError("flow range must look like 1-13")
    start, end = int(m.group(1)), int(m.group(2))
    if start > end:
        raise argparse.ArgumentTypeError("range start must be <= range end")
    return start, end


def discover_gold_flows(gold_root: Path) -> list[str]:
    flows: list[str] = []
    if not gold_root.exists():
        return flows

    for path in gold_root.iterdir():
        if not path.is_dir():
            continue
        gold_file = path / "gold_requirements.json"
        if gold_file.exists():
            flows.append(path.name)

    flows.sort(key=lambda x: (flow_prefix(x) is None, flow_prefix(x) or 10**9, x))
    return flows


def select_flows(
    *,
    flow_id: str | None,
    flow_range: tuple[int, int] | None,
    use_all: bool,
    gold_root: Path,
) -> list[str]:
    gold_flows = discover_gold_flows(gold_root)

    if flow_id:
        return [flow_id]

    if flow_range:
        start, end = flow_range
        return [
            fid
            for fid in gold_flows
            if (p := flow_prefix(fid)) is not None and start <= p <= end
        ]

    if use_all:
        return gold_flows

    raise ValueError("choose exactly one of --flow-id, --flow-range, or --all")


def build_prompt_for_flow(
    *,
    flow_id: str,
    target_partially: int,
    target_abstain: int,
    target_not_fulfilled: int,
    overwrite: bool,
) -> Path | None:
    task_path = FLOW_ROOT / flow_id / "task.json"
    gold_path = GOLD_ROOT / flow_id / "gold_requirements.json"
    out_path = OUT_ROOT / flow_id / "prompt.txt"

    if not gold_path.exists():
        print(f"[SKIP] {flow_id}: missing {gold_path}")
        return None

    if not task_path.exists():
        print(f"[SKIP] {flow_id}: missing {task_path}")
        return None

    if out_path.exists() and not overwrite:
        print(f"[SKIP] {flow_id}: prompt exists at {out_path} (use --overwrite)")
        return None

    task = json.loads(task_path.read_text(encoding="utf-8"))
    gold = json.loads(gold_path.read_text(encoding="utf-8"))

    prompt = build_contrastive_from_gold_prompt(
        task,
        gold,
        target_partially=target_partially,
        target_abstain=target_abstain,
        target_not_fulfilled=target_not_fulfilled,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(prompt, encoding="utf-8")
    print(f"[OK] {flow_id} -> {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--flow-id", type=str)
    scope.add_argument("--flow-range", type=parse_flow_range, help="e.g. 1-13")
    scope.add_argument("--all", action="store_true")

    parser.add_argument("--target-partially", type=int, default=2)
    parser.add_argument("--target-abstain", type=int, default=2)
    parser.add_argument("--target-not-fulfilled", type=int, default=2)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    flows = select_flows(
        flow_id=args.flow_id,
        flow_range=args.flow_range,
        use_all=args.all,
        gold_root=GOLD_ROOT,
    )

    if not flows:
        print("[WARN] No matching flows found.")
        return

    print(f"[INFO] Generating prompts for {len(flows)} flow(s)")
    for flow_id in flows:
        build_prompt_for_flow(
            flow_id=flow_id,
            target_partially=args.target_partially,
            target_abstain=args.target_abstain,
            target_not_fulfilled=args.target_not_fulfilled,
            overwrite=args.overwrite,
        )


if __name__ == "__main__":
    main()
