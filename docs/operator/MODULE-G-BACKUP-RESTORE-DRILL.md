# Module G — Backup Restore Drill

## Scope

Define backup restore drill artifacts without restoring any live backup.

## Purpose

Verify that each worker has a documented restore path from backup to validated fleet membership.

## Boundaries

This module does not:

- restore backups
- overwrite files
- delete backups
- rebuild hosts
- mutate source systems

## Drill proof fields

- worker
- role
- backup_source
- restore_target
- restore_mode
- validation_commands
- halt_criteria
