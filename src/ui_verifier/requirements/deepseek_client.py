from __future__ import annotations

import json
import os
from typing import Any
from urllib import request, error

from ui_verifier.requirements.gemini_usage import record_gemini_usage


DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


def _usage_from_openai_compatible(data: dict[str, Any]) -> dict[str, int]:
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    # DeepSeek completion_tokens already includes any reasoning tokens, so do not
    # also charge reasoning_tokens as separate output in the shared estimator.
    return {
        "input_tokens": int(usage.get("prompt_tokens") or 0),
        "output_tokens": int(usage.get("completion_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
        "cached_content_tokens": int(usage.get("prompt_cache_hit_tokens") or 0),
        "thoughts_tokens": 0,
    }


def run_deepseek_json(
    prompt: str,
    *,
    model_name: str,
    temperature: float = 0.0,
    thinking: bool = False,
) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set.")

    base_url = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL).rstrip("/")
    body: dict[str, Any] = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "stream": False,
    }
    if model_name.startswith("deepseek-v4"):
        body["thinking"] = {"type": "enabled" if thinking else "disabled"}

    req = request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DeepSeek API error {exc.code}: {detail}") from exc

    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("DeepSeek response did not contain choices.")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("DeepSeek response did not contain message content.")

    record_gemini_usage(
        model_name=model_name,
        usage=_usage_from_openai_compatible(data),
        request_kind="deepseek_chat_completion",
        image_count=0,
    )
    return content
