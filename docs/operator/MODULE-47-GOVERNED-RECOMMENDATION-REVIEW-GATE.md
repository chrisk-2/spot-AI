# Module 47 — Governed Recommendation Review Gate

## Purpose

Module 47 converts a verified Thinking Loop recommendation and its correlated
immutable W-05 review record into one deterministic eligibility decision.

The only successful decision is:

`ELIGIBLE_FOR_NEXT_GATE`

This does not mean eligible for execution.

## Required current evidence

- fresh Thinking Loop status
- healthy overall Thinking state
- verified situation, drift, risk, and reasoning states
- advisory-only recommendation
- immutable local review journal
- W-05 reviewer identity
- `PASS|FIX|NO` verdict
- matching deterministic proposal identity
- `proposal_review_only` authority
- `execution_allowed=false`
- `result_blocked=true`

Missing, stale, malformed, mismatched, `FIX`, or `NO` evidence fails closed.

## Future Controlled Hands gates

Eligibility only permits progression toward:

1. backup binding
2. rollback binding
3. approval when required
4. execution lease and TTL
5. execution window
6. replay-safe token
7. execution quorum
8. validation
9. immutable execution receipt
10. receipt chain
11. execution journal

None of these gates is bypassed or created by the eligibility evaluator.

## Locked safety state

- Spot Core remains sole executor.
- Workers cannot self-apply.
- W-05 review cannot authorize execution.
- OpenAI and Codex remain proposal/review-only.
- No backup means no change.
- No rollback means no execution.
- Step 6 remains unauthorized.
- `execution_allowed=false`
- `mutation_authority=false`
- `mutation_performed=false`

## Files

- `watch/review/recommendation-review-eligibility.py`
- `watch/review/recommendation-review-eligibility-validate.py`

The evaluator reads supplied evidence and writes JSON only to stdout. It does
not request reviews or write persistent artifacts.

## Immutable gate runner

The gate runner captures the current Thinking status, derives its deterministic
proposal identity, and searches the append-only local review history for the
latest record with the same `request_id`.

It does not request a review. Missing or mismatched review evidence remains
blocked.

Each persisted gate decision is created once under:

`/mnt/collective/logs/spot/reviews/recommendation-review-gate/`

Records are mode `0444`, are never overwritten, and contain both the correlated
evidence state and the complete fail-closed eligibility result.

The gate journal records only the decision produced by the evaluator. It is not
an approval journal, execution journal, backup, rollback binding, lease, token,
receipt, or mutation authorization.

## Operator commands

- `recommendation-review-gate`
  - evaluates the current Thinking recommendation
  - reads existing correlated review evidence
  - appends one immutable gate-decision record
  - does not request review or dispatch execution

- `recommendation-review-status`
  - reads the latest immutable gate record
  - performs no persistent write

- `recommendation-review-validate`
  - validates correlation, immutability, blocked behavior, and safety lockouts

## Current authority boundary

A Worker-05 `PASS` verdict establishes review eligibility only.

While Controlled Hands Step 6 remains unauthorized:

- review evidence must use `authority=proposal_review_only`
- review evidence must retain `execution_allowed=false`
- gate eligibility cannot authorize execution
- backup and rollback binding remain the next required gate
- Spot Core remains sole executor
- workers cannot self-apply
