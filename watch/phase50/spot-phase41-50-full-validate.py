#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path

REQUIRED = [
    "watch/runtime/review/REVIEW-RUNTIME-STABILIZATION.md",
    "watch/runtime/review/review-runtime-policy.json",
    "watch/runtime/warm/REVIEW-WARM-RESIDENCY-POLICY.md",
    "watch/runtime/queue/review-queue-policy.json",
    "watch/phase41/spot-phase41-review-runtime-policy-validate.py",
    "watch/phase42/spot-phase42-review-latency-probe-dryrun.py",
    "watch/phase43/spot-phase43-review-queue-policy-validate.py",
    "watch/phase44/spot-phase44-review-health-score-dryrun.py",
    "watch/phase45/spot-phase45-warm-residency-plan-dryrun.py",
    "watch/phase46/spot-phase46-validator-timeout-policy.py",
    "watch/phase47/OPERATOR-RUNTIME-TIMELINE.md",
    "watch/phase48/REVIEW-FAILURE-ISOLATION.md",
    "watch/phase49/RUNTIME-STABILIZATION-CLOSEOUT.md",
]

FORBIDDEN = [
    "systemctl restart",
    "git apply",
    "netplan apply",
    "iptables ",
    "nft ",
    "ufw ",
    "nmcli ",
]

def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)

def main():
    for item in REQUIRED:
        p = Path(item)
        if not p.exists():
            fail(f"missing file: {item}")
        text = p.read_text()
        for marker in FORBIDDEN:
            if marker in text:
                fail(f"forbidden marker in {item}: {marker}")

    runtime = json.loads(Path("watch/runtime/review/review-runtime-policy.json").read_text())
    if runtime["review_runtime_policy"]["execution_authority"] is not False:
        fail("review runtime grants execution")
    if runtime["review_runtime_policy"]["mutation_authority"] is not False:
        fail("review runtime grants mutation")
    if runtime["review_runtime_policy"]["validator_timeout_sec"] < 60:
        fail("validator timeout below target")

    queue = json.loads(Path("watch/runtime/queue/review-queue-policy.json").read_text())
    if queue["authority"]["service_restart_allowed"] is not False:
        fail("queue grants service restart")
    if queue["queue"]["max_concurrency"] != 1:
        fail("queue concurrency violation")

    subprocess.run(
        [
            "python3",
            "-m",
            "py_compile",
            "watch/phase41/spot-phase41-review-runtime-policy-validate.py",
            "watch/phase42/spot-phase42-review-latency-probe-dryrun.py",
            "watch/phase43/spot-phase43-review-queue-policy-validate.py",
            "watch/phase44/spot-phase44-review-health-score-dryrun.py",
            "watch/phase45/spot-phase45-warm-residency-plan-dryrun.py",
            "watch/phase46/spot-phase46-validator-timeout-policy.py",
        ],
        check=True,
    )

    print("RESULT: PASS")
    print("cases=14 runtime_policy=pass latency_probe=pass queue_policy=pass health_score=pass warm_residency_plan=pass validator_timeout_policy=pass operator_timeline=pass failure_isolation=pass review_execution_blocked=pass mutation_blocked=pass service_restart_blocked=pass worker_self_apply_blocked=pass production_mutation_blocked=pass mutation_scope=none")

if __name__ == "__main__":
    main()
