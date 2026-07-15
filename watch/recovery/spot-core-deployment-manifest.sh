#!/usr/bin/env bash
set -euo pipefail

if [ "$EUID" -ne 0 ]; then
    echo "Must run as root." >&2
    exit 1
fi

NODE="spot-core"
REPO="/home/ogre/spot-stack"
COLLECTIVE="/mnt/collective"

MANIFEST_ROOT="$COLLECTIVE/backups/spot-core/deployment-manifests"
REMOTE_STATUS_ROOT="$COLLECTIVE/logs/spot/recovery"
LOCAL_STATUS_ROOT="/var/lib/spot/recovery"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

TARGET="$MANIFEST_ROOT/$STAMP"
STATUS_LOCAL="$LOCAL_STATUS_ROOT/spot-core-deployment-manifest-latest.json"
STATUS_REMOTE="$REMOTE_STATUS_ROOT/spot-core-deployment-manifest-latest.json"

exec 9>/run/spot-core-deployment-manifest.lock

if ! flock -n 9; then
    echo "Deployment manifest is already running."
    exit 0
fi

test "$(hostname)" = "$NODE"
test -d "$REPO/.git"
mountpoint -q "$COLLECTIVE"
systemctl is-active --quiet docker

mkdir -p \
    "$TARGET/systemd" \
    "$TARGET/runtime" \
    "$TARGET/inventory" \
    "$LOCAL_STATUS_ROOT" \
    "$REMOTE_STATUS_ROOT"

HEAD="$(git -C "$REPO" rev-parse HEAD)"
BRANCH="$(git -C "$REPO" branch --show-current)"
TREE="$(git -C "$REPO" rev-parse "${HEAD}^{tree}")"

{
    echo "===== HOSTNAMECTL ====="
    hostnamectl

    echo
    echo "===== OS RELEASE ====="
    cat /etc/os-release

    echo
    echo "===== KERNEL ====="
    uname -a

    echo
    echo "===== CPU ====="
    lscpu

    echo
    echo "===== MEMORY ====="
    free -h

    echo
    echo "===== STORAGE ====="
    lsblk -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINTS,MODEL,SERIAL
} > "$TARGET/runtime/host.txt"

jq -n \
    --arg repository "$REPO" \
    --arg branch "$BRANCH" \
    --arg head "$HEAD" \
    --arg tree "$TREE" \
    --arg origin "$(git -C "$REPO" remote get-url origin)" \
    '{
        repository: $repository,
        branch: $branch,
        head: $head,
        tree: $tree,
        origin: $origin
    }' > "$TARGET/runtime/git.json"

{
    echo "docker=$(docker --version)"
    echo "docker_compose=$(docker compose version)"
    echo "git=$(git --version)"
    echo "jq=$(jq --version)"
    echo "python3=$(python3 --version)"
    echo "curl=$(curl --version | head -n1)"
    echo "rsync=$(rsync --version | head -n1)"
    echo "ssh=$(ssh -V 2>&1)"
    echo "node=$(node --version 2>/dev/null || echo MISSING)"
    echo "npm=$(npm --version 2>/dev/null || echo MISSING)"
    echo "cloudflared=$(cloudflared --version 2>/dev/null || echo MISSING)"
    echo "ttyd=$(ttyd --version 2>/dev/null || echo MISSING)"
} > "$TARGET/runtime/versions.txt"

dpkg-query \
    -W \
    -f='${binary:Package}\t${Version}\n' |
    sort \
    > "$TARGET/inventory/dpkg-packages.tsv"

apt-mark showmanual |
    sort \
    > "$TARGET/inventory/apt-manual-packages.txt"

if [ -x "$REPO/watch/.venv-mcp/bin/pip" ]; then
    "$REPO/watch/.venv-mcp/bin/pip" freeze |
        sort \
        > "$TARGET/inventory/watch-mcp-python-packages.txt"
fi

if [ -f "$REPO/starfleet-ui/package-lock.json" ]; then
    sha256sum \
        "$REPO/starfleet-ui/package-lock.json" \
        > "$TARGET/inventory/starfleet-ui-package-lock.sha256"
fi

sha256sum \
    "$REPO/docker-compose.yml" \
    > "$TARGET/runtime/docker-compose.sha256"

docker compose \
    -f "$REPO/docker-compose.yml" \
    config --services \
    > "$TARGET/runtime/docker-compose-services.txt"

