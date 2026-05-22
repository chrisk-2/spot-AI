# Milestone C — Review Journaling and Audit Visibility

## Purpose

Persist local review results as auditable review artifacts without granting mutation authority.

## Added Commands

- `watch/operator/spot-operator.sh review-journal`
- `watch/operator/spot-operator.sh review-journal-validate`
- `watch/operator/spot-operator.sh reviews [N]`
- `watch/operator/spot-operator.sh reviews-tail`
- `watch/operator/spot-operator.sh governance [N]`

## Journal Root

Default path:

`/mnt/collective/logs/spot/reviews`

## Review Artifact Fields

Each review journal includes:

- `ts`
- `ts_utc`
- `request_id`
- `provider`
- `reviewer`
- `model`
- `review_type`
- `verdict`
- `execution_allowed`
- `result_blocked`
- `authority`
- `confidence`
- `review_bundle_sha256`
- `raw_response_sha256`
- `review_bundle`
- `raw_response`
- `journal_path`

## Safety Boundaries

- This lane adds journal visibility only.
- This lane does not add mutation authority.
- Review PASS does not authorize execution.
- `proposal_review_only` must keep `execution_allowed=false`.
- Spot Core remains the sole executor and policy authority.
- No backup/review/rollback gate is bypassed.

## Acceptance Criteria

Commands must pass:

```bash
python3 -m py_compile watch/review/review-journal-write.py watch/review/review-journal-validate.py
bash -n watch/operator/spot-operator.sh
watch/operator/spot-operator.sh review-journal
watch/operator/spot-operator.sh review-journal-validate
watch/operator/spot-operator.sh reviews 5
watch/operator/spot-operator.sh governance 10
watch/operator/spot-operator.sh smoke
watch/operator/spot-operator.sh validate
git status --short

md
