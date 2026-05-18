#!/usr/bin/env bash
set -euo pipefail

OUT="/tmp/spot-remediation-fixture.heartbeat"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

printf '{"fixture":"spot-remediation-fixture","ts":"%s","status":"ok"}\n' "$TS" > "$OUT"
cat "$OUT"
