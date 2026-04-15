#!/usr/bin/env bash
set -e
echo "=== fleet ==="
fleet
echo
echo "=== spot gateway ==="
curl -sS http://127.0.0.1:8798/health | jq .
echo
echo "=== cluster gpu status summary ==="
curl -sS http://127.0.0.1:8798/cluster/gpu_status | jq -r '
  .workers | to_entries[] |
  "\(.key): \(.value.selected_gpu.name) | free=\(.value.selected_gpu.vram_free_mb)MB | temp=\(.value.selected_gpu.temp_c)C | power=\(.value.selected_gpu.power_w)W"
'
