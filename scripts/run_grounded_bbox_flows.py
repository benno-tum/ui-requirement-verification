#!/usr/bin/env python3
"""Run the controlled Gemini grounded-region verification over Mind2Web flows 1-13."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
FLOW_ROOT = ROOT / "data" / "processed" / "flows" / "mind2web"
GOLD_ROOT = ROOT / "data" / "annotations" / "verification_gold"
DEFAULT_RUN_ID = "bbox_gemini_grounded_regions_topk4_01_13_20260719"


def command(flow_id: str, out: Path, cache: Path, *, mode: str, image_variant: str, model: str) -> list[str]:
    single_call = mode == "single-call"
    return [
        sys.executable,
        str(ROOT / "scripts" / "run_verification_pipeline.py"),
        "--flow-dir", str(FLOW_ROOT / flow_id),
        "--image-variant", image_variant,
        "--requirements", str(GOLD_ROOT / flow_id / "verification_gold.json"),
        "--requirements-source", "benchmark",
        "--out", str(out),
        "--retriever", "lexical",
        "--top-k", "4",
        "--claims",
        "--no-llm-claim-fallback",
        "--verifier", "gemini-image",
        "--execution-mode", mode,
        "--verifier-model", model,
        "--verifier-temperature", "0.0",
        "--max-verifier-images", "4",
        "--max-verifier-group-images", "-1" if single_call else "4",
        "--max-verifier-group-claims", "-1" if single_call else "12",
        "--gemini-max-retries", "2",
        "--max-gemini-api-calls", "-1",
        "--claim-workers", "1",
        "--claim-decomposition-policy", "provided",
        "--max-claims", "4",
        "--verifier-cache", str(cache),
    ]


def diagnostics(data: dict) -> dict:
    return data.get("metadata", {}).get("gemini_image_verifier", {})


def valid_topk(path: Path) -> bool:
    if not path.exists():
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    info = diagnostics(data)
    completed_calls = int(info.get("api_calls") or 0) + int(info.get("cache_hits") or 0)
    return bool(data.get("results")) and completed_calls > 0 and int(info.get("fallbacks") or 0) == 0


def summarize(
    run_dir: Path,
    flow_ids: list[str],
    fallback_flows: list[str],
    *,
    image_variant: str,
    model: str,
    requested_execution_mode: str,
) -> None:
    flows = []
    total_evidence = total_boxes = total_requirements = total_claims = 0
    sources: Counter[str] = Counter()
    for flow_id in flow_ids:
        path = run_dir / f"{flow_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        evidence = [
            item
            for result in data.get("results", [])
            for claim in result.get("claims", [])
            for item in claim.get("evidence", [])
        ]
        boxes = [item for item in evidence if item.get("bbox")]
        source_counts = Counter(str(item.get("bbox_metadata", {}).get("source") or "unknown") for item in boxes)
        sources.update(source_counts)
        label_counts = Counter(str(result.get("final_label")) for result in data.get("results", []))
        claim_count = sum(len(result.get("claims", [])) for result in data.get("results", []))
        total_requirements += len(data.get("results", []))
        total_claims += claim_count
        total_evidence += len(evidence)
        total_boxes += len(boxes)
        info = diagnostics(data)
        flows.append({
            "flow_id": flow_id,
            "execution_mode": data.get("metadata", {}).get("execution_mode"),
            "requirements": len(data.get("results", [])),
            "claims": claim_count,
            "evidence_records": len(evidence),
            "bounding_boxes": len(boxes),
            "bbox_sources": dict(source_counts),
            "labels": dict(label_counts),
            "api_calls": info.get("api_calls", 0),
            "fallbacks": info.get("fallbacks", 0),
            "prompt_version": info.get("prompt_version"),
        })
    summary = {
        "schema_version": "gemini_grounded_bbox_run_set_v1",
        "run_id": run_dir.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "model": model,
            "requested_execution_mode": requested_execution_mode,
            "retriever": "lexical",
            "top_k": 4,
            "max_images_per_group": 4,
            "image_variant": image_variant,
            "claim_decomposition_policy": "provided",
            "aggregation": "active deterministic LabelAggregator",
            "grounding": (
                "Gemini evidence_regions refined by nearby multi-token OCR phrases when available; "
                "raw Gemini coordinates are retained in metadata"
            ),
        },
        "fallback_flows": fallback_flows,
        "totals": {
            "flows": len(flows),
            "requirements": total_requirements,
            "claims": total_claims,
            "evidence_records": total_evidence,
            "bounding_boxes": total_boxes,
            "bbox_sources": dict(sources),
        },
        "flows": flows,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=13)
    parser.add_argument(
        "--image-variant",
        choices=["processed", "preferred-original"],
        default="processed",
    )
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--request-timeout-ms", type=int, default=120000)
    parser.add_argument("--max-output-tokens", type=int, default=32768)
    parser.add_argument(
        "--execution-mode",
        choices=["topk-with-fallback", "single-call"],
        default="topk-with-fallback",
    )
    args = parser.parse_args()
    child_env = {
        **os.environ,
        "GEMINI_REQUEST_TIMEOUT_MS": str(args.request_timeout_ms),
        "GEMINI_MAX_OUTPUT_TOKENS": str(args.max_output_tokens),
    }
    flow_ids = [path.name for path in sorted(FLOW_ROOT.iterdir()) if path.is_dir() and path.name[:2].isdigit() and 1 <= int(path.name[:2]) <= 13]
    run_dir = ROOT / "data" / "generated" / "verification_pipeline_runs" / args.run_id
    (run_dir / "cache").mkdir(parents=True, exist_ok=True)
    (run_dir / "failed_topk").mkdir(parents=True, exist_ok=True)
    fallback_flows: list[str] = []
    for flow_id in flow_ids:
        number = int(flow_id[:2])
        if number < args.start or number > args.end:
            continue
        active = run_dir / f"{flow_id}.json"
        if args.execution_mode == "single-call":
            print(f"\n=== {flow_id}: single-call (all flow images) ===", flush=True)
            result = subprocess.run(
                command(
                    flow_id,
                    active,
                    run_dir / "cache" / f"{flow_id}_single_call.json",
                    mode="single-call",
                    image_variant=args.image_variant,
                    model=args.model,
                ),
                cwd=ROOT,
                check=True,
                env=child_env,
            )
            if result.returncode != 0 or not valid_topk(active):
                raise RuntimeError(
                    f"Single-call Gemini verification did not complete without fallback for {flow_id}."
                )
            continue
        topk_attempt = run_dir / "failed_topk" / f"{flow_id}.json"
        print(f"\n=== {flow_id}: batched-topk ===", flush=True)
        result = subprocess.run(
            command(
                flow_id,
                active,
                run_dir / "cache" / f"{flow_id}_topk.json",
                mode="batched-topk",
                image_variant=args.image_variant,
                model=args.model,
            ),
            cwd=ROOT,
            env=child_env,
        )
        if result.returncode == 0 and valid_topk(active):
            continue
        fallback_flows.append(flow_id)
        if active.exists():
            active.replace(topk_attempt)
        print(f"=== {flow_id}: fallback single-call ===", flush=True)
        subprocess.run(
            command(
                flow_id,
                active,
                run_dir / "cache" / f"{flow_id}_single_call.json",
                mode="single-call",
                image_variant=args.image_variant,
                model=args.model,
            ),
            cwd=ROOT,
            check=True,
            env=child_env,
        )
    completed = [flow_id for flow_id in flow_ids if (run_dir / f"{flow_id}.json").exists()]
    summarize(
        run_dir,
        completed,
        fallback_flows,
        image_variant=args.image_variant,
        model=args.model,
        requested_execution_mode=args.execution_mode,
    )
    print(f"\nCompleted {len(completed)} flows; fallbacks={fallback_flows}; summary={run_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
