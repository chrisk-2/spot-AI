#!/usr/bin/env python3
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone

TARGETS = [
    Path("watch/state/history/monitor-alert-transitions.jsonl"),
    Path("watch/state/history/monitor-summary.jsonl"),
]

def stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def split_lines(path):
    good, bad = [], []
    if not path.exists():
        return good, bad
    for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            json.loads(line)
            good.append(line)
        except Exception as e:
            bad.append({"line": n, "error": str(e), "content": line[:300]})
    return good, bad

def repair(path):
    good, bad = split_lines(path)
    out = {"path": str(path), "exists": path.exists(), "valid_lines": len(good), "invalid_lines": len(bad), "changed": False}
    if not path.exists() or not bad:
        return out
    qdir = path.parent / "corrupt"
    qdir.mkdir(parents=True, exist_ok=True)
    backup = qdir / f"{path.name}.pre-repair-{stamp()}"
    shutil.copy2(path, backup)
    path.write_text(("\n".join(good) + "\n") if good else "", encoding="utf-8")
    out["changed"] = True
    out["backup"] = str(backup)
    out["bad_sample"] = bad[:10]
    return out

print(json.dumps({
    "ts": datetime.now(timezone.utc).isoformat(),
    "mode": "repair_malformed_jsonl_preserve_source_copy",
    "results": [repair(p) for p in TARGETS],
}, indent=2, sort_keys=True))
