#!/usr/bin/env bash
set -uo pipefail

PASS=0
WARN=0
FAIL=0

say() { printf '%s\n' "$*"; }
pass() { PASS=$((PASS+1)); say "[PASS] $*"; }
warn() { WARN=$((WARN+1)); say "[WARN] $*"; }
fail() { FAIL=$((FAIL+1)); say "[FAIL] $*"; }

section() {
  echo
  echo "===== $* ====="
}

have_port() {
  local port="$1"
  sudo ss -lntp 2>/dev/null | grep -qE "127\.0\.0\.1:${port}|0\.0\.0\.0:${port}|:${port}[[:space:]]"
}

http_ok() {
  local url="$1"
  curl -fsS --max-time 8 "$url" >/dev/null
}

section "time / host"
date -Is
hostname

section "git"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git status --short --branch
  git log --oneline -3
  if [ -z "$(git status --porcelain)" ]; then
    pass "repo clean"
  else
    warn "repo has uncommitted changes"
  fi
else
  warn "not inside git repo"
fi

section "core services"
if systemctl is-active --quiet cloudflared; then
  pass "cloudflared active"
else
  fail "cloudflared not active"
fi

if systemctl --user is-active --quiet spot-mcp-wrapper.service; then
  pass "spot-mcp-wrapper.service active"
else
  fail "spot-mcp-wrapper.service not active"
fi

section "ports"
if have_port 8787; then pass "core API port 8787 listening"; else fail "core API port 8787 missing"; fi
if have_port 8010; then pass "bridge API port 8010 listening"; else fail "bridge API port 8010 missing"; fi
if have_port 8000; then pass "MCP wrapper port 8000 listening"; else fail "MCP wrapper port 8000 missing"; fi
if have_port 8001; then fail "bad MCP head port 8001 is listening"; else pass "bad MCP head port 8001 absent"; fi

sudo ss -lntp | egrep '8000|8001|8010|8787|20241|20242' || true

section "HTTP health"
if http_ok http://127.0.0.1:8787/health; then
  pass "core /health OK"
else
  fail "core /health failed"
fi

if http_ok http://127.0.0.1:8010/; then
  pass "bridge root OK"
else
  fail "bridge root failed"
fi

section "MCP initialize"
MCP_JSON="$(curl -sS --max-time 10 \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Content-Type: application/json' \
  -X POST \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"project-status","version":"1.0"}}}' \
  http://127.0.0.1:8000/ 2>/dev/null || true)"

if echo "$MCP_JSON" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["result"]["serverInfo"]["name"]=="Spot MCP"' >/dev/null 2>&1; then
  pass "MCP initialize OK"
  echo "$MCP_JSON" | python3 -m json.tool
else
  fail "MCP initialize failed"
  echo "$MCP_JSON"
fi

section "fleet reachability quick check"
for h in spot-worker-01 spot-worker-02 spot-worker-03 spot-worker-04 spot-worker-05 spot-worker-06; do
  if ping -c 1 -W 1 "$h" >/dev/null 2>&1; then
    pass "$h ping OK"
  else
    warn "$h ping failed"
  fi
done

section "SSH / ollama quick check"
for h in spot-worker-01 spot-worker-02 spot-worker-03 spot-worker-04 spot-worker-05 spot-worker-06; do
  OUT="$(timeout 8s ssh -o BatchMode=yes -o ConnectTimeout=4 -o ServerAliveInterval=2 -o ServerAliveCountMax=1 "$h" 'hostname; systemctl is-active ssh || true; systemctl is-active ollama || true' 2>&1)"
  RC=$?
  echo
  echo "### $h"
  echo "$OUT"
  if [ "$RC" -eq 0 ]; then
    pass "$h ssh command OK"
  else
    warn "$h ssh failed"
  fi
done

section "image inventory"
if [ -d /mnt/collective/starfleet-images/inventory ]; then
  pass "image inventory directory exists"
  ls -lah /mnt/collective/starfleet-images/inventory
else
  warn "image inventory directory missing"
fi

section "summary"
echo "PASS=$PASS WARN=$WARN FAIL=$FAIL"

if [ "$FAIL" -eq 0 ]; then
  echo "RESULT: PASS"
  exit 0
else
  echo "RESULT: FAIL"
  exit 1
fi
