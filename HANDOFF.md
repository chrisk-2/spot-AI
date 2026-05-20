# STARFLEET HANDOFF — 2026-05-07

Read order:
1. HANDOFF.md
2. spot-core/STATE.md

---

## SAFE RESUME POINT

System stable.
Fleet validation currently PASS.

Git tree should be clean before handoff completion.

Current active lane:
- PHASE 2 — BUILD SPOT CONTROLLED AUTONOMY

Phase 1.7 baseline locked.
Phase 2.1 through Phase 2.30 complete and non-mutating.

Production routing ownership locked:

```text
general -> spot-worker-01
utility -> spot-worker-02
coding  -> spot-worker-03
heavy   -> spot-worker-04

---

## PHASE 6 ACTIVE LANE — 2026-05-20

Phase 6 supervised operational autonomy begins with controlled fixture-service orchestration only.

Allowed:
- fixture service lifecycle simulation
- controlled supervisor state transitions
- governed apply queue simulation
- rollback continuity across supervised fixture operations
- execution lease expiration handling

Forbidden:
- production service mutation
- network/firewall/DNS/DHCP/routing mutation
- worker self-apply
- Codex mutation
- OpenAI mutation
- git apply in live environment
- service restart autonomy against production services

Expected intentional dirty runtime-only state:
- starfleet-ui/public/status.json
- watch/apply/journals/
- watch/phase6/runs/


---

## PHASE 6 COMPLETION TARGET — 2026-05-20

Phase 6 is complete only after:

watch/phase6/spot-phase6-full-validate.py

returns:

RESULT: PASS
cases=15 fixture_service_lifecycle=pass supervised_state_transitions=pass governed_apply_queue=pass backup_gate=pass rollback_gate=pass validation_gate=pass rollback_continuity=pass lease_expiration=pass replay_guard=pass target_escape=pass worker_self_apply=pass journal_records=pass mutation_scope=fixture_only

Phase 6 remains fixture-only and does not authorize production service mutation.
