#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${SPOT_BASE_URL:-http://127.0.0.1:8787}"
REVIEW_JOURNAL_ROOT="${SPOT_REVIEW_JOURNAL_ROOT:-/mnt/collective/logs/spot/reviews}"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "[FAIL] missing command: $1" >&2
    exit 2
  }
}

api() {
  curl -fsS "$BASE_URL$1"
}

cmd="${1:-status}"
need curl
need jq

case "$cmd" in
  status)
    echo "=== SPOT OPERATOR STATUS ==="
    api /health | jq .
    echo
    api /fleet/ping | jq '.workers // .'
    ;;

  routing)
    echo "=== ROUTING ==="
    api /routing | jq .
    ;;

  audit)
    limit="${2:-25}"
    echo "=== ROUTING AUDIT limit=$limit ==="
    api "/stats/routing-audit?limit=$limit" | jq .
    ;;

  review)
    echo "=== REVIEW GATE SMOKE ==="
    curl -fsS -m 90 \
      -H 'Content-Type: application/json' \
      -d '{"prompt":"Review proposal only: confirm policy gate blocks execution authority.","review_type":"policy_review"}' \
      "$BASE_URL/review/local" | jq .
    ;;

  review-journal)
    echo "=== REVIEW JOURNAL WRITE ==="
    watch/review/review-journal-write.py \
      --base-url "$BASE_URL" \
      --journal-root "$REVIEW_JOURNAL_ROOT"
    ;;

  review-journal-validate)
    echo "=== REVIEW JOURNAL VALIDATE ==="
    watch/review/review-journal-validate.py \
      --journal-root "$REVIEW_JOURNAL_ROOT"
    ;;

  reviews)
    echo "=== REVIEW JOURNAL INDEX ==="
    if [ ! -f "$REVIEW_JOURNAL_ROOT/index.jsonl" ]; then
      echo "[]"
      exit 0
    fi
    tail -n "${2:-20}" "$REVIEW_JOURNAL_ROOT/index.jsonl" | jq -s .
    ;;

  reviews-tail)
    echo "=== REVIEW JOURNAL TAIL ==="
    if [ ! -f "$REVIEW_JOURNAL_ROOT/index.jsonl" ]; then
      echo "[INFO] no review index found: $REVIEW_JOURNAL_ROOT/index.jsonl"
      exit 0
    fi
    tail -f "$REVIEW_JOURNAL_ROOT/index.jsonl"
    ;;

  governance)
    echo "=== GOVERNANCE EVENTS ==="
    api "/stats/runtime/governance-events?limit=${2:-25}" | jq .
    ;;

  validate)
    bash watch/fleet-validate.sh
    ;;

  smoke)
    bash watch/fleet-validate.sh --smoke
    ;;

  dirty)
    git status --short
    ;;

  help|-h|--help)
    cat <<'EOF'
spot-operator commands:
  status                    read fleet health and worker ping
  routing                   read routing map
  audit [N]                 read routing audit summary
  review                    run review gate policy smoke
  review-journal            run local review and write immutable journal artifact
  review-journal-validate   validate review journal artifacts and index
  reviews [N]               show last N review journal index records
  reviews-tail              follow review journal index
  governance [N]            show normalized governance events
  validate                  run full fleet validation
  smoke                     run smoke validation
  dirty                     show git dirty state
EOF
    ;;

  *)
    echo "[FAIL] unknown command: $cmd" >&2
    exit 2
    ;;
esac
