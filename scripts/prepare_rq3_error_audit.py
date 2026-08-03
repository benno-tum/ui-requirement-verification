from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = (
    BASE_DIR / "data/annotations/evaluation_audits/rq3_final_20260802"
)
GOLD_ROOT = BASE_DIR / "data/annotations/verification_gold"
RUN_ROOT = BASE_DIR / "data/generated/thesis_final_experiments"

CONDITIONS = [
    {
        "condition_code": "C01",
        "run_id": "fl_raw_all",
        "claim_policy": "raw",
        "screenshot_policy": "all",
        "repetitions": ["fl_raw_all_r2", "fl_raw_all_r3"],
    },
    {
        "condition_code": "C02",
        "run_id": "fl_gated_all",
        "claim_policy": "gated",
        "screenshot_policy": "all",
        "repetitions": [],
    },
    {
        "condition_code": "C03",
        "run_id": "fl_raw_top4",
        "claim_policy": "raw",
        "screenshot_policy": "top4",
        "repetitions": [],
    },
    {
        "condition_code": "C04",
        "run_id": "fl_gated_top4",
        "claim_policy": "gated",
        "screenshot_policy": "top4",
        "repetitions": ["fl_gated_top4_r2", "fl_gated_top4_r3"],
    },
    {
        "condition_code": "C05",
        "run_id": "g25_raw_all",
        "claim_policy": "raw",
        "screenshot_policy": "all",
        "repetitions": [],
    },
    {
        "condition_code": "C06",
        "run_id": "qwen3vl8b_openrouter_raw_top4",
        "claim_policy": "raw",
        "screenshot_policy": "top4",
        "repetitions": ["qwen_raw_top4_r2", "qwen_raw_top4_r3"],
    },
]

PRIMARY_CATEGORIES = [
    "UNSAFE_OVER_FULFILLMENT",
    "UNSUPPORTED_CONCRETE_NEGATIVE",
    "EXCESSIVE_ABSTENTION",
    "EVIDENCE_SELECTION_MISS",
    "EVIDENCE_INTERPRETATION_ERROR",
    "LABEL_BOUNDARY_DISAGREEMENT",
    "GOLD_REVIEW_CANDIDATE",
]

REQUIREMENT_TAGS = [
    "UNIVERSAL_OR_COMPLETENESS",
    "COMPARATIVE_OR_DISTINCT",
    "HIDDEN_BACKEND_OR_EXTERNAL",
    "PERSISTENCE_OR_CROSS_STEP",
    "LATE_RESULT_OR_CART_STATE",
    "MULTI_SCREEN_COMPOSITION",
    "NEGATION_OR_CONTRASTIVE",
    "LABEL_SCHEMA_AMBIGUITY",
    "ORDINARY_LOCAL_UI",
]

EVIDENCE_TAGS = [
    "DECISIVE_STEP_SELECTED",
    "DECISIVE_STEP_NOT_SELECTED",
    "ONLY_ENTRY_POINT_VISIBLE",
    "ACTION_WITHOUT_RESULT",
    "PARTIAL_CLAIM_COVERAGE",
    "NO_OBSERVABLE_PROXY",
    "LATE_STEP",
    "CROSS_STEP_STATE",
    "EVIDENCE_CORRECT_BUT_RATIONALE_WRONG",
    "LABEL_CORRECT_BUT_TRACEABILITY_WRONG",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare the frozen, condition-blinded RQ3 author-coding form and "
            "an automatic trigger inventory from stored predictions."
        )
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite a pristine form. Never use after author coding has begun.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_label(value: Any) -> str:
    label = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "PARTIAL": "PARTIALLY_FULFILLED",
        "PARTIALLYFULFILLED": "PARTIALLY_FULFILLED",
        "NOTFULFILLED": "NOT_FULFILLED",
    }
    return aliases.get(label, label)


def unique_ints(values: Any) -> list[int]:
    if not isinstance(values, list):
        return []
    seen: set[int] = set()
    result: list[int] = []
    for value in values:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number >= 0 and number not in seen:
            seen.add(number)
            result.append(number)
    return result


