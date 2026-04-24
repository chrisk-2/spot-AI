#!/usr/bin/env bash
set -euo pipefail

REPO="${HOME}/spot-stack"
STATE_FILE="$REPO/spot-core/STATE.md"
HANDOFF_FILE="$REPO/HANDOFF.md"
APP_FILE="$REPO/spot-core/spotcore/app.py"
CONFIG_FILE="$REPO/spot-core/config/cluster_config.json"
ROOT_COMPOSE="$REPO/docker-compose.yml"
CORE_COMPOSE="$REPO/spot-core/docker-compose.yml"
ROADMAP_FILE="$REPO/ROADMAP.md"

backup_status() {
    header "WORKER BACKUP STATUS"
    for h in spot-worker-01 spot-worker-02 spot-worker-03 spot-worker-04; do
        p="/mnt/collective/backups/$h/worker-config/latest/metadata.json"
        if [[ -f "$p" ]]; then
            ts=$(jq -r '.timestamp_utc' "$p" 2>/dev/null || echo unknown)
            echo "$h: OK last_backup=$ts"
        else
            echo "$h: MISSING"
        fi
    done
}

require_file() {
    local f="$1"
    if [[ ! -f "$f" ]]; then
        echo "[ERROR] Missing required file: $f" >&2
        exit 1
    fi
}

header() {
    printf '\n===== %s =====\n' "$1"
}

main() {
    cd "$REPO" || exit 1

    require_file "$HANDOFF_FILE"
    require_file "$STATE_FILE"
    require_file "$ROADMAP_FILE"
    require_file "$APP_FILE"
    require_file "$ROOT_COMPOSE"
    require_file "$CONFIG_FILE"

    header "GIT STATUS"
    git status --short

    git add "$HANDOFF_FILE" "$STATE_FILE" "$ROADMAP_FILE" "$APP_FILE" "$ROOT_COMPOSE" "$CONFIG_FILE"
    [[ -f "$CORE_COMPOSE" ]] && git add "$CORE_COMPOSE"

    header "STAGED DIFF SUMMARY"
    if git diff --cached --quiet; then
        echo "No staged changes."
    else
        git diff --cached --stat
    fi

    header "STAGED FILES"
    if git diff --cached --quiet; then
        echo "No staged files."
    else
        git diff --cached --name-only
    fi

    if git diff --cached --quiet; then
        echo "No changes to commit."
    else
        COMMIT_MSG="checkpoint: $(date '+%Y-%m-%d-%H:%M:%S')"
        git commit -m "$COMMIT_MSG"
        git push origin main
    fi

    header "CURRENT COMMIT"
    git log -1 --oneline

    header "CHECKPOINT INDEX"
    cat <<'BLOCK'
READ IN THIS ORDER NEXT CHAT:
1. /home/ogre/spot-stack/HANDOFF.md
2. /home/ogre/spot-stack/spot-core/STATE.md
3. /home/ogre/spot-stack/ROADMAP.md

NEXT CHAT DIRECTIVE:
- Read referenced files silently.
- Do not generate broad project summary.
- Assume prior architecture is accepted truth.
- Continue directly from current unresolved task.

CURRENT ACTIVE PHASE:
PHASE 1 — FINISH SPOT FOUNDATION
BLOCK

    backup_status

    header "QUICK STATUS"
    echo -n "spot-core: "
    curl -s http://127.0.0.1:8787/health 2>/dev/null | jq -r 'if .ok == true then "OK uptime_sec=\(.uptime_sec)" else "FAIL" end' || echo FAIL

    echo
    echo "worker request counts:"
    curl -s http://127.0.0.1:8787/stats/latency 2>/dev/null | jq -r 'to_entries[] | "\(.key): \(.value.count)"' || true

    header "RUNTIME HEALTH"
    curl -sS http://127.0.0.1:8787/health || true

    header "LATENCY SNAPSHOT"
    curl -sS http://127.0.0.1:8787/stats/latency | jq . 2>/dev/null || true

    header "RECENT DECISIONS"
    curl -sS http://127.0.0.1:8787/stats/recent-decisions?limit=5 | jq . 2>/dev/null || true

    header "SYSTEMD STATUS (SHORT)"
    systemctl --user --no-pager --full status spot-mcp | sed -n '1,10p' || true
    systemctl --user --no-pager --full status mcp-tunnel | sed -n '1,15p' || true

    header "DOCKER STATUS"
    docker compose ps || true

    header "NEW CHAT BLOCK"
    cat <<'BLOCK'
Read:
- /home/ogre/spot-stack/HANDOFF.md
- /home/ogre/spot-stack/spot-core/STATE.md
- /home/ogre/spot-stack/ROADMAP.md

Do not provide a comprehensive summary unless explicitly asked.
Proceed directly to the next unresolved implementation task in the active roadmap phase.
BLOCK
}

main "$@"
