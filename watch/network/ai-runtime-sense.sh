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

resolve_ipv4() {
  local host="$1"

  getent ahostsv4 "$host" 2>/dev/null |
    awk '$1 !~ /^127\./ {print $1; exit}'
}

echo "===== SPOT AI RUNTIME SENSE ====="
echo "timestamp=$(date -Is)"
echo "observer=$(hostname)"
echo "mode=read_only"
echo "mutation_authority=false"
echo

printf '%-18s %-12s %-16s %-10s %-8s %-8s\n' \
  "WORKER" "ROLE" "ADDRESS" "OLLAMA" "MODELS" "LOADED"

printf '%-18s %-12s %-16s %-10s %-8s %-8s\n' \
  "------------------" \
  "------------" \
  "----------------" \
  "----------" \
  "--------" \
  "--------"

online=0
offline=0
model_total=0
loaded_total=0

for item in "${WORKERS[@]}"; do
  host="${item%%:*}"
  role="${item#*:}"
  address="$(resolve_ipv4 "$host")"

  if [[ -z "$address" ]]; then
    printf '%-18s %-12s %-16s %-10s %-8s %-8s\n' \
      "$host" "$role" "UNRESOLVED" "UNKNOWN" "-" "-"
    offline=$((offline + 1))
    continue
  fi

  tags="$(
    curl -sS \
      --connect-timeout 2 \
      --max-time 8 \
      "http://${address}:11434/api/tags" 2>/dev/null || true
  )"

  if [[ -z "$tags" ]]; then
    printf '%-18s %-12s %-16s %-10s %-8s %-8s\n' \
      "$host" "$role" "$address" "OFFLINE" "-" "-"
    offline=$((offline + 1))
    continue
  fi

  running="$(
    curl -sS \
      --connect-timeout 2 \
      --max-time 8 \
      "http://${address}:11434/api/ps" 2>/dev/null || true
  )"

  counts="$(
    TAGS_JSON="$tags" RUNNING_JSON="$running" python3 - <<'PY'
import json
import os

def count_items(raw: str, key: str) -> int:
    try:
        obj = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return 0

    value = obj.get(key, [])
    return len(value) if isinstance(value, list) else 0

models = count_items(os.environ.get("TAGS_JSON", ""), "models")
loaded = count_items(os.environ.get("RUNNING_JSON", ""), "models")

print(f"{models} {loaded}")
PY
  )"

  model_count="${counts%% *}"
  loaded_count="${counts##* }"

  printf '%-18s %-12s %-16s %-10s %-8s %-8s\n' \
    "$host" "$role" "$address" "ONLINE" "$model_count" "$loaded_count"

  online=$((online + 1))
  model_total=$((model_total + model_count))
  loaded_total=$((loaded_total + loaded_count))
done

echo
echo "===== LOCAL GPU STATE ====="

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi \
    --query-gpu=index,name,memory.total,memory.used,utilization.gpu,temperature.gpu \
    --format=csv,noheader 2>/dev/null || true
else
  echo "nvidia_smi=not-installed"
fi

echo
echo "===== ROUTING EXPECTATIONS ====="
echo "general=spot-worker-01"
echo "utility=spot-worker-02"
echo "coding=spot-worker-03"
echo "heavy=spot-worker-04"
echo "review=spot-worker-05"
echo "reasoning=spot-worker-06"
echo

echo "summary_workers=${#WORKERS[@]}"
echo "summary_online=${online}"
echo "summary_offline=${offline}"
echo "summary_installed_models=${model_total}"
echo "summary_loaded_models=${loaded_total}"

if (( offline == 0 )); then
  echo "overall=HEALTHY"
else
  echo "overall=DEGRADED"
fi

echo "runtime_configuration_modified=false"
echo "mutation_performed=false"
