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
    monkeypatch.setattr(api_app, "VERIFICATION_PIPELINE_RUNS_ROOT", generated_root / "verification_pipeline_runs")
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
    _write_json(generated_root / "verification_pipeline_runs" / f"{flow_id}_gemini25_single_call.json", payload)
    nested_payload = {
        **payload,
        "results": [
            {
                "requirement_id": "REQ-1",
                "final_label": "FULFILLED",
                "claims": [
                    {
                        "status": "SUPPORTED",
                        "evidence": [
                            {
                                "step_index": 1,
                                "bbox": [1, 2, 10, 12],
                            }
                        ],
                    }
                ],
            }
        ],
    }
    _write_json(
        generated_root / "verification_pipeline_runs" / "bbox_topk_package" / f"{flow_id}.json",
        nested_payload,
    )
    _write_json(
        generated_root / "verification_pipeline_runs" / "bbox_topk_package" / "active" / f"{flow_id}.json",
        nested_payload,
    )
    _write_json(
        generated_root / "verification_pipeline_runs" / f"{flow_id}_invalid.json",
        {**payload, "metadata": {**payload["metadata"], "run_valid": False}},
    )
    _write_json(generated_root / "diagnosis_strict_gemini_flash_lite" / "metrics_with_claims.json", {"label_metrics": {}})

    runs = api_app.discover_pipeline_runs(flow_id)

    sources = {run["source"] for run in runs}
    assert "diagnosis_strict_aggregation_noapi" in sources
    assert "diagnosis_strict_gemini_flash_lite" in sources
    assert "benchmark_coverage_gemini_flash_lite" in sources
    assert "demo_verification" in sources
    assert "verification_pipeline_runs" in sources
    assert all(not run["path"].endswith("_invalid.json") for run in runs)
    assert any(run["metrics_available"] for run in runs if run["source"] == "diagnosis_strict_gemini_flash_lite")
    assert all(run["requirements_count"] == 1 for run in runs)
    packaged = [run for run in runs if run["source"] == "bbox_topk_package"]
    assert len(packaged) == 1
    assert packaged[0]["has_pipeline_evidence"] is True
    assert packaged[0]["evidence_count"] == 1
    assert packaged[0]["has_bbox_evidence"] is True
    assert packaged[0]["bbox_evidence_count"] == 1


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


def test_rephrase_claim_uses_text_llm_role(monkeypatch) -> None:
    calls = []

    def fake_run_text_json_llm(prompt: str, **kwargs):
        calls.append((prompt, kwargs))
        return '{"claim_text": "The checkout flow supports billing information reuse."}'

    monkeypatch.setattr(api_app, "run_text_json_llm", fake_run_text_json_llm)
    body = api_app.RephraseClaimRequest(
        requirement_text="The checkout flow shall allow copying passholder information into billing information.",
        claim_text="The checkout UI provides a visible copy control.",
        feedback="Remove UI wording.",
    )

    result = api_app.rephrase_claim(body)

    assert result == {"claim_text": "The checkout flow supports billing information reuse."}
    assert calls
    assert calls[0][1]["role"] == "claim_rephrase"
    assert calls[0][1]["model_name"] == "deepseek-chat"
    assert "Do not use, infer from, or refer to screenshots" in calls[0][0]


def test_pipeline_decomposed_claims_uses_deepseek_rule_guided_decomposition(monkeypatch) -> None:
    calls = []

    class FakeEvaluability:
        value = "UI_VERIFIABLE"

    class FakeClaim:
        claim_text = "The checkout flow supports billing information reuse."

    class FakeResult:
        claims = [
            type("EnumClaim", (), {"claim_text": "The checkout flow supports billing information reuse.", "ui_evaluability": FakeEvaluability()})(),
            type("StringClaim", (), {"claim_text": "The billing reuse is persisted.", "ui_evaluability": "NOT_UI_VERIFIABLE"})(),
        ]

    def fake_decompose_requirement_with_diagnostics(requirement_text: str, **kwargs):
        calls.append((requirement_text, kwargs))
        return FakeResult()

    monkeypatch.setattr(api_app, "decompose_requirement_with_diagnostics", fake_decompose_requirement_with_diagnostics)

    claims = api_app._pipeline_decomposed_claims("The checkout flow shall support billing information reuse.", max_claims=4)

    assert claims == [
        ("The checkout flow supports billing information reuse.", True),
        ("The billing reuse is persisted.", False),
    ]
    assert calls
    assert calls[0][1]["strategy"] == "rule_guided_llm"
    assert calls[0][1]["provider"] == "deepseek"
    assert calls[0][1]["model_name"] == "deepseek-chat"


def test_decompose_claims_endpoint_uses_pipeline_claims(monkeypatch) -> None:
    monkeypatch.setattr(
        api_app,
        "_pipeline_decomposed_claims",
        lambda requirement_text, *, max_claims: [
            ("The checkout flow supports billing information reuse.", True),
            ("The billing information reuse is persisted.", False),
        ],
    )

    result = api_app.decompose_claims(
        api_app.DecomposeClaimsRequest(
            requirement_text="The checkout flow shall support billing information reuse.",
            max_claims=4,
        )
    )

    assert result["provider"] == "deepseek"
    assert result["model_name"] == "deepseek-chat"
    assert result["claims"][0]["claim"] == "The checkout flow supports billing information reuse."
    assert result["claims"][0]["claim_type"] == "OBSERVABLE"
    assert result["claims"][1]["claim_type"] == "HIDDEN"


def test_regenerate_expected_claims_preserves_manual_decisions(tmp_path: Path, monkeypatch) -> None:
    flow_id = "01_demo_flow"
    verification_gold_root = tmp_path / "data" / "annotations" / "verification_gold"
    monkeypatch.setattr(api_app, "VERIFICATION_GOLD_ROOT", verification_gold_root)
    monkeypatch.setattr(
        api_app,
        "_pipeline_decomposed_claims",
        lambda requirement_text, *, max_claims: [("The system presents an order summary including subtotal and total.", True)],
    )
    _write_json(
        verification_gold_root / flow_id / "verification_gold.json",
        {
            "dataset": "mind2web",
            "flow_id": flow_id,
            "items": [
                {
                    "requirement_id": "REQ-01",
                    "flow_id": flow_id,
                    "text": "The system shall present an order summary including subtotal and total.",
                    "scope": "single_screen",
                    "step_indices": [1],
                    "ui_evaluability": "UI_VERIFIABLE",
                    "verification_label": "FULFILLED",
                    "claims": [
                        {
                            "claim": "The screenshot shows an old order summary.",
                            "status": "SUPPORTED",
                            "claim_type": "OBSERVABLE",
                            "importance": "CORE",
                            "evidence_steps": [1],
                            "evidence_units": [{"step_index": 1, "evidence_type": "screen"}],
                        }
                    ],
                    "evidence_steps": [1],
                    "evidence_units": [{"step_index": 1, "evidence_type": "screen"}],
                    "review_status": "accepted",
                    "created_at": "2026-01-01T00:00:00+00:00",
                }
            ],
        },
    )

    result = api_app.regenerate_expected_claims_for_flow(
        flow_id,
        max_claims=4,
        preserve_existing_decisions=True,
    )

    item = result["items"][0]
    assert result["changed_item_count"] == 1
    assert item["claims"][0]["claim"] != "The screenshot shows an old order summary."
    assert "screenshot" not in item["claims"][0]["claim"].lower()
    assert item["claims"][0]["status"] == "SUPPORTED"
    assert item["claims"][0]["evidence_steps"] == [1]
