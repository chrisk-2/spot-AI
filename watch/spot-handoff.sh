#!/usr/bin/env bash
set -Eeuo pipefail

SPOT_BASE_URL="${SPOT_BASE_URL:-http://127.0.0.1:8787}"
ROOT="${ROOT:-/home/ogre/spot-stack}"
STATE_DIR="${ROOT}/watch/state"
OUT_MD="${STATE_DIR}/HANDOFF-LATEST.md"
OUT_JSON="${STATE_DIR}/HANDOFF-LATEST.json"
OUT_CHAT="${STATE_DIR}/CHAT-RESUME.txt"
OUT_CODEX="${STATE_DIR}/CODEX_CONTEXT.md"

mkdir -p "$STATE_DIR"

TS_UTC="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
COMMIT="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
BRANCH="$(git -C "$ROOT" branch --show-current 2>/dev/null || echo unknown)"
DIRTY="$(git -C "$ROOT" status --short 2>/dev/null | wc -l | tr -d ' ')"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

safe_curl_json() {
  local url="$1" out="$2"
  curl -fsS --max-time 15 "$url" -o "$out" 2>/dev/null || echo '{}' > "$out"
  jq -e . "$out" >/dev/null 2>&1 || echo '{}' > "$out"
}

safe_file_json() {
  local src="$1" out="$2"
  if [[ -f "$src" ]] && jq -e . "$src" >/dev/null 2>&1; then
    cp "$src" "$out"
  else
    echo '{}' > "$out"
  fi
}

safe_tail_file() {
  local src="$1" out="$2" lines="${3:-20}"
  if [[ -f "$src" ]]; then
    tail -n "$lines" "$src" > "$out" || true
  else
    : > "$out"
  fi
}

safe_curl_json "${SPOT_BASE_URL}/health" "$tmp/health.json"
safe_curl_json "${SPOT_BASE_URL}/fleet/ping" "$tmp/fleet.json"
safe_curl_json "${SPOT_BASE_URL}/routing" "$tmp/routing.json"
safe_curl_json "${SPOT_BASE_URL}/stats/routing-audit?limit=50" "$tmp/routing-audit.json"
safe_curl_json "${SPOT_BASE_URL}/stats/recent-decisions?limit=10" "$tmp/recent-decisions.json"
safe_curl_json "${SPOT_BASE_URL}/operator/readiness" "$tmp/readiness.json"

safe_file_json "${STATE_DIR}/remediation-state.json" "$tmp/remediation.json"
safe_file_json "${STATE_DIR}/executor-preflight-summary.json" "$tmp/executor-preflight-summary.json"
safe_file_json "${STATE_DIR}/backup-binding-contract-summary.json" "$tmp/backup-binding-summary.json"
safe_file_json "${STATE_DIR}/backup-artifact-manifest-contract-summary.json" "$tmp/backup-artifact-summary.json"

safe_tail_file "${ROOT}/watch/contracts/executor-journal/index.jsonl" "$tmp/executor-journal-tail.jsonl" 25
safe_tail_file "${ROOT}/watch/contracts/approval-ledger/index.jsonl" "$tmp/approval-ledger-tail.jsonl" 25

VALIDATE_OUT="$tmp/validate.txt"
if command -v spot >/dev/null 2>&1; then
  spot validate > "$VALIDATE_OUT" 2>&1 || true
else
  bash "${ROOT}/watch/fleet-validate.sh" > "$VALIDATE_OUT" 2>&1 || true
fi

VALIDATE_RESULT="$(grep -E '^RESULT:' "$VALIDATE_OUT" | tail -n 1 | awk '{print $2}' || true)"
VALIDATE_SUMMARY="$(grep -E '^pass=' "$VALIDATE_OUT" | tail -n 1 || true)"

jq -n \
  --arg ts "$TS_UTC" \
  --arg commit "$COMMIT" \
  --arg branch "$BRANCH" \
  --argjson dirty "$DIRTY" \
  --arg validate_result "${VALIDATE_RESULT:-unknown}" \
  --arg validate_summary "${VALIDATE_SUMMARY:-unknown}" \
  --slurpfile health "$tmp/health.json" \
  --slurpfile fleet "$tmp/fleet.json" \
  --slurpfile routing "$tmp/routing.json" \
  --slurpfile audit "$tmp/routing-audit.json" \
  --slurpfile decisions "$tmp/recent-decisions.json" \
  --slurpfile readiness "$tmp/readiness.json" \
  --slurpfile remediation "$tmp/remediation.json" \
  --slurpfile preflight "$tmp/executor-preflight-summary.json" \
  --slurpfile backup_binding "$tmp/backup-binding-summary.json" \
  --slurpfile backup_artifact "$tmp/backup-artifact-summary.json" \
  '{
    timestamp_utc: $ts,
    repo: {
      branch: $branch,
      commit: $commit,
      dirty_files: $dirty
    },
    validation: {
      result: $validate_result,
      summary: $validate_summary
    },
    governance: {
      policy_state: "proposal_only_locked",
      mutation_performed: false,
      execution_performed: false,
      autonomous_apply_enabled: false
    },
    routing_owners: {
      general: "spot-worker-01",
      utility: "spot-worker-02",
      coding: "spot-worker-03",
      heavy: "spot-worker-04",
      reasoning: "spot-worker-06"
    },
    health: $health[0],
    fleet: $fleet[0],
    routing: $routing[0],
    routing_audit: $audit[0],
    recent_decisions: $decisions[0],
    readiness: $readiness[0],
    remediation: $remediation[0],
    executor_preflight_summary: $preflight[0],
    backup_binding_summary: $backup_binding[0],
    backup_artifact_summary: $backup_artifact[0]
  }' > "$OUT_JSON"

