#!/usr/bin/env python3

import json
import time
from datetime import datetime, UTC
from pathlib import Path

QUEUE_DIR = Path("watch/runtime/queue")
QUEUE_FILE = QUEUE_DIR / "review-queue-state.json"

DEFAULT_STATE = {
    "queue_name": "review-local",
    "max_concurrency": 1,
    "active": [],
    "pending": [],
    "completed": [],
    "execution_allowed": False,
    "mutation_allowed": False,
    "service_restart_allowed": False
}

def now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

def load_state():
    if not QUEUE_FILE.exists():
        return dict(DEFAULT_STATE)
    return json.loads(QUEUE_FILE.read_text())

def save_state(state):
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    state["updated_ts"] = now()
    QUEUE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))

def main():
    state = load_state()
    state["last_manager_run"] = now()
    state["execution_allowed"] = False
    state["mutation_allowed"] = False
    state["service_restart_allowed"] = False
    save_state(state)
    print("RESULT: PASS")
    print("review_queue_manager=dryrun")

if __name__ == "__main__":
    main()
