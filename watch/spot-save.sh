#!/usr/bin/env bash
set -euo pipefail

REPO="${HOME}/spot-stack"
STATE_FILE="$REPO/spot-core/STATE.md"
HANDOFF_FILE="$REPO/HANDOFF.md"
APP_FILE="$REPO/spot-core/spotcore/app.py"
ROOT_COMPOSE="$REPO/docker-compose.yml"
CORE_COMPOSE="$REPO/spot-core/docker-compose.yml"

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

print_file_if_exists() {
    local label="$1"
    local path="$2"

    header "$label"
    if [[ -f "$path" ]]; then
        nl -ba "$path"
    else
        echo "[SKIP] File not present: $path"
    fi
}

main() {
    cd "$REPO" || exit 1

    require_file "$HANDOFF_FILE"
    require_file "$STATE_FILE"
    require_file "$APP_FILE"

    echo "Opening STATE.md..."
    nano "$STATE_FILE"

    git add .

    if git diff --cached --quiet; then
        echo "No changes to commit."
    else
        COMMIT_MSG="checkpoint: $(date '+%Y-%m-%d-%H:%M:%S')"
        git commit -m "$COMMIT_MSG"
        git push origin main
    fi

    header "CURRENT COMMIT"
    git log -1 --oneline

    print_file_if_exists "HANDOFF.MD" "$HANDOFF_FILE"
    print_file_if_exists "STATE.MD" "$STATE_FILE"
    print_file_if_exists "APP.PY" "$APP_FILE"
    print_file_if_exists "ROOT DOCKER-COMPOSE" "$ROOT_COMPOSE"
    print_file_if_exists "SPOT-CORE DOCKER-COMPOSE" "$CORE_COMPOSE"

    header "NEW CHAT BLOCK"
    cat <<'BLOCK'
Continuing Spot bridge work.

Run first:
- spot_save
- read /home/ogre/spot-stack/HANDOFF.md
- read /home/ogre/spot-stack/spot-core/STATE.md
- read /home/ogre/spot-stack/spot-core/spotcore/app.py

Rules:
- no guessing
- read real runtime files before patching
- use runtime as source of truth
- fallback to GitHub only if runtime unavailable
- do not redesign system
- minimal changes only
- preserve auth and payload formats
- do not invent endpoints or models
- do not modify unrelated code
- enforce backup-first policy
- validate with python3 -m py_compile before restart

Task:
- read app.py
- identify EXACT /admin endpoints
- identify EXACT auth mechanism
- identify EXACT request payload structure
- THEN apply Pydantic models to those endpoints only
- do not change behavior
- enforce structure only (422 on invalid input)

Fallback rule:
If /home/ogre/spot-stack/spot-core/spotcore/app.py cannot be read:
- read from https://github.com/chrisk-2/spot-AI
- use that file ONLY

If neither is available:
- STOP

Output BEFORE patch:
1. exact /admin endpoints
2. exact auth mechanism
3. exact request fields

Then patch.
BLOCK
}

main "$@"
