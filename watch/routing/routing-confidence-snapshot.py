#!/usr/bin/env python3
import json
import time
import urllib.request

BASE_URL = "http://127.0.0.1:8787"

EXPECTED = {
    "general": "spot-worker-01",
    "utility": "spot-worker-02",
    "coding": "spot-worker-03",
    "heavy": "spot-worker-04",
    "review": "spot-worker-05",
    "reasoning": "spot-worker-06",
}

def get_json(path, timeout=10):
    url = BASE_URL + path
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"_error": repr(e)}

def score_worker(worker):
    score = 100
    reasons = []

    if worker.get("ok") is not True:
        score -= 50
        reasons.append("not_ok")

    if worker.get("eligible") is not True:
        score -= 30
        reasons.append("not_eligible")

    if worker.get("quarantined") is True:
        score -= 40
        reasons.append("quarantined")

    alerts = worker.get("alerts") or []
    if alerts:
        score -= min(30, len(alerts) * 10)
        reasons.append("alerts_present")

    latency = worker.get("latency") or {}
    avg_ms = latency.get("avg_total_ms")
    if isinstance(avg_ms, (int, float)):
        if avg_ms > 30000:
            score -= 20
            reasons.append("very_high_latency")
        elif avg_ms > 10000:
            score -= 10
            reasons.append("high_latency")

    fallback_count = worker.get("fallback_count_window")
    if isinstance(fallback_count, int) and fallback_count > 0:
        score -= min(20, fallback_count * 2)
        reasons.append("fallbacks_present")

    return max(0, min(100, score)), reasons

def main():
    fleet = get_json("/fleet/ping")
    routing = get_json("/routing")
    audit = get_json("/stats/routing-audit?limit=100")

    workers = fleet if isinstance(fleet, dict) else {}

    role_scores = {}

    for role, expected_worker in EXPECTED.items():
        worker = workers.get(expected_worker) or {}
        score, reasons = score_worker(worker)

        actual = None
        if isinstance(routing, dict):
            actual = routing.get(role)

        role_scores[role] = {
            "role": role,
            "expected_worker": expected_worker,
            "actual_worker": actual,
            "owner_match": actual in [None, expected_worker],
            "confidence": score,
            "reasons": reasons,
            "worker_ok": worker.get("ok"),
            "eligible": worker.get("eligible"),
            "quarantined": worker.get("quarantined"),
            "fallback_count_window": worker.get("fallback_count_window"),
        }

    out = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "read_only",
        "mutation_authority": False,
        "executor": "spot-core",
        "routing": routing,
        "routing_audit_summary": {
            "ok": audit.get("ok") if isinstance(audit, dict) else None,
            "violations": audit.get("violations") if isinstance(audit, dict) else None,
            "fallbacks": audit.get("fallbacks") if isinstance(audit, dict) else None,
            "window_count": audit.get("window_count") if isinstance(audit, dict) else None,
        },
        "role_scores": role_scores,
    }

    print(json.dumps(out, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
