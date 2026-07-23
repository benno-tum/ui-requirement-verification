from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List
import os

from ui_verifier.requirements.gemini_usage import extract_usage_metadata, record_gemini_usage


def _request_timeout_ms() -> int:
    raw = os.environ.get("GEMINI_REQUEST_TIMEOUT_MS", "120000")
    try:
        timeout_ms = int(raw)
    except ValueError as exc:
        raise ValueError("GEMINI_REQUEST_TIMEOUT_MS must be an integer.") from exc
    if timeout_ms < 1000:
        raise ValueError("GEMINI_REQUEST_TIMEOUT_MS must be at least 1000.")
    return timeout_ms


def _max_output_tokens() -> int | None:
    raw = os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("GEMINI_MAX_OUTPUT_TOKENS must be an integer.") from exc
    if value < 1:
        raise ValueError("GEMINI_MAX_OUTPUT_TOKENS must be positive.")
    return value


def _thinking_budget() -> int | None:
    raw = os.environ.get("GEMINI_THINKING_BUDGET", "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("GEMINI_THINKING_BUDGET must be an integer.") from exc
    if value < -1:
        raise ValueError("GEMINI_THINKING_BUDGET must be -1 or greater.")
    return value


def _thinking_level() -> str | None:
    raw = os.environ.get("GEMINI_THINKING_LEVEL", "").strip().lower()
    if not raw:
        return None
    if raw not in {"minimal", "low", "medium", "high"}:
        raise ValueError("GEMINI_THINKING_LEVEL must be minimal, low, medium, or high.")
    return raw


def _effective_thinking_options(
    *,
    thinking_level: str | None,
    thinking_budget: int | None,
) -> tuple[str | None, int | None]:
    if thinking_budget is not None and thinking_level is not None:
        raise ValueError("Set only one explicit thinking_budget or thinking_level.")
    if thinking_budget is not None:
        return None, thinking_budget
    if thinking_level is not None:
        return thinking_level, None
    effective_thinking_budget = _thinking_budget()
    effective_thinking_level = _thinking_level()
    if effective_thinking_budget is not None and effective_thinking_level is not None:
        raise ValueError("Set only one of GEMINI_THINKING_BUDGET and GEMINI_THINKING_LEVEL.")
    return effective_thinking_level, effective_thinking_budget


@dataclass(frozen=True)
class GeminiRunResult:
    text: str
    usage: dict[str, int]
    usage_record: dict[str, Any]


def run_gemini_with_usage(
    prompt: str,
    image_bytes_list: List[bytes],
    model_name: str,
    temperature: float = 0.2,
    usage_context: dict[str, Any] | None = None,
    thinking_level: str | None = None,
    thinking_budget: int | None = None,
    max_output_tokens: int | None = None,
) -> GeminiRunResult:
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=_request_timeout_ms()),
    )

    parts = [prompt]
    for img_bytes in image_bytes_list:
        parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))

    effective_thinking_level, effective_thinking_budget = _effective_thinking_options(
        thinking_level=thinking_level,
        thinking_budget=thinking_budget,
    )
    response = client.models.generate_content(
        model=model_name,
        contents=parts,
        config=types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
            max_output_tokens=(
                max_output_tokens if max_output_tokens is not None else _max_output_tokens()
            ),
            thinking_config=(
                types.ThinkingConfig(thinking_budget=effective_thinking_budget)
                if effective_thinking_budget is not None
                else (
                    types.ThinkingConfig(thinking_level=effective_thinking_level)
                    if effective_thinking_level is not None
                    else None
                )
            ),
        ),
    )

    usage = extract_usage_metadata(response)
    usage_record = record_gemini_usage(
        model_name=model_name,
        usage=usage,
        image_count=len(image_bytes_list),
        context=usage_context,
    )
    return GeminiRunResult(text=response.text, usage=usage, usage_record=usage_record)


def run_gemini(
    prompt: str,
    image_bytes_list: List[bytes],
    model_name: str,
    temperature: float = 0.2,
    usage_context: dict[str, Any] | None = None,
    thinking_level: str | None = None,
    thinking_budget: int | None = None,
    max_output_tokens: int | None = None,
) -> str:
    return run_gemini_with_usage(
        prompt,
        image_bytes_list,
        model_name,
        temperature=temperature,
        usage_context=usage_context,
        thinking_level=thinking_level,
        thinking_budget=thinking_budget,
        max_output_tokens=max_output_tokens,
    ).text
