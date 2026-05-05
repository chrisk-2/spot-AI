#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
STATE_DIR="${STATE_DIR:-${BASE_DIR}/state}"
LOG_DIR="${LOG_DIR:-${BASE_DIR}/logs}"
SPOT_BASE_URL="${SPOT_BASE_URL:-http://127.0.0.1:8787}"
SELF_HEAL_SCRIPT="${SELF_HEAL_SCRIPT:-${BASE_DIR}/spot-self-heal.sh}"
EXECUTOR_PREFLIGHT_SCRIPT="${EXECUTOR_PREFLIGHT_SCRIPT:-${BASE_DIR}/spot-executor-preflight.sh}"
BACKUP_BINDING_CONTRACT_SCRIPT="${BACKUP_BINDING_CONTRACT_SCRIPT:-${BASE_DIR}/spot-backup-binding-contract.sh}"
BACKUP_ARTIFACT_MANIFEST_CONTRACT_SCRIPT="${BACKUP_ARTIFACT_MANIFEST_CONTRACT_SCRIPT:-${BASE_DIR}/spot-backup-artifact-manifest-contract.sh}"
VALIDATOR="${VALIDATOR:-${BASE_DIR}/fleet-validate.sh}"
FLEET_STATUS_FILE="${FLEET_STATUS_FILE:-${STATE_DIR}/fleet-status.json}"
AUDIT_SUMMARY_FILE="${AUDIT_SUMMARY_FILE:-${STATE_DIR}/routing-audit-summary.json}"
AUDIT_FILE="${AUDIT_FILE:-${STATE_DIR}/routing-audit.jsonl}"
REMEDIATION_STATE_FILE="${REMEDIATION_STATE_FILE:-${STATE_DIR}/remediation-state.json}"
WATCH_LOG_FILE="${WATCH_LOG_FILE:-${LOG_DIR}/fleet-watch.log}"
REMEDIATE_LOG_FILE="${REMEDIATE_LOG_FILE:-${LOG_DIR}/fleet-remediate.log}"

MONITOR_HISTORY_DIR="${MONITOR_HISTORY_DIR:-${STATE_DIR}/history}"
MONITOR_SUMMARY_FILE="${MONITOR_SUMMARY_FILE:-${MONITOR_HISTORY_DIR}/monitor-summary.jsonl}"

DEFAULT_LOG_LINES="${DEFAULT_LOG_LINES:-80}"
CURL_TIMEOUT="${CURL_TIMEOUT:-20}"
TCP_TIMEOUT="${TCP_TIMEOUT:-3}"

MONITOR_DNS_WARN_COLD_MS="${MONITOR_DNS_WARN_COLD_MS:-120}"
MONITOR_DNS_ALERT_COLD_MS="${MONITOR_DNS_ALERT_COLD_MS:-250}"
MONITOR_DNS_WARN_WARM_MS="${MONITOR_DNS_WARN_WARM_MS:-90}"
MONITOR_DNS_ALERT_WARM_MS="${MONITOR_DNS_ALERT_WARM_MS:-180}"
MONITOR_NET_WARN_AVG_MS="${MONITOR_NET_WARN_AVG_MS:-20}"
MONITOR_NET_ALERT_AVG_MS="${MONITOR_NET_ALERT_AVG_MS:-75}"
MONITOR_NET_WARN_LOSS_PCT="${MONITOR_NET_WARN_LOSS_PCT:-1}"
MONITOR_NET_ALERT_LOSS_PCT="${MONITOR_NET_ALERT_LOSS_PCT:-5}"

