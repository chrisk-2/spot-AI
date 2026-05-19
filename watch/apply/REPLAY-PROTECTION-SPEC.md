# Replay Protection Spec

Phase: 3.0

## Purpose

Prevent accidental or malicious re-execution of a previously applied patch bundle.

## Required IDs

Every apply transaction must include:

- request_id
- patch_bundle_id
- review_id
- backup_binding_id
- apply_id
- execution_hash

## Replay Rules

- If patch_bundle_id already succeeded, reject.
- If apply_id already exists, reject.
- If execution_hash already succeeded, reject.
- If previous attempt failed, require a new apply_id.
- If previous attempt rolled back, require explicit operator approval before retry.

## Journal Path

Recommended future path:

/mnt/collective/logs/spot/actions/

## Final States

Allowed final states:

- APPLIED
- BLOCKED
- FAILED_VALIDATION
- ROLLED_BACK
- HALTED_FOR_APPROVAL
