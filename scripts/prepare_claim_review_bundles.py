#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from ui_verifier.common.flow_utils import find_step_images, parse_step_number


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_VERIFICATION_GOLD_ROOT = BASE_DIR / "data" / "annotations" / "verification_gold"
DEFAULT_FLOWS_ROOT = BASE_DIR / "data" / "processed" / "flows" / "mind2web"
DEFAULT_OUTPUT_ROOT = BASE_DIR / "data" / "generated" / "claim_review_bundles"


CLAIM_REVIEW_PROMPT = """# Claim-Level UI Verification Review

You are reviewing requirement claims against an ordered UI screenshot flow.

## Input

The ZIP contains:

- `claim_review_input.json`: requirements and draft claims to review.
- `images/step_XX.png`: ordered screenshots for the flow.
- `task.json`: task metadata when available.

Use only the screenshots and the requirement text. Do not assume backend state, persistence,
email delivery, payment processing, security, ranking correctness, or future visits unless the
visible UI directly supports it.

## What to Review

For each requirement and claim:

1. Decide whether the claim text is a good atomic decomposition of the requirement.
2. If the claim is too broad, duplicated, evidence-specific, or not actually implied by the requirement,
   provide a replacement claim in `suggested_claim_text`.
3. Assign claim metadata:
   - `status`: `SUPPORTED`, `CONTRADICTED`, `MISSING`, `HIDDEN`, `AMBIGUOUS`, or `OUT_OF_SCOPE`
   - `claim_type`: `OBSERVABLE` or `HIDDEN`
   - `importance`: `CORE` or `SUPPORTING`
   - `evidence_steps`: step indices that support or contradict observable claims
   - `note`: short reason grounded in visible evidence or explaining why evidence is missing/hidden

## Label Discipline

- `SUPPORTED`: visible evidence in the screenshots supports the claim.
- `CONTRADICTED`: visible evidence contradicts the claim. Missing evidence alone is not contradiction.
- `MISSING`: the claim could be visible, but the flow does not show enough evidence.
- `HIDDEN`: the claim depends on non-visible state or behavior.
- `AMBIGUOUS`: visible evidence exists, but its meaning is unclear.
- `OUT_OF_SCOPE`: the claim is a routine internal/system effect outside screenshot verification.

Observable `SUPPORTED` or `CONTRADICTED` claims must include at least one `evidence_steps` value.
Hidden claims usually should not cite screenshot evidence unless the screenshot shows a visible proxy.

## Output

Return JSON only. Do not use Markdown fences.

The output must have this shape:

{
  "flow_id": "<flow id>",
  "items": [
    {
      "requirement_id": "<id>",
      "claim_reviews": [
        {
          "claim_id": "<claim id or null>",
          "claim_text": "<original claim text>",
          "suggested_claim_text": "<replacement claim text or null>",
          "status": "SUPPORTED|CONTRADICTED|MISSING|HIDDEN|AMBIGUOUS|OUT_OF_SCOPE",
          "claim_type": "OBSERVABLE|HIDDEN",
          "importance": "CORE|SUPPORTING",
          "evidence_steps": [1, 2],
          "note": "<short evidence-grounded review note>"
        }
      ],
      "item_note": "<optional note about requirement-level ambiguity or claim decomposition>"
    }
  ]
}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create per-flow ZIP bundles for model-assisted claim-level review."
    )
    parser.add_argument(
        "--flow-id",
        action="append",
        dest="flow_ids",
        help="Flow id to export. Can be passed multiple times. Defaults to flows 01-13 found in verification_gold.",
    )
    parser.add_argument(
        "--verification-gold-root",
        type=Path,
        default=DEFAULT_VERIFICATION_GOLD_ROOT,
        help="Root containing <flow_id>/verification_gold.json files.",
    )
    parser.add_argument(
        "--flows-root",
        type=Path,
        default=DEFAULT_FLOWS_ROOT,
        help="Root containing local Mind2Web flow directories.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Directory where bundles and zips are written.",
    )
    parser.add_argument(
        "--include-all-needs-review",
        action="store_true",
        help="Include all needs_review items, even if their claims already look complete.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report selected cases without writing bundles.",
    )
    return parser.parse_args()


def discover_repo_flow_ids(verification_gold_root: Path) -> list[str]:
    return [
        path.parent.name
        for path in sorted(verification_gold_root.glob("*/verification_gold.json"))
        if path.parent.name[:2].isdigit() and 1 <= int(path.parent.name[:2]) <= 13
    ]


def _claim_review_flags(claim: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    status = claim.get("status")
    claim_type = claim.get("claim_type")
    importance = claim.get("importance")
    evidence_steps = claim.get("evidence_steps") or []
    note = str(claim.get("note") or "").strip()

    if not status or status == "MISSING":
        flags.append("placeholder_status")
    if not claim_type:
        flags.append("missing_claim_type")
    if not importance:
        flags.append("missing_importance")
    if claim_type == "OBSERVABLE" and status in {"SUPPORTED", "CONTRADICTED"} and not evidence_steps:
        flags.append("missing_evidence_steps")
    if status in {"SUPPORTED", "CONTRADICTED"} and not evidence_steps:
        flags.append("decision_without_evidence")
    if not note:
        flags.append("missing_note")
    return flags


def item_needs_claim_review(item: dict[str, Any], *, include_all_needs_review: bool = False) -> tuple[bool, list[str]]:
    if item.get("review_status") != "needs_review":
        return False, []
    if include_all_needs_review:
        return True, ["needs_review"]

    claims = item.get("claims") or []
    flags: list[str] = []
    if not claims:
        flags.append("missing_claims")
    for claim in claims:
        flags.extend(_claim_review_flags(claim))
    return bool(flags), sorted(set(flags))


def _review_claim_payload(claim: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "claim_id": claim.get("claim_id") or f"claim-{index}",
        "claim_text": claim.get("claim_text") or claim.get("claim"),
        "current_status": claim.get("status"),
        "current_claim_type": claim.get("claim_type"),
        "current_importance": claim.get("importance"),
        "current_evidence_steps": claim.get("evidence_steps", []),
        "current_note": claim.get("note"),
    }


def build_review_input(
    verification_gold_file: Path,
    flow_dir: Path,
    *,
    include_all_needs_review: bool = False,
) -> tuple[dict[str, Any], Counter[str]]:
    data = json.loads(verification_gold_file.read_text(encoding="utf-8"))
    step_paths = find_step_images(flow_dir)
    step_indices = [parse_step_number(path) for path in step_paths]
    task_path = flow_dir / "task.json"
    task = json.loads(task_path.read_text(encoding="utf-8")) if task_path.exists() else None

    counts: Counter[str] = Counter()
    review_items: list[dict[str, Any]] = []
    for item in data.get("items", []):
        include, flags = item_needs_claim_review(item, include_all_needs_review=include_all_needs_review)
        if not include:
            continue

        counts["items"] += 1
        for flag in flags:
            counts[flag] += 1
        claims = item.get("claims") or []
        counts["claims"] += len(claims)
        review_items.append(
            {
                "requirement_id": item.get("requirement_id"),
                "source_type": item.get("source_type"),
                "requirement_text": item.get("text"),
                "requirement_type": item.get("requirement_type"),
                "ui_evaluability": item.get("ui_evaluability"),
                "verification_label": item.get("verification_label"),
                "requirement_evidence_steps": item.get("evidence_steps", []),
                "requirement_rationale": item.get("rationale"),
                "review_flags": flags,
                "claims": [_review_claim_payload(claim, idx) for idx, claim in enumerate(claims, start=1)],
            }
        )

    payload = {
        "dataset": data.get("dataset", "mind2web"),
        "flow_id": data["flow_id"],
        "task": task,
        "available_steps": [
            {
                "step_index": parse_step_number(path),
                "image": f"images/{path.name}",
            }
            for path in step_paths
        ],
        "step_indices": step_indices,
        "items": review_items,
    }
    return payload, counts


def write_bundle(flow_id: str, payload: dict[str, Any], flow_dir: Path, output_root: Path) -> Path:
    bundle_dir = output_root / flow_id
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    images_dir = bundle_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    (bundle_dir / "prompt.md").write_text(CLAIM_REVIEW_PROMPT, encoding="utf-8")
    (bundle_dir / "claim_review_input.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    task_path = flow_dir / "task.json"
    if task_path.exists():
        shutil.copy2(task_path, bundle_dir / "task.json")
    for step_path in find_step_images(flow_dir):
        shutil.copy2(step_path, images_dir / step_path.name)

    zip_path = output_root / f"{flow_id}_claim_review_bundle.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(bundle_dir.rglob("*")):
            archive.write(path, path.relative_to(bundle_dir.parent))
    return zip_path


def main() -> None:
    args = parse_args()
    flow_ids = args.flow_ids or discover_repo_flow_ids(args.verification_gold_root)
    total = Counter()

    if not args.dry_run:
        args.output_root.mkdir(parents=True, exist_ok=True)
        (args.output_root / "generic_claim_review_prompt.md").write_text(CLAIM_REVIEW_PROMPT, encoding="utf-8")

    for flow_id in flow_ids:
        verification_gold_file = args.verification_gold_root / flow_id / "verification_gold.json"
        flow_dir = args.flows_root / flow_id
        if not verification_gold_file.exists():
            raise FileNotFoundError(f"Verification gold file not found: {verification_gold_file}")
        if not flow_dir.exists():
            raise FileNotFoundError(f"Flow directory not found: {flow_dir}")

        payload, counts = build_review_input(
            verification_gold_file,
            flow_dir,
            include_all_needs_review=args.include_all_needs_review,
        )
        total.update(counts)
        if args.dry_run:
            print(f"{flow_id}: {counts['items']} items, {counts['claims']} claims, flags={dict(counts)}")
            continue

        zip_path = write_bundle(flow_id, payload, flow_dir, args.output_root)
        print(f"Wrote {zip_path}: {counts['items']} items, {counts['claims']} claims")

    print(f"Total selected: {total['items']} items, {total['claims']} claims")


if __name__ == "__main__":
    main()
