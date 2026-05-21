#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone

def now():
    return datetime.now(timezone.utc).isoformat()

def fsync_parent(path):
    try:
        fd = os.open(str(path.parent), os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except Exception:
        pass

def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n"
    fd, tmpname = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent), text=True)
    tmp = Path(tmpname)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        fsync_parent(path)
    finally:
        tmp.unlink(missing_ok=True)

def append_jsonl(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    fsync_parent(path)

def validate_jsonl(path):
    path = Path(path)
    bad = []
    if not path.exists():
        return bad
    for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            json.loads(line)
        except Exception as e:
            bad.append({"line": n, "error": str(e), "content": line[:300]})
    return bad

def quarantine_jsonl(path):
    path = Path(path)
    bad = validate_jsonl(path)
    if not bad:
        return {"path": str(path), "quarantined": False, "invalid_count": 0}
    qdir = path.parent / "corrupt"
    qdir.mkdir(parents=True, exist_ok=True)
    dest = qdir / f"{path.name}.corrupt-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    shutil.copy2(path, dest)
    atomic_json(str(dest) + ".marker.json", {
        "ts": now(),
        "source": str(path),
        "copy": str(dest),
        "invalid_count": len(bad),
        "mode": "copy_only_source_preserved"
    })
    return {"path": str(path), "quarantined": True, "copy": str(dest), "invalid_count": len(bad)}

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("append-jsonl")
    p.add_argument("--path", required=True)
    p.add_argument("--json", required=True)

    p = sub.add_parser("write-json")
    p.add_argument("--path", required=True)
    p.add_argument("--json", required=True)

    p = sub.add_parser("validate-jsonl")
    p.add_argument("--path", required=True)

    p = sub.add_parser("quarantine-jsonl")
    p.add_argument("--path", required=True)

    a = ap.parse_args()

    if a.cmd == "append-jsonl":
        append_jsonl(a.path, json.loads(a.json))
        return 0
    if a.cmd == "write-json":
        atomic_json(a.path, json.loads(a.json))
        return 0
    if a.cmd == "validate-jsonl":
        bad = validate_jsonl(a.path)
        print(json.dumps({"valid": not bad, "invalid_count": len(bad), "invalid": bad[:25]}, indent=2, sort_keys=True))
        return 0 if not bad else 1
    if a.cmd == "quarantine-jsonl":
        print(json.dumps(quarantine_jsonl(a.path), indent=2, sort_keys=True))
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
