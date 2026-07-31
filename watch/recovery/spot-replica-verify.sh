#!/usr/bin/env bash
set -euo pipefail

REPLICA="/srv/spot-backup-data/replica"
CURRENT="$REPLICA/current"
STATE_DIR="/srv/spot-backup-data/failover-state"
STATUS="$STATE_DIR/replica-status.json"
LOCK="/run/lock/spot-replica-verify.lock"
MAX_AGE_SECONDS=7200

exec 9>"$LOCK"
flock -n 9 || exit 0

timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
mkdir -p "$STATE_DIR"

valid=false
fresh=false
checksums_valid=false
manifest_valid=false
age_seconds=-1
git_commit=""
snapshot_utc=""
release_path=""

if [ -e "$CURRENT" ]; then
    release_path="$(readlink -f "$CURRENT" || true)"
fi

if [ -n "$release_path" ] &&
   [ -d "$release_path" ] &&
   [ -s "$release_path/manifest.env" ] &&
   [ -s "$release_path/SHA256SUMS" ]; then

    manifest_valid=true

    snapshot_utc="$(
        awk -F= '$1=="snapshot_utc" {print $2}' \
            "$release_path/manifest.env"
    )"

    git_commit="$(
        awk -F= '$1=="git_commit" {print $2}' \
            "$release_path/manifest.env"
    )"

    activation_authorized="$(
        awk -F= '$1=="activation_authorized" {print $2}' \
            "$release_path/manifest.env"
    )"

    mutation_authority="$(
        awk -F= '$1=="mutation_authority" {print $2}' \
            "$release_path/manifest.env"
    )"

    execution_allowed="$(
        awk -F= '$1=="execution_allowed" {print $2}' \
            "$release_path/manifest.env"
    )"

    if [ "$activation_authorized" != false ] ||
       [ "$mutation_authority" != false ] ||
       [ "$execution_allowed" != false ]; then
        manifest_valid=false
    fi

    if (
        cd "$release_path"
        sha256sum --check --strict SHA256SUMS >/dev/null
    ); then
        checksums_valid=true
    fi

    snapshot_epoch="$(date -u -d "$snapshot_utc" +%s 2>/dev/null || echo 0)"
    now_epoch="$(date -u +%s)"

    if [ "$snapshot_epoch" -gt 0 ]; then
        age_seconds=$((now_epoch - snapshot_epoch))

        if [ "$age_seconds" -ge 0 ] &&
           [ "$age_seconds" -le "$MAX_AGE_SECONDS" ]; then
            fresh=true
        fi
    fi

    if [ "$manifest_valid" = true ] &&
       [ "$checksums_valid" = true ] &&
       [ "$fresh" = true ]; then
        valid=true
    fi
fi

temp="$(mktemp "$STATE_DIR/.replica-status.XXXXXX")"

jq -n \
    --arg timestamp "$timestamp" \
    --arg release_path "$release_path" \
    --arg snapshot_utc "$snapshot_utc" \
    --arg git_commit "$git_commit" \
    --argjson age_seconds "$age_seconds" \
    --argjson manifest_valid "$manifest_valid" \
    --argjson checksums_valid "$checksums_valid" \
    --argjson fresh "$fresh" \
    --argjson valid "$valid" \
    '{
        timestamp: $timestamp,
        release_path: $release_path,
        snapshot_utc: $snapshot_utc,
        git_commit: $git_commit,
        age_seconds: $age_seconds,
        manifest_valid: $manifest_valid,
        checksums_valid: $checksums_valid,
        fresh: $fresh,
        valid: $valid,
        activation_authorized: false
    }' > "$temp"

chmod 0640 "$temp"
chown root:ogre "$temp"
mv -f "$temp" "$STATUS"

[ "$valid" = true ]
