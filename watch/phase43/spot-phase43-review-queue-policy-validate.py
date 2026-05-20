#!/usr/bin/env python3

import json
import sys
from pathlib import Path

POLICY = Path("watch/runtime/queue/review-queue-policy.json")

def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)

def main():
    data = json.loads(POLICY.read_text())
    queue = data["queue"]
    auth = data["authority"]

    if queue["max_concurrency"] != 1:
        fail("review queue must be single concurrency")
    if "timeout" not in queue["retry_policy"]["retry_on"]:
        fail("timeout retry missing")
    if "policy_denied" not in queue["forbidden_retry_on"]:
        fail("policy denial retry guard missing")
    if auth["execution_allowed"] is not False:
        fail("queue grants execution")
    if auth["mutation_allowed"] is not False:
        fail("queue grants mutation")
    if auth["service_restart_allowed"] is not False:
        fail("queue grants service restart")

    print("RESULT: PASS")
    print("review_queue_policy=valid")

if __name__ == "__main__":
    main()
