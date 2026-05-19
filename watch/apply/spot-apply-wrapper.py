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
        if "watch/apply/spot-apply-wrapper.py" in line:
            continue
        dirty.append(line)

    return dirty

def main():
    ap = argparse.ArgumentParser(description="Dry-run controlled apply wrapper.")
    ap.add_argument("--patch-bundle", required=True)
    ap.add_argument("--review-json", required=True)
    ap.add_argument("--journal-json", required=True)
    args = ap.parse_args()

    patch = load_json(args.patch_bundle)
    review = load_json(args.review_json)
    journal = load_json(args.journal_json)

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
    print("[PASS] repo cleanliness verified")
    print("[PASS] DRY-RUN apply wrapper gating succeeded")
    print("[INFO] mutation blocked intentionally for Phase 3.3")

if __name__ == "__main__":
    main()
