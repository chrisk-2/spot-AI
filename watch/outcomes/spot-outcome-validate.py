#!/usr/bin/env python3
import json
import sys
from pathlib import Path

paths = [
    Path("/mnt/collective/logs/spot/actions/spot-action-outcomes.jsonl"),
    Path("runtime/spot-action-outcomes.buffer.jsonl"),
]

bad = 0
seen = 0
decision_count = 0
update_count = 0

for path in paths:
    if not path.exists():
        continue

    with path.open("r", encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue

            seen += 1
            try:
                rec = json.loads(line)
                rtype = rec.get("record_type", "decision")

                if rtype == "outcome_update":
                    update_count += 1
                    assert rec.get("parent_record_id")
                    assert rec.get("outcome", {}).get("verdict") in ("resolved", "no_change", "regressed", "unknown")
                    assert rec.get("outcome", {}).get("metric")
                else:
                    decision_count += 1
                    assert "decision" in rec
                    assert "immediate_result" in rec
                    assert "outcome" in rec
                    assert rec["decision"]["risk"] in ("low", "medium", "high")
                    assert rec["decision"]["decision"] in ("executed", "dismissed", "edited")
            except Exception as e:
                bad += 1
                print(f"[FAIL] {path}:{n}: {e}")

if bad:
    print(f"RESULT: FAIL bad={bad} checked={seen}")
    sys.exit(1)

print(f"RESULT: PASS checked={seen} decisions={decision_count} outcome_updates={update_count}")
