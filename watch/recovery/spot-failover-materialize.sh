#!/usr/bin/env bash
set -euo pipefail

test "$(hostname)" = "spot-core-backup"

STATE_ROOT="/srv/spot-backup-data/failover-state"
STAGE_STATUS="$STATE_ROOT/stage-status.json"
MATERIALIZE_STATUS="$STATE_ROOT/materialize-status.json"

AUTHORITY="/etc/spot-failover/authority-state"

RUNTIME_RELEASE_ROOT="/srv/spot-backup-data/failover-runtime/releases"
ACTIVE_ROOT="/srv/spot-backup-data/failover-active"
ACTIVE_RELEASE_ROOT="$ACTIVE_ROOT/releases"
ACTIVE_CURRENT="$ACTIVE_ROOT/current"
ACTIVATED_MARKER="$ACTIVE_ROOT/activated"

LOCK_FILE="$STATE_ROOT/materialize.lock"

pass() {
    printf '[PASS] %s\n' "$1"
}

fail() {
    printf '[FAIL] %s\n' "$1" >&2
    exit 1
}

false_value() {
    case "${1,,}" in
        false)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

test -s "$AUTHORITY"
test -s "$STAGE_STATUS"
test ! -e "$ACTIVATED_MARKER"

grep -Eiq \
    '^(DEFAULT_STATE|STATE)=standby$' \
    "$AUTHORITY" ||
    fail "standby state is not asserted"

grep -Eiq \
    '^(AUTHORITY_HOLDER|authority_holder)=spot-core$' \
    "$AUTHORITY" ||
    fail "spot-core is not the authority holder"

grep -Eiq \
    '^MUTATION_AUTHORITY=false$' \
    "$AUTHORITY" ||
    fail "mutation authority is not disabled"

grep -Eiq \
    '^EXECUTION_ALLOWED=false$' \
    "$AUTHORITY" ||
    fail "execution authority is not disabled"

jq -e . "$STAGE_STATUS" >/dev/null

jq -e '
    def false_value:
        if type == "boolean" then
            . == false
        elif type == "string" then
            ascii_downcase == "false"
        else
            false
        end;

    def true_value:
        if type == "boolean" then
            . == true
        elif type == "string" then
            ascii_downcase == "true"
        else
            false
        end;

    (.integrity_valid | true_value) and
    (.runtime_started | false_value) and
    (.activation_authorized | false_value) and
    (.mutation_authority | false_value) and
    (.execution_allowed | false_value)
' "$STAGE_STATUS" >/dev/null ||
    fail "staged runtime is not safe to materialize"

STAGED_RELEASE="$(
    jq -r '
        .staged_release //
        .stage_path //
        .release_path //
        .release //
        empty
    ' "$STAGE_STATUS"
)"

test -n "$STAGED_RELEASE"
STAGED_RELEASE="$(readlink -f "$STAGED_RELEASE")"