def evidence_steps(item: dict[str, Any]) -> list[int]:
    direct = unique_ints(item.get("evidence_steps"))
    if direct:
        return direct
    steps: list[int] = []
    for key in ("evidence", "evidence_units"):
        entries = item.get(key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            try:
                steps.append(int(entry.get("step_index")))
            except (TypeError, ValueError):
                continue
    return sorted(set(steps))


def gold_items() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(GOLD_ROOT.glob("[0-9][0-9]_*/verification_gold.json")):
        data = load_json(path)
        flow_id = str(data.get("flow_id") or path.parent.name)
        entries = data.get("items") or data.get("requirements")
        if not isinstance(entries, list):
            raise ValueError(f"gold file has no items: {path}")
        for raw in entries:
            if not isinstance(raw, dict):
                continue
            requirement_id = str(raw.get("requirement_id") or raw.get("id") or "")
            if not requirement_id:
                continue
            item = dict(raw)
            item["flow_id"] = str(raw.get("flow_id") or flow_id)
            item["requirement_id"] = requirement_id
            item["label"] = normalize_label(
                raw.get("verification_label") or raw.get("manual_verification_label")
            )
            item["evidence_steps_normalized"] = evidence_steps(raw)
            result[f"{item['flow_id']}::{requirement_id}"] = item
    if len(result) != 258:
        raise ValueError(f"expected 258 Mind2Web gold items, found {len(result)}")
    return result


def prediction_items(run_id: str) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    root = RUN_ROOT / run_id
    if not root.is_dir():
        raise FileNotFoundError(root)
    result: dict[str, dict[str, Any]] = {}
    digests: dict[str, str] = {}
    for path in sorted(root.glob("[0-9][0-9]_*.json")):
        data = load_json(path)
        flow_id = str(data.get("flow_id") or path.stem)
        entries = data.get("results") or data.get("verdicts") or data.get("items")
        if not isinstance(entries, list):
            raise ValueError(f"prediction file has no result list: {path}")
        for raw in entries:
            if not isinstance(raw, dict):
                continue
            requirement_id = str(raw.get("requirement_id") or raw.get("id") or "")
            if not requirement_id:
                continue
            item = dict(raw)
            item["flow_id"] = flow_id
            item["requirement_id"] = requirement_id
            item["label"] = normalize_label(
                raw.get("final_label") or raw.get("label") or raw.get("verification_label")
            )
            item["evidence_steps_normalized"] = evidence_steps(raw)
            result[f"{flow_id}::{requirement_id}"] = item
        digests[path.name] = file_sha256(path)
    if len(result) != 258:
        raise ValueError(f"{run_id}: expected 258 predictions, found {len(result)}")
    return result, digests


def attached_steps(prediction: dict[str, Any]) -> list[int]:
    steps: set[int] = set()
    claims = prediction.get("claims")
    if isinstance(claims, list):
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            metadata = claim.get("metadata")
            if isinstance(metadata, dict):
                steps.update(unique_ints(metadata.get("attached_step_indices")))
    return sorted(steps)


def relative_screenshot_paths(flow_id: str, steps: list[int]) -> list[str]:
    root = BASE_DIR / "data/processed/flows/mind2web" / flow_id
    preferred = root / "original"
    image_root = preferred if preferred.is_dir() else root
    paths: list[str] = []
    for step in steps:
        path = image_root / f"step_{step:02d}.png"
        if path.exists():
            paths.append(path.relative_to(BASE_DIR).as_posix())
    return paths


def all_flow_steps(flow_id: str) -> list[int]:
    root = BASE_DIR / "data/processed/flows/mind2web" / flow_id
    preferred = root / "original"
    image_root = preferred if preferred.is_dir() else root
    result: list[int] = []
    for path in sorted(image_root.glob("step_*.png")):
        match = re.search(r"step_(\d+)\.png$", path.name)
        if match:
            result.append(int(match.group(1)))
    if not result:
        raise FileNotFoundError(f"no screenshots for {flow_id}")
    return result


def suggest_requirement_tags(
    requirement_id: str,
    text: str,
    gold_evidence: list[int],
) -> list[str]:
    lowered = text.lower()
    tags: list[str] = []
    rules = [
        (
            "UNIVERSAL_OR_COMPLETENESS",
            r"\b(all|every|only|always|any|complete|comprehensive|entire|each)\b",
        ),
        (
            "COMPARATIVE_OR_DISTINCT",
            r"\b(compare|comparison|different|distinct|rank|ranking|alternative|than|versus)\b",
        ),
        (
            "HIDDEN_BACKEND_OR_EXTERNAL",
            r"\b(authenticat|authoriz|secure|persist|deliver|send|available|availability|valid|backend|inventory|payment|notification|email)\w*\b",
        ),
        (
            "PERSISTENCE_OR_CROSS_STEP",
            r"\b(persist|preserve|retain|remain|carry|subsequent|return|revisit|session|across pages|later view)\w*\b",
        ),
        (
            "LATE_RESULT_OR_CART_STATE",
            r"\b(result|review|summary|cart|checkout|confirmation|total|submitted|after submission|purchase)\w*\b",
        ),
    ]
    for tag, pattern in rules:
        if re.search(pattern, lowered):
            tags.append(tag)
    if len(set(gold_evidence)) > 1:
        tags.append("MULTI_SCREEN_COMPOSITION")
    if requirement_id.startswith("CONTR-") or re.search(
        r"\b(no|not|without|never|must not|shall not)\b", lowered
    ):
        tags.append("NEGATION_OR_CONTRASTIVE")
    if not tags:
        tags.append("ORDINARY_LOCAL_UI")
    return list(dict.fromkeys(tags))


def suggest_evidence_tags(
    *,
    gold_label: str,
    gold_evidence: list[int],
    predicted_label: str,
    predicted_evidence: list[int],
    supplied_steps: list[int],
    requirement_tags: list[str],
    full_steps: list[int],
) -> list[str]:
    tags: list[str] = []
    gold_set = set(gold_evidence)
    supplied_set = set(supplied_steps)
    predicted_set = set(predicted_evidence)
    if gold_set and gold_set & supplied_set:
        tags.append("DECISIVE_STEP_SELECTED")
    if gold_set and not gold_set.issubset(supplied_set):
        tags.append("DECISIVE_STEP_NOT_SELECTED")
    if gold_label == "PARTIALLY_FULFILLED":
        tags.append("PARTIAL_CLAIM_COVERAGE")
    if gold_label == "ABSTAIN" and not gold_set:
        tags.append("NO_OBSERVABLE_PROXY")
    if gold_set and full_steps and max(gold_set) >= max(full_steps) - 2:
        tags.append("LATE_STEP")
    if "PERSISTENCE_OR_CROSS_STEP" in requirement_tags:
        tags.append("CROSS_STEP_STATE")
    if (
        predicted_label == gold_label
        and gold_set
        and not gold_set.intersection(predicted_set)
    ):
        tags.append("LABEL_CORRECT_BUT_TRACEABILITY_WRONG")
    return list(dict.fromkeys(tags))


def suggested_primary_candidates(
    *,
    gold_label: str,
    predicted_label: str,
    gold_evidence: list[int],
    supplied_steps: list[int],
    screenshot_policy: str,
) -> list[str]:
    gold_set = set(gold_evidence)
    supplied_set = set(supplied_steps)
    candidates: list[str] = []
    if predicted_label == "FULFILLED" and gold_label != "FULFILLED":
        candidates.append("UNSAFE_OVER_FULFILLMENT")
    if predicted_label == "NOT_FULFILLED" and gold_label != "NOT_FULFILLED":
        candidates.extend(
            ["UNSUPPORTED_CONCRETE_NEGATIVE", "LABEL_BOUNDARY_DISAGREEMENT"]
        )
    if predicted_label == "ABSTAIN" and gold_label != "ABSTAIN":
        if gold_set and gold_set.issubset(supplied_set):
            candidates.append("EXCESSIVE_ABSTENTION")
        elif screenshot_policy == "top4" and gold_set - supplied_set:
            candidates.append("EVIDENCE_SELECTION_MISS")
        else:
            candidates.append("LABEL_BOUNDARY_DISAGREEMENT")
    if predicted_label != gold_label and gold_set and gold_set & supplied_set:
        candidates.append("EVIDENCE_INTERPRETATION_ERROR")
    return list(dict.fromkeys(candidates))


def inventory_row(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "condition_code": item["condition_code"],
        "label_mismatch": "LABEL_MISMATCH" in item["eligibility_reasons"],
        "model_abstain": item["predicted_label"] == "ABSTAIN",
        "unsafe_fulfilled": (
            item["predicted_label"] == "FULFILLED"
            and item["gold_label"] != "FULFILLED"
        ),
        "label_correct_evidence_no_overlap": (
            "LABEL_CORRECT_EVIDENCE_NO_OVERLAP" in item["eligibility_reasons"]
        ),
        "unstable": "UNSTABLE_ACROSS_REPETITIONS" in item["eligibility_reasons"],
        "gold_evidence_not_fully_supplied": bool(
            set(item["gold_evidence_steps"]) - set(item["supplied_step_indices"])
        ),
    }


def summarize_inventory(items: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = [
        "label_mismatch",
        "model_abstain",
        "unsafe_fulfilled",
        "label_correct_evidence_no_overlap",
        "unstable",
        "gold_evidence_not_fully_supplied",
    ]
    result: dict[str, Any] = {}
    for condition in CONDITIONS:
        code = condition["condition_code"]
        rows = [inventory_row(item) for item in items if item["condition_code"] == code]
        counts = {metric: sum(bool(row[metric]) for row in rows) for metric in metrics}
        result[code] = {"eligible_rows": len(rows), **counts}
    return result


def build_form() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    gold = gold_items()
    form_items: list[dict[str, Any]] = []
    condition_key: dict[str, Any] = {}
    population_summaries: dict[str, Any] = {}
    audit_index = 0

    for condition in CONDITIONS:
        code = str(condition["condition_code"])
        run_id = str(condition["run_id"])
        predictions, digests = prediction_items(run_id)
        repetition_predictions = [
            prediction_items(str(repetition))[0]
            for repetition in condition["repetitions"]
        ]
        condition_key[code] = {
            "run_id": run_id,
            "claim_policy": condition["claim_policy"],
            "screenshot_policy": condition["screenshot_policy"],
            "repetitions": condition["repetitions"],
            "source_file_sha256": digests,
        }
        predicted_label_counts = Counter(
            str(prediction["label"]) for prediction in predictions.values()
        )
        label_errors = sum(
            str(predictions[key]["label"]) != str(gold[key]["label"])
            for key in gold
        )
        unsafe_fulfilled = sum(
            str(predictions[key]["label"]) == "FULFILLED"
            and str(gold[key]["label"]) != "FULFILLED"
            for key in gold
        )
        label_correct_evidence_no_overlap = sum(
            str(predictions[key]["label"]) == str(gold[key]["label"])
            and bool(gold[key]["evidence_steps_normalized"])
            and not set(gold[key]["evidence_steps_normalized"]).intersection(
                predictions[key]["evidence_steps_normalized"]
            )
            for key in gold
        )
        reviewed_evidence_not_fully_supplied = sum(
            bool(
                set(gold[key]["evidence_steps_normalized"])
                - set(attached_steps(predictions[key]))
            )
            for key in gold
        )
        population_summaries[code] = {
            "benchmark_items": len(gold),
            "label_errors": label_errors,
            "predicted_label_counts": dict(predicted_label_counts),
            "predicted_fulfilled": predicted_label_counts["FULFILLED"],
            "model_abstains": predicted_label_counts["ABSTAIN"],
            "unsafe_fulfilled": unsafe_fulfilled,
            "false_fulfillment_rate": (
                unsafe_fulfilled / predicted_label_counts["FULFILLED"]
                if predicted_label_counts["FULFILLED"]
                else None
            ),
            "label_correct_evidence_no_overlap": label_correct_evidence_no_overlap,
            "reviewed_evidence_not_fully_supplied": reviewed_evidence_not_fully_supplied,
        }

        for key in sorted(gold):
            gold_item = gold[key]
            prediction = predictions[key]
            gold_label = str(gold_item["label"])
            predicted_label = str(prediction["label"])
            gold_steps = list(gold_item["evidence_steps_normalized"])
            predicted_steps = list(prediction["evidence_steps_normalized"])
            supplied = attached_steps(prediction)
            full_steps = all_flow_steps(str(gold_item["flow_id"]))
            repeat_labels = [
                str(repetition[key]["label"])
                for repetition in repetition_predictions
            ]
            observed_labels = [predicted_label, *repeat_labels]
            eligibility: list[str] = []
            if predicted_label != gold_label:
                eligibility.append("LABEL_MISMATCH")
            if predicted_label == "ABSTAIN":
                eligibility.append("MODEL_ABSTAIN")
            if predicted_label == "FULFILLED" and gold_label != "FULFILLED":
                eligibility.append("UNSAFE_FULFILLED")
            if (
                predicted_label == gold_label
                and gold_steps
                and not set(gold_steps).intersection(predicted_steps)
            ):
                eligibility.append("LABEL_CORRECT_EVIDENCE_NO_OVERLAP")
            if len(set(observed_labels)) > 1:
                eligibility.append("UNSTABLE_ACROSS_REPETITIONS")
            if not eligibility:
                continue

            audit_index += 1
            requirement_text = str(
                gold_item.get("text") or prediction.get("requirement_text") or ""
            )
            req_tags = suggest_requirement_tags(
                str(gold_item["requirement_id"]), requirement_text, gold_steps
            )
            ev_tags = suggest_evidence_tags(
                gold_label=gold_label,
                gold_evidence=gold_steps,
                predicted_label=predicted_label,
                predicted_evidence=predicted_steps,
                supplied_steps=supplied,
                requirement_tags=req_tags,
                full_steps=full_steps,
            )
            form_items.append(
                {
                    "audit_item_id": f"RQ3-{audit_index:04d}",
                    "condition_code": code,
                    "claim_policy": condition["claim_policy"],
                    "screenshot_policy": condition["screenshot_policy"],
                    "flow_id": gold_item["flow_id"],
                    "requirement_id": gold_item["requirement_id"],
                    "requirement_text": requirement_text,
                    "gold_label": gold_label,
                    "predicted_label": predicted_label,
                    "repetition_labels": repeat_labels,
                    "eligibility_reasons": eligibility,
                    "gold_evidence_steps": gold_steps,
                    "predicted_evidence_steps": predicted_steps,
                    "supplied_step_indices": supplied,
                    "missing_gold_evidence_steps": sorted(set(gold_steps) - set(supplied)),
                    "full_flow_step_indices": full_steps,
                    "supplied_screenshot_paths": relative_screenshot_paths(
                        str(gold_item["flow_id"]), supplied
                    ),
                    "full_flow_screenshot_paths": relative_screenshot_paths(
                        str(gold_item["flow_id"]), full_steps
                    ),
                    "gold_rationale": str(gold_item.get("rationale") or ""),
                    "prediction_rationale": str(prediction.get("rationale") or ""),
                    "prediction_uncertainty_reasons": prediction.get(
                        "uncertainty_reasons"
                    )
                    or [],
                    "automatic_suggestions": {
                        "primary_category_candidates": suggested_primary_candidates(
                            gold_label=gold_label,
                            predicted_label=predicted_label,
                            gold_evidence=gold_steps,
                            supplied_steps=supplied,
                            screenshot_policy=str(condition["screenshot_policy"]),
                        ),
                        "requirement_tags": req_tags,
                        "evidence_tags": ev_tags,
                        "warning": (
                            "Suggestions are deterministic triage only and are excluded "
                            "from reviewed RQ3 counts until accepted by the thesis author."
                        ),
                    },
                    "author_review": {
                        "decisive_evidence_supplied": None,
                        "primary_category": None,
                        "requirement_tags": [],
                        "evidence_tags": [],
                        "visible_evidence_rationale": "",
                        "gold_review_candidate": None,
                        "review_status": "PENDING",
                    },
                }
            )

    form_items.sort(
        key=lambda item: (
            str(item["flow_id"]),
            str(item["requirement_id"]),
            str(item["condition_code"]),
        )
    )
    for index, item in enumerate(form_items, start=1):
        item["audit_item_id"] = f"RQ3-{index:04d}"

    eligible_summaries = summarize_inventory(form_items)
    for code, summary in population_summaries.items():
        summary["eligible_rows"] = eligible_summaries[code]["eligible_rows"]
        summary["unstable"] = eligible_summaries[code]["unstable"]
    inventory = {
        "schema_version": "rq3_automatic_trigger_inventory_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "warning": (
            "These are mechanically observable triggers, not manually coded causes. "
            "Do not report them as error-taxonomy frequencies."
        ),
        "condition_summaries": population_summaries,
        "eligibility_reason_counts": dict(
            Counter(reason for item in form_items for reason in item["eligibility_reasons"])
        ),
        "total_review_rows": len(form_items),
    }
    form = {
        "schema_version": "rq3_author_error_audit_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "protocol": "docs/rq3_error_analysis_protocol_2026-07-23.md",
        "blind": "model identity blinded by condition code; evidence and claim policies remain visible because they are needed for causal classification",
        "scope": {
            "benchmark_items": len(gold),
            "conditions": len(CONDITIONS),
            "eligible_condition_item_rows": len(form_items),
            "unique_eligible_requirements": len(
                {
                    f"{item['flow_id']}::{item['requirement_id']}"
                    for item in form_items
                }
            ),
            "selection": [
                "gold/predicted label mismatch",
                "model ABSTAIN",
                "unsafe FULFILLED",
                "label correct with no reviewed-evidence overlap",
                "label instability across the available three-run family",
            ],
        },
        "instructions": {
            "primary_category_options": PRIMARY_CATEGORIES,
            "requirement_tag_options": REQUIREMENT_TAGS,
            "evidence_tag_options": EVIDENCE_TAGS,
            "required_author_fields": [
                "decisive_evidence_supplied",
                "primary_category",
                "requirement_tags",
                "evidence_tags",
                "visible_evidence_rationale",
                "gold_review_candidate",
                "review_status=COMPLETE",
            ],
            "important": (
                "Inspect the complete ordered flow and the supplied screenshots. "
                "Do not accept automatic suggestions without author review."
            ),
        },
        "items": form_items,
    }
    key = {
        "schema_version": "rq3_condition_key_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "warning": "Open only after author category coding where practicable.",
        "conditions": condition_key,
    }
    return form, inventory, key


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    form_path = args.output_dir / "rq3_author_error_audit_form.json"
    if form_path.exists() and not args.force:
        raise SystemExit(
            f"Refusing to overwrite existing audit form: {form_path}. "
            "Use --force only if no author response has been entered."
        )
    form, inventory, key = build_form()
    write_json(form_path, form)
    write_json(args.output_dir / "rq3_automatic_trigger_inventory.json", inventory)
    write_json(args.output_dir / "rq3_condition_key.json", key)
    print(
        f"benchmark_items={form['scope']['benchmark_items']} "
        f"conditions={form['scope']['conditions']} "
        f"review_rows={form['scope']['eligible_condition_item_rows']}"
    )
    for code, summary in inventory["condition_summaries"].items():
        print(
            f"{code}: eligible={summary['eligible_rows']} "
            f"errors={summary['label_errors']} "
            f"abstain={summary['model_abstains']} "
            f"unsafe_fulfilled={summary['unsafe_fulfilled']} "
            f"trace_miss={summary['label_correct_evidence_no_overlap']}"
        )
    print(f"form={form_path}")


if __name__ == "__main__":
    main()
