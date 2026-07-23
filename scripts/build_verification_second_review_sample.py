from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
LABELS = (
    "FULFILLED",
    "PARTIALLY_FULFILLED",
    "ABSTAIN",
    "NOT_FULFILLED",
)
DEFAULT_QUOTAS = {
    "FULFILLED": 12,
    "PARTIALLY_FULFILLED": 12,
    "ABSTAIN": 12,
    "NOT_FULFILLED": 8,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic, label-stratified, blinded second-review form "
            "for the frozen Mind2Web verification benchmark."
        )
    )
    parser.add_argument(
        "--gold-root",
        type=Path,
        default=BASE_DIR / "data/annotations/verification_gold",
    )
    parser.add_argument(
        "--flows-root",
        type=Path,
        default=BASE_DIR / "data/processed/flows/mind2web",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=BASE_DIR
        / "data/annotations/evaluation_audits/"
        "verification_label_second_review_20260723/second_review_form.json",
    )
    parser.add_argument("--seed", default="thesis-second-review-v1")
    return parser.parse_args()


def _load_gold(gold_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(gold_root.glob("[0-9][0-9]_*/verification_gold.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        flow_id = str(payload["flow_id"])
        for item in payload["items"]:
            label = str(item["verification_label"]).upper()
            if label not in LABELS:
                raise ValueError(
                    f"{flow_id}/{item.get('requirement_id')}: invalid label {label}"
                )
            records.append(
                {
                    "flow_id": flow_id,
                    "requirement_id": str(item["requirement_id"]),
                    "requirement_text": str(item["text"]),
                    "requirement_type": item.get("requirement_type"),
                    "scope": item.get("scope"),
                    "_gold_label": label,
                }
            )
    if len(records) != 258:
        raise ValueError(f"expected 258 frozen records, found {len(records)}")
    return records


def _rank(record: dict[str, Any], seed: str) -> str:
    material = (
        f"{seed}\0{record['flow_id']}\0{record['requirement_id']}"
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _select(
    records: list[dict[str, Any]],
    *,
    seed: str,
    quotas: dict[str, int],
) -> list[dict[str, Any]]:
    ranked = sorted(records, key=lambda item: _rank(item, seed))
    selected: list[dict[str, Any]] = []
    selected_keys: set[tuple[str, str]] = set()
    remaining = dict(quotas)

    def add(item: dict[str, Any]) -> None:
        key = (item["flow_id"], item["requirement_id"])
        if key in selected_keys:
            return
        label = item["_gold_label"]
        if remaining[label] <= 0:
            return
        selected.append(item)
        selected_keys.add(key)
        remaining[label] -= 1

    # Include every item in the rarest class.
    for item in ranked:
        if item["_gold_label"] == "NOT_FULFILLED":
            add(item)

    # Ensure that every flow is represented while preserving label quotas.
    represented = {item["flow_id"] for item in selected}
    for flow_id in sorted({item["flow_id"] for item in records} - represented):
        candidates = [
            item
            for item in ranked
            if item["flow_id"] == flow_id
            and remaining[item["_gold_label"]] > 0
            and (item["flow_id"], item["requirement_id"]) not in selected_keys
        ]
        if not candidates:
            raise ValueError(f"cannot cover flow {flow_id} within the label quotas")
        add(candidates[0])

    for label in LABELS:
        for item in ranked:
            if remaining[label] == 0:
                break
            if item["_gold_label"] == label:
                add(item)
        if remaining[label] != 0:
            raise ValueError(f"not enough records to fill quota for {label}")

    return sorted(
        selected,
        key=lambda item: (item["flow_id"], item["requirement_id"]),
    )


def _relative_screenshots(flows_root: Path, flow_id: str) -> list[str]:
    paths = sorted((flows_root / flow_id / "original").glob("step_*.png"))
    if not paths:
        raise FileNotFoundError(f"no ordered screenshots found for {flow_id}")
    return [str(path.relative_to(BASE_DIR)) for path in paths]


def build_review_form(
    *,
    gold_root: Path,
    flows_root: Path,
    seed: str,
) -> tuple[dict[str, Any], dict[str, int]]:
    records = _load_gold(gold_root)
    selected = _select(records, seed=seed, quotas=DEFAULT_QUOTAS)
    hidden_distribution = {
        label: sum(item["_gold_label"] == label for item in selected)
        for label in LABELS
    }
    items = []
    for index, item in enumerate(selected, start=1):
        items.append(
            {
                "audit_item_id": f"VSR-{index:03d}",
                "flow_id": item["flow_id"],
                "requirement_id": item["requirement_id"],
                "requirement_text": item["requirement_text"],
                "requirement_type": item["requirement_type"],
                "scope": item["scope"],
                "ordered_screenshots": _relative_screenshots(
                    flows_root, item["flow_id"]
                ),
                "reviewer_label": None,
                "reviewer_evidence_steps": [],
                "reviewer_confidence": None,
                "reviewer_notes": "",
            }
        )
    return (
        {
            "schema_version": "verification_second_review_v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "benchmark": {
                "dataset": "Mind2Web-derived reviewed verification benchmark",
                "flow_count": 13,
                "item_count": 258,
            },
            "sampling": {
                "seed": seed,
                "method": (
                    "Deterministic label-stratified sample with every rare "
                    "NOT_FULFILLED item and at least one item from every flow. "
                    "Per-item primary labels and model predictions are withheld."
                ),
                "sample_size": len(items),
            },
            "label_definitions": {
                "FULFILLED": (
                    "All core UI-observable claims are visibly supported by the "
                    "ordered screenshot flow."
                ),
                "PARTIALLY_FULFILLED": (
                    "A material observable part is supported, but at least one "
                    "core observable part is unsupported or unresolved."
                ),
                "NOT_FULFILLED": (
                    "The ordered screenshot flow visibly contradicts at least one "
                    "core observable claim."
                ),
                "ABSTAIN": (
                    "The screenshots do not provide enough visible evidence for a "
                    "safe positive, partial, or contradictory decision."
                ),
            },
            "review_instructions": [
                "Review items independently and in audit_item_id order.",
                "Do not inspect primary-author labels or model predictions.",
                "Use only UI-observable evidence in the supplied ordered screenshots.",
                "Do not infer backend correctness, persistence, security, completeness, or external effects.",
                "Record all decisive screenshot step numbers.",
                "Set reviewer_confidence to LOW, MEDIUM, or HIGH.",
            ],
            "reviewer": {
                "reviewer_id": "",
                "review_started_at": None,
                "review_completed_at": None,
            },
            "items": items,
        },
        hidden_distribution,
    )


def main() -> None:
    args = parse_args()
    payload, distribution = build_review_form(
        gold_root=args.gold_root,
        flows_root=args.flows_root,
        seed=args.seed,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"out={args.out} sample={len(payload['items'])} "
        f"flows={len({item['flow_id'] for item in payload['items']})} "
        f"hidden_distribution={distribution}"
    )


if __name__ == "__main__":
    main()
