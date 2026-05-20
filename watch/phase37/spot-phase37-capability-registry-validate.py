#!/usr/bin/env python3

import json
import sys
from pathlib import Path

REGISTRY = Path("watch/governance/capabilities/capability-registry-v1.json")

LOCKED = {
    "spot-worker-01": "general",
    "spot-worker-02": "utility",
    "spot-worker-03": "coding",
    "spot-worker-04": "heavy",
    "spot-worker-05": "review",
    "spot-worker-06": "reasoning",
    "spot-core": "executor",
}

def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)

def main():
    data = json.loads(REGISTRY.read_text())
    workers = data.get("workers", {})

    for worker, role in LOCKED.items():
        if worker not in workers:
            fail(f"missing worker: {worker}")
        if workers[worker].get("role") != role:
            fail(f"role mismatch: {worker}")
        if worker != "spot-core" and workers[worker].get("can_execute") is not False:
            fail(f"worker execution authority violation: {worker}")
        if workers[worker].get("can_self_apply") is not False:
            fail(f"self apply violation: {worker}")

    if workers["spot-core"].get("can_execute") is not True:
        fail("spot-core executor authority missing")

    print("RESULT: PASS")
    print("capability_registry=valid")

if __name__ == "__main__":
    main()
