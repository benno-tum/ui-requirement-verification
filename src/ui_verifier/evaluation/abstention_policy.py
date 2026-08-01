from __future__ import annotations

from copy import deepcopy
from typing import Any


SUPPORTED = {"SUPPORTED", "SUPPORTED_WITH_CAVEAT"}


def forced_evidence_label(result: dict[str, Any]) -> tuple[str, str]:
    """Choose a non-abstaining label from already frozen claim decisions.

    This is a closed-world policy counterfactual, not a new model prediction.
    """
    claims = [claim for claim in result.get("claims") or [] if claim.get("is_core", True)]
    statuses = [str(claim.get("status") or "") for claim in claims]
    has_evidence = bool(result.get("evidence")) or any(bool(claim.get("evidence")) for claim in claims)

    if "CONTRADICTED" in statuses:
        return "NOT_FULFILLED", "At least one central frozen claim decision is contradicted."
    if claims and all(status in SUPPORTED for status in statuses) and has_evidence:
        return "FULFILLED", "All central frozen claim decisions have visible support."
    if has_evidence and any(status in SUPPORTED | {"PARTIALLY_SUPPORTED"} for status in statuses):
        return "PARTIALLY_FULFILLED", "Some visible support exists, but the fulfilled gate is not met."
    return (
        "NOT_FULFILLED",
        "The forced closed-world policy treats insufficient visible support as a negative decision.",
    )


def reaggregate_without_abstention(run: dict[str, Any]) -> dict[str, Any]:
    output = deepcopy(run)
    changed = 0
    for result in output.get("results") or []:
        original = str(result.get("final_label") or "")
        if original != "ABSTAIN":
            continue
        forced_label, rationale = forced_evidence_label(result)
        metadata = dict(result.get("metadata") or {})
        metadata["abstention_policy_ablation"] = {
            "policy": "forced_evidence_closed_world_v1",
            "original_label": original,
            "forced_label": forced_label,
            "interpretation": "Deterministic policy counterfactual over frozen claim outputs; not a new LLM prediction.",
        }
        result["metadata"] = metadata
        result["final_label"] = forced_label
        result["rationale"] = rationale
        changed += 1

    metadata = dict(output.get("metadata") or {})
    metadata["abstention_policy_ablation"] = {
        "policy": "forced_evidence_closed_world_v1",
        "changed_abstentions": changed,
        "api_calls": 0,
        "additional_tokens": 0,
        "scope": "aggregation-policy ablation",
    }
    output["metadata"] = metadata
    return output
