# Phase 2.38 Fixture Heartbeat Contract Review Bundle

## Review Request
Review heartbeat contract remediation only.
Do not authorize execution.

## Context
First live fixture execution succeeded at systemd level but heartbeat verification failed due to missing /tmp heartbeat. This remediation changes heartbeat output to a host-visible dedicated fixture path.

## Required PASS Conditions
- fix is scoped only to fixture artifacts
- unit remains sandboxed
- write path is narrow and explicit
- script remains deterministic
- no production service is touched
- no live execution is authorized
- Spot Core remains sole future executor
- Worker-05 remains proposal_review_only

## Forbidden
- live install
- daemon-reload
- systemctl execution
- backup creation
- journal append
- executor dispatch
- worker-side apply authority

## SPEC
# Phase 2.38 — Fixture Heartbeat Contract Remediation

## Status
POST-LIVE DEFECT REMEDIATION DESIGN

## Defect
The first live fixture execution completed with systemd Result=success and ExecMainStatus=0, but heartbeat verification failed because /tmp/spot-remediation-fixture.heartbeat was not present.

## Likely Cause
The systemd unit uses PrivateTmp=true. The fixture wrote to its private /tmp namespace, while operator verification checked host /tmp.

## Fix
Move heartbeat output to a dedicated host-visible fixture path:

/var/lib/spot/remediation-fixture/heartbeat.json

## Required Unit Change
Allow write access only to:

/var/lib/spot/remediation-fixture

## Required Script Change
Create the heartbeat directory and write heartbeat.json there.

## Explicitly Forbidden
- no production service mutation
- no worker mutation
- no network/DNS/firewall/routing/SSH changes
- no broad filesystem writes
- no execution before review/backup/binding/authorization

## Verification
Future verification must check:

/var/lib/spot/remediation-fixture/heartbeat.json

Expected JSON:
{
  "fixture": "spot-remediation-fixture",
  "status": "ok"
}

## Authority
Spot Core remains sole executor.
Worker-05 remains proposal_review_only.

## UNIT
```ini
[Unit]
Description=Spot Remediation Fixture Service
Documentation=internal:starfleet-phase-2.38
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
ReadWritePaths=/var/lib/spot/remediation-fixture
CapabilityBoundingSet=
RestrictSUIDSGID=true
LockPersonality=true
MemoryDenyWriteExecute=true

[Install]
WantedBy=multi-user.target
```

## SCRIPT
```bash
#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="/var/lib/spot/remediation-fixture"
OUT="${OUT_DIR}/heartbeat.json"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

install -d -m 0755 "$OUT_DIR"
printf '{"fixture":"spot-remediation-fixture","ts":"%s","status":"ok"}\n' "$TS" > "$OUT"
cat "$OUT"
```
