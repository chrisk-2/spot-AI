#!/usr/bin/env bash
set -Eeuo pipefail

# Prune Spot monitor snapshot JSON files with tiered retention.
# Default policy:
# - keep all snapshots for the most recent 2 days
# - keep hourly representatives through day 14
# - keep daily representatives through day 60
# - delete snapshots older than day 60

ROOT="${1:-${SNAPSHOT_ROOT:-$HOME/spot-stack/watch/state/history/snapshots}}"
LOG="${PRUNE_LOG:-$HOME/spot-stack/watch/logs/prune-monitor-snapshots.log}"
KEEP_ALL_DAYS="${KEEP_ALL_DAYS:-2}"
KEEP_HOURLY_DAYS="${KEEP_HOURLY_DAYS:-14}"
KEEP_DAILY_DAYS="${KEEP_DAILY_DAYS:-60}"
DRY_RUN="${DRY_RUN:-0}"

mkdir -p "$(dirname "$LOG")"

log() {
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$LOG"
}

if [[ ! -d "$ROOT" ]]; then
  log "prune_snapshots missing_dir root=$ROOT"
  exit 0
fi

now="$(date -u +%s)"
deleted=0
kept=0
scanned=0

while IFS= read -r -d '' file; do
  scanned=$((scanned + 1))
  base="$(basename "$file")"

  # Expected monitor snapshot filename: YYYY-MM-DD-epoch.json
  if [[ ! "$base" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]+\.json$ ]]; then
    kept=$((kept + 1))
    continue
  fi

  mtime="$(stat -c %Y "$file")"
  age_days=$(( (now - mtime) / 86400 ))
  keep=0

  if (( age_days <= KEEP_ALL_DAYS )); then
    keep=1
  elif (( age_days <= KEEP_HOURLY_DAYS )); then
    # Keep snapshots near the top of each hour.
    minute="$(date -u -d "@$mtime" +%M)"
    if [[ "$minute" == "00" || "$minute" == "01" || "$minute" == "02" ]]; then
      keep=1
    fi
  elif (( age_days <= KEEP_DAILY_DAYS )); then
    # Keep snapshots near midnight UTC.
    hhmm="$(date -u -d "@$mtime" +%H%M)"
    if [[ "$hhmm" == "0000" || "$hhmm" == "0001" || "$hhmm" == "0002" ]]; then
      keep=1
    fi
  fi

  if (( keep == 1 )); then
    kept=$((kept + 1))
  else
    if [[ "$DRY_RUN" == "1" ]]; then
      printf 'DRY_RUN delete %s\n' "$file"
    else
      rm -f -- "$file"
    fi
    deleted=$((deleted + 1))
  fi
done < <(find "$ROOT" -maxdepth 1 -type f -name '*.json' -print0)

log "prune_snapshots root=$ROOT scanned=$scanned kept=$kept deleted=$deleted dry_run=$DRY_RUN keep_all_days=$KEEP_ALL_DAYS keep_hourly_days=$KEEP_HOURLY_DAYS keep_daily_days=$KEEP_DAILY_DAYS"
