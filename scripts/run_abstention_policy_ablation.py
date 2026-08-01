from __future__ import annotations

import argparse
import json
from pathlib import Path

from ui_verifier.evaluation.abstention_policy import reaggregate_without_abstention


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a no-API forced-decision policy ablation from frozen verification outputs."
    )
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_files = sorted(args.source_dir.glob("*.json"))
    if not source_files:
        raise FileNotFoundError(f"No verification JSON files found in {args.source_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    changed_total = 0
    for source_path in source_files:
        output_path = args.output_dir / source_path.name
        if output_path.exists() and not args.force:
            raise FileExistsError(f"Refusing to replace {output_path}; pass --force to overwrite.")
        source = json.loads(source_path.read_text(encoding="utf-8"))
        output = reaggregate_without_abstention(source)
        changed_total += int(output["metadata"]["abstention_policy_ablation"]["changed_abstentions"])
        output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        f"files={len(source_files)} changed_abstentions={changed_total} "
        f"additional_tokens=0 output_dir={args.output_dir}"
    )


if __name__ == "__main__":
    main()
