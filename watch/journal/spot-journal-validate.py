#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOTS = [
    Path("/mnt/collective/logs/spot"),
    Path("watch/state"),
    Path("watch/apply/journals"),
]

fail = 0
warn = 0

def validate(path):
    global fail, warn

    try:
        text = path.read_text(errors="replace")
    except PermissionError as e:
        print(f"WARN unreadable artifact: {path}: {e}")
        warn += 1
        return

    try:
        if path.suffix == ".json":
            if not text.strip():
                print(f"WARN empty json artifact: {path}")
                warn += 1
                return
            json.loads(text)

        elif path.suffix == ".jsonl":
            lines = [x for x in text.splitlines() if x.strip()]
            if not lines:
                print(f"WARN empty jsonl artifact: {path}")
                warn += 1
                return

            for line in lines:
                json.loads(line)

    except Exception as e:
        print(f"FAIL invalid journal: {path}: {e}")
        fail += 1

for root in ROOTS:
    if not root.exists():
        print(f"WARN missing root: {root}")
        warn += 1
        continue

    for f in root.rglob("*"):
        if f.is_file() and f.suffix in {".json", ".jsonl"}:
            validate(f)

print(f"RESULT: {'FAIL' if fail else 'PASS'} fail={fail} warn={warn}")
sys.exit(1 if fail else 0)
