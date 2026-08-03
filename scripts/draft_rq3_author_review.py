from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    BASE_DIR
    / "data/annotations/evaluation_audits/rq3_final_20260802"
    / "rq3_author_error_audit_form.json"
)
DEFAULT_OUTPUT = (
    BASE_DIR
    / "outputs/019fbfa1-94d4-7bb1-9a8a-81dd427302cf"
    / "rq3_ai_draft_error_audit_form.json"
)
DEFAULT_SUMMARY = DEFAULT_OUTPUT.with_name("rq3_ai_draft_summary.json")

ADDED_PRIMARY_CATEGORIES = [
    "APPROPRIATE_ABSTENTION",
    "TRACEABILITY_FAILURE",
    "PREDICTION_INSTABILITY",
]
ADDED_EVIDENCE_TAGS = ["RUN_INSTABILITY"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a reproducible AI draft of the frozen RQ3 author review. "
            "The output is explicitly provisional and must not replace author approval."
        )
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def has_reason(item: dict[str, Any], reason: str) -> bool:
    return reason in item.get("eligibility_reasons", [])


def first_visible_sentence(text: str, limit: int = 360) -> str:
    compact = re.sub(r"\s+", " ", str(text or "")).strip()
    if not compact:
        return "The stored screenshots and reviewed evidence steps determine the reference label"
    sentences = re.split(r"(?<=[.!?])\s+", compact)
    result = sentences[0].rstrip(".")
    if len(result) < 90 and len(sentences) > 1:
        result = f"{result}. {sentences[1].rstrip('.')}"
    if len(result) > limit:
        result = result[: limit - 1].rsplit(" ", 1)[0] + "…"
    return result


def suspicious_gold(item: dict[str, Any]) -> tuple[bool, str]:
    gold = str(item["gold_label"])
    rationale = str(item.get("gold_rationale") or "")
    lowered = rationale.lower()
    if gold == "FULFILLED":
        patterns = [
            "hidden business logic",
            "eligibility reason is not visible",
            "not fully verified",
            "cannot be proven",
            "workflow is missing",
            "not fully covered",
            "not captured",
            "cannot establish that every",
            "not directly demonstrated",
        ]
        for phrase in patterns:
            if phrase in lowered:
                return True, f"Gold is FULFILLED although its rationale says '{phrase}'."
    if gold == "PARTIALLY_FULFILLED":
        unsupported_core = [
            "central owner-only access rule cannot be judged",
            "completeness of returned cruises cannot be judged",
            "comparative requirement cannot be reliably judged",
        ]
        for phrase in unsupported_core:
            if phrase in lowered:
                return True, f"Gold is PARTIALLY_FULFILLED although the core claim '{phrase}'."
    return False, ""


def requirement_tags(item: dict[str, Any], primary: str) -> list[str]:
    requirement_id = str(item.get("requirement_id") or "")
    text = str(item.get("requirement_text") or "").lower()
    rationale = str(item.get("gold_rationale") or "").lower()
    combined = f"{text} {rationale}"
    tags: list[str] = []
    if re.search(r"\b(all|every|each|any|always|only|entire|complete|comprehensive)\b", text):
        tags.append("UNIVERSAL_OR_COMPLETENESS")
    if re.search(r"\b(compare|comparison|different|distinguish|distinct|ranking|alternative|than|versus|equivalent|same)\w*\b", text):
        tags.append("COMPARATIVE_OR_DISTINCT")
    if re.search(
        r"\b(authenticat|authoriz|backend|deliver|send|email|notification|payment|inventory|availability|validity|enforc|security|account owner)\w*\b",
        combined,
    ):
        tags.append("HIDDEN_BACKEND_OR_EXTERNAL")
    if re.search(
        r"\b(persist|preserv|retain|remain|carry|subsequent|return|revisit|session|later visit|across pages|between pages|current context)\w*\b",
        combined,
    ):
        tags.append("PERSISTENCE_OR_CROSS_STEP")
    if re.search(
        r"\b(result|review|summary|cart|checkout|confirmation|after submission|downstream|purchase|final state|search results?)\w*\b",
        combined,
    ):
        tags.append("LATE_RESULT_OR_CART_STATE")
    gold_steps = sorted(set(int(v) for v in item.get("gold_evidence_steps", [])))
    cross_step = "PERSISTENCE_OR_CROSS_STEP" in tags
    non_adjacent = len(gold_steps) > 1 and gold_steps[-1] - gold_steps[0] >= 4
    if cross_step or non_adjacent or re.search(r"\b(across|between|while moving|sequence|earlier|later)\b", text):
        tags.append("MULTI_SCREEN_COMPOSITION")
    if requirement_id.startswith("CONTR-") or re.search(
        r"\b(no|not|without|never|must not|shall not|rather than)\b", text
    ):
        tags.append("NEGATION_OR_CONTRASTIVE")
    if primary in {"LABEL_BOUNDARY_DISAGREEMENT", "GOLD_REVIEW_CANDIDATE"}:
        tags.append("LABEL_SCHEMA_AMBIGUITY")
    if not tags:
        tags.append("ORDINARY_LOCAL_UI")
    return unique(tags)


