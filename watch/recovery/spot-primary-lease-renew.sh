#!/usr/bin/env bash
set -euo pipefail
umask 077

KEY="/home/ogre/.ssh/spot_witness_primary_lease"
KNOWN_HOSTS="/home/ogre/.ssh/known_hosts"
STATE_DIR="/var/lib/spot-failover-primary"
STATUS="$STATE_DIR/witness-lease.json"
LOCK="/run/lock/spot-primary-lease-renew.lock"
TEMP="$(mktemp)"

cleanup() {
    rm -f "$TEMP"
}
trap cleanup EXIT

exec 9>"$LOCK"
flock -n 9 || exit 0

test "$(hostname)" = "spot-core"
test -s "$KEY"
test -s "$KNOWN_HOSTS"

if ! runuser -u ogre -- \
    /usr/bin/ssh \
        -F /dev/null \
        -i "$KEY" \
        -o IdentityAgent=none \
        -o IdentitiesOnly=yes \
        -o BatchMode=yes \
        -o ConnectTimeout=5 \
        -o StrictHostKeyChecking=yes \
        -o UserKnownHostsFile="$KNOWN_HOSTS" \
        -n \
        spot-lease-primary@192.168.60.20 \
        renew-primary \
        > "$TEMP"; then

    logger -t spot-primary-lease-renew \
        "witness lease renewal failed"

    exit 1
fi

jq -e '.witness == "starfleet-core"' "$TEMP" >/dev/null
jq -e '.holder == "spot-core"' "$TEMP" >/dev/null
jq -e '.lease_valid == true' "$TEMP" >/dev/null
jq -e '.command_authority == true' "$TEMP" >/dev/null
jq -e '.mutation_authority == false' "$TEMP" >/dev/null
jq -e '.execution_allowed == false' "$TEMP" >/dev/null
jq -e '.automatic_takeover_enabled == false' "$TEMP" >/dev/null

install \
    -o root \
    -g root \
    -m 0640 \
    "$TEMP" \
    "$STATUS"

logger -t spot-primary-lease-renew \
    "primary witness lease renewed"