case "$STAGED_RELEASE" in
    "$RUNTIME_RELEASE_ROOT"/*)
        ;;
    *)
        fail "staged release resolves outside runtime release root"
        ;;
esac

test -d "$STAGED_RELEASE"
test -d "$STAGED_RELEASE/repository"
test -d "$STAGED_RELEASE/spot-mcp"
test -s "$STAGED_RELEASE/repository/docker-compose.yml"
test -s "$STAGED_RELEASE/spot-mcp/app.py"

if [ -s "$STAGED_RELEASE/SHA256SUMS" ]; then
    (
        cd "$STAGED_RELEASE"
        sha256sum --check --quiet SHA256SUMS
    ) ||
        fail "staged release checksum validation failed"
fi

install -d \
    -m 0750 \
    -o ogre \
    -g ogre \
    "$ACTIVE_ROOT" \
    "$ACTIVE_RELEASE_ROOT"

exec 9>"$LOCK_FILE"

flock -n 9 ||
    fail "another materialization is already running"

test ! -e "$ACTIVATED_MARKER"

SOURCE_NAME="$(basename "$STAGED_RELEASE")"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET_RELEASE="$ACTIVE_RELEASE_ROOT/${SOURCE_NAME}-${STAMP}"

test ! -e "$TARGET_RELEASE"

TEMP_RELEASE="$(
    mktemp -d \
        "$ACTIVE_RELEASE_ROOT/.materialize.XXXXXX"
)"

cleanup() {
    if [ -n "${TEMP_RELEASE:-}" ] &&
       [ -d "$TEMP_RELEASE" ]; then
        rm -rf -- "$TEMP_RELEASE"
    fi
}

trap cleanup EXIT

cp -a \
    --reflink=auto \
    "$STAGED_RELEASE/." \
    "$TEMP_RELEASE/"

chown -R ogre:ogre "$TEMP_RELEASE"
chmod -R u+rwX "$TEMP_RELEASE"

test -d "$TEMP_RELEASE/repository"
test -d "$TEMP_RELEASE/spot-mcp"
test -s "$TEMP_RELEASE/repository/docker-compose.yml"
test -s "$TEMP_RELEASE/spot-mcp/app.py"

mv "$TEMP_RELEASE" "$TARGET_RELEASE"
TEMP_RELEASE=""

NEXT_CURRENT="$ACTIVE_ROOT/.current-${STAMP}"

ln -s "$TARGET_RELEASE" "$NEXT_CURRENT"
mv -Tf "$NEXT_CURRENT" "$ACTIVE_CURRENT"

project_path() {
    local projection="$1"
    local target="$2"
    local expected_suffix="$3"
    local old_target=""
    local temporary=""

    if [ -e "$projection" ] || [ -L "$projection" ]; then
        test -L "$projection" ||
            fail "$projection exists and is not a symbolic link"

        old_target="$(readlink -f "$projection")"

        case "$old_target" in
            "$ACTIVE_RELEASE_ROOT"/*/"$expected_suffix")
                ;;
            *)
                fail "$projection resolves outside managed active releases"
                ;;
        esac
    fi

    temporary="${projection}.module8-${STAMP}"

    test ! -e "$temporary"
    test ! -L "$temporary"

    ln -s "$target" "$temporary"
    chown -h ogre:ogre "$temporary"
    mv -Tf "$temporary" "$projection"

    test "$(readlink -f "$projection")" = "$target"
}

project_path \
    /home/ogre/spot-stack \
    "$TARGET_RELEASE/repository" \
    repository

project_path \
    /home/ogre/spot-mcp \
    "$TARGET_RELEASE/spot-mcp" \
    spot-mcp

test ! -e "$ACTIVATED_MARKER"

STATUS_TEMP="$STATE_ROOT/.materialize-status-${STAMP}.json"

jq -n \
    --arg generated_at "$(
        date -u +%Y-%m-%dT%H:%M:%SZ
    )" \
    --arg hostname "$(hostname)" \
    --arg source_release "$STAGED_RELEASE" \
    --arg active_release "$TARGET_RELEASE" \
    --arg stack_projection \
        "$(readlink -f /home/ogre/spot-stack)" \
    --arg mcp_projection \
        "$(readlink -f /home/ogre/spot-mcp)" \
    '{
        schema_version: 1,
        generated_at: $generated_at,
        hostname: $hostname,
        mode: "materialized-standby",
        source_release: $source_release,
        active_release: $active_release,
        projections: {
            spot_stack: $stack_projection,
            spot_mcp: $mcp_projection
        },
        integrity_valid: true,
        mutable_instance_ready: true,
        runtime_started: false,
        activation_marker_present: false,
        activation_authorized: false,
        mutation_authority: false,
        execution_allowed: false,
        automatic_takeover_enabled: false
    }' > "$STATUS_TEMP"

install \
    -o ogre \
    -g ogre \
    -m 0640 \
    "$STATUS_TEMP" \
    "$MATERIALIZE_STATUS"

rm -f "$STATUS_TEMP"

printf 'source_release=%s\n' "$STAGED_RELEASE"
printf 'active_release=%s\n' "$TARGET_RELEASE"
printf 'spot_stack=%s\n' \
    "$(readlink -f /home/ogre/spot-stack)"
printf 'spot_mcp=%s\n' \
    "$(readlink -f /home/ogre/spot-mcp)"

pass "fresh mutable activation instance created"
pass "Spot Stack and MCP projections installed"
pass "runtime remains stopped"
pass "activation authority remains disabled"
pass "no activation marker was created"
