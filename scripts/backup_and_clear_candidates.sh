#!/usr/bin/env bash
set -euo pipefail

# usage:
#   ./scripts/backup_and_clear_candidates.sh --all
#   ./scripts/backup_and_clear_candidates.sh 01_sixflags_a52fcf7a-50aa-4256-8796-654b3dc3adac
#
# optional env:
#   BASE_DIR=/path/to/tech ./scripts/backup_and_clear_candidates.sh --all

BASE_DIR="${BASE_DIR:-$(pwd)}"
CAND_ROOT="$BASE_DIR/data/generated/candidate_requirements"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_ROOT="$CAND_ROOT/_backup/$TIMESTAMP"

usage() {
  echo "Usage:"
  echo "  $0 --all"
  echo "  $0 <flow_id>"
  exit 1
}

ensure_dirs() {
  if [[ ! -d "$CAND_ROOT" ]]; then
    echo "Fehler: Kandidatenordner nicht gefunden: $CAND_ROOT" >&2
    exit 1
  fi
  mkdir -p "$BACKUP_ROOT"
}

backup_and_remove_one() {
  local flow_dir="$1"
  local flow_id
  flow_id="$(basename "$flow_dir")"
  local candidate_file="$flow_dir/candidate_requirements.json"

  if [[ ! -f "$candidate_file" ]]; then
    echo "[skip] $flow_id -> keine candidate_requirements.json vorhanden"
    return 0
  fi

  local target_dir="$BACKUP_ROOT/$flow_id"
  mkdir -p "$target_dir"

  cp "$candidate_file" "$target_dir/candidate_requirements.json"

  if cmp -s "$candidate_file" "$target_dir/candidate_requirements.json"; then
    rm "$candidate_file"
    echo "[ok]   $flow_id -> gesichert nach $target_dir und aktiv entfernt"
  else
    echo "[err]  $flow_id -> Backup-Prüfung fehlgeschlagen, Original bleibt erhalten" >&2
    return 1
  fi
}

main() {
  [[ $# -eq 1 ]] || usage
  ensure_dirs

  case "$1" in
    --all)
      shopt -s nullglob
      local found=0
      for flow_dir in "$CAND_ROOT"/*; do
        [[ -d "$flow_dir" ]] || continue
        [[ "$(basename "$flow_dir")" == "_backup" ]] && continue
        found=1
        backup_and_remove_one "$flow_dir"
      done

      if [[ "$found" -eq 0 ]]; then
        echo "Keine Flow-Ordner unter $CAND_ROOT gefunden."
      else
        echo
        echo "Backup abgeschlossen."
        echo "Backup-Ordner: $BACKUP_ROOT"
      fi
      ;;
    *)
      local flow_dir="$CAND_ROOT/$1"
      [[ -d "$flow_dir" ]] || {
        echo "Fehler: Flow-Ordner nicht gefunden: $flow_dir" >&2
        exit 1
      }
      backup_and_remove_one "$flow_dir"
      echo
      echo "Backup-Ordner: $BACKUP_ROOT"
      ;;
  esac
}

main "$@"