docker compose \
    -f "$REPO/docker-compose.yml" \
    config --images \
    > "$TARGET/runtime/docker-compose-images.txt"

docker ps \
    --no-trunc \
    --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' \
    > "$TARGET/runtime/docker-ps.txt"

docker inspect spot-core |
    jq '.[0] | {
        name: .Name,
        image: .Config.Image,
        image_id: .Image,
        created: .Created,
        restart_policy: .HostConfig.RestartPolicy,
        network_mode: .HostConfig.NetworkMode,
        mounts: [
            .Mounts[]? | {
                type: .Type,
                source: .Source,
                destination: .Destination,
                rw: .RW
            }
        ],
        exposed_ports: .Config.ExposedPorts,
        published_ports: .NetworkSettings.Ports,
        environment_variable_names: [
            .Config.Env[]? |
            split("=")[0]
        ] | sort
    }' \
    > "$TARGET/runtime/spot-core-container.json"

docker image inspect python:3.11-slim |
    jq '.[0] | {
        id: .Id,
        repo_tags: .RepoTags,
        repo_digests: .RepoDigests,
        created: .Created,
        architecture: .Architecture,
        os: .Os
    }' \
    > "$TARGET/runtime/spot-core-image.json" \
    2>/dev/null || true

# MODULE 9 SCRIPT PART 1 COMPLETE

sanitize_stream() {
    sed -E \
        -e '/^[[:space:]]*(Environment|EnvironmentFile|LoadCredential|LoadCredentialEncrypted|SetCredential|SetCredentialEncrypted)=/s#=.*#=[REDACTED]#' \
        -e 's#([Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Tt][Oo][Kk][Ee][Nn]|[Ss][Ee][Cc][Rr][Ee][Tt]|[Aa][Pp][Ii][_-]?[Kk][Ee][Yy]|[Pp][Rr][Ii][Vv][Aa][Tt][Ee][_-]?[Kk][Ee][Yy])=([^[:space:]]+)#\1=[REDACTED]#g' \
        -e 's#(Authorization:[[:space:]]*(Bearer|Basic))[[:space:]]+[^[:space:]]+#\1 [REDACTED]#Ig' \
        -e 's#(https?://[^:/[:space:]]+):[^@/[:space:]]+@#\1:[REDACTED]@#g'
}

SYSTEMD_UNITS="$TARGET/inventory/systemd-unit-files.tsv"

systemctl list-unit-files \
    --no-legend \
    --no-pager |
    awk '
        BEGIN { OFS="\t" }
        NF >= 2 && ($1 ~ /^(spot|starfleet|cloudflared|ttyd|docker)/ || $1 ~ /(spot|starfleet|recovery|fleet|edge)/) {
            print $1, $2, $3
        }
    ' |
    sort -u \
    > "$SYSTEMD_UNITS"

while IFS=$'\t' read -r unit state preset; do
    [ -n "$unit" ] || continue

    safe_name="$(printf '%s' "$unit" | tr '/@' '__')"

    {
        echo "# unit=$unit"
        echo "# state=$state"
        echo "# preset=${preset:-unknown}"
        echo

        systemctl cat "$unit" --no-pager 2>&1 |
            sanitize_stream
    } > "$TARGET/systemd/$safe_name.sanitized.txt"
done < "$SYSTEMD_UNITS"

systemctl list-timers \
    --all \
    --no-pager \
    > "$TARGET/runtime/systemd-timers.txt"

systemctl list-units \
    --type=service \
    --all \
    --no-legend \
    --no-pager |
    awk '
        $1 ~ /^(spot|starfleet|cloudflared|ttyd|docker)/ ||
        $1 ~ /(spot|starfleet|recovery|fleet|edge)/
    ' \
    > "$TARGET/runtime/systemd-service-state.txt"

ss -H -lntup \
    > "$TARGET/runtime/listening-ports.txt"

findmnt \
    --real \
    --output TARGET,SOURCE,FSTYPE,OPTIONS \
    > "$TARGET/runtime/mount-state.txt"

findmnt \
    --target "$COLLECTIVE" \
    --output TARGET,SOURCE,FSTYPE,OPTIONS \
    > "$TARGET/runtime/collective-mount.txt"

if [ -f /etc/fstab ]; then
    awk '
        /^[[:space:]]*#/ || /^[[:space:]]*$/ {
            print
            next
        }

        {
            line=$0
            gsub(/(password|passwd|pass|credentials|cred|secret|token)=[^,[:space:]]+/, "\\1=[REDACTED]", line)
            gsub(/(username|user)=[^,[:space:]]+/, "\\1=[REDACTED]", line)
            print line
        }
    ' /etc/fstab \
        > "$TARGET/runtime/fstab.sanitized"
