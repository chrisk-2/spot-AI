#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-status}"
REASON="${2:-operator-request}"

STATE_ROOT="/srv/spot-backup-data/failover-state"
ACTIVE_ROOT="/srv/spot-backup-data/failover-active"
ACTIVATED_MARKER="$ACTIVE_ROOT/activated"
CURRENT_LINK="$ACTIVE_ROOT/current"

AUTHORITY_DIR="/etc/spot-failover"
AUTHORITY_STATE="$AUTHORITY_DIR/authority-state"

MATERIALIZE_STATUS="$STATE_ROOT/materialize-status.json"
REPLICA_STATUS="$STATE_ROOT/replica-status.json"
CONTROL_STATUS="$STATE_ROOT/backup-control-status.json"
CONTROL_HISTORY="$STATE_ROOT/backup-control-history.jsonl"

COMPOSE_FILE="/home/ogre/spot-stack/docker-compose.yml"
LOCK="/run/lock/spot-backup-control.lock"

MCP_UNIT="spot-backup-mcp.service"
BRIDGE_UNIT="spot-backup-bridge-api.service"

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

witness_command() {
    local command="$1"

    /usr/sbin/runuser \
        -u ogre \
        -- \
        /usr/bin/ssh \
        -F /dev/null \
        -i /home/ogre/.ssh/spot_witness_backup_lease \
        -o IdentityAgent=none \
        -o IdentitiesOnly=yes \
        -o BatchMode=yes \
        -o ConnectTimeout=5 \
        -o StrictHostKeyChecking=yes \
        -o UserKnownHostsFile=/home/ogre/.ssh/known_hosts \
        -n \
        spot-lease-backup@192.168.60.20 \
        "$command"
}

validate_backup_lease() {
    local payload="$1"
    local now_epoch expires_epoch

    now_epoch="$(date -u +%s)"
    expires_epoch="$(jq -r '.expires_epoch // 0' <<<"$payload")"

    case "$expires_epoch" in
        ''|*[!0-9]*) return 1 ;;
    esac

    jq -e '
        .schema == "spot_failover_authority_lease_v1" and
        .witness == "starfleet-core" and
        .holder == "spot-core-backup" and
        .lease_valid == true and
        .lease_enforced == true and
        .command_authority == true and
        .automatic_takeover_enabled == false and
        .mutation_authority == false and
        .execution_allowed == false
    ' <<<"$payload" >/dev/null

    [ "$expires_epoch" -gt "$((now_epoch + 10))" ]
}

write_authority_state() {
    local state="$1"
    local holder="$2"
    local mutation="$3"
    local execution="$4"
    local activation="$5"
    local reason="$6"
    local temporary

    install -d -o root -g root -m 0755 "$AUTHORITY_DIR"

    temporary="$(
        mktemp "$AUTHORITY_DIR/.authority-state.XXXXXX"
    )"

    {
        printf 'state=%s\n' "$state"
        printf 'authority_holder=%s\n' "$holder"
        printf 'mutation_authority=%s\n' "$mutation"
        printf 'execution_allowed=%s\n' "$execution"
        printf 'activation_authorized=%s\n' "$activation"
        printf 'automatic_takeover_enabled=false\n'
        printf 'reason=%s\n' "$reason"
        printf 'updated_at=%s\n' "$(timestamp)"
    } > "$temporary"

    chmod 0644 "$temporary"
    chown root:root "$temporary"
    mv -f "$temporary" "$AUTHORITY_STATE"
}

