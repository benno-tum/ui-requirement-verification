from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT = (
    BASE_DIR
    / "data/annotations/evaluation_audits/rq3_final_20260802"
    / "rq3_author_error_audit_form.json"
)
DEFAULT_OUTPUT = DEFAULT_AUDIT.parent / "rq3_reviewed_summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and summarize a completed RQ3 author-coding form."
    )
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Write progress only; never emit category percentages from incomplete coding.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def review_complete(item: dict[str, Any]) -> bool:
    review = item.get("author_review")
    if not isinstance(review, dict):
        return False
    return bool(
        review.get("review_status") == "COMPLETE"
        and isinstance(review.get("decisive_evidence_supplied"), bool)
        and review.get("primary_category")
        and isinstance(review.get("requirement_tags"), list)
        and review.get("requirement_tags")
        and isinstance(review.get("evidence_tags"), list)
        and str(review.get("visible_evidence_rationale") or "").strip()
        and isinstance(review.get("gold_review_candidate"), bool)
    )


def safe_rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def counts_with_rates(counter: Counter[str], denominator: int) -> dict[str, Any]:
    return {
        key: {"count": value, "rate": safe_rate(value, denominator)}
        for key, value in sorted(counter.items())
    }


def summarize(data: dict[str, Any]) -> dict[str, Any]:
    items = data.get("items")
    if not isinstance(items, list):
        raise ValueError("audit has no items list")
    completed = [item for item in items if isinstance(item, dict) and review_complete(item)]
    pending = [
        str(item.get("audit_item_id"))
        for item in items
        if isinstance(item, dict) and not review_complete(item)
    ]
    progress: dict[str, Any] = {
        "total_review_rows": len(items),
        "completed_review_rows": len(completed),
        "pending_review_rows": len(pending),
        "pending_audit_item_ids": pending,
    }
    if pending:
        return {
            "schema_version": "rq3_review_progress_v1",
            "complete": False,
            "progress": progress,
            "warning": (
                "Category counts are intentionally withheld until every frozen "
                "eligible row is complete."
            ),
        }

    primary = Counter(
        str(item["author_review"]["primary_category"]) for item in completed
    )
    requirement_tags = Counter(
        str(tag)
        for item in completed
        for tag in item["author_review"]["requirement_tags"]
    )
    evidence_tags = Counter(
        str(tag)
        for item in completed
        for tag in item["author_review"]["evidence_tags"]
    )
    by_condition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in completed:
        by_condition[str(item["condition_code"])].append(item)

    condition_summaries: dict[str, Any] = {}
    for condition, rows in sorted(by_condition.items()):
        row_primary = Counter(
            str(item["author_review"]["primary_category"]) for item in rows
        )
        label_errors = sum(item["gold_label"] != item["predicted_label"] for item in rows)
        unsafe = [
            item
            for item in rows
            if item["predicted_label"] == "FULFILLED"
            and item["gold_label"] != "FULFILLED"
        ]
        abstains = [item for item in rows if item["predicted_label"] == "ABSTAIN"]
        condition_summaries[condition] = {
            "coded_rows": len(rows),
            "label_error_rows": label_errors,
            "unsafe_fulfilled_rows": len(unsafe),
            "abstention_rows": len(abstains),
            "primary_categories_among_coded_rows": counts_with_rates(
                row_primary, len(rows)
            ),
            "unsafe_fulfilled_primary_categories": counts_with_rates(
                Counter(
                    str(item["author_review"]["primary_category"])
                    for item in unsafe
                ),
                len(unsafe),
            ),
            "abstention_primary_categories": counts_with_rates(
                Counter(
                    str(item["author_review"]["primary_category"])
                    for item in abstains
                ),
                len(abstains),
            ),
        }

    return {
        "schema_version": "rq3_reviewed_summary_v1",
        "complete": True,
        "progress": progress,
        "denominator_note": (
            "Rows are condition-item observations from the six prespecified first "
            "runs, not 258 independent benchmark items. Per-condition denominators "
            "are reported separately."
        ),
        "primary_categories_among_all_coded_rows": counts_with_rates(
            primary, len(completed)
        ),
        "requirement_pattern_tags_among_all_coded_rows": counts_with_rates(
            requirement_tags, len(completed)
        ),
        "evidence_pattern_tags_among_all_coded_rows": counts_with_rates(
            evidence_tags, len(completed)
        ),
        "condition_summaries": condition_summaries,
    }


def main() -> None:
    args = parse_args()
    result = summarize(load_json(args.audit))
    if not result["complete"] and not args.allow_incomplete:
        progress = result["progress"]
        raise SystemExit(
            "RQ3 audit incomplete: "
            f"{progress['completed_review_rows']}/{progress['total_review_rows']} "
            "rows complete. Use --allow-incomplete for a progress artifact only."
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    progress = result["progress"]
    print(
        f"complete={result['complete']} "
        f"reviewed={progress['completed_review_rows']} "
        f"total={progress['total_review_rows']} out={args.out}"
    )


if __name__ == "__main__":
    main()