usage() {
  cat <<EOF
Usage: $(basename "$0") <command> [args]

Operator commands:
  ask [args]               Ask Spot through the routed assistant client
  propose [args]           Generate a proposal-only engineering plan
  proposals [count]        List saved Spot proposals
  show-proposal <id|file>  Show a saved Spot proposal
  approve <id|file>        Mark a saved proposal approved
  reject <id|file>         Mark a saved proposal rejected
  proposal-status <id|file> Show proposal lifecycle metadata
  generate-patch <id|file> Generate patch artifact from approved proposal
  generate-apply-plan <id|file> Generate supervised apply-plan artifact from approved proposal
  apply-plans [count]      List generated supervised apply-plan artifacts
  show-apply-plan <id|file> Show a generated supervised apply-plan artifact
  apply-plan-status <id|file> Show apply-plan lifecycle metadata
  apply-plan-check <id|file> Verify apply-plan safety guardrails without mutation
  apply-plan-verify <id|file> Verify reviewed or pending apply-plan safety guardrails
  approve-apply-plan <id|file> Mark apply-plan review approved without enabling mutation
  reject-apply-plan <id|file> Mark apply-plan review rejected
  prepare-execution-handoff <id|file> Prepare non-mutating execution handoff artifact
  execution-handoffs [count] List non-mutating execution handoff artifacts
  show-execution-handoff <id|file> Show non-mutating execution handoff artifact
  execution-handoff-status <id|file> Show execution handoff metadata
  execution-handoff-verify <id|file> Verify non-mutating execution handoff artifact
  executor-preflight <plugin-request-id|file>
                           Create dry-run-only executor preflight artifact
  executor-preflights [count]
                           List dry-run-only executor preflight artifacts
  show-executor-preflight <id|file>
                           Show dry-run-only executor preflight artifact
  verify-executor-preflight <id|file>
                           Verify dry-run-only executor preflight artifact
  executor-preflight-summary
                           Summarize dry-run-only executor preflight artifacts
  backup-binding-contract <executor-preflight-id|file>
                           Create design-only backup-binding contract artifact
  backup-binding-contracts [count]
                           List design-only backup-binding contract artifacts
  show-backup-binding-contract <id|file>
                           Show design-only backup-binding contract artifact
  verify-backup-binding-contract <id|file>
                           Verify design-only backup-binding contract artifact
  backup-binding-contract-summary
                           Summarize design-only backup-binding contract artifacts
  backup-artifact-manifest-contract <backup-binding-contract-id|file>
                           Create design-only backup artifact manifest contract
  backup-artifact-manifest-contracts [count]
                           List design-only backup artifact manifest contracts
  show-backup-artifact-manifest-contract <id|file>
                           Show design-only backup artifact manifest contract
  verify-backup-artifact-manifest-contract <id|file>
                           Verify design-only backup artifact manifest contract
  remember <type> <text>   Append durable memory entry
  memory [count]           Show recent durable memory entries
  recall <keyword>         Search durable memory entries
  status                   Show concise operator status summary
  status-json              Show raw JSON operator status
  validate                 Run scripted fleet validation
  validate-smoke [worker]  Run validation with quarantine/unquarantine smoke test
  smoke [worker]           Alias for validate-smoke
  health                   Show /health, fleet-status.json, and /fleet/ping summary
  quick-health             Show one-screen operator health summary
  routing                  Show routing ownership and scheduler routing state
  audit [limit]            Show routing audit summary and recent items
  self-heal [audit|plan|dry-run|apply]  Run self-heal audit/plan/preview/apply wrapper
  net-basics               Show current basic network facts and cleanup targets
  endpoints                Show basic live endpoint reachability checks
  dns-check                Verify key starfleet.local records against both DNS servers
  dns-latency [name]       Measure cold/warm DNS latency against primary, secondary, and 1.1.1.1
  net-latency              Measure internal network latency to key targets
  reverse-proxy-check      Verify named-host reverse proxy behavior through 192.168.60.20
  monitor-latest           Show latest monitor summary and linked snapshot overview
  monitor-history [count]  Show recent monitor summary history entries
  monitor-alerts           Evaluate latest monitor snapshot against read-only alert thresholds
  alert-state             Show current alert state file
  alert-history [count]   Show alert state transitions
  quarantine-state         Show worker eligibility/quarantine/degraded state
  remediation              Show remediation-state.json in operator-friendly form
  quarantine <worker> [seconds] [reason]
                           Quarantine a worker through spot-core API
  release <worker>         Release a quarantined worker through spot-core API
  logs [watch|remediate|both] [lines]
                           Print recent operator logs

Environment overrides:
  BASE_DIR
  STATE_DIR
  LOG_DIR
  SPOT_BASE_URL
  VALIDATOR
  FLEET_STATUS_FILE
  AUDIT_SUMMARY_FILE
  AUDIT_FILE
  REMEDIATION_STATE_FILE
  WATCH_LOG_FILE
  REMEDIATE_LOG_FILE
  MONITOR_HISTORY_DIR
  MONITOR_SUMMARY_FILE
  DEFAULT_LOG_LINES
  CURL_TIMEOUT
  TCP_TIMEOUT

Read-only monitor threshold overrides:
  MONITOR_DNS_WARN_COLD_MS
  MONITOR_DNS_ALERT_COLD_MS
  MONITOR_DNS_WARN_WARM_MS
  MONITOR_DNS_ALERT_WARM_MS
  MONITOR_NET_WARN_AVG_MS
  MONITOR_NET_ALERT_AVG_MS
  MONITOR_NET_WARN_LOSS_PCT
  MONITOR_NET_ALERT_LOSS_PCT

Examples:
  $(basename "$0") ask "what is the current fleet status?"
  $(basename "$0") propose "prepare a safe config patch plan"
  $(basename "$0") propose "fix worker-02 latency" --save
  $(basename "$0") proposals
  $(basename "$0") show-proposal P-YYYYMMDD-HHMMSS-name
  $(basename "$0") approve P-YYYYMMDD-HHMMSS-name
  $(basename "$0") proposal-status P-YYYYMMDD-HHMMSS-name
  $(basename "$0") generate-patch P-YYYYMMDD-HHMMSS-name
  $(basename "$0") generate-apply-plan P-YYYYMMDD-HHMMSS-name
  $(basename "$0") apply-plans
  $(basename "$0") apply-plan-status APPLY-P-YYYYMMDD-HHMMSS-name
  $(basename "$0") apply-plan-check APPLY-P-YYYYMMDD-HHMMSS-name
  $(basename "$0") apply-plan-verify APPLY-P-YYYYMMDD-HHMMSS-name
  $(basename "$0") approve-apply-plan APPLY-P-YYYYMMDD-HHMMSS-name
  $(basename "$0") prepare-execution-handoff APPLY-P-YYYYMMDD-HHMMSS-name
  $(basename "$0") execution-handoffs
  $(basename "$0") execution-handoff-status HANDOFF-APPLY-P-YYYYMMDD-HHMMSS-name
  $(basename "$0") execution-handoff-verify HANDOFF-APPLY-P-YYYYMMDD-HHMMSS-name
  $(basename "$0") executor-preflight PLUGIN-REQUEST-YYYYMMDD-HHMMSS-name
  $(basename "$0") executor-preflights
  $(basename "$0") show-executor-preflight EXECUTOR-PREFLIGHT-YYYYMMDD-HHMMSS-name
  $(basename "$0") verify-executor-preflight EXECUTOR-PREFLIGHT-YYYYMMDD-HHMMSS-name
  $(basename "$0") executor-preflight-summary
  $(basename "$0") backup-binding-contract EXECUTOR-PREFLIGHT-YYYYMMDD-HHMMSS-name
  $(basename "$0") backup-binding-contracts
  $(basename "$0") show-backup-binding-contract BACKUP-BINDING-CONTRACT-YYYYMMDD-HHMMSS-name
  $(basename "$0") verify-backup-binding-contract BACKUP-BINDING-CONTRACT-YYYYMMDD-HHMMSS-name
  $(basename "$0") backup-binding-contract-summary
  $(basename "$0") backup-artifact-manifest-contract BACKUP-BINDING-CONTRACT-YYYYMMDD-HHMMSS-name
  $(basename "$0") backup-artifact-manifest-contracts
  $(basename "$0") show-backup-artifact-manifest-contract BACKUP-ARTIFACT-MANIFEST-CONTRACT-YYYYMMDD-HHMMSS-name
  $(basename "$0") verify-backup-artifact-manifest-contract BACKUP-ARTIFACT-MANIFEST-CONTRACT-YYYYMMDD-HHMMSS-name
  $(basename "$0") remember fact "worker-02 has dual GPUs"
  $(basename "$0") memory
  $(basename "$0") recall worker-02
  $(basename "$0") status
  $(basename "$0") validate
  $(basename "$0") validate-smoke
  $(basename "$0") health
  $(basename "$0") quick-health
  $(basename "$0") routing
  $(basename "$0") audit
  $(basename "$0") self-heal audit
  $(basename "$0") self-heal apply
  $(basename "$0") net-basics
  $(basename "$0") endpoints
  $(basename "$0") dns-check
  $(basename "$0") dns-latency
  $(basename "$0") net-latency
  $(basename "$0") reverse-proxy-check
  $(basename "$0") monitor-latest
  $(basename "$0") monitor-history 10
  $(basename "$0") monitor-alerts
  $(basename "$0") quarantine-state
  $(basename "$0") remediation
  $(basename "$0") quarantine spot-worker-03 1800 manual_test
  $(basename "$0") release spot-worker-03
  $(basename "$0") logs both 100
EOF
}

need_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $cmd" >&2
    exit 2
  }
}

need_file() {
  local file="$1"
  [[ -f "$file" ]] || {
    echo "ERROR: required file not found: $file" >&2
    exit 2
  }
}

need_http() {
  need_cmd curl
  local endpoint="$1"
  curl -fsS --connect-timeout 5 --max-time "$CURL_TIMEOUT" "${SPOT_BASE_URL}${endpoint}" >/dev/null
}

api_get() {
  local endpoint="$1"
  curl -fsS --connect-timeout 5 --max-time "$CURL_TIMEOUT" "${SPOT_BASE_URL}${endpoint}"
}

api_post() {
  local endpoint="$1"
  curl -fsS -X POST --connect-timeout 5 --max-time "$CURL_TIMEOUT" "${SPOT_BASE_URL}${endpoint}"
}

api_delete() {
  local endpoint="$1"
  curl -fsS -X DELETE --connect-timeout 5 --max-time "$CURL_TIMEOUT" "${SPOT_BASE_URL}${endpoint}"
}

print_header() {
  printf '\n=== %s ===\n' "$1"
}

urlencode() {
  local raw="${1:-}"
  local out=""
  local i ch hex
  for ((i=0; i<${#raw}; i++)); do
    ch="${raw:i:1}"

    case "$ch" in
      [a-zA-Z0-9.~_-]) out+="$ch" ;;
      ' ') out+='%20' ;;
      *)
        printf -v hex '%%%02X' "'$ch"
        out+="$hex"
        ;;
    esac
  done
  printf '%s' "$out"
}

tcp_check() {
  local host="$1"
  local port="$2"
  timeout "$TCP_TIMEOUT" bash -lc "exec 3<>/dev/tcp/${host}/${port}" >/dev/null 2>&1
}

http_check() {
  local url="$1"
  local code
  code="$(curl -k -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time "$CURL_TIMEOUT" "$url" 2>/dev/null || true)"
  if [[ "$code" =~ ^[0-9]{3}$ && "$code" != "000" ]]; then
    printf '%s' "$code"
    return 0
  fi
  return 1
}

