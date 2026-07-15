#!/usr/bin/env bash
set -Eeuo pipefail

BASE_URL="${SPOT_BASE_URL:-http://127.0.0.1:8787}"
STATE_DIR="${WATCH_STATE_DIR:-/home/ogre/spot-stack/watch/state}"
FLEET_STATUS_FILE="${FLEET_STATUS_FILE:-${STATE_DIR}/fleet-status.json}"
ROUTING_AUDIT_SUMMARY_FILE="${ROUTING_AUDIT_SUMMARY_FILE:-${STATE_DIR}/routing-audit-summary.json}"
TIMEOUT="${SPOT_OVERVIEW_TIMEOUT:-5}"

section() {
  printf '\n===== %s =====\n' "$*"
}

json_get() {
  local path="$1"
  curl -fsS --connect-timeout 3 --max-time "$TIMEOUT" "${BASE_URL}${path}" 2>/dev/null || true
}

compact_json() {
  jq -c . 2>/dev/null || cat
}

section "SPOT OPERATOR OVERVIEW"
echo "timestamp=$(date -Is)"
echo "host=$(hostname)"
echo "base_url=${BASE_URL}"
echo "state_dir=${STATE_DIR}"
echo "mode=read_only"

section "REPO"
if git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "root=$(git rev-parse --show-toplevel)"
  echo "branch=$(git branch --show-current)"
  echo "head=$(git rev-parse --short HEAD)"
  git status --short --branch
else
  echo "repo=not_available"
fi

section "SYSTEMD"
echo "--- failed services ---"
systemctl --failed --no-pager || true

echo
echo "--- running spot surface ---"
systemctl list-units --type=service --state=running \
  '*spot*' '*starfleet*' '*caddy*' '*cloudflared*' '*ssh*' \
  --no-pager || true

section "LISTENERS"
ss -lntup | egrep ':22|:80|:443|:5173|:7681|:8010|:8787' || true

section "MOUNTS"
findmnt /mnt/collective /mnt/unimatrix6 /mnt/ai-data 2>/dev/null || true
df -h | egrep '/mnt/collective|/mnt/unimatrix6|/mnt/ai-data|unimatrix6|192.168.50.10' || true

section "CORE HEALTH"
json_get "/health" | compact_json

section "RUNTIME SUMMARY"
json_get "/stats/runtime" | compact_json

section "ROUTING AUDIT API"
json_get "/stats/routing-audit" | jq '{
  ok,
  window_count,
  primaries,
  fallbacks,
  violations,
  manual_overrides,
  last_violation_ts,
  role_owners
}' 2>/dev/null || true

section "FLEET STATUS FILE"
if [ -f "$FLEET_STATUS_FILE" ]; then
  jq '{
    ok: (.ok // .fleet_ok // null),
    ts: (.ts // .timestamp // null),
    core: (.core // null),
    hosts: (
      .hosts
      | if type == "object" then
          to_entries
          | map({
              name: .key,
              ok: (.value.ok // null),
              ssh_ok: (.value.ssh_ok // null),
              service_ok: (.value.service_ok // null),
              eligible: (.value.eligible // null),
              quarantined: (.value.quarantined // null),
              primary_role: (.value.primary_role // .value.role // null)
            })
        else
          null
        end
    )
  }' "$FLEET_STATUS_FILE" 2>/dev/null || cat "$FLEET_STATUS_FILE"
else
  echo "missing=${FLEET_STATUS_FILE}"
fi

section "ROUTING AUDIT SUMMARY FILE"
if [ -f "$ROUTING_AUDIT_SUMMARY_FILE" ]; then
  jq '{
    ok,
    window_count,
    primaries,
    fallbacks,
    violations,
    manual_overrides,
    by_role,
    role_owners
  }' "$ROUTING_AUDIT_SUMMARY_FILE" 2>/dev/null || cat "$ROUTING_AUDIT_SUMMARY_FILE"
else
  echo "missing=${ROUTING_AUDIT_SUMMARY_FILE}"
fi

section "WORKER REACHABILITY"
for h in \
  spot-worker-01 \
  spot-worker-02 \
  spot-worker-03 \
  spot-worker-04 \
  spot-worker-05 \
  spot-worker-06
do
  printf '%s ' "$h"
  if getent hosts "$h" >/dev/null 2>&1 && ping -c 1 -W 1 "$h" >/dev/null 2>&1; then
    printf 'ping=ok '
  else
    printf 'ping=fail '
  fi

  if ssh -o BatchMode=yes -o ConnectTimeout=3 "$h" 'printf "ssh=ok "; systemctl is-active ollama 2>/dev/null | tr "\n" " "; hostname' 2>/dev/null; then
    true
  else
    printf 'ssh=fail\n'
  fi
done

section "KNOWN NON-BLOCKERS"
echo "spot-edge-01=recovery_edge_registered_read_only_non_routing"
echo "unimatrix6_ssh=may_deny_ogre_while_storage_access_works"
echo "status_json=runtime_drift_do_not_commit"

section "AUTHORITY"
echo "spot_core_sole_executor=true"
echo "worker_self_apply=false"
echo "mutation_authority=false"
echo "mode=read_only"
