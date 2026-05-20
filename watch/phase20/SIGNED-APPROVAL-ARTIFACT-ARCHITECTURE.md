# Phase 20 — Signed Approval Artifact Architecture

Status: DESIGN-ONLY

## Purpose

Define deterministic approval artifacts that can later be cryptographically
validated without granting autonomous execution authority.

This phase does not authorize:
- production execution
- autonomous mutation
- approval bypass
- routing mutation
- worker execution authority

Spot Core remains sole executor.

---

# Core Model

Approval becomes a structured immutable artifact.

Human approval is no longer represented as:
- freeform text
- transient UI state
- shell confirmation only

Instead:
- approval is represented by a deterministic signed envelope
- approval artifacts are immutable
- approval artifacts are replay-safe
- approval artifacts are scope-bound
- approval artifacts are expiration-bound

---

# Required Properties

Every approval artifact must include:

- artifact_id
- candidate_id
- request_id
- operator_identity
- approval_scope
- approval_targets
- approval_actions
- issued_timestamp
- expiration_timestamp
- governance_hash
- deterministic_content_hash
- signer_identity
- signature_algorithm
- detached_signature
- immutable_receipt_id

---

# Safety Invariants

Mandatory invariants:

- approval does not bypass backup gate
- approval does not bypass rollback gate
- approval does not bypass validation gate
- approval does not bypass review gate
- approval cannot mutate routing ownership
- approval cannot elevate worker authority
- approval cannot authorize self-apply
- approval cannot authorize OpenAI execution
- approval cannot authorize Codex mutation

---

# Replay Protection

Approval artifacts must eventually support:

- nonce binding
- execution lease binding
- candidate hash binding
- expiration enforcement
- immutable receipt linkage

Replay-safe behavior is mandatory.

---

# Future Signing Direction

Future implementations may support:

- minisign
- signify
- age plugin signing
- GPG detached signatures
- hardware-backed signing
- multi-party quorum signatures

Current phase remains design-only.

---

# Enforcement Direction

Future execution wrapper requirements:

- unsigned artifact => reject
- expired artifact => reject
- mismatched candidate hash => reject
- mismatched scope => reject
- mismatched target => reject
- mismatched action => reject
- missing immutable receipt => reject

---

# Mutation Authority

This phase creates:
- schemas
- validators
- deterministic models

This phase does not create:
- live signing enforcement
- live execution authority
- autonomous approval
