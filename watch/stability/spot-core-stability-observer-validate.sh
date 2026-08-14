#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${1:-/home/ogre/spot-stack}"
SOURCE_DIR="$ROOT/watch/stability"

OBSERVER="$SOURCE_DIR/spot-core-stability-observer.sh"
SERVICE="$SOURCE_DIR/spot-core-stability-observer.service"
TIMER="$SOURCE_DIR/spot-core-stability-observer.timer"
DOC="$SOURCE_DIR/README.md"
VALIDATOR="$SOURCE_DIR/spot-core-stability-observer-validate.sh"

for FILE in \
    "$OBSERVER" \
    "$SERVICE" \
    "$TIMER" \
    "$DOC"
do
    test -s "$FILE"
done

bash -n "$OBSERVER"
bash -n "$VALIDATOR"

grep -Fq 'SOAK_SECONDS="${SOAK_SECONDS:-604800}"' "$OBSERVER"
grep -Fq 'execution_allowed_enabled' "$OBSERVER"
grep -Fq 'mutation_authority_enabled' "$OBSERVER"
grep -Fq 'automatic_takeover_enabled' "$OBSERVER"
grep -Fq 'spot_core_container_identity_changed' "$OBSERVER"
grep -Fq 'collective_storage_unavailable' "$OBSERVER"
grep -Fq 'exit 0' "$OBSERVER"

grep -Fq 'Type=oneshot' "$SERVICE"
grep -Fq 'NoNewPrivileges=true' "$SERVICE"
grep -Fq 'ProtectSystem=strict' "$SERVICE"
grep -Fq 'ReadWritePaths=/var/lib/spot/stability-soak' "$SERVICE"

grep -Fq 'OnUnitActiveSec=5min' "$TIMER"
grep -Fq 'Persistent=true' "$TIMER"

if grep -Eqi \
    'systemctl[[:space:]]+(restart|stop)|docker[[:space:]]+(restart|stop|rm)' \
    "$OBSERVER"
then
    echo "[FAIL] Observer contains prohibited mutation behavior"
    exit 1
fi

echo "observer_syntax=PASS"
echo "observer_read_only_contract=PASS"
echo "observer_governance_checks=PASS"
echo "service_hardening=PASS"
echo "timer_contract=PASS"
echo "RESULT: STABILITY OBSERVER SOURCE VALIDATION PASS"