fi

SECRET_METADATA="$TARGET/inventory/secret-file-metadata.tsv"

printf 'path\towner\tgroup\tmode\tsize_bytes\tmodified_utc\ttype\n' \
    > "$SECRET_METADATA"

secret_roots=(
    "/etc/spot"
    "/etc/cloudflared"
    "/home/ogre/spot-mcp"
    "/home/ogre/.config/systemd"
    "/root/.config/systemd"
)

for root in "${secret_roots[@]}"; do
    [ -d "$root" ] || continue

    while IFS= read -r -d '' secret_file; do
        stat \
            --printf='%n\t%U\t%G\t%a\t%s\t%y\t%F\n' \
            "$secret_file"
    done < <(
        find "$root" -xdev -type f \
            \( \
                -iname '*.env' -o \
                -iname '*.key' -o \
                -iname '*.pem' -o \
                -iname '*.crt' -o \
                -iname '*.p12' -o \
                -iname '*.pfx' -o \
                -iname '*credential*' -o \
                -iname '*secret*' -o \
                -iname '*token*' \
            \) \
            -print0 2>/dev/null
    )
done |
    sed -E 's/\.[0-9]+[[:space:]]+\+0000/\tUTC/' |
    sort -u \
    >> "$SECRET_METADATA"

RUNTIME_INVENTORY="$TARGET/inventory/non-git-runtime-files.tsv"

printf 'scope\tpath\towner\tgroup\tmode\tsize_bytes\tmodified_utc\ttype\n' \
    > "$RUNTIME_INVENTORY"

git -C "$REPO" ls-files \
    --others \
    --exclude-standard \
    -z |
while IFS= read -r -d '' relative_path; do
    absolute_path="$REPO/$relative_path"

    [ -e "$absolute_path" ] || continue

    stat \
        --printf="repository-untracked\t%n\t%U\t%G\t%a\t%s\t%y\t%F\n" \
        "$absolute_path"
done |
    sort -u \
    >> "$RUNTIME_INVENTORY"

runtime_roots=(
    "/var/lib/spot"
    "/var/log/spot"
    "/etc/spot"
    "/home/ogre/spot-mcp"
)

for root in "${runtime_roots[@]}"; do
    [ -e "$root" ] || continue

    find "$root" \
        -xdev \
        \( -type f -o -type l \) \
        -print0 2>/dev/null |
    while IFS= read -r -d '' runtime_file; do
        stat \
            --printf="host-runtime\t%n\t%U\t%G\t%a\t%s\t%y\t%F\n" \
            "$runtime_file"
    done
done |
    sort -u \
    >> "$RUNTIME_INVENTORY"

cat > "$TARGET/RESTORE_ORDER.txt" <<'RESTORE_ORDER'
SPOT CORE SANITIZED RESTORE ORDER

1. Install the recorded operating system and required packages.
2. Configure storage and restore the sanitized mount definitions.
3. Mount /mnt/collective and verify backup availability.
4. Clone the Spot repository from the recorded origin.
5. Check out the exact recorded Git commit and verify its tree hash.
6. Install Docker, Docker Compose, system packages, Python packages, Node.js, and npm dependencies.
7. Recreate required runtime directories with recorded ownership and modes.
8. Restore credentials only through the approved credential-management process.
9. Rotate any credential known or suspected to have been exposed.
10. Restore approved systemd definitions from controlled source material.
11. Run daemon-reload, enable required units, and start infrastructure dependencies.
12. Pull or rebuild the recorded container images.
13. Start Spot Core only through the approved operator process.
14. Run Spot validation and recovery validation.
15. Confirm execution_allowed=false and mutation_authority=false.
16. Publish recovery status only after every validation passes.

This package is inventory and recovery guidance only.
It contains no secret values and grants no execution or mutation authority.
RESTORE_ORDER

