#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$REPO_ROOT/data/annotations/flow_manifests/mind2web_repo_dataset_annotation_ids.txt"

python "$REPO_ROOT/scripts/export_mind2web.py" \
  --split test_task \
  --max-flows 0 \
  --allowed-flows-file "$MANIFEST"
