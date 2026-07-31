#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="/var/lib/spot-failover-witness"
STATE="$STATE_DIR/authority-lease.json"
OBSERVER="$STATE_DIR/status.json"
LOCK="/run/lock/spot-witness-authority.lock"

LEASE_TTL=45
MAX_OBSERVER_AGE=45
ACTION="${1:-status}"

mkdir -p "$STATE_DIR"

exec 9>"$LOCK"
flock -x 9

initialize_state() {
    local temporary

    temporary="$(mktemp "$STATE_DIR/.authority-lease.XXXXXX")"

    jq -n \
        --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        '{
            schema: "spot_failover_authority_lease_v1",
            witness: "starfleet-core",
            preferred_holder: "spot-core",
            holder: "none",
            epoch: 1,
            issued_at: null,
            expires_at: null,
            expires_epoch: 0,
            lease_valid: false,
            lease_enforced: true,
            automatic_takeover_enabled: false,
            command_authority: false,
            mutation_authority: false,
            execution_allowed: false,
            reason: "bootstrap-monitoring-only",
            updated_at: $timestamp
        }' > "$temporary"

    chmod 0644 "$temporary"
    chown root:root "$temporary"
    mv -f "$temporary" "$STATE"
}

ensure_state() {
    if [ ! -s "$STATE" ]; then
        initialize_state
    fi

    jq -e \
        '.schema == "spot_failover_authority_lease_v1"' \
        "$STATE" >/dev/null
}

show_status() {
    local now_epoch holder expires_epoch lease_valid

    ensure_state

    now_epoch="$(date -u +%s)"
    holder="$(jq -r '.holder // "none"' "$STATE")"
    expires_epoch="$(jq -r '.expires_epoch // 0' "$STATE")"

    case "$expires_epoch" in
        ''|*[!0-9]*) expires_epoch=0 ;;
    esac

    lease_valid=false

    if [ "$holder" != "none" ] &&
       [ "$expires_epoch" -gt "$now_epoch" ]; then
        lease_valid=true
    fi

    jq \
        --arg observed_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --argjson lease_valid "$lease_valid" \
        '.lease_valid = $lease_valid |
         .command_authority = $lease_valid |
         .mutation_authority = false |
         .execution_allowed = false |
         .automatic_takeover_enabled = false |
         .observed_at = $observed_at' \
        "$STATE"
}

renew_holder() {
    local requested_holder="$1"
    local reason="$2"
    local now_epoch current_holder current_expiry epoch
    local expires_epoch issued_at expires_at temporary

    ensure_state

    now_epoch="$(date -u +%s)"
    current_holder="$(jq -r '.holder // "none"' "$STATE")"
    current_expiry="$(jq -r '.expires_epoch // 0' "$STATE")"
    epoch="$(jq -r '.epoch // 0' "$STATE")"

    case "$current_expiry" in
        ''|*[!0-9]*) current_expiry=0 ;;
    esac

    case "$epoch" in
        ''|*[!0-9]*) epoch=0 ;;
    esac

    if [ "$current_holder" != "$requested_holder" ]; then
        epoch=$((epoch + 1))
    fi

    expires_epoch=$((now_epoch + LEASE_TTL))
    issued_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    expires_at="$(
        date -u -d "@$expires_epoch" +%Y-%m-%dT%H:%M:%SZ
    )"

    temporary="$(mktemp "$STATE_DIR/.authority-lease.XXXXXX")"

    jq \
        --arg holder "$requested_holder" \
        --arg issued_at "$issued_at" \
        --arg expires_at "$expires_at" \
        --arg timestamp "$issued_at" \
        --arg reason "$reason" \
        --argjson epoch "$epoch" \
        --argjson expires_epoch "$expires_epoch" \
        '.holder = $holder |
         .epoch = $epoch |
         .issued_at = $issued_at |
         .expires_at = $expires_at |
         .expires_epoch = $expires_epoch |
         .lease_valid = true |
         .lease_enforced = true |
         .command_authority = true |
         .mutation_authority = false |
         .execution_allowed = false |
         .automatic_takeover_enabled = false |
         .reason = $reason |
         .updated_at = $timestamp' \
        "$STATE" > "$temporary"

    chmod 0644 "$temporary"
    chown root:root "$temporary"
    mv -f "$temporary" "$STATE"

    logger -t spot-witness-authority \
        "lease holder=$requested_holder epoch=$epoch reason=$reason"

    show_status
}

expire_lease() {
    local now_epoch holder expires_epoch epoch temporary

    ensure_state

    now_epoch="$(date -u +%s)"
    holder="$(jq -r '.holder // "none"' "$STATE")"
    expires_epoch="$(jq -r '.expires_epoch // 0' "$STATE")"

    case "$expires_epoch" in
        ''|*[!0-9]*) expires_epoch=0 ;;
    esac

    if [ "$holder" = "none" ] ||
       [ "$expires_epoch" -eq 0 ] ||
       [ "$expires_epoch" -gt "$now_epoch" ]; then
        exit 0
    fi

    epoch="$(jq -r '.epoch // 0' "$STATE")"

    case "$epoch" in
        ''|*[!0-9]*) epoch=0 ;;
    esac

    epoch=$((epoch + 1))
    temporary="$(mktemp "$STATE_DIR/.authority-lease.XXXXXX")"

    jq \
        --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --argjson epoch "$epoch" \
        '.holder = "none" |
         .epoch = $epoch |
         .issued_at = null |
         .expires_at = null |
         .expires_epoch = 0 |
         .lease_valid = false |
         .lease_enforced = true |
         .command_authority = false |
         .mutation_authority = false |
         .execution_allowed = false |
         .automatic_takeover_enabled = false |
         .reason = "lease-expired" |
         .updated_at = $timestamp' \
        "$STATE" > "$temporary"

    chmod 0644 "$temporary"
    chown root:root "$temporary"
    mv -f "$temporary" "$STATE"

    logger -t spot-witness-authority \
        "authority lease expired epoch=$epoch"
}

