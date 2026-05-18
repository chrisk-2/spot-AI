# Phase 2.35B Live Fixture Install Review Bundle

## Review Request
Review design artifacts only.
Do not authorize execution.

## Required PASS Conditions
- Spot Core remains sole future executor
- backup-before-action enforced
- rollback-before-execution enforced
- execution remains blocked
- no live mutation occurs
- journal requirements are deterministic

## Forbidden
- live install
- daemon-reload
- service start
- service restart
- backup creation
- executor dispatch
- worker-side apply authority

## DESIGN
# Phase 2.35B — Live Fixture Install Design

## Status
DESIGN REVIEW ONLY

## Goal
Define the controlled installation path for the remediation fixture through Spot Core only.

## Scope
This phase defines:
- installation workflow
- backup binding requirements
- rollback workflow
- journal requirements
- executor boundaries

No live installation occurs in this phase.

## Explicitly Forbidden
- no systemctl enable
- no systemctl start
- no daemon-reload
- no live backup writes
- no service mutation
- no executor dispatch
- no worker-side apply authority

## Required Future Live Chain
Review PASS
-> backup artifact creation
-> backup verification
-> binding record creation
-> Spot Core executor validation
-> controlled install
-> verification
-> rollback-or-success journal

## Install Targets
Future install targets only:
- /etc/systemd/system/spot-remediation-fixture.service
- /usr/local/lib/spot/spot-remediation-fixture.sh

## Verification Requirements
- unit hash matches reviewed artifact
- script hash matches reviewed artifact
- fixture service remains isolated/sandboxed
- no unrelated unit changes
- journal records complete chain

## Authority
Spot Core remains sole future execution authority.
Worker-05 remains proposal_review_only.
execution_allowed remains false.

## BINDING
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

## ROLLBACK
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

## JOURNAL
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
