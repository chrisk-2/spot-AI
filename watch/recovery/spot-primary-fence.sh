#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="/var/lib/spot-failover-primary"
FENCE_FILE="$STATE_DIR/fenced"
LOCK="/run/lock/spot-primary-fence.lock"
COMPOSE="/home/ogre/spot-stack/docker-compose.yml"
LEASE_RENEW="/usr/local/sbin/spot-primary-lease-renew"
LEASE_STATUS="$STATE_DIR/witness-lease.json"
LEASE_RENEW_SERVICE="spot-primary-lease-renew.service"
LEASE_RENEW_TIMER="spot-primary-lease-renew.timer"
ACTION="${1:-status}"

mkdir -p "$STATE_DIR"

exec 9>"$LOCK"
flock -x 9

write_fence_state() {
    local reason="$1"
    local temporary

    temporary="$(mktemp "$STATE_DIR/.fenced.XXXXXX")"

    printf '%s\n' \
        "state=fenced" \
        "authority_holder=none" \
        "mutation_authority=false" \
        "execution_allowed=false" \
        "reason=$reason" \
        "engaged_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        > "$temporary"

    chmod 0640 "$temporary"
    chown root:root "$temporary"
    mv -f "$temporary" "$FENCE_FILE"
}

stop_primary_executor() {
    systemctl stop "$LEASE_RENEW_TIMER" 2>/dev/null || true
    systemctl stop "$LEASE_RENEW_SERVICE" 2>/dev/null || true

    systemctl stop \
        spot-self-heal.timer \
        spot-worker-recover.timer \
        spot-core-replication.timer \
        2>/dev/null || true

    systemctl stop \
        spot-self-heal.service \
        spot-worker-recover.service \
        spot-core-replication.service \
        spot-bridge-api.service \
        spot-mcp.service \
        2>/dev/null || true

    pkill -f \
        '/home/ogre/spot-stack/watch/spot-role-revert.py' \
        2>/dev/null || true

    systemctl stop cron.service 2>/dev/null || true

    if docker inspect spot-core >/dev/null 2>&1; then
        docker update \
            --restart=no \
            spot-core \
            >/dev/null 2>&1 || true

        docker stop \
            --time 20 \
            spot-core \
            >/dev/null 2>&1 || true
    fi
}

primary_lease_is_safe() {
    local minimum_expiry

    minimum_expiry="$(( $(date -u +%s) + 20 ))"

    jq -e \
        --argjson minimum_expiry "$minimum_expiry" \
        '
        .schema == "spot_failover_authority_lease_v1" and
        .witness == "starfleet-core" and
        .holder == "spot-core" and
        .lease_valid == true and
        .lease_enforced == true and
        .command_authority == true and
        .automatic_takeover_enabled == false and
        .mutation_authority == false and
        .execution_allowed == false and
        (.expires_epoch | type) == "number" and
        .expires_epoch > $minimum_expiry
        ' \
        "$LEASE_STATUS" >/dev/null
}

start_primary_executor() {
    systemctl start cron.service || return 1

    systemctl start \
        spot-self-heal.timer \
        spot-worker-recover.timer \
        spot-core-replication.timer ||
        return 1

    if docker inspect spot-core >/dev/null 2>&1; then
        docker update \
            --restart=unless-stopped \
            spot-core \
            >/dev/null ||
            return 1
    fi

    docker compose \
        -f "$COMPOSE" \
        up -d spot-core ||
        return 1

    for attempt in $(seq 1 30); do
        if curl \
            --fail \
            --silent \
            --max-time 2 \
            http://127.0.0.1:8787/health \
            >/dev/null 2>&1; then
            break
        fi

        sleep 1
    done

    curl \
        --fail \
        --silent \
        --max-time 3 \
        http://127.0.0.1:8787/health \
        >/dev/null ||
        return 1

    systemctl start \
        spot-mcp.service \
        spot-bridge-api.service ||
        return 1
}

release_primary_executor() {
    rm -f "$FENCE_FILE" || return 1
    systemctl start "$LEASE_RENEW_TIMER" || return 1
    start_primary_executor || return 1
}

show_status() {
    if [ -e "$FENCE_FILE" ]; then
        fenced=true
    else
        fenced=false
    fi

    container_running=false
    if [ "$(
        docker inspect \
            --format '{{.State.Running}}' \
            spot-core \
            2>/dev/null ||
            echo false
    )" = true ]; then
        container_running=true
    fi

    primary_api=false
    if curl \
        --fail \
        --silent \
        --max-time 2 \
        http://127.0.0.1:8787/health \
        >/dev/null 2>&1; then
        primary_api=true
    fi

    mcp_active=false
    systemctl is-active --quiet spot-mcp.service &&
        mcp_active=true

    bridge_active=false
    systemctl is-active --quiet spot-bridge-api.service &&
        bridge_active=true

    cron_active=false
    systemctl is-active --quiet cron.service &&
        cron_active=true

    guard_timer_active=false
    systemctl is-active --quiet \
        spot-primary-fence-guard.timer &&
        guard_timer_active=true

    printf '%s\n' \
        "host=$(hostname)" \
        "fenced=$fenced" \
        "container_running=$container_running" \
        "primary_api=$primary_api" \
        "mcp_active=$mcp_active" \
        "bridge_active=$bridge_active" \
        "cron_active=$cron_active" \
        "guard_timer_active=$guard_timer_active"
}

case "$ACTION" in
    status)
        show_status
        ;;

    engage)
        write_fence_state "operator-engage"
        stop_primary_executor

        logger -t spot-primary-fence \
            "primary executor fenced"

        show_status
        ;;

    enforce)
        if [ -e "$FENCE_FILE" ]; then
            stop_primary_executor
        fi
        ;;

    release)
        if [ ! -e "$FENCE_FILE" ]; then
            echo "[FAIL] primary is not fenced" >&2
            exit 1
        fi

        if ! "$LEASE_RENEW"; then
            logger -t spot-primary-fence \
                "release denied: primary lease renewal failed"

            echo "[FAIL] primary lease renewal failed" >&2
            exit 1
        fi

        if ! primary_lease_is_safe; then
            logger -t spot-primary-fence \
                "release denied: primary lease is not safe"

            echo "[FAIL] primary lease is not safe" >&2
            exit 1
        fi

        if ! release_primary_executor; then
            write_fence_state "release-start-failed"
            stop_primary_executor

            logger -t spot-primary-fence \
                "primary release failed and fence was restored"

            echo "[FAIL] primary release failed; fence restored" >&2
            exit 1
        fi

        logger -t spot-primary-fence \
            "primary executor released with validated witness lease"

        show_status
        ;;

    *)
        echo "usage: $0 {status|engage|enforce|release}" >&2
        exit 2
        ;;
esac