named_https_check() {
  local host="$1"
  local ip="$2"
  local port="${3:-443}"
  local path="${4:-/}"
  local code

  code="$(
    curl -k -sS -o /dev/null \
      -w '%{http_code}' \
      --connect-timeout 5 \
      --max-time "$CURL_TIMEOUT" \
      --resolve "${host}:${port}:${ip}" \
      "https://${host}:${port}${path}" 2>/dev/null || true
  )"

  if [[ "$code" =~ ^[0-9]{3}$ && "$code" != "000" ]]; then
    printf '%s' "$code"
    return 0
  fi
  return 1
}

endpoint_result_tcp() {
  local name="$1"
  local host="$2"
  local port="$3"
  if tcp_check "$host" "$port"; then
    jq -n \
      --arg name "$name" \
      --arg host "$host" \
      --argjson port "$port" \
      '{name:$name, type:"tcp", host:$host, port:$port, ok:true, detail:"tcp_connect_ok"}'
  else
    jq -n \
      --arg name "$name" \
      --arg host "$host" \
      --argjson port "$port" \
      '{name:$name, type:"tcp", host:$host, port:$port, ok:false, detail:"tcp_connect_failed"}'
  fi
}

endpoint_result_http() {
  local name="$1"
  local url="$2"
  local code=""
  if code="$(http_check "$url")"; then
    jq -n \
      --arg name "$name" \
      --arg url "$url" \
      --arg code "$code" \
      '{name:$name, type:"http", url:$url, ok:true, http_code:($code|tonumber)}'
  else
    jq -n \
      --arg name "$name" \
      --arg url "$url" \
      '{name:$name, type:"http", url:$url, ok:false, detail:"http_request_failed"}'
  fi
}

dns_record_check() {
  local server="$1"
  local name="$2"
  local expected="$3"
  local output=""
  local ok=false

  if command -v dig >/dev/null 2>&1; then
    output="$(dig +short @"$server" "$name" A 2>/dev/null || true)"
  elif command -v nslookup >/dev/null 2>&1; then
    output="$(nslookup "$name" "$server" 2>/dev/null | awk '/^Address: / {print $2}' | tail -n +2 || true)"
  else
    echo "ERROR: dns-check requires dig or nslookup" >&2
    exit 2
  fi

  if printf '%s\n' "$output" | grep -Fxq "$expected"; then
    ok=true

  fi

  jq -n \
    --arg server "$server" \
    --arg name "$name" \
    --arg expected "$expected" \
    --arg output "$output" \
    --argjson ok "$ok" \
    '{
      dns_server: $server,
      record: $name,
      expected_ip: $expected,
      ok: $ok,
      answers: ($output | split("\n") | map(select(length > 0)))
    }'
}

measure_dns_latency_item() {
  local name="$1"
  local server="$2"
  local query="$3"

  python3 - "$name" "$server" "$query" <<'PY'
import json, socket, struct, sys, time, random

name, server, query = sys.argv[1], sys.argv[2], sys.argv[3]

def build_query(qname: str, qtype: int = 1) -> tuple[int, bytes]:
    packet_id = random.randint(0, 65535)
    flags = 0x0100
    header = struct.pack("!HHHHHH", packet_id, flags, 1, 0, 0, 0)
    parts = qname.strip(".").split(".")
    qname_wire = b"".join(bytes([len(p)]) + p.encode("ascii") for p in parts) + b"\x00"
    question = qname_wire + struct.pack("!HH", qtype, 1)
    return packet_id, header + question

def resolve_once(server_ip: str, qname: str, timeout: float = 2.0) -> int:
    packet_id, payload = build_query(qname)
    start = time.perf_counter_ns()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(payload, (server_ip, 53))
        data, _ = sock.recvfrom(2048)
    finally:
        sock.close()
    if len(data) < 2:
        raise RuntimeError("short_dns_reply")
    reply_id = struct.unpack("!H", data[:2])[0]
    if reply_id != packet_id:
        raise RuntimeError("dns_reply_id_mismatch")
    return int((time.perf_counter_ns() - start) / 1_000_000)

try:
    cold_ms = resolve_once(server, query)
    warm_ms = resolve_once(server, query)
    result = {
        "name": name,
        "dns_server": server,
        "query": query,
        "ok": True,
        "cold_ms": cold_ms,
        "warm_ms": warm_ms,
        "error": None,
    }
except Exception as exc:
    result = {
        "name": name,
        "dns_server": server,
        "query": query,
        "ok": False,
        "cold_ms": None,
        "warm_ms": None,
        "error": repr(exc),
    }

print(json.dumps(result))
PY
}

measure_ping_latency_item() {
  local name="$1"
  local host="$2"

  python3 - "$name" "$host" <<'PY'
import json, re, subprocess, sys

name, host = sys.argv[1], sys.argv[2]

try:
    proc = subprocess.run(
        ["ping", "-c", "4", "-W", "2", host],
        capture_output=True,
        text=True,
        check=False,
    )
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    ok = proc.returncode == 0
    avg_ms = None
    loss_pct = None

    m_loss = re.search(r'(\d+(?:\.\d+)?)%\s*packet loss', output)
    if m_loss:
        loss_pct = float(m_loss.group(1))
        if loss_pct.is_integer():
            loss_pct = int(loss_pct)

    m_avg = re.search(r'=\s*([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)\s*ms', output)
    if m_avg:
        avg_ms = float(m_avg.group(2))

    result = {
        "name": name,
        "host": host,
        "ok": ok,
        "avg_ms": avg_ms,
        "packet_loss_pct": loss_pct,
        "error": None if ok or avg_ms is not None or loss_pct is not None else output.strip()[-400:],
    }
except Exception as exc:
    result = {
        "name": name,
        "host": host,
        "ok": False,
        "avg_ms": None,
        "packet_loss_pct": None,
        "error": repr(exc),
    }

print(json.dumps(result))
PY
}


cmd_executor_preflight() {
  need_cmd bash
  need_file "$EXECUTOR_PREFLIGHT_SCRIPT"
  bash "$EXECUTOR_PREFLIGHT_SCRIPT" create "$@"
}

cmd_executor_preflights() {
  need_cmd bash
  need_file "$EXECUTOR_PREFLIGHT_SCRIPT"
  bash "$EXECUTOR_PREFLIGHT_SCRIPT" list "$@"
}

cmd_show_executor_preflight() {
  need_cmd bash
  need_file "$EXECUTOR_PREFLIGHT_SCRIPT"
  bash "$EXECUTOR_PREFLIGHT_SCRIPT" show "$@"
}

cmd_verify_executor_preflight() {
  need_cmd bash
  need_file "$EXECUTOR_PREFLIGHT_SCRIPT"
  bash "$EXECUTOR_PREFLIGHT_SCRIPT" verify "$@"
}

cmd_executor_preflight_summary() {
  need_cmd bash
  need_file "$EXECUTOR_PREFLIGHT_SCRIPT"
  bash "$EXECUTOR_PREFLIGHT_SCRIPT" summary "$@"
}

cmd_backup_binding_contract() {
  need_cmd bash
  need_file "$BACKUP_BINDING_CONTRACT_SCRIPT"
  bash "$BACKUP_BINDING_CONTRACT_SCRIPT" create-design "$@"
}

cmd_backup_binding_contracts() {
  need_cmd bash
  need_file "$BACKUP_BINDING_CONTRACT_SCRIPT"
  bash "$BACKUP_BINDING_CONTRACT_SCRIPT" list "$@"
}

cmd_show_backup_binding_contract() {
  need_cmd bash
  need_file "$BACKUP_BINDING_CONTRACT_SCRIPT"
  bash "$BACKUP_BINDING_CONTRACT_SCRIPT" show "$@"
}

