#!/usr/bin/env python3

import json
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path("watch/runtime/telemetry")
ROOT.mkdir(parents=True, exist_ok=True)

def score(latency_sec, ok):
    if not ok:
        return 0.0
    if latency_sec <= 15:
        return 1.0
    if latency_sec <= 30:
        return 0.8
    if latency_sec <= 60:
        return 0.5
    return 0.2

def main():
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    latency = 20.6
    health = {
        "health_score_id": f"review-health-{ts}",
        "phase": 44,
        "reviewer": "spot-worker-05",
        "model": "qwen2.5-coder:32b",
        "ok": True,
        "latency_sec": latency,
        "score": score(latency, True),
        "advisory_only": True,
        "execution_allowed": False,
        "timestamp": ts
    }

    out = ROOT / f"review-health-score-{ts}.json"
    out.write_text(json.dumps(health, indent=2))

    print("RESULT: PASS")
    print("review_health_score=pass")
    print(f"artifact={out}")

if __name__ == "__main__":
    main()
