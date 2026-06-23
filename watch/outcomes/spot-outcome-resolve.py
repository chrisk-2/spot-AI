#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path
from spot_outcomes import pending_records, append_outcome_update

REPO_ROOT = Path(__file__).resolve().parents[2]

def run(cmd, timeout=8):
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return {
            "ok": p.returncode == 0,
            "returncode": p.returncode,
            "stdout": p.stdout.strip(),
            "stderr": p.stderr.strip(),
            "cmd": cmd,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "cmd": cmd}

def check_worker_ssh(target):
    if not target or target == "unknown":
        return "unknown", "worker_ssh", None, {"error": "missing target"}
    r = run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", target, "hostname"], timeout=8)
    return ("resolved" if r["ok"] else "no_change"), "worker_ssh", None, r

def check_restart_ollama(target):
    if not target or target == "unknown":
        return "unknown", "ollama_service_active", None, {"error": "missing target"}

    if target in ("localhost", "spot-core"):
        cmd = ["bash", "-lc", "systemctl is-active ollama"]
    else:
        cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", target, "systemctl is-active ollama"]

    r = run(cmd, timeout=8)
    active = r.get("stdout") == "active"
    return ("resolved" if active else "no_change"), "ollama_service_active", None, r

def find_json_state():
    candidates = [
        REPO_ROOT / "watch" / "fleet-status.json",
        REPO_ROOT / "watch" / "state" / "fleet-status.json",
        REPO_ROOT / "starfleet-ui" / "public" / "status.json",
        Path("/mnt/collective/logs/spot/fleet-status.json"),
        Path("/mnt/collective/fleet-status.json"),
    ]
    for path in candidates:
        if path.exists():
            try:
                yield path, json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue

def recursive_find_worker(obj, target):
    if isinstance(obj, dict):
        if str(obj.get("name") or obj.get("worker") or obj.get("host") or obj.get("hostname")) == target:
            return obj
        if target in obj and isinstance(obj[target], dict):
            return obj[target]
        for v in obj.values():
            found = recursive_find_worker(v, target)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = recursive_find_worker(item, target)
            if found:
                return found
    return None

def check_quarantine(target, wanted):
    for path, data in find_json_state():
        worker = recursive_find_worker(data, target)
        if not worker:
            continue
        q = worker.get("quarantined")
        eligible = worker.get("eligible")
        routing = worker.get("routing_enabled")
        after = {"path": str(path), "quarantined": q, "eligible": eligible, "routing_enabled": routing}

        if wanted:
            ok = q is True or eligible is False or routing is False
        else:
            ok = q is False or eligible is True or routing is True

        return ("resolved" if ok else "no_change"), "routing_quarantine_state", None, after

    return "unknown", "routing_quarantine_state", None, {"error": "no measurable fleet state found"}

def resolve_record(rec):
    d = rec.get("decision", {})
    action = str(d.get("action_type", ""))
    target = str(d.get("target", "unknown"))
    before = None

    if action in ("restart_ollama", "ollama_restart"):
        return check_restart_ollama(target)
    if action in ("worker_online", "wake_worker", "restart_worker"):
        return check_worker_ssh(target)
    if action in ("quarantine_worker", "worker_quarantine"):
        return check_quarantine(target, wanted=True)
    if action in ("unquarantine_worker", "worker_unquarantine", "release_worker"):
        return check_quarantine(target, wanted=False)

    return "unknown", "unmapped_action_metric", before, {"action_type": action, "target": target}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--min-age-seconds", type=int, default=180)
    p.add_argument("--limit", type=int, default=25)
    args = p.parse_args()

    count = 0
    for rec in pending_records(args.min_age_seconds):
        if count >= args.limit:
            break
        verdict, metric, before, after = resolve_record(rec)
        append_outcome_update(
            parent_record_id=rec["record_id"],
            verdict=verdict,
            metric=metric,
            before=before,
            after=after,
            notes="resolved by spot-outcome-resolve.py"
        )
        print(f"[RESOLVED] {rec['record_id']} {metric} {verdict}")
        count += 1

    print(f"RESULT: PASS resolved={count}")

if __name__ == "__main__":
    main()