cmd_verify_backup_binding_contract() {
  need_cmd bash
  need_file "$BACKUP_BINDING_CONTRACT_SCRIPT"
  bash "$BACKUP_BINDING_CONTRACT_SCRIPT" verify "$@"
}

cmd_backup_binding_contract_summary() {
  need_cmd bash
  need_file "$BACKUP_BINDING_CONTRACT_SCRIPT"
  bash "$BACKUP_BINDING_CONTRACT_SCRIPT" summary "$@"
}

cmd_backup_artifact_manifest_contract() {
  need_cmd bash
  need_file "$BACKUP_ARTIFACT_MANIFEST_CONTRACT_SCRIPT"
  bash "$BACKUP_ARTIFACT_MANIFEST_CONTRACT_SCRIPT" create-design "$@"
}

cmd_backup_artifact_manifest_contracts() {
  need_cmd bash
  need_file "$BACKUP_ARTIFACT_MANIFEST_CONTRACT_SCRIPT"
  bash "$BACKUP_ARTIFACT_MANIFEST_CONTRACT_SCRIPT" list "$@"
}

cmd_show_backup_artifact_manifest_contract() {
  need_cmd bash
  need_file "$BACKUP_ARTIFACT_MANIFEST_CONTRACT_SCRIPT"
  bash "$BACKUP_ARTIFACT_MANIFEST_CONTRACT_SCRIPT" show "$@"
}

cmd_verify_backup_artifact_manifest_contract() {
  need_cmd bash
  need_file "$BACKUP_ARTIFACT_MANIFEST_CONTRACT_SCRIPT"
  bash "$BACKUP_ARTIFACT_MANIFEST_CONTRACT_SCRIPT" verify "$@"
}

cmd_status_json() {
  need_cmd jq
  need_http "/health"

  jq -n \
    --argjson health "$(api_get "/health")" \
    --argjson ping "$(api_get "/fleet/ping")" \
    --argjson audit "$(api_get "/stats/routing-audit?limit=20")" \
    '{
      health: $health,
      routing_audit: {
        ok: $audit.ok,
        window_count: $audit.window_count,
        primaries: $audit.primaries,
        fallbacks: $audit.fallbacks,
        violations: $audit.violations,
        manual_overrides: $audit.manual_overrides,
        last_violation_ts: $audit.last_violation_ts
      },
      workers: (
        $ping
        | to_entries
        | map({
            worker: .key,
            ok: .value.ok,
            reason: .value.reason,
            primary_role: .value.primary_role,
            eligible: .value.eligible,
            quarantined: .value.quarantined,
            degraded: .value.degraded,
            degraded_reason: .value.degraded_reason,
            running_jobs: .value.running_jobs
          })
      )
    }'
}

cmd_status() {
  need_cmd jq
  need_http "/health"

  local data
  data="$(cmd_status_json)"

  local core_ok uptime routing_ok primaries fallbacks violations

  core_ok=$(echo "$data" | jq -r '.health.ok')
  uptime=$(echo "$data" | jq -r '.health.uptime_sec')
  routing_ok=$(echo "$data" | jq -r '.routing_audit.ok')
  primaries=$(echo "$data" | jq -r '.routing_audit.primaries')
  fallbacks=$(echo "$data" | jq -r '.routing_audit.fallbacks')
  violations=$(echo "$data" | jq -r '.routing_audit.violations')

  print_header "SPOT STATUS"

  printf "Core:        %s (uptime: %ss)\n" \
    "$([ "$core_ok" = "true" ] && echo OK || echo FAIL)" \
    "$uptime"

  printf "Routing:     %s (%s primary, %s fallback, %s violations)\n\n" \
    "$([ "$routing_ok" = "true" ] && echo OK || echo FAIL)" \
    "$primaries" "$fallbacks" "$violations"

  echo "Workers:"
  echo "$data" | jq -r '
    .workers[]
    | "  \(.worker)  [\(.primary_role)]  " +
      (if .ok then "OK" else "FAIL" end)
  '

  local all_ok
  all_ok=$(echo "$data" | jq '[.workers[].ok] | all')

  echo
  if [[ "$all_ok" == "true" && "$core_ok" == "true" && "$routing_ok" == "true" ]]; then
    echo "Fleet:       ALL SYSTEMS NOMINAL"
  else
    echo "Fleet:       DEGRADED"
  fi
}

cmd_self_heal() {
  need_cmd bash
  need_file "$SELF_HEAL_SCRIPT"

  local mode="${1:-audit}"

  case "$mode" in
    audit|plan|dry-run|apply) ;;
    *)
      echo "ERROR: invalid self-heal mode: $mode" >&2
      echo "Usage: $(basename "$0") self-heal [audit|plan|dry-run|apply]" >&2
      exit 2
      ;;
  esac

  bash "$SELF_HEAL_SCRIPT" "$mode"
}

cmd_validate() {
  need_cmd bash
  need_file "$VALIDATOR"
  bash "$VALIDATOR"
}

cmd_validate_smoke() {
  need_cmd bash
  need_file "$VALIDATOR"
  local worker="${1:-spot-worker-01}"
  bash "$VALIDATOR" --smoke --worker "$worker"
}

cmd_health() {
  need_cmd jq
  need_http "/health"

  print_header "spot-core /health"
  api_get "/health" | jq .

  print_header "fleet-status.json"
  if [[ -f "$FLEET_STATUS_FILE" ]]; then
    jq '{
      timestamp,
      core_health,
      routing_audit: {
        ok: .routing_audit.ok,
        primaries: .routing_audit.primaries,
        fallbacks: .routing_audit.fallbacks,
        violations: .routing_audit.violations,
        manual_overrides: .routing_audit.manual_overrides,
        window_count: .routing_audit.window_count,
        last_violation_ts: .routing_audit.last_violation_ts
      },
      hosts: (
        .hosts
        | to_entries
        | map({
            host: .key,
            ssh_ok: .value.ssh_ok,
            service_ok: .value.service_ok,
            quarantined: .value.quarantined,
            eligible: .value.eligible,
            alerts: .value.alerts,
            running_jobs: .value.running_jobs,
            load_1: .value.load_1,
            gpu_free_mb_max: .value.gpu_free_mb_max
          })
      )
    }' "$FLEET_STATUS_FILE"
  else
    echo "WARN: missing $FLEET_STATUS_FILE"
  fi

  print_header "spot-core /fleet/ping"
  api_get "/fleet/ping" | jq 'to_entries | map({
    worker: .key,
    ok: .value.ok,
    reason: .value.reason,
    primary_role: .value.primary_role,
    secondary_roles: .value.secondary_roles,
    quarantined: .value.quarantined,
    eligible: .value.eligible,
    alerts: .value.alerts,
    running_jobs: .value.running_jobs,
    watcher_running_jobs: .value.watcher_running_jobs
  })'
}

