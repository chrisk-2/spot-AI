#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="/var/lib/spot/remediation-fixture"
OUT="${OUT_DIR}/heartbeat.json"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

install -d -m 0755 "$OUT_DIR"
printf '{"fixture":"spot-remediation-fixture","ts":"%s","status":"ok"}\n' "$TS" > "$OUT"
cat "$OUT"
