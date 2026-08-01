from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BASE_DIR / "scripts/run_thesis_final_experiments.py"
SPEC = importlib.util.spec_from_file_location("run_thesis_final_experiments", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _config() -> dict:
    return MODULE.load_config(BASE_DIR / "configs/thesis_remaining_runs.json")


def _flow(config: dict) -> dict:
    flows, count = MODULE.benchmark_manifest(config)
    assert count == 258
    return flows[0]


def test_remaining_package_contains_only_planned_runs() -> None:
    config = _config()
    ids = {item["id"] for item in config["experiments"]}
    assert ids == {
        "fl_raw_all_r2",
        "fl_raw_all_r3",
        "fl_gated_top4_r2",
        "fl_gated_top4_r3",
        "qwen_raw_top4_r2",
        "qwen_raw_top4_r3",
        "fl_oracle_all",
        "fl_oracle_top4",
    }
    assert not any("g36" in item for item in ids)


def test_repetitions_have_distinct_output_and_cache_paths() -> None:
    config = _config()
    flow = _flow(config)
    experiments = {
        item["id"]: item
        for item in config["experiments"]
        if item["id"] in {"fl_raw_all_r2", "fl_raw_all_r3"}
    }
    commands = {
        name: MODULE.command_for(experiment, flow, config)
        for name, experiment in experiments.items()
    }
    assert commands["fl_raw_all_r2"] != commands["fl_raw_all_r3"]
    assert "fl_raw_all_r2" in " ".join(commands["fl_raw_all_r2"])
    assert "fl_raw_all_r3" in " ".join(commands["fl_raw_all_r3"])


def test_openrouter_repeat_reuses_frozen_groups_without_gemini_verification() -> None:
    config = _config()
    flow = _flow(config)
    experiment = next(
        item for item in config["experiments"] if item["id"] == "qwen_raw_top4_r2"
    )
    command = MODULE.command_for(experiment, flow, config)
    rendered = " ".join(command)
    assert "run_openrouter_qwen_baseline.py" in rendered
    assert "fl_raw_top4" in rendered
    assert "qwen_raw_top4_r2" in rendered
    assert "run_verification_pipeline.py" not in rendered
    assert "GEMINI_API_KEY" not in rendered
    assert "OPENROUTER_API_KEY" not in rendered


def test_oracle_runs_use_provided_claims_and_are_extended() -> None:
    config = _config()
    oracle = [
        item for item in config["experiments"] if item["group"] == "oracle_optional"
    ]
    assert len(oracle) == 2
    assert all(item["claim_policy"] == "provided" for item in oracle)
    assert all(item["tier"] == "extended" for item in oracle)


def test_order_ablation_is_matched_to_raw_all_and_passes_destroyed_chronology() -> None:
    config = MODULE.load_config(BASE_DIR / "configs/thesis_final_experiments.json")
    flow = _flow(config)
    experiment = next(
        item
        for item in config["experiments"]
        if item["id"] == "fl_raw_all_chronology_destroyed"
    )
    command = MODULE.command_for(experiment, flow, config)
    rendered = " ".join(command)

    assert experiment["matched_baseline"] == "fl_raw_all"
    assert experiment["model"] == "gemini-3.1-flash-lite"
    assert experiment["claim_policy"] == "disabled"
    assert experiment["evidence_strategy"] == "all"
    assert "--verifier-chronology-mode destroyed" in rendered
    assert "--verifier-order-seed 20260726" in rendered


def test_low_cost_order_ablation_matches_gemini_25_baseline() -> None:
    config = MODULE.load_config(BASE_DIR / "configs/thesis_final_experiments.json")
    flow = _flow(config)
    experiment = next(
        item
        for item in config["experiments"]
        if item["id"] == "g25_raw_all_chronology_destroyed"
    )
    command = MODULE.command_for(experiment, flow, config)
    rendered = " ".join(command)

    assert experiment["matched_baseline"] == "g25_raw_all"
    assert experiment["model"] == "gemini-2.5-flash-lite"
    assert experiment["thinking_budget"] == 0
    assert "--verifier-chronology-mode destroyed" in rendered
    assert "--verifier-thinking-budget 0" in rendered
    assert "--verifier-thinking-level" not in rendered
