# Phase 2.36 Controlled Live Fixture Activation Review Bundle

## Review Request
Review activation-plan artifacts only.
Do not authorize execution.

## Required PASS Conditions
- no executable live commands exist
- no production services are touched
- rollback remains design-only
- backup/binding requirements remain enforced
- Spot Core remains sole future executor
- execution_allowed remains false

## Forbidden
- install commands
- rollback commands
- daemon-reload
- systemctl execution
- backup creation
- executor dispatch
- worker-side apply authority

## PLAN
# Phase 2.36 — Controlled Live Fixture Activation Plan

## Status
LIVE ACTIVATION PLAN REVIEW ONLY

## Goal
Define the first controlled live fixture activation path without executing it.

## Target
spot-core only.

Fixture paths:
- /etc/systemd/system/spot-remediation-fixture.service
- /usr/local/lib/spot/spot-remediation-fixture.sh

## Risk Class
Low

## Future Allowed Mutation
Only after review PASS and explicit operator approval:
- install fixture unit
- install fixture script
- daemon-reload
- run oneshot fixture service
- verify heartbeat
- journal result

## Explicitly Forbidden In This Phase
- no live file writes
- no mkdir under /usr/local/lib/spot
- no copy to /etc/systemd/system
- no chmod live path
- no daemon-reload
- no systemctl start
- no service restart
- no backup writes
- no journal append
- no executor dispatch

## Required Gates Before Future Live Activation
- reviewed source artifact hashes match
- backup artifact created and verified
- backup binding record created
- rollback path recorded
- Spot Core executor selected
- execution_allowed true only after explicit operator approval
- Worker-05 remains review-only
- spot validate PASS before and after

## PROCEDURE
# Fixture Live Activation Procedure

## Preflight
- confirm repo clean except known untracked UI files
- confirm reviewed fixture artifacts exist
- confirm reviewed bundle hash matches sha256 file
- confirm Spot Core health
- confirm spot validate PASS

## Backup
Create backup path:
/mnt/collective/backups/spot-core/spot-remediation-fixture/<timestamp>/

Backup any existing:
- /etc/systemd/system/spot-remediation-fixture.service
- /usr/local/lib/spot/spot-remediation-fixture.sh

If files do not exist, record missing_source=true in metadata.

## Binding
Create binding record before install:
- reviewed bundle
- reviewed hash
- backup path
- backup verification status
- rollback commands
- execution mode


## Future Execution Placeholder

Live install commands are intentionally omitted in this review-only phase.

A later execution-authorized phase may define:
- install commands
- daemon-reload commands
- activation commands
- rollback execution commands

Only after:
- explicit operator approval
- Worker-05 PASS
- backup verification
- binding verification
- execution_allowed=true

## VERIFY
# Fixture Live Verify Commands

## Pre-activation
test -s watch/remediation/spot-remediation-fixture.sh
test -s watch/remediation/spot-remediation-fixture.service
bash -n watch/remediation/spot-remediation-fixture.sh
sha256sum -c watch/review/bundles/phase235a-fixture-implementation-review-bundle-*.md.sha256
spot validate

## Post-activation
systemctl is-active --quiet spot-remediation-fixture.service || systemctl status spot-remediation-fixture.service --no-pager
test -s /tmp/spot-remediation-fixture.heartbeat
jq -e '.fixture=="spot-remediation-fixture" and .status=="ok"' /tmp/spot-remediation-fixture.heartbeat
systemctl show spot-remediation-fixture.service -p Result -p ExecMainStatus --no-pager
spot validate

## ROLLBACK
# Fixture Live Rollback Design

## Status
ROLLBACK DESIGN ONLY

## Scope
Defines rollback intent and rollback boundaries only.

## Allowed Scope
Only fixture paths may eventually be restored or removed:
- /etc/systemd/system/spot-remediation-fixture.service
- /usr/local/lib/spot/spot-remediation-fixture.sh
- /tmp/spot-remediation-fixture.heartbeat

## Rollback Requirements
- rollback must remain Spot Core controlled
- rollback must require verified backup metadata
- rollback must require binding verification
- rollback must be journaled
- rollback must verify no unrelated services changed

## Explicitly Forbidden In This Phase
- no rollback execution
- no daemon-reload
- no systemctl stop/start
- no file deletion
- no restore action
