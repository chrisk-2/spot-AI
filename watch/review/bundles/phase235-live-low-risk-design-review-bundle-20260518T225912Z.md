# Phase 2.35 Design Review Bundle

## Current Phase
Phase 2.35 — First live low-risk remediation design

## Review Request
Review this design only. Do not authorize execution.

## Required Verdict
PASS only if:
- target is low-risk
- no live action is requested
- Spot Core remains sole apply authority
- backup, verification, rollback, and journal requirements are defined
- execution_allowed remains false

## Forbidden
- live source reads
- live backup writes
- service restart
- config mutation
- executor dispatch
- worker-side apply authority

## Artifact

# Phase 2.35 — First Live Low-Risk Remediation Design

## Status
DESIGN REVIEW ONLY

## Goal
Define the first live low-risk remediation target for Spot Core without executing it.

## Candidate Target
A dedicated disposable systemd test service on spot-core.

Suggested service name:
spot-remediation-fixture.service

## Risk Class
Low

## Allowed Future Action
Restart only the disposable fixture service through Spot Core after all gates pass.

## Forbidden
- no production service restart
- no worker config change
- no Ollama mutation
- no DNS/firewall/VLAN/routing/SSH changes
- no direct worker execution
- no W-3/W-4/W-5/W-6 apply authority
- no execution before backup binding exists

## Required Chain
Detect -> Analyze -> Classify -> Backup -> Plan -> Review -> Verify -> Execute through Spot Core only -> Test -> Rollback/Halt -> Journal

## Backup Requirement
Before any future restart/remediation, Spot Core must create and verify a backup artifact for the fixture service definition and metadata.

Backup target pattern:
/mnt/collective/backups/spot-core/spot-remediation-fixture/<timestamp>/

## Verification
Pre-check:
- service exists
- service is intentionally marked as fixture/sandbox
- service unit hash recorded
- backup artifact readable

Post-check:
- systemctl is-active spot-remediation-fixture.service returns active
- journal records action result
- no unrelated services changed

## Rollback
If verification fails:
- restore fixture unit from backup if modified
- daemon-reload if required
- restart fixture service or halt if restart fails
- record rollback result

## Authority
Spot Core only may execute future live action.
Worker-05 may review only.
Review authority remains proposal_review_only.
execution_allowed remains false for this design gate.

## Exit Criteria for Design Gate
- Worker-05 returns PASS
- execution_allowed remains false
- authority remains proposal_review_only
- spot validate remains PASS
