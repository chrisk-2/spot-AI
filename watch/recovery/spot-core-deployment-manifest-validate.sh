#!/usr/bin/env bash
set -euo pipefail

NODE="spot-core"
STATUS_LOCAL="/var/lib/spot/recovery/spot-core-deployment-manifest-latest.json"
STATUS_REMOTE="/mnt/collective/logs/spot/recovery/spot-core-deployment-manifest-latest.json"

pass=0
fail=0

pass_check() {
    echo "[PASS] $1"
    pass=$((pass + 1))
}

fail_check() {
    echo "[FAIL] $1"
    fail=$((fail + 1))
}

check_file() {
    local path="$1"
    local label="$2"

    if [ -s "$path" ]; then
        pass_check "$label"
    else
        fail_check "$label"
    fi
}

echo "=== SPOT CORE DEPLOYMENT MANIFEST VALIDATION ==="
echo "timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [ "$(hostname)" = "$NODE" ]; then
    pass_check "host is spot-core"
else
    fail_check "host is spot-core"
fi

if mountpoint -q /mnt/collective; then
    pass_check "collective mounted"
else
    fail_check "collective mounted"
fi

check_file "$STATUS_LOCAL" "local status exists"
check_file "$STATUS_REMOTE" "remote status exists"

if [ ! -s "$STATUS_LOCAL" ] || [ ! -s "$STATUS_REMOTE" ]; then
    echo
    echo "pass=$pass fail=$fail"
    echo "RESULT: FAIL"
    exit 1
fi

if jq -e . "$STATUS_LOCAL" >/dev/null 2>&1; then
    pass_check "local status valid JSON"
else
    fail_check "local status valid JSON"
fi

if jq -e . "$STATUS_REMOTE" >/dev/null 2>&1; then
    pass_check "remote status valid JSON"
else
    fail_check "remote status valid JSON"
fi

if cmp -s "$STATUS_LOCAL" "$STATUS_REMOTE"; then
    pass_check "local and remote status synchronized"
else
    fail_check "local and remote status synchronized"
fi

PACKAGE="$(
    jq -r '.package // empty' "$STATUS_LOCAL"
)"

EXPECTED_PACKAGE_SHA="$(
    jq -r '.package_sha256 // empty' "$STATUS_LOCAL"
)"

if [ -d "$PACKAGE" ]; then
    pass_check "manifest package exists"
else
    fail_check "manifest package exists"
fi

if [ ! -d "$PACKAGE" ]; then
    echo
    echo "pass=$pass fail=$fail"
    echo "RESULT: FAIL"
    exit 1
fi

required_files=(
    "manifest.json"
    "RESTORE_ORDER.txt"
    "SHA256SUMS"
    "PACKAGE.sha256"
    "runtime/host.txt"
    "runtime/git.json"
    "runtime/versions.txt"
    "runtime/docker-compose.sha256"
    "runtime/docker-compose-services.txt"
    "runtime/docker-compose-images.txt"
    "runtime/docker-ps.txt"
    "runtime/spot-core-container.json"
    "runtime/systemd-timers.txt"
    "runtime/systemd-service-state.txt"
    "runtime/listening-ports.txt"
    "runtime/mount-state.txt"
    "runtime/collective-mount.txt"
    "runtime/fstab.sanitized"
    "inventory/dpkg-packages.tsv"
    "inventory/apt-manual-packages.txt"
    "inventory/systemd-unit-files.tsv"
    "inventory/secret-file-metadata.tsv"
    "inventory/non-git-runtime-files.tsv"
)

missing_required=0

for relative_path in "${required_files[@]}"; do
    if [ ! -s "$PACKAGE/$relative_path" ]; then
        echo "[FAIL] required package file: $relative_path"
        missing_required=$((missing_required + 1))
    fi
done

if [ "$missing_required" -eq 0 ]; then
    pass_check "required package files complete"
else
    fail_check "required package files complete"
fi

