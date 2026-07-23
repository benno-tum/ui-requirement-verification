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
    / "gemini31flashlite_realistic_topk4_no_claims_01_13_20260721"
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


def write_run_summary() -> None:
    flows: list[dict[str, object]] = []
    totals = Counter()
    source_totals: Counter[str] = Counter()
    total_cost = 0.0
    for path in sorted(RUN_ROOT.glob("[0-1][0-9]_*.json")):
        run = json.loads(path.read_text(encoding="utf-8"))
        results = run.get("results") or []
        claims = [claim for result in results for claim in result.get("claims", [])]
        evidence = [item for claim in claims for item in claim.get("evidence", [])]
        boxes = [item for item in evidence if isinstance(item.get("bbox"), list)]
        sources = Counter(str((item.get("bbox_metadata") or {}).get("source") or "unknown") for item in boxes)
        source_totals.update(sources)
        diagnostics = (run.get("metadata") or {}).get("gemini_image_verifier") or {}
        usage = diagnostics.get("usage") or {}
        calls = int(diagnostics.get("api_calls") or 0)
        cost = float(usage.get("estimated_cost_usd") or 0.0)
        fallbacks = int(diagnostics.get("fallbacks") or 0)
        totals.update(requirements=len(results), claims=len(claims), evidence_records=len(evidence),
                      bounding_boxes=len(boxes), api_calls=calls, fallbacks=fallbacks)
        total_cost += cost
        flows.append({
            "flow_id": run.get("flow_id"),
            "execution_mode": "batched-topk-k4-raw-requirements-no-decomposition",
            "requirements": len(results), "claims": len(claims), "evidence_records": len(evidence),
            "bounding_boxes": len(boxes), "bbox_sources": dict(sources),
            "labels": dict(Counter(str(item.get("final_label") or "UNKNOWN") for item in results)),
            "api_calls": calls, "fallbacks": fallbacks, "estimated_cost_usd": cost,
            "prompt_version": diagnostics.get("prompt_version"),
        })
    if len(flows) != 13:
        return
    summary = {
        "schema_version": "realistic_topk_no_claims_run_set_v1", "run_id": RUN_ROOT.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "model": "gemini-3.1-flash-lite", "thinking_level": "low",
            "requested_execution_mode": "batched-topk", "top_k": 4,
            "image_variant": "preferred-original", "claim_decomposition_policy": "disabled",
            "effective_claim": "complete requirement text",
            "ui_evaluability": "independently predicted in the joint model call",
            "grounding": "Joint verification and OmniParser/OCR candidate selection",
            "prompt_version": "GEMINI_BATCHED_IMAGE_CLAIM_VERIFICATION_V2_GROUNDED_REGIONS_CANDIDATE_MARKS",
            "estimated_cost_usd": total_cost,
        },
        "fallback_flows": [item["flow_id"] for item in flows if item["fallbacks"]],
        "totals": {**dict(totals), "flows": 13, "bbox_sources": dict(source_totals),
                   "estimated_cost_usd": total_cost},
        "flows": flows,
    }
    (RUN_ROOT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare or execute the realistic Gemini 3.1 Flash-Lite active-top-k benchmark: "
            "raw requirements, no claim decomposition, and joint candidate-mark grounding."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Make API calls. Without this flag, only write the auditable experiment manifest.",
    )
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--flows", nargs="*", choices=sorted(CANDIDATE_DIRS))
    parser.add_argument("--max-output-tokens", type=int, default=16384)
    parser.add_argument("--cache-suffix", default="")
    parser.add_argument("--max-group-claims", type=int, default=12)
    return parser.parse_args()


def flow_directories(numbers: set[str] | None = None) -> list[Path]:
    flows = sorted(
        path
        for path in FLOW_ROOT.iterdir()
        if path.is_dir() and path.name[:2] in CANDIDATE_DIRS
    )
    if len(flows) != 13:
        raise ValueError(f"Expected 13 benchmark flows, found {len(flows)}.")
    return [flow for flow in flows if numbers is None or flow.name[:2] in numbers]


def command_for(
    flow_dir: Path,
    *,
    max_output_tokens: int = 16384,
    cache_suffix: str = "",
    max_group_claims: int = 12,
) -> list[str]:
    number = flow_dir.name[:2]
    gold = GOLD_ROOT / flow_dir.name / "verification_gold.json"
    candidates = CANDIDATE_ROOT / CANDIDATE_DIRS[number] / "candidates.json"
    assets = ASSET_ROOT / f"flow{number}_v7_factcoverage_20260721"
    output = RUN_ROOT / f"{flow_dir.name}.json"
    suffix = f"_{cache_suffix}" if cache_suffix else ""
    cache = RUN_ROOT / "cache" / f"{flow_dir.name}{suffix}.json"
    missing = [path for path in (gold, candidates, assets) if not path.exists()]
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
        "--no-claims",
        "--no-llm-claim-fallback",
        "--claim-decomposition-policy", "disabled",
        "--max-claims", "1",
        "--verifier", "gemini-image",
        "--execution-mode", "batched-topk",
        "--verifier-model", "gemini-3.1-flash-lite",
        "--verifier-temperature", "0",
        "--max-verifier-images", "4",
        "--max-verifier-group-images", "4",
        "--max-verifier-group-claims", str(max_group_claims),
        "--gemini-max-retries", "2",
        "--max-gemini-api-calls", "-1",
        "--claim-workers", "1",
        "--verifier-cache", str(cache),
        "--verifier-thinking-level", "low",
        "--verifier-max-output-tokens", str(max_output_tokens),
        "--verifier-predict-ui-evaluability",
        "--grounding-candidates", str(candidates),
        "--grounding-assets-dir", str(assets),
    ]


