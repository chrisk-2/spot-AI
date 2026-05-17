# Backup Creation Design

## Purpose

This document defines the design for Spot Core live backup creation.

Current phase: Phase 2.30 design review only.

This file does not authorize implementation, live source reads, live hashing, backup creation, backup binding, executor dispatch, service restart, or config mutation.

## Rule

No backup, no change.

Before any mutating action, Spot Core must create and verify a pre-change backup.

The backup must exist before execution.

The backup path must be recorded before execution.

If backup creation or verification fails, the action is blocked.

## Authority

Spot Core owns backup creation.

Workers may plan, propose, or review backup logic.

Workers may not create, delete, overwrite, bind, or apply backups.

Codex is proposal-only.

OpenAI is manual review-only.

## Backup target

Primary backup root:

```text
/mnt/collective/backups/
```

Required target pattern:

```text
/mnt/collective/backups/<target>/<service>/<timestamp>/
```

Timestamp format:

```text
YYYYMMDD-HHMMSSZ
```

## Required backup artifacts

Each backup must eventually contain:

```text
metadata.json
checksums.json or verification-marker.json
backup-created.log
source artifact copies or approved export artifacts
```

Phase 2.30 only designs these artifacts. It does not create them.

## Backup lifecycle

Required future lifecycle:

```text
classify action
resolve target and service
resolve source set
create unique backup directory
copy approved artifacts
write metadata
write checksum or verification marker
verify readability
write backup journal record
expose backup_path to action preflight
```

## Forbidden behavior

Backup creation must never:

- overwrite existing backups
- delete backups
- rename backups
- mutate source files
- perform remediation
- restart services
- write config changes
- dispatch executor actions
- run through Codex directly
- run through any worker directly

## Failure behavior

Any backup failure blocks execution.

Blocking failures include:

- backup root unavailable
- backup directory already exists
- source path missing
- source path outside allowed set
- copy failure
- metadata failure
- checksum or marker failure
- readability verification failure
- journal failure when journal-before-execute is required

## Phase 2.30 allowed work

Allowed:

- design documents
- metadata schema
- failure cases
- review standards
- learning-loop design
- W-5 review of this design

Forbidden:

- live backup creation
- live source reads
- live source hashing
- backup binding
- executor dispatch
- config writes
- service restarts

## W-5 review requirements

Worker-05 must verify:

- this design stays in Phase 2.30 scope
- Spot Core remains the only backup authority
- workers cannot create or modify backups
- Codex cannot mutate
- OpenAI cannot execute
- backup overwrite/delete is forbidden
- failure behavior is fail-closed
- no implementation is included

## Exit criteria

This design is complete when:

- W-5 returns PASS for design review
- metadata schema exists
- failure cases exist
- no implementation was added
- readiness checkpoint remains clean
