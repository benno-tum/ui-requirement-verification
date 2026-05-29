#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from ui_verifier.annotation.service import AnnotationService
from ui_verifier.annotation.storage import AnnotationStorage
from ui_verifier.requirements.claim_decomposition import build_requirement_claims
from ui_verifier.verification.schemas import ClaimEvidence, VerificationGoldFile, VerificationGoldItem


DEFAULT_GOLD_ROOT = Path("data/annotations/requirements_gold")


@dataclass(frozen=True)
class BackfillSummary:
    flow_id: str
    item_count: int
    items_updated: int
    claims_written: int
    path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize verification_gold files and add draft atomic claim suggestions "
            "for review items that do not have claims yet."
        )
    )
    parser.add_argument(
        "--flow-id",
        action="append",
        dest="flow_ids",
        help="Flow id to backfill. Can be passed multiple times. Defaults to all versioned gold flows.",
    )
    parser.add_argument(
        "--gold-root",
        type=Path,
        default=DEFAULT_GOLD_ROOT,
        help="Root containing <flow_id>/gold_requirements.json files.",
    )
    parser.add_argument(
        "--exclude-candidates",
        action="store_true",
        help="Only include accepted gold requirements when materializing verification_gold files.",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Replace existing claims. By default only items with no claims are changed.",
    )
    parser.add_argument(
        "--replace-trivial-copied",
        action="store_true",
        help="Replace single-claim suggestions that are exact copies of the requirement text.",
    )
    parser.add_argument(
        "--max-claims",
        type=int,
        default=8,
        help="Maximum number of draft claims to generate per requirement.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing files.",
    )
    return parser.parse_args()


def discover_gold_flow_ids(gold_root: Path) -> list[str]:
    if not gold_root.exists():
        return []
    return [
        path.name
        for path in sorted(gold_root.iterdir())
        if path.is_dir() and (path / "gold_requirements.json").exists()
    ]


def _should_backfill(item: VerificationGoldItem, *, replace_existing: bool) -> bool:
    return replace_existing or not item.claims


def _normalized_text_for_copy_check(text: str) -> str:
    return " ".join(text.strip().rstrip(".!?").lower().split())


def _has_single_copied_claim(item: VerificationGoldItem) -> bool:
    if len(item.claims) != 1:
        return False
    return _normalized_text_for_copy_check(item.claims[0].claim) == _normalized_text_for_copy_check(item.text)


def _draft_claims(item: VerificationGoldItem, *, max_claims: int) -> list[ClaimEvidence]:
    raw_claims = build_requirement_claims(
        item.text,
        item.requirement_id,
        max_claims=max_claims,
        include_evidence_steps=True,
    )
    return [ClaimEvidence.from_dict(claim) for claim in raw_claims]


def backfill_verification_claim_suggestions(
    service: AnnotationService,
    flow_id: str,
    *,
    include_candidates: bool = True,
    replace_existing: bool = False,
    replace_trivial_copied: bool = False,
    max_claims: int = 8,
    dry_run: bool = False,
) -> BackfillSummary:
    verification_gold_file = service.build_verification_gold_file(
        flow_id,
        include_candidates=include_candidates,
    )

    items_updated = 0
    claims_written = 0
    for item in verification_gold_file.items:
        should_replace_copied = replace_trivial_copied and _has_single_copied_claim(item)
        if not should_replace_copied and not _should_backfill(item, replace_existing=replace_existing):
            continue
        item.claims = _draft_claims(item, max_claims=max_claims)
        item.review_status = "needs_review"
        item.__post_init__()
        items_updated += 1
        claims_written += len(item.claims)

    path = service.storage.verification_gold_file_path(flow_id)
    if not dry_run and (items_updated or not path.exists()):
        service.storage.save_verification_gold_file(verification_gold_file)

    return BackfillSummary(
        flow_id=flow_id,
        item_count=len(verification_gold_file.items),
        items_updated=items_updated,
        claims_written=claims_written,
        path=path,
    )


def main() -> None:
    args = parse_args()
    flow_ids = args.flow_ids or discover_gold_flow_ids(args.gold_root)
    storage = AnnotationStorage(gold_root=args.gold_root)
    service = AnnotationService(storage=storage)

    total_items_updated = 0
    total_claims_written = 0
    for flow_id in flow_ids:
        summary = backfill_verification_claim_suggestions(
            service,
            flow_id,
            include_candidates=not args.exclude_candidates,
            replace_existing=args.replace_existing,
            replace_trivial_copied=args.replace_trivial_copied,
            max_claims=args.max_claims,
            dry_run=args.dry_run,
        )
        total_items_updated += summary.items_updated
        total_claims_written += summary.claims_written
        action = "Would update" if args.dry_run else "Updated"
        print(
            f"{action} {summary.path}: "
            f"{summary.items_updated}/{summary.item_count} items, {summary.claims_written} claims"
        )

    mode = "would write" if args.dry_run else "wrote"
    print(
        f"Scanned {len(flow_ids)} flows; {mode} {total_claims_written} claims "
        f"for {total_items_updated} verification items."
    )


if __name__ == "__main__":
    main()
