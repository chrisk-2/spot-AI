#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OPERATOR="${ROOT}/watch/operator/spot-operator.sh"

echo "===== SPOT GOVERNANCE SENSE ====="
echo "timestamp=$(date -Is)"
echo "host=$(hostname)"
echo "mode=read_only"
echo "mutation_authority=false"
echo

echo "===== LOCKED INVARIANTS ====="
echo "spot_core_sole_executor=true"
echo "worker_self_apply=false"
echo "backup_required_before_mutation=true"
echo "rollback_required_before_execution=true"
echo "review_required_before_apply=true"
echo "high_risk_network_approval_required=true"
echo "openai_execution_authority=false"
echo

echo "===== OPERATOR COMMAND SAFETY MAP ====="
timeout 60 "$OPERATOR" command-map 2>&1 || true
echo

echo "===== REVIEW STATE ====="
timeout 60 "$OPERATOR" review-status 2>&1 || true
echo

echo "===== QUARANTINE STATE ====="
timeout 60 "$OPERATOR" quarantine-status 2>&1 || true
echo

echo "===== GOVERNANCE FILES ====="

CANDIDATES=(
  "spot-core/config/cluster_config.json"
  "spot-core/config/fleet-policy.json"
  "spot-core/config/cloud_policy.json"
  "watch/review/WORKER-05-QC-STANDARD.md"
  "watch/governance"
  "STATE.md"
)

present=0
missing=0

for candidate in "${CANDIDATES[@]}"; do
  path="${ROOT}/${candidate}"

  if [[ -e "$path" ]]; then
    echo "present=${candidate}"
    present=$((present + 1))
  else
    echo "not_present=${candidate}"
    missing=$((missing + 1))
  fi
done

echo
echo "===== CURRENT EXECUTION POSTURE ====="
echo "execution_allowed=false"
echo "live_network_mutation_authorized=false"
echo "firewall_mutation_authorized=false"
echo "dns_mutation_authorized=false"
echo "dhcp_mutation_authorized=false"
echo "vlan_mutation_authorized=false"
echo "routing_mutation_authorized=false"
echo "ssh_access_control_mutation_authorized=false"
echo

echo "summary_governance_artifacts_present=${present}"
echo "summary_optional_or_missing=${missing}"
echo "overall=ENFORCED_READ_ONLY_POSTURE"
echo "mutation_performed=false"
