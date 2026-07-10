#!/usr/bin/env bash
set -Eeuo pipefail

cat <<'MAP'
===== SPOT OPERATOR COMMAND MAP =====
mode=read_only
mutation_authority=false
spot_core_sole_executor=true

READ-ONLY COMMANDS
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
  starfleet-edge-01 DNS unresolved until intentionally restored or removed.
  unimatrix6 may reject ogre SSH while storage access works.
  starfleet-ui/public/status.json is runtime drift and must not be committed.

NEXT STAGE-2 TARGETS
  1. Add focused operator subcommands for routing, review, quarantine, and logs.
  2. Expose command map in UI/operator panel.
  3. Make read-only network diagnostics visible.
MAP
