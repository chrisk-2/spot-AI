#!/usr/bin/env bash
set -u

WORKERS=(
  "spot-worker-01:general"
  "spot-worker-02:utility"
  "spot-worker-03:coding"
  "spot-worker-04:heavy"
  "spot-worker-05:review"
  "spot-worker-06:reasoning"
)

resolved=0
icmp_ok=0
ssh_ok=0
ollama_ok=0
warn=0

resolve_ipv4() {
  local host="$1"

  getent ahostsv4 "$host" 2>/dev/null |
    awk '$1 !~ /^127\./ {print $1; exit}'
}

port_open() {
  local address="$1"
  local port="$2"

  timeout 2 bash -c \
    "exec 3<>/dev/tcp/${address}/${port}" >/dev/null 2>&1
}

echo "===== SPOT WORKER RUNTIME SENSE ====="
echo "timestamp=$(date -Is)"
echo "observer=$(hostname)"
echo "mode=read_only"
echo "mutation_authority=false"
echo

printf '%-18s %-12s %-16s %-8s %-8s %-8s\n' \
  "WORKER" "ROLE" "ADDRESS" "ICMP" "SSH" "OLLAMA"

printf '%-18s %-12s %-16s %-8s %-8s %-8s\n' \
  "------------------" "------------" "----------------" "--------" "--------" "--------"

for item in "${WORKERS[@]}"; do
  host="${item%%:*}"
  role="${item#*:}"
  address="$(resolve_ipv4 "$host")"

  if [[ -z "$address" ]]; then
    printf '%-18s %-12s %-16s %-8s %-8s %-8s\n' \
      "$host" "$role" "UNRESOLVED" "UNKNOWN" "UNKNOWN" "UNKNOWN"

    warn=$((warn + 1))
    continue
  fi

  resolved=$((resolved + 1))

  if ping -c 1 -W 1 "$address" >/dev/null 2>&1; then
    icmp="PASS"
    icmp_ok=$((icmp_ok + 1))
  else
    icmp="WARN"
    warn=$((warn + 1))
  fi

  if port_open "$address" 22; then
    ssh="OPEN"
    ssh_ok=$((ssh_ok + 1))
  else
    ssh="CLOSED"
    warn=$((warn + 1))
  fi

  if port_open "$address" 11434; then
    ollama="OPEN"
    ollama_ok=$((ollama_ok + 1))
  else
    ollama="CLOSED"
    warn=$((warn + 1))
  fi

  printf '%-18s %-12s %-16s %-8s %-8s %-8s\n' \
    "$host" "$role" "$address" "$icmp" "$ssh" "$ollama"
done

echo
echo "===== SPOT CORE ADDRESS ====="

core_address="$(
  hostname -I 2>/dev/null |
    tr ' ' '\n' |
    awk '$1 ~ /^[0-9]+\./ && $1 !~ /^127\./ && $1 !~ /^172\./ {print; exit}'
)"

if [[ -z "$core_address" ]]; then
  core_address="$(
    ip -4 route get 1.1.1.1 2>/dev/null |
      awk '{for (i=1; i<=NF; i++) if ($i=="src") {print $(i+1); exit}}'
  )"
fi

echo "spot_core_address=${core_address:-UNKNOWN}"

echo
echo "summary_workers=${#WORKERS[@]}"
echo "summary_resolved=${resolved}"
echo "summary_icmp=${icmp_ok}"
echo "summary_ssh=${ssh_ok}"
echo "summary_ollama=${ollama_ok}"
echo "observations=${warn}"

if (( warn == 0 )); then
  echo "overall=HEALTHY"
else
  echo "overall=DEGRADED"
fi

echo "mutation_performed=false"
