#!/usr/bin/env python3

import hashlib
import json
import sys
from pathlib import Path

INDEX = Path("watch/runtime/archive/archive-index.jsonl")

def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)

def digest_without_hash(record):
    clean = dict(record)
    clean.pop("record_hash", None)
    return hashlib.sha256(
        json.dumps(clean, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

def main():
    if not INDEX.exists():
        fail("archive index missing")

    lines = [x for x in INDEX.read_text().splitlines() if x.strip()]
    if not lines:
        fail("archive index empty")

    seen = set()

    for line in lines:
        entry = json.loads(line)
        record_hash = entry.get("record_hash")
        path = Path(entry.get("path", ""))

        if record_hash in seen:
            fail(f"duplicate archive hash: {record_hash}")
        seen.add(record_hash)

        if not path.exists():
            fail(f"missing archive record: {path}")

        record = json.loads(path.read_text())

        if record.get("record_hash") != record_hash:
            fail("record hash mismatch")

        if digest_without_hash(record) != record_hash:
            fail("record content digest mismatch")

        if record.get("mutation_allowed") is not False:
            fail("archive record grants mutation")

        if record.get("execution_allowed") is not False:
            fail("archive record grants execution")

    print("RESULT: PASS")
    print("archive_integrity=valid")
    print(f"records={len(lines)}")

if __name__ == "__main__":
    main()
