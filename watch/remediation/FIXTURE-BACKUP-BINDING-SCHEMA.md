# Fixture Backup Binding Schema

## Required Fields
- binding_id
- timestamp
- target
- service
- reviewed_bundle
- reviewed_hash
- backup_path
- backup_verified
- rollback_defined
- executor_mode
- execution_allowed
- final_state

## Rules
- backup must exist before binding
- binding must exist before execution
- binding must reference immutable reviewed artifacts
- binding must be journaled
- execution without binding is forbidden
