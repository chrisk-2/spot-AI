#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

ROOTS = [
    Path("/mnt/collective/logs/spot"),
    Path("watch/state"),
    Path("watch/apply/journals"),
]
CATEGORIES = ["reviews", "actions", "backups", "rollbacks", "learning", "runtime"]

def valid_json_file(path):
    try:
        if path.suffix == ".json":
            json.loads(path.read_text(errors="replace"))
            return True, None
        if path.suffix == ".jsonl":
            for line in path.read_text(errors="replace").splitlines():
                if line.strip():
                    json.loads(line)
            return True, None
        return True, None
    except Exception as e:
        return False, str(e)

def summarize_path(path):
    files = [p for p in path.glob("*") if p.is_file()] if path.exists() else []
    recent = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[:10]
    bad = []
    for f in files:
        ok, err = valid_json_file(f)
        if not ok:
            bad.append({"file": str(f), "error": err})
    return {
        "path": str(path),
        "exists": path.exists(),
        "file_count": len(files),
        "invalid_count": len(bad),
        "invalid": bad[:20],
        "recent": [{"file": str(f), "size": f.stat().st_size} for f in recent],
    }

def main():
    out = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only",
        "mutation_authority": False,
        "executor": "spot-core",
        "roots": {},
        "categories": {},
    }

    for root in ROOTS:
        out["roots"][str(root)] = summarize_path(root)

    primary = ROOTS[0]
    for cat in CATEGORIES:
        out["categories"][cat] = summarize_path(primary / cat)

    print(json.dumps(out, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
