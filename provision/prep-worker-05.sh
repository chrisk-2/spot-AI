#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "target=spot-worker-05"
echo "role=review"
echo "script=$ROOT/provision/provision-worker.sh"

exec "$ROOT/provision/provision-worker.sh" spot-worker-05 "$@"
