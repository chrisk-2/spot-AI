#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---check}"

ROOT="/srv/spot-backup-data/replica"
RELEASE_ROOT="$ROOT/releases"
CURRENT="$ROOT/current"
STATE_ROOT="/srv/spot-backup-data/failover-state"
STATUS="$STATE_ROOT/retention-status.json"
HISTORY="/srv/spot-backup-data/failover-history/retention-history.jsonl"
AUTHORITY="/etc/spot-failover/authority-state"
REPLICA_STATUS="$STATE_ROOT/replica-status.json"
LOCK="/run/lock/spot-replica-retention.lock"

KEEP="${SPOT_REPLICA_KEEP:-4}"
MIN_KEEP="${SPOT_REPLICA_MIN_KEEP:-4}"
DELETE_LIMIT="${SPOT_REPLICA_DELETE_LIMIT:-64}"
MAX_DISK_USED="${SPOT_REPLICA_MAX_DISK_USED:-90}"
MAX_INODE_USED="${SPOT_REPLICA_MAX_INODE_USED:-90}"

fail() {
    printf '[FAIL] %s\n' "$*" >&2
    exit 1
}

case "$MODE" in
    --check|--apply)
        ;;
    *)
        fail "usage: $0 --check|--apply"
        ;;
esac

for numeric in \
    "$KEEP" \
    "$MIN_KEEP" \
    "$DELETE_LIMIT" \
    "$MAX_DISK_USED" \
    "$MAX_INODE_USED"
do
    [[ "$numeric" =~ ^[0-9]+$ ]] ||
        fail "retention settings must be numeric"
done

((MIN_KEEP >= 4)) ||
    fail "emergency retention floor is 4 releases"

((KEEP >= MIN_KEEP)) ||
    fail "normal retention must not be below the emergency floor"

((DELETE_LIMIT >= 1 && DELETE_LIMIT <= 256)) ||
    fail "delete limit must be between 1 and 256"

((MAX_DISK_USED >= 50 && MAX_DISK_USED <= 98)) ||
    fail "disk pressure threshold must be between 50 and 98"

((MAX_INODE_USED >= 50 && MAX_INODE_USED <= 98)) ||
    fail "inode pressure threshold must be between 50 and 98"

exec 9>"$LOCK"

if ! flock -n 9; then
    echo "[PASS] retention already running"
    exit 0
fi

test -d "$ROOT" ||
    fail "missing replica root"

test -d "$RELEASE_ROOT" ||
    fail "missing release root"

test ! -L "$RELEASE_ROOT" ||
    fail "release root must not be a symlink"

RELEASE_ROOT_REAL="$(realpath -e -- "$RELEASE_ROOT")"

test "$RELEASE_ROOT_REAL" = "$RELEASE_ROOT" ||
    fail "unexpected release root resolution"

test -L "$CURRENT" ||
    fail "current replica link is missing"

CURRENT_REAL="$(readlink -f -- "$CURRENT")"

case "$CURRENT_REAL" in
    "$RELEASE_ROOT_REAL"/[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]T[0-9][0-9][0-9][0-9][0-9][0-9]Z)
        ;;
    *)
        fail "current link resolves outside the validated release tree"
        ;;
esac

test -d "$CURRENT_REAL" ||
    fail "current release target is missing"

test -s "$AUTHORITY" ||
    fail "authority state is missing"

grep -Eiq \
    '^[[:space:]]*authority_holder[[:space:]]*=[[:space:]]*"?spot-core"?[[:space:]]*$' \
    "$AUTHORITY" ||
    fail "spot-core is not the declared authority holder"

for key in \
    activation_authorized \
    mutation_authority \
    execution_allowed
do
    grep -Eiq \
        "^[[:space:]]*${key}[[:space:]]*=[[:space:]]*\"?false\"?[[:space:]]*$" \
        "$AUTHORITY" ||
        fail "$key is not explicitly false"
done

test -s "$REPLICA_STATUS" ||
    fail "replica verification status is missing"

DISK_USED_PERCENT="$(
    df --output=pcent "$ROOT" |
        awk 'END {gsub(/%/, "", $1); print $1}'
)"

INODE_USED_PERCENT="$(
    df --output=ipcent "$ROOT" |
        awk 'END {gsub(/%/, "", $1); print $1}'
)"

[[ "$DISK_USED_PERCENT" =~ ^[0-9]+$ ]] ||
    fail "unable to determine disk utilization"

[[ "$INODE_USED_PERCENT" =~ ^[0-9]+$ ]] ||
    fail "unable to determine inode utilization"

RESOURCE_PRESSURE=false

if \
    ((DISK_USED_PERCENT >= MAX_DISK_USED)) ||
    ((INODE_USED_PERCENT >= MAX_INODE_USED))
