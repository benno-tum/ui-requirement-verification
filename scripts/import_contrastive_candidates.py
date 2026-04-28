from __future__ import annotations

import argparse
from pathlib import Path

from ui_verifier.requirements.contrastive_import import (
    DEFAULT_CANDIDATE_ROOT,
    DEFAULT_DUPLICATES_PATH,
    DEFAULT_FLOW_CATALOG_PATH,
    DEFAULT_FLOW_ROOT,
    DEFAULT_GOLD_ROOT,
    DEFAULT_IMPORT_ROOT,
    DEFAULT_MATCH_MANIFEST_PATH,
    DEFAULT_PARSED_BLOCKS_PATH,
    DEFAULT_RAW_PATH,
    DEFAULT_REPORT_PATH,
    DEFAULT_STAGED_ROOT,
    DEFAULT_UNMATCHED_PATH,
    build_duplicates_payload,
    build_flow_catalog,
    build_import_report,
    build_unmatched_expected_flows,
    create_match_manifest,
    parse_concatenated_json_blocks,
    stage_matched_outputs,
    write_json,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-path", type=Path, default=DEFAULT_RAW_PATH)
    parser.add_argument("--import-root", type=Path, default=DEFAULT_IMPORT_ROOT)
    parser.add_argument("--flow-root", type=Path, default=DEFAULT_FLOW_ROOT)
    parser.add_argument("--gold-root", type=Path, default=DEFAULT_GOLD_ROOT)
    parser.add_argument("--candidate-root", type=Path, default=DEFAULT_CANDIDATE_ROOT)
    args = parser.parse_args()

    raw_text = args.raw_path.read_text(encoding="utf-8")
    blocks = parse_concatenated_json_blocks(raw_text)

    parsed_blocks_path = args.import_root / DEFAULT_PARSED_BLOCKS_PATH.name
    flow_catalog_path = args.import_root / DEFAULT_FLOW_CATALOG_PATH.name
    match_manifest_path = args.import_root / DEFAULT_MATCH_MANIFEST_PATH.name
    duplicates_path = args.import_root / DEFAULT_DUPLICATES_PATH.name
    unmatched_path = args.import_root / DEFAULT_UNMATCHED_PATH.name
    report_path = args.import_root / DEFAULT_REPORT_PATH.name
    staged_root = args.import_root / DEFAULT_STAGED_ROOT.name

    write_json(parsed_blocks_path, [block.to_dict() for block in blocks])

    catalog = build_flow_catalog(
        flow_root=args.flow_root,
        gold_root=args.gold_root,
        candidate_root=args.candidate_root,
    )
    write_json(
        flow_catalog_path,
        [
            {
                key: value
                for key, value in entry.items()
                if not key.startswith("_")
            }
            for entry in catalog
        ],
    )

    manifest = create_match_manifest(blocks, catalog)
    write_json(match_manifest_path, manifest)

    duplicates = build_duplicates_payload(blocks, manifest)
    write_json(duplicates_path, duplicates)

    stage_matched_outputs(blocks, manifest, staged_root=staged_root)

    unmatched_expected_flows = build_unmatched_expected_flows(catalog, manifest)
    write_json(unmatched_path, unmatched_expected_flows)

    report = build_import_report(
        blocks=blocks,
        manifest=manifest,
        duplicates=duplicates,
        unmatched_expected_flows=unmatched_expected_flows,
    )
    report_path.write_text(report, encoding="utf-8")

    matched = sum(1 for entry in manifest if entry.get("status") == "matched")
    ambiguous = sum(1 for entry in manifest if entry.get("status") == "ambiguous")
    duplicate_count = sum(1 for entry in manifest if entry.get("status") == "duplicate")
    unmatched = sum(1 for entry in manifest if entry.get("status") == "unmatched")

    print(
        f"Parsed {len(blocks)} blocks | matched {matched} unique flows | "
        f"duplicates {duplicate_count} | ambiguous {ambiguous} | unmatched {unmatched}"
    )
    print(f"Wrote parsed blocks to {parsed_blocks_path}")
    print(f"Wrote flow catalog to {flow_catalog_path}")
    print(f"Wrote match manifest to {match_manifest_path}")
    print(f"Wrote duplicates report to {duplicates_path}")
    print(f"Wrote unmatched expected flows to {unmatched_path}")
    print(f"Wrote review report to {report_path}")
    print(f"Staged matched outputs under {staged_root}")


if __name__ == "__main__":
    main()
