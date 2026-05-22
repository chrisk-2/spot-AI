#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ogre/spot-stack"

cd "$ROOT"

echo "=== SPOT CONTROLLED AUTONOMY SUMMARY ==="
echo

git log --oneline -10

echo
echo "=== CURRENT STATUS ==="
git status --short

echo
echo "=== VALIDATION ==="
spot validate

echo
echo "=== GOVERNANCE VALIDATORS ==="

watch/operator/spot-operator.sh learning-validate
watch/operator/spot-operator.sh acceptance-validate
watch/operator/spot-operator.sh remediation-validate
watch/operator/spot-operator.sh rollback-failure-validate
watch/operator/spot-operator.sh sandbox-validate
watch/operator/spot-operator.sh approval-validate
watch/operator/spot-operator.sh failure-validate
watch/operator/spot-operator.sh bundle-validate
watch/operator/spot-operator.sh noop-validate
watch/operator/spot-operator.sh lease-validate
watch/operator/spot-operator.sh rollback-validate
watch/operator/spot-operator.sh receipt-validate
watch/operator/spot-operator.sh chain-validate

echo
echo "=== COMPLETE ==="
