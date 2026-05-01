
## 2026-05-01 Spot Assistant Checkpoint

Completed:
- D.1 Spot ask interface with routed worker/model execution.
- D.2 Saved proposal workflow.
- D.3 Proposal lifecycle: approve, reject, status.
- D.3b Approved patch artifact generation.
- D.5 Persistent shared memory on Unimatrix at /mnt/collective/spot/memory.
- D.5c searchable recall via spot recall.
- D.5d automatic memory injection into ask/propose.
- D.5e lifecycle memory capture with duplicate suppression.
- D.6 proposal historical awareness using prior proposals and patch artifacts.
- Proposal guardrail scanner added for forbidden invented paths/services.

Current approved pending work:
- P-20260501-133615-revise-routing-so-utility-role-remains-primary-o
- Patch artifact: PATCH-P-20260501-133615-revise-routing-so-utility-role-remains-primary-o.md

Known issue:
- worker-02 utility lane remains high-latency and can intermittently cause validation 503s.
- Proposed mitigation: keep worker-02 as utility primary but add worker-01 as utility fallback.

Policy:
- Spot Autonomy Policy and Safety Model is the governing execution model.
- Locked rule: No backup, no change.
- D.4a must implement supervised apply-plan plus backup-first execution wrapper before any config mutation.

Next:
- Build D.4a supervised apply-plan engine.
- Enforce Detect -> Analyze -> Classify -> Backup -> Plan -> Verify -> Execute -> Test/Rollback chain.
