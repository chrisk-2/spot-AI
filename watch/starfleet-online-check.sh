#!/usr/bin/env bash
set -u

TIMEOUT="${TIMEOUT:-2}"
WARN_MS="${WARN_MS:-5}"
MODE="${1:-table}"

BASE="$HOME/spot-stack"
LOG_DIR="$BASE/watch/logs"
STATE_DIR="$BASE/watch/state"
LOG_FILE="$LOG_DIR/starfleet-online-check.log"
JSON_FILE="$STATE_DIR/starfleet-online-check.json"
MD_FILE="$STATE_DIR/starfleet-online-check.md"

mkdir -p "$LOG_DIR" "$STATE_DIR"

RED=$'\033[31m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
NC=$'\033[0m'

HOSTS=(
  "opnsense|192.168.1.1|OPNsense|443"
  "dns-core|192.168.60.10|DNS Core|22,53"
  "starfleet-core|192.168.60.20|NPM UniFi DNS NTP|22,80,443,8443"
  "spot-core|192.168.60.30|Spot Core API|22,8787"
  "unimatrix6|192.168.50.10|NAS NFS|2049"
  "starfleet-tower|192.168.30.5|Tower|22"
  "spot-worker-01|192.168.10.10|general|22,11434"
  "spot-worker-02|192.168.10.11|utility/watcher|22,11434"
  "spot-ui-01|192.168.10.12|ui|22"
  "spot-worker-03|192.168.10.13|coding|22,11434"
  "spot-worker-04|192.168.10.14|heavy|22,11434"
  "spot-worker-05|192.168.10.15|review|22,11434"
  "spot-worker-06|192.168.10.16|reasoning|22,11434"
)

ok() { printf "%sOK%s" "$GREEN" "$NC"; }
warn() { printf "%sWARN%s" "$YELLOW" "$NC"; }
bad() { printf "%sFAIL%s" "$RED" "$NC"; }

tcp_check() {
  timeout "$TIMEOUT" bash -lc "cat < /dev/null > /dev/tcp/$1/$2" 2>/dev/null
}

latency_ms() {
  ping -c1 -W "$TIMEOUT" "$1" 2>/dev/null |
    awk -F'time=' '/time=/{print $2}' |
    awk '{print $1}'
}

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TMP_TSV="$(mktemp)"
trap 'rm -f "$TMP_TSV"' EXIT

fail=0
warns=0
total=0
ping_ok=0
svc_total=0
svc_ok=0

for entry in "${HOSTS[@]}"; do
  IFS='|' read -r name ip role ports <<<"$entry"
  total=$((total+1))

  ping="FAIL"
  latency="-"
  health="FAIL"
  services=""

  if ping -c1 -W "$TIMEOUT" "$ip" >/dev/null 2>&1; then
    ping="OK"
    ping_ok=$((ping_ok+1))
    latency="$(latency_ms "$ip")"
    [[ -z "$latency" ]] && latency="0"

    awk "BEGIN{exit !($latency > $WARN_MS)}" && health="WARN" || health="OK"
    [[ "$health" == "WARN" ]] && warns=$((warns+1))
  else
    fail=1
  fi

  IFS=',' read -ra port_arr <<<"$ports"
  for port in "${port_arr[@]}"; do
    [[ -z "$port" ]] && continue
    svc_total=$((svc_total+1))
    if tcp_check "$ip" "$port"; then
      svc_ok=$((svc_ok+1))
      services+="${port}:OK "
    else
      services+="${port}:FAIL "
      health="FAIL"
      fail=1
    fi
  done

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$name" "$ip" "$role" "$ping" "$latency" "$health" "$services" >> "$TMP_TSV"
done

python3 - "$ts" "$TMP_TSV" "$JSON_FILE" "$MD_FILE" "$total" "$ping_ok" "$svc_total" "$svc_ok" "$warns" "$fail" <<'PY'
import json, sys, pathlib

