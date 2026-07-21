from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from typing import Any

from ui_verifier.common.json_utils import parse_json_response
from ui_verifier.requirements.gemini_usage import empty_usage_summary
from ui_verifier.verification_pipeline.evidence_assets import build_screenshot_assets
from ui_verifier.verification_pipeline.gemini_image_claim_verifier import (
    GeminiImageClaimVerifier,
    _cache_key,
)
from ui_verifier.verification_pipeline.requirement_understanding import has_hidden_indicator
from ui_verifier.verification_pipeline.schemas import (
    ClaimStatus,
    ClaimVerificationResult,
    EvidenceItem,
    RequirementClaim,
    ScreenshotStep,
    UIEvaluability,
)


BatchJob = tuple[RequirementClaim, list[EvidenceItem], UIEvaluability]


class BatchedGeminiImageClaimVerifier(GeminiImageClaimVerifier):
    prompt_version = "GEMINI_BATCHED_IMAGE_CLAIM_VERIFICATION_V2_GROUNDED_REGIONS"

    def __init__(
        self,
        *,
        flow_id: str,
        screenshot_steps: list[ScreenshotStep],
        cache_path,
        grouping_strategy: str = "batched-topk",
        max_images_per_claim: int = 6,
        max_images_per_group: int | None = None,
        max_claims_per_group: int | None = None,
        group_workers: int = 1,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            flow_id=flow_id,
            screenshot_steps=screenshot_steps,
            cache_path=cache_path,
            max_images_per_claim=max_images_per_claim,
            **kwargs,
        )
        if grouping_strategy not in {"batched-topk", "single-call"}:
            raise ValueError("grouping_strategy must be 'batched-topk' or 'single-call'")
        if group_workers < 1:
            raise ValueError("group_workers must be at least 1")
        if max_claims_per_group is not None and max_claims_per_group < 1:
            raise ValueError("max_claims_per_group must be at least 1 when set")
        self.grouping_strategy = grouping_strategy
        self.max_images_per_group = max_images_per_group
        self.max_claims_per_group = max_claims_per_group
        self.group_workers = group_workers
        self.assets = build_screenshot_assets(screenshot_steps)
        self.diagnostics.update(
            {
                "grouping_strategy": grouping_strategy,
                "max_images_per_group": max_images_per_group,
                "max_claims_per_group": max_claims_per_group,
                "group_workers": group_workers,
                "groups": [],
                "group_count": 0,
                "images_attached_total": 0,
                "unique_images_attached": 0,
                "cached_content_tokens": 0,
                "usage": empty_usage_summary(),
                "asset_manifest": [
                    asset.to_metadata() for _, asset in sorted(self.assets.items())
                ],
            }
        )

    def verify_many(self, jobs: list[BatchJob]) -> list[ClaimVerificationResult]:
        results: list[ClaimVerificationResult | None] = [None] * len(jobs)
        batchable: list[dict[str, Any]] = []

        with self._state_lock:
            self.diagnostics["requested"] += len(jobs)

        for index, (claim, evidence, ui_evaluability) in enumerate(jobs):
            if not claim.is_observable or has_hidden_indicator(claim.claim_text):
                results[index] = self.fallback.verify(claim, evidence, ui_evaluability=ui_evaluability)
                continue
            selected_steps = self._selected_steps(claim, evidence) or self._fallback_steps()
            batchable.append(
                {
                    "index": index,
                    "claim": claim,
                    "evidence": evidence,
                    "ui_evaluability": ui_evaluability,
                    "selected_steps": selected_steps,
                }
            )

        groups = self._build_groups(batchable)
        with self._state_lock:
            self.diagnostics["group_count"] = len(groups)
            self.diagnostics["unique_images_attached"] = len(
                {
                    step_index
                    for group in groups
                    for step_index in group["step_indices"]
                }
            )
            self.diagnostics["images_attached_total"] = sum(len(group["step_indices"]) for group in groups)

        if self.group_workers == 1 or len(groups) <= 1:
            group_results = [self._verify_group(group) for group in groups]
        else:
            with ThreadPoolExecutor(max_workers=self.group_workers, thread_name_prefix="batched-verifier") as executor:
                group_results = list(executor.map(self._verify_group, groups))

        for group_result in group_results:
            for index, result in group_result.items():
                results[index] = result

        completed: list[ClaimVerificationResult] = []
        for index, result in enumerate(results):
            if result is None:
                claim, evidence, ui_evaluability = jobs[index]
                result = self.fallback.verify(claim, evidence, ui_evaluability=ui_evaluability)
            completed.append(result)
        return completed

    def _build_groups(self, batchable: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not batchable:
            return []
        if self.grouping_strategy == "single-call":
            return [
                self._group_payload(
                    group_id="G1",
                    jobs=batchable,
                    step_indices=sorted(self.step_to_path),
                )
            ]

        groups: list[dict[str, Any]] = []
        for item in batchable:
            selected = set(item["selected_steps"])
            overlapping_indices = [
                index for index, group in enumerate(groups) if selected.intersection(group["step_set"])
            ]
            if not overlapping_indices:
                groups.append({"jobs": [item], "step_set": set(selected)})
                continue

            first = overlapping_indices[0]
            groups[first]["jobs"].append(item)
            groups[first]["step_set"].update(selected)
            for index in reversed(overlapping_indices[1:]):
                groups[first]["jobs"].extend(groups[index]["jobs"])
                groups[first]["step_set"].update(groups[index]["step_set"])
                del groups[index]

        bounded_groups: list[dict[str, Any]] = []
        for group in groups:
            jobs = group["jobs"]
            chunk_size = self.max_claims_per_group or len(jobs)
            for start in range(0, len(jobs), chunk_size):
                chunk = jobs[start : start + chunk_size]
                bounded_groups.append(
                    {
                        "jobs": chunk,
                        "step_set": {
                            step
                            for item in chunk
                            for step in item["selected_steps"]
                        },
                    }
                )

        return [
            self._group_payload(
                group_id=f"G{index}",
                jobs=group["jobs"],
                step_indices=sorted(group["step_set"]),
            )
            for index, group in enumerate(bounded_groups, start=1)
        ]

    def _group_payload(
        self,
        *,
        group_id: str,
        jobs: list[dict[str, Any]],
        step_indices: list[int],
    ) -> dict[str, Any]:
        step_indices = [step for step in step_indices if step in self.step_to_path]
        if self.max_images_per_group is not None and len(step_indices) > self.max_images_per_group:
            step_indices = self._sample_steps(step_indices, self.max_images_per_group)
        claim_payloads = []
        for item in jobs:
            claim: RequirementClaim = item["claim"]
            claim_payloads.append(
                {
                    "claim_id": claim.claim_id,
                    "requirement_id": claim.requirement_id,
                    "requirement_text": claim.source_requirement_text,
                    "claim_text": claim.claim_text,
                    "ui_evaluability": item["ui_evaluability"].value,
                    "selected_evidence_step_indices": item["selected_steps"],
                }
            )
        return {
            "group_id": group_id,
            "jobs": jobs,
            "step_indices": step_indices,
            "payload": {
                "prompt_version": self.prompt_version,
                "flow_id": self.flow_id,
                "model_name": self.model_name,
                "group_id": group_id,
                "grouping_strategy": self.grouping_strategy,
                "attached_step_indices": step_indices,
                "screenshot_assets": [
                    self.assets[step].to_prompt_hint()
                    for step in step_indices
                    if step in self.assets
                ],
                "claims": claim_payloads,
            },
        }

    @staticmethod
    def _sample_steps(step_indices: list[int], max_steps: int) -> list[int]:
        if max_steps < 1:
            raise ValueError("max_images_per_group must be at least 1 when set")
        if len(step_indices) <= max_steps:
            return step_indices
        if max_steps == 1:
            return [step_indices[len(step_indices) // 2]]
        positions = {
            round(index * (len(step_indices) - 1) / (max_steps - 1))
            for index in range(max_steps)
        }
        return [step_indices[index] for index in sorted(positions)]

    def _verify_group(self, group: dict[str, Any]) -> dict[int, ClaimVerificationResult]:
        payload = group["payload"]
        key = _cache_key(payload)
        with self._state_lock:
            cached = self.cache.get(key)

        cache_hit = False
        usage: dict[str, int] = {}
        if isinstance(cached, dict) and isinstance(cached.get("parsed"), dict):
            parsed = cached["parsed"]
            cache_hit = True
            with self._state_lock:
                self.diagnostics["cache_hits"] += 1
        else:
            with self._state_lock:
                call_cap_reached = (
                    self.max_api_calls is not None and self._api_calls_started >= self.max_api_calls
                )
                if not call_cap_reached:
                    self._api_calls_started += 1
                    self.diagnostics["api_call_attempts"] += 1
            if call_cap_reached:
                self._record_group_fallback(group, f"Gemini image API call cap reached ({self.max_api_calls}).")
                return self._fallback_group(group)
            try:
                parsed, raw, usage = self._call_gemini_group(payload, group["step_indices"])
                with self._state_lock:
                    self.cache[key] = {"payload": payload, "parsed": parsed, "raw": raw, "usage": usage}
                    self._save_cache()
            except Exception as exc:
                self._record_group_fallback(group, str(exc))
                return self._fallback_group(group)

        parsed_by_claim = self._parse_group_claims(parsed)
        results: dict[int, ClaimVerificationResult] = {}
        for item in group["jobs"]:
            index = int(item["index"])
            claim: RequirementClaim = item["claim"]
            parsed_claim = parsed_by_claim.get(claim.claim_id)
            if parsed_claim is None:
                results[index] = self.fallback.verify(
                    claim,
                    item["evidence"],
                    ui_evaluability=item["ui_evaluability"],
                )
                continue
            try:
                result = self._result_from_batched_gemini(claim, parsed_claim, group)
            except Exception as exc:
                self._record_fallback(claim.claim_id, str(exc))
                result = self.fallback.verify(
                    claim,
                    item["evidence"],
                    ui_evaluability=item["ui_evaluability"],
                )
            results[index] = result

        with self._state_lock:
            self.diagnostics["groups"].append(
                {
                    "group_id": payload["group_id"],
                    "claim_ids": [item["claim"].claim_id for item in group["jobs"]],
                    "attached_step_indices": group["step_indices"],
                    "image_count": len(group["step_indices"]),
                    "cache_hit": cache_hit,
                    "include_sequence_context": self.include_sequence_context,
                    "usage": usage,
                }
            )
        return results

    def _call_gemini_group(
        self,
        payload: dict[str, Any],
        selected_steps: list[int],
    ) -> tuple[dict[str, Any], str, dict[str, int]]:
        from ui_verifier.requirements.gemini_client import run_gemini_with_usage

        image_bytes = [self.step_to_path[step_index].read_bytes() for step_index in selected_steps]
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = run_gemini_with_usage(
                    self._prompt(payload),
                    image_bytes,
                    model_name=self.model_name,
                    temperature=self.temperature,
                    usage_context={
                        "flow_id": self.flow_id,
                        "prompt_version": self.prompt_version,
                        "group_id": payload["group_id"],
                        "grouping_strategy": self.grouping_strategy,
                        "claim_ids": [claim["claim_id"] for claim in payload["claims"]],
                        "selected_evidence_step_indices": selected_steps,
                    },
                )
                parsed = parse_json_response(response.text)
                if not isinstance(parsed, dict):
                    raise ValueError("Gemini response was not a JSON object.")
                with self._state_lock:
                    self.diagnostics["api_calls"] += 1
                    self._add_usage(response.usage, response.usage_record)
                return parsed, response.text, response.usage
            except Exception as exc:
                last_error = exc
                message = str(exc)
                if attempt >= self.max_retries or not self._is_retryable_gemini_error(message):
                    raise
                import time

                time.sleep(self._retry_delay_seconds(message))
        raise last_error or RuntimeError("Gemini group call failed.")

    def _add_usage(self, usage: dict[str, int], usage_record: dict[str, Any]) -> None:
        usage_totals = self.diagnostics["usage"]
        usage_totals["request_count"] = int(usage_totals.get("request_count") or 0) + 1
        for key in ("input_tokens", "output_tokens", "thoughts_tokens", "total_tokens"):
            usage_totals[key] = int(usage_totals.get(key) or 0) + int(usage.get(key) or 0)
        self.diagnostics["cached_content_tokens"] = int(self.diagnostics.get("cached_content_tokens") or 0) + int(
            usage.get("cached_content_tokens") or 0
        )
        cost_usd = usage_record.get("estimated_cost_usd")
        if isinstance(cost_usd, (int, float)):
            usage_totals["estimated_cost_usd"] = float(usage_totals.get("estimated_cost_usd") or 0.0) + float(cost_usd)
        cost_eur = usage_record.get("estimated_cost_eur")
        if isinstance(cost_eur, (int, float)):
            existing = usage_totals.get("estimated_cost_eur")
            usage_totals["estimated_cost_eur"] = float(existing or 0.0) + float(cost_eur)

    @staticmethod
    def _parse_group_claims(parsed: dict[str, Any]) -> dict[str, dict[str, Any]]:
        claims = parsed.get("claims")
        if not isinstance(claims, list):
            claims = parsed.get("results")
        if not isinstance(claims, list):
            return {}
        parsed_by_id: dict[str, dict[str, Any]] = {}
        for item in claims:
            if not isinstance(item, dict):
                continue
            claim_id = str(item.get("claim_id") or "").strip()
            if claim_id:
                parsed_by_id[claim_id] = item
        return parsed_by_id

    def _result_from_batched_gemini(
        self,
        claim: RequirementClaim,
        parsed: dict[str, Any],
        group: dict[str, Any],
    ) -> ClaimVerificationResult:
        result = self._result_from_gemini(claim, parsed, group["step_indices"])
        return result.model_copy(
            update={
                "metadata": {
                    **result.metadata,
                    "prompt_group_id": group["payload"]["group_id"],
                    "prompt_version": self.prompt_version,
                    "model_name": self.model_name,
                    "grouping_strategy": self.grouping_strategy,
                    "attached_step_indices": group["step_indices"],
                    "claim_selected_step_indices": next(
                        (
                            item["selected_steps"]
                            for item in group["jobs"]
                            if item["claim"].claim_id == claim.claim_id
                        ),
                        [],
                    ),
                    "raw_model_label": str(parsed.get("claim_status") or parsed.get("status") or ""),
                }
            }
        )

    def _fallback_group(self, group: dict[str, Any]) -> dict[int, ClaimVerificationResult]:
        results: dict[int, ClaimVerificationResult] = {}
        for item in group["jobs"]:
            results[int(item["index"])] = self.fallback.verify(
                item["claim"],
                item["evidence"],
                ui_evaluability=item["ui_evaluability"],
            )
        return results

    def _record_group_fallback(self, group: dict[str, Any], error: str) -> None:
        with self._state_lock:
            self.diagnostics["fallbacks"] += len(group["jobs"])
            self.diagnostics["failures"].append(
                {
                    "group_id": group["payload"]["group_id"],
                    "claim_ids": [item["claim"].claim_id for item in group["jobs"]],
                    "error": error,
                }
            )

    def _prompt(self, payload: dict[str, Any]) -> str:
        return f"""
You are verifying multiple UI requirement claims from shared screenshot images.

The attached screenshot images are shared evidence for this prompt. They are attached in this exact order:
{payload["attached_step_indices"]}

Verify each claim independently. Shared screenshots are context, not automatic evidence for every claim.
Each claim also lists the top-k evidence steps selected for that claim; you may use any attached screenshot if it is visibly relevant.
OCR hints are optional image-derived Tesseract OCR. Treat OCR as a hint only; verify against the screenshots.
`evidence_step_indices` must contain only original step indices from the attached list above. Do not renumber attachments by position.

Strict label rules:
- Verify the exact claim wording. Do not improve, generalize, strengthen, or reinterpret it.
- Strong frontend text, controls, selected states, summaries, or helper copy can support routine user-facing behavior even when the backend is not directly observable.
- Hidden behavior needs uncertainty unless the frontend strongly and specifically represents that behavior.
- Do not require behavior traces for every valid requirement, but do not infer hidden guarantees from weak UI hints.
- Treat every material clause as conjunctive unless the wording explicitly offers alternatives.
- A bounded or closed UI set can support "all" or "complete"; open-world completeness, freshness, security, eligibility, or external correctness needs explicit visible evidence or a caveat.
- Result, confirmation, lookup-complete, synchronization, preservation, or state-change claims require the relevant state or a strong visible proxy.
- Direct transition claims require a visible affordance or demonstrated navigation from the relevant state.
- NOT_FULFILLED requires contradiction: an incompatible UI state, a conflicting alternative, explicit failure, or visible behavior that makes the claim false.
- Mere missing evidence usually means ABSTAIN at the requirement level, so use MISSING for a claim unless there is visible counter-evidence.
- For every cited screenshot, identify the smallest semantically sufficient visible region or regions for the exact claim. Do not box a page title or nearby keyword when a specific value, control, message, list, range, or state is the evidence.
- Return multiple regions when the claim depends on multiple indicators. Do not invent a local box for absent, whole-screen, or transition-only evidence.
- `box_2d` uses `[ymin, xmin, ymax, xmax]` normalized to integers from 0 to 1000 relative to the original attached screenshot.

Claim statuses:
- SUPPORTED: clear visible screenshot evidence.
- SUPPORTED_WITH_CAVEAT: sufficiently supported, but inferential, convention-based, or not airtight.
- PARTIALLY_SUPPORTED: some visible part is supported but an important material part is missing or ambiguous.
- MISSING: the claim could be visible, but attached screenshots do not show enough.
- HIDDEN: the claim is dominated by non-visual system behavior.
- CONTRADICTED: visible counter-evidence conflicts with the claim.

Input JSON:
{json.dumps(payload, indent=2, ensure_ascii=False)}

Return JSON only:
{{
  "claims": [
    {{
      "claim_id": "REQ-1-C1",
      "claim_status": "SUPPORTED | SUPPORTED_WITH_CAVEAT | PARTIALLY_SUPPORTED | MISSING | HIDDEN | CONTRADICTED",
      "evidence_step_indices": [1],
      "uncertainty_reasons": ["TEXTUAL_AMBIGUITY | SCOPE_OR_CONTEXT_AMBIGUITY | QUANTIFIER_OR_COMPLETENESS_AMBIGUITY | EVIDENCE_INTERPRETATION_AMBIGUITY | FLOW_COVERAGE_GAP | UNVERIFIED_SYSTEM_OUTCOME | NONTRIVIAL_HIDDEN_PROPERTY"],
      "visible_observations": ["short visible observation tied to screenshot evidence"],
      "evidence_regions": [
        {{
          "step_index": 1,
          "box_2d": [100, 120, 240, 760],
          "description": "specific visible indicator captured by this region",
          "role": "SUPPORTING | CONTRADICTING | PARTIAL",
          "localizability": "LOCAL_REGION | MULTI_REGION_PART"
        }}
      ],
      "rationale": "short explanation"
    }}
  ]
}}
""".strip()