def decisive_supplied(item: dict[str, Any]) -> bool:
    gold = set(int(v) for v in item.get("gold_evidence_steps", []))
    supplied = set(int(v) for v in item.get("supplied_step_indices", []))
    return bool(gold) and gold.issubset(supplied)


def classify_primary(item: dict[str, Any]) -> tuple[str, str, str]:
    gold = str(item["gold_label"])
    predicted = str(item["predicted_label"])
    supplied = decisive_supplied(item)
    missing = bool(item.get("missing_gold_evidence_steps"))
    unstable = has_reason(item, "UNSTABLE_ACROSS_REPETITIONS")
    candidate, candidate_reason = suspicious_gold(item)
    if candidate:
        return "GOLD_REVIEW_CANDIDATE", "LOW", candidate_reason
    if gold == predicted:
        if gold == "ABSTAIN":
            return (
                "APPROPRIATE_ABSTENTION",
                "HIGH",
                "The model preserved the reference abstention; zero evidence overlap is not treated as a trace failure for an abstaining verdict.",
            )
        if has_reason(item, "LABEL_CORRECT_EVIDENCE_NO_OVERLAP"):
            return (
                "TRACEABILITY_FAILURE",
                "HIGH",
                "The requirement label is correct, but the cited evidence does not overlap the reviewed evidence steps.",
            )
        if unstable:
            return (
                "PREDICTION_INSTABILITY",
                "MEDIUM",
                "The current label matches gold, but the repeated runs disagree.",
            )
        return (
            "EVIDENCE_INTERPRETATION_ERROR",
            "LOW",
            "The row was eligible without a current label error; inspect the stored trace manually.",
        )
    if predicted == "FULFILLED":
        return (
            "UNSAFE_OVER_FULFILLMENT",
            "HIGH",
            "FULFILLED exceeds the evidence-bounded reference label.",
        )
    if predicted == "NOT_FULFILLED":
        if gold == "ABSTAIN":
            return (
                "UNSUPPORTED_CONCRETE_NEGATIVE",
                "HIGH",
                "The screenshots do not provide the visible contradiction required for a concrete negative.",
            )
        if missing:
            return (
                "EVIDENCE_SELECTION_MISS",
                "HIGH",
                "Reviewed evidence exists in the complete flow but is absent from the supplied screenshots.",
            )
        return (
            "EVIDENCE_INTERPRETATION_ERROR",
            "MEDIUM",
            "Reviewed positive or partial evidence was supplied, but the model converted it into a concrete negative.",
        )
    if predicted == "ABSTAIN":
        if missing:
            return (
                "EVIDENCE_SELECTION_MISS",
                "HIGH",
                "The selected screenshots omit at least one reviewed evidence step.",
            )
        if supplied:
            return (
                "EXCESSIVE_ABSTENTION",
                "HIGH",
                "All reviewed evidence steps were supplied, but the model still abstained.",
            )
        return (
            "LABEL_BOUNDARY_DISAGREEMENT",
            "LOW",
            "The stored trace does not establish whether abstention reflects missing evidence or the operational label boundary.",
        )
    if missing:
        return (
            "EVIDENCE_SELECTION_MISS",
            "HIGH",
            "The selected screenshots omit at least one reviewed evidence step.",
        )
    if gold == "ABSTAIN":
        return (
            "LABEL_BOUNDARY_DISAGREEMENT",
            "LOW",
            "The model inferred partial support where the reference requires abstention from an unobservable core claim.",
        )
    return (
        "EVIDENCE_INTERPRETATION_ERROR",
        "MEDIUM",
        "The supplied visible evidence was mapped to the wrong non-abstaining label.",
    )


