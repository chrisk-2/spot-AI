#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="/srv/spot-backup-data/failover-state"
OBSERVER="$STATE_DIR/observer-status.json"
REPLICA="$STATE_DIR/replica-status.json"
STATUS="$STATE_DIR/consensus-status.json"
LOCK="/run/lock/spot-failover-consensus.lock"
MAX_WITNESS_AGE=45

exec 9>"$LOCK"
flock -n 9 || exit 0

timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
witness_temp="$(mktemp)"
output_temp="$(mktemp "$STATE_DIR/.consensus-status.XXXXXX")"

cleanup() {
    rm -f "$witness_temp" "$output_temp"
}
trap cleanup EXIT

witness_available=false
witness_fresh=false
witness_identity_valid=false
witness_primary_api=false
witness_takeover_candidate=false
witness_authority_granted=false
witness_age_seconds=-1

if ssh -n \
    -o BatchMode=yes \
    -o ConnectTimeout=5 \
    spot-witness-control \
    'cat /var/lib/spot-failover-witness/status.json' \
    > "$witness_temp" 2>/dev/null &&
   jq -e . "$witness_temp" >/dev/null 2>&1; then

    witness_available=true

    witness_name="$(jq -r '.witness // ""' "$witness_temp")"
    witness_timestamp="$(jq -r '.timestamp // ""' "$witness_temp")"

    if [ "$witness_name" = "starfleet-core" ]; then
        witness_identity_valid=true
    fi

    witness_epoch="$(
        date -u -d "$witness_timestamp" +%s 2>/dev/null ||
            echo 0
    )"

    now_epoch="$(date -u +%s)"

    if [ "$witness_epoch" -gt 0 ]; then
        witness_age_seconds=$((now_epoch - witness_epoch))

        if [ "$witness_age_seconds" -ge 0 ] &&
           [ "$witness_age_seconds" -le "$MAX_WITNESS_AGE" ]; then
            witness_fresh=true
        fi
    fi

    witness_primary_api="$(
        jq -r '.primary.api // false' "$witness_temp"
    )"

    witness_takeover_candidate="$(
        jq -r '.takeover_candidate // false' "$witness_temp"
    )"

    witness_authority_granted="$(
        jq -r '.authority_granted // false' "$witness_temp"
    )"
fi

local_primary_api=false
local_primary_reachable=false
replica_valid=false
replica_fresh=false

if [ -s "$OBSERVER" ]; then
    local_primary_api="$(
        jq -r '.primary.api // false' "$OBSERVER"
    )"

    local_primary_reachable="$(
        jq -r '.primary.reachable // false' "$OBSERVER"
    )"
fi

if [ -s "$REPLICA" ]; then
    replica_valid="$(jq -r '.valid // false' "$REPLICA")"
    replica_fresh="$(jq -r '.fresh // false' "$REPLICA")"
fi

consensus_primary_healthy=false
if [ "$witness_available" = true ] &&
   [ "$witness_fresh" = true ] &&
   [ "$witness_identity_valid" = true ] &&
   [ "$witness_primary_api" = true ] &&
   [ "$local_primary_api" = true ]; then
    consensus_primary_healthy=true
fi

observation_agreement=false
if [ "$witness_primary_api" = "$local_primary_api" ]; then
    observation_agreement=true
fi

takeover_eligible=false

jq -n \
    --arg timestamp "$timestamp" \
    --argjson witness_available "$witness_available" \
    --argjson witness_fresh "$witness_fresh" \
    --argjson witness_identity_valid "$witness_identity_valid" \
    --argjson witness_age_seconds "$witness_age_seconds" \
    --argjson witness_primary_api "$witness_primary_api" \
    --argjson witness_takeover_candidate "$witness_takeover_candidate" \
    --argjson witness_authority_granted "$witness_authority_granted" \
    --argjson local_primary_api "$local_primary_api" \
    --argjson local_primary_reachable "$local_primary_reachable" \
    --argjson replica_valid "$replica_valid" \
    --argjson replica_fresh "$replica_fresh" \
    --argjson observation_agreement "$observation_agreement" \
    --argjson consensus_primary_healthy "$consensus_primary_healthy" \
    --argjson takeover_eligible "$takeover_eligible" \
    '{
        timestamp: $timestamp,
        witness: {
            available: $witness_available,
            fresh: $witness_fresh,
            identity_valid: $witness_identity_valid,
            age_seconds: $witness_age_seconds,
            primary_api: $witness_primary_api,
            takeover_candidate: $witness_takeover_candidate,
            authority_granted: $witness_authority_granted
        },
        local_observer: {
            primary_api: $local_primary_api,
            primary_reachable: $local_primary_reachable
        },
        replica: {
            valid: $replica_valid,
            fresh: $replica_fresh
        },
        observation_agreement: $observation_agreement,
        consensus_primary_healthy: $consensus_primary_healthy,
        takeover_eligible: $takeover_eligible,
        automatic_takeover_enabled: false
    }' > "$output_temp"

chmod 0640 "$output_temp"
mv -f "$output_temp" "$STATUS"
