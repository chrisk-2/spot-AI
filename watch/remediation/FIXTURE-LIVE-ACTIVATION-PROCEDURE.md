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
