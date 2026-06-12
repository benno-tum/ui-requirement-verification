from __future__ import annotations

import json
from pathlib import Path

from ui_verifier.api import app as api_app


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_run_discovery_finds_diagnosis_and_demo_outputs(tmp_path: Path, monkeypatch) -> None:
    base_dir = tmp_path
    generated_root = base_dir / "data" / "generated"
    flow_id = "01_demo_flow"
    monkeypatch.setattr(api_app, "BASE_DIR", base_dir)
    monkeypatch.setattr(api_app, "GENERATED_ROOT", generated_root)
    monkeypatch.setattr(api_app, "VERIFICATION_PIPELINE_ROOT", generated_root / "verification_pipeline")
    monkeypatch.setattr(api_app, "DEMO_VERIFICATION_ROOT", generated_root / "demo_verification")

    payload = {
        "flow_id": flow_id,
        "results": [{"requirement_id": "REQ-1", "final_label": "FULFILLED", "claims": [{"status": "SUPPORTED"}]}],
        "metadata": {"verifier": "gemini-image", "verifier_model": "gemini-2.5-flash-lite", "retriever": "lexical"},
    }
    _write_json(generated_root / "diagnosis_strict_aggregation_noapi" / f"{flow_id}.json", payload)
    _write_json(generated_root / "diagnosis_strict_gemini_flash_lite" / f"{flow_id}.json", payload)
    _write_json(generated_root / "benchmark_coverage_gemini_flash_lite" / f"{flow_id}.json", payload)
    _write_json(generated_root / "demo_verification" / f"{flow_id}.json", payload)
    _write_json(generated_root / "diagnosis_strict_gemini_flash_lite" / "metrics_with_claims.json", {"label_metrics": {}})

    runs = api_app.discover_pipeline_runs(flow_id)

    sources = {run["source"] for run in runs}
    assert "diagnosis_strict_aggregation_noapi" in sources
    assert "diagnosis_strict_gemini_flash_lite" in sources
    assert "benchmark_coverage_gemini_flash_lite" in sources
    assert "demo_verification" in sources
    assert any(run["metrics_available"] for run in runs if run["source"] == "diagnosis_strict_gemini_flash_lite")
    assert all(run["requirements_count"] == 1 for run in runs)


def test_selected_run_loader_restricts_to_generated_json(tmp_path: Path, monkeypatch) -> None:
    base_dir = tmp_path
    generated_root = base_dir / "data" / "generated"
    monkeypatch.setattr(api_app, "BASE_DIR", base_dir)
    monkeypatch.setattr(api_app, "GENERATED_ROOT", generated_root)
    path = generated_root / "diagnosis" / "flow.json"
    _write_json(path, {"flow_id": "flow", "results": []})

    resolved = api_app._path_for_run_id("data/generated/diagnosis/flow.json")

    assert resolved == path.resolve()


def test_selected_run_endpoint_loads_requested_run(tmp_path: Path, monkeypatch) -> None:
    base_dir = tmp_path
    generated_root = base_dir / "data" / "generated"
    flow_id = "flow"
    monkeypatch.setattr(api_app, "BASE_DIR", base_dir)
    monkeypatch.setattr(api_app, "GENERATED_ROOT", generated_root)
    path = generated_root / "diagnosis" / "flow.json"
    _write_json(path, {"flow_id": flow_id, "results": [{"requirement_id": "REQ-1", "final_label": "FULFILLED"}]})
    monkeypatch.setattr(api_app.annotation_service, "list_verification_gold", lambda requested_flow_id: [])

    result = api_app.get_verification_pipeline_run(flow_id, "data/generated/diagnosis/flow.json")

    assert result["flow_id"] == flow_id
    assert result["results"][0]["requirement_id"] == "REQ-1"
    assert result["metadata"]["run_path"].endswith("data/generated/diagnosis/flow.json")


