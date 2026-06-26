#!/usr/bin/env bash
set -uo pipefail

IMAGE_ROOT="${IMAGE_ROOT:-/mnt/collective/starfleet-images}"
MODE="${1:-summary}"

PASS=0
WARN=0
FAIL=0

pass() { PASS=$((PASS+1)); echo "[PASS] $*"; }
warn() { WARN=$((WARN+1)); echo "[WARN] $*"; }
fail() { FAIL=$((FAIL+1)); echo "[FAIL] $*"; }

section() {
  echo
  echo "===== $* ====="
}

section "Starfleet image audit"
date -Is
echo "IMAGE_ROOT=$IMAGE_ROOT"
echo "MODE=$MODE"

section "storage"
if [ -d "$IMAGE_ROOT" ]; then
  pass "image root exists"
else
  fail "image root missing: $IMAGE_ROOT"
fi

if command -v findmnt >/dev/null 2>&1; then
  findmnt "$IMAGE_ROOT" -o SOURCE,FSTYPE,TARGET,OPTIONS 2>/dev/null || true
fi

if [ -d "$IMAGE_ROOT" ]; then
  df -hT "$IMAGE_ROOT" || true
fi

section "inventory files"
if [ -d "$IMAGE_ROOT/inventory" ]; then
  pass "inventory directory exists"
  ls -lah "$IMAGE_ROOT/inventory" || true
else
  warn "inventory directory missing"
fi

section "expected image coverage"
EXPECTED=(
  "spot-core"
  "spot-worker-01"
  "spot-worker-02"
  "spot-worker-03"
  "spot-worker-04"
  "spot-worker-05"
  "spot-worker-06"
  "opnsense"
)

for name in "${EXPECTED[@]}"; do
  if find "$IMAGE_ROOT" -mindepth 1 -maxdepth 2 -type d -iname "*${name}*" 2>/dev/null | grep -q .; then
    pass "$name image folder present"
    find "$IMAGE_ROOT" -mindepth 1 -maxdepth 2 -type d -iname "*${name}*" -printf '  %p\n' 2>/dev/null | sort
  else
    warn "$name image folder not found"
  fi
done

section "image folders"
if [ -d "$IMAGE_ROOT" ]; then
  find "$IMAGE_ROOT" -mindepth 1 -maxdepth 2 -type d 2>/dev/null | sort || true
fi

section "top-level sizes"
if [ -d "$IMAGE_ROOT" ]; then
  du -h --max-depth=1 "$IMAGE_ROOT" 2>/dev/null | sort -h || true
fi

if [ "$MODE" = "manifest" ]; then
  section "write manifest"
  mkdir -p "$IMAGE_ROOT/manifests"
  OUT="$IMAGE_ROOT/manifests/MANIFEST-$(date +%Y%m%d-%H%M%S).txt"
  {
    echo "Starfleet image manifest"
    date -Is
    echo "IMAGE_ROOT=$IMAGE_ROOT"
    echo
    echo "Mount:"
    findmnt "$IMAGE_ROOT" -o SOURCE,FSTYPE,TARGET,OPTIONS 2>/dev/null || true
    echo
    echo "Disk usage:"
    df -hT "$IMAGE_ROOT" || true
    echo
    echo "Directories:"
    find "$IMAGE_ROOT" -mindepth 1 -maxdepth 3 -type d 2>/dev/null | sort || true
    echo
    echo "Files:"
    find "$IMAGE_ROOT" -type f -printf '%p\t%s bytes\n' 2>/dev/null | sort || true
  } > "$OUT"
  pass "manifest written: $OUT"
fi

if [ "$MODE" = "hash" ]; then
  section "write sha256 hashes"
  mkdir -p "$IMAGE_ROOT/manifests"
  OUT="$IMAGE_ROOT/manifests/SHA256SUMS-$(date +%Y%m%d-%H%M%S).txt"
  find "$IMAGE_ROOT" -type f \
    ! -path "$IMAGE_ROOT/manifests/*" \
    -print0 2>/dev/null | sort -z | xargs -0 sha256sum > "$OUT"
  pass "hash file written: $OUT"
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
