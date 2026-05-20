#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path

FILES = [
    "watch/runtime/queue/review-queue-manager.py",
    "watch/runtime/warm/review-warm-residency-daemon.py",
    "watch/runtime/metrics/review-latency-metrics.py",
]

STATE_FILES = [
    "watch/runtime/queue/review-queue-state.json",
    "watch/runtime/warm/review-warm-residency-state.json",
    "watch/runtime/metrics/review-latency-metrics.json",
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
    for path in FILES:
        p = Path(path)
        if not p.exists():
            fail(f"missing file: {path}")
        text = p.read_text()
        for marker in FORBIDDEN:
            if marker in text:
                fail(f"forbidden marker in {path}: {marker}")

    subprocess.run(["python3", "-m", "py_compile", *FILES], check=True)

    subprocess.run(["watch/runtime/queue/review-queue-manager.py"], check=True)
    subprocess.run(["watch/runtime/warm/review-warm-residency-daemon.py"], check=True)
    subprocess.run(["watch/runtime/metrics/review-latency-metrics.py"], check=True)

    for path in STATE_FILES:
        p = Path(path)
        if not p.exists():
            fail(f"missing state: {path}")
        data = json.loads(p.read_text())
        for key in ["execution_allowed", "mutation_allowed"]:
            if data.get(key) is not False:
                fail(f"{path} grants {key}")

    queue = json.loads(Path("watch/runtime/queue/review-queue-state.json").read_text())
    if queue.get("max_concurrency") != 1:
        fail("queue max_concurrency violation")

    warm = json.loads(Path("watch/runtime/warm/review-warm-residency-state.json").read_text())
    if warm.get("service_restart_allowed") is not False:
        fail("warm daemon grants service restart")

    metrics = json.loads(Path("watch/runtime/metrics/review-latency-metrics.json").read_text())
    if metrics.get("classification") not in ["warm", "acceptable_cold", "slow"]:
        fail("invalid latency classification")

    print("RESULT: PASS")
    print("cases=10 review_queue_manager=pass warm_residency_daemon=pass latency_metrics=pass queue_single_concurrency=pass service_restart_blocked=pass execution_blocked=pass mutation_blocked=pass state_files_valid=pass py_compile=pass mutation_scope=none")

if __name__ == "__main__":
    main()