then
    RESOURCE_PRESSURE=true
fi

REPLICA_GATE="verified-status"

if jq -e \
    '(.valid // .replica_valid // false) == true' \
    "$REPLICA_STATUS" >/dev/null
then
    :
elif [ "$RESOURCE_PRESSURE" = true ]; then
    jq -e \
        '
            .manifest_valid == true and
            .checksums_valid == true and
            (.release_path | type) == "string"
        ' \
        "$REPLICA_STATUS" >/dev/null ||
        fail "no verified release is available for low-space recovery"

    RECOVERY_ANCHOR="$(jq -r '.release_path' "$REPLICA_STATUS")"

    case "$RECOVERY_ANCHOR" in
        "$RELEASE_ROOT_REAL"/[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]T[0-9][0-9][0-9][0-9][0-9][0-9]Z)
            ;;
        *)
            fail "verified recovery anchor escaped release root"
            ;;
    esac

    test -d "$RECOVERY_ANCHOR" ||
        fail "verified recovery anchor is missing"

    test ! -L "$RECOVERY_ANCHOR" ||
        fail "verified recovery anchor must not be a symlink"

    RECOVERY_ANCHOR_REAL="$(realpath -e -- "$RECOVERY_ANCHOR")"

    test "$RECOVERY_ANCHOR_REAL" = "$RECOVERY_ANCHOR" ||
        fail "verified recovery anchor resolved unexpectedly"

    REPLICA_GATE="verified-recorded-release-low-space"
else
    fail "latest replica is not verified and no resource pressure exists"
fi

declare -A PROTECTED=()
PROTECTED["$CURRENT_REAL"]=1

echo "[INFO] checking bounded protected links"

LINK_SCAN_ROOTS=(
    "$ROOT"
    "$STATE_ROOT"
)

for candidate in \
    /srv/spot-backup-data/failover-runtime \
    /srv/spot-backup-data/failover-active \
    /srv/spot-backup-data/runtime \
    /srv/spot-backup-data/stage \
    /srv/spot-backup-data/staging
do
    if [ -d "$candidate" ]; then
        LINK_SCAN_ROOTS+=("$candidate")
    fi
done

while IFS= read -r -d '' link; do
    target="$(readlink -f -- "$link" 2>/dev/null || true)"

    case "$target" in
        "$RELEASE_ROOT_REAL"/[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]T[0-9][0-9][0-9][0-9][0-9][0-9]Z)
            PROTECTED["$target"]=1
            ;;
    esac
done < <(
    find "${LINK_SCAN_ROOTS[@]}" \
        -xdev \
        -maxdepth 5 \
        \( \
            -path "$RELEASE_ROOT_REAL" -o \
            -path "$RELEASE_ROOT_REAL/*" -o \
            -path '*/releases' -o \
            -path '*/releases/*' \
        \) -prune -o \
        -type l \
        -print0
)

echo "[INFO] checking recorded release references"

while IFS= read -r referenced_release; do
    [ -n "$referenced_release" ] ||
        continue

    if [ -d "$referenced_release" ]; then
        PROTECTED["$referenced_release"]=1
    fi
done < <(
    {
        grep -RhoE \
            '/srv/spot-backup-data/replica/releases/[0-9]{8}T[0-9]{6}Z' \
            "$STATE_ROOT" \
            2>/dev/null ||
            true
    } |
        LC_ALL=C sort -u
)

ENTRIES=()

while IFS= read -r -d '' entry; do
    name="${entry##*/}"

    [[ "$name" =~ ^[0-9]{8}T[0-9]{6}Z$ ]] ||
        fail "unexpected release entry: $entry"

    test -d "$entry" ||
        fail "release entry is not a directory: $entry"

    test ! -L "$entry" ||
        fail "release entry must not be a symlink: $entry"

    ENTRIES+=("$name")
done < <(
    find "$RELEASE_ROOT_REAL" \
        -mindepth 1 \
        -maxdepth 1 \
        -print0
)

