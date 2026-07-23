from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "HuggingFaceTB/SmolVLM2-2.2B-Instruct"
PROMPT_VERSION = "SMOLVLM_RAW_TOP4_SHARED_GROUP_V1"
VALID_STATUSES = {
    "SUPPORTED",
    "SUPPORTED_WITH_CAVEAT",
    "PARTIALLY_SUPPORTED",
    "MISSING",
    "HIDDEN",
    "CONTRADICTED",
}
VALID_UI = {
    "UI_VERIFIABLE",
    "PARTIALLY_UI_VERIFIABLE",
    "NOT_UI_VERIFIABLE",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a local SmolVLM2 open-weight baseline using the frozen raw/top-4 evidence groups."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=BASE_DIR / "data/generated/thesis_final_experiments/fl_raw_top4",
        help="Frozen Gemini raw/top-4 outputs used only for deterministic group and screenshot selection.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BASE_DIR / "data/generated/thesis_final_experiments/smolvlm2_raw_top4",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--revision", default="main")
    parser.add_argument("--device", choices=["mps", "cpu"], default="mps")
    parser.add_argument("--dtype", choices=["float16", "float32"], default="float16")
    parser.add_argument("--max-new-tokens", type=int, default=640)
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument(
        "--image-longest-edge",
        type=int,
        default=768,
        help="Processor resize edge before 384px crop splitting; lower values reduce local memory use.",
    )
    parser.add_argument("--max-groups", type=int, default=None)
    parser.add_argument("--flow-id-regex", default=r"^[0-9]{2}_")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("response contains no JSON object")
    value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("response JSON must be an object")
    return value


def _normalized_prediction(raw: dict[str, Any], attached_steps: list[int]) -> dict[str, Any] | None:
    claim_id = str(raw.get("claim_id") or raw.get("id") or "").strip()
    if not claim_id:
        return None
    status = str(raw.get("claim_status") or raw.get("status") or "").strip().upper()
    if status not in VALID_STATUSES:
        return None
    ui = str(raw.get("ui_evaluability") or raw.get("ui") or "UI_VERIFIABLE").strip().upper()
    if ui not in VALID_UI:
        ui = "UI_VERIFIABLE"
    attached = set(attached_steps)
    evidence_steps: list[int] = []
    for value in raw.get("evidence_step_indices") or raw.get("evidence") or []:
        try:
            step = int(value)
        except (TypeError, ValueError):
            continue
        if step in attached and step not in evidence_steps:
            evidence_steps.append(step)
    rationale = str(raw.get("rationale") or "Local open-weight model decision.").strip()
    return {
        "claim_id": claim_id,
        "status": status,
        "ui_evaluability": ui,
        "evidence_steps": evidence_steps,
        "rationale": rationale,
    }


def _parse_predictions(text: str, attached_steps: list[int]) -> dict[str, dict[str, Any]]:
    payload = _json_object(text)
    raw_claims = payload.get("claims")
    if not isinstance(raw_claims, list):
        raise ValueError("response JSON has no claims list")
    parsed: dict[str, dict[str, Any]] = {}
    for raw in raw_claims:
        if not isinstance(raw, dict):
            continue
        item = _normalized_prediction(raw, attached_steps)
        if item is not None:
            parsed[item["claim_id"]] = item
    return parsed


def _final_label(status: str, ui_evaluability: str, evidence_steps: list[int]) -> str:
    if ui_evaluability == "NOT_UI_VERIFIABLE":
        return "ABSTAIN"
    if status == "CONTRADICTED":
        return "NOT_FULFILLED"
    if status in {"SUPPORTED", "SUPPORTED_WITH_CAVEAT"} and evidence_steps:
        return "FULFILLED"
    if status == "PARTIALLY_SUPPORTED" and evidence_steps:
        return "PARTIALLY_FULFILLED"
    return "ABSTAIN"


