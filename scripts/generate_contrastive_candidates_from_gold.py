from __future__ import annotations

import argparse
from pathlib import Path

from ui_verifier.requirements.contrastive_generation import (
    DEFAULT_CONTEXT_ROOT,
    DEFAULT_FLOW_ROOT,
    DEFAULT_GOLD_ROOT,
    DEFAULT_OUTPUT_ROOT,
    build_prompt_for_flow,
    default_raw_response_path,
    list_gold_flow_ids,
    maybe_print_or_copy_prompt,
    parse_existing_response,
    prepare_bundle_for_flow,
)


def _resolve_flow_ids(gold_root: Path, flow_id: str | None, max_flows: int) -> list[str]:
    if flow_id:
        return [flow_id]
    return list_gold_flow_ids(gold_root)[:max_flows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold-root", type=Path, default=DEFAULT_GOLD_ROOT)
    parser.add_argument("--flow-id", type=str, default=None)
    parser.add_argument("--max-flows", type=int, default=1)
    parser.add_argument("--target-partially", type=int, default=5)
    parser.add_argument("--target-abstain", type=int, default=5)
    parser.add_argument("--target-not-fulfilled", type=int, default=5)
    parser.add_argument("--model", type=str, default="manual-chatgpt")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--prepare-manual-bundle", action="store_true")
    parser.add_argument("--print-prompt", action="store_true")
    parser.add_argument("--copy-prompt", action="store_true")
    parser.add_argument("--parse-existing-response", action="store_true")
    parser.add_argument("--raw-response-path", type=Path, default=None)
    args = parser.parse_args()

    if args.prepare_manual_bundle == args.parse_existing_response:
        raise SystemExit("Choose exactly one of --prepare-manual-bundle or --parse-existing-response.")

    flow_ids = _resolve_flow_ids(args.gold_root, args.flow_id, args.max_flows)
    if not flow_ids:
        print("No gold requirement flows found.")
        return

    if args.raw_response_path is not None and len(flow_ids) != 1:
        raise SystemExit("--raw-response-path requires exactly one target flow.")

    for flow_id in flow_ids:
        prompt, _, _, _ = build_prompt_for_flow(
            flow_id,
            gold_root=args.gold_root,
            flow_root=DEFAULT_FLOW_ROOT,
            context_root=DEFAULT_CONTEXT_ROOT,
            target_partially=args.target_partially,
            target_abstain=args.target_abstain,
            target_not_fulfilled=args.target_not_fulfilled,
        )
        maybe_print_or_copy_prompt(
            prompt=prompt,
            print_prompt=args.print_prompt,
            copy_prompt=args.copy_prompt,
            flow_id=flow_id,
        )

        if args.prepare_manual_bundle:
            output_dir = DEFAULT_OUTPUT_ROOT / flow_id
            bundle_dir = output_dir / "manual_contrastive_bundle"
            if args.dry_run:
                print(f"[DRY RUN] Would create manual bundle for {flow_id} at {bundle_dir}")
                continue

            bundle_dir, _ = prepare_bundle_for_flow(
                flow_id=flow_id,
                output_root=DEFAULT_OUTPUT_ROOT,
                gold_root=args.gold_root,
                flow_root=DEFAULT_FLOW_ROOT,
                context_root=DEFAULT_CONTEXT_ROOT,
                target_partially=args.target_partially,
                target_abstain=args.target_abstain,
                target_not_fulfilled=args.target_not_fulfilled,
                model_name=args.model,
                temperature=args.temperature,
            )
            print(f"[OK] {flow_id} -> {bundle_dir}")
            continue

        raw_response_path = args.raw_response_path or default_raw_response_path(DEFAULT_OUTPUT_ROOT / flow_id)
        if args.dry_run:
            print(f"[DRY RUN] Would parse {raw_response_path} for {flow_id}")
            continue

        contrastive_file = parse_existing_response(
            flow_id=flow_id,
            raw_response_path=raw_response_path,
            model_name=args.model,
            generation_temperature=args.temperature,
            gold_root=args.gold_root,
            flow_root=DEFAULT_FLOW_ROOT,
            context_root=DEFAULT_CONTEXT_ROOT,
            output_root=DEFAULT_OUTPUT_ROOT,
        )
        print(
            f"[OK] {flow_id} -> "
            f"{DEFAULT_OUTPUT_ROOT / flow_id / 'contrastive_candidates.json'} "
            f"({len(contrastive_file.requirements)} requirements)"
        )


if __name__ == "__main__":
    main()
