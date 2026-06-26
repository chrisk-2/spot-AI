#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/ogre/spot-stack}"
RUNTIME_DIR="${RUNTIME_DIR:-/home/ogre/spot-mcp}"
USER_SYSTEMD_DIR="${USER_SYSTEMD_DIR:-/home/ogre/.config/systemd/user}"

mkdir -p "$RUNTIME_DIR" "$USER_SYSTEMD_DIR"

install -m 0644 "$REPO_ROOT/watch/mcp/spot_mcp_wrapper.py" "$RUNTIME_DIR/spot_mcp_wrapper.py"
install -m 0644 "$REPO_ROOT/watch/mcp/spot-mcp-wrapper.service" "$USER_SYSTEMD_DIR/spot-mcp-wrapper.service"

# Keep the old bad heads disabled if they exist.
systemctl --user disable --now mcp-tunnel.service 2>/dev/null || true
systemctl --user disable --now spot-mcp.service 2>/dev/null || true

systemctl --user daemon-reload
systemctl --user enable --now spot-mcp-wrapper.service

echo "===== MCP wrapper service ====="
systemctl --user status spot-mcp-wrapper.service --no-pager

echo
echo "===== MCP ports ====="
sudo ss -lntp | egrep '8000|8001|8010|8787|20241|20242' || true
