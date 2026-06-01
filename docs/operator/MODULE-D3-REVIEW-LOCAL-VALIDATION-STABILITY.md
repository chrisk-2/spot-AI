# Module D3 — Review Local Validation Stability

## Scope

Normalize `/review/local` validation so normal `spot validate` checks route health without invoking a long-running reviewer job.

## Reason

The prior validation path submitted a review request and waited up to 30 seconds. That made validator output noisy when the local reviewer was busy even though the route itself was alive.

## New behavior

- `watch/review/review-local-health.py` checks `/review/local` reachability.
- HTTP 405 or similar non-GET responses count as healthy route presence.
- Full review execution remains separate from fleet validation.

## Boundaries

This module does not:

- change review authority
- bypass Worker-05 review policy
- allow execution
- change worker ownership
- touch UI files
- mutate runtime state

## Expected validation

`spot validate` should no longer wait 30 seconds on `/review/local`.

Expected line:

`[PASS] /review/local route reachable`
