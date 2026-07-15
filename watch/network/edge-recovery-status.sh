#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REGISTRY="${ROOT}/spot-core/config/host_registry.json"

NODE="spot-edge-01"
STATUS_ROOT="/mnt/collective/logs/spot/edge/${NODE}"

VALIDATOR_MAX_AGE="${EDGE_VALIDATOR_MAX_AGE:-7200}"
MIRROR_MAX_AGE="${EDGE_MIRROR_MAX_AGE:-7200}"
RESTORE_MAX_AGE="${EDGE_RESTORE_MAX_AGE:-108000}"
KIT_MAX_AGE="${EDGE_KIT_MAX_AGE:-28800}"

PASS=0
FAIL=0

record() {
  local status="$1"
  local check="$2"
  local detail="$3"

  printf '[%s] %-30s %s\n' \
    "$status" \
    "$check" \
    "$detail"

  case "$status" in
    PASS)
      PASS=$((PASS + 1))
      ;;
    FAIL)
      FAIL=$((FAIL + 1))
      ;;
  esac
}

probe_tcp() {
  local address="$1"
  local port="$2"

  timeout 3 bash -c \
    "exec 3<>/dev/tcp/${address}/${port}" \
    >/dev/null 2>&1
}

check_status_file() {
  local label="$1"
  local filename="$2"
  local max_age="$3"
  local expression="$4"

  local path="${STATUS_ROOT}/${filename}"
  local timestamp
  local epoch
  local now
  local age

  if [[ ! -s "$path" ]]; then
    record FAIL "$label" "missing: $path"
    return
  fi

  if ! jq -e "$expression" "$path" >/dev/null 2>&1; then
    record FAIL "$label" "status or governance assertion failed"
    return
  fi

  timestamp="$(jq -r '.timestamp // empty' "$path")"

  if [[ -z "$timestamp" ]]; then
    record FAIL "$label" "timestamp missing"
    return
  fi

  epoch="$(date -u -d "$timestamp" +%s 2>/dev/null || true)"
  now="$(date -u +%s)"

  if [[ -z "$epoch" ]]; then
    record FAIL "$label" "invalid timestamp: $timestamp"
    return
  fi

  age=$((now - epoch))

  if (( age < 0 )); then
    record FAIL "$label" "timestamp is in the future"
    return
  fi

  if (( age > max_age )); then
    record FAIL "$label" "stale age=${age}s max=${max_age}s"
    return
  fi

  record PASS "$label" "PASS age=${age}s"
}

echo "===== SPOT EDGE RECOVERY STATUS ====="
echo "timestamp=$(date -Is)"
echo "observer=$(hostname)"
echo "node=$NODE"
echo "mode=read_only"
echo "mutation_authority=false"
echo

EDGE_IP="$(
  jq -r \
    --arg node "$NODE" \
    '.hosts[]? | select(.name == $node) | .ip // empty' \
    "$REGISTRY" 2>/dev/null |
  head -n1
)"

if [[ -z "$EDGE_IP" ]]; then
  record FAIL registry "spot-edge-01 not registered"
else
  record PASS registry "$NODE=$EDGE_IP"
fi

if [[ -n "$EDGE_IP" ]] &&
  ping -c 1 -W 2 "$EDGE_IP" >/dev/null 2>&1
then
  record PASS icmp "$EDGE_IP reachable"
else
  record FAIL icmp "${EDGE_IP:-UNKNOWN} unreachable"
fi

if [[ -n "$EDGE_IP" ]] &&
  probe_tcp "$EDGE_IP" 22
then
  record PASS ssh "$EDGE_IP:22 open"
else
  record FAIL ssh "${EDGE_IP:-UNKNOWN}:22 closed"
fi

if mountpoint -q /mnt/collective; then
  record PASS collective_mount "/mnt/collective mounted"
else
  record FAIL collective_mount "/mnt/collective unavailable"
fi

check_status_file \
  edge_validator \
  latest.json \
  "$VALIDATOR_MAX_AGE" \
  '.result == "PASS"
   and .governance.mutation_authority == false
   and .governance.public_exposure == false'

check_status_file \
  repository_mirror \
  spot-stack-mirror-latest.json \
  "$MIRROR_MAX_AGE" \
  '.result == "PASS"
   and .access_mode == "pull-only"
   and .mutation_authority == false'

check_status_file \
  restore_drill \
  spot-stack-restore-drill-latest.json \
  "$RESTORE_MAX_AGE" \
  '.result == "PASS"
   and .source_modified == false
   and .mutation_authority == false
   and .validation.repository_restored == true
   and .validation.commit_match == true
   and .validation.tree_match == true'

check_status_file \
  recovery_kit \
  spot-stack-recovery-kit-latest.json \
  "$KIT_MAX_AGE" \
  '.result == "PASS"
   and .source_modified == false
   and .mutation_authority == false
   and .package_verified == true
   and .restore_test_verified == true'

MIRROR_HEAD="$(
  jq -r \
    '.head_after // empty' \
    "$STATUS_ROOT/spot-stack-mirror-latest.json" \
    2>/dev/null || true
)"

RESTORE_HEAD="$(
  jq -r \
    '.expected_head // empty' \
    "$STATUS_ROOT/spot-stack-restore-drill-latest.json" \
    2>/dev/null || true
)"

KIT_HEAD="$(
  jq -r \
    '.head // empty' \
    "$STATUS_ROOT/spot-stack-recovery-kit-latest.json" \
    2>/dev/null || true
)"

if [[ -n "$MIRROR_HEAD" ]] &&
  [[ "$MIRROR_HEAD" == "$RESTORE_HEAD" ]] &&
  [[ "$MIRROR_HEAD" == "$KIT_HEAD" ]]
then
  record PASS recovery_head_consistency "$MIRROR_HEAD"
else
  record FAIL recovery_head_consistency \
    "mirror=${MIRROR_HEAD:-missing} restore=${RESTORE_HEAD:-missing} kit=${KIT_HEAD:-missing}"
fi

echo
echo "summary: pass=$PASS fail=$FAIL"

if (( FAIL == 0 )); then
  echo "overall: HEALTHY"
  echo "mutation_performed: false"
  exit 0
fi

echo "overall: DEGRADED"
echo "mutation_performed: false"
exit 1
