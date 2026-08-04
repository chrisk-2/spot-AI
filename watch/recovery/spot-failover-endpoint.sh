#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-status}"
CONFIG="${SPOT_FAILOVER_ENDPOINT_CONFIG:-/etc/spot-failover/endpoint.env}"
LOCK="/run/lock/spot-failover-endpoint.lock"

ACTIVE_MARKER="/srv/spot-backup-data/failover-active/activated"
BACKUP_AUTHORITY="/etc/spot-failover/authority-state"
PRIMARY_FENCE="/var/lib/spot-failover-primary/fenced"

fail() {
    printf '[FAIL] %s\n' "$*" >&2
    exit 1
}

test -r "$CONFIG" ||
    fail "missing endpoint configuration: $CONFIG"

# shellcheck disable=SC1090
source "$CONFIG"

: "${SPOT_ENDPOINT_ROLE:?missing SPOT_ENDPOINT_ROLE}"
: "${SPOT_ENDPOINT_INTERFACE:?missing SPOT_ENDPOINT_INTERFACE}"
: "${SPOT_ENDPOINT_VIP:?missing SPOT_ENDPOINT_VIP}"
: "${SPOT_ENDPOINT_PREFIX:?missing SPOT_ENDPOINT_PREFIX}"
: "${SPOT_WITNESS_IP:?missing SPOT_WITNESS_IP}"

case "$SPOT_ENDPOINT_ROLE" in
    spot-core|spot-core-backup)
        ;;
    *)
        fail "invalid endpoint role: $SPOT_ENDPOINT_ROLE"
        ;;
esac

test "$(hostname)" = "$SPOT_ENDPOINT_ROLE" ||
    fail \
        "host role mismatch: expected $SPOT_ENDPOINT_ROLE, got $(hostname)"

ip link show dev "$SPOT_ENDPOINT_INTERFACE" >/dev/null 2>&1 ||
    fail "missing interface: $SPOT_ENDPOINT_INTERFACE"

VIP_CIDR="${SPOT_ENDPOINT_VIP}/${SPOT_ENDPOINT_PREFIX}"

exec 9>"$LOCK"
flock -n 9 || exit 0

witness_status() {
    case "$SPOT_ENDPOINT_ROLE" in
        spot-core)
            runuser -u ogre -- \
                ssh \
                    -i /home/ogre/.ssh/spot_witness_primary_lease \
                    -o BatchMode=yes \
                    -o ConnectTimeout=5 \
                    -o IdentitiesOnly=yes \
                    "spot-lease-primary@${SPOT_WITNESS_IP}" \
                    status
            ;;

        spot-core-backup)
            runuser -u ogre -- \
                /usr/local/sbin/spot-witness-backup-client \
                status
            ;;
    esac
}

lease_allows_endpoint() {
    local status
    local now

    now="$(date +%s)"
    status="$(witness_status 2>/dev/null)" || return 1

    printf '%s\n' "$status" |
        jq -e \
            --arg holder "$SPOT_ENDPOINT_ROLE" \
            --argjson now "$now" \
            '
            .schema == "spot_failover_authority_lease_v1" and
            .holder == $holder and
            .lease_valid == true and
            .lease_enforced == true and
            .command_authority == true and
            .mutation_authority == false and
            .execution_allowed == false and
            (.expires_epoch | type == "number") and
            .expires_epoch > $now
            ' \
            >/dev/null
}

local_state_allows_endpoint() {
    case "$SPOT_ENDPOINT_ROLE" in
        spot-core)
            test ! -e "$PRIMARY_FENCE"
            ;;

        spot-core-backup)
            test -e "$ACTIVE_MARKER"
            grep -Fxq 'state=active' "$BACKUP_AUTHORITY"
            grep -Fxq \
                'authority_holder=spot-core-backup' \
                "$BACKUP_AUTHORITY"
            grep -Fxq \
                'activation_authorized=true' \
                "$BACKUP_AUTHORITY"
            grep -Fxq \
                'mutation_authority=true' \
                "$BACKUP_AUTHORITY"
            grep -Fxq \
                'execution_allowed=true' \
                "$BACKUP_AUTHORITY"
            ;;
    esac
}

vip_present() {
    ip -4 -o address show dev "$SPOT_ENDPOINT_INTERFACE" |
        awk \
            -v vip="$VIP_CIDR" \
            '$4 == vip { found = 1 }
             END { exit(found ? 0 : 1) }'
}

acquire() {
    lease_allows_endpoint ||
        fail "witness lease does not authorize $SPOT_ENDPOINT_ROLE"

    local_state_allows_endpoint ||
        fail "local state does not authorize $SPOT_ENDPOINT_ROLE"

    if vip_present; then
        echo "[PASS] endpoint already owned: $VIP_CIDR"
        return 0
    fi

    command -v arping >/dev/null 2>&1 ||
        fail "iputils-arping is required before endpoint acquisition"

    arping -V 2>&1 |
        grep -Fqi 'iputils' ||
        fail "unsupported arping implementation; iputils-arping is required"

    arping \
        -D \
        -q \
        -c 3 \
        -w 4 \
        -I "$SPOT_ENDPOINT_INTERFACE" \
        "$SPOT_ENDPOINT_VIP" ||
        fail "endpoint conflict detected: $SPOT_ENDPOINT_VIP"

    ip address add \
        "$VIP_CIDR" \
        dev "$SPOT_ENDPOINT_INTERFACE"

    arping \
        -U \
        -q \
        -c 3 \
        -I "$SPOT_ENDPOINT_INTERFACE" \
        "$SPOT_ENDPOINT_VIP" ||
        true

    vip_present ||
        fail "endpoint acquisition did not persist"

    echo "[PASS] endpoint acquired: $VIP_CIDR"
}

release() {
    if vip_present; then
        ip address del \
            "$VIP_CIDR" \
            dev "$SPOT_ENDPOINT_INTERFACE"
    fi

    vip_present &&
        fail "endpoint release did not persist"

    echo "[PASS] endpoint absent: $VIP_CIDR"
}

status() {
    echo "host=$(hostname)"
    echo "role=$SPOT_ENDPOINT_ROLE"
    echo "interface=$SPOT_ENDPOINT_INTERFACE"
    echo "vip=$SPOT_ENDPOINT_VIP"
    echo "prefix=$SPOT_ENDPOINT_PREFIX"

    if vip_present; then
        echo "endpoint_owned=true"
    else
        echo "endpoint_owned=false"
    fi

    if lease_allows_endpoint; then
        echo "lease_authorized=true"
    else
        echo "lease_authorized=false"
    fi

    if local_state_allows_endpoint; then
        echo "local_state_authorized=true"
    else
        echo "local_state_authorized=false"
    fi
}

case "$ACTION" in
    acquire)
        acquire
        ;;

    release)
        release
        ;;

    enforce)
        if lease_allows_endpoint &&
           local_state_allows_endpoint; then
            acquire
        else
            release
        fi
        ;;

    status)
        status
        ;;

    *)
        fail "usage: $0 {status|acquire|release|enforce}"
        ;;
esac
