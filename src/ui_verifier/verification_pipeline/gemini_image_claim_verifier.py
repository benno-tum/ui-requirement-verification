from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import threading
import time
from typing import Any

from ui_verifier.common.json_utils import parse_json_response
from ui_verifier.model_config import model_name_for, temperature_for
from ui_verifier.verification_pipeline.claim_verification import ClaimVerifier
from ui_verifier.verification_pipeline.requirement_understanding import has_hidden_indicator
from ui_verifier.verification_pipeline.schemas import (
    ClaimStatus,
    ClaimVerificationResult,
    EvidenceItem,
    RequirementClaim,
    ScreenshotStep,
    UIEvaluability,
    UncertaintyReason,
)


def _short_text(text: str, max_chars: int = 700) -> str:
    normalized = " ".join(text.split()).strip()
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 3].rstrip()}..."


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
        if not isinstance(data, dict) or data.get("engine") != "tesseract":
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
        "SUPPORTED_WITH_CAVEAT": ClaimStatus.SUPPORTED_WITH_CAVEAT,
        "SUPPORTED WITH CAVEAT": ClaimStatus.SUPPORTED_WITH_CAVEAT,
        "SUPPORTED_BUT_NOT_PROVEN": ClaimStatus.SUPPORTED_WITH_CAVEAT,
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
    prompt_version = "GEMINI_IMAGE_CLAIM_VERIFICATION_V6"

    def __init__(
        self,
        *,
        flow_id: str,
        screenshot_steps: list[ScreenshotStep],
        cache_path: Path,
        model_name: str = model_name_for("demo_image_verifier"),
        temperature: float = temperature_for("demo_image_verifier"),
        max_images_per_claim: int = 6,
        max_retries: int = 0,
        max_api_calls: int | None = 10,
        include_sequence_context: bool = True,
        fallback: ClaimVerifier | None = None,
    ) -> None:
        self.flow_id = flow_id
        self.step_to_path = {step.step_index: Path(step.screenshot_path) for step in screenshot_steps}
        self.cache_path = cache_path
        self.model_name = model_name
        self.temperature = temperature
        self.max_images_per_claim = max_images_per_claim
        self.max_retries = max_retries
        self.max_api_calls = max_api_calls
        self.include_sequence_context = include_sequence_context
        self.fallback = fallback or ClaimVerifier()
        self.cache = self._load_cache()
        self._state_lock = threading.Lock()
        self._api_calls_started = 0
        self.diagnostics: dict[str, Any] = {
            "requested": 0,
            "api_calls": 0,
            "api_call_attempts": 0,
            "cache_hits": 0,
            "fallbacks": 0,
            "failures": [],
            "cache_path": str(cache_path),
            "model_name": model_name,
            "prompt_version": self.prompt_version,
            "max_retries": max_retries,
            "max_api_calls": max_api_calls,
            "include_sequence_context": include_sequence_context,
        }

    def verify(
        self,
        claim: RequirementClaim,
        evidence: list[EvidenceItem],
        *,
        ui_evaluability: UIEvaluability,
    ) -> ClaimVerificationResult:
        with self._state_lock:
            self.diagnostics["requested"] += 1
        if not claim.is_observable or has_hidden_indicator(claim.claim_text):
            return self.fallback.verify(claim, evidence, ui_evaluability=ui_evaluability)

        selected_steps = self._selected_steps(claim, evidence) or self._fallback_steps()
        payload = self._request_payload(claim, selected_steps, ui_evaluability=ui_evaluability)
        key = _cache_key(payload)
        with self._state_lock:
            cached = self.cache.get(key)

        if isinstance(cached, dict) and isinstance(cached.get("parsed"), dict):
            with self._state_lock:
                self.diagnostics["cache_hits"] += 1
            parsed = cached["parsed"]
        else:
            with self._state_lock:
                call_cap_reached = (
                    self.max_api_calls is not None and self._api_calls_started >= self.max_api_calls
                )
                if not call_cap_reached:
                    self._api_calls_started += 1
                    self.diagnostics["api_call_attempts"] += 1
            if call_cap_reached:
                self._record_fallback(
                    claim.claim_id,
                    f"Gemini image API call cap reached ({self.max_api_calls}).",
                )
                return self.fallback.verify(claim, evidence, ui_evaluability=ui_evaluability)
            try:
                parsed, raw = self._call_gemini(payload, selected_steps)
                with self._state_lock:
                    self.cache[key] = {"payload": payload, "parsed": parsed, "raw": raw}
                    self._save_cache()
            except Exception as exc:
                self._record_fallback(claim.claim_id, str(exc))
                return self.fallback.verify(claim, evidence, ui_evaluability=ui_evaluability)

        try:
            return self._result_from_gemini(claim, parsed, selected_steps)
        except Exception as exc:
            self._record_fallback(claim.claim_id, str(exc))
            return self.fallback.verify(claim, evidence, ui_evaluability=ui_evaluability)

    def _record_fallback(self, claim_id: str, error: str) -> None:
        with self._state_lock:
            self.diagnostics["fallbacks"] += 1
            self.diagnostics["failures"].append({"claim_id": claim_id, "error": error})

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

    def _selected_steps(self, claim: RequirementClaim, evidence: list[EvidenceItem]) -> list[int]:
        steps = sorted({item.step_index for item in evidence if item.step_index in self.step_to_path})
        if not steps:
            return []

        all_steps = sorted(self.step_to_path)
        candidates = list(steps)
        if self.include_sequence_context and self._needs_sequence_evidence(claim.claim_text):
            candidates.extend([all_steps[0], all_steps[-1]])

        if len(candidates) < self.max_images_per_claim:
            remaining_slots = self.max_images_per_claim - len(set(candidates))
            if remaining_slots > 0:
                positions = {
                    round(index * (len(all_steps) - 1) / max(remaining_slots - 1, 1))
                    for index in range(remaining_slots)
                }
                candidates.extend(all_steps[index] for index in sorted(positions))

        candidates = sorted(set(candidates))
        if len(candidates) <= self.max_images_per_claim:
            return candidates
        if self.max_images_per_claim == 1:
            return [candidates[len(candidates) // 2]]
        positions = {
            round(index * (len(candidates) - 1) / (self.max_images_per_claim - 1))
            for index in range(self.max_images_per_claim)
        }
        return [candidates[index] for index in sorted(positions)]

    @staticmethod
    def _needs_sequence_evidence(text: str) -> bool:
        return bool(
            re.search(
                r"\b("
                r"preserv(?:e|es|ed|ing)|retain(?:s|ed|ing)?|remain(?:s|ed|ing)?|"
                r"update(?:s|d|ing)?|synchroni[sz](?:e|es|ed|ing)|"
                r"while|continues?|later fields?|as the (?:shopper|user)|"
                r"before and after|after (?:entering|selecting|choosing|changing)|"
                r"cart|checkout|order summary|line items?|result state|results view|"
                r"confirmation|review step|review panel|before submitting"
                r")\b",
                text,
                re.IGNORECASE,
            )
        )

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
`evidence_step_indices` must contain only original step indices from the attached list above. Do not renumber the attachments by their position.

Strict rules:
- Only visible UI evidence counts.
- Verify the exact claim wording. Do not demand a downstream outcome when the claim only asks for a visible action, control, field, or navigation affordance.
- Strong frontend text, controls, selected states, summaries, or helper copy can support routine user-facing behavior even if the backend is not directly observable. Use SUPPORTED_WITH_CAVEAT when the hidden part is routine and directly represented by a specific UI proxy; use PARTIALLY_SUPPORTED when an important material part is still unobserved.
- For "all", "every", "complete", or "available" claims, a bounded or closed UI set can support the quantifier when the screen presents it as the relevant complete set. Open-world completeness, freshness, external correctness, security, or eligibility scope still needs explicit visible evidence or a caveat.
- Conversely, do not infer a downstream result, navigation outcome, submitted state, or completed action merely because a button or input form is visible. A later screenshot must visibly show that outcome.
- Do not substitute nearby objects for the exact object in the claim. For example, preserved cart items or quantities do not prove preservation of a digital ticket fulfillment choice.
- Digital/mobile fulfillment or delivery claims require visible fulfillment-specific evidence such as a delivery selector, digital/mobile ticket option, email delivery, mobile wallet, or selected fulfillment state. Generic ticket/cart/checkout evidence is not enough.
- Treat every material clause as conjunctive unless the wording explicitly offers alternatives. Evidence for only one side of "and", "as well as", or "in addition to" is not enough for SUPPORTED.
- Comparative or exclusive claims about anonymous versus signed-in users, owners versus non-owners, valid versus invalid inputs, before versus after states, or leaving and returning require both compared states unless a specific visible UI proxy states the restriction or distinction.
- Result, confirmation, or lookup-complete claims require a distinct post-action state with the relevant result or confirmation; pre-submit forms, entered values, and validation errors are not enough.
- Direct transition or direct return claims require a visible affordance or demonstrated navigation from the relevant page/state to the claimed target. A visible menu elsewhere is not enough for a direct path unless it is open or usable in that same state.
- Do not treat editable input fields as a separate review state, confirmation, synchronized summary, or preview unless that distinct UI component is visibly present.
- For claims about preservation, updates, synchronization, or other state changes, compare the attached screenshots chronologically rather than judging one screenshot in isolation.
- SUPPORTED requires clear visible screenshot evidence.
- SUPPORTED_WITH_CAVEAT means the claim is sufficiently supported for fulfillment, but the evidence is inferential, partially visible, or convention-based rather than airtight.
- PARTIALLY_SUPPORTED means some visible part is supported but important visible detail is missing or ambiguous.
- MISSING means the claim could be visible but the screenshots do not show enough.
- HIDDEN means the claim is about hidden/non-visual system behavior.
- CONTRADICTED requires visible counter-evidence: an incompatible UI state, an alternative flow that conflicts with the claim, an explicit error/failure state, or visible text/control behavior that makes the claim false.
- Mere absence of a required feature is MISSING unless the screenshots show a conflicting alternative or demonstrated behavior that contradicts the claim.
- Incomplete flow coverage, an unopened menu/control, or a state that was never exercised is MISSING, not CONTRADICTED.

Input JSON:
{json.dumps(payload, indent=2, ensure_ascii=False)}

Return JSON only:
{{
  "claim_id": "{payload["claim_id"]}",
  "claim_status": "SUPPORTED | SUPPORTED_WITH_CAVEAT | PARTIALLY_SUPPORTED | MISSING | HIDDEN | CONTRADICTED",
  "evidence_step_indices": [1],
  "uncertainty_reasons": ["TEXTUAL_AMBIGUITY | SCOPE_OR_CONTEXT_AMBIGUITY | QUANTIFIER_OR_COMPLETENESS_AMBIGUITY | EVIDENCE_INTERPRETATION_AMBIGUITY | FLOW_COVERAGE_GAP | UNVERIFIED_SYSTEM_OUTCOME | NONTRIVIAL_HIDDEN_PROPERTY"],
  "visible_observations": ["short visible observation tied to screenshot evidence"],
  "rationale": "short explanation"
}}
""".strip()

    def _call_gemini(self, payload: dict[str, Any], selected_steps: list[int]) -> tuple[dict[str, Any], str]:
        from ui_verifier.requirements.gemini_client import run_gemini

        image_bytes = [self.step_to_path[step_index].read_bytes() for step_index in selected_steps]
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                raw = run_gemini(
                    self._prompt(payload),
                    image_bytes,
                    model_name=self.model_name,
                    temperature=self.temperature,
                    usage_context={
                        "flow_id": self.flow_id,
                        "requirement_id": payload["requirement_id"],
                        "claim_id": payload["claim_id"],
                        "prompt_version": self.prompt_version,
                        "selected_evidence_step_indices": selected_steps,
                    },
                )
                parsed = parse_json_response(raw)
                if not isinstance(parsed, dict):
                    raise ValueError("Gemini response was not a JSON object.")
                with self._state_lock:
                    self.diagnostics["api_calls"] += 1
                return parsed, raw
            except Exception as exc:
                last_error = exc
                message = str(exc)
                if attempt >= self.max_retries or not self._is_retryable_gemini_error(message):
                    raise
                time.sleep(self._retry_delay_seconds(message))
        raise last_error or RuntimeError("Gemini call failed.")

    @staticmethod
    def _is_retryable_gemini_error(message: str) -> bool:
        return (
            "RESOURCE_EXHAUSTED" in message
            or "UNAVAILABLE" in message
            or "retry" in message.lower()
            or "not a JSON object" in message
            or "invalid json" in message.lower()
            or "parsed as json" in message.lower()
        )

    @staticmethod
    def _retry_delay_seconds(message: str) -> float:
        retry_delay = re.search(r"retryDelay['\"]?:\s*['\"]?(\d+)s", message)
        if retry_delay:
            return min(float(retry_delay.group(1)) + 1.0, 65.0)
        retry_in = re.search(r"retry in ([0-9.]+)s", message, flags=re.IGNORECASE)
        if retry_in:
            return min(float(retry_in.group(1)) + 1.0, 65.0)
        return 8.0 if "UNAVAILABLE" in message else 15.0

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
        invalid_positive_evidence = (
            status
            in {
                ClaimStatus.SUPPORTED,
                ClaimStatus.SUPPORTED_WITH_CAVEAT,
                ClaimStatus.PARTIALLY_SUPPORTED,
                ClaimStatus.CONTRADICTED,
            }
            and not step_indices
        )
        if invalid_positive_evidence:
            status = ClaimStatus.MISSING
        observations = parsed.get("visible_observations")
        if not isinstance(observations, list):
            observations = []
        observation_text = " ".join(_short_text(str(item), 260) for item in observations if str(item).strip())
        if not observation_text:
            observation_text = str(parsed.get("rationale") or "Gemini image verifier returned a claim decision.").strip()

        evidence: list[EvidenceItem] = []
        if status in {ClaimStatus.SUPPORTED, ClaimStatus.SUPPORTED_WITH_CAVEAT, ClaimStatus.PARTIALLY_SUPPORTED, ClaimStatus.CONTRADICTED}:
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
        if invalid_positive_evidence:
            rationale = (
                "The verifier returned a positive or contradictory decision without citing any attached screenshot "
                "step, so the claim was downgraded to missing evidence."
            )

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
            metadata={
                "prompt_group_id": None,
                "prompt_version": self.prompt_version,
                "model_name": self.model_name,
                "grouping_strategy": "per-claim",
                "attached_step_indices": selected_steps,
                "claim_selected_step_indices": selected_steps,
                "raw_model_label": str(parsed.get("claim_status") or parsed.get("status") or ""),
            },
        )

    @staticmethod
    def _confidence_for_status(status: ClaimStatus) -> float:
        if status == ClaimStatus.SUPPORTED:
            return 0.85
        if status == ClaimStatus.SUPPORTED_WITH_CAVEAT:
            return 0.72
        if status == ClaimStatus.PARTIALLY_SUPPORTED:
            return 0.6
        if status == ClaimStatus.CONTRADICTED:
            return 0.75
        if status == ClaimStatus.MISSING:
            return 0.0
        return 0.2