ts, tsv, json_file, md_file = sys.argv[1:5]
total, ping_ok, svc_total, svc_ok, warns, fail = map(int, sys.argv[5:11])

hosts = []
for line in pathlib.Path(tsv).read_text().splitlines():
    name, ip, role, ping, latency, health, services = line.split("\t")
    svc = {}
    for item in services.split():
        port, status = item.split(":")
        svc[port] = status
    hosts.append({
        "host": name,
        "ip": ip,
        "role": role,
        "ping": ping,
        "latency_ms": None if latency == "-" else float(latency),
        "health": health,
        "services": svc,
    })

result = "PASS" if fail == 0 and warns == 0 else ("WARN" if fail == 0 else "FAIL")
data = {
    "timestamp_utc": ts,
    "result": result,
    "summary": {
        "hosts_ping": f"{ping_ok}/{total}",
        "services": f"{svc_ok}/{svc_total}",
        "warnings": warns,
        "failures": fail,
    },
    "hosts": hosts,
}

pathlib.Path(json_file).write_text(json.dumps(data, indent=2) + "\n")

rows = [
    f"# Starfleet Online Check",
    "",
    f"- Timestamp UTC: `{ts}`",
    f"- Result: **{result}**",
    f"- Hosts ping: `{ping_ok}/{total}`",
    f"- Services: `{svc_ok}/{svc_total}`",
    f"- Warnings: `{warns}`",
    "",
    "| Host | IP | Role | Ping | Latency ms | Health | Services |",
    "|---|---:|---|---:|---:|---:|---|",
]
for h in hosts:
    svc = " ".join(f"{p}:{s}" for p, s in h["services"].items())
    rows.append(f"| {h['host']} | {h['ip']} | {h['role']} | {h['ping']} | {h['latency_ms']} | {h['health']} | `{svc}` |")
pathlib.Path(md_file).write_text("\n".join(rows) + "\n")
PY

print_table() {
  {
    echo "===== STARFLEET ONLINE CHECK $ts ====="
    printf "%-18s %-15s %-16s %-6s %-10s %-7s %s\n" "HOST" "IP" "ROLE" "PING" "LATENCY" "HEALTH" "SERVICES"

    while IFS=$'\t' read -r name ip role ping latency health services; do
      case "$ping" in OK) ping_c="$(ok)" ;; *) ping_c="$(bad)" ;; esac
      case "$health" in OK) health_c="$(ok)" ;; WARN) health_c="$(warn)" ;; *) health_c="$(bad)" ;; esac
      [[ "$latency" != "-" ]] && latency="${latency} ms"
      printf "%-27b %-15s %-16s %-15b %-10s %-16b %s\n" "$name" "$ip" "$role" "$ping_c" "$latency" "$health_c" "$services"
    done < "$TMP_TSV"

    echo
    echo "SUMMARY:"
    echo "  hosts_ping:   $ping_ok/$total"
    echo "  services:     $svc_ok/$svc_total"
    echo "  warnings:     $warns"
    echo "  json:         $JSON_FILE"
    echo "  markdown:     $MD_FILE"

    echo
    if [[ "$fail" -eq 0 && "$warns" -eq 0 ]]; then
      echo "RESULT: PASS - ALL STARFLEET SYSTEMS ONLINE"
    elif [[ "$fail" -eq 0 ]]; then
      echo "RESULT: WARN - ALL SYSTEMS ONLINE, LATENCY WARNING PRESENT"
    else
      echo "RESULT: FAIL - ONE OR MORE STARFLEET SYSTEMS NEED ATTENTION"
    fi
  } | tee -a "$LOG_FILE"
}

case "$MODE" in
  table|"")
    print_table
    ;;
  json)
    cat "$JSON_FILE"
    ;;
  md|markdown)
    cat "$MD_FILE"
    ;;
  quiet)
    cat "$JSON_FILE" >> "$LOG_FILE"
    ;;
  *)
    echo "usage: $0 [table|json|md|quiet]" >&2
    exit 2
    ;;
esac

exit "$fail"
