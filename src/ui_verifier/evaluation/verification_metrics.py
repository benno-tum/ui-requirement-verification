from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Iterable

from ui_verifier.verification.schemas import VerificationLabel


DEFAULT_LABELS = [label.value for label in VerificationLabel]
DEFAULT_CLAIM_STATUSES = [
    "SUPPORTED",
    "SUPPORTED_WITH_CAVEAT",
    "PARTIALLY_SUPPORTED",
    "MISSING",
    "CONTRADICTED",
    "HIDDEN",
    "AMBIGUOUS",
    "OUT_OF_SCOPE",
]

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(slots=True)
class ClaimRecord:
    text: str
    status: str
    evidence_steps: list[int] = field(default_factory=list)


@dataclass(slots=True)
class RequirementRecord:
    flow_id: str
    requirement_id: str
    label: str | None = None
    evidence_steps: list[int] = field(default_factory=list)
    claims: list[ClaimRecord] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.flow_id}::{self.requirement_id}"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_label(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "PARTIAL": "PARTIALLY_FULFILLED",
        "PARTIALLYFULFILLED": "PARTIALLY_FULFILLED",
        "NOTFULFILLED": "NOT_FULFILLED",
    }
    return aliases.get(normalized, normalized)


def _normalize_status(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    return value.strip().upper().replace("-", "_").replace(" ", "_")


def _step_index(item: Any) -> int | None:
    if not isinstance(item, dict):
        return None
    value = item.get("step_index")
    try:
        step = int(value)
    except (TypeError, ValueError):
        return None
    return step if step >= 0 else None


def _steps_from_items(items: Iterable[Any]) -> list[int]:
    steps: list[int] = []
    seen: set[int] = set()
    for item in items:
        step = _step_index(item)
        if step is None or step in seen:
            continue
        seen.add(step)
        steps.append(step)
    return steps


def _steps_from_any(data: dict[str, Any]) -> list[int]:
    raw_steps = data.get("evidence_steps")
    if isinstance(raw_steps, list):
        steps: list[int] = []
        seen: set[int] = set()
        for value in raw_steps:
            try:
                step = int(value)
            except (TypeError, ValueError):
                continue
            if step >= 0 and step not in seen:
                seen.add(step)
                steps.append(step)
        if steps:
            return steps

    for key in ("evidence", "evidence_units"):
        raw_items = data.get(key)
        if isinstance(raw_items, list):
            steps = _steps_from_items(raw_items)
            if steps:
                return steps
    return []


def _claim_text(data: dict[str, Any]) -> str:
    for key in ("claim", "claim_text", "text"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _claims_from_gold_item(item: dict[str, Any]) -> list[ClaimRecord]:
    records: list[ClaimRecord] = []
    raw_claims = item.get("claims")
    if not isinstance(raw_claims, list):
        return records
    for claim in raw_claims:
        if not isinstance(claim, dict):
            continue
        status = _normalize_status(claim.get("status"))
        text = _claim_text(claim)
        if not status or not text:
            continue
        records.append(ClaimRecord(text=text, status=status, evidence_steps=_steps_from_any(claim)))
    return records


def _claims_from_prediction_item(item: dict[str, Any]) -> list[ClaimRecord]:
    records: list[ClaimRecord] = []
    raw_claims = item.get("claims")
    if not isinstance(raw_claims, list):
        return records
    for claim in raw_claims:
        if not isinstance(claim, dict):
            continue
        status = _normalize_status(claim.get("status") or claim.get("label"))
        text = _claim_text(claim)
        if not status or not text:
            continue
        records.append(ClaimRecord(text=text, status=status, evidence_steps=_steps_from_any(claim)))
    return records


def load_gold_file(path: Path) -> list[RequirementRecord]:
    data = _load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"Gold file must be a JSON object: {path}")
    flow_id = str(data.get("flow_id") or path.parent.name)
    raw_items = data.get("items") or data.get("requirements")
    if not isinstance(raw_items, list):
        raise ValueError(f"Gold file has no items list: {path}")

    records: list[RequirementRecord] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        requirement_id = str(item.get("requirement_id") or item.get("id") or "").strip()
        if not requirement_id:
            continue
        label = _normalize_label(item.get("verification_label") or item.get("manual_verification_label"))
        records.append(
            RequirementRecord(
                flow_id=str(item.get("flow_id") or flow_id),
                requirement_id=requirement_id,
                label=label,
                evidence_steps=_steps_from_any(item),
                claims=_claims_from_gold_item(item),
            )
        )
    return records


def load_gold_root(root: Path) -> dict[str, RequirementRecord]:
    if root.is_file():
        paths = [root]
    else:
        paths = sorted(root.glob("*/verification_gold.json"))
    records: dict[str, RequirementRecord] = {}
    for path in paths:
        for record in load_gold_file(path):
            records[record.key] = record
    return records


def _prediction_items(data: dict[str, Any]) -> tuple[str, list[dict[str, Any]], str]:
    flow_id = str(data.get("flow_id") or "")
    if isinstance(data.get("verdicts"), list):
        return flow_id, [item for item in data["verdicts"] if isinstance(item, dict)], "verification_run"
    if isinstance(data.get("results"), list):
        return flow_id, [item for item in data["results"] if isinstance(item, dict)], "pipeline_output"
    if isinstance(data.get("items"), list):
        return flow_id, [item for item in data["items"] if isinstance(item, dict)], "items"
    raise ValueError("Prediction file must contain verdicts, results, or items")


def load_prediction_file(path: Path) -> list[RequirementRecord]:
    data = _load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"Prediction file must be a JSON object: {path}")
    flow_id, raw_items, kind = _prediction_items(data)
    if not flow_id:
        flow_id = path.parent.name if path.name == "verification_run.json" else path.stem

    records: list[RequirementRecord] = []
    for item in raw_items:
        requirement_id = str(item.get("requirement_id") or item.get("id") or "").strip()
        if not requirement_id:
            continue
        label = _normalize_label(item.get("label") or item.get("final_label") or item.get("verification_label"))
        records.append(
            RequirementRecord(
                flow_id=flow_id,
                requirement_id=requirement_id,
                label=label,
                evidence_steps=_steps_from_any(item),
                claims=_claims_from_prediction_item(item) if kind == "pipeline_output" else [],
            )
        )
    return records