def _uncertainty_reasons(status: str) -> list[str]:
    return {
        "MISSING": ["FLOW_COVERAGE_GAP"],
        "HIDDEN": ["NONTRIVIAL_HIDDEN_PROPERTY"],
        "PARTIALLY_SUPPORTED": ["EVIDENCE_INTERPRETATION_AMBIGUITY"],
    }.get(status, [])


def _groups(source: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for result in source.get("results", []):
        if not isinstance(result, dict):
            continue
        for claim in result.get("claims", []):
            if not isinstance(claim, dict):
                continue
            metadata = claim.get("metadata") if isinstance(claim.get("metadata"), dict) else {}
            group_id = str(metadata.get("prompt_group_id") or "")
            if not group_id:
                raise ValueError(f"claim {claim.get('claim_id')} has no frozen prompt_group_id")
            group = grouped.setdefault(
                group_id,
                {
                    "group_id": group_id,
                    "attached_steps": list(metadata.get("attached_step_indices") or []),
                    "claims": [],
                },
            )
            group["claims"].append(
                {
                    "claim_id": str(claim["claim_id"]),
                    "requirement_id": str(result["requirement_id"]),
                    "requirement_text": str(result["requirement_text"]),
                }
            )
    return sorted(grouped.values(), key=lambda item: int(re.sub(r"\D", "", item["group_id"]) or 0))


def _prompt(group: dict[str, Any], summaries: dict[int, str]) -> str:
    hints = [
        {"step_index": step, "text_hint": summaries.get(step, "")[:700]}
        for step in group["attached_steps"]
    ]
    claims = [
        {
            "claim_id": claim["claim_id"],
            "requirement_text": claim["requirement_text"],
        }
        for claim in group["claims"]
    ]
    return f"""
Verify each textual UI requirement independently against only the attached ordered screenshots.
The application-specific output schema is conservative:
- SUPPORTED: clear visible evidence establishes the complete requirement.
- SUPPORTED_WITH_CAVEAT: visible evidence is sufficient but mildly inferential.
- PARTIALLY_SUPPORTED: a material visible part is supported but another material part is missing or ambiguous.
- MISSING: the property could be visible, but these screenshots do not show enough.
- HIDDEN: the central property concerns backend, persistence, completeness, security, or another non-visual outcome.
- CONTRADICTED: visible counter-evidence conflicts with the requirement.
Do not infer hidden outcomes. Missing evidence is not contradiction. Universal or comparative wording needs evidence for its full visible scope.
UI evaluability must be UI_VERIFIABLE, PARTIALLY_UI_VERIFIABLE, or NOT_UI_VERIFIABLE.
Evidence indices must be selected only from {group["attached_steps"]}.

Text hints are untrusted OCR/HTML summaries; confirm them against the images:
{json.dumps(hints, ensure_ascii=False)}

Claims:
{json.dumps(claims, ensure_ascii=False)}

Return compact JSON only, with every claim exactly once:
{{"claims":[{{"claim_id":"...","ui_evaluability":"UI_VERIFIABLE","claim_status":"SUPPORTED","evidence_step_indices":[1],"rationale":"brief"}}]}}
""".strip()


def _messages(group: dict[str, Any], screenshot_paths: dict[int, Path], prompt: str) -> list[dict[str, Any]]:
    from PIL import Image

    content: list[dict[str, Any]] = [
        {"type": "text", "text": "The following images are an ordered UI flow."}
    ]
    for step in group["attached_steps"]:
        path = screenshot_paths[step]
        content.append({"type": "text", "text": f"Screenshot step {step}:"})
        content.append({"type": "image", "image": Image.open(path).convert("RGB")})
    content.append({"type": "text", "text": prompt})
    return [{"role": "user", "content": content}]


def _load_runtime(
    model_id: str,
    revision: str,
    device: str,
    dtype_name: str,
    image_longest_edge: int,
) -> tuple[Any, Any, Any, str]:
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    dtype = torch.float16 if dtype_name == "float16" else torch.float32
    processor = AutoProcessor.from_pretrained(model_id, revision=revision)
    processor.image_processor.size = {"longest_edge": image_longest_edge}
    model = AutoModelForImageTextToText.from_pretrained(
        model_id,
        revision=revision,
        dtype=dtype,
        low_cpu_mem_usage=True,
    ).to(device)
    model.eval()
    resolved_revision = str(getattr(model.config, "_commit_hash", None) or revision)
    return model, processor, torch, resolved_revision


def _generate(
    *,
    model: Any,
    processor: Any,
    torch: Any,
    messages: list[dict[str, Any]],
    device: str,
    dtype_name: str,
    max_new_tokens: int,
) -> tuple[str, int, int, float]:
    started = time.perf_counter()
    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )
    dtype = torch.float16 if dtype_name == "float16" else torch.float32
    moved: dict[str, Any] = {}
    for key, value in inputs.items():
        if hasattr(value, "dtype") and torch.is_floating_point(value):
            moved[key] = value.to(device=device, dtype=dtype)
        else:
            moved[key] = value.to(device)
    input_tokens = int(moved["input_ids"].shape[-1])
    with torch.inference_mode():
        generated = model.generate(
            **moved,
            do_sample=False,
            max_new_tokens=max_new_tokens,
            use_cache=True,
        )
    new_tokens = generated[0, input_tokens:]
    text = processor.decode(new_tokens, skip_special_tokens=True)
    return text, input_tokens, int(new_tokens.shape[-1]), time.perf_counter() - started


