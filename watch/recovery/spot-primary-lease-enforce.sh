#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="/var/lib/spot-failover-primary"
LEASE="$STATE_DIR/witness-lease.json"
MARKER="$STATE_DIR/lease-enforcement-enabled"
STATUS="$STATE_DIR/lease-enforcement-status.json"
FENCE_FILE="$STATE_DIR/fenced"
FENCE="/usr/local/sbin/spot-primary-fence"
LOCK="/run/lock/spot-primary-lease-enforce.lock"

exec 9>"$LOCK"
flock -n 9 || exit 0

timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
now_epoch="$(date -u +%s)"

write_status() {
    local enabled="$1"
    local lease_valid="$2"
    local fenced="$3"
    local reason="$4"
    local expires_epoch="$5"

    temporary="$(mktemp "$STATE_DIR/.lease-enforcement-status.XXXXXX")"

    jq -n \
        --arg timestamp "$timestamp" \
        --arg reason "$reason" \
        --argjson enforcement_enabled "$enabled" \
        --argjson lease_valid "$lease_valid" \
        --argjson fenced "$fenced" \
        --argjson expires_epoch "$expires_epoch" \
        '{
            timestamp: $timestamp,
            host: "spot-core",
            enforcement_enabled: $enforcement_enabled,
            lease_valid: $lease_valid,
            fenced: $fenced,
            expires_epoch: $expires_epoch,
            reason: $reason,
            automatic_release_enabled: false
        }' > "$temporary"

    chmod 0640 "$temporary"
    chown root:root "$temporary"
    mv -f "$temporary" "$STATUS"
}

if [ ! -e "$MARKER" ]; then
    fenced=false
    [ -e "$FENCE_FILE" ] && fenced=true

    write_status \
        false \
        false \
        "$fenced" \
        "enforcement-marker-absent" \
        0

    exit 0
fi

if [ -e "$FENCE_FILE" ]; then
    "$FENCE" enforce

    write_status \
        true \
        false \
        true \
        "persistent-fence-already-engaged" \
        0

    exit 0
fi

lease_valid=false
reason="lease-file-unavailable"
expires_epoch=0

if [ -s "$LEASE" ] &&
   jq -e . "$LEASE" >/dev/null 2>&1; then

    holder="$(jq -r '.holder // "none"' "$LEASE")"
    witness="$(jq -r '.witness // ""' "$LEASE")"
    expires_epoch="$(jq -r '.expires_epoch // 0' "$LEASE")"
    witness_enforced="$(
        jq -r '.lease_enforced // false' "$LEASE"
    )"

    case "$expires_epoch" in
        ''|*[!0-9]*) expires_epoch=0 ;;
    esac

    if [ "$witness" != "starfleet-core" ]; then
        reason="invalid-witness-identity"
    elif [ "$witness_enforced" != true ]; then
        reason="witness-enforcement-disabled"
    elif [ "$holder" != "spot-core" ]; then
        reason="primary-does-not-hold-lease"
    elif [ "$expires_epoch" -le "$now_epoch" ]; then
        reason="primary-lease-expired"
    else
        lease_valid=true
        reason="primary-lease-valid"
    fi
fi

if [ "$lease_valid" = true ]; then
    write_status \
        true \
        true \
        false \
        "$reason" \
        "$expires_epoch"

    exit 0
fi

write_status \
    true \
    false \
    true \
    "$reason" \
    "$expires_epoch"

logger -t spot-primary-lease-enforce \
    "self-fencing primary reason=$reason"

"$FENCE" engage