def load_prediction_root(path: Path) -> dict[str, RequirementRecord]:
    if path.is_file():
        paths = [path]
    else:
        direct = sorted(path.glob("*.json"))
        nested = sorted(path.glob("*/verification_run.json"))
        paths = direct + nested
    records: dict[str, RequirementRecord] = {}
    for file_path in paths:
        try:
            loaded = load_prediction_file(file_path)
        except ValueError:
            continue
        for record in loaded:
            records[record.key] = record
    return records


def _safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def classification_metrics(
    gold: dict[str, RequirementRecord],
    predictions: dict[str, RequirementRecord],
    *,
    labels: list[str] | None = None,
    missing_prediction_label: str = "ABSTAIN",
) -> dict[str, Any]:
    labels = labels or DEFAULT_LABELS
    label_set = set(labels)
    confusion = {gold_label: {pred_label: 0 for pred_label in labels} for gold_label in labels}
    per_class: dict[str, dict[str, float | int]] = {}
    pairs: list[tuple[str, str]] = []
    missing_predictions = 0
    skipped_gold_without_label = 0

    for key, gold_record in gold.items():
        gold_label = gold_record.label
        if gold_label not in label_set:
            skipped_gold_without_label += 1
            continue
        pred_record = predictions.get(key)
        pred_label = pred_record.label if pred_record else None
        if pred_label not in label_set:
            pred_label = missing_prediction_label
        if pred_record is None:
            missing_predictions += 1
        pairs.append((gold_label, pred_label))
        confusion[gold_label][pred_label] += 1

    total = len(pairs)
    accuracy = _safe_div(sum(1 for g, p in pairs if g == p), total)
    for label in labels:
        tp = sum(1 for g, p in pairs if g == label and p == label)
        fp = sum(1 for g, p in pairs if g != label and p == label)
        fn = sum(1 for g, p in pairs if g == label and p != label)
        support = sum(1 for g, _ in pairs if g == label)
        predicted = sum(1 for _, p in pairs if p == label)
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2 * precision * recall, precision + recall)
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
            "predicted": predicted,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }

    macro_f1 = _safe_div(sum(float(per_class[label]["f1"]) for label in labels), len(labels))
    weighted_f1 = _safe_div(
        sum(float(per_class[label]["f1"]) * int(per_class[label]["support"]) for label in labels),
        total,
    )
    predicted_fulfilled = sum(1 for _, pred_label in pairs if pred_label == "FULFILLED")
    false_fulfilled = sum(1 for gold_label, pred_label in pairs if pred_label == "FULFILLED" and gold_label != "FULFILLED")

    return {
        "total": total,
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "per_class": per_class,
        "confusion_matrix": confusion,
        "abstain_rate": _safe_div(sum(1 for _, pred_label in pairs if pred_label == "ABSTAIN"), total),
        "false_fulfillment_rate": _safe_div(false_fulfilled, predicted_fulfilled),
        "false_fulfilled": false_fulfilled,
        "predicted_fulfilled": predicted_fulfilled,
        "prediction_coverage": _safe_div(total - missing_predictions, total),
        "missing_predictions": missing_predictions,
        "skipped_gold_without_label": skipped_gold_without_label,
    }


