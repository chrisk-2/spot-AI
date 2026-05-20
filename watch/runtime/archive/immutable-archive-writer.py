#!/usr/bin/env python3

import hashlib
import json
import sys
from datetime import datetime, UTC
from pathlib import Path

ARCHIVE_DIR = Path("watch/runtime/archive/records")
INDEX = Path("watch/runtime/archive/archive-index.jsonl")

def now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

def digest(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)

def main():
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    INDEX.parent.mkdir(parents=True, exist_ok=True)

    ts = now()
    record = {
        "record_type": "governance-runtime-proof",
        "source": "group2-dryrun",
        "timestamp": ts,
        "execution_allowed": False,
        "mutation_allowed": False,
        "service_restart_allowed": False,
        "archive_mode": "append_only_dryrun"
    }
    record_hash = digest(record)
    record["record_hash"] = record_hash

    out = ARCHIVE_DIR / f"{record_hash}.json"
    if out.exists():
        fail("archive record already exists; refusing overwrite")

    out.write_text(json.dumps(record, indent=2, sort_keys=True))

    index_line = {
        "ts": ts,
        "record_hash": record_hash,
        "path": str(out),
        "append_only": True
    }

    with INDEX.open("a") as f:
        f.write(json.dumps(index_line, sort_keys=True) + "\n")

    print("RESULT: PASS")
    print("immutable_archive_writer=dryrun")
    print(f"record={out}")

if __name__ == "__main__":
    main()
