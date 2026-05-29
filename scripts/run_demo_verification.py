from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.generate_ocr_sidecars import OcrRunSummary, generate_ocr_sidecars
from scripts.run_verification_pipeline import _load_steps_metadata, load_requirements
from ui_verifier.common.flow_utils import find_step_images, parse_step_number
from ui_verifier.common.json_utils import parse_json_response
from ui_verifier.verification_pipeline.claim_verification import ClaimVerifier
from ui_verifier.verification_pipeline.evidence_retrieval import build_evidence_retriever
from ui_verifier.verification_pipeline.pipeline import EvidenceFirstVerificationPipeline
from ui_verifier.verification_pipeline.requirement_understanding import (
    GeminiClaimDecomposer,
    RequirementUnderstanding,
    has_hidden_indicator,
)
from ui_verifier.verification_pipeline.schemas import (
    ClaimStatus,
    ClaimVerificationResult,
    EvidenceItem,
    PipelineInput,
    PipelineOutput,
    RequirementClaim,
    ScreenshotStep,
    UIEvaluability,
    UncertaintyReason,
)


DEFAULT_FLOW_ID = "03_mbta_c094948f-afc6-415c-968a-9e105e2db118"
FALLBACK_FLOW_IDS = [
    DEFAULT_FLOW_ID,
    "08_amtrak_845fbfa9-1b98-4df4-b7c5-4c71ef3e5b1b",
    "13_yellowpages_34c474ef-389c-421d-acbf-de5531437083",
]


class DemoDataError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScreenshotSelection:
    flow_id: str
    screenshot_dir: Path
    metadata_dir: Path
    checked_paths: list[Path]


def _rel(path: Path, *, base_dir: Path = BASE_DIR) -> str:
    try:
        return str(path.resolve().relative_to(base_dir.resolve()))
    except ValueError:
        return str(path)


def _has_step_images(path: Path) -> bool:
    return path.exists() and any(path.glob("step_*.png"))


