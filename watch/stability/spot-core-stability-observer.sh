#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

STATE_DIR="${STATE_DIR:-/var/lib/spot/stability-soak}"
BASELINE="${BASELINE:-$STATE_DIR/baseline.json}"
LATEST="${LATEST:-$STATE_DIR/latest.json}"
SAMPLES="${SAMPLES:-$STATE_DIR/samples.jsonl}"
LOCK="${LOCK:-$STATE_DIR/observer.lock}"

CONTAINER="${CONTAINER:-spot-core}"
LEASE="${LEASE:-/var/lib/spot-failover-primary/witness-lease.json}"
FENCE_FILE="${FENCE_FILE:-/var/lib/spot-failover-primary/fenced}"

SOAK_SECONDS="${SOAK_SECONDS:-604800}"

mkdir -p "$STATE_DIR"
chmod 700 "$STATE_DIR"

exec 9>"$LOCK"

if ! flock -n 9; then
    echo "observer_already_running=true"
    exit 0
fi

for COMMAND in \
    curl \
    date \
    docker \
    jq \
    systemctl \
    timeout
do
    command -v "$COMMAND" >/dev/null 2>&1 || {
        echo "[FAIL] Missing command: $COMMAND" >&2
        exit 2
    }
done

TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
NOW_EPOCH="$(date -u +%s)"

INSPECT="$(docker inspect "$CONTAINER")"

CONTAINER_ID="$(jq -r '.[0].Id' <<<"$INSPECT")"
CONTAINER_CREATED="$(jq -r '.[0].Created' <<<"$INSPECT")"
CONTAINER_STARTED="$(jq -r '.[0].State.StartedAt' <<<"$INSPECT")"
CONTAINER_RUNNING="$(jq -r '.[0].State.Running' <<<"$INSPECT")"
CONTAINER_RESTARTS="$(jq -r '.[0].RestartCount' <<<"$INSPECT")"
CONTAINER_OOM="$(jq -r '.[0].State.OOMKilled' <<<"$INSPECT")"

DOCKER_RESTARTS="$(
    systemctl show docker.service \
        --property=NRestarts \
        --value
)"

DOCKER_STARTED="$(
    systemctl show docker.service \
        --property=ExecMainStartTimestamp \
        --value
)"

MCP_ACTIVE="$(
    systemctl is-active spot-mcp.service 2>/dev/null ||
    true
)"

MCP_RESTARTS="$(
    systemctl show spot-mcp.service \
        --property=NRestarts \
        --value
)"

MCP_STARTED="$(
    systemctl show spot-mcp.service \
        --property=ExecMainStartTimestamp \
        --value
)"

BRIDGE_ACTIVE="$(
    systemctl is-active spot-bridge-api.service 2>/dev/null ||
    true
)"

BRIDGE_RESTARTS="$(
    systemctl show spot-bridge-api.service \
        --property=NRestarts \
        --value
)"

BRIDGE_STARTED="$(
    systemctl show spot-bridge-api.service \
        --property=ExecMainStartTimestamp \
        --value
)"

CORE_CODE="$(
    curl \
        --silent \
        --output /dev/null \
        --write-out '%{http_code}' \
        --connect-timeout 3 \
        --max-time 10 \
        http://127.0.0.1:8787/health ||
    true
)"

BRIDGE_CODE="$(
    curl \
        --silent \
        --output /dev/null \
        --write-out '%{http_code}' \
        --connect-timeout 3 \
        --max-time 10 \
        http://127.0.0.1:8010/health ||
    true
)"

COLLECTIVE_ACCESSIBLE=false

if timeout 10 stat /mnt/collective >/dev/null 2>&1; then
    COLLECTIVE_ACCESSIBLE=true
fi

PRIMARY_FENCED=false

if test -f "$FENCE_FILE"; then
    PRIMARY_FENCED=true
fi

