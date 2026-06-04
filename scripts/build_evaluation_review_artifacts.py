from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = BASE_DIR / "data" / "annotations" / "verification_gold" / "03_mbta_c094948f-afc6-415c-968a-9e105e2db118" / "verification_gold.json"
DEFAULT_PREDICTIONS = BASE_DIR / "data" / "generated" / "verification_pipeline" / "03_mbta_verification_gold_deepseek_claims.json"
DEFAULT_OUT = BASE_DIR / "data" / "generated" / "evaluation_review" / "03_mbta_deepseek_claims"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def items_from_gold(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        items = data.get("items") or data.get("requirements")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    raise ValueError("Gold file must contain items/requirements list")


def items_from_predictions(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        items = data.get("results") or data.get("verdicts") or data.get("items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    raise ValueError("Prediction file must contain results/verdicts/items list")


def requirement_id(item: dict[str, Any]) -> str:
    return str(item.get("requirement_id") or item.get("id") or "").strip()


def label(item: dict[str, Any], *, prediction: bool = False) -> str | None:
    keys = ["final_label", "label", "verification_label", "manual_verification_label"] if prediction else ["verification_label", "manual_verification_label", "label", "final_label"]
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().upper().replace("-", "_").replace(" ", "_")
    return None


def text(item: dict[str, Any]) -> str:
    for key in ("text", "requirement_text", "harvested_text", "claim_text"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())
    return ""


def evidence_steps(item: dict[str, Any]) -> list[int]:
    if isinstance(item.get("evidence_steps"), list):
        return _int_steps(item["evidence_steps"])
    if isinstance(item.get("evidence"), list):
        return _int_steps(e.get("step_index") for e in item["evidence"] if isinstance(e, dict))
    if isinstance(item.get("evidence_units"), list):
        return _int_steps(e.get("step_index") for e in item["evidence_units"] if isinstance(e, dict))
    return []


def _int_steps(values: Any) -> list[int]:
    out: list[int] = []
    seen: set[int] = set()
    for value in values:
        try:
            step = int(value)
        except (TypeError, ValueError):
            continue
        if step >= 0 and step not in seen:
            out.append(step)
            seen.add(step)
    return out


def claims(item: dict[str, Any]) -> list[dict[str, Any]]:
    raw = item.get("claims")
    return [claim for claim in raw if isinstance(claim, dict)] if isinstance(raw, list) else []


def claim_text(claim: dict[str, Any]) -> str:
    for key in ("claim", "claim_text", "text"):
        value = claim.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())
    return ""


def claim_status(claim: dict[str, Any]) -> str | None:
    for key in ("status", "label"):
        value = claim.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().upper().replace("-", "_").replace(" ", "_")
    return None


def slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value.strip())
    return value.strip("_") or "item"


def compact_claims(raw_claims: list[dict[str, Any]], *, prediction: bool) -> list[dict[str, Any]]:
    compact = []
    for claim in raw_claims:
        entry: dict[str, Any] = {
            "text": claim_text(claim),
            "status": claim_status(claim),
            "evidence_steps": evidence_steps(claim),
        }
        if prediction:
            entry.update(
                {
                    "claim_id": claim.get("claim_id"),
                    "is_core": claim.get("is_core"),
                    "is_observable": claim.get("is_observable"),
                    "confidence": claim.get("confidence"),
                    "rationale": claim.get("rationale"),
                    "evidence": [
                        {
                            "step_index": evidence.get("step_index"),
                            "source": evidence.get("source"),
                            "confidence": evidence.get("confidence"),
                            "observation": evidence.get("visible_observation"),
                        }
                        for evidence in claim.get("evidence", [])
                        if isinstance(evidence, dict)
                    ],
                }
            )
        else:
            entry.update(
                {
                    "claim_type": claim.get("claim_type"),
                    "importance": claim.get("importance"),
                    "note": claim.get("note"),
                }
            )
        compact.append(entry)
    return compact


def build_case(gold_item: dict[str, Any], pred_item: dict[str, Any] | None) -> dict[str, Any]:
    gold_label = label(gold_item)
    pred_label = label(pred_item or {}, prediction=True)
    case_type = "match"
    if pred_item is None:
        case_type = "missing_prediction"
    elif pred_label == "FULFILLED" and gold_label != "FULFILLED":
        case_type = "false_fulfillment"
    elif pred_label != gold_label:
        case_type = "label_mismatch"
    elif set(evidence_steps(gold_item)).isdisjoint(set(evidence_steps(pred_item))) and evidence_steps(gold_item):
        case_type = "label_match_evidence_mismatch"

    return {
        "requirement_id": requirement_id(gold_item),
        "case_type": case_type,
        "requirement_text": text(gold_item) or text(pred_item or {}),
        "gold": {
            "label": gold_label,
            "ui_evaluability": gold_item.get("ui_evaluability"),
            "evidence_steps": evidence_steps(gold_item),
            "evidence_note": gold_item.get("evidence_note"),
            "rationale": gold_item.get("rationale"),
            "annotation_notes": gold_item.get("annotation_notes"),
            "claims": compact_claims(claims(gold_item), prediction=False),
        },
        "prediction": None
        if pred_item is None
        else {
            "label": pred_label,
            "ui_evaluability": pred_item.get("ui_evaluability"),
            "evidence_steps": evidence_steps(pred_item),
            "rationale": pred_item.get("rationale"),
            "uncertainty_reasons": pred_item.get("uncertainty_reasons"),
            "claims": compact_claims(claims(pred_item), prediction=True),
        },
    }


def write_markdown(case: dict[str, Any], path: Path) -> None:
    pred = case["prediction"] or {}
    lines = [
        f"# {case['requirement_id']} - {case['case_type']}",
        "",
        f"Requirement: {case['requirement_text']}",
        "",
        f"Gold label: `{case['gold']['label']}`",
        f"Pred label: `{pred.get('label')}`",
        f"Gold evidence steps: `{case['gold']['evidence_steps']}`",
        f"Pred evidence steps: `{pred.get('evidence_steps')}`",
        "",
        "## Gold Notes",
        "",
        f"Evidence note: {case['gold'].get('evidence_note') or ''}",
        f"Rationale: {case['gold'].get('rationale') or ''}",
        f"Annotation notes: {case['gold'].get('annotation_notes') or ''}",
        "",
        "## Gold Claims",
        "",
    ]
    for idx, claim in enumerate(case["gold"]["claims"], start=1):
        lines.extend([
            f"{idx}. `{claim.get('status')}` {claim.get('text')}",
            f"Evidence steps: `{claim.get('evidence_steps')}`",
            "",
        ])
    lines.extend(["## Predicted Claims", ""])
    for idx, claim in enumerate(pred.get("claims") or [], start=1):
        lines.extend([
            f"{idx}. `{claim.get('status')}` {claim.get('text')}",
            f"Evidence steps: `{claim.get('evidence_steps')}` confidence=`{claim.get('confidence')}`",
            f"Rationale: {claim.get('rationale') or ''}",
        ])
        for evidence in claim.get("evidence") or []:
            observation = evidence.get("observation") or ""
            if len(observation) > 700:
                observation = observation[:700] + "..."
            lines.append(f"- step `{evidence.get('step_index')}` score=`{evidence.get('confidence')}`: {observation}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build human-review artifacts for gold/prediction verification differences.")
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--include-matches", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    gold_data = load_json(args.gold)
    pred_data = load_json(args.predictions)
    gold_items = {requirement_id(item): item for item in items_from_gold(gold_data)}
    pred_items = {requirement_id(item): item for item in items_from_predictions(pred_data)}

    cases = [build_case(gold_items[rid], pred_items.get(rid)) for rid in sorted(gold_items)]
    selected = [case for case in cases if args.include_matches or case["case_type"] != "match"]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for subdir in ("false_fulfillment", "label_mismatch", "evidence_mismatch", "missing_prediction", "all_cases"):
        (args.out_dir / subdir).mkdir(exist_ok=True)

    counts: dict[str, int] = {}
    for case in cases:
        counts[case["case_type"]] = counts.get(case["case_type"], 0) + 1

    summary = {
        "gold": str(args.gold),
        "predictions": str(args.predictions),
        "out_dir": str(args.out_dir),
        "case_counts": counts,
        "selected_count": len(selected),
        "false_fulfillment_ids": [case["requirement_id"] for case in cases if case["case_type"] == "false_fulfillment"],
        "label_mismatch_ids": [case["requirement_id"] for case in cases if case["case_type"] == "label_mismatch"],
    }
    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    summary_lines = [
        "# Evaluation Review Summary",
        "",
        f"Gold: `{args.gold}`",
        f"Predictions: `{args.predictions}`",
        "",
        "## Case Counts",
        "",
    ]
    for key in sorted(counts):
        summary_lines.append(f"- `{key}`: {counts[key]}")
    summary_lines.extend(["", "## False Fulfillments", ""])
    for case in cases:
        if case["case_type"] == "false_fulfillment":
            summary_lines.append(f"- `{case['requirement_id']}` gold=`{case['gold']['label']}` pred=`{case['prediction']['label']}`: {case['requirement_text']}")
    (args.out_dir / "summary.md").write_text("\n".join(summary_lines), encoding="utf-8")

    for case in selected:
        rid = slug(case["requirement_id"])
        json_path = args.out_dir / "all_cases" / f"{rid}.json"
        md_path = args.out_dir / "all_cases" / f"{rid}.md"
        json_path.write_text(json.dumps(case, indent=2, ensure_ascii=False), encoding="utf-8")
        write_markdown(case, md_path)
        if case["case_type"] == "false_fulfillment":
            target = args.out_dir / "false_fulfillment" / f"{rid}.md"
            write_markdown(case, target)
        elif case["case_type"] == "label_mismatch":
            target = args.out_dir / "label_mismatch" / f"{rid}.md"
            write_markdown(case, target)
        elif case["case_type"] == "missing_prediction":
            target = args.out_dir / "missing_prediction" / f"{rid}.md"
            write_markdown(case, target)
        elif case["case_type"] == "label_match_evidence_mismatch":
            target = args.out_dir / "evidence_mismatch" / f"{rid}.md"
            write_markdown(case, target)

    print(f"cases={len(cases)} selected={len(selected)} out_dir={args.out_dir}")
    print(f"summary={args.out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