renew_primary() {
    local now_epoch current_holder current_expiry

    ensure_state

    now_epoch="$(date -u +%s)"
    current_holder="$(jq -r '.holder // "none"' "$STATE")"
    current_expiry="$(jq -r '.expires_epoch // 0' "$STATE")"

    case "$current_expiry" in
        ''|*[!0-9]*) current_expiry=0 ;;
    esac

    if [ "$current_holder" = "spot-core-backup" ] &&
       [ "$current_expiry" -gt "$now_epoch" ]; then
        echo "active backup lease prevents primary renewal" >&2
        exit 3
    fi

    renew_holder "spot-core" "primary-renewal"
}

validate_backup_grant() {
    local observer_timestamp observer_epoch now_epoch observer_age

    test -s "$OBSERVER"
    jq -e '.witness == "starfleet-core"' "$OBSERVER" >/dev/null
    jq -e '.primary.api == false' "$OBSERVER" >/dev/null
    jq -e '.backup.reachable == true' "$OBSERVER" >/dev/null
    jq -e '.takeover_candidate == true' "$OBSERVER" >/dev/null

    observer_timestamp="$(jq -r '.timestamp // ""' "$OBSERVER")"
    observer_epoch="$(
        date -u -d "$observer_timestamp" +%s 2>/dev/null ||
        echo 0
    )"
    now_epoch="$(date -u +%s)"

    [ "$observer_epoch" -gt 0 ]

    observer_age=$((now_epoch - observer_epoch))

    [ "$observer_age" -ge 0 ]
    [ "$observer_age" -le "$MAX_OBSERVER_AGE" ]
}

grant_backup() {
    if ! validate_backup_grant; then
        echo \
            "backup grant denied: fresh independent takeover evidence unavailable" \
            >&2
        exit 4
    fi

    renew_holder \
        "spot-core-backup" \
        "operator-controlled-backup-grant"
}

renew_backup() {
    local now_epoch current_holder current_expiry

    ensure_state

    now_epoch="$(date -u +%s)"
    current_holder="$(jq -r '.holder // "none"' "$STATE")"
    current_expiry="$(jq -r '.expires_epoch // 0' "$STATE")"

    case "$current_expiry" in
        ''|*[!0-9]*) current_expiry=0 ;;
    esac

    if [ "$current_holder" != "spot-core-backup" ] ||
       [ "$current_expiry" -le "$now_epoch" ]; then
        echo "backup renewal denied: no active backup lease" >&2
        exit 3
    fi

    renew_holder "spot-core-backup" "backup-renewal"
}

revoke_backup() {
    local current_holder epoch temporary

    ensure_state

    current_holder="$(jq -r '.holder // "none"' "$STATE")"

    if [ "$current_holder" = "spot-core" ]; then
        echo "backup revoke denied: primary currently holds authority" >&2
        exit 3
    fi

    epoch="$(jq -r '.epoch // 0' "$STATE")"

    case "$epoch" in
        ''|*[!0-9]*) epoch=0 ;;
    esac

    if [ "$current_holder" = "spot-core-backup" ]; then
        epoch=$((epoch + 1))
    fi

    temporary="$(mktemp "$STATE_DIR/.authority-lease.XXXXXX")"

    jq \
        --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --argjson epoch "$epoch" \
        '.holder = "none" |
         .epoch = $epoch |
         .issued_at = null |
         .expires_at = null |
         .expires_epoch = 0 |
         .lease_valid = false |
         .lease_enforced = true |
         .command_authority = false |
         .mutation_authority = false |
         .execution_allowed = false |
         .automatic_takeover_enabled = false |
         .reason = "operator-controlled-backup-revoke" |
         .updated_at = $timestamp' \
        "$STATE" > "$temporary"

    chmod 0644 "$temporary"
    chown root:root "$temporary"
    mv -f "$temporary" "$STATE"

    logger -t spot-witness-authority \
        "backup authority revoked epoch=$epoch"

    show_status
}

case "$ACTION" in
    initialize)
        ensure_state
        ;;

    status)
        show_status
        ;;

    expire)
        expire_lease
        ;;

    renew-primary)
        renew_primary
        ;;

    grant-backup)
        grant_backup
        ;;

    renew-backup)
        renew_backup
        ;;

    revoke-backup)
        revoke_backup
        ;;

    *)
        echo \
            "usage: $0 {initialize|status|expire|renew-primary|grant-backup|renew-backup|revoke-backup}" \
            >&2
        exit 2
        ;;
esac
