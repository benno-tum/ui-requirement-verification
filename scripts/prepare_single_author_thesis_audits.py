from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ui_verifier.evaluation.review_audit import (  # noqa: E402
    claim_counts,
    load_verification_gold,
    structural_conflict_reasons,
)
from ui_verifier.verification_pipeline.requirement_understanding import (  # noqa: E402
    RequirementUnderstanding,
    find_hidden_indicators,
)

V7_AUDIT = (
    BASE_DIR
    / "data/annotations/evaluation_audits"
    / "gemini25flash_omnimark_v7_factcoverage_bbox_allflows_01_13_20260721"
)
V7_RUN = (
    BASE_DIR
    / "data/generated/verification_pipeline_runs"
    / "bbox_gemini25flash_omnimark_v7_factcoverage_allflows_01_13_20260721"
)
DEFAULT_OUTPUT = (
    BASE_DIR
    / "data/annotations/evaluation_audits"
    / "single_author_final_20260725"
)
SEED = 20260725


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare prediction-hidden single-author UI-evaluability and "
            "stratified V7 region-grounding audit forms."
        )
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--region-items-per-flow", type=int, default=4)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_key(value: str) -> str:
    return hashlib.sha256(f"{SEED}:{value}".encode()).hexdigest()


def screenshot_path(flow_id: str, step: int, dataset: str = "mind2web") -> str:
    dataset_root = BASE_DIR / "data/processed/flows" / dataset / flow_id
    preferred = dataset_root / "original" / f"step_{step:02d}.png"
    fallback = (
        dataset_root / f"step_{step:02d}.png"
    )
    path = preferred if preferred.exists() else fallback
    if not path.exists():
        raise FileNotFoundError(
            f"missing review screenshot for {dataset}:{flow_id}:step {step}"
        )
    return path.relative_to(BASE_DIR).as_posix()


def all_screenshot_paths(flow_id: str, dataset: str) -> list[str]:
    flow_root = BASE_DIR / "data/processed/flows" / dataset / flow_id
    preferred = flow_root / "original"
    root = preferred if preferred.is_dir() else flow_root
    paths = sorted(root.glob("step_*.png"))
    if not paths:
        raise FileNotFoundError(f"no review screenshots for {dataset}:{flow_id}")
    return [path.relative_to(BASE_DIR).as_posix() for path in paths]


def divergence_hypothesis(reference_label: str, pipeline_label: str) -> str:
    hypotheses = {
        (
            "PARTIALLY_UI_VERIFIABLE",
            "UI_VERIFIABLE",
        ): (
            "The deterministic classifier found no configured hidden-property "
            "indicator, while the author reference treats the requirement as "
            "containing both visible and non-visible obligations. Check whether "
            "the hidden meaning is implicit or the reference is too conservative."
        ),
        (
            "UI_VERIFIABLE",
            "PARTIALLY_UI_VERIFIABLE",
        ): (
            "The classifier detected both visible UI vocabulary and a configured "
            "hidden-property term. Check whether that term denotes an actually "
            "hidden effect or merely a visibly inspectable UI concept in context."
        ),
        (
            "UI_VERIFIABLE",
            "NOT_UI_VERIFIABLE",
        ): (
            "The classifier detected hidden-property vocabulary but no configured "
            "visible-UI indicator. Check whether the requirement nevertheless "
            "describes an observable UI state or interaction."
        ),
        (
            "NOT_UI_VERIFIABLE",
            "UI_VERIFIABLE",
        ): (
            "The classifier found no configured hidden-property indicator, while "
            "the reference considers the central obligation non-visible. Check "
            "for implicit backend, persistence, security, or external-effect meaning."
        ),
        (
            "PARTIALLY_UI_VERIFIABLE",
            "NOT_UI_VERIFIABLE",
        ): (
            "The classifier detected hidden-property vocabulary and no configured "
            "visible indicator, while the reference identifies a visible component. "
            "Check which UI affordance or state supplies that component."
        ),
        (
            "NOT_UI_VERIFIABLE",
            "PARTIALLY_UI_VERIFIABLE",
        ): (
            "The classifier detected both visible and hidden vocabulary, while the "
            "reference treats the visible portion as insufficient or non-central. "
            "Check whether the visible component is independently verifiable."
        ),
    }
    return hypotheses.get(
        (reference_label, pipeline_label),
        "The operational rules assign different UI-evaluability labels; inspect the requirement semantics and visible evidence boundary.",
    )


