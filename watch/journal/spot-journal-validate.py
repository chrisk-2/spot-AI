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

def check_file(path):
    global fail
    try:
        if path.suffix == ".json":
            json.loads(path.read_text(errors="replace"))
        elif path.suffix == ".jsonl":
            for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
                if line.strip():
                    json.loads(line)
    except Exception as e:
        print(f"FAIL invalid journal: {path}: {e}")
        fail += 1

for root in ROOTS:
    if not root.exists():
        print(f"WARN missing journal root: {root}")
        warn += 1
        continue
    for f in root.rglob("*"):
        if f.is_file() and f.suffix in {".json", ".jsonl"}:
            check_file(f)

print(f"RESULT: {'FAIL' if fail else 'PASS'} fail={fail} warn={warn}")
sys.exit(1 if fail else 0)
