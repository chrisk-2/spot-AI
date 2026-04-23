#!/usr/bin/env bash
set -euo pipefail

export SPOT_BASE_URL="${SPOT_BASE_URL:-http://127.0.0.1:8787}"
export SPOT_ADMIN_TOKEN="${SPOT_ADMIN_TOKEN:-$(docker exec spot-core printenv SPOTCORE_ADMIN_API_TOKEN)}"

LOG_DIR="/home/ogre/spot-stack/watch/logs"
mkdir -p "$LOG_DIR"

exec /home/ogre/spot-stack/watch/.venv-mcp/bin/python \
  /home/ogre/spot-stack/watch/spot_mcp_server.py \
  2>>"$LOG_DIR/spot-mcp.stderr.log"
