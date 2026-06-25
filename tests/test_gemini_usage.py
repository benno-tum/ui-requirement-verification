from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from ui_verifier.requirements.gemini_client import _request_timeout_ms
from ui_verifier.requirements.gemini_usage import (
    estimate_cost_usd,
    extract_usage_metadata,
    record_gemini_usage,
)


def test_gemini_request_timeout_defaults_to_two_minutes(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_REQUEST_TIMEOUT_MS", raising=False)

    assert _request_timeout_ms() == 120_000


def test_gemini_request_timeout_rejects_too_small_value(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_REQUEST_TIMEOUT_MS", "500")

    with pytest.raises(ValueError, match="at least 1000"):
        _request_timeout_ms()


def test_extract_usage_metadata_from_sdk_like_response() -> None:
    response = SimpleNamespace(
        usage_metadata=SimpleNamespace(
            prompt_token_count=1000,
            candidates_token_count=200,
            thoughts_token_count=50,
            total_token_count=1250,
            cached_content_token_count=10,
        )
    )

    usage = extract_usage_metadata(response)

    assert usage == {
        "input_tokens": 1000,
        "output_tokens": 200,
        "total_tokens": 1250,
        "cached_content_tokens": 10,
        "thoughts_tokens": 50,
    }


def test_estimate_cost_usd_for_gemini_25_flash_lite() -> None:
    cost = estimate_cost_usd(
        "gemini-2.5-flash-lite",
        {"input_tokens": 1_000_000, "output_tokens": 500_000, "thoughts_tokens": 100_000},
    )

    assert cost == 0.34


def test_record_gemini_usage_writes_log_and_summary(tmp_path, monkeypatch) -> None:
    log_path = tmp_path / "usage.jsonl"
    summary_path = tmp_path / "summary.json"
    monkeypatch.setenv("GEMINI_USAGE_LOG", str(log_path))
    monkeypatch.setenv("GEMINI_USAGE_SUMMARY", str(summary_path))
    monkeypatch.setenv("GEMINI_EUR_PER_USD", "0.92")

    record_gemini_usage(
        model_name="gemini-2.5-flash",
        usage={"input_tokens": 1_000_000, "output_tokens": 1_000_000, "thoughts_tokens": 0, "total_tokens": 2_000_000},
        image_count=2,
        context={"flow_id": "flow-1", "claim_id": "REQ-1-C1"},
    )

    log_records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert len(log_records) == 1
    assert log_records[0]["estimated_cost_usd"] == 2.8
    assert log_records[0]["estimated_cost_eur"] == 2.8 * 0.92
    assert log_records[0]["context"] == {"flow_id": "flow-1", "claim_id": "REQ-1-C1"}
    assert summary["request_count"] == 1
    assert summary["estimated_cost_usd"] == 2.8
    assert summary["estimated_cost_eur"] == 2.8 * 0.92
    assert summary["models"]["gemini-2.5-flash"]["request_count"] == 1
