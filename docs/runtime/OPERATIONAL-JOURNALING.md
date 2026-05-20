# Operational Journaling Completion

Operational journaling is read-only visibility over Spot runtime records.

## Authority Boundary

- Spot Core remains the only executor.
- This lane grants no mutation authority.
- Journal visibility does not bypass review, backup, approval, rollback, or policy gates.
- Missing journal roots are warnings.
- Invalid JSON or JSONL journal content is a validation failure.

## Journal Roots

- `/mnt/collective/logs/spot`
- `watch/state`
- `watch/apply/journals`

## Operator Commands

- `watch/journal/spot-journal-status.py`
- `watch/journal/spot-journal-validate.py`

## API Endpoint

- `GET /stats/runtime/journals?limit=5`

## Expected Result

The operator can inspect runtime journal health without touching execution paths.
