from __future__ import annotations

import argparse
from pathlib import Path

from ui_verifier.common.flow_utils import find_flow_dirs
from ui_verifier.data.mind2web_originals import ensure_flow_original_images


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_FLOWS_ROOT = BASE_DIR / "data" / "processed" / "flows" / "mind2web"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--flows-root", type=Path, default=DEFAULT_FLOWS_ROOT)
    parser.add_argument(
        "--flow-id",
        action="append",
        dest="flow_ids",
        help="Specific flow id to backfill. Can be passed multiple times.",
    )
    args = parser.parse_args()

    flows_root = args.flows_root
    if not flows_root.exists():
        raise FileNotFoundError(f"Flows root not found: {flows_root}")

    if args.flow_ids:
        flow_dirs = [flows_root / flow_id for flow_id in args.flow_ids]
    else:
        flow_dirs = find_flow_dirs(flows_root)

    total = 0
    hydrated = 0
    for flow_dir in flow_dirs:
        total += 1
        if not flow_dir.exists():
            print(f"[MISSING] {flow_dir.name}")
            continue
        original_paths = ensure_flow_original_images(flow_dir)
        if original_paths:
            hydrated += 1
            print(f"[OK] {flow_dir.name}: {len(original_paths)} original screenshots available")
        else:
            print(f"[SKIP] {flow_dir.name}: no original screenshots available")

    print(f"\nDone. {hydrated}/{total} flows have original screenshots available.")


if __name__ == "__main__":
    main()
