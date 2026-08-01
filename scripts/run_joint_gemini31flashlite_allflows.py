from __future__ import annotations

# Historical July 2026 wrapper retained for result provenance.
# New controlled runs must use run_thesis_final_experiments.py.

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


BASE_DIR = Path(__file__).resolve().parents[1]
FLOW_ROOT = BASE_DIR / "data/processed/flows/mind2web"
GOLD_ROOT = BASE_DIR / "data/annotations/verification_gold"
RUN_ROOT = (
    BASE_DIR
    / "data/generated/verification_pipeline_runs"
    / "gemini31flashlite_joint_verification_omnimark_singlecall_01_13_20260721"
)
CANDIDATE_ROOT = BASE_DIR / "data/generated/omniparser_candidate_marks"
ASSET_ROOT = BASE_DIR / "data/generated/gemini25_omnimark_grounding"

CANDIDATE_DIRS = {
    "01": "flow01_v7_20260721",
    "02": "flow02_20260720",
    "03": "flow03_v7_20260721",
    "04": "flow04_v7_20260721",
    "05": "flow05_v7_20260721",
    "06": "flow06_v7_20260721",
    "07": "flow07_timing_20260720",
    "08": "flow08_v7_20260721",
    "09": "flow09_v7_20260721",
    "10": "flow10_v7_20260721",
    "11": "flow11_v7_20260721",
    "12": "flow12_v6_20260721",
    "13": "flow13_v7_20260721",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run joint verification and candidate-mark grounding once per benchmark flow."
    )
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--flows", nargs="*", choices=sorted(CANDIDATE_DIRS))
    parser.add_argument("--max-output-tokens", type=int, default=16384)
    parser.add_argument("--cache-suffix", default="")
    return parser.parse_args()


def flow_directories() -> list[Path]:
    flows = sorted(path for path in FLOW_ROOT.iterdir() if path.is_dir() and path.name[:2] in CANDIDATE_DIRS)
    if len(flows) != 13:
        raise ValueError(f"Expected 13 benchmark flows, found {len(flows)}.")
    return flows


def command_for(
    flow_dir: Path,
    *,
    max_output_tokens: int,
    cache_suffix: str,
) -> list[str]:
    number = flow_dir.name[:2]
    gold = GOLD_ROOT / flow_dir.name / "verification_gold.json"
    candidates = CANDIDATE_ROOT / CANDIDATE_DIRS[number] / "candidates.json"
    assets = ASSET_ROOT / f"flow{number}_v7_factcoverage_20260721"
    output = RUN_ROOT / f"{flow_dir.name}.json"
    suffix = f"_{cache_suffix}" if cache_suffix else ""
    cache = RUN_ROOT / "cache" / f"{flow_dir.name}{suffix}.json"
    required = [gold, candidates, assets]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(missing[0])
    return [
        sys.executable,
        str(BASE_DIR / "scripts/run_verification_pipeline.py"),
        "--flow-dir", str(flow_dir),
        "--image-variant", "preferred-original",
        "--requirements", str(gold),
        "--requirements-source", "benchmark",
        "--out", str(output),
        "--retriever", "lexical",
        "--top-k", "4",
        "--claims",
        "--no-llm-claim-fallback",
        "--claim-decomposition-policy", "provided",
        "--max-claims", "4",
        "--verifier", "gemini-image",
        "--execution-mode", "single-call",
        "--verifier-model", "gemini-3.1-flash-lite",
        "--verifier-temperature", "0",
        "--max-verifier-images", "4",
        "--max-verifier-group-images", "-1",
        "--max-verifier-group-claims", "-1",
        "--gemini-max-retries", "2",
        "--max-gemini-api-calls", "-1",
        "--claim-workers", "1",
        "--verifier-cache", str(cache),
        "--verifier-thinking-level", "low",
        "--verifier-max-output-tokens", str(max_output_tokens),
        "--grounding-candidates", str(candidates),
        "--grounding-assets-dir", str(assets),
    ]


