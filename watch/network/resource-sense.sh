#!/usr/bin/env bash
set -u

warn=0

echo "===== SPOT HOST RESOURCE SENSE ====="
echo "timestamp=$(date -Is)"
echo "host=$(hostname)"
echo "mode=read_only"
echo "mutation_authority=false"
echo

echo "===== CPU / LOAD ====="
uptime
printf 'logical_cpus=%s\n' "$(nproc)"
printf 'load_1m=%s\n' "$(awk '{print $1}' /proc/loadavg)"
printf 'load_5m=%s\n' "$(awk '{print $2}' /proc/loadavg)"
printf 'load_15m=%s\n' "$(awk '{print $3}' /proc/loadavg)"
echo

echo "===== MEMORY ====="
free -h
echo

mem_available_kb="$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)"
mem_total_kb="$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)"

if [[ -n "$mem_available_kb" && -n "$mem_total_kb" && "$mem_total_kb" -gt 0 ]]; then
  mem_available_pct=$((mem_available_kb * 100 / mem_total_kb))
  echo "memory_available_percent=${mem_available_pct}"

  if (( mem_available_pct < 10 )); then
    echo "memory_status=WARN"
    warn=$((warn + 1))
  else
    echo "memory_status=PASS"
  fi
fi

echo
echo "===== FILESYSTEM UTILIZATION ====="
df -hPT -x tmpfs -x devtmpfs -x squashfs
echo

while read -r filesystem blocks used available capacity mountpoint; do
  pct="${capacity%\%}"

  if [[ "$pct" =~ ^[0-9]+$ ]] && (( pct >= 90 )); then
    echo "disk_warning filesystem=${filesystem} mount=${mountpoint} used=${capacity}"
    warn=$((warn + 1))
  fi
done < <(
  df -P -x tmpfs -x devtmpfs -x squashfs |
    awk 'NR > 1 {print $1, $2, $3, $4, $5, $6}'
)

echo
echo "===== INODE UTILIZATION ====="
df -hiP -x tmpfs -x devtmpfs -x squashfs
echo

while read -r filesystem inodes iused ifree capacity mountpoint; do
  pct="${capacity%\%}"

  if [[ "$pct" =~ ^[0-9]+$ ]] && (( pct >= 90 )); then
    echo "inode_warning filesystem=${filesystem} mount=${mountpoint} used=${capacity}"
    warn=$((warn + 1))
  fi
done < <(
  df -iP -x tmpfs -x devtmpfs -x squashfs |
    awk 'NR > 1 {print $1, $2, $3, $4, $5, $6}'
)

echo
echo "===== TEMPERATURES ====="

thermal_found=0

for zone in /sys/class/thermal/thermal_zone*; do
  [[ -r "$zone/temp" ]] || continue

  thermal_found=1
  type="$(cat "$zone/type" 2>/dev/null || echo unknown)"
  raw="$(cat "$zone/temp" 2>/dev/null || echo 0)"

  if [[ "$raw" =~ ^[0-9]+$ ]]; then
    awk -v t="$raw" -v type="$type" \
      'BEGIN {printf "thermal type=%s temperature_c=%.1f\n", type, t / 1000}'
  fi
done

if command -v sensors >/dev/null 2>&1; then
  thermal_found=1
  sensors 2>/dev/null || true
fi

if (( thermal_found == 0 )); then
  echo "thermal_data=unavailable"
fi

echo
echo "===== BLOCK DEVICES ====="
lsblk -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS,MODEL
echo

echo "observations=${warn}"

if (( warn == 0 )); then
  echo "overall=HEALTHY"
else
  echo "overall=DEGRADED"
fi

echo "mutation_performed=false"
