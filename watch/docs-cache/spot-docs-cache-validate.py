#!/usr/bin/env python3
import json
import sys
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
cfg_path = repo / "config" / "docs-cache-allowlist.json"
cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

bad = 0
if cfg.get("mode") != "manual_refresh_only":
    print("[FAIL] docs cache mode must be manual_refresh_only")
    bad += 1

rule = cfg.get("quarantine_rule", "").lower()
if "reference" not in rule or "never action instructions" not in rule:
    print("[FAIL] quarantine rule must separate reference from action instructions")
    bad += 1

root = Path(cfg.get("cache_root", "/mnt/collective/docs-cache"))
root.mkdir(parents=True, exist_ok=True)

if bad:
    print(f"RESULT: FAIL bad={bad}")
    sys.exit(1)

print(f"RESULT: PASS cache_root={root}")