def evidence_tags(item: dict[str, Any], primary: str, req_tags: list[str]) -> list[str]:
    gold_steps = set(int(v) for v in item.get("gold_evidence_steps", []))
    supplied_steps = set(int(v) for v in item.get("supplied_step_indices", []))
    tags: list[str] = []
    if gold_steps and gold_steps.intersection(supplied_steps):
        tags.append("DECISIVE_STEP_SELECTED")
    if gold_steps and not gold_steps.issubset(supplied_steps):
        tags.append("DECISIVE_STEP_NOT_SELECTED")
    rationale = str(item.get("gold_rationale") or "").lower()
    gold = str(item["gold_label"])
    if gold == "ABSTAIN" and re.search(r"entry point|control|button|form|action|mechanism", rationale):
        tags.append("ONLY_ENTRY_POINT_VISIBLE")
    if gold == "ABSTAIN" and re.search(r"outcome|result|after|submission|transfer|enforcement|delivered", rationale):
        tags.append("ACTION_WITHOUT_RESULT")
    if gold == "PARTIALLY_FULFILLED" or re.search(r"partly|partial|some|not fully|only one", rationale):
        tags.append("PARTIAL_CLAIM_COVERAGE")
    if gold == "ABSTAIN" and re.search(r"not visible|not shown|cannot|hidden|outside|no observable|not captured", rationale):
        tags.append("NO_OBSERVABLE_PROXY")
    full_steps = [int(v) for v in item.get("full_flow_step_indices", [])]
    if gold_steps and full_steps and max(gold_steps) >= max(full_steps) - 2:
        tags.append("LATE_STEP")
    if "LATE_RESULT_OR_CART_STATE" in req_tags and gold_steps:
        tags.append("LATE_STEP")
    if "PERSISTENCE_OR_CROSS_STEP" in req_tags:
        tags.append("CROSS_STEP_STATE")
    if primary == "TRACEABILITY_FAILURE":
        tags.append("LABEL_CORRECT_BUT_TRACEABILITY_WRONG")
    if has_reason(item, "UNSTABLE_ACROSS_REPETITIONS"):
        tags.append("RUN_INSTABILITY")
    if not tags:
        tags.append("DECISIVE_STEP_SELECTED" if decisive_supplied(item) else "NO_OBSERVABLE_PROXY")
    return unique(tags)


def rationale_for(item: dict[str, Any], primary: str) -> str:
    visible = first_visible_sentence(str(item.get("gold_rationale") or ""))
    gold_steps = ", ".join(str(v) for v in item.get("gold_evidence_steps", [])) or "none"
    predicted_steps = ", ".join(str(v) for v in item.get("predicted_evidence_steps", [])) or "none"
    missing = ", ".join(str(v) for v in item.get("missing_gold_evidence_steps", [])) or "none"
    if primary == "APPROPRIATE_ABSTENTION":
        return f"{visible}; the screenshots therefore support retaining ABSTAIN rather than asserting a concrete outcome."
    if primary == "TRACEABILITY_FAILURE":
        return f"{visible}; reviewed steps {gold_steps} support the label, but the cited steps ({predicted_steps}) do not overlap them."
    if primary == "PREDICTION_INSTABILITY":
        labels = "; ".join([str(item["predicted_label"]), *map(str, item.get("repetition_labels", []))])
        return f"The same stored evidence produced labels {labels}; the current correct result is therefore not run-stable."
    if primary == "GOLD_REVIEW_CANDIDATE":
        return f"{visible}; this wording conflicts with the frozen {item['gold_label']} label and requires author re-inspection before model-error attribution."
    if primary == "UNSAFE_OVER_FULFILLMENT":
        return f"{visible}; predicting FULFILLED overstates what the screenshots visibly establish."
    if primary == "UNSUPPORTED_CONCRETE_NEGATIVE":
        return f"{visible}; no visible contradiction supports replacing the reference {item['gold_label']} with NOT_FULFILLED."
    if primary == "EXCESSIVE_ABSTENTION":
        return f"{visible}; all reviewed evidence steps ({gold_steps}) were supplied, so ABSTAIN is unnecessarily conservative."
    if primary == "EVIDENCE_SELECTION_MISS":
        return f"{visible}; the supplied screenshot subset omits reviewed step(s) {missing}, preventing a defensible decision."
    if primary == "LABEL_BOUNDARY_DISAGREEMENT":
        return f"{visible}; the remaining disagreement is whether that visible support crosses the {item['gold_label']}–{item['predicted_label']} boundary."
    return f"{visible}; the relevant reviewed steps ({gold_steps}) were supplied, but the model mapped their visible content to {item['predicted_label']}."


def draft_item(item: dict[str, Any]) -> dict[str, Any]:
    drafted = deepcopy(item)
    primary, confidence, basis = classify_primary(item)
    req_tags = requirement_tags(item, primary)
    ev_tags = evidence_tags(item, primary, req_tags)
    gold_candidate = primary == "GOLD_REVIEW_CANDIDATE"
    priority = (
        "PRIORITY"
        if confidence == "LOW"
        or gold_candidate
        or has_reason(item, "UNSTABLE_ACROSS_REPETITIONS")
        else "SPOT_CHECK"
    )
    drafted["author_review"] = {
        "decisive_evidence_supplied": decisive_supplied(item),
        "primary_category": primary,
        "requirement_tags": req_tags,
        "evidence_tags": ev_tags,
        "visible_evidence_rationale": rationale_for(item, primary),
        "gold_review_candidate": gold_candidate,
        "review_status": "DRAFT_COMPLETE",
    }
    drafted["ai_draft_metadata"] = {
        "confidence": confidence,
        "check_priority": priority,
        "classification_basis": basis,
        "user_decision": "PENDING",
        "user_corrected_primary_category": None,
        "user_note": "",
    }
    return drafted


