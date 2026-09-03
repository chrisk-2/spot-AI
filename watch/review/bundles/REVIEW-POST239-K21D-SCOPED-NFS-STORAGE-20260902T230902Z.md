# POST-2.39 K21D Scoped NFS Storage Review Bundle

Review ID: REVIEW-POST239-K21D-SCOPED-NFS-STORAGE-20260902T230902Z
Created UTC: 2026-09-02T23:09:02Z
Review class: policy and safety
Primary reviewer: spot-worker-05
Preferred model: deepseek-r1:32b

## Reviewed artifacts

- watch/storage/POST239-K21D-SCOPED-NFS-STORAGE-DESIGN.md
- SHA-256: e127b728a8604d71683a53f7df59db56550f1515468beec337840abf69e84e99
- watch/storage/post239-k21d-scoped-nfs-storage-design-v1.json
- SHA-256: 78b8fe437bb60a554fb334bd479912b8453be6577a78de9e7a3cffa09fa0698f
- Repository HEAD: 2960639befb1a6c3b9b2aeb1f7003699b1714f1b

## Verified evidence

- The existing /mnt/collective CIFS mount cannot preserve required ownership and mode metadata.
- The latest controlled NFS probe preserved root:root, directory mode 0700, file mode 0400, content integrity, and fsync.
- Direct NFSv4 subdirectory mounting from /volume1/spotvault passed.
- Both proposed NFS destination subdirectories were absent during discovery.
- The existing /mnt/collective mount is used by Docker and must remain unchanged.
- No persistent probe mount or probe artifact remains.
- The prior K21D authorization remains revoked and unconsumed.
- No K21D live destination currently exists.

## Required design constraints

1. Use exactly two scoped NFSv4 mounts at the fixed K21D paths.
2. Do not replace or modify the parent /mnt/collective CIFS mount.
3. Do not restart Docker.
4. Copy records using exclusive creation without overwriting.
5. Require 0400 root:root for record files.
6. Require 0700 root:root for protected directories.
7. Verify all approved SHA-256 values before and after migration.
8. Retain the original CIFS records as the rollback baseline.
9. Rollback must remove only the two scoped mount units.
10. Do not install or activate K21D during storage correction.
11. Require a new single-use authorization before mutation.
12. Keep Spot Core as the sole executor.

## Reviewer questions

1. Does the selected boundary preserve the fixed K21D paths without disturbing Docker?
2. Are the NFS options and systemd dependency requirements fail-closed?
3. Does the migration prevent overwrite, identity drift, and content drift?
4. Is the rollback complete and independently verifiable?
5. Are any additional deterministic gates required before authorization?
6. Does the plan preserve the existing governance and executor boundaries?

## Required response

Return one machine-readable JSON object using this contract:

{
  "review_id": "REVIEW-POST239-K21D-SCOPED-NFS-STORAGE-20260902T230902Z",
  "verdict": "PASS|FIX|NO",
  "execution_allowed": false,
  "confidence": "low|medium|high",
  "intent_match": "pass|fix|fail",
  "code_match": "pass|fix|fail",
  "policy_match": "pass|fix|fail",
  "backup_required": true,
  "backup_verified": false,
  "rollback_defined": true,
  "validation_defined": true,
  "required_fixes": [],
  "notes": "short reviewer summary"
}

For this design-only review, execution_allowed must remain false. A PASS verdict permits construction of a separate single-use authorization; it does not authorize storage mutation.

Current execution_allowed: false
Current mutation_authority: false
