# Controlled Apply Wrapper Design

Phase: 3.0

## Purpose

Create a single Spot Core-controlled entrypoint for repo/config mutations.

Future path:

watch/apply/spot-apply-wrapper.py

## Wrapper Responsibilities

1. Load patch bundle.
2. Validate schema.
3. Verify review PASS.
4. Verify execution_allowed=true.
5. Verify backup binding.
6. Verify rollback definition.
7. Verify validation commands.
8. Verify repo state is clean except allowed runtime exclusions.
9. Verify expected file hashes.
10. Apply patch.
11. Run validators.
12. Commit checkpoint if required.
13. Roll back or halt on failure.
14. Journal final outcome.

## Hard Blocks

The wrapper must reject apply when:

- no review PASS
- no backup binding
- no rollback
- no validation
- repo dirty outside allowed exclusions
- bundle already successfully applied
- target path escapes repo
- patch modifies forbidden files
- worker attempts direct apply

## Authority

Only Spot Core may run apply.
Workers, Codex, W-5, W-6, and OpenAI cannot apply.