write_control_status() {
    local mode="$1"
    local result="$2"
    local reason="$3"
    local witness_holder="${4:-unknown}"
    local temporary marker_present container_running
    local mcp_active bridge_active

    marker_present="$(boolean test -e "$ACTIVATED_MARKER")"
    container_running="$(
        boolean docker inspect \
            --format='{{.State.Running}}' \
            spot-core
    )"
    mcp_active="$(boolean systemctl is-active --quiet "$MCP_UNIT")"
    bridge_active="$(boolean systemctl is-active --quiet "$BRIDGE_UNIT")"

    temporary="$(mktemp "$STATE_ROOT/.backup-control-status.XXXXXX")"

    jq -n \
        --arg timestamp "$(timestamp)" \
        --arg host "$(hostname)" \
        --arg mode "$mode" \
        --arg result "$result" \
        --arg reason "$reason" \
        --arg witness_holder "$witness_holder" \
        --argjson marker_present "$marker_present" \
        --argjson container_running "$container_running" \
        --argjson mcp_active "$mcp_active" \
        --argjson bridge_active "$bridge_active" \
        '{
            schema: "spot_backup_control_status_v1",
            timestamp: $timestamp,
            host: $host,
            mode: $mode,
            result: $result,
            reason: $reason,
            witness_holder: $witness_holder,
            activation_marker_present: $marker_present,
            container_running: $container_running,
            mcp_active: $mcp_active,
            bridge_active: $bridge_active,
            automatic_takeover_enabled: false,
            mutation_authority:
                ($mode == "active" and $result == "ready"),
            execution_allowed:
                ($mode == "active" and $result == "ready")
        }' > "$temporary"

    chmod 0644 "$temporary"
    chown root:root "$temporary"
    mv -f "$temporary" "$CONTROL_STATUS"

    cat "$CONTROL_STATUS" >> "$CONTROL_HISTORY"
    chmod 0644 "$CONTROL_HISTORY"

    cat "$CONTROL_STATUS"
}

remove_runtime() {
    systemctl stop "$BRIDGE_UNIT" 2>/dev/null || true
    systemctl stop "$MCP_UNIT" 2>/dev/null || true

    if docker ps -a \
        --format '{{.Names}}' |
        grep -Fxq spot-core
    then
        docker rm -f spot-core >/dev/null 2>&1 || true
    fi

    rm -f "$ACTIVATED_MARKER"
}

return_passive() {
    local reason="$1"

    remove_runtime

    write_authority_state \
        standby \
        none \
        false \
        false \
        false \
        "$reason"

    write_control_status \
        standby \
        passive \
        "$reason" \
        none
}

validate_materialization() {
    test -s "$MATERIALIZE_STATUS"
    test -s "$REPLICA_STATUS"
    test -L "$CURRENT_LINK"
    test -L /home/ogre/spot-stack
    test -L /home/ogre/spot-mcp
    test -f "$COMPOSE_FILE"
    test ! -e "$ACTIVATED_MARKER"

    jq -e '
        .integrity_valid == true and
        .projections_ready == true and
        .runtime_started == false and
        .activation_authorized == false and
        .automatic_takeover_enabled == false
    ' "$MATERIALIZE_STATUS" >/dev/null

    jq -e '
        .valid == true
    ' "$REPLICA_STATUS" >/dev/null

    docker compose \
        -f "$COMPOSE_FILE" \
        config --services |
        grep -Fx spot-core >/dev/null

    if docker ps -a \
        --format '{{.Names}}' |
        grep -Fxq spot-core
    then
        echo "standby container already exists" >&2
        return 1
    fi

    systemctl is-active --quiet "$MCP_UNIT" &&
        return 1

    systemctl is-active --quiet "$BRIDGE_UNIT" &&
        return 1

    return 0
}

create_activation_marker() {
    local witness_payload="$1"
    local temporary epoch expires_at

    epoch="$(jq -r '.epoch' <<<"$witness_payload")"
    expires_at="$(jq -r '.expires_at' <<<"$witness_payload")"

    temporary="$(mktemp "$ACTIVE_ROOT/.activated.XXXXXX")"

    jq -n \
        --arg timestamp "$(timestamp)" \
        --arg host "$(hostname)" \
        --arg epoch "$epoch" \
        --arg expires_at "$expires_at" \
        '{
            schema: "spot_backup_activation_marker_v1",
            timestamp: $timestamp,
            host: $host,
            authority_holder: "spot-core-backup",
            witness: "starfleet-core",
            witness_epoch: ($epoch | tonumber),
            lease_expires_at: $expires_at,
            activation_authorized: true,
            automatic_takeover_enabled: false,
            mutation_authority: true,
            execution_allowed: true
        }' > "$temporary"

    chmod 0644 "$temporary"
    chown root:root "$temporary"
    mv -f "$temporary" "$ACTIVATED_MARKER"
}

