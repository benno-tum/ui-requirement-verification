from __future__ import annotations

import argparse
import base64
from io import BytesIO
import json
import os
from pathlib import Path
import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional for direct CLI use.
    load_dotenv = None

from run_smolvlm_open_baseline import (
    BASE_DIR,
    _groups,
    _parse_predictions,
    _prompt,
    _result,
    _sha256,
)


MODEL = "qwen/qwen3-vl-8b-instruct"
PROMPT_VERSION = "OPENROUTER_QWEN3VL_RAW_TOP4_SHARED_GROUP_V1"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the open-weight Qwen3-VL baseline through OpenRouter."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=BASE_DIR / "data/generated/thesis_final_experiments/fl_raw_top4",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BASE_DIR / "data/generated/thesis_final_experiments/qwen3vl8b_openrouter_raw_top4",
    )
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    parser.add_argument("--max-output-tokens", type=int, default=1600)
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--image-longest-edge", type=int, default=1600)
    parser.add_argument("--jpeg-quality", type=int, default=88)
    parser.add_argument("--flow-id-regex", default=r"^[0-9]{2}_")
    parser.add_argument("--max-groups", type=int, default=None)
    parser.add_argument("--cost-ceiling-usd", type=float, default=1.0)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def _image_data_url(path: Path, *, longest_edge: int, jpeg_quality: int) -> str:
    with Image.open(path) as opened:
        image = opened.convert("RGB")
        scale = min(1.0, longest_edge / max(image.size))
        if scale < 1.0:
            image = image.resize(
                (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
                Image.Resampling.LANCZOS,
            )
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=jpeg_quality, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _content(
    group: dict[str, Any],
    screenshot_paths: dict[int, Path],
    prompt: str,
    *,
    longest_edge: int,
    jpeg_quality: int,
) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [
        {"type": "text", "text": "The following images are an ordered UI flow."}
    ]
    for step in group["attached_steps"]:
        content.append({"type": "text", "text": f"Screenshot step {step}:"})
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": _image_data_url(
                        screenshot_paths[step],
                        longest_edge=longest_edge,
                        jpeg_quality=jpeg_quality,
                    )
                },
            }
        )
    content.append({"type": "text", "text": prompt})
    return content


