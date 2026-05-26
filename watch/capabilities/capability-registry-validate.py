#!/usr/bin/env python3
import json
import subprocess

REQUIRED_ROLES = {
    "general": "spot-worker-01",
    "utility": "spot-worker-02",
    "coding": "spot-worker-03",
    "heavy": "spot-worker-04",
    "review": "spot-worker-05",
    "reasoning": "spot-worker-06",
}

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def ok(msg):
    print(f"[PASS] {msg}")

def main():
    p = subprocess.run(
        ["watch/capabilities/capability-registry-snapshot.py"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )

    if p.returncode != 0:
        print(p.stderr)
        fail("capability registry snapshot command failed")

    try:
        data = json.loads(p.stdout)
    except Exception as e:
        fail(f"snapshot invalid JSON: {e!r}")

    if data.get("mode") != "read_only":
        fail("mode must be read_only")
    ok("read-only mode")

    if data.get("mutation_authority") is not False:
        fail("mutation_authority must be false")
    ok("no mutation authority")

    workers = data.get("workers")
    if not isinstance(workers, dict):
        fail("workers map missing")
    ok("workers map present")

    for role, worker_name in REQUIRED_ROLES.items():
        worker = workers.get(worker_name)
        if not isinstance(worker, dict):
            fail(f"{worker_name} missing for role {role}")
        if worker.get("primary_role") != role:
            fail(f"{worker_name} primary_role mismatch for {role}")
        ok(f"{role} -> {worker_name}")

    print("RESULT: PASS")

if __name__ == "__main__":
    main()
