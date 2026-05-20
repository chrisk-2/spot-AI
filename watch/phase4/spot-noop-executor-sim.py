#!/usr/bin/env python3
import argparse
import hashlib
import json
from datetime import datetime, UTC
from pathlib import Path

CASES = {"allowed_noop", "kill_switch_blocked", "lease_collision"}

def utc_now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

def sha256_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

def main():
    ap = argparse.ArgumentParser(description="Phase 4 noop executor simulator.")
    ap.add_argument("--request-id", required=True)
    ap.add_argument("--case", required=True, choices=sorted(CASES))
    ap.add_argument("--target", default="phase4-noop-fixture")
    ap.add_argument("--out-dir", default="watch/phase4/runs")
    args = ap.parse_args()

    material = "|".join([args.request_id, args.case, args.target, "phase4-noop-executor"])
    digest = sha256_text(material)[:12]

    allowed = args.case == "allowed_noop"
    reason = None if allowed else args.case

    doc = {
        "receipt_id": f"RECEIPT-{digest}",
        "created_at": utc_now(),
        "request_id": args.request_id,
        "execution_id": f"EXEC-{digest}",
        "lease_id": f"LEASE-{digest}",
        "phase": "4",
        "executor": "spot-core",
        "action_type": "noop",
        "target": args.target,
        "risk_class": "none",
        "case": args.case,
        "blocked_reason": reason,
        "mutation_performed": False,
        "execution_performed": allowed,
        "noop_performed": allowed,
        "rollback_required": False,
        "rollback_performed": False,
        "kill_switch_checked": True,
        "lease_checked": True,
        "git_apply_performed": False,
        "service_restart_performed": False,
        "final_outcome": "success" if allowed else "blocked",
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{doc['receipt_id']}.json"
    out.write_text(json.dumps(doc, indent=2) + "\n")
    print(out)

if __name__ == "__main__":
    main()