HOST_COUNT="$(wc -l < "$TARGET/runtime/host.txt")"
UNIT_COUNT="$(awk 'END { print NR + 0 }' "$SYSTEMD_UNITS")"
TIMER_COUNT="$(
    grep -Ec '\.timer([[:space:]]|$)' \
        "$TARGET/runtime/systemd-timers.txt" || true
)"
PORT_COUNT="$(
    awk 'NF { count++ } END { print count + 0 }' \
        "$TARGET/runtime/listening-ports.txt"
)"
PACKAGE_COUNT="$(
    awk 'NF { count++ } END { print count + 0 }' \
        "$TARGET/inventory/dpkg-packages.tsv"
)"
SECRET_METADATA_COUNT="$(
    awk 'NR > 1 { count++ } END { print count + 0 }' \
        "$SECRET_METADATA"
)"
RUNTIME_FILE_COUNT="$(
    awk 'NR > 1 { count++ } END { print count + 0 }' \
        "$RUNTIME_INVENTORY"
)"

jq -n \
    --arg schema_version "1.0" \
    --arg node "$NODE" \
    --arg created_at "$TIMESTAMP" \
    --arg package_path "$TARGET" \
    --arg repository "$REPO" \
    --arg branch "$BRANCH" \
    --arg head "$HEAD" \
    --arg tree "$TREE" \
    --argjson host_inventory_lines "$HOST_COUNT" \
    --argjson systemd_units "$UNIT_COUNT" \
    --argjson timers "$TIMER_COUNT" \
    --argjson listening_ports "$PORT_COUNT" \
    --argjson installed_packages "$PACKAGE_COUNT" \
    --argjson secret_metadata_records "$SECRET_METADATA_COUNT" \
    --argjson non_git_runtime_records "$RUNTIME_FILE_COUNT" \
    '{
        schema_version: $schema_version,
        manifest_type: "sanitized-spot-core-deployment-recovery",
        node: $node,
        created_at: $created_at,
        package_path: $package_path,
        source: {
            repository: $repository,
            branch: $branch,
            head: $head,
            tree: $tree
        },
        inventory: {
            host_inventory_lines: $host_inventory_lines,
            systemd_units: $systemd_units,
            timers: $timers,
            listening_ports: $listening_ports,
            installed_packages: $installed_packages,
            secret_metadata_records: $secret_metadata_records,
            non_git_runtime_records: $non_git_runtime_records
        },
        controls: {
            sanitized: true,
            secret_values_included: false,
            restore_authority_granted: false,
            execution_allowed: false,
            mutation_authority: false,
            spot_core_sole_execution_authority: true,
            edge_pull_only: true,
            edge_routing_allowed: false,
            exposed_administrative_token_rotation_required: true
        },
        restore_order: "RESTORE_ORDER.txt"
    }' > "$TARGET/manifest.json"

(
    cd "$TARGET"

    find . \
        -type f \
        ! -name SHA256SUMS \
        ! -name PACKAGE.sha256 \
        -print0 |
        sort -z |
        xargs -0 sha256sum \
        > SHA256SUMS

    sha256sum SHA256SUMS \
        > PACKAGE.sha256
)

PACKAGE_SHA256="$(
    awk '{print $1}' "$TARGET/PACKAGE.sha256"
)"

STATUS_TEMP="$(mktemp "$LOCAL_STATUS_ROOT/.deployment-manifest.XXXXXX")"

jq -n \
    --arg node "$NODE" \
    --arg generated_at "$TIMESTAMP" \
    --arg package "$TARGET" \
    --arg package_sha256 "$PACKAGE_SHA256" \
    --arg git_head "$HEAD" \
    '{
        node: $node,
        generated_at: $generated_at,
        package: $package,
        package_sha256: $package_sha256,
        git_head: $git_head,
        result: "PASS",
        sanitized: true,
        secret_values_included: false,
        restore_authority_granted: false,
        execution_allowed: false,
        mutation_authority: false,
        token_rotation_required: true
    }' > "$STATUS_TEMP"

chmod 0644 "$STATUS_TEMP"
mv -f "$STATUS_TEMP" "$STATUS_LOCAL"

REMOTE_TEMP="$REMOTE_STATUS_ROOT/.spot-core-deployment-manifest-latest.$STAMP.tmp"
cp "$STATUS_LOCAL" "$REMOTE_TEMP"
chmod 0644 "$REMOTE_TEMP"
mv -f "$REMOTE_TEMP" "$STATUS_REMOTE"

echo "manifest_package: $TARGET"
echo "manifest_status_local: $STATUS_LOCAL"
echo "manifest_status_remote: $STATUS_REMOTE"
echo "package_sha256: $PACKAGE_SHA256"
echo "RESULT: PASS"

# MODULE 9 SCRIPT PART 2 COMPLETE
