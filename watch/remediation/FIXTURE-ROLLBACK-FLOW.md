# Fixture Rollback Flow

## Trigger
Rollback occurs if:
- install verification fails
- hash mismatch detected
- fixture exits unexpectedly
- journal incomplete
- executor validation fails

## Rollback Actions
- stop fixture if active
- restore unit from verified backup
- restore script from verified backup
- daemon-reload through Spot Core only
- verify fixture inactive or restored
- verify no unrelated service changed

## Required Journal Fields
- rollback_started
- rollback_completed
- rollback_result
- restored_backup_path
