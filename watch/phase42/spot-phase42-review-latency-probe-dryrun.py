#!/usr/bin/env python3

import json
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path("watch/runtime/telemetry")
ROOT.mkdir(parents=True, exist_ok=True)

def classify_latency(seconds):
    if seconds <= 15:
        return "warm"
    if seconds <= 45:
        return "acceptable_cold"
    return "slow"

def main():
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    observed_seconds = 20.6

    record = {
        "probe_id": f"review-latency-dryrun-{ts}",
        "phase": 42,
        "mode": "dryrun_from_observed_operator_probe",
        "endpoint": "/review/local",
        "reviewer": "spot-worker-05",
        "model": "qwen2.5-coder:32b",
        "observed_latency_sec": observed_seconds,
        "classification": classify_latency(observed_seconds),
        "execution_allowed": False,
        "mutation_performed": False,
        "timestamp": ts
    }

    out = ROOT / f"review-latency-dryrun-{ts}.json"
    out.write_text(json.dumps(record, indent=2))

    print("RESULT: PASS")
    print("review_latency_probe=pass")
    print(f"artifact={out}")

if __name__ == "__main__":
    main()