def test_pipeline_start_command_uses_safe_subprocess_args(tmp_path: Path, monkeypatch) -> None:
    base_dir = tmp_path
    generated_root = base_dir / "data" / "generated"
    flow_id = "01_demo_flow"
    flow_dir = base_dir / "data" / "processed" / "flows" / "mind2web" / flow_id
    requirements_dir = base_dir / "data" / "annotations" / "requirements_gold" / flow_id
    flow_dir.mkdir(parents=True)
    requirements_dir.mkdir(parents=True)
    (requirements_dir / "gold_requirements.json").write_text('{"flow_id": "01_demo_flow", "requirements": []}', encoding="utf-8")

    monkeypatch.setattr(api_app, "BASE_DIR", base_dir)
    monkeypatch.setattr(api_app, "GENERATED_ROOT", generated_root)
    monkeypatch.setattr(api_app, "REQUIREMENTS_GOLD_ROOT", base_dir / "data" / "annotations" / "requirements_gold")
    monkeypatch.setattr(api_app, "VERIFICATION_GOLD_ROOT", base_dir / "data" / "annotations" / "verification_gold")
    monkeypatch.setattr(api_app.flow_catalog, "resolve_flow", lambda requested_flow_id: ("mind2web", flow_dir))

    body = api_app.StartPipelineRunRequest(
        verifier="gemini-image",
        verifier_model="gemini-2.5-flash-lite",
        retriever="lexical",
        top_k=3,
        max_images=6,
        max_gemini_api_calls=5,
        use_cache=True,
        output_dir_name="safe_runs",
    )

    command, output_path = api_app.build_pipeline_run_command(flow_id, body, job_id="job123")

    assert isinstance(command, list)
    assert "--flow-dir" in command
    assert "--verifier" in command
    assert "--requirements-source" in command
    assert "accepted" in command
    assert "gemini-image" in command
    assert output_path == (generated_root / "safe_runs" / f"{flow_id}.json").resolve()
    assert all(";" not in part for part in command)


def test_pipeline_start_command_can_use_verification_benchmark_items(tmp_path: Path, monkeypatch) -> None:
    base_dir = tmp_path
    generated_root = base_dir / "data" / "generated"
    flow_id = "01_demo_flow"
    flow_dir = base_dir / "data" / "processed" / "flows" / "mind2web" / flow_id
    benchmark_dir = base_dir / "data" / "annotations" / "verification_gold" / flow_id
    flow_dir.mkdir(parents=True)
    benchmark_dir.mkdir(parents=True)
    _write_json(
        benchmark_dir / "verification_gold.json",
        {
            "flow_id": flow_id,
            "items": [
                {"requirement_id": "REQ-01", "text": "The page shows search."},
                {"requirement_id": "CONTR-01", "text": "The page preserves search state."},
            ],
        },
    )

    monkeypatch.setattr(api_app, "BASE_DIR", base_dir)
    monkeypatch.setattr(api_app, "GENERATED_ROOT", generated_root)
    monkeypatch.setattr(api_app, "REQUIREMENTS_GOLD_ROOT", base_dir / "data" / "annotations" / "requirements_gold")
    monkeypatch.setattr(api_app, "VERIFICATION_GOLD_ROOT", base_dir / "data" / "annotations" / "verification_gold")
    monkeypatch.setattr(api_app.flow_catalog, "resolve_flow", lambda requested_flow_id: ("mind2web", flow_dir))

    body = api_app.StartPipelineRunRequest(
        verifier="deterministic_rule_based",
        requirements_source="benchmark",
        max_gemini_api_calls=0,
        output_dir_name="benchmark_runs",
    )

    command, _ = api_app.build_pipeline_run_command(flow_id, body, job_id="job123")

    requirements_index = command.index("--requirements") + 1
    source_index = command.index("--requirements-source") + 1
    assert command[requirements_index].endswith("verification_gold/01_demo_flow/verification_gold.json")
    assert command[source_index] == "benchmark"
