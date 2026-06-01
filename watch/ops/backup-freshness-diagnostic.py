#!/usr/bin/env python3
import json, time
from pathlib import Path

ROOT = Path("/mnt/collective/backups")
WARN_HOURS = 24
now = time.time()

result = {
    "check": "backup_freshness_diagnostic",
    "root": str(ROOT),
    "exists": ROOT.exists(),
    "warn_hours": WARN_HOURS,
    "status": "PASS",
    "warnings": [],
    "latest": []
}

if not ROOT.exists():
    result["status"] = "WARN"
    result["warnings"].append("backup root missing")
else:
    candidates = [p for p in ROOT.rglob("*") if p.is_dir()]
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for p in candidates[:15]:
        age_hours = round((now - p.stat().st_mtime) / 3600, 2)
        result["latest"].append({"path": str(p), "age_hours": age_hours})
    if not result["latest"]:
        result["status"] = "WARN"
        result["warnings"].append("no backup directories found")
    elif result["latest"][0]["age_hours"] > WARN_HOURS:
        result["status"] = "WARN"
        result["warnings"].append("latest backup exceeds freshness threshold")

print(json.dumps(result, indent=2))