cat > "$OUT_MD" <<MD
# Starfleet / Spot Handoff Latest

Generated UTC: ${TS_UTC}

## Repo

- Branch: \`${BRANCH}\`
- Commit: \`${COMMIT}\`
- Dirty files: \`${DIRTY}\`

## Validation

- Result: \`${VALIDATE_RESULT:-unknown}\`
- Summary: \`${VALIDATE_SUMMARY:-unknown}\`

\`\`\`text
$(cat "$VALIDATE_OUT")
\`\`\`

## Current Routing Ownership

\`\`\`text
general   -> spot-worker-01
utility   -> spot-worker-02
coding    -> spot-worker-03
heavy     -> spot-worker-04
reasoning -> spot-worker-06
\`\`\`

## Current Known Runtime Notes

- Worker-06 may be quarantined/offline; do not block active autonomy work on it.
- Heavy premium routing should use worker-04 with qwen3:30b-a3b.
- Codex remains proposal/patch-only.
- Spot Core remains validation/apply authority.
- No autonomous runtime mutation.
- No autonomous service restart.
- No autonomous routing/network mutation.
- No backup delete/overwrite.
- No-backup-no-change remains enforced.

## Key Artifacts

- Machine snapshot: \`watch/state/HANDOFF-LATEST.json\`
- Chat resume prompt: \`watch/state/CHAT-RESUME.txt\`
- Codex context: \`watch/state/CODEX_CONTEXT.md\`
MD

cat > "$OUT_CHAT" <<CHAT
Read HANDOFF.md, spot-core/STATE.md, and watch/state/HANDOFF-LATEST.md first.

Resume Starfleet OS / Spot autonomy work from commit ${COMMIT} on branch ${BRANCH}.

Current live validation:
${VALIDATE_SUMMARY:-unknown}
RESULT: ${VALIDATE_RESULT:-unknown}

Current operating constraints:
- proposal_only_locked
- mutation_performed=false
- execution_performed=false
- Codex is proposal/patch-only
- Spot Core is validation/apply authority
- no autonomous live writes
- no autonomous service restarts
- no routing ownership changes
- no network/firewall/DNS mutation
- no backup deletion/overwrite
- no-backup-no-change enforced

Current routing ownership:
general -> spot-worker-01
utility -> spot-worker-02
coding -> spot-worker-03
heavy -> spot-worker-04
reasoning -> spot-worker-06

Known current exception:
worker-06 is physically unreachable/quarantined; continue without worker-06 unless specifically working hardware recovery.

Current fixed behavior:
premium heavy no-fallback routes to spot-worker-04 / qwen3:30b-a3b.

Next target:
continue Codex integration and supervised Spot autonomy continuity/journal/preflight work.
CHAT

cat > "$OUT_CODEX" <<CODEX
# Codex Context — Starfleet / Spot

Generated UTC: ${TS_UTC}

## Mode

Codex is proposal/patch-only.

Do not perform live writes, service restarts, network mutation, routing ownership changes, or backup mutation.

All changes must be reviewable and validated by Spot/operator.

## Repo

- Root: ${ROOT}
- Branch: ${BRANCH}
- Commit: ${COMMIT}
- Dirty files: ${DIRTY}

## Validation

- Result: ${VALIDATE_RESULT:-unknown}
- Summary: ${VALIDATE_SUMMARY:-unknown}

## Routing Ownership

- general -> spot-worker-01
- utility -> spot-worker-02
- coding -> spot-worker-03
- heavy -> spot-worker-04
- reasoning -> spot-worker-06

## Current Runtime Exception

worker-06 may be quarantined/offline. Do not assume it is usable.

## Required Discipline

- No \`git add .\`
- Minimal patches
- Syntax-check before restart
- Runtime state separate from source config
- Preserve audit/history files
- Backups required before mutation
- Prefer deterministic validation commands
CODEX

printf '%s\n' "wrote: $OUT_MD"
printf '%s\n' "wrote: $OUT_JSON"
printf '%s\n' "wrote: $OUT_CHAT"
printf '%s\n' "wrote: $OUT_CODEX"
