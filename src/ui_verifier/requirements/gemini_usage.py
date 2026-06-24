from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import os
import threading


# Values are USD per 1M tokens. Keep this table explicit so cost estimates are auditable.
# Gemini prices: https://ai.google.dev/gemini-api/docs/pricing
# DeepSeek prices: https://api-docs.deepseek.com/quick_start/pricing
MODEL_PRICING_USD_PER_1M: dict[str, dict[str, float]] = {
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "gemini-2.5-flash-lite-preview": {"input": 0.10, "output": 0.40},
    "gemini-2.5-flash-lite-preview-09-2025": {"input": 0.10, "output": 0.40},
    "gemini-3.1-flash-lite": {"input": 0.25, "output": 1.50},
    "gemini-3.5-flash": {"input": 1.50, "output": 9.00},
    "deepseek-v4-flash": {"input": 0.14, "output": 0.28},
    "deepseek-v4-pro": {"input": 1.74, "output": 3.48},
}

DEFAULT_USAGE_LOG_PATH = Path("data/generated/gemini_usage/usage.jsonl")
DEFAULT_USAGE_SUMMARY_PATH = Path("data/generated/gemini_usage/summary.json")
_USAGE_WRITE_LOCK = threading.Lock()


def usage_log_path() -> Path:
    return Path(os.environ.get("GEMINI_USAGE_LOG", DEFAULT_USAGE_LOG_PATH)).expanduser()


def usage_summary_path() -> Path:
    return Path(os.environ.get("GEMINI_USAGE_SUMMARY", DEFAULT_USAGE_SUMMARY_PATH)).expanduser()


def _int_attr(obj: Any, name: str) -> int:
    value = getattr(obj, name, None)
    if value is None and isinstance(obj, dict):
        value = obj.get(name)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def extract_usage_metadata(response: Any) -> dict[str, int]:
    metadata = getattr(response, "usage_metadata", None)
    if metadata is None:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cached_content_tokens": 0,
            "thoughts_tokens": 0,
        }

    input_tokens = _int_attr(metadata, "prompt_token_count")
    output_tokens = _int_attr(metadata, "candidates_token_count")
    thoughts_tokens = _int_attr(metadata, "thoughts_token_count")
    total_tokens = _int_attr(metadata, "total_token_count")
    cached_tokens = _int_attr(metadata, "cached_content_token_count")

    if not total_tokens:
        total_tokens = input_tokens + output_tokens + thoughts_tokens

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cached_content_tokens": cached_tokens,
        "thoughts_tokens": thoughts_tokens,
    }


def _pricing_for_model(model_name: str) -> dict[str, float] | None:
    if model_name in MODEL_PRICING_USD_PER_1M:
        return MODEL_PRICING_USD_PER_1M[model_name]

    # Versioned aliases often append a date suffix. Use the stable family price if known.
    for known_model, pricing in MODEL_PRICING_USD_PER_1M.items():
        if model_name.startswith(f"{known_model}-"):
            return pricing
    return None


def estimate_cost_usd(model_name: str, usage: dict[str, int]) -> float | None:
    pricing = _pricing_for_model(model_name)
    if pricing is None:
        return None

    input_cost = usage.get("input_tokens", 0) * pricing["input"] / 1_000_000
    output_cost = usage.get("output_tokens", 0) * pricing["output"] / 1_000_000
    # Gemini pricing says output includes thinking tokens for the models above.
    thoughts_cost = usage.get("thoughts_tokens", 0) * pricing["output"] / 1_000_000
    return input_cost + output_cost + thoughts_cost


def eur_per_usd() -> float | None:
    raw = os.environ.get("GEMINI_EUR_PER_USD")
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            records.append(parsed)
    return records


def _write_summary(records: list[dict[str, Any]], path: Path) -> None:
    totals: dict[str, Any] = {
        "request_count": len(records),
        "input_tokens": 0,
        "output_tokens": 0,
        "thoughts_tokens": 0,
        "total_tokens": 0,
        "estimated_cost_usd": 0.0,
        "estimated_cost_eur": None,
        "models": {},
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    for record in records:
        model = str(record.get("model") or "unknown")
        model_totals = totals["models"].setdefault(
            model,
            {
                "request_count": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "thoughts_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
                "estimated_cost_eur": None,
            },
        )
        usage = record.get("usage") if isinstance(record.get("usage"), dict) else {}
        cost_usd = record.get("estimated_cost_usd")
        cost_usd = float(cost_usd) if isinstance(cost_usd, (int, float)) else 0.0

        for key in ("input_tokens", "output_tokens", "thoughts_tokens", "total_tokens"):
            value = int(usage.get(key) or 0)
            totals[key] += value
            model_totals[key] += value
        totals["estimated_cost_usd"] += cost_usd
        model_totals["estimated_cost_usd"] += cost_usd
        model_totals["request_count"] += 1

    rate = eur_per_usd()
    if rate is not None:
        totals["estimated_cost_eur"] = totals["estimated_cost_usd"] * rate
        for model_totals in totals["models"].values():
            model_totals["estimated_cost_eur"] = model_totals["estimated_cost_usd"] * rate

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(totals, indent=2, ensure_ascii=False), encoding="utf-8")


def empty_usage_summary() -> dict[str, Any]:
    return {
        "request_count": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "thoughts_tokens": 0,
        "total_tokens": 0,
        "estimated_cost_usd": 0.0,
        "estimated_cost_eur": None,
        "models": {},
        "updated_at": None,
    }


def read_usage_summary() -> dict[str, Any]:
    path = usage_summary_path()
    if not path.exists():
        return empty_usage_summary()
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return empty_usage_summary()
    return parsed if isinstance(parsed, dict) else empty_usage_summary()


def record_gemini_usage(
    *,
    model_name: str,
    usage: dict[str, int],
    request_kind: str = "generate_content",
    image_count: int = 0,
) -> dict[str, Any]:
    cost_usd = estimate_cost_usd(model_name, usage)
    rate = eur_per_usd()
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_kind": request_kind,
        "model": model_name,
        "image_count": image_count,
        "usage": usage,
        "estimated_cost_usd": cost_usd,
        "estimated_cost_eur": cost_usd * rate if cost_usd is not None and rate is not None else None,
        "eur_per_usd": rate,
        "pricing_source": "https://ai.google.dev/gemini-api/docs/pricing",
    }

    with _USAGE_WRITE_LOCK:
        log_path = usage_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        _write_summary(_read_jsonl(log_path), usage_summary_path())
    return record