def _post(api_key: str, payload: dict[str, Any], *, timeout_seconds: int = 300) -> dict[str, Any]:
    request = Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Title": "TUM UI Requirement Verification Thesis",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            value = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {body[:1000]}") from exc
    except URLError as exc:
        raise RuntimeError(f"OpenRouter network error: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("OpenRouter response was not a JSON object")
    return value


def _response_text(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("response has no choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise ValueError("response has no message")
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(item.get("text") or "")
            for item in content
            if isinstance(item, dict)
        )
    raise ValueError("response message has no text content")


def main() -> None:
    args = parse_args()
    if load_dotenv is not None:
        load_dotenv(BASE_DIR / ".env")
    api_key = os.getenv(args.api_key_env)
    if not api_key:
        raise RuntimeError(
            f"{args.api_key_env} is not set. Create an OpenRouter key and expose it only as an environment variable."
        )
    if not (384 <= args.image_longest_edge <= 4096):
        raise ValueError("image-longest-edge must be between 384 and 4096")
    if not (1 <= args.jpeg_quality <= 100):
        raise ValueError("jpeg-quality must be between 1 and 100")
    if args.cost_ceiling_usd <= 0:
        raise ValueError("cost-ceiling-usd must be positive")

    pattern = re.compile(args.flow_id_regex)
    source_paths = sorted(
        path for path in args.source_dir.glob("*.json") if pattern.match(path.stem)
    )
    if not source_paths:
        raise ValueError(f"no source files found in {args.source_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = args.output_dir / "raw_responses"
    raw_dir.mkdir(parents=True, exist_ok=True)
    accumulated_cost = 0.0

    for source_path in source_paths:
        output_path = args.output_dir / source_path.name
        if output_path.exists() and not args.force:
            print(f"{source_path.stem}: exists")
            continue
        source = json.loads(source_path.read_text(encoding="utf-8"))
        groups = _groups(source)
        if args.max_groups is not None:
            groups = groups[: args.max_groups]
        screens = source.get("screen_representations", [])
        screenshot_paths = {
            int(item["step_index"]): Path(item["screenshot_path"]) for item in screens
        }
        summaries = {
            int(item["step_index"]): str(item.get("screen_summary") or item.get("visible_text") or "")
            for item in screens
        }
        predictions: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = {}
        raw_records: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        calls = 0
        total_runtime = 0.0
        prompt_tokens = 0
        completion_tokens = 0

        for group in groups:
            if accumulated_cost >= args.cost_ceiling_usd:
                raise RuntimeError(
                    f"local cost guard reached ${accumulated_cost:.4f}; refusing another request"
                )
            prompt = _prompt(group, summaries)
            parsed: dict[str, dict[str, Any]] = {}
            errors: list[str] = []
            for attempt in range(1, args.max_attempts + 1):
                payload = {
                    "model": args.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": _content(
                                group,
                                screenshot_paths,
                                prompt,
                                longest_edge=args.image_longest_edge,
                                jpeg_quality=args.jpeg_quality,
                            ),
                        }
                    ],
                    "temperature": 0,
                    "max_tokens": args.max_output_tokens,
                    "response_format": {"type": "json_object"},
                    "provider": {
                        "allow_fallbacks": False,
                        "require_parameters": True,
                        "data_collection": "deny",
                    },
                }
                started = time.perf_counter()
                response = _post(api_key, payload)
                runtime = time.perf_counter() - started
                calls += 1
                total_runtime += runtime
                usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
                prompt_tokens += int(usage.get("prompt_tokens") or 0)
                completion_tokens += int(usage.get("completion_tokens") or 0)
                call_cost = float(usage.get("cost") or 0.0)
                accumulated_cost += call_cost
                text = _response_text(response)
                raw_records.append(
                    {
                        "group_id": group["group_id"],
                        "attempt": attempt,
                        "runtime_seconds": runtime,
                        "response_id": response.get("id"),
                        "model": response.get("model"),
                        "provider": response.get("provider"),
                        "usage": usage,
                        "response_text": text,
                    }
                )
                try:
                    parsed = _parse_predictions(text, group["attached_steps"])
                except (ValueError, json.JSONDecodeError) as exc:
                    errors.append(f"{type(exc).__name__}: {exc}")
                    continue
                expected = {claim["claim_id"] for claim in group["claims"]}
                if expected.issubset(parsed):
                    break
                errors.append(f"missing claims: {sorted(expected - set(parsed))}")

            for claim in group["claims"]:
                prediction = parsed.get(claim["claim_id"])
                if prediction is None:
                    prediction = {
                        "claim_id": claim["claim_id"],
                        "status": "MISSING",
                        "ui_evaluability": "UI_VERIFIABLE",
                        "evidence_steps": [],
                        "rationale": "The hosted open-weight model did not return a valid structured decision.",
                    }
                    failures.append(
                        {
                            "group_id": group["group_id"],
                            "claim_id": claim["claim_id"],
                            "errors": errors,
                        }
                    )
                predictions[claim["requirement_id"]] = (claim, prediction, group)
            print(
                f"{source_path.stem} {group['group_id']}: claims={len(group['claims'])} "
                f"parsed={len(parsed)} accumulated_cost=${accumulated_cost:.4f}"
            )

        results = [
            _result(
                claim=predictions[result["requirement_id"]][0],
                prediction=predictions[result["requirement_id"]][1],
                group=predictions[result["requirement_id"]][2],
                screenshot_paths=screenshot_paths,
                model_id=args.model,
                prompt_version=PROMPT_VERSION,
                evidence_source="qwen3vl_openrouter",
            )
            for result in source.get("results", [])
            if result.get("requirement_id") in predictions
        ]
        raw_path = raw_dir / source_path.name
        raw_path.write_text(json.dumps(raw_records, indent=2, ensure_ascii=False), encoding="utf-8")
        output = {
            "flow_id": source["flow_id"],
            "screen_representations": screens,
            "results": results,
            "metadata": {
                "pipeline": "hosted_open_weight_raw_top4_baseline",
                "model_name": args.model,
                "host": "OpenRouter",
                "endpoint": ENDPOINT,
                "prompt_version": PROMPT_VERSION,
                "temperature": 0,
                "max_output_tokens": args.max_output_tokens,
                "provider_routing": {
                    "allow_fallbacks": False,
                    "require_parameters": True,
                    "data_collection": "deny",
                },
                "image_preprocessing": {
                    "longest_edge": args.image_longest_edge,
                    "format": "JPEG",
                    "quality": args.jpeg_quality,
                },
                "source_group_manifest": str(source_path),
                "source_group_manifest_sha256": _sha256(source_path),
                "bounding_boxes_requested": False,
                "grounding_candidates": None,
                "calls": calls,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "runtime_seconds": total_runtime,
                "accumulated_run_cost_usd": accumulated_cost,
                "failures": failures,
                "raw_responses_path": str(raw_path),
                "raw_responses_sha256": _sha256(raw_path),
            },
        }
        output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        print(
            f"{source_path.stem}: results={len(results)} failures={len(failures)} "
            f"calls={calls} cost=${accumulated_cost:.4f}"
        )


if __name__ == "__main__":
    main()
