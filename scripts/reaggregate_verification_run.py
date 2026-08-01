from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from ui_verifier.common.json_utils import parse_json_response
from ui_verifier.requirements.gemini_client import run_gemini_with_usage


BASE_DIR = Path(__file__).resolve().parents[1]
PROMPT_VERSION = "SEMANTIC_REQUIREMENT_AGGREGATION_V1"
LABELS = {"FULFILLED", "PARTIALLY_FULFILLED", "NOT_FULFILLED", "ABSTAIN"}
EVIDENCE_BASES = {
    "DIRECT_UI_EVIDENCE",
    "VISIBLE_SUCCESS_PROXY",
    "EXTRAVISUAL_INFERENCE",
    "NO_EVIDENCE",
}
POSITIVE_BASES = {"DIRECT_UI_EVIDENCE", "VISIBLE_SUCCESS_PROXY"}
POSITIVE_CLAIM_STATUSES = {"SUPPORTED", "SUPPORTED_WITH_CAVEAT", "PARTIALLY_SUPPORTED"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reaggregate frozen claim results with a text-only Gemini call.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--max-requirements-per-call",
        type=int,
        default=-1,
        help="Bound independent requirement-level aggregation prompts. Use -1 for one prompt.",
    )
    return parser.parse_args()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _aggregation_payload(run: dict[str, Any]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for result in run.get("results", []):
        claims = []
        for claim in result.get("claims", []):
            claims.append(
                {
                    "claim_id": claim.get("claim_id"),
                    "claim_text": claim.get("claim_text"),
                    "status": claim.get("status"),
                    "is_core": claim.get("is_core", True),
                    "is_observable": claim.get("is_observable", True),
                    "uncertainty_reasons": claim.get("uncertainty_reasons", []),
                    "rationale": claim.get("rationale"),
                    "evidence": [
                        {
                            "step_index": evidence.get("step_index"),
                            "visible_observation": evidence.get("visible_observation"),
                            "bbox": evidence.get("bbox"),
                            "matched_text": (evidence.get("bbox_metadata") or {}).get("matched_text"),
                        }
                        for evidence in claim.get("evidence", [])
                    ],
                }
            )
        payload.append(
            {
                "requirement_id": result.get("requirement_id"),
                "requirement_text": result.get("requirement_text"),
                "ui_evaluability": result.get("ui_evaluability"),
                "claims": claims,
            }
        )
    return payload


def _prompt(payload: list[dict[str, Any]]) -> str:
    return f"""You are aggregating frozen UI claim-verification results into requirement-level labels.
Prompt version: {PROMPT_VERSION}

You must not change claim text, claim status, evidence, or observability. You receive no screenshots. Use only the
frozen claim records below.

For every claim, classify evidence_basis as exactly one of:
- DIRECT_UI_EVIDENCE: visible UI content directly establishes the exact claim.
- VISIBLE_SUCCESS_PROXY: a visible UI state is an accepted proxy for a routine user-facing outcome.
- EXTRAVISUAL_INFERENCE: support depends on external knowledge or inference about implementation, platform,
  architecture, licensing, legal acceptance, backend behavior, security, persistence, or other hidden properties.
- NO_EVIDENCE: no evidence supports the claim.

Aggregation rules:
- FULFILLED requires every core claim to be supported by DIRECT_UI_EVIDENCE or an appropriate
  VISIBLE_SUCCESS_PROXY.
- PARTIALLY_FULFILLED requires at least one complete core obligation to have DIRECT_UI_EVIDENCE or an appropriate
  VISIBLE_SUCCESS_PROXY, while another core obligation remains missing, hidden, contradicted, or unresolved.
- EXTRAVISUAL_INFERENCE never creates FULFILLED or PARTIALLY_FULFILLED.
- Runtime information does not prove implementation language or platform independence.
- A named look-and-feel does not prove a UI framework unless the screenshot explicitly states that relationship.
- Contributor names do not prove license terms.
- NOT_FULFILLED requires visible counter-evidence, not mere absence.
- Otherwise choose ABSTAIN.
- SUPPORTED_WITH_CAVEAT and PARTIALLY_SUPPORTED do not automatically earn positive requirement-level credit; inspect
  whether their cited evidence directly supports a complete original obligation.

Return JSON only:
{{
  "requirements": [
    {{
      "requirement_id": "...",
      "proposed_label": "FULFILLED | PARTIALLY_FULFILLED | NOT_FULFILLED | ABSTAIN",
      "decisive_claim_ids": ["..."],
      "claim_evidence_basis": {{"CLAIM-ID": "DIRECT_UI_EVIDENCE | VISIBLE_SUCCESS_PROXY | EXTRAVISUAL_INFERENCE | NO_EVIDENCE"}},
      "abstention_reason": "string or null",
      "rationale": "short requirement-level explanation"
    }}
  ]
}}

Frozen claim results:
{json.dumps(payload, indent=2, ensure_ascii=False)}
"""


def _validate_decision(result: dict[str, Any], decision: dict[str, Any]) -> tuple[str, list[str]]:
    proposed = str(decision.get("proposed_label") or "ABSTAIN")
    interventions: list[str] = []
    if proposed not in LABELS:
        return "ABSTAIN", ["INVALID_LABEL"]
    if result.get("ui_evaluability") == "NOT_UI_VERIFIABLE" and proposed != "ABSTAIN":
        return "ABSTAIN", ["NOT_UI_VERIFIABLE_GATE"]

    claims = {str(claim.get("claim_id")): claim for claim in result.get("claims", [])}
    bases = decision.get("claim_evidence_basis") if isinstance(decision.get("claim_evidence_basis"), dict) else {}
    normalized_bases = {str(claim_id): str(basis) for claim_id, basis in bases.items() if str(basis) in EVIDENCE_BASES}
    positive_claim_ids = {
        claim_id
        for claim_id, claim in claims.items()
        if claim.get("status") in POSITIVE_CLAIM_STATUSES
        and normalized_bases.get(claim_id) in POSITIVE_BASES
        and bool(claim.get("evidence"))
    }
    contradicted = any(claim.get("status") == "CONTRADICTED" for claim in claims.values())

    if proposed in {"FULFILLED", "PARTIALLY_FULFILLED"} and not positive_claim_ids:
        interventions.append("NO_DIRECT_OR_PROXY_SUPPORTED_CORE_CLAIM")
        proposed = "ABSTAIN"
    if proposed == "NOT_FULFILLED" and not contradicted:
        interventions.append("NO_VISIBLE_CONTRADICTION")
        proposed = "ABSTAIN"
    return proposed, interventions


def _combine_usage(usages: list[dict[str, Any]]) -> dict[str, int]:
    fields = {field for usage in usages for field in usage}
    return {
        field: sum(int(usage.get(field, 0) or 0) for usage in usages)
        for field in fields
    }


def main() -> None:
    load_dotenv(BASE_DIR / ".env")
    args = parse_args()
    if args.max_requirements_per_call == 0 or args.max_requirements_per_call < -1:
        raise ValueError("max_requirements_per_call must be -1 or at least 1")
    source = json.loads(args.input.read_text(encoding="utf-8"))
    payload = _aggregation_payload(source)
    chunk_size = args.max_requirements_per_call if args.max_requirements_per_call > 0 else len(payload)
    decisions: list[dict[str, Any]] = []
    usages: list[dict[str, Any]] = []
    usage_records: list[dict[str, Any]] = []
    for offset in range(0, len(payload), chunk_size):
        chunk = payload[offset : offset + chunk_size]
        response = run_gemini_with_usage(
            _prompt(chunk),
            [],
            args.model,
            temperature=args.temperature,
            usage_context={
                "role": "semantic_requirement_aggregation",
                "prompt_version": PROMPT_VERSION,
                "source_run": str(args.input),
                "requirement_batch": offset // chunk_size + 1,
            },
        )
        parsed = parse_json_response(response.text)
        chunk_decisions = parsed.get("requirements") if isinstance(parsed, dict) else None
        if not isinstance(chunk_decisions, list):
            raise ValueError("Semantic aggregation response must contain a requirements list.")
        decisions.extend(item for item in chunk_decisions if isinstance(item, dict))
        usages.append(response.usage)
        usage_records.append(response.usage_record)
    decision_by_id = {str(item.get("requirement_id")): item for item in decisions if isinstance(item, dict)}

    output = deepcopy(source)
    output["metadata"] = {
        **output.get("metadata", {}),
        "pipeline": "semantic_reaggregation",
        "aggregation_method": "constrained_text_only_gemini",
        "aggregation_model": args.model,
        "aggregation_temperature": args.temperature,
        "aggregation_prompt_version": PROMPT_VERSION,
        "source_run_path": str(args.input),
        "source_run_sha256": _sha256(args.input),
        "claims_frozen": True,
        "screenshots_reattached": False,
        "aggregation_usage": _combine_usage(usages),
        "aggregation_usage_record": usage_records[0] if len(usage_records) == 1 else None,
        "aggregation_usage_records": usage_records,
        "aggregation_batch_count": len(usage_records),
        "max_requirements_per_call": args.max_requirements_per_call,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    for result in output.get("results", []):
        requirement_id = str(result.get("requirement_id"))
        decision = decision_by_id.get(requirement_id)
        if decision is None:
            decision = {
                "requirement_id": requirement_id,
                "proposed_label": "ABSTAIN",
                "decisive_claim_ids": [],
                "claim_evidence_basis": {},
                "abstention_reason": "Semantic aggregator omitted this requirement.",
                "rationale": "No semantic aggregation decision was returned.",
            }
        pre_aggregation_label = result.get("final_label")
        validated_label, interventions = _validate_decision(result, decision)
        result["final_label"] = validated_label
        result["rationale"] = str(decision.get("rationale") or "Semantic aggregation returned no rationale.")
        result["metadata"] = {
            **result.get("metadata", {}),
            "pre_aggregation_label": pre_aggregation_label,
            "semantic_aggregation": decision,
            "aggregation_safety_interventions": interventions,
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"flow={output.get('flow_id')} requirements={len(output.get('results', []))} out={args.out}")
    for result in output.get("results", []):
        decision = result.get("metadata", {}).get("semantic_aggregation", {})
        print(
            f"{result.get('requirement_id')}: proposed={decision.get('proposed_label')} "
            f"validated={result.get('final_label')} "
            f"interventions={result.get('metadata', {}).get('aggregation_safety_interventions', [])}"
        )


if __name__ == "__main__":
    main()
