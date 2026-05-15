#!/usr/bin/env bash
set -euo pipefail

REPO="${REPO:-$HOME/spot-stack}"
KEEP_SNAPSHOTS="${KEEP_SNAPSHOTS:-200}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

REPORT_DIR="$REPO/watch/reports"
QUAR="$REPO/watch/quarantine/$TS"
REPORT="$REPORT_DIR/cleanup-$TS.txt"

mkdir -p "$REPORT_DIR" "$QUAR"

cd "$REPO"

log() {
    echo "[$(date -u +%H:%M:%S)] $*"
}

safe_move() {
    local src="$1"

    if [[ -e "$src" ]]; then
        mkdir -p "$QUAR/$(dirname "$src")"
        mv "$src" "$QUAR/$src"
        echo "MOVED $src"
    fi
}

{
    echo "=== Spot cleanup ==="
    echo "timestamp=$TS"
    echo

    echo "## git status before"
    git status --short
    echo

    echo "## removing pycache"
    find . -type d -name '__pycache__' -prune -print -exec rm -rf {} +

    echo
    echo "## quarantining generated failure tests"

    while IFS= read -r path; do
        safe_move "$path"
    done < <(
        find watch/contracts -type d -name 'failure-tests' 2>/dev/null || true
    )

    echo
    echo "## pruning old snapshots"

    SNAP_DIR="watch/state/history/snapshots"

    if [[ -d "$SNAP_DIR" ]]; then
        mapfile -t OLD < <(
            ls -1t "$SNAP_DIR"/*.json 2>/dev/null | tail -n +"$((KEEP_SNAPSHOTS + 1))"
        )

        for f in "${OLD[@]}"; do
            safe_move "$f"
        done
    fi

    echo
    echo "## git status after"
    git status --short

} | tee "$REPORT"

echo
echo "cleanup complete"
echo "report: $REPORT"
echo "quarantine: $QUAR"