wait_for_url() {
    local url="$1"
    local attempts="${2:-45}"

    for attempt in $(seq 1 "$attempts")
    do
        if curl -fsS \
            --connect-timeout 2 \
            --max-time 3 \
            "$url" >/dev/null
        then
            return 0
        fi

        sleep 1
    done

    return 1
}

activate_runtime() {
    local confirmation="${2:-}"
    local witness_payload witness_holder

    if [ "$confirmation" != "OPERATOR-CONFIRMED" ]; then
        echo \
            "usage: sudo spot-backup-control activate OPERATOR-CONFIRMED" \
            >&2
        exit 2
    fi

    validate_materialization

    witness_payload="$(witness_command renew-backup)"
    validate_backup_lease "$witness_payload"

    witness_holder="$(
        jq -r '.holder' <<<"$witness_payload"
    )"

    activation_error() {
        local rc="$?"

        trap - ERR

        return_passive \
            "activation-failed-rc-$rc" \
            >/dev/null 2>&1 ||
            true

        exit "$rc"
    }

    trap activation_error ERR

    write_authority_state \
        active \
        spot-core-backup \
        true \
        true \
        true \
        operator-controlled-activation

    create_activation_marker "$witness_payload"

    docker compose \
        -f "$COMPOSE_FILE" \
        up -d --no-deps spot-core

    wait_for_url http://127.0.0.1:8787/health 45

    witness_payload="$(witness_command renew-backup)"
    validate_backup_lease "$witness_payload"

    systemctl start "$MCP_UNIT"
    systemctl start "$BRIDGE_UNIT"

    wait_for_url http://127.0.0.1:8010/healthz 30

    systemctl is-active --quiet "$MCP_UNIT"
    systemctl is-active --quiet "$BRIDGE_UNIT"

    trap - ERR

    write_control_status \
        active \
        ready \
        operator-controlled-activation \
        "$witness_holder"
}

show_status() {
    local witness_payload witness_holder witness_valid
    local marker_present container_running mcp_active bridge_active

    witness_holder=unavailable
    witness_valid=false

    if witness_payload="$(witness_command status 2>/dev/null)"; then
        witness_holder="$(
            jq -r '.holder // "unknown"' <<<"$witness_payload"
        )"

        if validate_backup_lease "$witness_payload"; then
            witness_valid=true
        fi
    fi

    marker_present="$(boolean test -e "$ACTIVATED_MARKER")"
    container_running="$(
        boolean docker inspect \
            --format='{{.State.Running}}' \
            spot-core
    )"
    mcp_active="$(boolean systemctl is-active --quiet "$MCP_UNIT")"
    bridge_active="$(boolean systemctl is-active --quiet "$BRIDGE_UNIT")"

    jq -n \
        --arg timestamp "$(timestamp)" \
        --arg host "$(hostname)" \
        --arg witness_holder "$witness_holder" \
        --argjson witness_valid "$witness_valid" \
        --argjson marker_present "$marker_present" \
        --argjson container_running "$container_running" \
        --argjson mcp_active "$mcp_active" \
        --argjson bridge_active "$bridge_active" \
        '{
            schema: "spot_backup_control_status_v1",
            timestamp: $timestamp,
            host: $host,
            witness_holder: $witness_holder,
            backup_lease_valid: $witness_valid,
            activation_marker_present: $marker_present,
            container_running: $container_running,
            mcp_active: $mcp_active,
            bridge_active: $bridge_active,
            automatic_takeover_enabled: false
        }'
}

install -d -o root -g ogre -m 0770 "$STATE_ROOT"
install -d -o root -g root -m 0755 "$ACTIVE_ROOT"

case "$ACTION" in
    activate)
        activate_runtime "$@"
        ;;

    deactivate)
        return_passive \
            "operator-controlled-deactivation:$REASON"
        ;;

    rollback)
        return_passive \
            "guarded-rollback:$REASON"
        ;;

    status)
        show_status
        ;;

    *)
        echo \
            "usage: $0 {status|activate OPERATOR-CONFIRMED|deactivate [reason]|rollback [reason]}" \
            >&2
        exit 2
        ;;
esac