def manifest_for(
    flows: list[Path],
    *,
    max_output_tokens: int = 16384,
    cache_suffix: str = "",
    max_group_claims: int = 12,
) -> dict[str, object]:
    return {
        "schema_version": "realistic_topk_no_claims_experiment_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "prepared_not_executed",
        "scientific_purpose": (
            "Evaluate raw requirement verification without benchmark-provided or pipeline-decomposed claims, "
            "using the previously selected active top-k K=4 retrieval configuration."
        ),
        "model": "gemini-3.1-flash-lite",
        "thinking_level": "low",
        "requirements_input": "benchmark requirement text only",
        "gold_fields_excluded_from_prompt": [
            "claims",
            "claim statuses",
            "verification labels",
            "evidence steps",
            "evidence regions",
            "rationales",
            "annotation notes",
        ],
        "claim_decomposition": {
            "enabled": False,
            "policy": "disabled",
            "effective_claim": "the complete requirement text",
            "max_claims_per_requirement": 1,
        },
        "retrieval": {
            "method": "lexical",
            "top_k": 4,
            "execution_mode": "batched-topk",
            "max_screenshot_steps_per_call": 4,
            "max_requirements_per_call": max_group_claims,
            "include_sequence_context": True,
        },
        "grounding": {
            "mode": "joint verification and candidate-mark selection",
            "candidate_sources": ["OmniParser UI regions", "Tesseract OCR lines"],
            "supplemental_coordinate_fallback": True,
        },
        "ui_evaluability": {
            "predicted_jointly_by_model": True,
            "pipeline_preclassification_hidden_from_prompt": True,
            "manual_label_used_only_for_post_run_evaluation": True,
            "classes": ["UI_VERIFIABLE", "PARTIALLY_UI_VERIFIABLE", "NOT_UI_VERIFIABLE"],
        },
        "offline_preflight": {
            "requirements": 258,
            "expected_model_calls": 26,
            "screenshot_step_uploads": 102,
            "actual_image_attachments_including_mark_layers": 387,
            "estimated_input_tokens": 1202035,
            "estimated_generated_and_thinking_tokens": 36120,
            "estimated_cost_usd": 0.355,
            "recommended_cost_allowance_usd_including_retries": 0.50,
        },
        "execution_note": (
            "The standard configuration uses at most 12 requirements per group. Flow 11 required the same "
            "deterministic completeness recovery with groups of at most 4 after the model repeatedly omitted "
            "records from one 8-requirement group. K, prompt, model, and screenshot cap remained unchanged."
        ),
        "post_run_evaluation": {
            "verification": [
                "accuracy",
                "macro_f1",
                "per_class_precision_recall_f1",
                "confusion_matrix",
                "false_fulfillment_rate",
            ],
            "ui_evaluability": [
                "raw_agreement",
                "macro_f1",
                "per_class_precision_recall_f1",
                "confusion_matrix",
                "unweighted_cohen_kappa",
                "ordinal_weighted_cohen_kappa",
            ],
            "grounding": [
                "box_count",
                "applicable_claim_box_coverage",
                "manual_inspection_judgments",
            ],
        },
        "flows": [
            {
                "flow_id": flow.name,
                "output": str(RUN_ROOT / f"{flow.name}.json"),
                "command": command_for(
                    flow,
                    max_output_tokens=max_output_tokens,
                    cache_suffix=cache_suffix,
                    max_group_claims=max_group_claims,
                ),
            }
            for flow in flows
        ],
    }


def run_flow(
    flow_dir: Path,
    *,
    force: bool,
    max_output_tokens: int,
    cache_suffix: str,
    max_group_claims: int,
) -> dict[str, object]:
    output = RUN_ROOT / f"{flow_dir.name}.json"
    if output.is_file() and not force:
        return {"flow_id": flow_dir.name, "status": "existing", "output": str(output)}
    result = subprocess.run(
        command_for(
            flow_dir,
            max_output_tokens=max_output_tokens,
            cache_suffix=cache_suffix,
            max_group_claims=max_group_claims,
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


def main() -> None:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be positive.")
    numbers = set(args.flows) if args.flows else None
    flows = flow_directories(numbers)
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = manifest_for(
        flows,
        max_output_tokens=args.max_output_tokens,
        cache_suffix=args.cache_suffix,
        max_group_claims=args.max_group_claims,
    )
    manifest_path = RUN_ROOT / "experiment_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Prepared {manifest_path} for {len(flows)} flow(s).", flush=True)
    if not args.execute:
        return

    results: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                run_flow,
                flow,
                force=args.force,
                max_output_tokens=args.max_output_tokens,
                cache_suffix=args.cache_suffix,
                max_group_claims=args.max_group_claims,
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
        json.dumps({"configuration": manifest, "results": results}, indent=2),
        encoding="utf-8",
    )
    write_run_summary()
    failures = [result for result in results if result["status"] == "failed"]
    if failures:
        raise SystemExit(f"{len(failures)} flow(s) failed.")


if __name__ == "__main__":
    main()