((${#ENTRIES[@]} > 0)) ||
    fail "no replica releases found"

mapfile -t RELEASES < <(
    printf '%s\n' "${ENTRIES[@]}" |
        LC_ALL=C sort
)

COUNT="${#RELEASES[@]}"
TARGET_KEEP="$KEEP"

if \
    [ "$RESOURCE_PRESSURE" = true ] &&
    ((COUNT <= KEEP))
then
    TARGET_KEEP="$MIN_KEEP"
fi

NEED=0

if ((COUNT > TARGET_KEEP)); then
    NEED=$((COUNT - TARGET_KEEP))
fi

CANDIDATES=()

for name in "${RELEASES[@]}"; do
    ((${#CANDIDATES[@]} < NEED)) ||
        break

    path="$RELEASE_ROOT_REAL/$name"

    if [[ -v "PROTECTED[$path]" ]]; then
        continue
    fi

    CANDIDATES+=("$name")

    if ((${#CANDIDATES[@]} >= DELETE_LIMIT)); then
        break
    fi
done
CURRENT_RELEASE="${CURRENT_REAL##*/}"

printf 'mode: %s\n' "$MODE"
printf 'release_count: %s\n' "$COUNT"
printf 'keep_newest: %s\n' "$KEEP"
printf 'minimum_keep: %s\n' "$MIN_KEEP"
printf 'target_keep: %s\n' "$TARGET_KEEP"
printf 'disk_used_percent: %s\n' "$DISK_USED_PERCENT"
printf 'inode_used_percent: %s\n' "$INODE_USED_PERCENT"
printf 'resource_pressure: %s\n' "$RESOURCE_PRESSURE"
printf 'replica_gate: %s\n' "$REPLICA_GATE"
printf 'current_release: %s\n' "$CURRENT_RELEASE"
printf 'eligible_this_run: %s\n' "${#CANDIDATES[@]}"

if ((${#CANDIDATES[@]} > 0)); then
    printf 'first_candidate: %s\n' "${CANDIDATES[0]}"
    printf 'last_candidate: %s\n' \
        "${CANDIDATES[$((${#CANDIDATES[@]} - 1))]}"
fi

if [ "$MODE" = "--check" ]; then
    echo "[PASS] retention safety check"
    exit 0
fi

DELETED=0

for name in "${CANDIDATES[@]}"; do
    expected="$RELEASE_ROOT_REAL/$name"

    [[ "$name" =~ ^[0-9]{8}T[0-9]{6}Z$ ]] ||
        fail "candidate name failed final validation"

    test -d "$expected" ||
        fail "candidate disappeared before deletion: $expected"

    test ! -L "$expected" ||
        fail "candidate became a symlink: $expected"

    resolved="$(realpath -e -- "$expected")"

    test "$resolved" = "$expected" ||
        fail "candidate resolved unexpectedly: $expected"

    case "$resolved" in
        "$RELEASE_ROOT_REAL"/[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]T[0-9][0-9][0-9][0-9][0-9][0-9]Z)
            ;;
        *)
            fail "candidate escaped release root"
            ;;
    esac

    if [[ -v "PROTECTED[$resolved]" ]]; then
        fail "candidate became protected: $resolved"
    fi

    rm -rf --one-file-system -- "$resolved"
    DELETED=$((DELETED + 1))
done

GENERATED_AT="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
REMAINING=$((COUNT - DELETED))

mkdir -p "$(dirname "$STATUS")" "$(dirname "$HISTORY")"

TMP_STATUS="$(mktemp "$STATE_ROOT/.retention-status.XXXXXX")"

jq -n \
    --arg generated_at "$GENERATED_AT" \
    --arg current_release "$CURRENT_RELEASE" \
    --arg replica_gate "$REPLICA_GATE" \
    --argjson keep_newest "$KEEP" \
    --argjson minimum_keep "$MIN_KEEP" \
    --argjson target_keep "$TARGET_KEEP" \
    --argjson delete_limit "$DELETE_LIMIT" \
    --argjson disk_used_percent "$DISK_USED_PERCENT" \
    --argjson inode_used_percent "$INODE_USED_PERCENT" \
    --argjson resource_pressure "$RESOURCE_PRESSURE" \
    --argjson deleted "$DELETED" \
    --argjson remaining "$REMAINING" \
    '{
        generated_at: $generated_at,
        result: "PASS",
        policy: "capacity-aware-protected-retention",
        current_release: $current_release,
        replica_gate: $replica_gate,
        keep_newest: $keep_newest,
        minimum_keep: $minimum_keep,
        target_keep: $target_keep,
        delete_limit: $delete_limit,
        disk_used_percent: $disk_used_percent,
        inode_used_percent: $inode_used_percent,
        resource_pressure: $resource_pressure,
        deleted_this_run: $deleted,
        remaining_releases: $remaining,
        authority_holder: "spot-core",
        activation_authorized: false,
        mutation_authority: false,
        execution_allowed: false
    }' > "$TMP_STATUS"

chmod 0644 "$TMP_STATUS"
mv -f -- "$TMP_STATUS" "$STATUS"
jq -c . "$STATUS" >> "$HISTORY"
chmod 0644 "$HISTORY"

printf 'deleted_this_run: %s\n' "$DELETED"
printf 'remaining_releases: %s\n' "$REMAINING"
echo "[PASS] replica retention completed"
