#!/usr/bin/env python3
import json
import time
import urllib.request

BASE_URL = "http://127.0.0.1:8787"

REQUIRED_ENDPOINTS = {
    "health": "/health",
    "fleet_ping": "/fleet/ping",
    "routing": "/routing",
    "routing_audit": "/stats/routing-audit?limit=25",
    "governance_events": "/stats/runtime/governance-events?limit=25",
}

OPTIONAL_ENDPOINTS = {
    "runtime_journals": "/stats/runtime/journals",
    "review_lease": "/stats/runtime/review-lease",
    "queue_metrics": "/stats/runtime/queue",
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

def main():
    out = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "read_only",
        "mutation_authority": False,
        "executor": "spot-core",
        "required": {name: get_json(path) for name, path in REQUIRED_ENDPOINTS.items()},
        "optional": {name: get_json(path) for name, path in OPTIONAL_ENDPOINTS.items()},
    }

    print(json.dumps(out, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