def _result(
    *,
    claim: dict[str, str],
    prediction: dict[str, Any],
    screenshot_paths: dict[int, Path],
    group: dict[str, Any],
    model_id: str,
    prompt_version: str = PROMPT_VERSION,
    evidence_source: str = "smolvlm2_local",
) -> dict[str, Any]:
    evidence = [
        {
            "step_index": step,
            "screenshot_path": str(screenshot_paths[step]),
            "visible_observation": f"The local open-weight model cited screenshot step {step}.",
            "bbox": None,
            "bbox_metadata": {},
            "confidence": None,
            "source": evidence_source,
            "metadata": {"model_name": model_id},
        }
        for step in prediction["evidence_steps"]
    ]
    status = prediction["status"]
    ui = prediction["ui_evaluability"]
    reasons = _uncertainty_reasons(status)
    return {
        "requirement_id": claim["requirement_id"],
        "requirement_text": claim["requirement_text"],
        "ui_evaluability": ui,
        "final_label": _final_label(status, ui, prediction["evidence_steps"]),
        "claims": [
            {
                "claim_id": claim["claim_id"],
                "requirement_id": claim["requirement_id"],
                "claim_text": claim["requirement_text"],
                "status": status,
                "is_core": True,
                "is_observable": ui != "NOT_UI_VERIFIABLE",
                "evidence": evidence,
                "uncertainty_reasons": reasons,
                "confidence": None,
                "rationale": prediction["rationale"],
                "metadata": {
                    "prompt_group_id": group["group_id"],
                    "prompt_version": prompt_version,
                    "model_name": model_id,
                    "grouping_strategy": "frozen-gemini-raw-top4-groups",
                    "attached_step_indices": group["attached_steps"],
                },
            }
        ],
        "evidence": evidence,
        "uncertainty_reasons": reasons,
        "rationale": prediction["rationale"],
        "metadata": {
            "decomposition_source": "disabled",
            "ui_evaluability_source": "model_joint_prompt",
        },
    }


