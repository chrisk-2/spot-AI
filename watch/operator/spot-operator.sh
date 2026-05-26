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


  review-health)
    echo "=== REVIEW HEALTH ==="
    api "/fleet/ping" | jq '{
      review: ."spot-worker-05",
      reasoning: ."spot-worker-06"
    }'
    ;;

  review-openai)
    echo "=== OPENAI REVIEW GATE ==="
    echo "[INFO] approval-required external review only"
    ;;

  review-escalate)
    echo "=== REVIEW ESCALATION PATH ==="
    echo "worker-05 -> worker-06 -> approval-required external review"
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

  executor-chain)
    echo "=== EXECUTOR ROLLBACK CHAIN ==="
    echo "detect -> analyze -> classify -> backup -> bind -> review -> preflight -> execute -> verify -> rollback/halt -> journal"
    ;;

  executor-policy)
    echo "=== EXECUTOR POLICY ==="
    echo "Spot Core is sole executor"
    echo "No backup means no change"
    echo "No rollback means no execution"
    echo "No review means no apply"
    echo "Workers do not self-apply"
    ;;

  network-truth)
    exec watch/network/network-truth-snapshot.py
    ;;

  network-validate)
    exec watch/network/network-truth-validate.py
    ;;

  runtime-snapshot)
    exec watch/runtime/observability/runtime-observability-snapshot.py
    ;;

  runtime-validate)
    exec watch/runtime/observability/runtime-observability-validate.py
    ;;

  capabilities)
    exec watch/capabilities/capability-registry-snapshot.py
    ;;

  capabilities-validate)
    exec watch/capabilities/capability-registry-validate.py
    ;;

  ui-status)
    exec watch/ui/ui-operator-status-export.py
    ;;

  ui-status-validate)
    exec watch/ui/ui-operator-status-validate.py
    ;;

  execution-plan)
    shift || true
    exec watch/orchestration/controlled-execution-plan.py "$@"
    ;;

  execution-plan-validate)
    exec watch/orchestration/controlled-execution-plan-validate.py
    ;;



  chain)
    exec watch/chain/chain-show.py
    ;;
  chain-show)
    shift || true
    exec watch/chain/chain-show.py "$@"
    ;;
  chain-validate)
    shift || true
    exec watch/chain/chain-validate.py "$@"
    ;;

  receipts)
    exec watch/receipt/receipt-show.py
    ;;
  receipt-show)
    shift || true
    exec watch/receipt/receipt-show.py "$@"
    ;;
  receipt-validate)
    shift || true
    exec watch/receipt/receipt-validate.py "$@"
    ;;

  leases)
    exec watch/lease/lease-show.py
    ;;
  lease-show)
    shift || true
    exec watch/lease/lease-show.py "$@"
    ;;
  lease-validate)
    shift || true
    exec watch/lease/lease-validate.py "$@"
    ;;
  rollbacks)
    exec watch/rollback/rollback-show.py
    ;;
  rollback-show)
    shift || true
    exec watch/rollback/rollback-show.py "$@"
    ;;
  rollback-validate)
    shift || true
    exec watch/rollback/rollback-validate.py "$@"
    ;;
  preflight)
    shift || true
    exec watch/preflight/preflight-check.py "$@"
    ;;

  noop-show)
    shift || true
    exec watch/executor/noop-show.py "$@"
    ;;
  noop-validate)
    shift || true
    exec watch/executor/noop-validate.py "$@"
    ;;
  bundles)
    exec watch/governance/bundle-show.py
    ;;
  bundle-show)
    shift || true
    exec watch/governance/bundle-show.py "$@"
    ;;
  bundle-validate)
    shift || true
    exec watch/governance/bundle-validate.py "$@"
    ;;

  approvals)
    exec watch/approval/approval-show.py
    ;;
  approval-show)
    shift || true
    exec watch/approval/approval-show.py "$@"
    ;;
  approval-validate)
    shift || true
    exec watch/approval/approval-validate.py "$@"
    ;;
  failures)
    exec watch/failure/failure-proof-show.py
    ;;
  failure-show)
    shift || true
    exec watch/failure/failure-proof-show.py "$@"
    ;;
  failure-validate)
    shift || true
    exec watch/failure/failure-proof-validate.py "$@"
    ;;

  sandbox-show)
    shift || true
    exec watch/sandbox/sandbox-mutation-show.py "$@"
    ;;
  sandbox-validate)
    shift || true
    exec watch/sandbox/sandbox-mutation-validate.py "$@"
    ;;

  remediation-show)
    shift || true
    exec watch/remediation/controlled-remediation-show.py "$@"
    ;;
  remediation-validate)
    shift || true
    exec watch/remediation/controlled-remediation-validate.py "$@"
    ;;

  remediation-policy)
    exec watch/remediation/governed-remediation-policy.py
    ;;

  remediation-policy-validate)
    exec watch/remediation/governed-remediation-policy-validate.py
    ;;
  rollback-failure-show)
    shift || true
    exec watch/remediation/rollback-on-failure-show.py "$@"
    ;;
  rollback-failure-validate)
    shift || true
    exec watch/remediation/rollback-on-failure-validate.py "$@"
    ;;

  learning-show)
    shift || true
    exec watch/learning/learning-proposal-show.py "$@"
    ;;
  learning-validate)
    shift || true
    exec watch/learning/learning-proposal-validate.py "$@"
    ;;
  acceptance-show)
    shift || true
    exec watch/acceptance/controlled-autonomy-show.py "$@"
    ;;
  acceptance-validate)
    shift || true
    exec watch/acceptance/controlled-autonomy-validate.py "$@"
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
  review-health             show review/reasoning worker health
  review-openai             show external review gate status
  review-escalate           show escalation chain
  review-journal            run local review and write immutable journal artifact
  review-journal-validate   validate review journal artifacts and index
  reviews [N]               show last N review journal index records
  reviews-tail              follow review journal index
  governance [N]            show normalized governance events
  executor-chain            show required execution chain
  executor-policy           show executor safety policy
  network-truth             collect read-only network truth snapshot
  network-validate          validate read-only network truth collection
  runtime-snapshot          collect runtime observability snapshot
  runtime-validate          validate runtime observability endpoints
  capabilities             show normalized worker capability registry
  capabilities-validate    validate worker role/capability registry
  ui-status                 export normalized UI operator status
  ui-status-validate        validate UI operator export
  execution-plan            create read-only controlled execution plan
  execution-plan-validate   validate controlled execution planner
  remediation-policy        show governed remediation policy
  remediation-policy-validate validate governed remediation policy
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
