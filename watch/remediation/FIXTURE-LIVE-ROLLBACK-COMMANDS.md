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
