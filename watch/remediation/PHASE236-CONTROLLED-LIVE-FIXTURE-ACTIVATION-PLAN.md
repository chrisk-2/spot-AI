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
