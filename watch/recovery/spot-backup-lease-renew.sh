#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-renew}"

STATE_ROOT="/srv/spot-backup-data/failover-state"
MARKER="/srv/spot-backup-data/failover-active/activated"
WITNESS_STATE="$STATE_ROOT/witness-authority.json"
RENEW_STATUS="$STATE_ROOT/backup-lease-renew-status.json"
LOCK="/run/lock/spot-backup-lease-renew.lock"

exec 9>"$LOCK"
flock -x 9

timestamp() {
    date -u +%Y-%m-%dT%H:%M:%SZ
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

write_status() {
    local result="$1"
    local reason="$2"
    local temporary

    temporary="$(mktemp "$STATE_ROOT/.backup-lease-renew.XXXXXX")"

    jq -n \
        --arg timestamp "$(timestamp)" \
        --arg host "$(hostname)" \
        --arg result "$result" \
        --arg reason "$reason" \
        '{
            schema: "spot_backup_lease_renew_status_v1",
            timestamp: $timestamp,
            host: $host,
            result: $result,
            reason: $reason,
            automatic_takeover_enabled: false
        }' > "$temporary"

    chmod 0644 "$temporary"
    chown root:root "$temporary"
    mv -f "$temporary" "$RENEW_STATUS"
}

install -d -o root -g ogre -m 0770 "$STATE_ROOT"

case "$ACTION" in
    --status-only)
        witness_command status
        exit 0
        ;;

    renew)
        ;;

    *)
        echo "usage: $0 [renew|--status-only]" >&2
        exit 2
        ;;
esac

if [ ! -e "$MARKER" ]; then
    write_status skipped activation-marker-absent
    exit 0
fi

if ! payload="$(witness_command renew-backup)"; then
    write_status failed witness-renewal-command-failed
    exit 1
fi

now_epoch="$(date -u +%s)"
expires_epoch="$(jq -r '.expires_epoch // 0' <<<"$payload")"

case "$expires_epoch" in
    ''|*[!0-9]*)
        write_status failed invalid-expiry
        exit 1
        ;;
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

temporary="$(mktemp "$STATE_ROOT/.witness-authority.XXXXXX")"
printf '%s\n' "$payload" > "$temporary"
chmod 0644 "$temporary"
chown root:root "$temporary"
mv -f "$temporary" "$WITNESS_STATE"

write_status renewed backup-lease-renewed