LEASE_VALID=false
LEASE_ENFORCED=false
COMMAND_AUTHORITY=false
MUTATION_AUTHORITY=true
EXECUTION_ALLOWED=true
AUTOMATIC_TAKEOVER=true
LEASE_HOLDER="unknown"

if test -s "$LEASE" && jq empty "$LEASE" >/dev/null 2>&1; then
    LEASE_HOLDER="$(jq -r '.holder // "unknown"' "$LEASE")"
    LEASE_VALID="$(jq -r '.lease_valid // false' "$LEASE")"
    LEASE_ENFORCED="$(jq -r '.lease_enforced // false' "$LEASE")"
    COMMAND_AUTHORITY="$(jq -r '.command_authority // false' "$LEASE")"
    MUTATION_AUTHORITY="$(jq -r 'if has("mutation_authority") then .mutation_authority else true end' "$LEASE")"
    EXECUTION_ALLOWED="$(jq -r 'if has("execution_allowed") then .execution_allowed else true end' "$LEASE")"
    AUTOMATIC_TAKEOVER="$(
        jq -r 'if has("automatic_takeover_enabled") then .automatic_takeover_enabled else true end' "$LEASE"
    )"
fi

CURRENT="$(mktemp "$STATE_DIR/current.XXXXXX")"

jq -n \
    --arg timestamp "$TIMESTAMP" \
    --argjson observed_epoch "$NOW_EPOCH" \
    --arg container_id "$CONTAINER_ID" \
    --arg container_created "$CONTAINER_CREATED" \
    --arg container_started "$CONTAINER_STARTED" \
    --argjson container_running "$CONTAINER_RUNNING" \
    --argjson container_restart_count "$CONTAINER_RESTARTS" \
    --argjson container_oom_killed "$CONTAINER_OOM" \
    --argjson docker_restart_count "$DOCKER_RESTARTS" \
    --arg docker_started "$DOCKER_STARTED" \
    --arg mcp_active "$MCP_ACTIVE" \
    --argjson mcp_restart_count "$MCP_RESTARTS" \
    --arg mcp_started "$MCP_STARTED" \
    --arg bridge_active "$BRIDGE_ACTIVE" \
    --argjson bridge_restart_count "$BRIDGE_RESTARTS" \
    --arg bridge_started "$BRIDGE_STARTED" \
    --arg core_http_code "$CORE_CODE" \
    --arg bridge_http_code "$BRIDGE_CODE" \
    --argjson collective_accessible "$COLLECTIVE_ACCESSIBLE" \
    --argjson primary_fenced "$PRIMARY_FENCED" \
    --arg lease_holder "$LEASE_HOLDER" \
    --argjson lease_valid "$LEASE_VALID" \
    --argjson lease_enforced "$LEASE_ENFORCED" \
    --argjson command_authority "$COMMAND_AUTHORITY" \
    --argjson mutation_authority "$MUTATION_AUTHORITY" \
    --argjson execution_allowed "$EXECUTION_ALLOWED" \
    --argjson automatic_takeover_enabled "$AUTOMATIC_TAKEOVER" \
    '{
        timestamp: $timestamp,
        observed_epoch: $observed_epoch,
        container: {
            id: $container_id,
            created_at: $container_created,
            started_at: $container_started,
            running: $container_running,
            restart_count: $container_restart_count,
            oom_killed: $container_oom_killed
        },
        docker: {
            restart_count: $docker_restart_count,
            started_at: $docker_started
        },
        services: {
            spot_mcp: {
                active: $mcp_active,
                restart_count: $mcp_restart_count,
                started_at: $mcp_started
            },
            spot_bridge_api: {
                active: $bridge_active,
                restart_count: $bridge_restart_count,
                started_at: $bridge_started
            }
        },
        endpoints: {
            spot_core_http_code: $core_http_code,
            spot_bridge_http_code: $bridge_http_code
        },
        storage: {
            collective_accessible: $collective_accessible
        },
        governance: {
            primary_fenced: $primary_fenced,
            lease_holder: $lease_holder,
            lease_valid: $lease_valid,
            lease_enforced: $lease_enforced,
            command_authority: $command_authority,
            mutation_authority: $mutation_authority,
            execution_allowed: $execution_allowed,
            automatic_takeover_enabled: $automatic_takeover_enabled
        }
    }' > "$CURRENT"