def run_flow(
    flow_dir: Path,
    *,
    force: bool,
    max_output_tokens: int,
    cache_suffix: str,
) -> dict[str, object]:
    output = RUN_ROOT / f"{flow_dir.name}.json"
    if output.is_file() and not force:
        return {"flow_id": flow_dir.name, "status": "existing", "output": str(output)}
    result = subprocess.run(
        command_for(
            flow_dir,
            max_output_tokens=max_output_tokens,
            cache_suffix=cache_suffix,
        ),
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "flow_id": flow_dir.name,
        "status": "completed" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "output": str(output),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def write_run_summary() -> None:
    flow_summaries: list[dict[str, object]] = []
    total_requirements = total_claims = total_boxes = total_calls = 0
    total_cost = 0.0
    source_counts: Counter[str] = Counter()
    for path in sorted(RUN_ROOT.glob("[0-1][0-9]_*.json")):
        run = json.loads(path.read_text(encoding="utf-8"))
        results = run.get("results") or []
        claims = [claim for result in results for claim in result.get("claims", [])]
        evidence = [item for claim in claims for item in claim.get("evidence", [])]
        boxed = [item for item in evidence if isinstance(item.get("bbox"), list)]
        for item in boxed:
            source_counts[str((item.get("bbox_metadata") or {}).get("source") or "unknown")] += 1
        diagnostics = (run.get("metadata") or {}).get("gemini_image_verifier") or {}
        usage = diagnostics.get("usage") or {}
        labels = Counter(str(result.get("final_label") or "UNKNOWN") for result in results)
        calls = int(diagnostics.get("api_calls") or 0)
        cost = float(usage.get("estimated_cost_usd") or 0.0)
        total_requirements += len(results)
        total_claims += len(claims)
        total_boxes += len(boxed)
        total_calls += calls
        total_cost += cost
        flow_summaries.append(
            {
                "flow_id": run.get("flow_id"),
                "execution_mode": "single-call-joint-verification-candidate-grounding",
                "requirements": len(results),
                "claims": len(claims),
                "evidence_records": len(evidence),
                "bounding_boxes": len(boxed),
                "bbox_sources": dict(
                    Counter(
                        str((item.get("bbox_metadata") or {}).get("source") or "unknown")
                        for item in boxed
                    )
                ),
                "labels": dict(labels),
                "api_calls": calls,
                "fallbacks": int(diagnostics.get("fallbacks") or 0),
                "estimated_cost_usd": cost,
                "prompt_version": diagnostics.get("prompt_version"),
            }
        )
    if len(flow_summaries) != 13:
        return
    summary = {
        "schema_version": "joint_verification_candidate_grounding_run_set_v1",
        "run_id": RUN_ROOT.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "model": "gemini-3.1-flash-lite",
            "thinking_level": "low",
            "requested_execution_mode": "single-call",
            "image_variant": "preferred-original",
            "claim_decomposition_policy": "provided",
            "aggregation": "claim decisions aggregated by the evidence-first pipeline",
            "grounding": "Joint claim verification and OmniParser/OCR candidate selection in the same per-flow prompt",
            "prompt_version": "GEMINI_BATCHED_IMAGE_CLAIM_VERIFICATION_V2_GROUNDED_REGIONS_CANDIDATE_MARKS",
            "estimated_cost_usd": total_cost,
        },
        "fallback_flows": [item["flow_id"] for item in flow_summaries if item["fallbacks"]],
        "totals": {
            "flows": len(flow_summaries),
            "requirements": total_requirements,
            "claims": total_claims,
            "evidence_records": total_boxes,
            "bounding_boxes": total_boxes,
            "bbox_sources": dict(source_counts),
            "api_calls": total_calls,
            "estimated_cost_usd": total_cost,
        },
        "flows": flow_summaries,
    }
    (RUN_ROOT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be positive.")
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    flows = flow_directories()
    if args.flows:
        requested = set(args.flows)
        flows = [flow for flow in flows if flow.name[:2] in requested]
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                run_flow,
                flow,
                force=args.force,
                max_output_tokens=args.max_output_tokens,
                cache_suffix=args.cache_suffix,
            ): flow.name
            for flow in flows
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"{result['flow_id']}: {result['status']}", flush=True)
            if result["status"] == "failed":
                print(result.get("stderr") or result.get("stdout") or "", flush=True)
    results.sort(key=lambda item: str(item["flow_id"]))
    (RUN_ROOT / "orchestration_summary.json").write_text(
        json.dumps({"model": "gemini-3.1-flash-lite", "thinking_level": "low", "results": results}, indent=2),
        encoding="utf-8",
    )
    write_run_summary()
    failures = [result for result in results if result["status"] == "failed"]
    if failures:
        raise SystemExit(f"{len(failures)} flow(s) failed.")


if __name__ == "__main__":
    main()
