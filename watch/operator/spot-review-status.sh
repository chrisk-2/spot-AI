#!/usr/bin/env bash
set -Eeuo pipefail

BASE_URL="${SPOT_BASE_URL:-http://127.0.0.1:8787}"
REVIEW_ROOT="${SPOT_REVIEW_LOG_ROOT:-/mnt/collective/logs/spot/reviews}"
ALT_REVIEW_ROOT="/home/ogre/spot-stack/watch/state"
TIMEOUT="${SPOT_REVIEW_STATUS_TIMEOUT:-5}"

section() { printf '\n===== %s =====\n' "$*"; }

section "SPOT REVIEW STATUS"
echo "timestamp=$(date -Is)"
echo "mode=read_only"
echo "mutation_authority=false"
echo "primary_reviewer=spot-worker-05"
echo "escalation_reviewer=spot-worker-06"
echo "external_review=approval_required"

section "LOCAL REVIEW ENDPOINT HEALTH"
curl -fsS --connect-timeout 3 --max-time "$TIMEOUT" "${BASE_URL}/review/local" 2>/dev/null | jq -c . 2>/dev/null || echo "review_local_get=unavailable_or_method_not_allowed"

section "REVIEW LOG ROOTS"
for root in "$REVIEW_ROOT" "$ALT_REVIEW_ROOT"; do
  echo "--- $root ---"
  if [ -d "$root" ]; then
    find "$root" -maxdepth 2 -type f \( -name '*review*' -o -name '*.jsonl' -o -name '*.json' \) -printf '%TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null | sort | tail -20 || true
  else
    echo "missing=$root"
  fi
done

section "LOCAL REVIEW HISTORY SUMMARY"
hist="$(find "$REVIEW_ROOT" "$ALT_REVIEW_ROOT" -maxdepth 2 -type f -name '*review*.jsonl' 2>/dev/null | head -1 || true)"
if [ -n "$hist" ] && [ -f "$hist" ]; then
  echo "history=$hist"
  tail -50 "$hist" | jq -s '{
    records: length,
    verdicts: (map(.verdict // .decision // "unknown") | group_by(.) | map({key: .[0], count: length})),
    latest: (.[-5:] // [])
  }' 2>/dev/null || tail -20 "$hist"
else
  echo "history=not_found"
fi

section "REVIEW POLICY"
echo "model_may_not_approve_own_work=true"
echo "worker_03_builds=true"
echo "worker_05_reviews=true"
echo "worker_06_escalates=true"
echo "spot_core_enforces=true"
echo "openai_manual_external_only=true"
