# Review Normalization Spec

Phase: 3.0

## Purpose

Normalize W-5, W-6, Codex, and OpenAI review outputs before Spot Core consumes them.

Spot Core must not treat raw model prose as authorization.

## Normalized Contract

{
  "provider": "",
  "reviewer": "",
  "review_id": "",
  "patch_bundle_id": "",
  "verdict": "PASS|FIX|NO",
  "execution_allowed": false,
  "confidence": "low|medium|high",
  "intent_match": "pass|fix|fail",
  "code_match": "pass|fix|fail|not_applicable",
  "policy_match": "pass|fix|fail",
  "phase_match": "pass|fix|fail",
  "backup_required": true,
  "backup_verified": false,
  "rollback_defined": true,
  "validation_defined": true,
  "required_fixes": [],
  "blocking_findings": [],
  "notes": ""
}

## Normalization Rules

- Missing verdict becomes NO.
- Invalid JSON becomes NO.
- execution_allowed defaults false.
- Any policy failure forces NO.
- Any missing rollback for mutation forces NO.
- Any missing validation for mutation forces NO.
- PASS is valid only if all required gates are explicit.