def build_ui_form() -> dict[str, Any]:
    gold_items = load_verification_gold(
        BASE_DIR / "data/annotations/verification_gold"
    )
    classifier = RequirementUnderstanding()
    items = []
    disagreements: list[tuple[dict[str, Any], str]] = []
    for item in gold_items:
        pipeline_label = classifier.classify_ui_evaluability(
            str(item["text"])
        ).value
        if str(item["ui_evaluability"]) != pipeline_label:
            disagreements.append((item, pipeline_label))
    disagreements.sort(
        key=lambda pair: (
            str(pair[0]["ui_evaluability"]),
            pair[1],
            stable_key(f"{pair[0]['flow_id']}:{pair[0]['requirement_id']}"),
        )
    )
    for index, (item, pipeline_label) in enumerate(disagreements, start=1):
        steps = [
            int(step)
            for step in (item.get("step_indices") or item.get("evidence_steps") or [])
        ]
        dataset = str(item["dataset"])
        flow_id = str(item["flow_id"])
        screenshots = (
            [
                screenshot_path(flow_id, step, dataset)
                for step in steps
            ]
            if steps
            else all_screenshot_paths(flow_id, dataset)
        )
        observable_claims, hidden_claims = claim_counts(item)
        reference_label = str(item["ui_evaluability"])
        pipeline_value = classifier.classify_ui_evaluability(str(item["text"]))
        pipeline_rationale = classifier._rationale(  # noqa: SLF001
            pipeline_value,
            str(item["text"]),
        )
        items.append(
            {
                "audit_item_id": f"UID-{index:03d}",
                "flow_id": flow_id,
                "dataset": dataset,
                "requirement_id": str(item["requirement_id"]),
                "requirement_text": str(item["text"]),
                "step_indices": steps,
                "ordered_screenshots": screenshots,
                "reference_label": reference_label,
                "pipeline_label": pipeline_label,
                "pipeline_rationale": pipeline_rationale,
                "detected_hidden_indicators": find_hidden_indicators(
                    str(item["text"])
                ),
                "reference_basis": {
                    "observable_claim_count": observable_claims,
                    "hidden_claim_count": hidden_claims,
                    "structural_conflict_reasons": structural_conflict_reasons(item),
                    "original_annotation_notes": str(
                        item.get("annotation_notes") or ""
                    ),
                },
                "divergence_hypothesis": divergence_hypothesis(
                    reference_label,
                    pipeline_label,
                ),
                "author_resolution": None,
                "author_final_label": None,
                "author_confidence": None,
                "author_rationale": "",
                "author_amendment_recommended": None,
                "author_note": "",
            }
        )
    return {
        "schema_version": "single_author_ui_disagreement_audit_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "blind": False,
        "reference_fields_included": True,
        "pipeline_labels_included": True,
        "scope": {
            "source_item_count": len(gold_items),
            "disagreement_item_count": len(items),
            "datasets": ["mind2web", "pure"],
            "selection": "Every accepted item whose author reference label differs from the deterministic classifier label.",
        },
        "instructions": {
            "purpose": (
                "Targeted qualitative audit of every author-reference versus "
                "deterministic-classifier disagreement. This is not a random "
                "sample, accuracy estimate, or independent validation."
            ),
            "resolutions": [
                "KEEP_REFERENCE",
                "ADOPT_PIPELINE",
                "CHOOSE_DIFFERENT_LABEL",
                "REQUIREMENT_AMBIGUOUS",
            ],
            "required_fields": [
                "author_resolution",
                "author_final_label",
                "author_amendment_recommended",
            ],
        },
        "items": items,
    }


def region_groups() -> list[dict[str, Any]]:
    manifest = load_json(V7_AUDIT / "bbox_manifest.json")
    reference = load_json(V7_AUDIT / "bbox_reference.json")
    grouped: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for item in manifest["items"]:
        ref = reference["items"][item["audit_item_id"]]
        key = (
            str(item["flow_id"]),
            str(item["requirement_id"]),
            str(item["claim_id"]),
            int(item["step_index"]),
        )
        group = grouped.setdefault(
            key,
            {
                "flow_id": key[0],
                "requirement_id": key[1],
                "claim_id": key[2],
                "step_index": key[3],
                "requirement_text": item["requirement_text"],
                "claim_text": item["claim_text"],
                "image_path": item["image_path"],
                "image_width": item["image_width"],
                "image_height": item["image_height"],
                "image_sha256": item["image_sha256"],
                "claim_status": ref.get("claim_status"),
                "regions": [],
            },
        )
        prediction = ref.get("prediction") or {}
        group["regions"].append(
            {
                "audit_item_id": item["audit_item_id"],
                "bbox": prediction.get("bbox"),
                "source": prediction.get("source"),
                "description": prediction.get("description"),
                "candidate_id": prediction.get("candidate_id"),
            }
        )
    return list(grouped.values())


