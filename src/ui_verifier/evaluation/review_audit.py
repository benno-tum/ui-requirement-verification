from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import threading
from typing import Any, Iterable

from PIL import Image

from ui_verifier.common.flow_utils import find_step_images, parse_step_number
from ui_verifier.localization import TextBoxLocalizer
from ui_verifier.verification_pipeline.requirement_understanding import RequirementUnderstanding


UI_LABELS = (
    "NOT_UI_VERIFIABLE",
    "PARTIALLY_UI_VERIFIABLE",
    "UI_VERIFIABLE",
)
UI_LABEL_ORDINAL = {label: index for index, label in enumerate(UI_LABELS)}
BBOX_APPLICABILITY = {
    "SINGLE_REGION",
    "MULTI_REGION",
    "WHOLE_SCREEN_OR_TRANSITION",
    "NO_VISIBLE_REGION",
}
BBOX_REVIEW_VALUES = {"YES", "PARTIAL", "NO", "NOT_APPLICABLE"}
BBOX_ERROR_CATEGORIES = {
    "WRONG_TEXT",
    "TOO_TIGHT",
    "TOO_BROAD",
    "WRONG_REGION",
    "COORDINATE_MISMATCH",
    "NON_TEXT_EVIDENCE",
    "MULTI_REGION_EVIDENCE",
}