def build_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    primary = Counter(item["author_review"]["primary_category"] for item in items)
    confidence = Counter(item["ai_draft_metadata"]["confidence"] for item in items)
    by_condition: dict[str, Counter[str]] = defaultdict(Counter)
    for item in items:
        by_condition[str(item["condition_code"])][item["author_review"]["primary_category"]] += 1
    candidates: dict[str, dict[str, Any]] = {}
    priority_requirements: dict[str, dict[str, Any]] = {}
    for item in items:
        key = f"{item['flow_id']}::{item['requirement_id']}"
        if item["author_review"]["gold_review_candidate"]:
            candidates[key] = {
                "flow_id": item["flow_id"],
                "requirement_id": item["requirement_id"],
                "requirement_text": item["requirement_text"],
                "gold_label": item["gold_label"],
                "gold_rationale": item["gold_rationale"],
            }
        if item["ai_draft_metadata"]["check_priority"] == "PRIORITY":
            entry = priority_requirements.setdefault(
                key,
                {
                    "flow_id": item["flow_id"],
                    "requirement_id": item["requirement_id"],
                    "requirement_text": item["requirement_text"],
                    "gold_label": item["gold_label"],
                    "gold_rationale": item["gold_rationale"],
                    "audit_item_ids": [],
                    "draft_categories": [],
                    "reasons": [],
                },
            )
            entry["audit_item_ids"].append(item["audit_item_id"])
            entry["draft_categories"].append(item["author_review"]["primary_category"])
            entry["reasons"].append(item["ai_draft_metadata"]["classification_basis"])
    for entry in priority_requirements.values():
        entry["draft_categories"] = unique(entry["draft_categories"])
        entry["reasons"] = unique(entry["reasons"])
    return {
        "schema_version": "rq3_ai_draft_summary_v1",
        "status": "FOR_AUTHOR_REVIEW",
        "warning": "AI-drafted judgments are provisional and are not author-coded thesis results.",
        "rows": len(items),
        "primary_category_counts": dict(sorted(primary.items())),
        "confidence_counts": dict(sorted(confidence.items())),
        "condition_category_counts": {
            code: dict(sorted(counts.items())) for code, counts in sorted(by_condition.items())
        },
        "gold_review_candidate_requirements": list(candidates.values()),
        "priority_requirements": list(priority_requirements.values()),
    }


def main() -> None:
    args = parse_args()
    source = load_json(args.source)
    result = deepcopy(source)
    result["schema_version"] = "rq3_ai_draft_error_audit_v1"
    result["draft_created_at"] = datetime.now(timezone.utc).isoformat()
    result["draft_status"] = "FOR_AUTHOR_REVIEW"
    result["draft_warning"] = (
        "This is an AI-drafted coding pass based on frozen gold labels, reviewed "
        "evidence steps, stored rationales, and supplied-step metadata. It must not "
        "be reported as author coding until the author approves or revises it."
    )
    result["protocol_amendment_proposed"] = {
        "reason": (
            "The frozen eligibility rule includes correct ABSTAIN decisions, "
            "label-correct trace misses, and current-correct unstable predictions, "
            "but the original seven failure categories have no valid code for them."
        ),
        "added_primary_categories": ADDED_PRIMARY_CATEGORIES,
        "added_evidence_tags": ADDED_EVIDENCE_TAGS,
        "status": "AWAITING_AUTHOR_APPROVAL",
    }
    options = result.setdefault("instructions", {}).setdefault(
        "primary_category_options", []
    )
    result["instructions"]["primary_category_options"] = unique(
        [*options, *ADDED_PRIMARY_CATEGORIES]
    )
    evidence_options = result["instructions"].setdefault("evidence_tag_options", [])
    result["instructions"]["evidence_tag_options"] = unique(
        [*evidence_options, *ADDED_EVIDENCE_TAGS]
    )
    result["items"] = [draft_item(item) for item in source.get("items", [])]
    summary = build_summary(result["items"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    args.summary_out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"draft_rows={len(result['items'])} out={args.out}")
    print(f"categories={summary['primary_category_counts']}")
    print(f"confidence={summary['confidence_counts']}")
    print(
        "gold_candidate_requirements="
        f"{len(summary['gold_review_candidate_requirements'])} "
        f"priority_requirements={len(summary['priority_requirements'])}"
    )


if __name__ == "__main__":
    main()
