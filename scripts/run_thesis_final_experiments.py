from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = BASE_DIR / "configs/thesis_final_experiments.json"
FLOW_ROOT = BASE_DIR / "data/processed/flows/mind2web"
GOLD_ROOT = BASE_DIR / "data/annotations/verification_gold"
OUTPUT_ROOT = BASE_DIR / "data/generated/thesis_final_experiments"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preflight or execute the frozen thesis experiment matrix. API calls require --execute."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--experiments", nargs="*", help="Experiment IDs. Defaults to every configured experiment.")
    parser.add_argument("--groups", nargs="*", help="Experiment groups configured in the selected file.")
    parser.add_argument(
        "--tiers",
        nargs="*",
        choices=["core", "extended"],
        help="Select the RQ-sufficient core tier or optional extended experiments.",
    )
    parser.add_argument("--flows", nargs="*", help="Two-digit flow numbers. Defaults to all 13 flows.")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--execute", action="store_true", help="Execute subprocesses that may call paid APIs.")
    parser.add_argument("--force", action="store_true", help="Replace existing experiment outputs.")
    parser.add_argument(
        "--cost-ceiling-usd",
        type=float,
        default=None,
        help="Required for paid execution; must cover the selected upper-bound estimate.",
    )
    parser.add_argument(
        "--manifest-out",
        type=Path,
        default=None,
        help="Preflight manifest path. Defaults to a config-specific file under the output root.",
    )
    return parser.parse_args()


def load_config(path: Path, *, _seen: set[Path] | None = None) -> dict[str, Any]:
    path = path.resolve()
    seen = set() if _seen is None else set(_seen)
    if path in seen:
        raise ValueError(f"Cyclic experiment config inheritance involving {path}.")
    seen.add(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "thesis_final_experiments_v1":
        raise ValueError(f"Unsupported experiment config schema in {path}.")
    parent = payload.get("extends")
    if parent:
        parent_path = Path(str(parent))
        if not parent_path.is_absolute():
            parent_path = BASE_DIR / parent_path
        inherited = load_config(parent_path, _seen=seen)
        payload = {**inherited, **payload}
    return payload


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def repository_state() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "git_commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "git_dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
        "python_version": platform.python_version(),
        "google_genai_version": package_version("google-genai"),
        "platform": platform.platform(),
    }