cmd_quick_health() {
  need_cmd jq
  need_http "/health"

  print_header "quick health"
  jq -n \
    --argjson health "$(api_get "/health")" \
    --argjson ping "$(api_get "/fleet/ping")" \
    --argjson audit "$(api_get "/stats/routing-audit?limit=20")" \
    --argjson endpoints "$(
      jq -n \
        --argjson items "[
          $(endpoint_result_http 'spot-core-health' 'http://127.0.0.1:8787/health'),
          $(endpoint_result_tcp 'opnsense-https' '192.168.1.1' 443),
          $(endpoint_result_tcp 'dns-core-http' '192.168.60.10' 80),
          $(endpoint_result_tcp 'starfleet-core-https' '192.168.60.20' 443),
          $(endpoint_result_tcp 'spot-ollama' '192.168.10.10' 11434)
        ]" \
        '{
          summary: {
            ok_count: ($items | map(select(.ok == true)) | length),
            fail_count: ($items | map(select(.ok != true)) | length)
          },
          items: $items
        }'
    )" \
    '{
      health: $health,
      routing_audit: {
        ok: $audit.ok,
        violations: $audit.violations,
        fallbacks: $audit.fallbacks,
        manual_overrides: $audit.manual_overrides,
        last_violation_ts: $audit.last_violation_ts
      },
      workers: (
        $ping
        | to_entries
        | map({
            worker: .key,
            ok: .value.ok,
            reason: .value.reason,
            eligible: .value.eligible,
            quarantined: .value.quarantined,
            degraded: .value.degraded,
            running_jobs: .value.running_jobs
          })
      ),
      endpoints: ($endpoints.summary + {items: $endpoints.items})
    }'
}

cmd_routing() {
  need_cmd jq
  need_http "/routing"

  print_header "role ownership"
  api_get "/routing" | jq '{
    role_owners,
    role_priority,
    priority_order,
    queue_policy,
    retry_policy,
    active_requests,
    active_gpu_requests,
    active_model_requests,
    waiting_requests,
    penalty_box
  }'
}

cmd_audit() {
  need_cmd jq
  local limit="${1:-20}"

  print_header "spot-core /stats/routing-audit"
  api_get "/stats/routing-audit?limit=${limit}" | jq '{
    ok,
    window_count,
    primaries,
    fallbacks,
    violations,
    manual_overrides,
    last_violation_ts,
    role_owners,
    by_role,
    items
  }'

  print_header "routing-audit-summary.json"
  if [[ -f "$AUDIT_SUMMARY_FILE" ]]; then
    jq . "$AUDIT_SUMMARY_FILE"
  else
    echo "WARN: missing $AUDIT_SUMMARY_FILE"
  fi

  print_header "routing-audit.jsonl tail"
  if [[ -f "$AUDIT_FILE" ]]; then
    tail -n "${limit}" "$AUDIT_FILE" | jq -R 'fromjson?'
  else
    echo "WARN: missing $AUDIT_FILE"
  fi
}

cmd_net_basics() {
  need_cmd jq

  print_header "current network basics"
  jq -n '{
    gateway_firewall: {
      host: "opnsense",
      ip: "192.168.1.1",
      role: "router/firewall/gateway/vpn"
    },
    dns: {
      primary: "192.168.60.10",
      secondary: "192.168.60.20",
      domain: "starfleet.local"
    },
    ntp: {
      primary: "192.168.60.20",
      backup: "192.168.60.10"
    },
    vpn: {
      wireguard_gateway: "10.6.0.1",
      remote_admin_subnet: "10.6.0.0/24"
    },
    infrastructure: [
      {
        host: "dns-core",
        ip: "192.168.60.10",
        zone: "bridge",
        role: "Primary DNS / AdGuard"
      },
      {
        host: "starfleet-core",
        ip: "192.168.60.20",
        zone: "bridge",
        role: "NPM + UniFi + secondary DNS + NTP"
      }
    ],
    engineering: [
      {
        host: "spot",
        ip: "192.168.10.10",
        zone: "engineering",
        role: "primary orchestrator"
      },
      {
        host: "m-5",
        ip: "192.168.10.11",
        zone: "engineering",
        role: "worker"
      },
      {
        host: "readyroom",
        ip: "192.168.10.12",
        zone: "engineering",
        role: "interface / dashboard"
      },
      {
        host: "daystrom",
        ip: "192.168.10.13",
        zone: "engineering",
        role: "worker"
      }
    ],
    section_31: [
      {
        host: "starfleet-tower",
        ip: "192.168.30.5",
        zone: "section_31",
        role: "Homarr / Portainer / Uptime Kuma / Glances / Netdata"
      }
    ],
    storage: [
      {
        host: "unimatrix6",
        ip: "192.168.50.10",
        zone: "unimatrix",
        role: "NAS / storage"
      }
    ],
    management: [
      {
        host: "Ogre PC",
        ip: "192.168.99.150",
        zone: "command",
        role: "admin workstation"
      }
    ],
    reverse_proxy: [
      {
        name: "adguard2.starfleet.local",
        target: "192.168.60.20:8443"
      },
      {
        name: "adguard1.starfleet.local",
        target: "192.168.60.10:80"
      },
      {
        name: "dashboard.starfleet.local",
        target: "192.168.30.5:7575"
      }
    ],
    cleanup_targets: [
      "192.168.1.11 -> old dns-core2 (remove)",
      "192.168.1.133 -> old AdGuard (remove)",
      "192.168.1.148 -> old UniFi (remove)"
    ],
    note: "Current mode is basic working network state; full firewall/policy build-out is not yet complete."
  }'
}

cmd_endpoints() {
  need_cmd jq
  need_cmd curl
  need_cmd timeout
  need_cmd bash

  print_header "endpoint checks"
  jq -n \
    --argjson items "[
      $(endpoint_result_http 'spot-core-health' 'http://127.0.0.1:8787/health'),
      $(endpoint_result_tcp 'opnsense-https' '192.168.1.1' 443),
      $(endpoint_result_tcp 'dns-core-http' '192.168.60.10' 80),
      $(endpoint_result_tcp 'starfleet-core-https' '192.168.60.20' 443),
      $(endpoint_result_tcp 'spot-ollama' '192.168.10.10' 11434),
      $(endpoint_result_tcp 'starfleet-tower-homarr' '192.168.30.5' 7575),
      $(endpoint_result_tcp 'unimatrix6-nfs' '192.168.50.10' 2049)
    ]" \
    '{
      summary: {
        ok_count: ($items | map(select(.ok == true)) | length),
        fail_count: ($items | map(select(.ok != true)) | length)
      },
      items: $items
    }'
}

cmd_dns_check() {
  need_cmd jq
  if ! command -v dig >/dev/null 2>&1 && ! command -v nslookup >/dev/null 2>&1; then
    echo "ERROR: dns-check requires dig or nslookup" >&2
    exit 2
  fi

  print_header "dns checks"
  jq -n \
    --argjson items "[
      $(dns_record_check '192.168.60.10' 'adguard1.starfleet.local' '192.168.60.10'),
      $(dns_record_check '192.168.60.20' 'adguard1.starfleet.local' '192.168.60.10'),
      $(dns_record_check '192.168.60.10' 'adguard2.starfleet.local' '192.168.60.20'),
      $(dns_record_check '192.168.60.20' 'adguard2.starfleet.local' '192.168.60.20'),
      $(dns_record_check '192.168.60.10' 'dashboard.starfleet.local' '192.168.30.5'),
      $(dns_record_check '192.168.60.20' 'dashboard.starfleet.local' '192.168.30.5')
    ]" \
    '{
      summary: {
        ok_count: ($items | map(select(.ok == true)) | length),
        fail_count: ($items | map(select(.ok != true)) | length)
      },
      items: $items
    }'
}

cmd_dns_latency() {
  need_cmd jq
  local query="${1:-google.com}"

  print_header "dns latency"
  jq -n \
    --arg query "$query" \
    --argjson items "[
      $(measure_dns_latency_item 'dns-core-primary' '192.168.60.10' "$query"),
      $(measure_dns_latency_item 'dns-core-secondary' '192.168.60.20' "$query"),
      $(measure_dns_latency_item 'cloudflare-direct' '1.1.1.1' "$query")
    ]" \
    '{
      query: $query,
      summary: {
        ok_count: ($items | map(select(.ok == true)) | length),
        fail_count: ($items | map(select(.ok != true)) | length)
      },
      items: $items
    }'
}

