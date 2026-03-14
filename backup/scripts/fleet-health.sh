#!/usr/bin/env bash
set -u

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
BASE_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
DISPATCH_HELPER="${DISPATCH_HELPER:-$BASE_DIR/fleet-dispatch-probes}"

GATEWAY_HEALTH_URL="${GATEWAY_HEALTH_URL:-http://127.0.0.1:8798/health}"
GATEWAY_GPU_STATUS_URL="${GATEWAY_GPU_STATUS_URL:-http://127.0.0.1:8798/cluster/gpu_status}"
SPOT_WORKER_HEALTH_URL="${SPOT_WORKER_HEALTH_URL:-http://127.0.0.1:8797/health}"
READYROOM_HEALTH_URL="${READYROOM_HEALTH_URL:-http://192.168.10.12:8790/health}"

CURL_BIN="${CURL_BIN:-curl}"
JQ_BIN="${JQ_BIN:-jq}"

HOT_TEMP_C="${HOT_TEMP_C:-70}"
LOW_VRAM_MB="${LOW_VRAM_MB:-2048}"
HIGH_POWER_W="${HIGH_POWER_W:-170}"

c_reset=$'\033[0m'
c_green=$'\033[0;32m'
c_yellow=$'\033[1;33m'
c_red=$'\033[0;31m'

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

print_header() {
  printf '\n===============================\n'
  printf ' STARFLEET CLUSTER STATUS\n'
  printf '===============================\n\n'
}

health_label() {
  local url="$1"
  if "$CURL_BIN" -fsS --connect-timeout 2 --max-time 4 "$url" >/dev/null 2>&1; then
    printf '%bOK%b' "$c_green" "$c_reset"
  else
    printf '%bDOWN%b' "$c_red" "$c_reset"
  fi
}

show_core_services() {
  printf 'Core Services\n'
  printf '%-18s %s\n' "spot gateway"  "$(health_label "$GATEWAY_HEALTH_URL")"
  printf '%-18s %s\n' "spot worker"   "$(health_label "$SPOT_WORKER_HEALTH_URL")"
  printf '%-18s %s\n' "readyroom-ui"  "$(health_label "$READYROOM_HEALTH_URL")"
  printf '\n'
}

fetch_gpu_json() {
  "$CURL_BIN" -fsS --connect-timeout 2 --max-time 5 "$GATEWAY_GPU_STATUS_URL" 2>/dev/null
}