def resolve_flow_id(flow_id: str, *, base_dir: Path = BASE_DIR) -> str:
    requirements_root = base_dir / "data" / "annotations" / "requirements_gold"
    exact = requirements_root / flow_id / "gold_requirements.json"
    if exact.exists():
        return flow_id

    matches = [
        path.name
        for path in requirements_root.glob(f"{flow_id}*")
        if (path / "gold_requirements.json").exists()
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise DemoDataError(f"Flow id prefix {flow_id!r} is ambiguous: {', '.join(matches)}")
    return flow_id


def screenshot_candidate_dirs(flow_id: str, *, base_dir: Path = BASE_DIR) -> list[Path]:
    return [
        base_dir / "data" / "processed" / "flows" / "mind2web" / flow_id,
        base_dir
        / "data"
        / "generated"
        / "candidate_requirements"
        / flow_id
        / "manual_harvest_bundle"
        / "images",
    ]


def resolve_screenshot_dir(
    flow_id: str,
    *,
    base_dir: Path = BASE_DIR,
    explicit_flow_dir: Path | None = None,
) -> ScreenshotSelection:
    checked_paths = [explicit_flow_dir] if explicit_flow_dir is not None else screenshot_candidate_dirs(flow_id, base_dir=base_dir)
    checked_paths = [path for path in checked_paths if path is not None]

    for candidate in checked_paths:
        if _has_step_images(candidate):
            processed_dir = base_dir / "data" / "processed" / "flows" / "mind2web" / flow_id
            metadata_dir = processed_dir if (processed_dir / "steps.json").exists() else candidate
            return ScreenshotSelection(
                flow_id=flow_id,
                screenshot_dir=candidate,
                metadata_dir=metadata_dir,
                checked_paths=checked_paths,
            )

    checked = "\n".join(f"- {_rel(path, base_dir=base_dir)}" for path in checked_paths)
    raise DemoDataError(
        "No step_*.png screenshots found for the demo flow.\n"
        f"flow_id: {flow_id}\n"
        "Checked paths:\n"
        f"{checked}"
    )


def resolve_requirements_path(
    flow_id: str,
    *,
    base_dir: Path = BASE_DIR,
    explicit_requirements: Path | None = None,
) -> Path:
    path = explicit_requirements or (
        base_dir / "data" / "annotations" / "requirements_gold" / flow_id / "gold_requirements.json"
    )
    if not path.exists():
        raise DemoDataError(f"Requirements file does not exist: {_rel(path, base_dir=base_dir)}")
    return path


def resolve_reference_path(flow_id: str, *, base_dir: Path = BASE_DIR, explicit_reference: Path | None = None) -> Path | None:
    path = explicit_reference or (
        base_dir / "data" / "annotations" / "verification_gold" / flow_id / "verification_gold.json"
    )
    return path if path.exists() else None


def discover_demo_screenshot_steps(selection: ScreenshotSelection, *, screen_source_mode: str = "current") -> list[ScreenshotStep]:
    metadata_by_step = _load_steps_metadata(selection.metadata_dir)
    paths = sorted(find_step_images(selection.screenshot_dir), key=parse_step_number)
    steps: list[ScreenshotStep] = []
    for path in paths:
        step_index = parse_step_number(path)
        metadata = dict(metadata_by_step.get(step_index, {}))
        if screen_source_mode == "image-only":
            metadata = {
                key: value
                for key, value in metadata.items()
                if key not in {"raw_html", "pos_candidates"}
            }
        steps.append(
            ScreenshotStep(
                step_index=step_index,
                screenshot_path=str(path),
                metadata=metadata,
            )
        )
    return steps


def select_retriever_name(requested: str) -> str:
    if requested != "auto":
        return requested
    try:
        import sklearn  # noqa: F401
    except ImportError:
        return "lexical"
    return "tfidf"


def maybe_generate_ocr(
    image_paths: list[Path],
    *,
    mode: str,
    tesseract_cmd: str,
) -> OcrRunSummary | None:
    if mode == "never":
        return None
    return generate_ocr_sidecars(
        image_paths,
        force=mode == "force",
        tesseract_cmd=tesseract_cmd,
    )


def _load_image_derived_ocr(path: Path) -> str | None:
    candidates = [
        path.with_suffix(".ocr.json"),
        path.with_name(f"{path.stem}_ocr.json"),
        path.parent / "ocr" / f"{path.stem}.json",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        if data.get("engine") != "tesseract":
            continue
        text = str(data.get("ocr_text") or data.get("text") or "").strip()
        if text:
            return _short_text(text, 1200)
    return None


def _cache_key(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_status(value: object) -> ClaimStatus:
    normalized = str(value or "").strip().upper()
    aliases = {
        "SUPPORTED": ClaimStatus.SUPPORTED,
        "PARTIALLY_SUPPORTED": ClaimStatus.PARTIALLY_SUPPORTED,
        "PARTIAL": ClaimStatus.PARTIALLY_SUPPORTED,
        "MISSING": ClaimStatus.MISSING,
        "HIDDEN": ClaimStatus.HIDDEN,
        "CONTRADICTED": ClaimStatus.CONTRADICTED,
        "CONTRADICTION": ClaimStatus.CONTRADICTED,
        "AMBIGUOUS": ClaimStatus.AMBIGUOUS,
    }
    if normalized not in aliases:
        raise ValueError(f"Unsupported Gemini claim status: {value!r}")
    return aliases[normalized]


def _normalize_uncertainty_reasons(values: object) -> list[UncertaintyReason]:
    if not isinstance(values, list):
        return []
    reasons: list[UncertaintyReason] = []
    for value in values:
        try:
            reasons.append(UncertaintyReason(str(value).strip().upper()))
        except ValueError:
            continue
    return list(dict.fromkeys(reasons))


class GeminiImageClaimVerifier:
    prompt_version = "GEMINI_IMAGE_CLAIM_VERIFICATION_V1"

    def __init__(
        self,
        *,
        flow_id: str,
        screenshot_steps: list[ScreenshotStep],
        cache_path: Path,
        model_name: str = "gemini-2.5-flash-lite",
        temperature: float = 0.0,
        max_images_per_claim: int = 6,
        max_retries: int = 0,
        max_api_calls: int | None = 10,
        fallback: ClaimVerifier | None = None,
    ) -> None:
        self.flow_id = flow_id
        self.screenshot_steps = screenshot_steps
        self.step_to_path = {step.step_index: Path(step.screenshot_path) for step in screenshot_steps}
        self.cache_path = cache_path
        self.model_name = model_name
        self.temperature = temperature
        self.max_images_per_claim = max_images_per_claim
        self.max_retries = max_retries
        self.max_api_calls = max_api_calls
        self.fallback = fallback or ClaimVerifier()
        self.cache = self._load_cache()
        self.diagnostics: dict[str, Any] = {
            "requested": 0,
            "api_calls": 0,
            "cache_hits": 0,
            "fallbacks": 0,
            "failures": [],
            "cache_path": str(cache_path),
            "model_name": model_name,
            "prompt_version": self.prompt_version,
            "max_retries": max_retries,
            "max_api_calls": max_api_calls,
        }

    def verify(
        self,
        claim: RequirementClaim,
        evidence: list[EvidenceItem],
        *,
        ui_evaluability: UIEvaluability,
    ) -> ClaimVerificationResult:
        self.diagnostics["requested"] += 1
        if not claim.is_observable or has_hidden_indicator(claim.claim_text):
            return self.fallback.verify(claim, evidence, ui_evaluability=ui_evaluability)

        selected_steps = self._selected_steps(evidence)
        if not selected_steps:
            selected_steps = self._fallback_steps()
        payload = self._request_payload(claim, selected_steps, ui_evaluability=ui_evaluability)
        key = _cache_key(payload)

        cached = self.cache.get(key)
        if isinstance(cached, dict) and isinstance(cached.get("parsed"), dict):
            self.diagnostics["cache_hits"] += 1
            parsed = cached["parsed"]
        else:
            if self.max_api_calls is not None and int(self.diagnostics.get("api_calls", 0)) >= self.max_api_calls:
                self.diagnostics["fallbacks"] += 1
                self.diagnostics["failures"].append(
                    {
                        "claim_id": claim.claim_id,
                        "error": f"Gemini image API call cap reached for this run ({self.max_api_calls}).",
                    }
                )
                return self.fallback.verify(claim, evidence, ui_evaluability=ui_evaluability)
            try:
                parsed, raw = self._call_gemini(payload, selected_steps)
                self.cache[key] = {"payload": payload, "parsed": parsed, "raw": raw}
                self._save_cache()
            except Exception as exc:
                self.diagnostics["fallbacks"] += 1
                self.diagnostics["failures"].append({"claim_id": claim.claim_id, "error": str(exc)})
                return self.fallback.verify(claim, evidence, ui_evaluability=ui_evaluability)

        try:
            return self._result_from_gemini(claim, parsed, selected_steps)
        except Exception as exc:
            self.diagnostics["fallbacks"] += 1
            self.diagnostics["failures"].append({"claim_id": claim.claim_id, "error": str(exc)})
            return self.fallback.verify(claim, evidence, ui_evaluability=ui_evaluability)

    def _load_cache(self) -> dict[str, Any]:
        if not self.cache_path.exists():
            return {}
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self.cache, indent=2, ensure_ascii=False), encoding="utf-8")

    def _selected_steps(self, evidence: list[EvidenceItem]) -> list[int]:
        steps = sorted({item.step_index for item in evidence if item.step_index in self.step_to_path})
        return steps[: self.max_images_per_claim]

    def _fallback_steps(self) -> list[int]:
        return sorted(self.step_to_path)[: self.max_images_per_claim]

    def _request_payload(
        self,
        claim: RequirementClaim,
        selected_steps: list[int],
        *,
        ui_evaluability: UIEvaluability,
    ) -> dict[str, Any]:
        return {
            "prompt_version": self.prompt_version,
            "flow_id": self.flow_id,
            "model_name": self.model_name,
            "requirement_id": claim.requirement_id,
            "requirement_text": claim.source_requirement_text,
            "claim_id": claim.claim_id,
            "claim_text": claim.claim_text,
            "ui_evaluability": ui_evaluability.value,
            "selected_evidence_step_indices": selected_steps,
            "ocr_hints": [
                {
                    "step_index": step_index,
                    "source": "image_derived_tesseract_ocr",
                    "text": _load_image_derived_ocr(self.step_to_path[step_index]) or "",
                }
                for step_index in selected_steps
            ],
        }

    def _prompt(self, payload: dict[str, Any]) -> str:
        return f"""
You are verifying one UI requirement claim from screenshot images.

Use the attached screenshot images as the primary evidence source. The images are attached in this exact order:
{payload["selected_evidence_step_indices"]}

OCR hints are optional image-derived Tesseract OCR. Treat OCR as a hint only; verify against the screenshots.
Do not use raw HTML, DOM, backend state, database state, payment processing, email delivery, security guarantees, ranking correctness, persistence, or future-session behavior unless there is a visible UI proxy in the screenshots.

Strict rules:
- Only visible UI evidence counts.
- SUPPORTED requires clear visible screenshot evidence.
- PARTIALLY_SUPPORTED means some visible part is supported but important visible detail is missing or ambiguous.
- MISSING means the claim could be visible but the screenshots do not show enough.
- HIDDEN means the claim is about hidden/non-visual system behavior.
- CONTRADICTED requires visible counter-evidence in the screenshots.
- Missing evidence alone is not CONTRADICTED.

Input JSON:
{json.dumps(payload, indent=2, ensure_ascii=False)}

Return JSON only:
{{
  "claim_id": "{payload["claim_id"]}",
  "claim_status": "SUPPORTED | PARTIALLY_SUPPORTED | MISSING | HIDDEN | CONTRADICTED",
  "evidence_step_indices": [1],
  "uncertainty_reasons": ["TEXTUAL_AMBIGUITY | SCOPE_OR_CONTEXT_AMBIGUITY | QUANTIFIER_OR_COMPLETENESS_AMBIGUITY | EVIDENCE_INTERPRETATION_AMBIGUITY | FLOW_COVERAGE_GAP | UNVERIFIED_SYSTEM_OUTCOME | NONTRIVIAL_HIDDEN_PROPERTY"],
  "visible_observations": ["short visible observation tied to screenshot evidence"],
  "rationale": "short explanation"
}}
""".strip()

    def _call_gemini(self, payload: dict[str, Any], selected_steps: list[int]) -> tuple[dict[str, Any], str]:
        from ui_verifier.requirements.gemini_client import run_gemini

        image_bytes = [self.step_to_path[step_index].read_bytes() for step_index in selected_steps]
        prompt = self._prompt(payload)
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                raw = run_gemini(
                    prompt,
                    image_bytes,
                    model_name=self.model_name,
                    temperature=self.temperature,
                )
                break
            except Exception as exc:
                last_error = exc
                message = str(exc)
                if attempt >= self.max_retries or not self._is_retryable_gemini_error(message):
                    raise
                time.sleep(self._retry_delay_seconds(message))
        else:
            raise last_error or RuntimeError("Gemini call failed.")
        self.diagnostics["api_calls"] += 1
        parsed = parse_json_response(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Gemini response was not a JSON object.")
        return parsed, raw

    @staticmethod
    def _is_retryable_gemini_error(message: str) -> bool:
        return "RESOURCE_EXHAUSTED" in message or "UNAVAILABLE" in message or "retry" in message.lower()

    @staticmethod
    def _retry_delay_seconds(message: str) -> float:
        retry_delay = re.search(r"retryDelay['\"]?:\s*['\"]?(\d+)s", message)
        if retry_delay:
            return min(float(retry_delay.group(1)) + 1.0, 65.0)
        retry_in = re.search(r"retry in ([0-9.]+)s", message, flags=re.IGNORECASE)
        if retry_in:
            return min(float(retry_in.group(1)) + 1.0, 65.0)
        if "UNAVAILABLE" in message:
            return 8.0
        return 15.0

    def _result_from_gemini(
        self,
        claim: RequirementClaim,
        parsed: dict[str, Any],
        selected_steps: list[int],
    ) -> ClaimVerificationResult:
        status = _normalize_status(parsed.get("claim_status") or parsed.get("status"))
        evidence_step_indices = parsed.get("evidence_step_indices")
        if not isinstance(evidence_step_indices, list):
            evidence_step_indices = []
        step_indices = [
            int(step)
            for step in evidence_step_indices
            if isinstance(step, int) and step in self.step_to_path and step in selected_steps
        ]
        observations = parsed.get("visible_observations")
        if not isinstance(observations, list):
            observations = []
        observation_text = " ".join(_short_text(str(item), 260) for item in observations if str(item).strip())
        if not observation_text:
            observation_text = str(parsed.get("rationale") or "Gemini image verifier returned a claim decision.").strip()

        evidence: list[EvidenceItem] = []
        if status in {ClaimStatus.SUPPORTED, ClaimStatus.PARTIALLY_SUPPORTED, ClaimStatus.CONTRADICTED}:
            for step_index in step_indices:
                evidence.append(
                    EvidenceItem(
                        step_index=step_index,
                        screenshot_path=str(self.step_to_path[step_index]),
                        visible_observation=observation_text,
                        confidence=self._confidence_for_status(status),
                        source="gemini_image",
                        metadata={"model_name": self.model_name},
                    )
                )

        reasons = _normalize_uncertainty_reasons(parsed.get("uncertainty_reasons"))
        if status in {ClaimStatus.MISSING, ClaimStatus.PARTIALLY_SUPPORTED, ClaimStatus.AMBIGUOUS}:
            reasons = list(dict.fromkeys([*reasons, UncertaintyReason.EVIDENCE_INTERPRETATION_AMBIGUITY]))
        if status == ClaimStatus.MISSING:
            reasons = list(dict.fromkeys([*reasons, UncertaintyReason.FLOW_COVERAGE_GAP]))
        if status == ClaimStatus.HIDDEN:
            reasons = list(dict.fromkeys([*reasons, UncertaintyReason.NONTRIVIAL_HIDDEN_PROPERTY]))

        rationale = str(parsed.get("rationale") or "Gemini image verifier returned this claim decision.").strip()
        return ClaimVerificationResult(
            claim_id=claim.claim_id,
            requirement_id=claim.requirement_id,
            claim_text=claim.claim_text,
            status=status,
            is_core=claim.is_core,
            is_observable=claim.is_observable and status != ClaimStatus.HIDDEN,
            evidence=evidence,
            uncertainty_reasons=reasons,
            confidence=self._confidence_for_status(status),
            rationale=rationale,
        )

    @staticmethod
    def _confidence_for_status(status: ClaimStatus) -> float:
        if status == ClaimStatus.SUPPORTED:
            return 0.85
        if status == ClaimStatus.PARTIALLY_SUPPORTED:
            return 0.6
        if status == ClaimStatus.CONTRADICTED:
            return 0.75
        if status == ClaimStatus.MISSING:
            return 0.0
        return 0.2


def _counter_to_dict(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _requirement_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        items = data.get("items") or data.get("requirements") or data.get("verdicts") or []
    elif isinstance(data, list):
        items = data
    else:
        items = []
    return [item for item in items if isinstance(item, dict)]


def compare_with_reference(output: PipelineOutput, reference_path: Path | None) -> dict[str, object]:
    if reference_path is None:
        return {
            "status": "missing_reference",
            "reference_path": None,
            "summary": {},
            "items": [],
        }

    data = json.loads(reference_path.read_text(encoding="utf-8"))
    reference_items = {
        str(item.get("requirement_id")): item
        for item in _requirement_items(data)
        if item.get("requirement_id")
    }
    output_by_id = {result.requirement_id: result for result in output.results}

    rows: list[dict[str, object]] = []
    for result in output.results:
        reference = reference_items.get(result.requirement_id)
        predicted = result.final_label.value
        reference_label = str(reference.get("verification_label")) if reference else None
        matches = reference_label == predicted if reference_label else None
        rows.append(
            {
                "requirement_id": result.requirement_id,
                "predicted_label": predicted,
                "reference_label": reference_label,
                "matches_reference": matches,
                "reference_review_status": reference.get("review_status") if reference else None,
                "reference_evidence_steps": reference.get("evidence_steps") if reference else [],
                "predicted_evidence_steps": sorted({item.step_index for item in result.evidence}),
                "reference_text": reference.get("text") if reference else None,
                "predicted_text": result.requirement_text,
            }
        )

    reference_only = sorted(set(reference_items) - set(output_by_id))
    compared = [row for row in rows if row["reference_label"]]
    matches_count = sum(1 for row in compared if row["matches_reference"] is True)
    mismatches_count = sum(1 for row in compared if row["matches_reference"] is False)
    review_status_distribution: Counter[str] = Counter(
        str(item.get("review_status", "missing")) for item in reference_items.values()
    )

    return {
        "status": "compared",
        "reference_path": str(reference_path),
        "summary": {
            "reference_items": len(reference_items),
            "compared_items": len(compared),
            "matches": matches_count,
            "mismatches": mismatches_count,
            "missing_reference_for_predictions": len(output.results) - len(compared),
            "reference_only_items": len(reference_only),
            "accuracy_on_matched_ids": round(matches_count / len(compared), 4) if compared else None,
            "reference_review_status_distribution": _counter_to_dict(review_status_distribution),
        },
        "items": rows,
        "reference_only_requirement_ids": reference_only,
    }


def summarize_output(output: PipelineOutput) -> dict[str, object]:
    label_distribution: Counter[str] = Counter()
    claim_status_distribution: Counter[str] = Counter()
    evidence_step_indices: set[int] = set()
    claim_count = 0

    for result in output.results:
        label_distribution[result.final_label.value] += 1
        claim_count += len(result.claims)
        for claim in result.claims:
            claim_status_distribution[claim.status.value] += 1
            for item in claim.evidence:
                evidence_step_indices.add(item.step_index)

    return {
        "requirements_count": len(output.results),
        "claim_count": claim_count,
        "label_distribution": _counter_to_dict(label_distribution),
        "claim_status_distribution": _counter_to_dict(claim_status_distribution),
        "evidence_step_indices": sorted(evidence_step_indices),
    }


def _claim_evidence_steps(claim: Any) -> list[int]:
    return sorted({item.step_index for item in claim.evidence})


def _artifact_requirements(output: PipelineOutput) -> list[dict[str, object]]:
    requirements: list[dict[str, object]] = []
    for result in output.results:
        requirements.append(
            {
                "requirement_id": result.requirement_id,
                "requirement_text": result.requirement_text,
                "ui_evaluability": result.ui_evaluability.value,
                "final_label": result.final_label.value,
                "evidence_steps": sorted({item.step_index for item in result.evidence}),
                "uncertainty_reasons": [reason.value for reason in result.uncertainty_reasons],
                "rationale": result.rationale,
                "claims": [
                    {
                        "claim_id": claim.claim_id,
                        "claim_text": claim.claim_text,
                        "status": claim.status.value,
                        "is_observable": claim.is_observable,
                        "evidence_steps": _claim_evidence_steps(claim),
                        "confidence": claim.confidence,
                        "uncertainty_reasons": [reason.value for reason in claim.uncertainty_reasons],
                        "rationale": claim.rationale,
                        "evidence": [
                            {
                                "step_index": item.step_index,
                                "screenshot_path": item.screenshot_path,
                                "source": item.source,
                                "confidence": item.confidence,
                                "visible_observation": item.visible_observation,
                            }
                            for item in claim.evidence
                        ],
                    }
                    for claim in result.claims
                ],
            }
        )
    return requirements


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_pipeline_artifacts(output: PipelineOutput, artifacts_dir: Path) -> None:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    requirements = _artifact_requirements(output)
    comparison = output.metadata.get("reference_comparison", {})

    write_json(artifacts_dir / "00_run_summary.json", output.metadata)
    write_json(
        artifacts_dir / "01_screenshot_flow.json",
        {
            "flow_id": output.flow_id,
            "screenshots": [
                {
                    "step_index": screen.step_index,
                    "screenshot_path": screen.screenshot_path,
                    "image_width": screen.image_width,
                    "image_height": screen.image_height,
                    "sources": screen.sources,
                }
                for screen in output.screen_representations
            ],
        },
    )
    write_json(artifacts_dir / "02_ocr_summary.json", output.metadata.get("ocr", {}))
    write_json(
        artifacts_dir / "03_screen_representations.json",
        [
            {
                "step_index": screen.step_index,
                "screenshot_path": screen.screenshot_path,
                "sources": screen.sources,
                "visible_text": screen.visible_text,
                "screen_summary": screen.screen_summary,
            }
            for screen in output.screen_representations
        ],
    )
    write_json(
        artifacts_dir / "04_claims.json",
        [
            {
                "requirement_id": requirement["requirement_id"],
                "claim_id": claim["claim_id"],
                "claim_text": claim["claim_text"],
                "status": claim["status"],
                "is_observable": claim["is_observable"],
                "evidence_steps": claim["evidence_steps"],
                "confidence": claim["confidence"],
                "rationale": claim["rationale"],
            }
            for requirement in requirements
            for claim in requirement["claims"]  # type: ignore[index]
        ],
    )
    write_json(artifacts_dir / "05_evidence_by_requirement.json", requirements)
    write_json(artifacts_dir / "06_reference_comparison.json", comparison)
    write_pipeline_trace(output, artifacts_dir / "pipeline_trace.md")
    write_presentation_text(output, artifacts_dir / "presentation_text.md")


def _short_text(text: str, max_chars: int = 700) -> str:
    text = " ".join(str(text).split()).strip()
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3].rstrip()}..."


def _json_block(payload: object) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def write_presentation_text(output: PipelineOutput, path: Path) -> None:
    summary = summarize_output(output)
    comparison = output.metadata.get("reference_comparison", {})
    comparison_summary = comparison.get("summary", {}) if isinstance(comparison, dict) else {}
    comparison_items = comparison.get("items", []) if isinstance(comparison, dict) else []
    mismatches = [
        item
        for item in comparison_items
        if isinstance(item, dict) and item.get("matches_reference") is False
    ]
    ocr = output.metadata.get("ocr", {})

    lines: list[str] = [
        "# UI Requirement Verification Demo Artifacts",
        "",
        "This text is generated for presentation preparation. It is intentionally verbose and split by pipeline module with input and output.",
        "",
        "## Run Request",
        "",
        "Command:",
        "",
        "```bash",
        f"PYTHONPATH=src:. python scripts/run_demo_verification.py --flow-id {output.flow_id}",
        "```",
        "",
        "Resolved inputs:",
        "",
        "```json",
        _json_block(
            {
                "flow_id": output.flow_id,
                "flow_dir": output.metadata.get("flow_dir"),
                "requirements_path": output.metadata.get("requirements_path"),
                "checked_screenshot_paths": output.metadata.get("checked_screenshot_paths"),
                "reference_path": comparison.get("reference_path") if isinstance(comparison, dict) else None,
                "requested_retriever": output.metadata.get("requested_retriever"),
                "selected_retriever": output.metadata.get("selected_retriever"),
                "top_k": output.metadata.get("top_k"),
                "verifier": output.metadata.get("verifier"),
                "gemini_mllm_verifier_used": output.metadata.get("gemini_mllm_verifier_used"),
            }
        ),
        "```",
        "",
        "## Module 1: Screenshot Flow Validation",
        "",
        "Input:",
        "",
        "- Candidate screenshot directories from processed flow data and manual harvest bundle.",
        "- Files matching `step_*.png`.",
        "",
        "Output:",
        "",
        "```json",
        _json_block(
            {
                "screenshot_count": len(output.screen_representations),
                "step_indices": [screen.step_index for screen in output.screen_representations],
                "screenshots": [
                    {
                        "step_index": screen.step_index,
                        "screenshot_path": screen.screenshot_path,
                        "image_width": screen.image_width,
                        "image_height": screen.image_height,
                    }
                    for screen in output.screen_representations
                ],
            }
        ),
        "```",
        "",
        "## Module 2: OCR Sidecars / Screen Text",
        "",
        "Input:",
        "",
        "- Ordered screenshots from Module 1.",
        "- Existing OCR sidecars if present.",
        "- Local Tesseract if OCR sidecars are missing and OCR is enabled.",
        "- Mind2Web `steps.json` raw HTML metadata when available.",
        "",
        "Output:",
        "",
        "```json",
        _json_block(
            {
                "ocr": ocr,
                "screen_source_labels": _screen_source_labels(output),
                "screen_text_samples": [
                    {
                        "step_index": screen.step_index,
                        "sources": screen.sources,
                        "visible_text_sample": _short_text(screen.visible_text, 500),
                    }
                    for screen in output.screen_representations[:5]
                ],
            }
        ),
        "```",
        "",
        "## Module 3: Requirement Understanding / Claims",
        "",
        "Input:",
        "",
        "- Gold requirements JSON.",
        "- Deterministic claim decomposition, with one-claim fallback for atomic requirements.",
        "",
        "Output:",
        "",
        "```json",
        _json_block(
            {
                "requirements_count": summary["requirements_count"],
                "claim_count": summary["claim_count"],
                "claims_demo_decision": output.metadata.get("claims_demo_decision"),
                "claims": [
                    {
                        "requirement_id": result.requirement_id,
                        "claim_id": claim.claim_id,
                        "claim_text": claim.claim_text,
                        "is_observable": claim.is_observable,
                    }
                    for result in output.results
                    for claim in result.claims
                ],
            }
        ),
        "```",
        "",
        "## Module 4: Evidence Retrieval",
        "",
        "Input:",
        "",
        "- Claims from Module 3.",
        "- Screen representations from Module 2.",
        f"- Retriever: `{output.metadata.get('selected_retriever')}`.",
        "",
        "Output:",
        "",
        "```json",
        _json_block(
            [
                {
                    "requirement_id": result.requirement_id,
                    "claim_id": claim.claim_id,
                    "claim_text": claim.claim_text,
                    "status": claim.status.value,
                    "evidence": [
                        {
                            "step_index": item.step_index,
                            "source": item.source,
                            "confidence": item.confidence,
                            "visible_observation": _short_text(item.visible_observation, 450),
                        }
                        for item in claim.evidence
                    ],
                }
                for result in output.results
                for claim in result.claims
            ]
        ),
        "```",
        "",
        "## Module 5: Claim Verification / Label Aggregation",
        "",
        "Input:",
        "",
        "- Retrieved evidence per claim.",
        "- Evidence-first label rules.",
        "",
        "Output:",
        "",
        "```json",
        _json_block(
            {
                "label_distribution": summary["label_distribution"],
                "claim_status_distribution": summary["claim_status_distribution"],
                "requirements": [
                    {
                        "requirement_id": result.requirement_id,
                        "requirement_text": result.requirement_text,
                        "ui_evaluability": result.ui_evaluability.value,
                        "final_label": result.final_label.value,
                        "evidence_steps": sorted({item.step_index for item in result.evidence}),
                        "uncertainty_reasons": [reason.value for reason in result.uncertainty_reasons],
                        "rationale": result.rationale,
                    }
                    for result in output.results
                ],
            }
        ),
        "```",
        "",
        "## Module 6: Reviewed-Label Comparison",
        "",
        "Input:",
        "",
        "- Pipeline predictions from Module 5.",
        "- Reviewed labels from `verification_gold`, when available.",
        "",
        "Output:",
        "",
        "```json",
        _json_block(
            {
                "summary": comparison_summary,
                "mismatches": mismatches,
            }
        ),
        "```",
        "",
        "## Presentation Notes",
        "",
        "- Claims are useful because they explain why a requirement is supported, hidden, missing, or only partially supported.",
        "- Missing evidence alone does not produce `NOT_FULFILLED`; visible contradiction is required.",
        "- Current deterministic mode is useful for a robust demo but can over-predict `FULFILLED` when textual overlap is strong.",
        "- Gemini/MLLM verifier is not used in this run.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def package_demo_artifacts(
    *,
    flow_id: str,
    out_path: Path,
    report_path: Path | None,
    artifacts_dir: Path | None,
    package_dir: Path | None = None,
    copy_to_clipboard: bool = True,
) -> dict[str, object]:
    target_dir = package_dir or Path(tempfile.gettempdir()) / "ui_verifier_demo_packages"
    target_dir.mkdir(parents=True, exist_ok=True)
    package_root = target_dir / flow_id
    if package_root.exists():
        shutil.rmtree(package_root)
    package_root.mkdir(parents=True)

    shutil.copy2(out_path, package_root / out_path.name)
    if report_path is not None and report_path.exists():
        shutil.copy2(report_path, package_root / report_path.name)
    if artifacts_dir is not None and artifacts_dir.exists():
        shutil.copytree(artifacts_dir, package_root / artifacts_dir.name)

    archive_base = target_dir / flow_id
    archive_path = Path(shutil.make_archive(str(archive_base), "zip", root_dir=target_dir, base_dir=flow_id))
    shutil.rmtree(package_root)

    clipboard = copy_path_to_clipboard(archive_path) if copy_to_clipboard else {"status": "skipped"}
    return {
        "status": "created",
        "archive_path": str(archive_path),
        "clipboard": clipboard,
    }


def copy_path_to_clipboard(path: Path) -> dict[str, str]:
    return copy_text_to_clipboard(str(path), status="copied_path")


def copy_file_text_to_clipboard(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"status": "failed", "reason": str(exc)}
    return copy_text_to_clipboard(text, status="copied_text")


def copy_text_to_clipboard(text: str, *, status: str = "copied_text") -> dict[str, str]:
    pbcopy = shutil.which("pbcopy")
    if pbcopy is None:
        return {"status": "unavailable", "reason": "pbcopy not found"}
    try:
        subprocess.run(
            [pbcopy],
            input=text,
            text=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception as exc:
        return {"status": "failed", "reason": str(exc)}
    return {"status": status}


def _screen_source_labels(output: PipelineOutput) -> list[str]:
    labels: set[str] = set()
    for screen in output.screen_representations:
        for source in screen.sources:
            if "/ocr/" in source or "\\ocr\\" in source or source.endswith(".ocr.json") or source.endswith(".ocr.txt"):
                labels.add("ocr_sidecar")
            elif source in {"image_metadata", "raw_html", "sidecar", "placeholder_ocr"}:
                labels.add(source)
            else:
                labels.add("sidecar_file")
    return sorted(labels)


def write_pipeline_trace(output: PipelineOutput, trace_path: Path) -> None:
    summary = summarize_output(output)
    comparison = output.metadata.get("reference_comparison", {})
    comparison_summary = comparison.get("summary", {}) if isinstance(comparison, dict) else {}
    lines = [
        f"# Pipeline Trace: {output.flow_id}",
        "",
        "## 1. Screenshot Flow Validation",
        "",
        f"- Selected screenshot directory: `{output.metadata.get('flow_dir')}`",
        f"- Screenshots: {len(output.screen_representations)}",
        f"- Step indices: {[screen.step_index for screen in output.screen_representations]}",
        "",
        "## 2. OCR / Screen Text",
        "",
        f"- OCR status: `{(output.metadata.get('ocr') or {}).get('status') if isinstance(output.metadata.get('ocr'), dict) else 'unknown'}`",
        f"- Screen representation sources: {_screen_source_labels(output)}",
        "",
        "## 3. Requirement Understanding",
        "",
        f"- Requirements: {summary['requirements_count']}",
        f"- Claims: {summary['claim_count']}",
        f"- Claims decision: {output.metadata.get('claims_demo_decision')}",
        "",
        "## 4. Evidence Retrieval",
        "",
        f"- Retriever: `{output.metadata.get('selected_retriever')}`",
        f"- Top-k: {output.metadata.get('top_k')}",
        f"- Evidence steps used: {summary['evidence_step_indices']}",
        "",
        "## 5. Label Aggregation",
        "",
        f"- Verifier: `{output.metadata.get('verifier')}`",
        f"- Label distribution: {summary['label_distribution']}",
        f"- Claim status distribution: {summary['claim_status_distribution']}",
        "",
        "## 6. Reference Comparison",
        "",
        f"- Reference status: `{comparison.get('status') if isinstance(comparison, dict) else 'unknown'}`",
        f"- Matches: {comparison_summary.get('matches')}",
        f"- Mismatches: {comparison_summary.get('mismatches')}",
        f"- Accuracy on matched ids: {comparison_summary.get('accuracy_on_matched_ids')}",
        "",
    ]
    trace_path.write_text("\n".join(lines), encoding="utf-8")


def write_markdown_report(output: PipelineOutput, report_path: Path) -> None:
    summary = summarize_output(output)
    comparison = output.metadata.get("reference_comparison", {})
    comparison_items = comparison.get("items", []) if isinstance(comparison, dict) else []
    comparison_by_id = {
        str(item.get("requirement_id")): item for item in comparison_items if isinstance(item, dict)
    }
    comparison_summary = comparison.get("summary", {}) if isinstance(comparison, dict) else {}
    lines = [
        f"# Demo Verification Report: {output.flow_id}",
        "",
        f"- Requirements: {summary['requirements_count']}",
        f"- Claims: {summary['claim_count']}",
        f"- Labels: {summary['label_distribution']}",
        f"- Retriever: {output.metadata.get('retriever')}",
        f"- Verifier: {output.metadata.get('verifier')}",
        f"- Reference comparison: {comparison_summary}",
        "",
        "## Requirements",
        "",
    ]
    for result in output.results:
        evidence_steps = sorted({item.step_index for item in result.evidence})
        comparison_row = comparison_by_id.get(result.requirement_id, {})
        reference_label = comparison_row.get("reference_label")
        match = comparison_row.get("matches_reference")
        if match is True:
            comparison_text = f"matches reviewed label `{reference_label}`"
        elif match is False:
            comparison_text = f"differs from reviewed label `{reference_label}`"
        else:
            comparison_text = "no reviewed reference label matched this requirement id"
        lines.extend(
            [
                f"### {result.requirement_id}: {result.final_label.value}",
                "",
                result.requirement_text,
                "",
                f"- UI evaluability: {result.ui_evaluability.value}",
                f"- Reviewed-label comparison: {comparison_text}",
                f"- Evidence steps: {evidence_steps}",
                f"- Uncertainty: {[reason.value for reason in result.uncertainty_reasons]}",
                f"- Rationale: {result.rationale}",
                "",
                "| Claim | Status | Evidence steps | Confidence | Rationale |",
                "|---|---:|---:|---:|---|",
            ]
        )
        for claim in result.claims:
            claim_steps = _claim_evidence_steps(claim)
            confidence = "" if claim.confidence is None else f"{claim.confidence:.3f}"
            claim_text = claim.claim_text.replace("|", "\\|")
            rationale = claim.rationale.replace("|", "\\|")
            lines.append(
                f"| {claim_text} | {claim.status.value} | {claim_steps} | {confidence} | {rationale} |"
            )
        lines.append("")
        if result.evidence:
            lines.extend(["Evidence snippets:", ""])
            for item in result.evidence[:3]:
                snippet = item.visible_observation.replace("\n", " ").strip()
                lines.append(f"- Step {item.step_index}: {snippet}")
            lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def build_pipeline_output(args: argparse.Namespace, *, base_dir: Path = BASE_DIR) -> tuple[PipelineOutput, Path, Path | None]:
    load_dotenv(base_dir / ".env")

    flow_id = resolve_flow_id(args.flow_id, base_dir=base_dir)
    selection = resolve_screenshot_dir(flow_id, base_dir=base_dir, explicit_flow_dir=args.flow_dir)
    requirements_path = resolve_requirements_path(flow_id, base_dir=base_dir, explicit_requirements=args.requirements)
    reference_path = resolve_reference_path(flow_id, base_dir=base_dir, explicit_reference=args.reference)
    out_path = args.out or (base_dir / "data" / "generated" / "demo_verification" / f"{flow_id}.json")
    artifacts_dir = args.artifacts_dir or (out_path.parent / f"{out_path.stem}_artifacts")
    screenshots = discover_demo_screenshot_steps(selection, screen_source_mode=args.screen_source)

    image_paths = [Path(step.screenshot_path) for step in screenshots]
    ocr_summary = maybe_generate_ocr(
        image_paths,
        mode=args.ocr,
        tesseract_cmd=args.tesseract_cmd,
    )

    requirements = load_requirements(requirements_path, default_flow_id=flow_id)
    retriever_name = select_retriever_name(args.retriever)
    retriever = build_evidence_retriever(retriever_name, top_k=args.top_k)

    gemini_key_present = bool(os.environ.get("GEMINI_API_KEY"))
    fallback_decomposer = None
    gemini_claim_fallback_enabled = False
    gemini_claim_fallback_note = None
    if args.llm_claim_fallback:
        if gemini_key_present:
            fallback_decomposer = GeminiClaimDecomposer(model_name=args.claim_model)
            gemini_claim_fallback_enabled = True
        else:
            gemini_claim_fallback_note = "GEMINI_API_KEY is not set; using deterministic claim decomposition."

    requirement_understander = RequirementUnderstanding(fallback_decomposer=fallback_decomposer)
    claim_verifier: ClaimVerifier | GeminiImageClaimVerifier
    gemini_image_verifier: GeminiImageClaimVerifier | None = None
    verifier_fallback_note = None
    if args.verifier == "gemini-image":
        gemini_image_verifier = GeminiImageClaimVerifier(
            flow_id=flow_id,
            screenshot_steps=screenshots,
            cache_path=artifacts_dir / "gemini_image_claim_verification.json",
            model_name=args.verifier_model,
            temperature=args.verifier_temperature,
            max_images_per_claim=args.max_verifier_images,
            max_retries=args.gemini_max_retries,
            max_api_calls=None if args.max_gemini_api_calls < 0 else args.max_gemini_api_calls,
        )
        claim_verifier = gemini_image_verifier
        if not gemini_key_present:
            verifier_fallback_note = "GEMINI_API_KEY is not set; uncached claims fall back to deterministic verification."
    else:
        claim_verifier = ClaimVerifier()

    pipeline = EvidenceFirstVerificationPipeline(
        requirement_understander=requirement_understander,
        evidence_retriever=retriever,
        claim_verifier=claim_verifier,
    )
    output = pipeline.run(
        PipelineInput(
            flow_id=flow_id,
            screenshots=screenshots,
            requirements=requirements,
            metadata={
                "demo": True,
                "flow_dir": _rel(selection.screenshot_dir, base_dir=base_dir),
                "metadata_dir": _rel(selection.metadata_dir, base_dir=base_dir),
                "checked_screenshot_paths": [_rel(path, base_dir=base_dir) for path in selection.checked_paths],
                "requirements_path": _rel(requirements_path, base_dir=base_dir),
                "requested_retriever": args.retriever,
                "selected_retriever": retriever_name,
                "top_k": args.top_k,
                "screen_source_mode": args.screen_source,
                "raw_html_used": args.screen_source != "image-only",
                "ocr_used": ocr_summary is not None and (ocr_summary.generated > 0 or ocr_summary.reused > 0),
                "screenshot_images_used": False,
                "ocr": ocr_summary.as_dict() if ocr_summary else {"status": "skipped", "mode": "never"},
                "claims_used": True,
                "claims_demo_decision": (
                    "Claims are kept as lightweight internal structure because they explain partial, missing, "
                    "hidden, and abstained outcomes. Atomic requirements fall back to one claim."
                ),
                "verifier": args.verifier,
                "verifier_model": args.verifier_model if args.verifier == "gemini-image" else None,
                "verifier_fallback": "deterministic_rule_based",
                "verifier_fallback_note": verifier_fallback_note,
                "gemini_mllm_verifier_used": False,
                "gemini_claim_fallback_requested": args.llm_claim_fallback,
                "gemini_claim_fallback_enabled": gemini_claim_fallback_enabled,
                "gemini_claim_fallback_note": gemini_claim_fallback_note,
                "gemini_api_key_present": gemini_key_present,
                "limitations": [
                    "No full bounding-box localization.",
                    "No research-grade visual grounding.",
                    "No robust visible contradiction detection.",
                    "No full transition-level ordered-flow reasoning.",
                    "Missing evidence alone is never treated as NOT_FULFILLED.",
                ],
            },
        )
    )
    if gemini_image_verifier is not None:
        diagnostics = dict(gemini_image_verifier.diagnostics)
        api_or_cache_results = int(diagnostics.get("api_calls", 0)) + int(diagnostics.get("cache_hits", 0))
        output.metadata["gemini_image_verifier"] = diagnostics
        output.metadata["gemini_mllm_verifier_used"] = api_or_cache_results > 0
        output.metadata["screenshot_images_used"] = api_or_cache_results > 0
        output.metadata["gemini_mllm_verifier_fallback_used"] = int(diagnostics.get("fallbacks", 0)) > 0
    output.metadata["raw_html_used"] = any("raw_html" in screen.sources for screen in output.screen_representations)
    output.metadata["ocr_used"] = any("sidecar" in screen.sources for screen in output.screen_representations)
    output.metadata.update(summarize_output(output))
    reference_comparison = compare_with_reference(output, reference_path)
    if reference_comparison.get("reference_path"):
        reference_comparison["reference_path"] = _rel(Path(str(reference_comparison["reference_path"])), base_dir=base_dir)
    output.metadata["reference_comparison"] = reference_comparison

    report_path = None if args.no_report else out_path.with_suffix(".md")
    return output, out_path, report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the evidence-first demo verifier on a real annotated flow.")
    parser.add_argument("--flow-id", default=DEFAULT_FLOW_ID, help="Full flow id or unique prefix, e.g. 03_mbta")
    parser.add_argument("--flow-dir", type=Path, default=None, help="Optional explicit directory containing step_*.png")
    parser.add_argument("--requirements", type=Path, default=None, help="Optional requirements JSON path")
    parser.add_argument("--reference", type=Path, default=None, help="Optional verification_gold JSON path for label comparison")
    parser.add_argument("--out", type=Path, default=None, help="Output JSON path")
    parser.add_argument("--artifacts-dir", type=Path, default=None, help="Directory for presentation-friendly pipeline artifacts")
    parser.add_argument("--package-dir", type=Path, default=None, help="Directory for the generated zip package. Defaults to macOS temp storage.")
    parser.add_argument("--retriever", choices=["auto", "tfidf", "lexical", "embedding"], default="auto")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--screen-source", choices=["current", "image-only"], default="current")
    parser.add_argument("--verifier", choices=["deterministic", "gemini-image"], default="deterministic")
    parser.add_argument("--verifier-model", default="gemini-2.5-flash-lite")
    parser.add_argument("--verifier-temperature", type=float, default=0.0)
    parser.add_argument("--max-verifier-images", type=int, default=6)
    parser.add_argument("--gemini-max-retries", type=int, default=0)
    parser.add_argument(
        "--max-gemini-api-calls",
        type=int,
        default=10,
        help="Maximum uncached Gemini image calls per run before deterministic fallback is used. Use -1 for no cap.",
    )
    parser.add_argument("--ocr", choices=["missing", "force", "never"], default="missing")
    parser.add_argument("--tesseract-cmd", default="tesseract")
    parser.add_argument("--llm-claim-fallback", action="store_true")
    parser.add_argument("--claim-model", default="gemini-2.5-flash-lite")
    parser.add_argument("--no-report", action="store_true", help="Do not write a Markdown summary next to the JSON")
    parser.add_argument("--no-artifacts", action="store_true", help="Do not write stage-by-stage artifact files")
    parser.add_argument("--no-package", action="store_true", help="Do not create a zip package of JSON, report, and artifacts")
    parser.add_argument("--no-clipboard", action="store_true", help="Do not copy the zip path to the macOS clipboard")
    parser.add_argument(
        "--clipboard-mode",
        choices=["package-path", "presentation-text"],
        default="package-path",
        help="Copy either the generated zip path or the generated presentation text to the macOS clipboard.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        output, out_path, report_path = build_pipeline_output(args)
    except DemoDataError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc

    out_path.parent.mkdir(parents=True, exist_ok=True)
    artifacts_dir = args.artifacts_dir or (out_path.parent / f"{out_path.stem}_artifacts")
    if not args.no_artifacts:
        output.metadata["artifacts_dir"] = _rel(artifacts_dir)
    out_path.write_text(json.dumps(output.model_dump(mode="json"), indent=2, ensure_ascii=False), encoding="utf-8")
    if report_path is not None:
        write_markdown_report(output, report_path)
    if not args.no_artifacts:
        write_pipeline_artifacts(output, artifacts_dir)
    package_summary: dict[str, object] | None = None
    clipboard_summary: dict[str, str] | None = None
    if not args.no_package:
        package_summary = package_demo_artifacts(
            flow_id=output.flow_id,
            out_path=out_path,
            report_path=report_path,
            artifacts_dir=None if args.no_artifacts else artifacts_dir,
            package_dir=args.package_dir,
            copy_to_clipboard=(not args.no_clipboard and args.clipboard_mode == "package-path"),
        )
        output.metadata["package"] = package_summary
        out_path.write_text(json.dumps(output.model_dump(mode="json"), indent=2, ensure_ascii=False), encoding="utf-8")
        clipboard = package_summary.get("clipboard")
        if isinstance(clipboard, dict):
            clipboard_summary = clipboard
    if not args.no_clipboard and args.clipboard_mode == "presentation-text":
        if args.no_artifacts:
            clipboard_summary = {"status": "failed", "reason": "presentation text requires artifacts"}
        else:
            clipboard_summary = copy_file_text_to_clipboard(artifacts_dir / "presentation_text.md")
            output.metadata["clipboard"] = clipboard_summary
            out_path.write_text(json.dumps(output.model_dump(mode="json"), indent=2, ensure_ascii=False), encoding="utf-8")

    summary = summarize_output(output)
    ocr = output.metadata.get("ocr", {})
    comparison = output.metadata.get("reference_comparison", {})
    comparison_summary = comparison.get("summary", {}) if isinstance(comparison, dict) else {}
    print(f"flow={output.flow_id}")
    print(f"out={_rel(out_path)}")
    if report_path is not None:
        print(f"report={_rel(report_path)}")
    if not args.no_artifacts:
        print(f"artifacts={_rel(artifacts_dir)}")
    if package_summary:
        print(f"package={package_summary.get('archive_path')}")
    if clipboard_summary:
        print(f"clipboard={clipboard_summary.get('status')}")
    print(f"screenshots={len(output.screen_representations)} requirements={summary['requirements_count']} claims={summary['claim_count']}")
    print(f"labels={summary['label_distribution']}")
    if comparison_summary:
        print(
            "reference_comparison="
            f"matches={comparison_summary.get('matches')} "
            f"mismatches={comparison_summary.get('mismatches')} "
            f"accuracy={comparison_summary.get('accuracy_on_matched_ids')}"
        )
    print(f"retriever={output.metadata.get('selected_retriever')} verifier={output.metadata.get('verifier')}")
    print(
        f"screen_source_mode={output.metadata.get('screen_source_mode')} "
        f"raw_html_used={output.metadata.get('raw_html_used')} "
        f"ocr_used={output.metadata.get('ocr_used')} "
        f"screenshot_images_used={output.metadata.get('screenshot_images_used')}"
    )
    print(f"gemini_mllm_verifier_used={output.metadata.get('gemini_mllm_verifier_used')}")
    if output.metadata.get("gemini_image_verifier"):
        diagnostics = output.metadata["gemini_image_verifier"]
        if isinstance(diagnostics, dict):
            print(
                "gemini_image_verifier="
                f"api_calls={diagnostics.get('api_calls')} "
                f"cache_hits={diagnostics.get('cache_hits')} "
                f"fallbacks={diagnostics.get('fallbacks')}"
            )
    print(f"ocr_status={ocr.get('status') if isinstance(ocr, dict) else 'unknown'}")
    if isinstance(ocr, dict):
        print(f"ocr_generated={ocr.get('generated', 0)} ocr_reused={ocr.get('reused', 0)} ocr_failed={ocr.get('failed', 0)}")


if __name__ == "__main__":
    main()
