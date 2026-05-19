#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()

ALLOWED_STATES = [
    "PASS"
]

def fail(msg):
    print(f"[FAIL] {msg}", file=sys.stderr)
    raise SystemExit(1)

def run(cmd):
    return subprocess.run(
        cmd,
        shell=True,
        text=True,
        capture_output=True
    )

def load_json(path):
    return json.loads(Path(path).read_text())

def repo_dirty():
    r = run("git status --porcelain")
    if r.returncode != 0:
        fail("git status failed")

    dirty = []
    for line in r.stdout.splitlines():
        if "starfleet-ui/public/status.json" in line:
            continue
        if "watch/apply/journals/" in line:
            continue
        if "watch/patches/bundles/" in line:
            continue
        if "watch/review/bundles/" in line:
            continue
        if "watch/rollback/bindings/" in line:
            continue
        if "watch/backup/bindings/" in line:
            continue
        if "watch/backup/spot-backup-binding-new.py" in line:
            continue
        if "watch/backup/spot-backup-binding-validate.py" in line:
            continue
        if "watch/apply/spot-apply-wrapper.py" in line:
            continue
        dirty.append(line)

    return dirty

def main():
    ap = argparse.ArgumentParser(description="Dry-run controlled apply wrapper.")
    ap.add_argument("--patch-bundle", required=True)
    ap.add_argument("--review-json", required=True)
    ap.add_argument("--journal-json", required=True)
    ap.add_argument("--rollback-binding-json", required=False)
    ap.add_argument("--backup-binding-json", required=False)
    args = ap.parse_args()

    patch = load_json(args.patch_bundle)
    review = load_json(args.review_json)
    journal = load_json(args.journal_json)
    rollback_binding = load_json(args.rollback_binding_json) if args.rollback_binding_json else None
    backup_binding = load_json(args.backup_binding_json) if args.backup_binding_json else None

    if backup_binding is None:
        fail("backup binding required")

    if backup_binding.get("mutation_performed") is not False:
        fail("backup binding mutation_performed must remain false")

    if backup_binding.get("execution_performed") is not False:
        fail("backup binding execution_performed must remain false")

    if backup_binding.get("verified") is not True:
        fail("backup binding not verified")

    if backup_binding.get("patch_bundle_id") != patch.get("patch_bundle_id"):
        fail("backup patch_bundle_id mismatch")

    if backup_binding.get("backup_binding_id") != journal.get("backup_binding_id"):
        fail("backup backup_binding_id mismatch")

    if rollback_binding is None:
        fail("rollback binding required")

    if rollback_binding.get("mutation_performed") is not False:
        fail("rollback binding mutation_performed must remain false")

    if rollback_binding.get("execution_performed") is not False:
        fail("rollback binding execution_performed must remain false")

    if rollback_binding.get("backup_binding_id") != journal.get("backup_binding_id"):
        fail("rollback backup_binding_id mismatch")

    if rollback_binding.get("apply_id") != journal.get("apply_id"):
        fail("rollback apply_id mismatch")

    if rollback_binding.get("patch_bundle_id") != patch.get("patch_bundle_id"):
        fail("rollback patch_bundle_id mismatch")

    if not rollback_binding.get("restore_strategy"):
        fail("rollback restore_strategy missing")

    if review["verdict"] not in ALLOWED_STATES:
        fail("review verdict not PASS")

    if review["execution_allowed"] is not True:
        fail("execution_allowed not true")

    if review["policy_match"] != "pass":
        fail("policy_match not pass")

    if review["phase_match"] != "pass":
        fail("phase_match not pass")

    if review["rollback_defined"] is not True:
        fail("rollback not defined")

    if review["validation_defined"] is not True:
        fail("validation not defined")

    if journal["mutation_performed"] is not False:
        fail("mutation_performed must remain false")

    if journal["execution_performed"] is not False:
        fail("execution_performed must remain false")

    dirty = repo_dirty()
    if dirty:
        print("[INFO] repo dirty entries:")
        for d in dirty:
            print(d)
        fail("repo has unapproved dirty state")

    print("[PASS] patch bundle verified")
    print("[PASS] review verified")
    print("[PASS] apply journal verified")
    print("[PASS] backup binding verified")
    print("[PASS] rollback binding verified")
    print("[PASS] repo cleanliness verified")
    print("[PASS] DRY-RUN apply wrapper gating succeeded")
    print("[INFO] mutation blocked intentionally for Phase 3.3")

if __name__ == "__main__":
    main()
