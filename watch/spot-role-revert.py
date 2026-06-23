#!/usr/bin/env python3
"""
spot-role-revert.py — Auto-revert role ownership when canonical owner comes back online.
Run by fleet-watch on every cycle. Edits cluster_config.json and signals spot-core to reload.
"""
import json, sys, time, subprocess, logging
from pathlib import Path

CFG_PATH   = Path("/home/ogre/spot-stack/spot-core/config/cluster_config.json")
STATE_PATH = Path("/home/ogre/spot-stack/watch/state/fleet-status.json")
REVERT_LOG = Path("/home/ogre/spot-stack/watch/logs/role-revert.jsonl")
APP_PATH   = Path("/home/ogre/spot-stack/spot-core/spotcore/app.py")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("role-revert")

def now(): return int(time.time())

def load(p, default):
    try: return json.loads(p.read_text())
    except: return default

def append_log(entry):
    REVERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with REVERT_LOG.open("a") as f:
        f.write(json.dumps({**entry, "ts": now()}) + "\n")

def worker_online(name, state):
    h = state.get("hosts", {}).get(name, {})
    return h.get("ssh_ok") is True and h.get("service_ok") is True and not h.get("quarantined")

def current_role_owner_in_app() -> dict:
    """Parse ROLE_OWNERS dict from app.py."""
    src = APP_PATH.read_text()
    start = src.find("\nROLE_OWNERS: dict[str, str] = {")
    end = src.find("\n}", start) + 2
    block = src[start:end]
    owners = {}
    for line in block.splitlines():
        line = line.strip().rstrip(",")
        if ":" in line and "spot-worker" in line:
            k, v = line.split(":", 1)
            k = k.strip().strip('"')
            v = v.strip().strip('"').split("#")[0].strip()
            owners[k] = v
    return owners

def set_role_owner_in_app(role, worker):
    src = APP_PATH.read_text()
    # Find and replace the specific role line
    import re
    pattern = rf'("{role}":\s*)"spot-worker-\d+"'
    replacement = rf'\1"{worker}"'
    new_src, n = re.subn(pattern, replacement, src)
    if n == 0:
        # Role not present — insert it
        old_block = "\nROLE_OWNERS: dict[str, str] = {"
        new_src = src.replace(old_block, old_block + f'\n    "{role}": "{worker}",', 1)
    import ast
    ast.parse(new_src)
    APP_PATH.write_text(new_src)

def update_role_priority_front(cfg, role, worker):
    rp = cfg["role_priority"].get(role, [])
    cfg["role_priority"][role] = [worker] + [w for w in rp if w != worker]

def run():
    cfg   = load(CFG_PATH, {})
    state = load(STATE_PATH, {})
    canonical = cfg.get("role_owners_canonical", {})
    standins  = cfg.get("role_standin_priority", {})

    if not canonical:
        log.info("No role_owners_canonical in config — nothing to do")
        return

    current_owners = current_role_owner_in_app()
    changed = False

    for role, canon_worker in canonical.items():
        current = current_owners.get(role)

        if current == canon_worker:
            # Already correct — check if canonical is actually online
            if not worker_online(canon_worker, state):
                # Canonical owner offline — find best standin
                standin_list = standins.get(role, [])
                for standin in standin_list:
                    if standin != canon_worker and worker_online(standin, state):
                        log.warning(f"STANDIN: {role} canonical {canon_worker} offline → assigning {standin}")
                        set_role_owner_in_app(role, standin)
                        update_role_priority_front(cfg, role, standin)
                        cfg["workers"][standin]["primary_role"] = role
                        append_log({"event": "standin_assigned", "role": role, "canonical": canon_worker, "standin": standin})
                        changed = True
                        break
            continue

        # Current owner is a stand-in — check if canonical is back
        if worker_online(canon_worker, state):
            log.info(f"REVERT: {role} reverting from {current} (stand-in) → {canon_worker} (canonical)")
            set_role_owner_in_app(role, canon_worker)
            update_role_priority_front(cfg, role, canon_worker)
            # Restore stand-in's primary role to its canonical role
            standin_canonical = {v: k for k, v in canonical.items()}.get(current)
            if standin_canonical and standin_canonical != role:
                cfg["workers"][current]["primary_role"] = standin_canonical
            append_log({"event": "revert", "role": role, "from": current, "to": canon_worker})
            changed = True

    if changed:
        CFG_PATH.write_text(json.dumps(cfg, indent=2))
        # Signal spot-core to reload config (it hot-reloads on mtime change)
        CFG_PATH.touch()
        log.info("Config updated and touched for hot-reload")
        # Also restart spot-core to pick up app.py changes
        subprocess.run(
            ["docker", "compose", "-f", "/home/ogre/spot-stack/docker-compose.yml",
             "restart", "spot-core"],
            capture_output=True
        )
        log.info("spot-core restarted")
    else:
        log.info("No ownership changes needed")

if __name__ == "__main__":
    run()
