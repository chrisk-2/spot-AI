#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
mkdir -p watch/state

python3 - <<'PY'
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
STATE_DIR = ROOT / "watch" / "state"
STATE_FILE = STATE_DIR / "spot-life.json"
EVENT_FILE = STATE_DIR / "spot-life-events.jsonl"

WORKERS = {
    "spot-worker-01": "general",
    "spot-worker-02": "utility/watcher",
    "spot-worker-03": "coding",
    "spot-worker-04": "heavy",
    "spot-worker-05": "review",
    "spot-worker-06": "reasoning/heavy-overflow",
}

NON_WORKERS = ["spot-ui-01", "starfleet-tower", "starfleet-core"]

JSON_SOURCES = [
    "watch/state/spot-readiness.json",
    "watch/state/readiness.json",
    "watch/state/readiness-status.json",
    "watch/state/spot-self-heal.json",
    "watch/state/self-heal.json",
    "watch/state/self-heal-actions.json",
    "watch/state/fleet-status.json",
    "watch/state/routing-health.json",
    "watch/state/routing-audit.json",
    "watch/state/governance.json",
    "starfleet-ui/public/status.json",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run(cmd: list[str], timeout: int = 5) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return {"ok": p.returncode == 0, "rc": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except Exception as e:
        return {"ok": False, "rc": None, "stdout": "", "stderr": str(e)}


def http_ok(url: str, timeout: int = 2) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "spot-life-pulse/read-only"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= int(r.status) < 300
    except Exception:
        return False


def load_sources() -> list[dict[str, Any]]:
    out = []
    for rel in JSON_SOURCES:
        p = ROOT / rel
        if not p.exists() or not p.is_file():
            continue
        try:
            out.append({"source": rel, "data": json.loads(p.read_text(encoding="utf-8"))})
        except Exception as e:
            out.append({"source": rel, "data": None, "error": str(e)})
    return out


def walk(obj: Any, path: tuple[str, ...] = ()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = path + (str(k),)
            yield p, v
            yield from walk(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, path + (str(i),))


def norm(v: Any) -> str | None:
    if isinstance(v, bool):
        return "OK" if v else "FAIL"
    if isinstance(v, str):
        s = v.strip()
        u = s.upper()
        if u in {"OK", "READY", "PASS", "PASSED", "HEALTHY", "CLEAR", "NOMINAL", "TRUE"}:
            return "OK"
        if u in {"WARN", "WARNING", "DEGRADED"}:
            return "WARN"
        if u in {"FAIL", "FAILED", "ERROR", "BLOCKED", "DOWN", "FALSE"}:
            return "FAIL"
        return s if s else None
    if isinstance(v, dict):
        for k in ("status", "state", "ok", "ready", "healthy"):
            if k in v:
                return norm(v[k])
    return None


def find_status(sources: list[dict[str, Any]], markers: list[str]) -> dict[str, Any]:
    for src in sources:
        data = src.get("data")
        if data is None:
            continue
        for path, value in walk(data):
            joined = ".".join(path).lower()
            if any(m in joined for m in markers):
                status = norm(value)
                if status:
                    return {"status": status, "source": src["source"], "path": ".".join(path)}
    return {"status": "UNKNOWN", "source": None, "path": None}


def self_heal_count(sources: list[dict[str, Any]]) -> dict[str, Any]:
    for src in sources:
        data = src.get("data")
        if data is None:
            continue
        src_name = str(src["source"]).lower()
        for path, value in walk(data):
            joined = ".".join(path).lower()
            key = path[-1].lower() if path else ""
            if (("self" in src_name and "heal" in src_name) or ("self" in joined and "heal" in joined)) and ("action" in joined or key == "actions"):
                if isinstance(value, list):
                    return {"count": len(value), "source": src["source"], "path": ".".join(path)}
                if isinstance(value, int):
                    return {"count": value, "source": src["source"], "path": ".".join(path)}
    return {"count": None, "source": None, "path": None}


def json_backup_status(sources: list[dict[str, Any]]) -> dict[str, Any]:
    for src in sources:
        data = src.get("data")
        if data is None:
            continue
        for path, value in walk(data):
            joined = ".".join(path).lower()
            if any(k in joined for k in ("backups_ok", "backup_fresh", "backup_freshness")):
                s = norm(value)
                if s == "OK":
                    return {"status": "fresh", "source": src["source"], "path": ".".join(path)}
                if s == "FAIL":
                    return {"status": "stale", "source": src["source"], "path": ".".join(path)}
    return {"status": "unknown", "source": None, "path": None}


def newest_mtime(base: Path, limit_seconds: float = 3.0) -> float | None:
    if not base.exists() or not base.is_dir():
        return None
    start = time.time()
    newest = None
    seen = 0
    for root, dirs, files in os.walk(base):
        if time.time() - start > limit_seconds:
            break
        if len(Path(root).relative_to(base).parts) >= 5:
            dirs[:] = []
        for f in files:
            seen += 1
            if seen > 10000 or time.time() - start > limit_seconds:
                break
            try:
                mt = (Path(root) / f).stat().st_mtime
                newest = mt if newest is None else max(newest, mt)
            except Exception:
                pass
    return newest


def _newest_backup_mtime(base: Path) -> float | None:
    helper = globals().get("newest_mtime_limited") or globals().get("newest_mtime")
    if helper:
        try:
            return helper(base)
        except Exception:
            return None
    return None


def _direct_backup_freshness() -> dict[str, Any]:
    now = time.time()
    per_worker: dict[str, Any] = {}

    roots = [
        Path("/mnt/collective/backups"),
        Path("/mnt/collective/spot/backups"),
        Path("/mnt/collective/logs/spot/backups"),
        Path("/mnt/unimatrix6/backups"),
        Path("/mnt/unimatrix6/spot/backups"),
        Path("/mnt/unimatrix6/logs/spot/backups"),
    ]

    for worker in WORKERS:
        newest: float | None = None
        found_base: Path | None = None

        for root in roots:
            for c in (
                root / worker,
                root / "fleet" / worker,
                root / "workers" / worker,
                root / "worker" / worker,
                root / "hosts" / worker,
            ):
                mt = _newest_backup_mtime(c)
                if mt is not None and (newest is None or mt > newest):
                    newest = mt
                    found_base = c

        if newest is None:
            per_worker[worker] = {"status": "unknown", "age_hours": None, "source": None}
        else:
            age_hours = round((now - newest) / 3600, 2)
            per_worker[worker] = {
                "status": "fresh" if age_hours <= 24 else "stale",
                "age_hours": age_hours,
                "source": str(found_base) if found_base else None,
            }

    known = [v for v in per_worker.values() if v["age_hours"] is not None]

    if len(known) == len(WORKERS) and all(v["status"] == "fresh" for v in known):
        status = "fresh"
    elif any(v["status"] == "stale" for v in known):
        status = "stale"
    else:
        status = "unknown"

    return {
        "status": status,
        "max_age_hours": max((v["age_hours"] for v in known), default=None),
        "per_worker": per_worker,
        "source": "direct_backup_tree",
    }


def _validator_backup_freshness() -> dict[str, Any] | None:
    candidates = [
        ["./watch/module/spot-module.sh", "validate"],
        ["./watch/fleet-validate.sh"],
    ]

    for cmd in candidates:
        if not Path(cmd[0]).exists():
            continue

        result = run(cmd, timeout=240)
        output = f"{result.get('stdout', '')}\n{result.get('stderr', '')}"

        if result.get("rc") != 0:
            continue
        if "RESULT: PASS" not in output and not re.search(r"pass=\d+\s+warn=0\s+fail=0", output):
            continue

        per_worker: dict[str, Any] = {}
        for worker in WORKERS:
            m = re.search(rf"backup freshness:\s*{re.escape(worker)}\s+age=([0-9.]+)h", output)
            if not m:
                continue
            age_hours = float(m.group(1))
            per_worker[worker] = {
                "status": "fresh" if age_hours <= 24 else "stale",
                "age_hours": age_hours,
                "source": "validator:" + " ".join(cmd),
            }

        if len(per_worker) == len(WORKERS):
            known = list(per_worker.values())
            status = "fresh" if all(v["status"] == "fresh" for v in known) else "stale"
            return {
                "status": status,
                "max_age_hours": max(v["age_hours"] for v in known),
                "per_worker": per_worker,
                "source": "validator",
            }

    return None


def backup_freshness(sources: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    direct = _direct_backup_freshness()
    if direct["status"] == "fresh":
        return direct

    validator = _validator_backup_freshness()
    if validator is not None:
        return validator

    return direct


def probe(host: str, role: str | None = None) -> dict[str, Any]:
    dns_ok = False
    addresses = []
    try:
        addresses = sorted({x[4][0] for x in socket.getaddrinfo(host, None)})
        dns_ok = bool(addresses)
    except Exception:
        pass

    ping = run(["ping", "-c", "1", "-W", "1", host], timeout=3)
    ssh = run([
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=3",
        "-o", "PreferredAuthentications=publickey",
        "-o", "PasswordAuthentication=no",
        host,
        "hostname",
    ], timeout=5)

    remote_hostname = ssh["stdout"].splitlines()[0].strip() if ssh["stdout"] else ""
    hostname_match = remote_hostname == host if remote_hostname else False

    return {
        "host": host,
        "role": role,
        "dns_ok": dns_ok,
        "addresses": addresses,
        "ping_ok": bool(ping["ok"]),
        "ssh_ok": bool(ssh["ok"]),
        "hostname": remote_hostname,
        "hostname_match": hostname_match,
        "healthy": bool(ssh["ok"] and (hostname_match or not remote_hostname)),
    }



def _extract_json_objects(raw: str) -> list[Any]:
    objects: list[Any] = []
    raw = raw.strip()
    if not raw:
        return objects

    try:
        objects.append(json.loads(raw))
        return objects
    except Exception:
        pass

    for line in raw.splitlines():
        line = line.strip()
        if not line or not line.startswith(("{", "[")):
            continue
        try:
            objects.append(json.loads(line))
        except Exception:
            continue

    return objects


def _readiness_from_commands() -> dict[str, Any]:
    candidates = [
        ["./watch/spot-ops.sh", "readiness"],
        ["./watch/spot-ops.sh", "ready"],
        ["./watch/spot-ops.sh", "status"],
        ["./watch/module/spot-module.sh", "status"],
        ["./watch/readiness.sh"],
        ["./watch/spot-readiness.sh"],
    ]

    for cmd in candidates:
        if not Path(cmd[0]).exists():
            continue

        result = run(cmd, timeout=30)
        output = f"{result.get('stdout', '')}\n{result.get('stderr', '')}".strip()
        if not output:
            continue

        for obj in _extract_json_objects(output):
            status = normalize_status(obj)
            if status:
                return {
                    "status": status,
                    "source": "command:" + " ".join(cmd),
                    "path": "$",
                }

        upper = output.upper()
        if re.search(r"\bREADINESS\b.*\bOK\b", upper) or re.search(r"\bSTATUS\b.*\bOK\b", upper) or re.search(r"\bREADY\b", upper):
            if not re.search(r"\bFAIL\b|\bERROR\b|\bBLOCKED\b", upper):
                return {
                    "status": "OK",
                    "source": "command:" + " ".join(cmd),
                    "path": "stdout",
                }

    for cmd in (["./watch/module/spot-module.sh", "validate"], ["./watch/fleet-validate.sh"]):
        if not Path(cmd[0]).exists():
            continue
        result = run(cmd, timeout=240)
        output = f"{result.get('stdout', '')}\n{result.get('stderr', '')}"
        if result.get("rc") == 0 and ("RESULT: PASS" in output or re.search(r"pass=\d+\s+warn=0\s+fail=0", output)):
            return {
                "status": "OK",
                "source": "validator:" + " ".join(cmd),
                "path": "summary",
            }

    return {"status": "UNKNOWN", "source": None, "path": None}


def _self_heal_from_commands() -> dict[str, Any]:
    candidates = [
        ["./watch/spot-ops.sh", "self-heal"],
        ["./watch/spot-ops.sh", "selfheal"],
        ["./watch/spot-ops.sh", "heal"],
        ["./watch/self-heal.sh"],
        ["./watch/spot-self-heal.sh"],
    ]

    for cmd in candidates:
        if not Path(cmd[0]).exists():
            continue

        result = run(cmd, timeout=30)
        output = f"{result.get('stdout', '')}\n{result.get('stderr', '')}".strip()
        if not output:
            continue

        for obj in _extract_json_objects(output):
            if isinstance(obj, list):
                return {"count": len(obj), "source": "command:" + " ".join(cmd), "path": "$"}
            if isinstance(obj, dict):
                for key in ("actions", "planned_actions", "proposals", "items"):
                    if isinstance(obj.get(key), list):
                        return {
                            "count": len(obj[key]),
                            "source": "command:" + " ".join(cmd),
                            "path": key,
                        }
                for key in ("action_count", "count", "pending"):
                    if isinstance(obj.get(key), int):
                        return {
                            "count": obj[key],
                            "source": "command:" + " ".join(cmd),
                            "path": key,
                        }

        lower = output.lower()
        if "actions: []" in lower or "actions=[]" in lower or "no actions" in lower or output.strip() == "[]":
            return {"count": 0, "source": "command:" + " ".join(cmd), "path": "stdout"}

    for cmd in (["./watch/module/spot-module.sh", "validate"], ["./watch/fleet-validate.sh"]):
        if not Path(cmd[0]).exists():
            continue
        result = run(cmd, timeout=240)
        output = f"{result.get('stdout', '')}\n{result.get('stderr', '')}"
        if result.get("rc") == 0 and ("RESULT: PASS" in output or re.search(r"pass=\d+\s+warn=0\s+fail=0", output)):
            return {
                "count": 0,
                "source": "validator_clean_no_self_heal_actions",
                "path": "summary",
            }

    return {"count": None, "source": None, "path": None}

def main() -> None:
    sources = load_sources()

    core_ok = http_ok("http://127.0.0.1:8787/health") or http_ok("http://127.0.0.1:8787/stats/runtime") or http_ok("http://127.0.0.1:8787/")
    bridge_ok = http_ok("http://127.0.0.1:8010/")

    workers = {h: probe(h, r) for h, r in WORKERS.items()}
    non_workers = {h: probe(h) for h in NON_WORKERS}

    workers_healthy = sum(1 for x in workers.values() if x["healthy"])
    readiness = find_status(sources, ["readiness", "ready"])
    if readiness["status"] == "UNKNOWN":
        readiness = _readiness_from_commands()
    self_heal = self_heal_count(sources)
    if self_heal["count"] is None:
        self_heal = _self_heal_from_commands()

    # Keep schema stable for consumers: expose both names.
    if "action_count" not in self_heal and "count" in self_heal:
        self_heal["action_count"] = self_heal["count"]
    if "count" not in self_heal and "action_count" in self_heal:
        self_heal["count"] = self_heal["action_count"]
    backups = backup_freshness(sources)
    routing = find_status(sources, ["routing_health", "routing.status", "routing_status", "route_health"])

    concerns = []
    for h, s in workers.items():
        if not s["healthy"]:
            concerns.append(f"{h} worker health degraded")
    for h, s in non_workers.items():
        if not s["ssh_ok"]:
            concerns.append(f"{h} SSH down")
    if readiness["status"] not in {"OK", "UNKNOWN"}:
        concerns.append(f"readiness {readiness['status']}")
    if isinstance(self_heal["count"], int) and self_heal["count"] > 0:
        concerns.append(f"self-heal has {self_heal['count']} action(s) pending")
    if backups["status"] == "stale":
        concerns.append("backup freshness stale")
    if routing["status"] not in {"OK", "UNKNOWN"}:
        concerns.append(f"routing {routing['status']}")

    if any("worker health degraded" in x for x in concerns):
        suggested = "restore worker reachability before advancing autonomy."
    elif any(x.endswith("SSH down") for x in concerns):
        suggested = "confirm whether offline non-worker hosts are expected."
    elif isinstance(self_heal["count"], int) and self_heal["count"] > 0:
        suggested = "review self-heal proposals without applying changes."
    else:
        suggested = "continue read-only observation cadence; do not enable mutation."

    pulse = {
        "timestamp": now_utc(),
        "schema": "spot.life_pulse.v1",
        "mode": "read_only_observe_summarize_journal_propose",
        "spot_awake": bool(core_ok or bridge_ok),
        "ready_state": "ready" if (core_ok or bridge_ok) and workers_healthy == len(WORKERS) and readiness["status"] in {"OK", "UNKNOWN"} else "degraded",
        "mutation_authority": False,
        "execution_allowed": False,
        "apis": {
            "core_api_8787_ok": bool(core_ok),
            "bridge_api_8010_ok": bool(bridge_ok),
            "bridge_health_path": "http://127.0.0.1:8010/",
        },
        "fleet": {
            "workers_total": len(WORKERS),
            "workers_healthy": workers_healthy,
            "workers": workers,
            "non_worker_hosts": non_workers,
        },
        "readiness": readiness,
        "self_heal": self_heal,
        "backups": backups,
        "routing": routing,
        "governance": {
            "state": "observe_only",
            "mutation_authority": False,
            "execution_allowed": False,
            "auto_apply": False,
            "full_autonomy": False,
            "policy": "read-only life pulse; summarize and propose only",
        },
        "open_concerns": concerns,
        "suggested_next_action": suggested,
    }

    action_count = pulse["self_heal"]["count"]
    self_heal_text = "Self-heal action count unknown." if action_count is None else ("Self-heal has no actions." if action_count == 0 else f"Self-heal has {action_count} action(s).")
    backup_text = "Backups fresh." if backups["status"] == "fresh" else ("Backups stale." if backups["status"] == "stale" else "Backup freshness unknown.")
    concern_text = ", ".join(concerns) if concerns else "none"

    pulse["summary"] = (
        f"Spot is {'awake' if pulse['spot_awake'] else 'not awake'}. "
        f"Fleet workers {workers_healthy}/{len(WORKERS)} healthy. "
        f"Readiness {readiness['status']}. {self_heal_text} {backup_text} "
        f"Open concerns: {concern_text}. "
        f"Suggested next action: {suggested} Mutation authority: false."
    )

    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(pulse, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(STATE_FILE)

    with EVENT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(pulse, sort_keys=True) + "\n")

    print(pulse["summary"])


main()
PY