show_workers() {
  printf 'Workers\n'
  printf '%s\n' '-------------------------------'

  if ! need_cmd "$CURL_BIN" || ! need_cmd "$JQ_BIN"; then
    printf '%bWARN%b   curl and jq are required for worker inventory\n\n' "$c_yellow" "$c_reset"
    return 0
  fi

  local json
  json=$(fetch_gpu_json) || {
    printf '%bWARN%b   could not read worker GPU telemetry from gateway\n\n' "$c_yellow" "$c_reset"
    return 0
  }

  local lines
  lines=$(printf '%s' "$json" | "$JQ_BIN" -r '
    .workers
    | to_entries[]
    | .key as $worker
    | (.value.selected_gpu // {}) as $gpu
    | [
        $worker,
        ($gpu.name // "-"),
        (($gpu.vram_free_mb // 0) | tostring),
        (($gpu.vram_total_mb // 0) | tostring),
        (($gpu.temp_c // "-") | tostring),
        (($gpu.power_w // "-") | tostring)
      ]
    | @tsv
  ' 2>/dev/null)

  if [[ -z "$lines" ]]; then
    printf '%bWARN%b   gateway answered, but GPU payload shape changed\n\n' "$c_yellow" "$c_reset"
    return 0
  fi

  while IFS=$'\t' read -r name gpu free total temp power; do
    if [[ "$total" =~ ^[0-9]+$ && "$free" =~ ^[0-9]+$ && "$total" != "0" ]]; then
      printf '%-15s %-28s %5s/%-5s MB free   %sC  %sW\n' "$name" "$gpu" "$free" "$total" "$temp" "$power"
    else
      printf '%-15s %-28s %s\n' "$name" "$gpu" 'telemetry unavailable'
    fi
  done <<< "$lines"

  printf '\n'
}

show_cluster_load() {
  printf 'Cluster Load\n'
  printf '%s\n' '-------------------------------'

  if ! need_cmd "$CURL_BIN" || ! need_cmd "$JQ_BIN"; then
    printf '%bWARN%b   curl and jq are required for cluster load\n\n' "$c_yellow" "$c_reset"
    return 0
  fi

  local json
  json=$(fetch_gpu_json) || {
    printf '%bWARN%b   could not read cluster load from gateway\n\n' "$c_yellow" "$c_reset"
    return 0
  }

  local exec_count free_total total_total best_fit best_free hottest hottest_temp highest_draw highest_power
  exec_count=$(printf '%s' "$json" | "$JQ_BIN" -r '[.workers | to_entries[] | select(.key | endswith("_exec"))] | length')
  free_total=$(printf '%s' "$json" | "$JQ_BIN" -r '[.workers | to_entries[] | select(.key | endswith("_exec")) | (.value.selected_gpu.vram_free_mb // 0)] | add // 0')
  total_total=$(printf '%s' "$json" | "$JQ_BIN" -r '[.workers | to_entries[] | select(.key | endswith("_exec")) | (.value.selected_gpu.vram_total_mb // 0)] | add // 0')
  best_fit=$(printf '%s' "$json" | "$JQ_BIN" -r '[.workers | to_entries[] | select(.key | endswith("_exec")) | {name: .key, free: (.value.selected_gpu.vram_free_mb // 0)}] | sort_by(.free) | reverse | .[0].name // "-"')
  best_free=$(printf '%s' "$json" | "$JQ_BIN" -r '[.workers | to_entries[] | select(.key | endswith("_exec")) | {name: .key, free: (.value.selected_gpu.vram_free_mb // 0)}] | sort_by(.free) | reverse | .[0].free // 0')
  hottest=$(printf '%s' "$json" | "$JQ_BIN" -r '[.workers | to_entries[] | select(.key | endswith("_exec")) | {name: .key, temp: ((.value.selected_gpu.temp_c // "0") | tonumber)}] | sort_by(.temp) | reverse | .[0].name // "-"')
  hottest_temp=$(printf '%s' "$json" | "$JQ_BIN" -r '[.workers | to_entries[] | select(.key | endswith("_exec")) | {name: .key, temp: ((.value.selected_gpu.temp_c // "0") | tonumber)}] | sort_by(.temp) | reverse | .[0].temp // 0')
  highest_draw=$(printf '%s' "$json" | "$JQ_BIN" -r '[.workers | to_entries[] | select(.key | endswith("_exec")) | {name: .key, power: ((.value.selected_gpu.power_w // "0") | tonumber)}] | sort_by(.power) | reverse | .[0].name // "-"')
  highest_power=$(printf '%s' "$json" | "$JQ_BIN" -r '[.workers | to_entries[] | select(.key | endswith("_exec")) | {name: .key, power: ((.value.selected_gpu.power_w // "0") | tonumber)}] | sort_by(.power) | reverse | .[0].power // 0')

  printf '%-17s %s workers\n' 'exec pool:' "$exec_count"
  printf '%-17s %s/%s MB\n' 'free VRAM total:' "$free_total" "$total_total"
  printf '%-17s %s (%s MB free)\n' 'best fit now:' "$best_fit" "$best_free"
  printf '%-17s %s (%sC)\n' 'hottest exec:' "$hottest" "$hottest_temp"
  printf '%-17s %s (%.2fW)\n' 'highest draw:' "$highest_draw" "$highest_power"
  printf '\n'
}

show_heartbeat() {
  printf 'Heartbeat\n'
  printf '%s\n' '-------------------------------'

  if [[ ! -x "$DISPATCH_HELPER" ]]; then
    printf '%bWARN%b   missing dispatch helper: %s\n\n' "$c_yellow" "$c_reset" "$DISPATCH_HELPER"
    return 0
  fi

  FLEET_PROBES_ONLY=heartbeat "$DISPATCH_HELPER" | sed '/^Dispatch test$/d;/^-------------------------------$/d' || true
  printf '\n'
}

show_warnings() {
  printf 'Warnings\n'
  printf '%s\n' '-------------------------------'

  if ! need_cmd "$CURL_BIN" || ! need_cmd "$JQ_BIN"; then
    printf '%bWARN%b   curl and jq are required for warnings\n\n' "$c_yellow" "$c_reset"
    return 0
  fi

  local json warnings
  json=$(fetch_gpu_json) || {
    printf '%bWARN%b   could not read telemetry for warnings\n\n' "$c_yellow" "$c_reset"
    return 0
  }

  warnings=$(printf '%s' "$json" | "$JQ_BIN" -r --argjson hot "$HOT_TEMP_C" --argjson low "$LOW_VRAM_MB" --argjson power "$HIGH_POWER_W" '
    [
      .workers | to_entries[] |
      .key as $name |
      (.value.selected_gpu // {}) as $gpu |
      (
        ($gpu.vram_free_mb // 0) as $free |
        ($gpu.vram_total_mb // 0) as $total |
        (($gpu.temp_c // "0") | tonumber) as $temp |
        (($gpu.power_w // "0") | tonumber) as $watts |
        [
          if ($total > 0 and $free < $low) then "WARN   \($name) low free VRAM: \($free) MB" else empty end,
          if ($temp >= $hot) then "WARN   \($name) high temp: \($temp)C" else empty end,
          if ($watts >= $power) then "WARN   \($name) high power draw: \($watts)W" else empty end
        ][]
      )
    ] | .[]
  ' 2>/dev/null)

  if [[ -z "$warnings" ]]; then
    printf 'none\n\n'
  else
    printf '%s\n\n' "$warnings"
  fi
}

show_dispatch() {
  if [[ -x "$DISPATCH_HELPER" ]]; then
    "$DISPATCH_HELPER"
  else
    printf 'Dispatch test\n'
    printf '%s\n' '-------------------------------'
    printf '%bWARN%b   missing dispatch helper: %s\n' "$c_yellow" "$c_reset" "$DISPATCH_HELPER"
  fi
  printf '===============================\n\n'
}

print_header
show_core_services
show_workers
show_cluster_load
show_heartbeat
show_warnings
show_dispatch
