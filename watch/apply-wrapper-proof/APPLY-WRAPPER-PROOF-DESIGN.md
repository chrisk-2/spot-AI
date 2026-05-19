# Phase 3.12 — Dry-Run Apply Wrapper Integration Proof

## Purpose

Prove the dry-run apply-wrapper can consume Phase 3 proof bundles and produce deterministic allow/reject decisions without mutation.

## Inputs

- Phase 3 proof bundle

## Output Root

watch/apply-wrapper-proof/runs/

## Required Cases

### safe_envelope

Expected:
- wrapper_allowed=true
- rejection_reason=null

### unsafe_mutation

Expected:
- wrapper_allowed=false
- rejection_reason=unsafe_mutation

### unsafe_execution

Expected:
- wrapper_allowed=false
- rejection_reason=unsafe_execution

### unsafe_rollback

Expected:
- wrapper_allowed=false
- rejection_reason=unsafe_rollback

### executor_drift

Expected:
- wrapper_allowed=false
- rejection_reason=executor_drift

### worker_self_apply

Expected:
- wrapper_allowed=false
- rejection_reason=worker_self_apply

### codex_mutation

Expected:
- wrapper_allowed=false
- rejection_reason=codex_mutation

### openai_mutation

Expected:
- wrapper_allowed=false
- rejection_reason=openai_mutation

## Forbidden Operations

- no git apply
- no config mutation
- no service restart
- no rollback restore
- no worker execution
- no runtime source-of-truth mutation