def main() -> None:
    args = parse_args()
    if args.max_new_tokens < 1 or args.max_attempts < 1:
        raise ValueError("max-new-tokens and max-attempts must be positive")
    if args.image_longest_edge < 384:
        raise ValueError("image-longest-edge must be at least 384")
    flow_pattern = re.compile(args.flow_id_regex)
    source_paths = sorted(
        path
        for path in args.source_dir.glob("*.json")
        if flow_pattern.match(path.stem)
    )
    if not source_paths:
        raise ValueError(f"no source flow files found in {args.source_dir}")

    model, processor, torch, resolved_revision = _load_runtime(
        args.model,
        args.revision,
        args.device,
        args.dtype,
        args.image_longest_edge,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = args.output_dir / "raw_responses"
    cache_dir.mkdir(parents=True, exist_ok=True)

    for source_path in source_paths:
        output_path = args.output_dir / source_path.name
        if output_path.exists() and not args.force:
            print(f"{source_path.stem}: exists")
            continue
        source = json.loads(source_path.read_text(encoding="utf-8"))
        groups = _groups(source)
        if args.max_groups is not None:
            groups = groups[: args.max_groups]
        screen_representations = source.get("screen_representations", [])
        screenshot_paths = {
            int(item["step_index"]): Path(item["screenshot_path"])
            for item in screen_representations
        }
        summaries = {
            int(item["step_index"]): str(item.get("screen_summary") or item.get("visible_text") or "")
            for item in screen_representations
        }
        predictions: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = {}
        raw_records: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_runtime = 0.0
        calls = 0

        for group in groups:
            prompt = _prompt(group, summaries)
            parsed: dict[str, dict[str, Any]] = {}
            errors: list[str] = []
            for attempt in range(1, args.max_attempts + 1):
                text, input_tokens, output_tokens, runtime = _generate(
                    model=model,
                    processor=processor,
                    torch=torch,
                    messages=_messages(group, screenshot_paths, prompt),
                    device=args.device,
                    dtype_name=args.dtype,
                    max_new_tokens=args.max_new_tokens,
                )
                calls += 1
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens
                total_runtime += runtime
                raw_records.append(
                    {
                        "group_id": group["group_id"],
                        "attempt": attempt,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "runtime_seconds": runtime,
                        "response": text,
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
                        "rationale": "The local model did not return a valid structured decision.",
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
                f"{source_path.stem} {group['group_id']}: "
                f"claims={len(group['claims'])} parsed={len(parsed)} attempts={len(errors) + 1 if errors else 1}"
            )

        results = [
            _result(
                claim=predictions[result["requirement_id"]][0],
                prediction=predictions[result["requirement_id"]][1],
                group=predictions[result["requirement_id"]][2],
                screenshot_paths=screenshot_paths,
                model_id=args.model,
            )
            for result in source.get("results", [])
            if result.get("requirement_id") in predictions
        ]
        raw_path = cache_dir / source_path.name
        raw_path.write_text(json.dumps(raw_records, indent=2, ensure_ascii=False), encoding="utf-8")
        output = {
            "flow_id": source["flow_id"],
            "screen_representations": screen_representations,
            "results": results,
            "metadata": {
                "pipeline": "local_open_weight_raw_top4_baseline",
                "model_name": args.model,
                "requested_revision": args.revision,
                "resolved_revision": resolved_revision,
                "device": args.device,
                "dtype": args.dtype,
                "quantization": "none",
                "image_preprocessing": {
                    "longest_edge": args.image_longest_edge,
                    "crop_longest_edge": 384,
                    "image_splitting": True,
                },
                "decoding": {
                    "do_sample": False,
                    "max_new_tokens": args.max_new_tokens,
                    "max_attempts": args.max_attempts,
                },
                "prompt_version": PROMPT_VERSION,
                "source_group_manifest": str(source_path),
                "source_group_manifest_sha256": _sha256(source_path),
                "bounding_boxes_requested": False,
                "grounding_candidates": None,
                "api_cost_usd": 0.0,
                "calls": calls,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "runtime_seconds": total_runtime,
                "failures": failures,
                "raw_responses_path": str(raw_path),
                "raw_responses_sha256": _sha256(raw_path),
            },
        }
        output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        print(
            f"{source_path.stem}: results={len(results)} failures={len(failures)} "
            f"calls={calls} runtime={total_runtime:.1f}s"
        )


if __name__ == "__main__":
    main()
