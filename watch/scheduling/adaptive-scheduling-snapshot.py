#!/usr/bin/env python3
import json
import subprocess
import time

ROLE_ORDER = ["general", "utility", "coding", "heavy", "review", "reasoning"]

def run_json(cmd, timeout=30):
    p = subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    if p.returncode != 0:
        return {"_ok": False, "_error": p.stderr.strip()}
    try:
        data = json.loads(p.stdout)
        if isinstance(data, dict):
            data["_ok"] = True
        return data
    except Exception as e:
        return {"_ok": False, "_error": repr(e)}

def confidence_band(score):
    if score >= 90:
        return "high"
    if score >= 70:
        return "medium"
    if score >= 50:
        return "low"
    return "blocked"

def main():
    capabilities = run_json(["watch/capabilities/capability-registry-snapshot.py"])
    routing = run_json(["watch/routing/routing-confidence-snapshot.py"])

    workers = capabilities.get("workers") or {}
    role_scores = routing.get("role_scores") or {}

    recommendations = {}

    for role in ROLE_ORDER:
        score = role_scores.get(role) or {}
        worker_name = score.get("expected_worker")
        worker = workers.get(worker_name) or {}

        confidence = score.get("confidence", 0)
        band = confidence_band(confidence)

        recommendations[role] = {
            "role": role,
            "recommended_worker": worker_name,
            "confidence": confidence,
            "confidence_band": band,
            "advisory_only": True,
            "eligible": worker.get("eligible"),
            "quarantined": worker.get("quarantined"),
            "primary_role": worker.get("primary_role"),
            "installed_models": worker.get("installed_models") or [],
            "warm_models": worker.get("warm_models") or {},
            "reasons": score.get("reasons") or [],
            "action": "use_locked_owner" if band != "blocked" else "hold_for_operator_review",
        }

    out = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "read_only",
        "mutation_authority": False,
        "execution_allowed": False,
        "executor": "spot-core",
        "advisory_only": True,
        "inputs": {
            "capabilities_ok": capabilities.get("_ok"),
            "routing_confidence_ok": routing.get("_ok"),
        },
        "recommendations": recommendations,
    }

    print(json.dumps(out, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
