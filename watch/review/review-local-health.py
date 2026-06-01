#!/usr/bin/env python3
import json
import time
import urllib.error
import urllib.request

URL = "http://127.0.0.1:8787/review/local"
TIMEOUT = 3

started = time.time()
result = {
    "check": "review_local_health",
    "url": URL,
    "timeout_seconds": TIMEOUT,
    "status": "WARN",
    "reachable": False,
    "http_status": None,
    "elapsed_ms": None,
    "note": ""
}

try:
    req = urllib.request.Request(URL, method="GET")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        result["http_status"] = r.status
        result["reachable"] = True
        result["status"] = "PASS"
        result["note"] = "endpoint reachable"
except urllib.error.HTTPError as e:
    result["http_status"] = e.code
    result["reachable"] = True
    if e.code in (400, 401, 403, 404, 405, 422):
        result["status"] = "PASS"
        result["note"] = "endpoint reachable; returned expected non-GET response"
    else:
        result["status"] = "WARN"
        result["note"] = "endpoint reachable; unexpected HTTP error"
except Exception as e:
    result["status"] = "WARN"
    result["note"] = f"{type(e).__name__}: {e}"

result["elapsed_ms"] = round((time.time() - started) * 1000, 2)
print(json.dumps(result, indent=2))
raise SystemExit(0 if result["status"] == "PASS" else 1)