def evidence_metrics(
    gold: dict[str, RequirementRecord],
    predictions: dict[str, RequirementRecord],
    *,
    k_values: list[int] | None = None,
) -> dict[str, Any]:
    k_values = k_values or [1, 3]
    rows = []
    for key, gold_record in gold.items():
        gold_steps = set(gold_record.evidence_steps)
        if not gold_steps:
            continue
        pred_steps = predictions.get(key).evidence_steps if key in predictions else []
        first_hit_rank = None
        for index, step in enumerate(pred_steps, start=1):
            if step in gold_steps:
                first_hit_rank = index
                break
        row = {
            "key": key,
            "gold_steps": sorted(gold_steps),
            "predicted_steps": pred_steps,
            "first_hit_rank": first_hit_rank,
            "reciprocal_rank": 1 / first_hit_rank if first_hit_rank else 0.0,
        }
        for k in k_values:
            top_k = pred_steps[:k]
            hits = len(set(top_k).intersection(gold_steps))
            row[f"precision_at_{k}"] = _safe_div(hits, len(top_k))
            row[f"recall_at_{k}"] = _safe_div(hits, len(gold_steps))
            row[f"hit_at_{k}"] = 1.0 if hits else 0.0
        rows.append(row)

    total = len(rows)
    result: dict[str, Any] = {
        "total_with_gold_evidence": total,
        "mrr": _safe_div(sum(float(row["reciprocal_rank"]) for row in rows), total),
    }
    for k in k_values:
        result[f"precision_at_{k}"] = _safe_div(sum(float(row[f"precision_at_{k}"]) for row in rows), total)
        result[f"recall_at_{k}"] = _safe_div(sum(float(row[f"recall_at_{k}"]) for row in rows), total)
        result[f"hit_at_{k}"] = _safe_div(sum(float(row[f"hit_at_{k}"]) for row in rows), total)
    return result


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _token_f1(a: str, b: str) -> float:
    a_tokens = _tokens(a)
    b_tokens = _tokens(b)
    if not a_tokens or not b_tokens:
        return 0.0
    overlap = len(a_tokens.intersection(b_tokens))
    precision = _safe_div(overlap, len(b_tokens))
    recall = _safe_div(overlap, len(a_tokens))
    return _safe_div(2 * precision * recall, precision + recall)


def _match_claims(gold_claims: list[ClaimRecord], pred_claims: list[ClaimRecord], threshold: float) -> list[tuple[ClaimRecord, ClaimRecord | None]]:
    unmatched_pred = set(range(len(pred_claims)))
    matches: list[tuple[ClaimRecord, ClaimRecord | None]] = []
    for gold_claim in gold_claims:
        best_index = None
        best_score = 0.0
        for index in unmatched_pred:
            score = _token_f1(gold_claim.text, pred_claims[index].text)
            if score > best_score:
                best_index = index
                best_score = score
        if best_index is not None and best_score >= threshold:
            unmatched_pred.remove(best_index)
            matches.append((gold_claim, pred_claims[best_index]))
        else:
            matches.append((gold_claim, None))
    return matches


def claim_status_metrics(
    gold: dict[str, RequirementRecord],
    predictions: dict[str, RequirementRecord],
    *,
    statuses: list[str] | None = None,
    unmatched_prediction_status: str = "MISSING",
    match_threshold: float = 0.55,
) -> dict[str, Any]:
    statuses = statuses or DEFAULT_CLAIM_STATUSES
    pairs: list[tuple[str, str]] = []
    matched_claims = 0
    gold_claim_count = 0
    prediction_claim_count = 0

    for key, gold_record in gold.items():
        if not gold_record.claims:
            continue
        pred_claims = predictions.get(key).claims if key in predictions else []
        gold_claim_count += len(gold_record.claims)
        prediction_claim_count += len(pred_claims)
        for gold_claim, pred_claim in _match_claims(gold_record.claims, pred_claims, match_threshold):
            pred_status = pred_claim.status if pred_claim else unmatched_prediction_status
            if pred_claim:
                matched_claims += 1
            pairs.append((gold_claim.status, pred_status))

    temp_gold = {
        str(index): RequirementRecord(flow_id="claims", requirement_id=str(index), label=gold_status)
        for index, (gold_status, _) in enumerate(pairs)
    }
    temp_pred = {
        str(index): RequirementRecord(flow_id="claims", requirement_id=str(index), label=pred_status)
        for index, (_, pred_status) in enumerate(pairs)
    }
    metrics = classification_metrics(
        temp_gold,
        temp_pred,
        labels=statuses,
        missing_prediction_label=unmatched_prediction_status,
    )
    metrics.update(
        {
            "gold_claim_count": gold_claim_count,
            "prediction_claim_count": prediction_claim_count,
            "matched_claims": matched_claims,
            "claim_match_recall": _safe_div(matched_claims, gold_claim_count),
        }
    )
    return metrics


def evaluate_predictions(
    gold_root: Path,
    predictions_path: Path,
    *,
    include_claims: bool = True,
    k_values: list[int] | None = None,
) -> dict[str, Any]:
    gold = load_gold_root(gold_root)
    predictions = load_prediction_root(predictions_path)
    label_metrics = classification_metrics(gold, predictions)
    result: dict[str, Any] = {
        "gold_count": len(gold),
        "prediction_count": len(predictions),
        "label_metrics": label_metrics,
        "evidence_metrics": evidence_metrics(gold, predictions, k_values=k_values),
    }
    if include_claims:
        result["claim_status_metrics"] = claim_status_metrics(gold, predictions)
    return result
