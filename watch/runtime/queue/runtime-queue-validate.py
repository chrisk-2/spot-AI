#!/usr/bin/env python3
import json
import subprocess
import tempfile
import time
from pathlib import Path

ROOT_BASE = Path("watch/runtime/queue/runs")

def run(cmd, expect=0):
    p = subprocess.run(cmd, text=True, capture_output=True)
    ok = p.returncode == expect
    return ok, p

def emit(ok, name, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{(' ' + detail) if detail else ''}")
    return ok

def main():
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    root = ROOT_BASE / f"validate-{ts}"

    checks = []

    ok, p = run(["watch/runtime/queue/runtime-queue-store.py", "--root", str(root), "init"])
    checks.append(emit(ok, "queue_init"))

    ok, p = run([
        "watch/runtime/queue/runtime-queue-store.py", "--root", str(root),
        "enqueue", "--target", "fixture-service", "--action", "restart-sim", "--risk-class", "low"
    ])
    checks.append(emit(ok, "enqueue_candidate"))
    cid = json.loads(p.stdout)["candidate_id"]

    ok, p = run([
        "watch/runtime/queue/runtime-queue-locks.py", "--root", str(root),
        "lease", "--candidate-id", cid, "--owner", "spot-worker-03"
    ], expect=2)
    checks.append(emit(ok, "worker_self_lease_blocked"))

    ok, p = run([
        "watch/runtime/queue/runtime-queue-locks.py", "--root", str(root),
        "lease", "--candidate-id", cid, "--owner", "spot-core", "--ttl", "30"
    ])
    checks.append(emit(ok, "spot_core_lease_acceptance"))

    ok, p = run([
        "watch/runtime/queue/runtime-queue-locks.py", "--root", str(root),
        "lease", "--candidate-id", cid, "--owner", "spot-core", "--ttl", "30"
    ], expect=2)
    checks.append(emit(ok, "duplicate_active_lease_blocked"))

    ok, p = run([
        "watch/runtime/queue/runtime-queue-locks.py", "--root", str(root),
        "complete", "--candidate-id", cid
    ])
    checks.append(emit(ok, "complete_with_valid_lease"))

    ok, p = run([
        "watch/runtime/queue/runtime-queue-store.py", "--root", str(root),
        "enqueue", "--target", "fixture-service", "--action", "restart-sim", "--risk-class", "low"
    ], expect=2)
    checks.append(emit(ok, "terminal_replay_blocked"))

    ok, p = run([
        "watch/runtime/queue/runtime-queue-store.py", "--root", str(root),
        "enqueue", "--target", "fixture-service", "--action", "reload-sim", "--risk-class", "low"
    ])
    cid2 = json.loads(p.stdout)["candidate_id"]
    checks.append(emit(ok, "second_enqueue_candidate"))

    ok, p = run([
        "watch/runtime/queue/runtime-queue-locks.py", "--root", str(root),
        "lease", "--candidate-id", cid2, "--owner", "spot-core", "--ttl", "1"
    ])
    checks.append(emit(ok, "short_lease_created"))

    time.sleep(2)

    ok, p = run(["watch/runtime/queue/runtime-queue-recover.py", "--root", str(root)])
    recovered = json.loads(p.stdout)["recovered"]
    checks.append(emit(ok and cid2 in recovered, "stale_lease_recovered"))

    state = json.loads((root / "queue-state.json").read_text())
    receipts = list((root / "receipts").glob("*.json"))
    checks.append(emit(state.get("scope") == "fixture_only", "mutation_scope_fixture_only"))
    checks.append(emit(len(receipts) >= 5, "immutable_receipts_present", f"count={len(receipts)}"))

    passed = sum(1 for x in checks if x)
    failed = len(checks) - passed

    print("\n=== SUMMARY ===")
    print(f"pass={passed} fail={failed}")
    if failed:
        print("RESULT: FAIL")
        return 1

    print("RESULT: PASS")
    print("cases=11 queue_init=pass enqueue_candidate=pass worker_self_lease_blocked=pass spot_core_lease_acceptance=pass duplicate_active_lease_blocked=pass complete_with_valid_lease=pass terminal_replay_blocked=pass second_enqueue_candidate=pass short_lease_created=pass stale_lease_recovered=pass mutation_scope=fixture_only")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
