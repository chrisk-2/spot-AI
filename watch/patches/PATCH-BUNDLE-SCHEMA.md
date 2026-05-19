# Patch Bundle Schema

Phase: 3.0
Purpose: deterministic code/config mutation artifact.

## Rules

- Patch bundles are proposal artifacts only.
- Patch bundles do not authorize execution.
- Codex/W-3 may generate bundles.
- W-5 reviews bundles.
- Spot Core alone may apply approved bundles.
- Bundle must bind to backup, review, validation, and rollback before apply.

## Required Fields

{
  "schema_version": "1.0",
  "request_id": "",
  "patch_bundle_id": "",
  "phase": "3.0",
  "created_utc": "",
  "generated_by": {
    "worker": "",
    "provider": "",
    "model": ""
  },
  "target": {
    "host": "",
    "repo": "",
    "service": ""
  },
  "risk_class": "low|medium|high",
  "intent": "",
  "files": [],
  "diff_artifacts": [],
  "validation": [],
  "rollback": {
    "required": true,
    "strategy": "",
    "commands": []
  },
  "review_required": true,
  "execution_allowed": false
}

## Execution Invariant

A patch bundle may not be applied unless Spot Core has verified:

- review verdict PASS
- backup binding exists
- rollback defined
- validation defined
- repo state matches expected pre-change state
- bundle has not already been successfully applied
