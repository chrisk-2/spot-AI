# Backup Metadata Schema

## Purpose

This document defines the required metadata fields for future Spot Core backup artifacts.

Current phase: Phase 2.30 design review only.

This file defines schema only. It does not create backups, read live source files, hash live source files, bind backups, dispatch executors, or mutate configuration.

## Metadata file

Required filename:

```text
metadata.json
```

Required future location:

```text
/mnt/collective/backups/<target>/<service>/<timestamp>/metadata.json
```

## Required schema identity

Every metadata file must include:

```json
{
  "schema": "spot.backup.metadata.v1"
}
```

## Required fields

Required top-level fields:

```text
schema
backup_id
request_id
action_id
target
service
risk_class
phase
backup_path
source_paths
created_utc
created_by
policy_decision
checksum_summary
verification_result
rollback_reference
notes
```

## Field definitions

### schema

Must identify the metadata schema version.

Expected value:

```text
spot.backup.metadata.v1
```

### backup_id

Unique backup identifier.

Recommended format:

```text
BACKUP-<target>-<service>-<YYYYMMDD-HHMMSSZ>
```

### request_id

Identifier for the originating user request, alert, or remediation event.

### action_id

Identifier for the planned action.

May be null during early planning, but must be populated before backup binding.

### target

System or host being protected.

Examples:

```text
spot-core
spot-worker-03
opnsense
```

### service

Service or subsystem being protected.

Examples:

```text
spot-mcp
fleet-watch
ollama
nginx
```

### risk_class

Allowed values:

```text
LOW
MEDIUM
HIGH
```

### phase

Current autonomy phase.

Example:

```text
2.32
```

### backup_path

Absolute path to the backup directory.

Must match the created backup directory.

### source_paths

Array of explicitly approved source paths or artifact identifiers.

Must not contain unrestricted root paths, broad home directories, or unbounded globs.

### created_utc

UTC timestamp of backup creation.

Format:

```text
YYYYMMDD-HHMMSSZ
```

### created_by

Expected value for autonomous backup creation:

```text
spot-core
```

Workers and providers must not be listed as backup creators.

### policy_decision

Object recording policy status at backup time.

Required keys:

```text
backup_required
backup_allowed
mutation_allowed
execution_allowed
approval_required
```

### checksum_summary

Object recording checksum or marker status.

Required keys:

```text
method
artifact_count
checksum_file
status
```

### verification_result

Object recording backup verification result.

Required keys:

```text
verified
verified_utc
readable
required_artifacts_present
metadata_path_matches
errors
```

### rollback_reference

Object describing how rollback can locate the artifact later.

Required keys:

```text
rollback_supported
backup_path
restore_notes
```

### notes

Short free-text notes.

Must not contain secrets, tokens, passwords, private keys, or raw credentials.

## Forbidden metadata content

metadata.json must not include:

- passwords
- API keys
- private keys
- session tokens
- OAuth tokens
- raw secret file contents
- unrestricted environment dumps
- unrelated host inventory
- unbounded command output

## Minimal example

```json
{
  "schema": "spot.backup.metadata.v1",
  "backup_id": "BACKUP-spot-core-spot-mcp-20260517-060000Z",
  "request_id": "REQ-20260517-001",
  "action_id": "ACT-20260517-001",
  "target": "spot-core",
  "service": "spot-mcp",
  "risk_class": "LOW",
  "phase": "2.32",
  "backup_path": "/mnt/collective/backups/spot-core/spot-mcp/20260517-060000Z/",
  "source_paths": ["/home/ogre/spot-stack/example.conf"],
  "created_utc": "20260517-060000Z",
  "created_by": "spot-core",
  "policy_decision": {
    "backup_required": true,
    "backup_allowed": true,
    "mutation_allowed": false,
    "execution_allowed": false,
    "approval_required": false
  },
  "checksum_summary": {
    "method": "sha256",
    "artifact_count": 1,
    "checksum_file": "checksums.json",
    "status": "present"
  },
  "verification_result": {
    "verified": true,
    "verified_utc": "20260517-060010Z",
    "readable": true,
    "required_artifacts_present": true,
    "metadata_path_matches": true,
    "errors": []
  },
  "rollback_reference": {
    "rollback_supported": true,
    "backup_path": "/mnt/collective/backups/spot-core/spot-mcp/20260517-060000Z/",
    "restore_notes": "Use approved rollback wrapper only."
  },
  "notes": "Example schema record only."
}
```

## W-5 review requirements

Worker-05 must verify:

- schema is explicit
- required fields are sufficient
- backup creator remains Spot Core
- metadata does not authorize execution
- metadata does not contain secrets
- metadata supports later backup binding and rollback
- metadata cannot be used to bypass policy

## Exit criteria

This schema is complete when:

- W-5 returns PASS for design review
- failure cases reference this schema
- backup creation design references this schema
- no implementation was added
