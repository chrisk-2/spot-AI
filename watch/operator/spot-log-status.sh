#!/usr/bin/env bash
set -Eeuo pipefail

LOG_BASE="${SPOT_LOG_BASE:-/mnt/collective/logs/spot}"
LIMIT="${SPOT_LOG_LIMIT:-10}"

section() { printf '\n===== %s =====\n' "$*"; }

section "SPOT LOG STATUS"
echo "timestamp=$(date -Is)"
echo "mode=read_only"
echo "mutation_authority=false"
echo "log_base=${LOG_BASE}"

section "LOG ROOT COUNTS"
for d in actions reviews backups rollbacks learning archive fleet-truth; do
  path="${LOG_BASE}/${d}"
  if [ -d "$path" ]; then
    count="$(find "$path" -type f 2>/dev/null | wc -l | tr -d ' ')"
    newest="$(find "$path" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2- || true)"
    echo "$d count=$count newest=${newest:-none}"
  else
    echo "$d missing=$path"
  fi
done

section "RECENT ACTIONS"
if [ -d "${LOG_BASE}/actions" ]; then
  find "${LOG_BASE}/actions" -maxdepth 1 -type d -printf '%TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null | sort | tail -"$LIMIT"
else
  echo "actions_root_missing"
fi

section "RECENT BACKUPS"
if [ -d "/mnt/collective/backups" ]; then
  find /mnt/collective/backups -maxdepth 4 -type d -printf '%TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null | sort | tail -"$LIMIT"
else
  echo "backup_root_missing"
fi

section "RECENT RESULT LINES"
if [ -d "${LOG_BASE}/actions" ]; then
  grep -R "RESULT:\|pass=\|warn=\|fail=" "${LOG_BASE}/actions" 2>/dev/null | tail -"$LIMIT" || true
fi

section "AUTHORITY"
echo "logs_append_only=true"
echo "logs_delete_allowed=false"
echo "backup_delete_allowed=false"