if ! test -f "$BASELINE"; then
    DEADLINE_EPOCH="$((NOW_EPOCH + SOAK_SECONDS))"
    DEADLINE_UTC="$(
        date -u \
            -d "@$DEADLINE_EPOCH" \
            +%Y-%m-%dT%H:%M:%SZ
    )"

    jq \
        --argjson start_epoch "$NOW_EPOCH" \
        --argjson deadline_epoch "$DEADLINE_EPOCH" \
        --arg deadline_utc "$DEADLINE_UTC" \
        --argjson required_seconds "$SOAK_SECONDS" \
        '. + {
            soak: {
                start_epoch: $start_epoch,
                start_utc: .timestamp,
                deadline_epoch: $deadline_epoch,
                deadline_utc: $deadline_utc,
                required_seconds: $required_seconds
            }
        }' "$CURRENT" > "$BASELINE"

    chmod 600 "$BASELINE"
fi

START_EPOCH="$(jq -r '.soak.start_epoch' "$BASELINE")"
DEADLINE_EPOCH="$(jq -r '.soak.deadline_epoch' "$BASELINE")"
ELAPSED_SECONDS="$((NOW_EPOCH - START_EPOCH))"
REMAINING_SECONDS="$((DEADLINE_EPOCH - NOW_EPOCH))"

if test "$REMAINING_SECONDS" -lt 0; then
    REMAINING_SECONDS=0
fi

REASONS="$(mktemp "$STATE_DIR/reasons.XXXXXX")"
: > "$REASONS"

add_reason() {
    printf '%s\n' "$1" >> "$REASONS"
}

BASELINE_CONTAINER_ID="$(jq -r '.container.id' "$BASELINE")"
BASELINE_CONTAINER_RESTARTS="$(
    jq -r '.container.restart_count' "$BASELINE"
)"
BASELINE_DOCKER_RESTARTS="$(
    jq -r '.docker.restart_count' "$BASELINE"
)"
BASELINE_MCP_RESTARTS="$(
    jq -r '.services.spot_mcp.restart_count' "$BASELINE"
)"
BASELINE_BRIDGE_RESTARTS="$(
    jq -r '.services.spot_bridge_api.restart_count' "$BASELINE"
)"

test "$CONTAINER_ID" = "$BASELINE_CONTAINER_ID" ||
add_reason "spot_core_container_identity_changed"

test "$CONTAINER_RESTARTS" -eq "$BASELINE_CONTAINER_RESTARTS" ||
add_reason "spot_core_restart_count_changed"

test "$DOCKER_RESTARTS" -eq "$BASELINE_DOCKER_RESTARTS" ||
add_reason "docker_restart_count_changed"

test "$MCP_RESTARTS" -eq "$BASELINE_MCP_RESTARTS" ||
add_reason "spot_mcp_restart_count_changed"

test "$BRIDGE_RESTARTS" -eq "$BASELINE_BRIDGE_RESTARTS" ||
add_reason "spot_bridge_restart_count_changed"

test "$CONTAINER_RUNNING" = "true" ||
add_reason "spot_core_not_running"

test "$CONTAINER_OOM" = "false" ||
add_reason "spot_core_oom_killed"

test "$MCP_ACTIVE" = "active" ||
add_reason "spot_mcp_not_active"

test "$BRIDGE_ACTIVE" = "active" ||
add_reason "spot_bridge_not_active"

test "$CORE_CODE" = "200" ||
add_reason "spot_core_health_failed"

case "$BRIDGE_CODE" in
    200|404)
        ;;
    *)
        add_reason "spot_bridge_endpoint_failed"
        ;;
