#!/usr/bin/env python3
import json
import shutil
import time
from pathlib import Path
from spot_risk import resolve_risk

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "watch" / "policy" / "action-policy.json"

def action_name(obj):
    for key in ("action_type", "action", "name", "id", "type"):
        if obj.get(key):
            return str(obj[key])
    return ""

def normalize(obj):
    changed = 0
    if isinstance(obj, dict):
        name = action_name(obj)
        looks_actionish = bool(name) and (
            "allow" in obj or "enabled" in obj or "description" in obj or "command" in obj or "params" in obj
        )
        if looks_actionish:
            old = obj.get("risk")
            new = resolve_risk(name, obj.get("target", ""), obj, old)
            if old != new:
                obj["risk"] = new
                changed += 1
        for v in obj.values():
            changed += normalize(v)
    elif isinstance(obj, list):
        for item in obj:
            changed += normalize(item)
    return changed

if not POLICY_PATH.exists():
    print(f"RESULT: SKIP missing={POLICY_PATH}")
    raise SystemExit(0)

data = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
changed = normalize(data)

if changed:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    shutil.copy2(POLICY_PATH, POLICY_PATH.with_suffix(POLICY_PATH.suffix + f".bak-risk-{stamp}"))
    POLICY_PATH.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

print(f"RESULT: PASS policy={POLICY_PATH} risk_fields_changed={changed}")