_AUDIT_MUTATION_LOCK = threading.RLock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def image_asset_metadata_errors(item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    path = Path(str(item.get("image_path") or ""))
    if not path.is_file():
        return ["IMAGE_NOT_FOUND"]
    try:
        with Image.open(path) as image:
            if int(item.get("image_width") or 0) != image.width or int(item.get("image_height") or 0) != image.height:
                errors.append("IMAGE_DIMENSION_MISMATCH")
    except OSError:
        return ["IMAGE_UNREADABLE"]
    if str(item.get("image_sha256") or "") != sha256_file(path):
        errors.append("IMAGE_HASH_MISMATCH")
    if item.get("coordinate_space") != "image_pixels":
        errors.append("INVALID_COORDINATE_SPACE")
    return errors


def stable_key(seed: int, value: str) -> str:
    return hashlib.sha256(f"{seed}|{value}".encode("utf-8")).hexdigest()


def dataset_for_flow(flow_id: str) -> str:
    return "pure" if flow_id.startswith("pure_") else "mind2web"


def source_group(item: dict[str, Any]) -> str:
    requirement_id = str(item.get("requirement_id") or "")
    source_type = str(item.get("source_type") or "")
    return "contrastive" if requirement_id.startswith("CONTR-") or source_type == "requirements_candidate" else "source"


def claim_counts(item: dict[str, Any]) -> tuple[int, int]:
    claims = item.get("claims") if isinstance(item.get("claims"), list) else []
    observable = sum(1 for claim in claims if claim.get("claim_type") == "OBSERVABLE")
    hidden = sum(1 for claim in claims if claim.get("claim_type") == "HIDDEN")
    return observable, hidden


def structural_conflict_reasons(item: dict[str, Any]) -> list[str]:
    observable, hidden = claim_counts(item)
    label = item.get("ui_evaluability")
    reasons: list[str] = []
    if label == "UI_VERIFIABLE" and hidden > 0:
        reasons.append("UI_LABEL_HAS_HIDDEN_CLAIM")
    if label == "PARTIALLY_UI_VERIFIABLE" and (observable == 0 or hidden == 0):
        reasons.append("PARTIAL_LABEL_MISSING_OBSERVABLE_OR_HIDDEN_CLAIM")
    if label == "NOT_UI_VERIFIABLE" and observable > 0:
        reasons.append("NOT_UI_LABEL_HAS_OBSERVABLE_CLAIM")
    return reasons


def load_verification_gold(gold_root: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(gold_root.glob("*/verification_gold.json")):
        data = load_json(path)
        for raw_item in data.get("items", []):
            item = dict(raw_item)
            item["dataset"] = dataset_for_flow(str(item.get("flow_id") or data.get("flow_id") or ""))
            items.append(item)
    return items


def _round_robin_controls(candidates: list[dict[str, Any]], *, count: int, seed: int) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in candidates:
        key = (
            str(item.get("ui_evaluability")),
            str(item.get("dataset")),
            source_group(item),
        )
        buckets[key].append(item)
    for bucket in buckets.values():
        bucket.sort(key=lambda item: stable_key(seed, f"{item['flow_id']}|{item['requirement_id']}"))

    selected: list[dict[str, Any]] = []
    ordered_keys = sorted(buckets, key=lambda value: stable_key(seed, "|".join(value)))
    while len(selected) < count and ordered_keys:
        next_keys: list[tuple[str, str, str]] = []
        for key in ordered_keys:
            if buckets[key] and len(selected) < count:
                selected.append(buckets[key].pop(0))
            if buckets[key]:
                next_keys.append(key)
        ordered_keys = next_keys
    if len(selected) != count:
        raise ValueError(f"Only {len(selected)} UI controls were available; expected {count}.")
    return selected


def build_ui_review_bundle(
    items: list[dict[str, Any]],
    *,
    sample_size: int = 72,
    seed: int = 20260717,
) -> tuple[dict[str, Any], dict[str, Any]]:
    by_id = {f"{item['flow_id']}|{item['requirement_id']}": item for item in items}
    selected_ids = {
        key
        for key, item in by_id.items()
        if item.get("ui_evaluability") == "NOT_UI_VERIFIABLE" or structural_conflict_reasons(item)
    }
    if len(selected_ids) > sample_size:
        raise ValueError(f"{len(selected_ids)} mandatory UI audit items exceed sample size {sample_size}.")
    controls_needed = sample_size - len(selected_ids)
    controls = _round_robin_controls(
        [item for key, item in by_id.items() if key not in selected_ids],
        count=controls_needed,
        seed=seed,
    )
    selected_ids.update(f"{item['flow_id']}|{item['requirement_id']}" for item in controls)
    selected = [by_id[key] for key in selected_ids]
    selected.sort(key=lambda item: stable_key(seed, f"{item['flow_id']}|{item['requirement_id']}"))

    public_items: list[dict[str, Any]] = []
    references: dict[str, Any] = {}
    for index, item in enumerate(selected, start=1):
        audit_item_id = f"UI-{index:03d}"
        public_items.append(
            {
                "audit_item_id": audit_item_id,
                "flow_id": item["flow_id"],
                "dataset": item["dataset"],
                "requirement_id": item["requirement_id"],
                "requirement_text": item["text"],
                "step_indices": item.get("step_indices") or item.get("evidence_steps") or [],
            }
        )
        references[audit_item_id] = {
            "flow_id": item["flow_id"],
            "requirement_id": item["requirement_id"],
            "gold_label": item["ui_evaluability"],
            "structural_conflict_reasons": structural_conflict_reasons(item),
            "source_group": source_group(item),
            "annotated_by": item.get("annotated_by"),
        }

    manifest = {
        "schema_version": "ui_evaluability_review_v1",
        "blind": True,
        "seed": seed,
        "sample_size": len(public_items),
        "sampling_note": "Targeted audit: all NOT_UI_VERIFIABLE and structural-conflict items plus stratified controls.",
        "items": public_items,
    }
    private = {
        "schema_version": "ui_evaluability_review_reference_v1",
        "items": references,
    }
    return manifest, private


def _flow_dir(flows_root: Path, flow_id: str) -> tuple[str, Path]:
    matches = [(path.parent.name, path) for path in flows_root.glob(f"*/{flow_id}") if path.is_dir()]
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one flow directory for {flow_id}, found {len(matches)}.")
    return matches[0]


def _step_path(flow_dir: Path, step_index: int) -> Path:
    matches = [path for path in find_step_images(flow_dir) if parse_step_number(path) == step_index]
    if not matches:
        raise FileNotFoundError(f"Step {step_index} not found in {flow_dir}.")
    return matches[0]


def _claim_text(claim: dict[str, Any]) -> str:
    return str(claim.get("claim_text") or claim.get("claim") or "").strip()


def bbox_candidates_for_flow(
    item_by_flow: dict[str, list[dict[str, Any]]],
    *,
    flows_root: Path,
    flow_id: str,
    localizer: TextBoxLocalizer,
) -> list[dict[str, Any]]:
    dataset, flow_dir = _flow_dir(flows_root, flow_id)
    candidates: list[dict[str, Any]] = []
    for item in item_by_flow.get(flow_id, []):
        for claim_index, claim in enumerate(item.get("claims") or [], start=1):
            claim_text = _claim_text(claim)
            if not claim_text:
                continue
            claim_id = str(claim.get("claim_id") or f"{item['requirement_id']}-C{claim_index}")
            for step_index in sorted(set(int(value) for value in claim.get("evidence_steps") or [])):
                image_path = _step_path(flow_dir, step_index)
                suggestions = localizer.suggest(claim_text, image_path, max_candidates=5)
                with Image.open(image_path) as image:
                    width, height = int(image.width), int(image.height)
                top = suggestions[0] if suggestions else None
                candidates.append(
                    {
                        "dataset": dataset,
                        "flow_id": flow_id,
                        "requirement_id": item["requirement_id"],
                        "requirement_text": item["text"],
                        "claim_id": claim_id,
                        "claim_text": claim_text,
                        "step_index": step_index,
                        "image_path": str(image_path),
                        "image_name": image_path.name,
                        "image_width": width,
                        "image_height": height,
                        "image_sha256": sha256_file(image_path),
                        "prediction": top,
                        "all_suggestions": suggestions,
                        "claim_status": claim.get("status"),
                        "claim_type": claim.get("claim_type"),
                        "source_group": source_group(item),
                    }
                )
    return candidates


def _bbox_stratum(candidate: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
    prediction = candidate.get("prediction")
    if not prediction:
        score_bucket = "no_proposal"
        level = "none"
    else:
        score = float(prediction.get("score") or 0.0)
        score_bucket = "low" if score < 0.2 else "medium" if score < 0.4 else "high"
        level = str(prediction.get("level") or "unknown")
    length_bucket = "short" if len(candidate["claim_text"].split()) < 12 else "long"
    visible_status = str(candidate.get("claim_status") or "UNKNOWN")
    # Before human region annotation, OCR overlap is the only deterministic proxy
    # available for text evidence versus broader visual evidence.
    evidence_mode_proxy = "OCR_TEXT_CANDIDATE" if prediction and float(prediction.get("score") or 0.0) >= 0.2 else "BROADER_VISUAL_CANDIDATE"
    return score_bucket, level, length_bucket, visible_status, evidence_mode_proxy, str(candidate.get("source_group"))


def _stratified_bbox_sample(candidates: list[dict[str, Any]], *, count: int, seed: int) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        buckets[_bbox_stratum(candidate)].append(candidate)
    for bucket in buckets.values():
        bucket.sort(
            key=lambda item: stable_key(
                seed,
                f"{item['flow_id']}|{item['requirement_id']}|{item['claim_id']}|{item['step_index']}",
            )
        )
    selected: list[dict[str, Any]] = []
    keys = sorted(buckets, key=lambda value: stable_key(seed, "|".join(value)))
    while len(selected) < count and keys:
        remaining: list[tuple[str, str, str, str, str, str]] = []
        for key in keys:
            if buckets[key] and len(selected) < count:
                selected.append(buckets[key].pop(0))
            if buckets[key]:
                remaining.append(key)
        keys = remaining
    if len(selected) != count:
        raise ValueError(f"Only {len(selected)} bbox candidates available; expected {count}.")
    return selected


def build_bbox_review_bundle(
    items: list[dict[str, Any]],
    *,
    flows_root: Path,
    flow_ids: Iterable[str],
    per_flow: int = 15,
    seed: int = 20260717,
) -> tuple[dict[str, Any], dict[str, Any]]:
    item_by_flow: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        item_by_flow[str(item["flow_id"])].append(item)
    localizer = TextBoxLocalizer()
    selected: list[dict[str, Any]] = []
    for flow_id in flow_ids:
        candidates = bbox_candidates_for_flow(
            item_by_flow,
            flows_root=flows_root,
            flow_id=flow_id,
            localizer=localizer,
        )
        selected.extend(_stratified_bbox_sample(candidates, count=per_flow, seed=seed))
    selected.sort(
        key=lambda item: stable_key(
            seed,
            f"{item['flow_id']}|{item['requirement_id']}|{item['claim_id']}|{item['step_index']}",
        )
    )

    public_items: list[dict[str, Any]] = []
    references: dict[str, Any] = {}
    for index, item in enumerate(selected, start=1):
        audit_item_id = f"BBOX-{index:03d}"
        image_path = Path(item["image_path"])
        image_url = f"/static/flows/{item['dataset']}/{item['flow_id']}/{image_path.name}"
        public_items.append(
            {
                "audit_item_id": audit_item_id,
                "dataset": item["dataset"],
                "flow_id": item["flow_id"],
                "requirement_id": item["requirement_id"],
                "requirement_text": item["requirement_text"],
                "claim_id": item["claim_id"],
                "claim_text": item["claim_text"],
                "step_index": item["step_index"],
                "image_url": image_url,
                "image_path": item["image_path"],
                "image_width": item["image_width"],
                "image_height": item["image_height"],
                "image_sha256": item["image_sha256"],
                "coordinate_space": "image_pixels",
            }
        )
        references[audit_item_id] = {
            "prediction": item["prediction"],
            "all_suggestions": item["all_suggestions"],
            "claim_status": item["claim_status"],
            "claim_type": item["claim_type"],
            "source_group": item["source_group"],
            "sampling_stratum": _bbox_stratum(item),
        }
    return (
        {
            "schema_version": "bounding_box_review_v1",
            "blind": True,
            "seed": seed,
            "sample_size": len(public_items),
            "sampling_note": "Conditional OCR localization audit over human claim-step pairs.",
            "items": public_items,
        },
        {
            "schema_version": "bounding_box_review_reference_v1",
            "items": references,
        },
    )


def _safe_reviewer_id(value: str) -> str:
    normalized = "".join(character for character in value.strip().lower() if character.isalnum() or character in "-_")
    if not normalized or len(normalized) > 64:
        raise ValueError("reviewer_id must contain 1-64 letters, digits, hyphens, or underscores.")
    return normalized


@dataclass
class EvaluationAuditStore:
    root: Path

    def audit_dir(self, audit_id: str) -> Path:
        if not audit_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in audit_id):
            raise ValueError("Invalid audit id.")
        path = (self.root / audit_id).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError("Invalid audit path.")
        return path

    def list_audits(self) -> list[dict[str, Any]]:
        audits: list[dict[str, Any]] = []
        if not self.root.exists():
            return audits
        for path in sorted(self.root.iterdir()):
            manifest_path = path / "audit.json"
            if path.is_dir() and manifest_path.exists():
                audits.append(load_json(manifest_path))
        return sorted(audits, key=lambda audit: str(audit.get("created_at") or ""), reverse=True)

    def load_public_manifest(self, audit_id: str, kind: str) -> dict[str, Any]:
        filename = "ui_manifest.json" if kind == "ui" else "bbox_manifest.json"
        path = self.audit_dir(audit_id) / filename
        if not path.exists():
            raise FileNotFoundError(path)
        return load_json(path)

    def load_private_reference(self, audit_id: str, kind: str) -> dict[str, Any]:
        filename = "ui_reference.json" if kind == "ui" else "bbox_reference.json"
        path = self.audit_dir(audit_id) / filename
        if not path.exists():
            raise FileNotFoundError(path)
        return load_json(path)

    def _review_path(self, audit_id: str, reviewer_id: str, kind: str) -> Path:
        reviewer = _safe_reviewer_id(reviewer_id)
        return self.audit_dir(audit_id) / "responses" / reviewer / f"{kind}_reviews.json"

    def load_reviews(self, audit_id: str, reviewer_id: str, kind: str) -> dict[str, Any]:
        path = self._review_path(audit_id, reviewer_id, kind)
        if not path.exists():
            return {"schema_version": f"{kind}_review_responses_v1", "reviewer_id": _safe_reviewer_id(reviewer_id), "items": {}}
        return load_json(path)

    def save_review(self, audit_id: str, reviewer_id: str, kind: str, item_id: str, review: dict[str, Any]) -> dict[str, Any]:
        manifest = self.load_public_manifest(audit_id, kind)
        valid_ids = {item["audit_item_id"] for item in manifest.get("items", [])}
        if item_id not in valid_ids:
            raise KeyError(item_id)
        with _AUDIT_MUTATION_LOCK:
            responses = self.load_reviews(audit_id, reviewer_id, kind)
            stored = {**review, "updated_at": utc_now()}
            responses.setdefault("items", {})[item_id] = stored
            write_json(self._review_path(audit_id, reviewer_id, kind), responses)
        return stored

    def load_bbox_inspection_judgments(self, audit_id: str) -> dict[str, Any]:
        path = self.audit_dir(audit_id) / "bbox_inspection_judgments.json"
        if not path.exists():
            return {"schema_version": "bbox_inspection_judgments_v1", "items": {}}
        return load_json(path)

    def save_bbox_inspection_judgment(self, audit_id: str, item_id: str, judgment: dict[str, Any]) -> dict[str, Any]:
        manifest = self.load_public_manifest(audit_id, "bbox")
        if item_id not in {item["audit_item_id"] for item in manifest.get("items", [])}:
            raise KeyError(item_id)
        with _AUDIT_MUTATION_LOCK:
            stored = {**judgment, "updated_at": utc_now()}
            payload = self.load_bbox_inspection_judgments(audit_id)
            payload.setdefault("items", {})[item_id] = stored
            write_json(self.audit_dir(audit_id) / "bbox_inspection_judgments.json", payload)
        return stored

    def load_bbox_candidate_selections(self, audit_id: str) -> dict[str, Any]:
        path = self.audit_dir(audit_id) / "bbox_candidate_selections.json"
        if not path.exists():
            return {"schema_version": "bbox_candidate_selections_v1", "items": {}}
        return load_json(path)

    def save_bbox_candidate_selection(self, audit_id: str, item_id: str, selection: dict[str, Any]) -> dict[str, Any]:
        manifest = self.load_public_manifest(audit_id, "bbox")
        if item_id not in {item["audit_item_id"] for item in manifest.get("items", [])}:
            raise KeyError(item_id)
        with _AUDIT_MUTATION_LOCK:
            stored = {**selection, "updated_at": utc_now()}
            payload = self.load_bbox_candidate_selections(audit_id)
            payload.setdefault("items", {})[item_id] = stored
            write_json(self.audit_dir(audit_id) / "bbox_candidate_selections.json", payload)
        return stored

    def public_items_for_reviewer(self, audit_id: str, reviewer_id: str, kind: str) -> dict[str, Any]:
        manifest = self.load_public_manifest(audit_id, kind)
        responses = self.load_reviews(audit_id, reviewer_id, kind).get("items", {})
        references = self.load_private_reference(audit_id, kind).get("items", {}) if kind == "bbox" else {}
        items: list[dict[str, Any]] = []
        for item in manifest.get("items", []):
            item_id = item["audit_item_id"]
            response = responses.get(item_id)
            public_item = {**item, "review": response}
            if kind == "bbox" and response and response.get("gold_locked"):
                public_item["prediction"] = references.get(item_id, {}).get("prediction")
            items.append(public_item)
        return {**manifest, "reviewer_id": _safe_reviewer_id(reviewer_id), "items": items}


def validate_ui_review(review: dict[str, Any]) -> dict[str, Any]:
    label = str(review.get("label") or "")
    if label not in UI_LABELS:
        raise ValueError(f"label must be one of: {', '.join(UI_LABELS)}")
    confidence = float(review.get("confidence", 0.5))
    if confidence < 0 or confidence > 1:
        raise ValueError("confidence must be between 0 and 1.")
    return {
        "label": label,
        "rationale": str(review.get("rationale") or "").strip(),
        "confidence": confidence,
        "ambiguous": bool(review.get("ambiguous", False)),
    }


def _normalize_box(box: Any) -> dict[str, float]:
    if not isinstance(box, dict):
        raise ValueError("Each gold box must be an object.")
    try:
        normalized = {key: float(box[key]) for key in ("x1", "y1", "x2", "y2")}
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Each gold box needs numeric x1, y1, x2, and y2.") from exc
    if normalized["x2"] <= normalized["x1"] or normalized["y2"] <= normalized["y1"]:
        raise ValueError("Gold boxes must have positive width and height.")
    return normalized


def validate_bbox_review(review: dict[str, Any], *, image_width: int, image_height: int) -> dict[str, Any]:
    applicability = str(review.get("applicability") or "")
    if applicability not in BBOX_APPLICABILITY:
        raise ValueError(f"applicability must be one of: {', '.join(sorted(BBOX_APPLICABILITY))}")
    boxes = [_normalize_box(box) for box in review.get("gold_boxes") or []]
    for box in boxes:
        if box["x1"] < 0 or box["y1"] < 0 or box["x2"] > image_width or box["y2"] > image_height:
            raise ValueError("Gold boxes must fit within the declared image dimensions.")
    if applicability == "SINGLE_REGION" and len(boxes) != 1:
        raise ValueError("SINGLE_REGION requires exactly one gold box.")
    if applicability == "MULTI_REGION" and len(boxes) < 2:
        raise ValueError("MULTI_REGION requires at least two gold boxes.")
    if applicability in {"WHOLE_SCREEN_OR_TRANSITION", "NO_VISIBLE_REGION"} and boxes:
        raise ValueError(f"{applicability} does not accept gold boxes.")
    relevance = str(review.get("relevance") or "NOT_APPLICABLE")
    sufficiency = str(review.get("sufficiency") or "NOT_APPLICABLE")
    if relevance not in BBOX_REVIEW_VALUES or sufficiency not in BBOX_REVIEW_VALUES:
        raise ValueError("Invalid relevance or sufficiency value.")
    errors = sorted(set(str(value) for value in review.get("error_categories") or []))
    if any(value not in BBOX_ERROR_CATEGORIES for value in errors):
        raise ValueError("Invalid bounding-box error category.")
    return {
        "applicability": applicability,
        "gold_boxes": boxes,
        "evidence_note": str(review.get("evidence_note") or "").strip(),
        "gold_locked": bool(review.get("gold_locked", False)),
        "relevance": relevance,
        "sufficiency": sufficiency,
        "error_categories": errors,
    }


def confusion_matrix(pairs: Iterable[tuple[str, str]], labels: Iterable[str] = UI_LABELS) -> dict[str, dict[str, int]]:
    label_list = list(labels)
    counts = Counter(pairs)
    return {gold: {predicted: counts[(gold, predicted)] for predicted in label_list} for gold in label_list}


def classification_metrics(pairs: list[tuple[str, str]], labels: Iterable[str] = UI_LABELS) -> dict[str, Any]:
    label_list = list(labels)
    matrix = confusion_matrix(pairs, label_list)
    total = len(pairs)
    if total == 0:
        return {"n": 0, "confusion_matrix": matrix}
    correct = sum(matrix[label][label] for label in label_list)
    accuracy = correct / total
    per_class: dict[str, dict[str, float | int]] = {}
    recalls: list[float] = []
    f1_values: list[float] = []
    for label in label_list:
        tp = matrix[label][label]
        gold_count = sum(matrix[label].values())
        predicted_count = sum(matrix[gold][label] for gold in label_list)
        precision = tp / predicted_count if predicted_count else 0.0
        recall = tp / gold_count if gold_count else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"support": gold_count, "precision": precision, "recall": recall, "f1": f1}
        if gold_count:
            recalls.append(recall)
        f1_values.append(f1)
    gold_counts = {label: sum(matrix[label].values()) for label in label_list}
    predicted_counts = {label: sum(matrix[gold][label] for gold in label_list) for label in label_list}
    expected = sum(gold_counts[label] * predicted_counts[label] for label in label_list) / (total * total)
    kappa = (accuracy - expected) / (1 - expected) if expected < 1 else 1.0
    weighted_observed = 0.0
    weighted_expected = 0.0
    maximum_distance = max(1, len(label_list) - 1)
    for gold in label_list:
        for predicted in label_list:
            weight = abs(UI_LABEL_ORDINAL[gold] - UI_LABEL_ORDINAL[predicted]) / maximum_distance
            weighted_observed += weight * matrix[gold][predicted] / total
            weighted_expected += weight * gold_counts[gold] * predicted_counts[predicted] / (total * total)
    weighted_kappa = 1 - weighted_observed / weighted_expected if weighted_expected else 1.0
    return {
        "n": total,
        "accuracy": accuracy,
        "balanced_accuracy": sum(recalls) / len(recalls) if recalls else 0.0,
        "macro_f1": sum(f1_values) / len(f1_values),
        "cohen_kappa": kappa,
        "linear_weighted_kappa": weighted_kappa,
        "per_class": per_class,
        "confusion_matrix": matrix,
    }


def iou(left: dict[str, float], right: dict[str, float]) -> float:
    intersection_width = max(0.0, min(left["x2"], right["x2"]) - max(left["x1"], right["x1"]))
    intersection_height = max(0.0, min(left["y2"], right["y2"]) - max(left["y1"], right["y1"]))
    intersection = intersection_width * intersection_height
    left_area = max(0.0, left["x2"] - left["x1"]) * max(0.0, left["y2"] - left["y1"])
    right_area = max(0.0, right["x2"] - right["x1"]) * max(0.0, right["y2"] - right["y1"])
    union = left_area + right_area - intersection
    return intersection / union if union else 0.0


def center_inside(prediction: dict[str, float], gold: dict[str, float]) -> bool:
    center_x = (prediction["x1"] + prediction["x2"]) / 2
    center_y = (prediction["y1"] + prediction["y2"]) / 2
    return gold["x1"] <= center_x <= gold["x2"] and gold["y1"] <= center_y <= gold["y2"]


def _prediction_box(reference: dict[str, Any]) -> dict[str, float] | None:
    prediction = reference.get("prediction")
    if not isinstance(prediction, dict):
        return None
    bbox = prediction.get("bbox")
    if not isinstance(bbox, dict):
        return None
    return _normalize_box(bbox)


def bbox_metrics(
    public_items: list[dict[str, Any]],
    references: dict[str, Any],
    reviews: dict[str, Any],
) -> dict[str, Any]:
    item_by_id = {item["audit_item_id"]: item for item in public_items}
    rows: list[dict[str, Any]] = []
    for item_id, review in reviews.items():
        item = item_by_id.get(item_id)
        if not item or not review.get("gold_locked"):
            continue
        predicted = _prediction_box(references.get(item_id, {}))
        gold_boxes = [_normalize_box(box) for box in review.get("gold_boxes") or []]
        localizable = review.get("applicability") in {"SINGLE_REGION", "MULTI_REGION"}
        valid = False
        if predicted:
            valid = (
                predicted["x1"] >= 0
                and predicted["y1"] >= 0
                and predicted["x2"] <= item["image_width"]
                and predicted["y2"] <= item["image_height"]
            )
        maximum_iou = max((iou(predicted, gold) for gold in gold_boxes), default=0.0) if predicted else 0.0
        center_hit = any(center_inside(predicted, gold) for gold in gold_boxes) if predicted else False
        rows.append(
            {
                "dataset": item["dataset"],
                "localizable": localizable,
                "single_region": review.get("applicability") == "SINGLE_REGION",
                "prediction_present": predicted is not None,
                "prediction_valid": valid,
                "maximum_iou": maximum_iou,
                "center_hit": center_hit,
                "relevance": review.get("relevance"),
                "sufficiency": review.get("sufficiency"),
                "applicability": review.get("applicability"),
            }
        )

    def summarize(subset: list[dict[str, Any]]) -> dict[str, Any]:
        localizable = [row for row in subset if row["localizable"]]
        single = [row for row in subset if row["single_region"] and row["prediction_present"]]
        predicted = [row for row in subset if row["prediction_present"]]
        return {
            "n_reviewed": len(subset),
            "coordinate_validity_rate": sum(row["prediction_valid"] for row in predicted) / len(predicted) if predicted else None,
            "proposal_coverage": sum(row["prediction_present"] for row in localizable) / len(localizable) if localizable else None,
            "single_region_evaluated": len(single),
            "mean_maximum_iou": sum(row["maximum_iou"] for row in single) / len(single) if single else None,
            "iou_at_0_25": sum(row["maximum_iou"] >= 0.25 for row in single) / len(single) if single else None,
            "iou_at_0_50": sum(row["maximum_iou"] >= 0.5 for row in single) / len(single) if single else None,
            "center_inside_gold_rate": sum(row["center_hit"] for row in single) / len(single) if single else None,
            "human_relevance_rate": sum(row["relevance"] == "YES" for row in predicted) / len(predicted) if predicted else None,
            "human_sufficiency_rate": sum(row["sufficiency"] == "YES" for row in predicted) / len(predicted) if predicted else None,
            "unsupported_multi_region_or_transition_rate": sum(
                row["applicability"] in {"MULTI_REGION", "WHOLE_SCREEN_OR_TRANSITION"} for row in subset
            )
            / len(subset)
            if subset
            else None,
        }

    return {
        "overall": summarize(rows),
        "by_dataset": {dataset: summarize([row for row in rows if row["dataset"] == dataset]) for dataset in sorted({row["dataset"] for row in rows})},
    }


def classifier_metrics_for_gold(items: list[dict[str, Any]]) -> dict[str, Any]:
    classifier = RequirementUnderstanding()
    pairs = [
        (str(item["ui_evaluability"]), classifier.classify_ui_evaluability(str(item["text"])).value)
        for item in items
    ]
    return classification_metrics(pairs)
