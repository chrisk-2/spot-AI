#!/usr/bin/env bash
set -euo pipefail

STATE_ROOT="/srv/spot-backup-data/failover-state"
MARKER="/srv/spot-backup-data/failover-active/activated"
AUTHORITY_STATE="/etc/spot-failover/authority-state"
STATUS="$STATE_ROOT/backup-lease-enforcement-status.json"
CONTROL="/usr/local/sbin/spot-backup-control"
RENEW="/usr/local/sbin/spot-backup-lease-renew"
LOCK="/run/lock/spot-backup-lease-enforce.lock"

exec 9>"$LOCK"
flock -x 9

timestamp() {
    date -u +%Y-%m-%dT%H:%M:%SZ
}

boolean() {
    if "$@" >/dev/null 2>&1; then
        echo true
    else
        echo false
    fi
}

write_status() {
    local result="$1"
    local reason="$2"
    local lease_valid="$3"
    local marker_present container_running mcp_active bridge_active
    local temporary

    marker_present="$(boolean test -e "$MARKER")"
    container_running="$(
        boolean docker inspect \
            --format='{{.State.Running}}' \
            spot-core
    )"
    mcp_active="$(
        boolean systemctl is-active --quiet \
            spot-backup-mcp.service
    )"
    bridge_active="$(
        boolean systemctl is-active --quiet \
            spot-backup-bridge-api.service
    )"

    temporary="$(mktemp "$STATE_ROOT/.backup-enforcement.XXXXXX")"

    jq -n \
        --arg timestamp "$(timestamp)" \
        --arg host "$(hostname)" \
        --arg result "$result" \
        --arg reason "$reason" \
        --argjson lease_valid "$lease_valid" \
        --argjson marker_present "$marker_present" \
        --argjson container_running "$container_running" \
        --argjson mcp_active "$mcp_active" \
        --argjson bridge_active "$bridge_active" \
        '{
            schema: "spot_backup_lease_enforcement_status_v1",
            timestamp: $timestamp,
            host: $host,
            result: $result,
            reason: $reason,
            backup_lease_valid: $lease_valid,
            activation_marker_present: $marker_present,
            container_running: $container_running,
            mcp_active: $mcp_active,
            bridge_active: $bridge_active,
            automatic_takeover_enabled: false
        }' > "$temporary"

    chmod 0644 "$temporary"
    chown root:root "$temporary"
    mv -f "$temporary" "$STATUS"
}

install -d -o root -g ogre -m 0770 "$STATE_ROOT"

container_running="$(
    boolean docker inspect \
        --format='{{.State.Running}}' \
        spot-core
)"
mcp_active="$(
    boolean systemctl is-active --quiet \
        spot-backup-mcp.service
)"
bridge_active="$(
    boolean systemctl is-active --quiet \
        spot-backup-bridge-api.service
)"

if [ ! -e "$MARKER" ]; then
    if [ "$container_running" = true ] ||
       [ "$mcp_active" = true ] ||
       [ "$bridge_active" = true ]; then
        "$CONTROL" \
            rollback \
            passive-runtime-detected >/dev/null

        write_status \
            rolled-back \
            passive-runtime-detected \
            false

        exit 1
    fi

    write_status \
        passive \
        activation-marker-absent \
        false

    exit 0
fi

lease_valid=false
reason=backup-lease-unavailable

if payload="$("$RENEW" --status-only 2>/dev/null)"; then
    now_epoch="$(date -u +%s)"
    expires_epoch="$(jq -r '.expires_epoch // 0' <<<"$payload")"

    case "$expires_epoch" in
        ''|*[!0-9]*) expires_epoch=0 ;;
    esac

    if jq -e '
        .schema == "spot_failover_authority_lease_v1" and
        .witness == "starfleet-core" and
        .holder == "spot-core-backup" and
        .lease_valid == true and
        .lease_enforced == true and
        .command_authority == true and
        .automatic_takeover_enabled == false and
        .mutation_authority == false and
        .execution_allowed == false
    ' <<<"$payload" >/dev/null &&
       [ "$expires_epoch" -gt "$now_epoch" ]; then
        lease_valid=true
        reason=backup-lease-valid
    fi
fi

authority_valid=false

if [ -s "$AUTHORITY_STATE" ] &&
   grep -Eiq '^(DEFAULT_STATE|STATE)=active$' \
       "$AUTHORITY_STATE" &&
   grep -Eiq \
       '^(AUTHORITY_HOLDER|authority_holder)=spot-core-backup$' \
       "$AUTHORITY_STATE" &&
   grep -Eiq '^MUTATION_AUTHORITY=true$' \
       "$AUTHORITY_STATE" &&
   grep -Eiq '^EXECUTION_ALLOWED=true$' \
       "$AUTHORITY_STATE" &&
   grep -Eiq '^ACTIVATION_AUTHORIZED=true$' \
       "$AUTHORITY_STATE" &&
   grep -Eiq '^AUTOMATIC_TAKEOVER_ENABLED=false$' \
       "$AUTHORITY_STATE"
then
    authority_valid=true
fi

if [ "$lease_valid" != true ] ||
   [ "$authority_valid" != true ] ||
   [ "$container_running" != true ] ||
   [ "$mcp_active" != true ] ||
   [ "$bridge_active" != true ]; then
    "$CONTROL" \
        rollback \
        lease-or-runtime-enforcement-failure >/dev/null

    write_status \
        rolled-back \
        lease-or-runtime-enforcement-failure \
        false

    exit 1
fi

write_status enforced "$reason" true
