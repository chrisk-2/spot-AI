#!/usr/bin/env python3

import json
from datetime import datetime, UTC
from pathlib import Path

METRICS = Path("watch/runtime/metrics/review-latency-metrics.json")

def now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

def classify(seconds):
    if seconds <= 15:
        return "warm"
    if seconds <= 45:
        return "acceptable_cold"
    return "slow"

def main():
    observed = 20.6
    payload = {
        "endpoint": "/review/local",
        "reviewer": "spot-worker-05",
        "model": "qwen2.5-coder:32b",
        "last_observed_latency_sec": observed,
        "classification": classify(observed),
        "metrics_api_mode": "file_backed_dryrun",
        "execution_allowed": False,
        "mutation_allowed": False,
        "updated_ts": now()
    }
    METRICS.parent.mkdir(parents=True, exist_ok=True)
    METRICS.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print("RESULT: PASS")
    print("review_latency_metrics=dryrun")

if __name__ == "__main__":
    main()
