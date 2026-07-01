#!/usr/bin/env bash
set -euo pipefail

# Read-only Kea lease probe.
# Required env:
#   OPNSENSE_API_KEY
#   OPNSENSE_API_SECRET
# Optional:
#   OPNSENSE_BASE_URL=https://192.168.1.1

BASE="${OPNSENSE_BASE_URL:-https://192.168.1.1}"
ENDPOINT="/api/kea/leases/search"

if [[ -z "${OPNSENSE_API_KEY:-}" || -z "${OPNSENSE_API_SECRET:-}" ]]; then
  printf '{"ok":false,"skipped":true,"reason":"missing OPNSENSE_API_KEY or OPNSENSE_API_SECRET","endpoint":"%s"}\n' "$ENDPOINT"
  exit 0
fi

curl -skS \
  --connect-timeout 3 \
  --max-time 8 \
  -u "${OPNSENSE_API_KEY}:${OPNSENSE_API_SECRET}" \
  "${BASE}${ENDPOINT}"
printf '\n'
