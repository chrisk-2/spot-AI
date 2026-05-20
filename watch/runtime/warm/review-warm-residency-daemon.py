#!/usr/bin/env python3

import json
from datetime import datetime, UTC
from pathlib import Path

STATE = Path("watch/runtime/warm/review-warm-residency-state.json")

TARGETS = [
    {
        "worker": "spot-worker-05",
        "model": "qwen2.5-coder:32b",
        "purpose": "primary_review"
    },
    {
        "worker": "spot-worker-06",
        "model": "qwen2.5:32b",
        "purpose": "reasoning_escalation"
    }
]

def now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

def main():
    STATE.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "mode": "dryrun_only",
        "targets": TARGETS,
        "warm_prompt_allowed": False,
        "service_restart_allowed": False,
        "mutation_allowed": False,
        "execution_allowed": False,
        "updated_ts": now()
    }
    STATE.write_text(json.dumps(state, indent=2, sort_keys=True))
    print("RESULT: PASS")
    print("warm_residency_daemon=dryrun")

if __name__ == "__main__":
    main()
