# Backup Failure Cases

## Purpose

This document defines backup failure cases that must block execution.

Current phase: Phase 2.30 design review only.

This file defines required failure behavior only. It does not implement backup creation, read live source files, hash live source files, bind backups, dispatch executors, or mutate configuration.

## Failure principle

Backup failure must fail closed.

If Spot cannot prove that a required backup exists, is verified, and is recorded before execution, Spot Core must block the mutating action.

## Required rejected cases

The future backup implementation must reject these cases.

### backup_root_unavailable

Condition:

```text
/mnt/collective/backups/ is unavailable or not writable for approved backup creation.
```

Expected result:

```text
block execution
record failure
no mutation
```

### backup_directory_already_exists

Condition:

```text
target backup directory already exists
```

Expected result:

```text
block execution
do not reuse directory
do not overwrite existing backup
```

### source_path_missing

Condition:

```text
declared source path does not exist
```

Expected result:

```text
block execution
record missing source
```

### source_path_outside_allowed_set

Condition:

```text
source path is outside the approved source set
```

Expected result:

```text
block execution
record policy violation
```

### unrestricted_source_requested

Condition:

```text
source request includes /, /home, /etc, broad glob, or unbounded recursive copy
```

Expected result:

```text
block execution
record unsafe scope
```

### copy_failure

Condition:

```text
approved source cannot be copied to backup directory
```

Expected result:

```text
block execution
record copy failure
```

### metadata_missing

Condition:

```text
metadata.json was not created
```

Expected result:

```text
block execution
record metadata failure
```

### metadata_invalid_schema

Condition:

```text
metadata.json lacks schema or required fields
```

Expected result:

```text
block execution
record schema failure
```

### metadata_path_mismatch

Condition:

```text
metadata backup_path does not match actual backup directory
```

Expected result:

```text
block execution
record mismatch
```

### checksum_missing

Condition:

```text
checksum or verification marker is absent
```

Expected result:

```text
block execution
record verification failure
```

### checksum_mismatch

Condition:

```text
checksum verification fails
```

Expected result:

```text
block execution
record checksum mismatch
```

### backup_unreadable

Condition:

```text
backup artifact exists but cannot be read back
```

Expected result:

```text
block execution
record readability failure
```

### journal_write_failure

Condition:

```text
required backup journal entry cannot be written before execution
```

Expected result:

```text
block execution when journal-before-execute is required
record journal failure if possible
```

### worker_attempted_backup

Condition:

```text
W-3, W-4, W-5, W-6, Codex, or OpenAI attempts to create or bind backup directly
```

Expected result:

```text
block execution
record authority violation
```

### backup_after_execution

Condition:

```text
backup timestamp is after action execution timestamp
```

Expected result:

```text
block or invalidate action
record ordering violation
```

### backup_delete_or_overwrite_attempt

Condition:

```text
operation attempts to delete, overwrite, rename, or modify existing backup history
```

Expected result:

```text
block execution
record hard policy violation
```

## Required non-mutation assertions

Every failure test must assert:

```text
mutation_performed == false
execution_performed == false
source_modified == false
service_restarted == false
network_mutated == false
```

## Phase 2.30 validation

Phase 2.30 only requires design review of these cases.

No failure harness implementation is authorized by this document.

## Later implementation validation

Future implementation phases must include fixture-based failure tests for each rejected case.

The tests must prove:

- the unsafe case is rejected
- no source file is modified
- no executor dispatch occurs
- no service restart occurs
- no network change occurs
- the failure is journaled or reported

## W-5 review requirements

Worker-05 must verify:

- all major backup failure classes are represented
- failures block execution
- backup history cannot be overwritten or deleted
- workers and providers cannot create backups directly
- ordering requires backup before execution
- failure tests require non-mutation assertions
- this document contains no implementation

## Exit criteria

This failure case design is complete when:

- W-5 returns PASS for design review
- backup creation design references these cases
- metadata schema supports these cases
- no implementation was added
