from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT = (
    BASE_DIR
    / "outputs/019fbfa1-94d4-7bb1-9a8a-81dd427302cf"
    / "rq3_chatgpt_multimodal_batches_20260802"
    / "rq3_llm_visual_repaired_error_audit_form.json"
)
DEFAULT_PYTHON_DRAFT = (
    BASE_DIR
    / "outputs/019fbfa1-94d4-7bb1-9a8a-81dd427302cf"
    / "rq3_ai_draft_error_audit_form.json"
)
DEFAULT_OUTPUT = (
    BASE_DIR
    / "data/annotations/evaluation_audits/rq3_final_20260802"
    / "rq3_visual_coding_summary.json"
)
DEFAULT_AUTHOR_BOUNDARY_REVIEW = (
    BASE_DIR
    / "data/annotations/evaluation_audits/rq3_final_20260802"
    / "rq3_author_boundary_consistency_review.json"
)

PRIMARY_CATEGORIES = {
    "UNSAFE_OVER_FULFILLMENT",
    "UNSUPPORTED_CONCRETE_NEGATIVE",
    "EXCESSIVE_ABSTENTION",
    "EVIDENCE_SELECTION_MISS",
    "EVIDENCE_INTERPRETATION_ERROR",
    "LABEL_BOUNDARY_DISAGREEMENT",
    "APPROPRIATE_ABSTENTION",
    "TRACEABILITY_FAILURE",
    "PREDICTION_INSTABILITY",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and summarize the repaired screenshot-aware RQ3 coding."
    )
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--python-draft", type=Path, default=DEFAULT_PYTHON_DRAFT)
    parser.add_argument(
        "--author-boundary-review",
        type=Path,
        default=DEFAULT_AUTHOR_BOUNDARY_REVIEW,
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def rate(count: int, denominator: int) -> float:
    return count / denominator if denominator else 0.0


def counter_table(counter: Counter[str], denominator: int) -> dict[str, Any]:
    return {
        key: {"count": value, "rate": rate(value, denominator)}
        for key, value in counter.most_common()
    }


def apply_author_boundary_review(
    audit: dict[str, Any], boundary_review: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    if boundary_review.get("schema_version") != "rq3_author_boundary_consistency_review_v1":
        raise ValueError("unsupported author boundary-review schema")
    if boundary_review.get("status") != "COMPLETE":
        raise ValueError("author boundary review is incomplete")
    decisions = boundary_review.get("requirement_decisions")
    if not isinstance(decisions, list):
        raise ValueError("author boundary review has no requirement decisions")

    reviewed = deepcopy(audit)
    original_boundary_ids = {
        str(item["audit_item_id"])
        for item in audit.get("items", [])
        if isinstance(item.get("llm_visual_review"), dict)
        and item["llm_visual_review"].get("primary_category")
        == "LABEL_BOUNDARY_DISAGREEMENT"
    }
    item_by_id = {
        str(item["audit_item_id"]): item for item in reviewed.get("items", [])
    }
    reviewed_ids: set[str] = set()
    changed_ids: set[str] = set()
    for decision in decisions:
        audit_ids = [str(value) for value in decision.get("audit_item_ids", [])]
        if not audit_ids:
            raise ValueError("author boundary decision has no audit_item_ids")
        initial = str(decision.get("initial_category"))
        final = str(decision.get("reviewed_category"))
        rationale = str(decision.get("reviewed_rationale") or "").strip()
        if initial != "LABEL_BOUNDARY_DISAGREEMENT":
            raise ValueError(f"unexpected initial boundary category: {initial}")
        if final not in {"LABEL_BOUNDARY_DISAGREEMENT", "EXCESSIVE_ABSTENTION"}:
            raise ValueError(f"unsupported reviewed boundary category: {final}")
        if not rationale:
            raise ValueError("author boundary decision has no rationale")
        for audit_id in audit_ids:
            if audit_id in reviewed_ids:
                raise ValueError(f"duplicate author-reviewed audit ID: {audit_id}")
            item = item_by_id.get(audit_id)
            if item is None:
                raise ValueError(f"unknown author-reviewed audit ID: {audit_id}")
            if str(item.get("flow_id")) != str(decision.get("flow_id")):
                raise ValueError(f"flow mismatch for author-reviewed row {audit_id}")
            if str(item.get("requirement_id")) != str(decision.get("requirement_id")):
                raise ValueError(f"requirement mismatch for author-reviewed row {audit_id}")
            review = item.get("llm_visual_review")
            if not isinstance(review, dict) or str(review.get("primary_category")) != initial:
                raise ValueError(f"initial category mismatch for author-reviewed row {audit_id}")
            review["primary_category"] = final
            review["author_boundary_review"] = {
                "review_date": boundary_review.get("review_date"),
                "reviewed_category": final,
                "reviewed_rationale": rationale,
            }
            reviewed_ids.add(audit_id)
            if final != initial:
                changed_ids.add(audit_id)

    expected = boundary_review.get("scope", {})
    if len(reviewed_ids) != int(expected.get("reviewed_rows", -1)):
        raise ValueError("author boundary-review row count does not match its scope")
    if reviewed_ids != original_boundary_ids:
        missing = sorted(original_boundary_ids - reviewed_ids)
        extra = sorted(reviewed_ids - original_boundary_ids)
        raise ValueError(
            "author boundary review does not cover exactly the original boundary rows: "
            f"missing={missing} extra={extra}"
        )
    if len(changed_ids) != int(expected.get("reclassified_rows", -1)):
        raise ValueError("author boundary-review reclassification count does not match its scope")
    if len(reviewed_ids) - len(changed_ids) != int(expected.get("retained_rows", -1)):
        raise ValueError("author boundary-review retained count does not match its scope")
    distinct_requirements = {
        (str(decision["flow_id"]), str(decision["requirement_id"]))
        for decision in decisions
    }
    if len(distinct_requirements) != int(expected.get("distinct_requirements", -1)):
        raise ValueError(
            "author boundary-review distinct-requirement count does not match its scope"
        )
    metadata = {
        "status": "COMPLETE",
        "review_date": boundary_review.get("review_date"),
        "review_role": boundary_review.get("review_role"),
        "reviewed_rows": len(reviewed_ids),
        "reclassified_rows": len(changed_ids),
        "retained_rows": len(reviewed_ids) - len(changed_ids),
        "distinct_requirements": len(distinct_requirements),
        "decision_rule": boundary_review.get("decision_rule"),
    }
    return reviewed, metadata


def validate_item(item: dict[str, Any]) -> list[str]:
    audit_id = str(item.get("audit_item_id"))
    review = item.get("llm_visual_review")
    if not isinstance(review, dict):
        return [f"{audit_id}: missing llm_visual_review"]
    problems: list[str] = []
    category = str(review.get("primary_category"))
    gold = str(item.get("gold_label"))
    predicted = str(item.get("predicted_label"))
    supplied = review.get("decisive_evidence_supplied")
    if category not in PRIMARY_CATEGORIES:
        problems.append(f"{audit_id}: invalid primary category {category}")
    if review.get("gold_review_candidate") is not False:
        problems.append(f"{audit_id}: gold-review flag is not false")
    if review.get("review_status") != "LLM_VISUAL_DRAFT_COMPLETE":
        problems.append(f"{audit_id}: incomplete visual review")
    if not isinstance(supplied, bool):
        problems.append(f"{audit_id}: decisive-evidence flag is not Boolean")
    if not str(review.get("visible_evidence_rationale") or "").strip():
        problems.append(f"{audit_id}: empty visual rationale")
    if category == "UNSAFE_OVER_FULFILLMENT" and not (
        predicted == "FULFILLED" and gold != "FULFILLED"
    ):
        problems.append(f"{audit_id}: invalid unsafe-over-fulfillment precondition")
    if category == "UNSUPPORTED_CONCRETE_NEGATIVE" and not (
        predicted == "NOT_FULFILLED" and gold != "NOT_FULFILLED"
    ):
        problems.append(f"{audit_id}: invalid unsupported-negative precondition")
    if category == "EXCESSIVE_ABSTENTION" and not (
        predicted == "ABSTAIN" and gold != "ABSTAIN" and supplied is True
    ):
        problems.append(f"{audit_id}: invalid excessive-abstention precondition")
    if category == "EVIDENCE_SELECTION_MISS" and supplied is not False:
        problems.append(f"{audit_id}: selection miss despite supplied decisive evidence")
    if category == "APPROPRIATE_ABSTENTION" and not (
        predicted == gold == "ABSTAIN"
    ):
        problems.append(f"{audit_id}: invalid appropriate-abstention precondition")
    if category == "TRACEABILITY_FAILURE" and not (
        predicted == gold and gold != "ABSTAIN"
    ):
        problems.append(f"{audit_id}: invalid traceability precondition")
    if category == "PREDICTION_INSTABILITY" and not (
        predicted == gold
        and "UNSTABLE_ACROSS_REPETITIONS" in item.get("eligibility_reasons", [])
    ):
        problems.append(f"{audit_id}: invalid instability precondition")
    if category in {
        "EVIDENCE_INTERPRETATION_ERROR",
        "LABEL_BOUNDARY_DISAGREEMENT",
    } and predicted == gold:
        problems.append(f"{audit_id}: mismatch category assigned to a correct label")
    return problems


def agreement_summary(
    items: list[dict[str, Any]], python_draft: dict[str, Any]
) -> dict[str, Any]:
    python_by_id = {
        str(item["audit_item_id"]): str(item["author_review"]["primary_category"])
        for item in python_draft.get("items", [])
    }
    pairs = [
        (
            python_by_id[str(item["audit_item_id"])],
            str(item["llm_visual_review"]["primary_category"]),
        )
        for item in items
    ]
    exact = sum(left == right for left, right in pairs)
    left_counts = Counter(left for left, _ in pairs)
    right_counts = Counter(right for _, right in pairs)
    labels = set(left_counts) | set(right_counts)
    expected = sum(
        rate(left_counts[label], len(pairs)) * rate(right_counts[label], len(pairs))
        for label in labels
    )
    observed = rate(exact, len(pairs))
    kappa = (observed - expected) / (1 - expected) if expected < 1 else 0.0
    return {
        "purpose": "post-hoc consistency check; not human inter-rater reliability",
        "rows": len(pairs),
        "exact_agreement_count": exact,
        "exact_agreement_rate": observed,
        "expected_chance_agreement": expected,
        "cohens_kappa": kappa,
    }


def summarize(
    audit: dict[str, Any],
    python_draft: dict[str, Any],
    author_boundary_review: dict[str, Any],
) -> dict[str, Any]:
    items = audit.get("items")
    if not isinstance(items, list):
        raise ValueError("audit has no items list")
    audit_ids = [str(item.get("audit_item_id")) for item in items]
    if len(audit_ids) != len(set(audit_ids)):
        raise ValueError("duplicate audit_item_id values")
    problems = [problem for item in items for problem in validate_item(item)]
    if problems:
        raise ValueError("invalid repaired audit:\n" + "\n".join(problems[:50]))

    rows = [(item, item["llm_visual_review"]) for item in items]
    label_errors = [pair for pair in rows if pair[0]["gold_label"] != pair[0]["predicted_label"]]
    abstentions = [pair for pair in rows if pair[0]["predicted_label"] == "ABSTAIN"]
    unsafe = [
        pair
        for pair in rows
        if pair[0]["predicted_label"] == "FULFILLED"
        and pair[0]["gold_label"] != "FULFILLED"
    ]
    distinct_requirements_by_error_category: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for item, review in label_errors:
        distinct_requirements_by_error_category[str(review["primary_category"])].add(
            (str(item["flow_id"]), str(item["requirement_id"]))
        )

    by_condition: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for pair in rows:
        by_condition[str(pair[0]["condition_code"])].append(pair)
    condition_summaries: dict[str, Any] = {}
    for condition, condition_rows in sorted(by_condition.items()):
        errors = [
            pair
            for pair in condition_rows
            if pair[0]["gold_label"] != pair[0]["predicted_label"]
        ]
        condition_summaries[condition] = {
            "coded_rows": len(condition_rows),
            "label_error_rows": len(errors),
            "label_error_categories": counter_table(
                Counter(review["primary_category"] for _, review in errors),
                len(errors),
            ),
        }

    result = {
        "schema_version": "rq3_visual_coding_summary_v1",
        "status": "COMPLETE_LLM_ASSISTED_VISUAL_CODING_WITH_AUTHOR_BOUNDARY_REVIEW",
        "method_note": (
            "Primary categories were assigned by the repaired screenshot-aware GPT visual "
            "review. A targeted primary-author consistency review then inspected all rows "
            "initially assigned LABEL_BOUNDARY_DISAGREEMENT and applied the frozen category "
            "precedence rule. Accepted benchmark references and model predictions remained "
            "frozen. The deterministic Python draft is used only as a post-hoc consistency "
            "check and is not pooled into counts."
        ),
        "author_boundary_review": author_boundary_review,
        "scope": {
            "condition_item_rows": len(rows),
            "distinct_requirements": len(
                {(item["flow_id"], item["requirement_id"]) for item in items}
            ),
            "flows": len({item["flow_id"] for item in items}),
            "conditions": len(by_condition),
            "label_error_rows": len(label_errors),
            "model_abstention_rows": len(abstentions),
            "unsafe_fulfilled_rows": len(unsafe),
        },
        "primary_categories_all_coded_rows": counter_table(
            Counter(review["primary_category"] for _, review in rows), len(rows)
        ),
        "primary_categories_among_label_errors": counter_table(
            Counter(review["primary_category"] for _, review in label_errors),
            len(label_errors),
        ),
        "distinct_requirements_by_primary_category_among_label_errors": {
            category: len(values)
            for category, values in sorted(
                distinct_requirements_by_error_category.items(),
                key=lambda pair: (-len(pair[1]), pair[0]),
            )
        },
        "primary_categories_among_model_abstentions": counter_table(
            Counter(review["primary_category"] for _, review in abstentions),
            len(abstentions),
        ),
        "requirement_tags_among_label_errors": counter_table(
            Counter(tag for _, review in label_errors for tag in review["requirement_tags"]),
            len(label_errors),
        ),
        "evidence_tags_among_label_errors": counter_table(
            Counter(tag for _, review in label_errors for tag in review["evidence_tags"]),
            len(label_errors),
        ),
        "condition_summaries": condition_summaries,
        "python_visual_consistency": agreement_summary(items, python_draft),
        "limitations": [
            "Rows repeat requirements across conditions and are not independent benchmark items.",
            "Category frequencies are descriptive for 13 flows and do not estimate population prevalence.",
            "The screenshot-aware coder is an LLM, not an independent human reviewer.",
            "The primary-author consistency review targeted the original label-boundary rows and is not an independent reliability sample.",
            "Requirement and evidence tags are multi-valued, so their percentages overlap.",
        ],
    }
    return result


def markdown_report(summary: dict[str, Any]) -> str:
    scope = summary["scope"]
    lines = [
        "# Repaired screenshot-aware RQ3 coding",
        "",
        "## Coverage",
        "",
        f"- {scope['condition_item_rows']} condition-item rows",
        f"- {scope['distinct_requirements']} distinct requirements",
        f"- {scope['flows']} flows and {scope['conditions']} conditions",
        f"- {scope['label_error_rows']} label-error rows",
        f"- {scope['model_abstention_rows']} model-abstention rows",
        "- zero remaining gold-review candidates or flags",
        f"- {summary['author_boundary_review']['reviewed_rows']} original boundary rows received a targeted primary-author consistency review",
        "",
        "## Categories among label errors",
        "",
        "| Category | Count | Share | Distinct requirements |",
        "|---|---:|---:|---:|",
    ]
    for category, value in summary["primary_categories_among_label_errors"].items():
        distinct = summary["distinct_requirements_by_primary_category_among_label_errors"][category]
        lines.append(
            f"| `{category}` | {value['count']} | {value['rate']:.1%} | {distinct} |"
        )
    lines.extend(
        [
            "",
            "## Abstention outcomes",
            "",
            "| Category | Count | Share |",
            "|---|---:|---:|",
        ]
    )
    for category, value in summary["primary_categories_among_model_abstentions"].items():
        lines.append(f"| `{category}` | {value['count']} | {value['rate']:.1%} |")
    consistency = summary["python_visual_consistency"]
    lines.extend(
        [
            "",
            "## Consistency check",
            "",
            f"The screenshot-aware coding and the separate deterministic heuristic agree "
            f"on {consistency['exact_agreement_count']} of {consistency['rows']} rows "
            f"({consistency['exact_agreement_rate']:.1%}; Cohen's kappa "
            f"{consistency['cohens_kappa']:.3f}). This is a post-hoc consistency check, "
            "not human inter-rater reliability.",
            "",
            "## Interpretation boundary",
            "",
            "The results are sufficient for a descriptive RQ3 answer about recurring failure "
            "mechanisms in the frozen 13-flow benchmark. They do not support population-level "
            "prevalence estimates or independent-human reliability claims.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    reviewed_audit, boundary_metadata = apply_author_boundary_review(
        load_object(args.audit.resolve()),
        load_object(args.author_boundary_review.resolve()),
    )
    summary = summarize(
        reviewed_audit,
        load_object(args.python_draft.resolve()),
        boundary_metadata,
    )
    output = args.out.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(markdown_report(summary), encoding="utf-8")
    print(
        f"status={summary['status']} rows={summary['scope']['condition_item_rows']} "
        f"label_errors={summary['scope']['label_error_rows']} out={output}"
    )


if __name__ == "__main__":
    main()
