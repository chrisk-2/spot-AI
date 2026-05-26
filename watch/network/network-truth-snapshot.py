#!/usr/bin/env python3
import json
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path("/home/ogre/spot-stack")
BASE_URL = "http://127.0.0.1:8787"
STATUS_JSON = ROOT / "starfleet-ui/public/status.json"

def sh(cmd, timeout=8):
    try:
        p = subprocess.run(
            cmd,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return {
            "ok": p.returncode == 0,
            "returncode": p.returncode,
            "stdout": p.stdout.strip(),
            "stderr": p.stderr.strip(),
        }
    except Exception as e:
        return {
            "ok": False,
            "returncode": -1,
            "stdout": "",
            "stderr": repr(e),
        }

def get_json(path, timeout=8):
    url = BASE_URL + path
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return {
                "ok": True,
                "url": url,
                "data": json.loads(r.read().decode("utf-8")),
            }
    except Exception as e:
        return {
            "ok": False,
            "url": url,
            "error": repr(e),
            "data": None,
        }

def load_status():
    if not STATUS_JSON.exists():
        return {"ok": False, "path": str(STATUS_JSON), "data": None}
    try:
        return {
            "ok": True,
            "path": str(STATUS_JSON),
            "data": json.loads(STATUS_JSON.read_text()),
        }
    except Exception as e:
        return {"ok": False, "path": str(STATUS_JSON), "error": repr(e), "data": None}

def main():
    out = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "read_only",
        "mutation_authority": False,
        "executor": "spot-core",
        "sources": {
            "spot_health": get_json("/health"),
            "fleet_ping": get_json("/fleet/ping"),
            "routing": get_json("/routing"),
            "routing_audit": get_json("/stats/routing-audit?limit=25"),
            "fleet_status_file": load_status(),
            "local_routes": sh("ip route"),
            "local_addresses": sh("ip -brief addr"),
            "local_dns": sh("resolvectl status 2>/dev/null || systemd-resolve --status 2>/dev/null || cat /etc/resolv.conf"),
            "local_listeners": sh("ss -lntup"),
        },
    }
    print(json.dumps(out, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
