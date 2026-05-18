# Phase 2.35A Fixture Implementation Review Bundle

## Review Request
Review source artifacts only. Do not authorize execution.

## Required Verdict
PASS only if:
- artifacts are sandbox/fixture scoped
- no live install/start/restart is performed
- no production service is touched
- systemd unit is constrained
- script is deterministic and harmless
- Spot Core remains sole future apply authority
- execution_allowed remains false

## Forbidden
- live source reads
- live backup writes
- systemd mutation
- daemon-reload
- service start/restart
- executor dispatch
- worker-side apply authority

## Spec
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

## Unit
```ini
[Unit]
Description=Spot Remediation Fixture Service
Documentation=internal:starfleet-phase-2.35a
ConditionPathExists=/usr/local/lib/spot/spot-remediation-fixture.sh

[Service]
Type=oneshot
ExecStart=/usr/local/lib/spot/spot-remediation-fixture.sh
User=root
Group=root
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/tmp
CapabilityBoundingSet=
RestrictSUIDSGID=true
LockPersonality=true
MemoryDenyWriteExecute=true

[Install]
WantedBy=multi-user.target
```

## Script
```bash
#!/usr/bin/env bash
set -euo pipefail

OUT="/tmp/spot-remediation-fixture.heartbeat"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

printf '{"fixture":"spot-remediation-fixture","ts":"%s","status":"ok"}\n' "$TS" > "$OUT"
cat "$OUT"
```
