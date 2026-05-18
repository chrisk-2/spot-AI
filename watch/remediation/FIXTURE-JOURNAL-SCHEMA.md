# Fixture Journal Schema

## Required Fields
- ts
- request_id
- action_id
- phase
- target
- service
- reviewed_bundle
- reviewed_hash
- backup_path
- binding_id
- executor_mode
- verification_result
- rollback_result
- final_outcome

## Constraints
- append-only
- immutable history
- no overwrite
- no delete
