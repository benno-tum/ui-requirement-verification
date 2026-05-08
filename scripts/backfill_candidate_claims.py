#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ui_verifier.requirements.claim_decomposition import build_requirement_claims


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill atomic draft claims for candidate_requirements.json files."
    )
    parser.add_argument(
        "--candidate-root",
        type=Path,
        default=Path("data/generated/candidate_requirements"),
        help="Root containing <flow_id>/candidate_requirements.json files.",
    )
    parser.add_argument(
        "--flow-glob",
        default="pure_*",
        help="Glob for flow directories under candidate-root. Default targets PURE flows.",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Replace all existing claims. By default only missing or trivial copied claims are replaced.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing files.",
    )
    return parser.parse_args()


def _is_trivial_copied_claim(requirement: dict[str, Any]) -> bool:
    claims = requirement.get("claims")
    if not isinstance(claims, list) or len(claims) != 1:
        return False
    claim = claims[0]
    if not isinstance(claim, dict):
        return False
    claim_text = str(claim.get("claim_text") or claim.get("claim") or "").strip()
    requirement_text = str(requirement.get("text") or "").strip()
    if not claim_text or not requirement_text:
        return False
    if claim_text != requirement_text:
        return False
    return not claim.get("status") or claim.get("source") == "pure_requirement"


def _should_replace_claims(requirement: dict[str, Any], *, replace_existing: bool) -> bool:
    if replace_existing:
        return True
    claims = requirement.get("claims")
    if not isinstance(claims, list) or not claims:
        return True
    return _is_trivial_copied_claim(requirement)


def _backfill_file(path: Path, *, replace_existing: bool, dry_run: bool) -> tuple[int, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    requirements = payload.get("requirements", [])
    if not isinstance(requirements, list):
        return 0, 0

    updated = 0
    total_claims = 0
    for requirement in requirements:
        if not isinstance(requirement, dict):
            continue
        if not _should_replace_claims(requirement, replace_existing=replace_existing):
            continue

        requirement_id = str(requirement.get("requirement_id") or "").strip()
        text = str(requirement.get("text") or "").strip()
        if not requirement_id or not text:
            continue

        claims = build_requirement_claims(text, requirement_id, include_evidence_steps=True)
        requirement["claims"] = claims
        total_claims += len(claims)
        updated += 1

    if updated and not dry_run:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return updated, total_claims


def main() -> None:
    args = parse_args()
    candidate_paths = sorted(args.candidate_root.glob(f"{args.flow_glob}/candidate_requirements.json"))
    files_changed = 0
    requirements_changed = 0
    claims_written = 0

    for path in candidate_paths:
        updated, claim_count = _backfill_file(
            path,
            replace_existing=args.replace_existing,
            dry_run=args.dry_run,
        )
        if not updated:
            continue
        files_changed += 1
        requirements_changed += updated
        claims_written += claim_count
        action = "Would update" if args.dry_run else "Updated"
        print(f"{action} {path}: {updated} requirements, {claim_count} claims")

    mode = "would write" if args.dry_run else "wrote"
    print(
        f"Scanned {len(candidate_paths)} files; {mode} {claims_written} claims "
        f"for {requirements_changed} requirements in {files_changed} files."
    )


if __name__ == "__main__":
    main()
