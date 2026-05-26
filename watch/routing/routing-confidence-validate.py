#!/usr/bin/env python3
import json
import subprocess

EXPECTED = {
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
        ["watch/routing/routing-confidence-snapshot.py"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )

    if p.returncode != 0:
        print(p.stderr)
        fail("routing confidence snapshot failed")

    data = json.loads(p.stdout)

    if data.get("mode") != "read_only":
        fail("mode must be read_only")
    ok("read-only mode")

    if data.get("mutation_authority") is not False:
        fail("mutation_authority must be false")
    ok("no mutation authority")

    scores = data.get("role_scores")
    if not isinstance(scores, dict):
        fail("role_scores missing")
    ok("role_scores present")

    for role, expected_worker in EXPECTED.items():
        item = scores.get(role)
        if not isinstance(item, dict):
            fail(f"{role} score missing")
        if item.get("expected_worker") != expected_worker:
            fail(f"{role} expected worker mismatch")
        if item.get("owner_match") is not True:
            fail(f"{role} owner mismatch")
        confidence = item.get("confidence")
        if not isinstance(confidence, int):
            fail(f"{role} confidence missing")
        if confidence < 50:
            fail(f"{role} confidence below threshold: {confidence}")
        ok(f"{role} confidence {confidence}")

    print("RESULT: PASS")

if __name__ == "__main__":
    main()
