#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$(pwd)}"
SRC_DIR="$REPO_ROOT/data/processed/flows/mind2web"
DST_DIR="$REPO_ROOT/data/generated/candidate_requirements"

if [[ ! -d "$SRC_DIR" ]]; then
  echo "Fehler: Quellordner nicht gefunden: $SRC_DIR" >&2
  exit 1
fi

mkdir -p "$DST_DIR"

created=0
existing=0

for flow_dir in "$SRC_DIR"/*; do
  [[ -d "$flow_dir" ]] || continue

  flow_id="$(basename "$flow_dir")"
  target_dir="$DST_DIR/$flow_id"

  if [[ -d "$target_dir" ]]; then
    echo "Schon vorhanden: $target_dir"
    ((existing+=1))
  else
    mkdir -p "$target_dir"
    echo "Angelegt: $target_dir"
    ((created+=1))
  fi
done

echo
echo "Fertig."
echo "Neu angelegt: $created"
echo "Schon vorhanden: $existing"
