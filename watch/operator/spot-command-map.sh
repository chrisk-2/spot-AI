#!/usr/bin/env bash
set -Eeuo pipefail

cat <<'MAP'
===== SPOT OPERATOR COMMAND MAP =====
mode=read_only
mutation_authority=false
spot_core_sole_executor=true

READ-ONLY COMMANDS
  ./watch/operator/spot-operator.sh network-senses
    Purpose: Run aggregate read-only network senses.
    Risk: none.
    Mutation: none.

  ./watch/operator/spot-operator.sh dns-sense
    Purpose: Show DNS resolver and name-resolution health.
    Risk: none.
    Mutation: none.

  ./watch/operator/spot-operator.sh gateway-sense
    Purpose: Show gateway/path reachability.
    Risk: none.
    Mutation: none.

  ./watch/operator/spot-operator.sh service-sense
    Purpose: Show local and fleet service reachability.
    Risk: none.
    Mutation: none.

  ./watch/operator/spot-operator.sh routing
    Purpose: Show routing audit status and role owners.
    Risk: none.
    Mutation: none.

  ./watch/operator/spot-operator.sh review-status
    Purpose: Show review gate and review log status.
    Risk: none.
    Mutation: none.

  ./watch/operator/spot-operator.sh quarantine-status
    Purpose: Show quarantine/eligibility state.
    Risk: none.
    Mutation: none.

  ./watch/operator/spot-operator.sh operator-logs
    Purpose: Show Spot action/review/backup/rollback log status.
    Risk: none.
    Mutation: none.

  ./watch/operator/spot-operator.sh overview
    Purpose: Show fleet/operator overview.
    Risk: none.
    Mutation: none.
    Safe for routine use.

  ./watch/operator/spot-operator.sh status
    Purpose: Show Spot operator/API status.
    Risk: none.
    Mutation: none.
    Safe for routine use.

  ./watch/operator/spot-overview.sh
    Purpose: Direct overview command.
    Risk: none.
    Mutation: none.
    Safe for routine use.


APPEND-ONLY THINKING COMMANDS
  ./watch/operator/spot-operator.sh situation-assessment
    Purpose: Classify the current operational situation.
    Risk: none.
    Mutation: append-only thinking memory only.
    Boundary: no approval or execution authority.

  ./watch/operator/spot-operator.sh drift-detection
    Purpose: Compare verified situation assessments.
    Risk: none.
    Mutation: append-only thinking memory only.
    Boundary: no routing, ownership, or service mutation.

  ./watch/operator/spot-operator.sh risk-assessment
    Purpose: Score operational risk deterministically.
    Risk: none.
    Mutation: append-only thinking memory only.
    Boundary: risk classification cannot authorize execution.

  ./watch/operator/spot-operator.sh operational-reasoning
    Purpose: Generate advisory operational recommendations.
    Risk: none.
    Mutation: append-only thinking memory only.
    Boundary: proposal-only; no self-approval or auto-apply.

  ./watch/operator/spot-operator.sh thinking-loop
    Purpose: Run situation, drift, risk, and reasoning in order.
    Risk: none.
    Mutation: append-only thinking memory only.
    Boundary: execution_allowed=false and mutation_authority=false.

  ./watch/operator/spot-operator.sh thinking-status
    Purpose: Show the latest verified Thinking Loop state.
    Risk: none.
    Mutation: none.
    Safe for routine use.

VALIDATION-ONLY COMMANDS
  ./watch/operator/spot-operator.sh validate
    Purpose: Run normal fleet validation.
    Risk: low.
    Mutation: validator may append audit/runtime status.
    Safe because it does not alter worker config or services.

  ./watch/operator/spot-operator.sh smoke
    Purpose: Run quarantine/release smoke validation.
    Risk: low/controlled.
    Mutation: temporary runtime quarantine state only.
    Boundary: must release worker and validate no restart required.

CONTROLLED ACTION COMMANDS
  Quarantine / release / recovery / remediation commands
    Purpose: Controlled operational action.
    Risk: medium unless otherwise classified.
    Required: action log, backup where applicable, validation, rollback path.
    Boundary: Spot Core remains sole authority.

RESTRICTED / HIGH-RISK ACTIONS
  Firewall, VLAN, DNS, DHCP, routing, gateway, SSH access-control changes
    Risk: high.
    Required: explicit approval, backup, review, rollback, validation.
    Boundary: no autonomous execution.

FORBIDDEN BY POLICY
  Worker self-apply.
  Execution without backup when mutating state.
  Execution without rollback definition.
  Hidden mutation paths.
  OpenAI/Codex direct mutation.
  Bypassing Spot Core.

CURRENT KNOWN NON-BLOCKERS
  starfleet-edge-01 is registered as a read-only, non-routing recovery edge.
  unimatrix6 may reject ogre SSH while storage access works.
  starfleet-ui/public/status.json is runtime drift and must not be committed.

NEXT STAGE-2 TARGETS
  1. Expose command map in UI/operator panel.
  2. Promote read-only network senses into diagnostics summaries.
  3. Begin structured incident timeline from existing logs.
MAP
