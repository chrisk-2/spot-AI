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
