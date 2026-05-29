#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from json import JSONDecoder
from pathlib import Path
import shutil
import subprocess
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_VERIFICATION_GOLD_ROOT = BASE_DIR / "data" / "annotations" / "verification_gold"
DEFAULT_BACKUP_ROOT = BASE_DIR / "data" / "generated" / "verification_gold_recovery_backups"
DEFAULT_GIT_SPEC = "HEAD:requirement_claim_evidence_suggestions.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recover legacy reviewed claim/evidence annotations into verification_gold files."
    )
    parser.add_argument(
        "--legacy-file",
        type=Path,
        help="Path to a legacy JSON or JSON-stream file. If omitted, --git-spec is used.",
    )
    parser.add_argument(
        "--git-spec",
        default=DEFAULT_GIT_SPEC,
        help="Git object spec to read when --legacy-file is omitted.",
    )
    parser.add_argument(
        "--verification-gold-root",
        type=Path,
        default=DEFAULT_VERIFICATION_GOLD_ROOT,
        help="Root containing <flow_id>/verification_gold.json files.",
    )
    parser.add_argument(
        "--backup-root",
        type=Path,
        default=DEFAULT_BACKUP_ROOT,
        help="Root for backups of files before modification.",
    )
    parser.add_argument(
        "--flow-id",
        action="append",
        dest="flow_ids",
        help="Flow id to recover. Can be passed multiple times. Defaults to all matching flows.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing files.",
    )
    return parser.parse_args()


def _read_legacy_text(args: argparse.Namespace) -> str:
    if args.legacy_file is not None:
        return args.legacy_file.read_text(encoding="utf-8")
    result = subprocess.run(
        ["git", "show", args.git_spec],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def load_json_stream(text: str) -> list[dict[str, Any]]:
    decoder = JSONDecoder()
    pos = 0
    documents: list[dict[str, Any]] = []
    while pos < len(text):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos >= len(text):
            break
        document, pos = decoder.raw_decode(text, pos)
        if isinstance(document, list):
            documents.extend(item for item in document if isinstance(item, dict))
        elif isinstance(document, dict):
            documents.append(document)
    return documents


def _normalize_text(text: object) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _source_rank(legacy_item: dict[str, Any], current_item: dict[str, Any]) -> tuple[int, int, int]:
    source = str(legacy_item.get("source") or "")
    requirement_id = str(current_item.get("requirement_id") or "")
    current_text = _normalize_text(current_item.get("text"))
    legacy_text = _normalize_text(legacy_item.get("requirement_text") or legacy_item.get("text"))
    exact_text = 1 if current_text and current_text == legacy_text else 0

    if requirement_id.startswith("CONTR-"):
        source_score = 3 if source == "candidate" else 1 if source == "gold" else 0
    else:
        source_score = 3 if source == "gold" else 2 if source == "" else 1
    claim_count = len(legacy_item.get("claims") or [])
    return exact_text, source_score, claim_count


def _best_legacy_by_flow_and_id(documents: list[dict[str, Any]]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    indexed: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for document in documents:
        flow_id = document.get("flow_id")
        if not flow_id:
            continue
        for item in document.get("items", []):
            requirement_id = item.get("requirement_id")
            if requirement_id and item.get("claims"):
                indexed[str(flow_id)][str(requirement_id)].append(item)
    return indexed


def _claim_type_from_kind(claim_kind: str) -> str:
    return "HIDDEN" if claim_kind.startswith("HIDDEN") else "OBSERVABLE"


def _importance_from_kind(claim_kind: str) -> str:
    return "SUPPORTING" if claim_kind == "SUPPORTING_CONTEXT" else "CORE"


def _convert_claim(legacy_claim: dict[str, Any]) -> dict[str, Any]:
    claim_text = legacy_claim.get("claim") or legacy_claim.get("claim_text")
    claim_kind = str(legacy_claim.get("claim_kind") or "")
    return {
        "claim": claim_text,
        "status": legacy_claim.get("status") or "MISSING",
        "claim_type": legacy_claim.get("claim_type") or _claim_type_from_kind(claim_kind),
        "importance": legacy_claim.get("importance") or _importance_from_kind(claim_kind),
        "evidence_steps": list(legacy_claim.get("evidence_steps") or []),
        "note": legacy_claim.get("note"),
    }


def _has_richer_claims(legacy_item: dict[str, Any], current_item: dict[str, Any]) -> bool:
    legacy_claims = legacy_item.get("claims") or []
    current_claims = current_item.get("claims") or []
    if len(legacy_claims) > len(current_claims):
        return True
    legacy_supported = sum(1 for claim in legacy_claims if claim.get("status") not in {None, "MISSING"})
    current_supported = sum(1 for claim in current_claims if claim.get("status") not in {None, "MISSING"})
    if legacy_supported > current_supported:
        return True
    legacy_evidence = sum(len(claim.get("evidence_steps") or []) for claim in legacy_claims)
    current_evidence = sum(len(claim.get("evidence_steps") or []) for claim in current_claims)
    return legacy_evidence > current_evidence


def recover_file(
    path: Path,
    legacy_index: dict[str, dict[str, list[dict[str, Any]]]],
    *,
    dry_run: bool,
    backup_root: Path,
) -> tuple[int, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    flow_id = str(payload.get("flow_id") or path.parent.name)
    candidates_by_id = legacy_index.get(flow_id, {})
    changed_items = 0
    changed_claims = 0

    for item in payload.get("items", []):
        requirement_id = str(item.get("requirement_id") or "")
        candidates = candidates_by_id.get(requirement_id, [])
        if not candidates:
            continue
        legacy_item = max(candidates, key=lambda candidate: _source_rank(candidate, item))
        if not _has_richer_claims(legacy_item, item):
            continue

        item["claims"] = [_convert_claim(claim) for claim in legacy_item.get("claims", [])]
        for field in (
            "verification_label",
            "ui_evaluability",
            "uncertainty_reasons",
            "evidence_steps",
            "evidence_note",
            "rationale",
            "review_status",
        ):
            if field in legacy_item:
                item[field] = legacy_item[field]
        changed_items += 1
        changed_claims += len(item["claims"])

    if changed_items and not dry_run:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = backup_root / timestamp / flow_id / path.name
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return changed_items, changed_claims


def main() -> None:
    args = parse_args()
    documents = load_json_stream(_read_legacy_text(args))
    legacy_index = _best_legacy_by_flow_and_id(documents)
    flow_ids = args.flow_ids or sorted(legacy_index)

    total_items = 0
    total_claims = 0
    for flow_id in flow_ids:
        path = args.verification_gold_root / flow_id / "verification_gold.json"
        if not path.exists():
            continue
        changed_items, changed_claims = recover_file(
            path,
            legacy_index,
            dry_run=args.dry_run,
            backup_root=args.backup_root,
        )
        total_items += changed_items
        total_claims += changed_claims
        action = "Would recover" if args.dry_run else "Recovered"
        print(f"{action} {path}: {changed_items} items, {changed_claims} claims")

    print(f"Total: {total_items} items, {total_claims} claims")


if __name__ == "__main__":
    main()
