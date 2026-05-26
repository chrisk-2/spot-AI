#!/usr/bin/env python3
import json
import time
from pathlib import Path

ROOT = Path("/home/ogre/spot-stack")
CONFIG = ROOT / "spot-core/config/cluster_config.json"
STATUS = ROOT / "starfleet-ui/public/status.json"

def load_json(path):
    if not path.exists():
        return {"ok": False, "path": str(path), "error": "missing", "data": None}
    try:
        return {"ok": True, "path": str(path), "data": json.loads(path.read_text())}
    except Exception as e:
        return {"ok": False, "path": str(path), "error": repr(e), "data": None}

def main():
    cfg = load_json(CONFIG)
    status = load_json(STATUS)

    cfg_data = cfg.get("data") or {}
    status_data = status.get("data") or {}

    workers = cfg_data.get("workers") or {}
    role_priority = cfg_data.get("role_priority") or {}

    fleet_hosts = {}
    hosts = status_data.get("hosts")
    if isinstance(hosts, list):
        for h in hosts:
            if isinstance(h, dict) and h.get("host"):
                fleet_hosts[h["host"]] = h
    elif isinstance(hosts, dict):
        fleet_hosts = hosts

    normalized = {}

    for name, worker in workers.items():
        if not isinstance(worker, dict):
            worker = {}

        live = fleet_hosts.get(name) or {}

        normalized[name] = {
            "worker": name,
            "ip": worker.get("ip") or live.get("ip"),
            "base_url": worker.get("base_url") or live.get("base_url"),
            "primary_role": worker.get("primary_role") or live.get("primary_role"),
            "secondary_roles": worker.get("secondary_roles") or live.get("secondary_roles") or [],
            "routing_enabled": worker.get("routing_enabled"),
            "eligible": live.get("eligible"),
            "quarantined": live.get("quarantined"),
            "configured_models": worker.get("models") or [],
            "installed_models": live.get("installed_models") or [],
            "warm_models": live.get("warm_models") or {},
            "alerts": live.get("alerts") or [],
        }

    out = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "read_only",
        "mutation_authority": False,
        "executor": "spot-core",
        "config": {
            "ok": cfg["ok"],
            "path": cfg["path"],
        },
        "fleet_status": {
            "ok": status["ok"],
            "path": status["path"],
        },
        "role_priority": role_priority,
        "workers": normalized,
    }

    print(json.dumps(out, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
