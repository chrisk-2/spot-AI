# Phase 2.35A — Fixture Implementation Spec

## Status
IMPLEMENTATION ARTIFACT REVIEW ONLY

## Goal
Create repo-staged fixture artifacts for a disposable low-risk systemd remediation target.

## Target
spot-remediation-fixture.service

## Scope
This phase creates source artifacts only.

## Explicitly Forbidden
- no systemd install
- no daemon-reload
- no service start/restart
- no live backup writes
- no executor dispatch
- no production service changes
- no worker-side apply authority

## Fixture Behavior
The fixture script is harmless and deterministic:
- writes a timestamped heartbeat under /tmp only
- exits success
- has no network access requirement
- changes no production config
- provides a safe future restart target

## Future Live Gate Requirements
Before any live service install/restart:
- Worker-05 implementation review PASS
- Spot Core only execution path
- backup artifact created and verified
- backup binding record created
- journal record created
- rollback path defined
- spot validate PASS

## Rollback Design
If the fixture is installed in a future phase:
- stop fixture service if active
- restore/remove only fixture unit according to recorded backup/binding
- daemon-reload only through Spot Core executor
- verify no unrelated service changed

## Authority
Spot Core remains the only future apply authority.
Worker-05 remains proposal_review_only.
execution_allowed remains false in this phase.
