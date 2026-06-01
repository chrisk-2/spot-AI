#!/usr/bin/env python3
import json
import urllib.error
import urllib.request
import time

URLS = [
    "http://127.0.0.1:8787/review/local",
    "http://127.0.0.1:8787/health",
]
TIMEOUT = 3

out = {
    "check": "review_local_diagnostic",
    "timeout_seconds": TIMEOUT,
    "status": "PASS",
    "results": []
}

for url in URLS:
    started = time.time()
    row = {"url": url}
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            row["http_status"] = r.status
            row["elapsed_ms"] = round((time.time() - started) * 1000, 2)
            row["ok"] = 200 <= r.status < 500
    except urllib.error.HTTPError as e:
        row["http_status"] = e.code
        row["elapsed_ms"] = round((time.time() - started) * 1000, 2)
        row["ok"] = True
        row["note"] = "endpoint reachable; returned HTTP error"
    except Exception as e:
        row["elapsed_ms"] = round((time.time() - started) * 1000, 2)
        row["ok"] = False
        row["error"] = type(e).__name__
        row["detail"] = str(e)
        out["status"] = "WARN"
    out["results"].append(row)

print(json.dumps(out, indent=2))