cmd_net_latency() {
  need_cmd jq
  need_cmd ping

  print_header "network latency"
  jq -n \
    --argjson items "[
      $(measure_ping_latency_item 'opnsense' '192.168.1.1'),
      $(measure_ping_latency_item 'dns-core' '192.168.60.10'),
      $(measure_ping_latency_item 'starfleet-core' '192.168.60.20'),
      $(measure_ping_latency_item 'unimatrix6' '192.168.50.10'),
      $(measure_ping_latency_item 'spot-worker-01' '192.168.10.10')
    ]" \
    '{
      summary: {
        ok_count: ($items | map(select(.ok == true)) | length),
        fail_count: ($items | map(select(.ok != true)) | length)
      },
      items: $items
    }'
}

cmd_reverse_proxy_check() {
  need_cmd jq
  need_cmd curl

  local items=()
  local code expected_ok note

  code=""
  expected_ok=false
  note=""

  if code="$(named_https_check 'unifi.starfleet.local' '192.168.60.20' 443 '/')"; then
    expected_ok=false
    [[ "$code" == "200" || "$code" == "302" || "$code" == "401" || "$code" == "403" ]] && expected_ok=true
    note="expected named-host proxy response for UniFi should be auth or app redirect, not root default-site behavior"
    items+=("$(jq -n \
        --arg name 'unifi.starfleet.local' \
        --arg ip '192.168.60.20' \
        --argjson port 443 \
        --arg scheme 'https' \
        --arg path '/' \
        --arg code "$code" \
        --arg note "$note" \
        --argjson expected_ok "$expected_ok" \
        '{
          name:$name,
          target_ip:$ip,
          port:$port,
          scheme:$scheme,
          path:$path,
          http_code:($code|tonumber),
          ok:$expected_ok,
          note:$note
        }')"
    )
  else
    items+=("$(jq -n \
        --arg name 'unifi.starfleet.local' \
        --arg ip '192.168.60.20' \
        --argjson port 443 \
        --arg scheme 'https' \
        --arg path '/' \
        '{
          name:$name,
          target_ip:$ip,
          port:$port,
          scheme:$scheme,
          path:$path,
          ok:false,
          detail:"named_https_request_failed"
        }')"
    )
  fi

  if code="$(named_https_check 'adguard.starfleet.local' '192.168.60.20' 443 '/')"; then
    expected_ok=false
    [[ "$code" == "200" || "$code" == "302" || "$code" == "401" || "$code" == "403" ]] && expected_ok=true
    note="expected named-host proxy response for AdGuard should be backend/app response, not root default-site behavior"
    items+=("$(jq -n \
        --arg name 'adguard.starfleet.local' \
        --arg ip '192.168.60.20' \
        --argjson port 443 \
        --arg scheme 'https' \
        --arg path '/' \
        --arg code "$code" \
        --arg note "$note" \
        --argjson expected_ok "$expected_ok" \
        '{
          name:$name,
          target_ip:$ip,
          port:$port,
          scheme:$scheme,
          path:$path,
          http_code:($code|tonumber),
          ok:$expected_ok,
          note:$note
        }')"
    )
  else
    items+=("$(jq -n \
        --arg name 'adguard.starfleet.local' \
        --arg ip '192.168.60.20' \
        --argjson port 443 \
        --arg scheme 'https' \
        --arg path '/' \
        '{
          name:$name,
          target_ip:$ip,
          port:$port,
          scheme:$scheme,
          path:$path,
          ok:false,
          detail:"named_https_request_failed"
        }')"
    )
  fi

  if code="$(named_https_check 'dashboard.starfleet.local' '192.168.60.20' 443 '/')"; then
    expected_ok=false
    [[ "$code" == "200" || "$code" == "301" || "$code" == "302" || "$code" == "307" || "$code" == "308" ]] && expected_ok=true
    note="expected dashboard path should resolve through proxy and may redirect to /board"
    items+=("$(jq -n \
        --arg name 'dashboard.starfleet.local' \
        --arg ip '192.168.60.20' \
        --argjson port 443 \
        --arg scheme 'https' \
        --arg path '/' \
        --arg code "$code" \
        --arg note "$note" \
        --argjson expected_ok "$expected_ok" \
        '{
          name:$name,
          target_ip:$ip,
          port:$port,
          scheme:$scheme,
          path:$path,
          http_code:($code|tonumber),
          ok:$expected_ok,
          note:$note
        }')"
    )
  else
    items+=("$(jq -n \
        --arg name 'dashboard.starfleet.local' \
        --arg ip '192.168.60.20' \
        --argjson port 443 \
        --arg scheme 'https' \
        --arg path '/' \
        '{
          name:$name,
          target_ip:$ip,
          port:$port,
          scheme:$scheme,
          path:$path,
          ok:false,
          detail:"named_https_request_failed"
        }')"
    )
  fi

  print_header "reverse proxy checks"
  jq -n \
    --argjson items "$(printf '%s\n' "${items[@]}" | jq -s '.')" \
    '{
      summary: {
        ok_count: ($items | map(select(.ok == true)) | length),
        fail_count: ($items | map(select(.ok != true)) | length)
      },
      items: $items
    }'
}

