from __future__ import annotations

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


def run_gemini(
    prompt: str,
    image_bytes_list: List[bytes],
    model_name: str,
    temperature: float = 0.2,
    usage_context: dict[str, Any] | None = None,
) -> str:
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

    response = client.models.generate_content(
        model=model_name,
        contents=parts,
        config=types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
        ),
    )

    record_gemini_usage(
        model_name=model_name,
        usage=extract_usage_metadata(response),
        image_count=len(image_bytes_list),
        context=usage_context,
    )

    return response.text