def select_region_groups(per_flow: int) -> list[dict[str, Any]]:
    by_flow: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for group in region_groups():
        group["selection_features"] = {
            "claim_status": group.get("claim_status"),
            "region_count": len(group["regions"]),
            "sources": sorted(
                {
                    str(region.get("source"))
                    for region in group["regions"]
                    if region.get("source")
                }
            ),
        }
        by_flow[group["flow_id"]].append(group)

    selected: list[dict[str, Any]] = []
    for flow_id in sorted(by_flow):
        candidates = sorted(
            by_flow[flow_id],
            key=lambda item: stable_key(
                f"{flow_id}:{item['requirement_id']}:{item['claim_id']}:{item['step_index']}"
            ),
        )
        chosen: list[dict[str, Any]] = []
        covered: set[str] = set()
        while candidates and len(chosen) < per_flow:
            def score(item: dict[str, Any]) -> tuple[int, str]:
                features = {
                    f"status:{item['selection_features']['claim_status']}",
                    f"count:{min(item['selection_features']['region_count'], 2)}",
                    *{
                        f"source:{source}"
                        for source in item["selection_features"]["sources"]
                    },
                }
                gain = len(features - covered)
                identity = (
                    f"{flow_id}:{item['requirement_id']}:"
                    f"{item['claim_id']}:{item['step_index']}"
                )
                return gain, stable_key(identity)

            best = max(candidates, key=score)
            candidates.remove(best)
            chosen.append(best)
            covered.update(
                {
                    f"status:{best['selection_features']['claim_status']}",
                    f"count:{min(best['selection_features']['region_count'], 2)}",
                    *{
                        f"source:{source}"
                        for source in best["selection_features"]["sources"]
                    },
                }
            )
        selected.extend(chosen)
    return selected


def no_visible_region_claims() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(V7_RUN.glob("[0-1][0-9]_*.json")):
        payload = load_json(path)
        flow_id = str(payload["flow_id"])
        for result in payload["results"]:
            for claim in result["claims"]:
                if claim.get("status") in {"MISSING", "HIDDEN"} or claim.get("evidence"):
                    continue
                steps = [
                    int(step)
                    for step in claim.get("metadata", {}).get(
                        "claim_selected_step_indices", []
                    )
                ]
                items.append(
                    {
                        "flow_id": flow_id,
                        "requirement_id": result["requirement_id"],
                        "claim_id": claim["claim_id"],
                        "requirement_text": result["requirement_text"],
                        "claim_text": claim["claim_text"],
                        "claim_status": claim["status"],
                        "selected_step_indices": steps,
                        "ordered_screenshots": [
                            screenshot_path(flow_id, step) for step in steps
                        ],
                        "regions": [],
                        "selection_features": {
                            "explicit_no_visible_region": True,
                        },
                    }
                )
    return items


def blank_region_fields(item: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "reaudit_item_id": f"V7AR-{index:03d}",
        **item,
        "author_applicability": None,
        "author_candidate_exists": None,
        "author_geometric_validity": None,
        "author_semantic_relevance": None,
        "author_evidential_sufficiency": None,
        "author_missing_facts": [],
        "author_error_categories": [],
        "author_localization_abstention_appropriate": None,
        "author_confidence": None,
        "author_note": "",
    }


def build_region_form(per_flow: int) -> dict[str, Any]:
    selected = select_region_groups(per_flow)
    selected.extend(no_visible_region_claims())
    items = [blank_region_fields(item, index) for index, item in enumerate(selected, 1)]
    return {
        "schema_version": "single_author_v7_region_audit_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "sampling": {
            "region_groups_per_flow": per_flow,
            "flow_count": 13,
            "explicit_nonmissing_no_visible_region_claims": 8,
            "sample_size": len(items),
            "method": (
                "Deterministic within-flow diversity sampling over claim status, "
                "region count, and region source, plus every non-missing claim "
                "with no returned region."
            ),
        },
        "limitations": (
            "Author-conducted quality audit; not independent localization "
            "validation. Source outputs were generated before this form."
        ),
        "items": items,
    }


def write_once(path: Path, payload: dict[str, Any], force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists; pass --force to replace it")
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    if args.region_items_per_flow < 1:
        raise ValueError("--region-items-per-flow must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    ui_path = args.output_dir / "ui_evaluability_disagreement_audit_form.json"
    region_path = args.output_dir / "v7_region_author_audit_form.json"
    write_once(ui_path, build_ui_form(), args.force)
    write_once(
        region_path,
        build_region_form(args.region_items_per_flow),
        args.force,
    )
    print(f"ui_form={ui_path}")
    print(f"region_form={region_path}")


if __name__ == "__main__":
    main()