cmd_monitor_latest() {
  need_cmd jq
  need_file "$MONITOR_SUMMARY_FILE"

  local latest_line latest_json snapshot_file
  latest_line="$(tail -n 1 "$MONITOR_SUMMARY_FILE")"
  [[ -n "$latest_line" ]] || {
    echo "ERROR: no monitor summary entries found in $MONITOR_SUMMARY_FILE" >&2
    exit 2
  }

  latest_json="$(printf '%s\n' "$latest_line" | jq .)"
  snapshot_file="$(printf '%s\n' "$latest_json" | jq -r '.snapshot_file // empty')"

  print_header "latest monitor summary"
  printf '%s\n' "$latest_json"

  if [[ -n "$snapshot_file" && -f "$snapshot_file" ]]; then
    print_header "latest snapshot overview"
    jq '{
      timestamp,
      quick_health: {
        health_ok: (.quick_health.health.ok // false),
        routing_ok: (.quick_health.routing_audit.ok // false),
        endpoint_fail_count: (.quick_health.endpoints.fail_count // null)
      },
      dns_latency: {
        query: .dns_latency.query,
        fail_count: (.dns_latency.summary.fail_count // null),
        items: .dns_latency.items
      },
      net_latency: {
        fail_count: (.net_latency.summary.fail_count // null),
        items: .net_latency.items
      }
    }' "$snapshot_file"
  else
    echo "WARN: latest snapshot file missing: ${snapshot_file:-<empty>}"
  fi
}

cmd_monitor_history() {
  need_cmd jq
  need_file "$MONITOR_SUMMARY_FILE"

  local count="${1:-10}"
  print_header "monitor history"
  tail -n "$count" "$MONITOR_SUMMARY_FILE" | jq .
}

cmd_monitor_alerts() {
  need_cmd jq
  need_file "$MONITOR_SUMMARY_FILE"

  local latest_line latest_json
  latest_line="$(tail -n 1 "$MONITOR_SUMMARY_FILE")"
  [[ -n "$latest_line" ]] || {
    echo "ERROR: no monitor summary entries found in $MONITOR_SUMMARY_FILE" >&2
    exit 2
  }
  latest_json="$(printf '%s\n' "$latest_line" | jq .)"

  print_header "monitor alerts"
  jq -n \
    --argjson latest "$latest_json" \
    --argjson dns_warn_cold "$MONITOR_DNS_WARN_COLD_MS" \
    --argjson dns_alert_cold "$MONITOR_DNS_ALERT_COLD_MS" \
    --argjson dns_warn_warm "$MONITOR_DNS_WARN_WARM_MS" \
    --argjson dns_alert_warm "$MONITOR_DNS_ALERT_WARM_MS" \
    --argjson net_warn_avg "$MONITOR_NET_WARN_AVG_MS" \
    --argjson net_alert_avg "$MONITOR_NET_ALERT_AVG_MS" \
    --argjson net_warn_loss "$MONITOR_NET_WARN_LOSS_PCT" \
    --argjson net_alert_loss "$MONITOR_NET_ALERT_LOSS_PCT" \
    '
    def severity_rank($s):
      if $s == "ALERT" then 2
      elif $s == "WARN" then 1
      else 0 end;

    def mk_reason($severity; $type; $name; $message):
      {severity:$severity, type:$type, name:$name, message:$message};

    def summarize($reasons):
      if ($reasons | map(.severity == "ALERT") | any) then "ALERT"
      elif ($reasons | map(.severity == "WARN") | any) then "WARN"
      else "OK" end;

    [
      (if ($latest.health_ok // false) | not
       then mk_reason("ALERT"; "health"; "spot-core"; "spot-core /health is not ok")
       else empty end),

      (if ($latest.routing_ok // false) | not
       then mk_reason("ALERT"; "routing"; "routing-audit"; "routing audit status is not ok")
       else empty end),

      (if ($latest.routing_violations // 0) > 0
       then mk_reason("ALERT"; "routing"; "routing-audit"; ("routing violations=" + (($latest.routing_violations // 0)|tostring)))
       else empty end),

      (if ($latest.worker_fail_count // 0) > 0
       then mk_reason("ALERT"; "workers"; "fleet-workers"; ("worker_fail_count=" + (($latest.worker_fail_count // 0)|tostring)))
       else empty end),

      (if ($latest.endpoint_fail_count // 0) > 0
       then mk_reason("ALERT"; "endpoints"; "service-endpoints"; ("endpoint_fail_count=" + (($latest.endpoint_fail_count // 0)|tostring)))
       else empty end),

      (if ($latest.dns_fail_count // 0) > 0
       then mk_reason("ALERT"; "dns"; "dns-checks"; ("dns_fail_count=" + (($latest.dns_fail_count // 0)|tostring)))
       else empty end),

      (if ($latest.net_fail_count // 0) > 0
       then mk_reason("ALERT"; "network"; "net-checks"; ("net_fail_count=" + (($latest.net_fail_count // 0)|tostring)))
       else empty end),

      (($latest.dns_cold_ms // {}) | to_entries[]? | (
        if (.value >= $dns_alert_cold)
        then mk_reason("ALERT"; "dns-latency-cold"; .key; ("cold_ms=" + (.value|tostring) + " >= " + ($dns_alert_cold|tostring)))
        elif (.value >= $dns_warn_cold)
        then mk_reason("WARN"; "dns-latency-cold"; .key; ("cold_ms=" + (.value|tostring) + " >= " + ($dns_warn_cold|tostring)))
        else empty end
      )),

      (($latest.dns_warm_ms // {}) | to_entries[]? | (
        if (.value >= $dns_alert_warm)
        then mk_reason("ALERT"; "dns-latency-warm"; .key; ("warm_ms=" + (.value|tostring) + " >= " + ($dns_alert_warm|tostring)))
        elif (.value >= $dns_warn_warm)
        then mk_reason("WARN"; "dns-latency-warm"; .key; ("warm_ms=" + (.value|tostring) + " >= " + ($dns_warn_warm|tostring)))
        else empty end
      )),

      (($latest.net_avg_ms // {}) | to_entries[]? | (
        if (.value >= $net_alert_avg)
        then mk_reason("ALERT"; "net-latency"; .key; ("avg_ms=" + (.value|tostring) + " >= " + ($net_alert_avg|tostring)))
        elif (.value >= $net_warn_avg)
        then mk_reason("WARN"; "net-latency"; .key; ("avg_ms=" + (.value|tostring) + " >= " + ($net_warn_avg|tostring)))
        else empty end
      )),

      (($latest.net_loss_pct // {}) | to_entries[]? | (
        if (.value >= $net_alert_loss)
        then mk_reason("ALERT"; "net-loss"; .key; ("packet_loss_pct=" + (.value|tostring) + " >= " + ($net_alert_loss|tostring)))
        elif (.value >= $net_warn_loss)
        then mk_reason("WARN"; "net-loss"; .key; ("packet_loss_pct=" + (.value|tostring) + " >= " + ($net_warn_loss|tostring)))
        else empty end
      ))
    ] as $reasons
    | {
        timestamp: ($latest.timestamp // null),
        status: summarize($reasons),
        threshold_config: {
          dns_warn_cold_ms: $dns_warn_cold,
          dns_alert_cold_ms: $dns_alert_cold,
          dns_warn_warm_ms: $dns_warn_warm,
          dns_alert_warm_ms: $dns_alert_warm,
          net_warn_avg_ms: $net_warn_avg,
          net_alert_avg_ms: $net_alert_avg,
          net_warn_loss_pct: $net_warn_loss,
          net_alert_loss_pct: $net_alert_loss
        },
        summary: {
          total_reasons: ($reasons | length),
          alert_count: ($reasons | map(select(.severity == "ALERT")) | length),
          warn_count: ($reasons | map(select(.severity == "WARN")) | length)
        },
        reasons: $reasons,
        latest: {
          health_ok: ($latest.health_ok // null),
          routing_ok: ($latest.routing_ok // null),
          routing_violations: ($latest.routing_violations // null),
          routing_fallbacks: ($latest.routing_fallbacks // null),
          worker_fail_count: ($latest.worker_fail_count // null),
          endpoint_fail_count: ($latest.endpoint_fail_count // null),
          dns_fail_count: ($latest.dns_fail_count // null),
          net_fail_count: ($latest.net_fail_count // null),
          snapshot_file: ($latest.snapshot_file // null)
        }
      }'
}

cmd_quarantine_state() {
  need_cmd jq
  need_http "/fleet/ping"

  print_header "quarantine state"
  api_get "/fleet/ping" | jq 'to_entries | map({
    worker: .key,
    ok: .value.ok,
    reason: .value.reason,
    eligible: .value.eligible,
    quarantined: .value.quarantined,
    degraded: .value.degraded,
    degraded_reason: .value.degraded_reason,
    fallback_count_window: .value.fallback_count_window
  })'
}

cmd_remediation() {
  need_cmd jq
  need_file "$REMEDIATION_STATE_FILE"

  print_header "remediation state"
  jq 'to_entries
    | map(select(.key != "_meta"))
    | map({
        worker: .key,
        quarantined: (.value.quarantined // false),
        degraded: (.value.degraded // false),
        degraded_reason: (.value.degraded_reason // null),
        fallback_count_window: (.value.fallback_count_window // 0),
        reason: (.value.reason // null),
        last_updated_ts: (.value.last_updated_ts // null),
        since_ts: (.value.since_ts // null),
        release_ts: (.value.release_ts // null),
        last_updated_by: (.value.last_updated_by // null)
      })' "$REMEDIATION_STATE_FILE"

  print_header "remediation meta"
  jq '._meta // {}' "$REMEDIATION_STATE_FILE"
}

cmd_quarantine() {
  need_cmd jq
  local worker="${1:-}"
  local seconds="${2:-1800}"
  local reason="${3:-manual_quarantine}"

  [[ -n "$worker" ]] || {
    echo "ERROR: worker is required" >&2
    usage
    exit 2
  }

  local encoded_reason
  encoded_reason="$(urlencode "$reason")"

  print_header "quarantine ${worker}"
  api_post "/quarantine/${worker}?seconds=${seconds}&reason=${encoded_reason}" | jq .
}

cmd_release() {
  need_cmd jq
  local worker="${1:-}"

  [[ -n "$worker" ]] || {
    echo "ERROR: worker is required" >&2
    usage
    exit 2
  }

  print_header "release ${worker}"
  api_delete "/quarantine/${worker}" | jq .
}

show_log_block() {
  local label="$1"
  local file="$2"
  local lines="$3"

  print_header "${label} (${file})"
  if [[ -f "$file" ]]; then
    tail -n "$lines" "$file"
  else
    echo "WARN: missing $file"
  fi
}

cmd_alert_state() {
  need_cmd jq
  print_header "alert state"
  local file="${STATE_DIR}/history/monitor-alert-latest.json"

  if [[ -f "$file" ]]; then
    jq '{timestamp, status, summary, latest, reasons}' "$file"
  else
    echo "WARN: missing $file"
  fi
}

cmd_alert_history() {
  need_cmd jq
  local count="${1:-10}"
  local file="${STATE_DIR}/history/monitor-alert-transitions.jsonl"

  print_header "alert history (last ${count})"
  if [[ -f "$file" ]]; then
    tail -n "$count" "$file" | jq -R 'fromjson?'
  else
    echo "WARN: missing $file"
  fi
}

cmd_logs() {
  local which="${1:-both}"
  local lines="${2:-$DEFAULT_LOG_LINES}"

  case "$which" in
    watch)
      show_log_block "fleet-watch.log" "$WATCH_LOG_FILE" "$lines"
      ;;
    remediate)
      show_log_block "fleet-remediate.log" "$REMEDIATE_LOG_FILE" "$lines"
      ;;
    both)
      show_log_block "fleet-watch.log" "$WATCH_LOG_FILE" "$lines"
      show_log_block "fleet-remediate.log" "$REMEDIATE_LOG_FILE" "$lines"
      ;;
    *)
      echo "ERROR: invalid logs target: $which" >&2
      usage
      exit 2
      ;;
  esac
}

main() {
  local cmd="${1:-}"
  shift || true

  case "$cmd" in
    ask)                 bash "${BASE_DIR}/spot-client.sh" ask "$@" ;;
    propose)             bash "${BASE_DIR}/spot-client.sh" propose "$@" ;;
    proposals)           bash "${BASE_DIR}/spot-client.sh" proposals "$@" ;;
    show-proposal)       bash "${BASE_DIR}/spot-client.sh" show-proposal "$@" ;;
    approve)             bash "${BASE_DIR}/spot-client.sh" approve "$@" ;;
    reject)              bash "${BASE_DIR}/spot-client.sh" reject "$@" ;;
    generate-apply-plan) bash "${BASE_DIR}/spot-client.sh" generate-apply-plan "$@" ;;
    proposal-status)     bash "${BASE_DIR}/spot-client.sh" proposal-status "$@" ;;
    apply-plans)         bash "${BASE_DIR}/spot-client.sh" apply-plans "$@" ;;
    show-apply-plan)     bash "${BASE_DIR}/spot-client.sh" show-apply-plan "$@" ;;
    apply-plan-status)   bash "${BASE_DIR}/spot-client.sh" apply-plan-status "$@" ;;
    apply-plan-check)    bash "${BASE_DIR}/spot-client.sh" apply-plan-check "$@" ;;
    apply-plan-verify)   bash "${BASE_DIR}/spot-client.sh" apply-plan-verify "$@" ;;
    approve-apply-plan)  bash "${BASE_DIR}/spot-client.sh" approve-apply-plan "$@" ;;
    reject-apply-plan)   bash "${BASE_DIR}/spot-client.sh" reject-apply-plan "$@" ;;
    prepare-execution-handoff) bash "${BASE_DIR}/spot-client.sh" prepare-execution-handoff "$@" ;;
    execution-handoffs)        bash "${BASE_DIR}/spot-client.sh" execution-handoffs "$@" ;;
    show-execution-handoff) bash "${BASE_DIR}/spot-client.sh" show-execution-handoff "$@" ;;
    execution-handoff-status) bash "${BASE_DIR}/spot-client.sh" execution-handoff-status "$@" ;;
    execution-handoff-verify) bash "${BASE_DIR}/spot-client.sh" execution-handoff-verify "$@" ;;
    executor-preflight)  cmd_executor_preflight "$@" ;;
    executor-preflights) cmd_executor_preflights "$@" ;;
    show-executor-preflight) cmd_show_executor_preflight "$@" ;;
    verify-executor-preflight) cmd_verify_executor_preflight "$@" ;;
    executor-preflight-summary) cmd_executor_preflight_summary "$@" ;;
    backup-binding-contract) cmd_backup_binding_contract "$@" ;;
    backup-binding-contracts) cmd_backup_binding_contracts "$@" ;;
    show-backup-binding-contract) cmd_show_backup_binding_contract "$@" ;;
    verify-backup-binding-contract) cmd_verify_backup_binding_contract "$@" ;;
    backup-binding-contract-summary) cmd_backup_binding_contract_summary "$@" ;;
    backup-artifact-manifest-contract) cmd_backup_artifact_manifest_contract "$@" ;;
    backup-artifact-manifest-contracts) cmd_backup_artifact_manifest_contracts "$@" ;;
    show-backup-artifact-manifest-contract) cmd_show_backup_artifact_manifest_contract "$@" ;;
    verify-backup-artifact-manifest-contract) cmd_verify_backup_artifact_manifest_contract "$@" ;;
    generate-patch)      bash "${BASE_DIR}/spot-client.sh" generate-patch "$@" ;;
    remember)            bash "${BASE_DIR}/spot-client.sh" remember "$@" ;;
    memory)              bash "${BASE_DIR}/spot-client.sh" memory "$@" ;;
    recall)              bash "${BASE_DIR}/spot-client.sh" recall "$@" ;;
    status)              cmd_status "$@" ;;
    status-json)         cmd_status_json "$@" ;;
    validate)            cmd_validate "$@" ;;
    validate-smoke)      cmd_validate_smoke "$@" ;;
    smoke)               cmd_validate_smoke "$@" ;;
    health)              cmd_health "$@" ;;
    quick-health)        cmd_quick_health "$@" ;;
    routing)             cmd_routing "$@" ;;
    audit)               cmd_audit "$@" ;;
    self-heal)           cmd_self_heal "$@" ;;
    net-basics)          cmd_net_basics "$@" ;;
    endpoints)           cmd_endpoints "$@" ;;
    dns-check)           cmd_dns_check "$@" ;;
    dns-latency)         cmd_dns_latency "$@" ;;
    net-latency)         cmd_net_latency "$@" ;;
    reverse-proxy-check) cmd_reverse_proxy_check "$@" ;;
    monitor-latest)      cmd_monitor_latest "$@" ;;
    monitor-history)     cmd_monitor_history "$@" ;;
    monitor-alerts)      cmd_monitor_alerts "$@" ;;
    alert-state)         cmd_alert_state "$@" ;;
    alert-history)       cmd_alert_history "$@" ;;
    quarantine-state)    cmd_quarantine_state "$@" ;;
    remediation)         cmd_remediation "$@" ;;
    quarantine)          cmd_quarantine "$@" ;;
    release)             cmd_release "$@" ;;
    logs)                cmd_logs "$@" ;;
    -h|--help|"")        usage ;;
    *)
      echo "ERROR: unknown command: $cmd" >&2
      usage
      exit 2
      ;;
  esac
}

main "$@"