if jq -e '
    .manifest_type == "sanitized-spot-core-deployment-recovery" and
    .node == "spot-core" and
    .controls.sanitized == true and
    .controls.secret_values_included == false and
    .controls.restore_authority_granted == false and
    .controls.execution_allowed == false and
    .controls.mutation_authority == false and
    .controls.spot_core_sole_execution_authority == true and
    .controls.edge_pull_only == true and
    .controls.edge_routing_allowed == false and
    .controls.exposed_administrative_token_rotation_required == true
' "$PACKAGE/manifest.json" >/dev/null 2>&1; then
    pass_check "manifest governance controls locked"
else
    fail_check "manifest governance controls locked"
fi

if jq -e '
    .result == "PASS" and
    .sanitized == true and
    .secret_values_included == false and
    .restore_authority_granted == false and
    .execution_allowed == false and
    .mutation_authority == false and
    .token_rotation_required == true
' "$STATUS_LOCAL" >/dev/null 2>&1; then
    pass_check "published status governance controls locked"
else
    fail_check "published status governance controls locked"
fi

ACTUAL_PACKAGE_SHA="$(
    sha256sum "$PACKAGE/SHA256SUMS" |
        awk '{print $1}'
)"

RECORDED_PACKAGE_SHA="$(
    awk '{print $1}' "$PACKAGE/PACKAGE.sha256"
)"

if [ -n "$EXPECTED_PACKAGE_SHA" ] &&
   [ "$EXPECTED_PACKAGE_SHA" = "$RECORDED_PACKAGE_SHA" ] &&
   [ "$EXPECTED_PACKAGE_SHA" = "$ACTUAL_PACKAGE_SHA" ]; then
    pass_check "package checksum identity matches status"
else
    fail_check "package checksum identity matches status"
fi

if (
    cd "$PACKAGE"
    sha256sum --check --quiet SHA256SUMS
); then
    pass_check "package file checksums valid"
else
    fail_check "package file checksums valid"
fi

if awk -F '\t' '
    NR == 1 {
        if ($1 != "path" ||
            $2 != "owner" ||
            $3 != "group" ||
            $4 != "mode" ||
            $5 != "size_bytes") {
            exit 1
        }
        next
    }

    NF < 7 {
        exit 1
    }

    $4 !~ /^[0-7]{3,4}$/ {
        exit 1
    }

    $5 !~ /^[0-9]+$/ {
        exit 1
    }
' "$PACKAGE/inventory/secret-file-metadata.tsv"; then
    pass_check "secret inventory contains metadata structure only"
else
    fail_check "secret inventory contains metadata structure only"
fi

if grep -RIlE \
    --exclude='SHA256SUMS' \
    --exclude='PACKAGE.sha256' \
    --exclude='secret-file-metadata.tsv' \
    --exclude='non-git-runtime-files.tsv' \
    -- \
    '-----BEGIN (OPENSSH|RSA|EC|DSA|PRIVATE) PRIVATE KEY-----' \
    "$PACKAGE" |
    grep -q .; then
    fail_check "no private key material detected"
else
    pass_check "no private key material detected"
fi

if grep -RIlE \
    --exclude='SHA256SUMS' \
    --exclude='PACKAGE.sha256' \
    --exclude='secret-file-metadata.tsv' \
    --exclude='non-git-runtime-files.tsv' \
    '(Authorization:[[:space:]]*(Bearer|Basic)[[:space:]]+[A-Za-z0-9+/_.=-]{12,}|(password|passwd|token|secret|api[_-]?key|private[_-]?key)=[^[:space:]\[]+)' \
    "$PACKAGE" |
    grep -q .; then
    fail_check "no obvious secret assignments detected"
else
    pass_check "no obvious secret assignments detected"
fi

if grep -Fq \
    'It contains no secret values and grants no execution or mutation authority.' \
    "$PACKAGE/RESTORE_ORDER.txt"; then
    pass_check "restore authority disclaimer present"
else
    fail_check "restore authority disclaimer present"
fi

echo
echo "pass=$pass fail=$fail"

if [ "$fail" -eq 0 ]; then
    echo "RESULT: PASS"
    exit 0
fi

echo "RESULT: FAIL"
exit 1