def artifact_manifest(config: dict[str, Any]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for relative_path in config.get("reporting_compliance", {}).get("artifact_files", []):
        path = BASE_DIR / str(relative_path)
        if not path.is_file():
            raise FileNotFoundError(f"Configured reporting artifact does not exist: {relative_path}")
        entries.append({"path": str(relative_path), "sha256": sha256(path)})
    return entries


def benchmark_files(config: dict[str, Any]) -> list[Path]:
    pattern = str(config["benchmark"]["flow_glob"])
    paths = sorted(GOLD_ROOT.glob(pattern))
    excluded = tuple(config["benchmark"].get("exclude_flow_prefixes") or [])
    paths = [path for path in paths if not path.parent.name.startswith(excluded)]
    expected = int(config["benchmark"]["expected_flows"])
    if len(paths) != expected:
        raise ValueError(f"Expected {expected} benchmark flows, found {len(paths)}.")
    return paths


def benchmark_manifest(config: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    entries: list[dict[str, Any]] = []
    requirement_ids: set[str] = set()
    for path in benchmark_files(config):
        payload = json.loads(path.read_text(encoding="utf-8"))
        flow_id = str(payload.get("flow_id") or path.parent.name)
        if flow_id.startswith("pure_"):
            raise ValueError(f"PURE item leaked into the Mind2Web benchmark: {flow_id}")
        items = payload.get("items") or []
        for item in items:
            key = f"{flow_id}::{item.get('requirement_id')}"
            if key in requirement_ids:
                raise ValueError(f"Duplicate benchmark requirement key: {key}")
            requirement_ids.add(key)
        flow_dir = FLOW_ROOT / flow_id
        screenshots = sorted((flow_dir / "original").glob("step_*.png")) or sorted(flow_dir.glob("step_*.png"))
        if not screenshots:
            raise FileNotFoundError(f"No screenshots found for {flow_id}.")
        entries.append(
            {
                "flow_id": flow_id,
                "gold_path": str(path.relative_to(BASE_DIR)),
                "gold_sha256": sha256(path),
                "requirements": len(items),
                "screenshots": len(screenshots),
            }
        )
    expected_items = int(config["benchmark"]["expected_requirements"])
    if len(requirement_ids) != expected_items:
        raise ValueError(f"Expected {expected_items} unique requirements, found {len(requirement_ids)}.")
    return entries, len(requirement_ids)


def estimate(
    experiment: dict[str, Any], config: dict[str, Any], *, flow_fraction: float = 1.0
) -> dict[str, Any]:
    tokens = experiment["estimated_tokens"]
    input_lower = math.ceil(int(tokens["input_lower"]) * flow_fraction)
    input_upper = math.ceil(int(tokens["input_upper"]) * flow_fraction)
    output_lower = math.ceil(int(tokens["output_thinking_lower"]) * flow_fraction)
    output_upper = math.ceil(int(tokens["output_thinking_upper"]) * flow_fraction)
    model = experiment.get("model")
    if not model:
        cost_lower = cost_upper = 0.0
    else:
        pricing = config["pricing_usd_per_1m_tokens"][model]
        cost_lower = (
            input_lower * float(pricing["input"])
            + output_lower * float(pricing["output_including_thinking"])
        ) / 1_000_000
        cost_upper = (
            input_upper * float(pricing["input"])
            + output_upper * float(pricing["output_including_thinking"])
        ) / 1_000_000
    return {
        "input_tokens": {"lower": input_lower, "upper": input_upper},
        "output_and_thinking_tokens": {"lower": output_lower, "upper": output_upper},
        "total_tokens": {
            "lower": input_lower + output_lower,
            "upper": input_upper + output_upper,
        },
        "estimated_cost_usd": {"lower": round(cost_lower, 4), "upper": round(cost_upper, 4)},
        "basis": "Ranges extrapolated from complete Gemini runs and scaled by the selected fraction of 13 flows.",
    }


def command_for(
    experiment: dict[str, Any],
    flow: dict[str, Any],
    config: dict[str, Any],
    *,
    force: bool = False,
) -> list[str]:
    common = config["common"]
    experiment_id = str(experiment["id"])
    flow_id = str(flow["flow_id"])
    gold = BASE_DIR / str(flow["gold_path"])
    output_dir = OUTPUT_ROOT / experiment_id
    output = output_dir / f"{flow_id}.json"
    cache = output_dir / "cache" / f"{flow_id}.json"
    command = [
        sys.executable,
        str(BASE_DIR / "scripts/run_verification_pipeline.py"),
        "--flow-dir", str(FLOW_ROOT / flow_id),
        "--image-variant", str(common["image_variant"]),
        "--requirements", str(gold),
        "--requirements-source", "benchmark",
        "--out", str(output),
        "--retriever", str(common["retriever"]),
        "--top-k", str(common["top_k"]),
        "--max-claims", str(common["max_claims"]),
        "--no-llm-claim-fallback",
    ]
    claim_policy = str(experiment["claim_policy"])
    if claim_policy == "disabled":
        command.extend(["--no-claims", "--claim-decomposition-policy", "disabled"])
    else:
        command.extend(["--claims", "--claim-decomposition-policy", claim_policy])

    if experiment["verifier"] == "deterministic":
        command.extend(["--verifier", "deterministic"])
        return command

    if experiment["verifier"] == "openrouter-qwen":
        command = [
            sys.executable,
            str(BASE_DIR / "scripts/run_openrouter_qwen_baseline.py"),
            "--source-dir",
            str(OUTPUT_ROOT / str(experiment["source_experiment"])),
            "--output-dir",
            str(output_dir),
            "--flow-id-regex",
            f"^{re.escape(flow_id)}$",
            "--model",
            str(experiment["model"]),
            "--max-attempts",
            str(experiment.get("max_attempts", 2)),
            "--cost-ceiling-usd",
            str(experiment.get("per_flow_cost_ceiling_usd", 0.02)),
        ]
        if force:
            command.append("--force")
        return command

    evidence_strategy = str(experiment["evidence_strategy"])
    execution_mode = "single-call" if evidence_strategy == "all" else "batched-topk"
    thinking_level = experiment.get("thinking_level", common.get("thinking_level"))
    thinking_budget = experiment.get("thinking_budget")
    max_group_claims = experiment.get("max_group_claims")
    if max_group_claims is None:
        max_group_claims = -1 if evidence_strategy == "all" else common["max_topk_group_claims"]
    if thinking_level is not None and thinking_budget is not None:
        raise ValueError(f"Experiment {experiment_id} configures both thinking level and thinking budget.")
    command.extend(
        [
            "--verifier", "gemini-image",
            "--execution-mode", execution_mode,
            "--verifier-model", str(experiment["model"]),
            "--verifier-temperature", str(common["temperature"]),
            "--max-verifier-images", str(common["top_k"]),
            "--max-verifier-group-images", "-1" if evidence_strategy == "all" else str(common["top_k"]),
            "--max-verifier-group-claims", str(max_group_claims),
            "--gemini-max-retries", str(common["gemini_max_retries"]),
            "--max-gemini-api-calls", "-1",
            "--claim-workers", "1",
            "--verifier-cache", str(cache),
            "--verifier-max-output-tokens", str(common["max_output_tokens"]),
        ]
    )
    if thinking_level is not None:
        command.extend(["--verifier-thinking-level", str(thinking_level)])
    if thinking_budget is not None:
        command.extend(["--verifier-thinking-budget", str(thinking_budget)])
    if common.get("predict_ui_evaluability"):
        command.append("--verifier-predict-ui-evaluability")
    if not common.get("sequence_context", True):
        command.append("--no-sequence-context")
    return command


def selected_experiments(config: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    experiments = list(config["experiments"])
    if args.experiments:
        requested = set(args.experiments)
        known = {str(item["id"]) for item in experiments}
        unknown = requested - known
        if unknown:
            raise ValueError(f"Unknown experiment IDs: {', '.join(sorted(unknown))}")
        experiments = [item for item in experiments if item["id"] in requested]
    if args.groups:
        groups = set(args.groups)
        experiments = [item for item in experiments if item["group"] in groups]
    if args.tiers:
        tiers = set(args.tiers)
        experiments = [item for item in experiments if item["tier"] in tiers]
    if not experiments:
        raise ValueError("No experiments selected.")
    return experiments


def run_one(command: list[str], output: Path, *, force: bool) -> dict[str, Any]:
    if output.exists() and not force:
        return {"status": "existing", "output": str(output)}
    result = subprocess.run(command, cwd=BASE_DIR, text=True, capture_output=True, check=False)
    return {
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
    config_path = args.config.resolve()
    config = load_config(config_path)
    flows, requirement_count = benchmark_manifest(config)
    if args.flows:
        requested_flows = set(args.flows)
        flows = [flow for flow in flows if str(flow["flow_id"])[:2] in requested_flows]
        missing = requested_flows - {str(flow["flow_id"])[:2] for flow in flows}
        if missing:
            raise ValueError(f"Unknown flow numbers: {', '.join(sorted(missing))}")
    experiments = selected_experiments(config, args)
    flow_fraction = len(flows) / int(config["benchmark"]["expected_flows"])
    estimates = {
        str(item["id"]): estimate(item, config, flow_fraction=flow_fraction)
        for item in experiments
    }
    upper_cost = sum(value["estimated_cost_usd"]["upper"] for value in estimates.values())
    lower_cost = sum(value["estimated_cost_usd"]["lower"] for value in estimates.values())
    total_tokens_lower = sum(value["total_tokens"]["lower"] for value in estimates.values())
    total_tokens_upper = sum(value["total_tokens"]["upper"] for value in estimates.values())

    commands: list[dict[str, Any]] = []
    for experiment in experiments:
        for flow in flows:
            command = command_for(experiment, flow, config, force=args.force)
            commands.append(
                {
                    "experiment_id": experiment["id"],
                    "flow_id": flow["flow_id"],
                    "output": str(OUTPUT_ROOT / str(experiment["id"]) / f"{flow['flow_id']}.json"),
                    "command": command,
                }
            )

    manifest = {
        "schema_version": "thesis_final_preflight_manifest_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "prepared_not_executed" if not args.execute else "execution_requested",
        "config_path": str(config_path.relative_to(BASE_DIR)),
        "config_sha256": sha256(config_path),
        "resolved_config_sha256": hashlib.sha256(
            json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "repository_state": repository_state(),
        "research_questions": config["research_questions"],
        "label_schema": config["label_schema"],
        "reporting_compliance": config["reporting_compliance"],
        "postprocessing_experiments": config.get("postprocessing_experiments", []),
        "artifact_manifest": artifact_manifest(config),
        "benchmark": {
            "requirements": requirement_count,
            "all_expected_requirements": config["benchmark"]["expected_requirements"],
            "flows": flows,
        },
        "selected_experiments": [
            {**experiment, "estimate": estimates[str(experiment["id"])]} for experiment in experiments
        ],
        "selection_totals": {
            "experiments": len(experiments),
            "flow_commands": len(commands),
            "total_tokens": {"lower": total_tokens_lower, "upper": total_tokens_upper},
            "estimated_cost_usd": {"lower": round(lower_cost, 4), "upper": round(upper_cost, 4)},
            "recommended_cost_ceiling_usd_with_30_percent_retry_reserve": round(upper_cost * 1.3, 2),
        },
        "commands": commands,
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path = args.manifest_out
    if manifest_path is None:
        manifest_path = OUTPUT_ROOT / f"{config_path.stem}_preflight_manifest.json"
    elif not manifest_path.is_absolute():
        manifest_path = BASE_DIR / manifest_path
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Prepared {manifest_path}")
    print(
        f"experiments={len(experiments)} flows={len(flows)} commands={len(commands)} "
        f"tokens={total_tokens_lower}-{total_tokens_upper} "
        f"estimated_cost_usd={lower_cost:.2f}-{upper_cost:.2f}"
    )
    if not args.execute:
        return

    paid = any(experiment.get("model") for experiment in experiments)
    if paid and args.cost_ceiling_usd is None:
        raise SystemExit("Paid execution requires --cost-ceiling-usd.")
    if paid and float(args.cost_ceiling_usd) < upper_cost:
        raise SystemExit(
            f"Cost ceiling ${args.cost_ceiling_usd:.2f} is below the selected upper estimate ${upper_cost:.2f}."
        )
    env_text = ""
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        env_text = env_path.read_text(encoding="utf-8")
    selected_verifiers = {str(experiment.get("verifier")) for experiment in experiments}
    if "gemini-image" in selected_verifiers:
        gemini_available = bool(os.environ.get("GEMINI_API_KEY")) or bool(
            re.search(r"(?m)^\s*GEMINI_API_KEY\s*=", env_text)
        )
        if not gemini_available:
            raise SystemExit("GEMINI_API_KEY is not available in the environment or project .env file.")
    if "openrouter-qwen" in selected_verifiers:
        openrouter_available = bool(os.environ.get("OPENROUTER_API_KEY")) or bool(
            re.search(r"(?m)^\s*OPENROUTER_API_KEY\s*=", env_text)
        )
        if not openrouter_available:
            raise SystemExit(
                "OPENROUTER_API_KEY is not available in the environment or project .env file."
            )

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {}
        for item in commands:
            output = Path(str(item["output"]))
            output.parent.mkdir(parents=True, exist_ok=True)
            future = executor.submit(run_one, item["command"], output, force=args.force)
            futures[future] = item
        for future in as_completed(futures):
            item = futures[future]
            result = {**item, **future.result()}
            results.append(result)
            print(f"{item['experiment_id']} {item['flow_id']}: {result['status']}", flush=True)

    results.sort(key=lambda item: (str(item["experiment_id"]), str(item["flow_id"])))
    result_path = OUTPUT_ROOT / "orchestration_results.json"
    result_path.write_text(
        json.dumps(
            {
                "schema_version": "thesis_final_orchestration_results_v1",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "manifest_sha256": sha256(manifest_path),
                "results": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    failures = [result for result in results if result["status"] == "failed"]
    if failures:
        raise SystemExit(f"{len(failures)} flow command(s) failed. See {result_path}.")


if __name__ == "__main__":
    main()
