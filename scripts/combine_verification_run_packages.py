from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Combine compatible per-flow verification run packages.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, action="append", required=True)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = output_dir.name
    summaries = [load_json(path.resolve() / "summary.json") for path in args.run_dir]
    first_configuration = dict(summaries[0].get("configuration") or {})
    compatibility_keys = ("model", "requested_execution_mode", "image_variant", "prompt_version")
    for summary in summaries[1:]:
        configuration = summary.get("configuration") or {}
        for key in compatibility_keys:
            if configuration.get(key) != first_configuration.get(key):
                raise ValueError(f"Incompatible {key}: {configuration.get(key)!r}")

    flows: list[dict[str, Any]] = []
    fallbacks: list[Any] = []
    totals: Counter[str] = Counter()
    bbox_sources: Counter[str] = Counter()
    total_cost = 0.0
    for run_dir, summary in zip(args.run_dir, summaries):
        run_dir = run_dir.resolve()
        fallbacks.extend(summary.get("fallback_flows") or [])
        total_cost += float((summary.get("totals") or {}).get("estimated_cost_usd") or 0.0)
        for key in ("flows", "requirements", "claims", "evidence_records", "bounding_boxes"):
            totals[key] += int((summary.get("totals") or {}).get(key) or 0)
        bbox_sources.update((summary.get("totals") or {}).get("bbox_sources") or {})
        for flow in summary.get("flows") or []:
            flow_id = str(flow.get("flow_id") or "")
            if not flow_id:
                raise ValueError(f"Missing flow_id in {run_dir}")
            source_path = run_dir / f"{flow_id}.json"
            if not source_path.is_file():
                raise FileNotFoundError(source_path)
            shutil.copy2(source_path, output_dir / source_path.name)
            flows.append(flow)

    flows.sort(key=lambda item: str(item.get("flow_id") or ""))
    first_configuration["estimated_cost_usd"] = total_cost
    combined = {
        "schema_version": summaries[0].get("schema_version"),
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": first_configuration,
        "fallback_flows": fallbacks,
        "totals": {
            **dict(totals),
            "bbox_sources": dict(bbox_sources),
            "estimated_cost_usd": total_cost,
        },
        "flows": flows,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"Combined {len(flows)} flows, {totals['bounding_boxes']} boxes, "
        f"${total_cost:.4f} into {output_dir}"
    )


if __name__ == "__main__":
    main()
