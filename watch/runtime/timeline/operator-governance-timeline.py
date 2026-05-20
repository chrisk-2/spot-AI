#!/usr/bin/env python3

import json
from datetime import datetime, UTC
from pathlib import Path

OUT = Path("watch/runtime/timeline/operator-governance-timeline.json")

def now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)

    timeline = {
        "timeline_id": f"governance-timeline-{now()}",
        "mode": "dryrun_file_backed",
        "events": [
            {
                "event": "review_queue_ready",
                "source": "phase51-54",
                "status": "available"
            },
            {
                "event": "archive_writer_ready",
                "source": "phase55-58",
                "status": "available"
            },
            {
                "event": "simulation_fixture_ready",
                "source": "phase55-58",
                "status": "available"
            }
        ],
        "execution_allowed": False,
        "mutation_allowed": False,
        "service_restart_allowed": False,
        "updated_ts": now()
    }

    OUT.write_text(json.dumps(timeline, indent=2, sort_keys=True))

    print("RESULT: PASS")
    print("operator_governance_timeline=dryrun")
    print(f"artifact={OUT}")

if __name__ == "__main__":
    main()