esac

test "$COLLECTIVE_ACCESSIBLE" = "true" ||
add_reason "collective_storage_unavailable"

test "$PRIMARY_FENCED" = "false" ||
add_reason "primary_fenced"

test "$LEASE_HOLDER" = "spot-core" ||
add_reason "lease_holder_changed"

test "$LEASE_VALID" = "true" ||
add_reason "lease_invalid"

test "$LEASE_ENFORCED" = "true" ||
add_reason "lease_not_enforced"

test "$COMMAND_AUTHORITY" = "true" ||
add_reason "command_authority_lost"

test "$MUTATION_AUTHORITY" = "false" ||
add_reason "mutation_authority_enabled"

test "$EXECUTION_ALLOWED" = "false" ||
add_reason "execution_allowed_enabled"

test "$AUTOMATIC_TAKEOVER" = "false" ||
add_reason "automatic_takeover_enabled"

REASON_COUNT="$(
    sed '/^[[:space:]]*$/d' "$REASONS" |
    wc -l
)"

PREVIOUS_FAILURE_COUNT=0

if test -f "$LATEST"; then
    PREVIOUS_FAILURE_COUNT="$(
        jq -r '.soak.failure_sample_count // 0' "$LATEST"
    )"
fi

FAILURE_SAMPLE_COUNT="$PREVIOUS_FAILURE_COUNT"

if test "$REASON_COUNT" -gt 0; then
    FAILURE_SAMPLE_COUNT="$((FAILURE_SAMPLE_COUNT + 1))"
fi

STATUS="SOAKING"

if test "$FAILURE_SAMPLE_COUNT" -gt 0; then
    STATUS="FAIL"
elif test "$NOW_EPOCH" -ge "$DEADLINE_EPOCH"; then
    STATUS="PASS"
fi

REASONS_JSON="$(
    sed '/^[[:space:]]*$/d' "$REASONS" |
    jq -R . |
    jq -s .
)"

OUTPUT="$(mktemp "$STATE_DIR/latest.XXXXXX")"

jq \
    --arg status "$STATUS" \
    --argjson elapsed_seconds "$ELAPSED_SECONDS" \
    --argjson remaining_seconds "$REMAINING_SECONDS" \
    --argjson failure_sample_count "$FAILURE_SAMPLE_COUNT" \
    --argjson reasons "$REASONS_JSON" \
    --arg baseline_file "$BASELINE" \
    '. + {
        soak: {
            status: $status,
            elapsed_seconds: $elapsed_seconds,
            remaining_seconds: $remaining_seconds,
            failure_sample_count: $failure_sample_count,
            reasons: $reasons,
            baseline_file: $baseline_file
        }
    }' "$CURRENT" > "$OUTPUT"

chmod 600 "$OUTPUT"
mv -f "$OUTPUT" "$LATEST"

jq -c . "$LATEST" >> "$SAMPLES"
chmod 600 "$SAMPLES"

rm -f "$CURRENT" "$REASONS"

jq '{
    timestamp,
    status: .soak.status,
    elapsed_seconds: .soak.elapsed_seconds,
    remaining_seconds: .soak.remaining_seconds,
    failure_sample_count: .soak.failure_sample_count,
    reasons: .soak.reasons,
    container_id: .container.id,
    container_restart_count: .container.restart_count,
    docker_restart_count: .docker.restart_count,
    spot_core_http_code: .endpoints.spot_core_http_code,
    spot_mcp_active: .services.spot_mcp.active,
    spot_bridge_active: .services.spot_bridge_api.active,
    collective_accessible: .storage.collective_accessible,
    primary_fenced: .governance.primary_fenced,
    execution_allowed: .governance.execution_allowed,
    mutation_authority: .governance.mutation_authority
}' "$LATEST"

echo "RESULT: SPOT CORE STABILITY SAMPLE RECORDED"
exit 0
