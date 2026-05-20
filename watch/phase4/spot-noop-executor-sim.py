#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

CASES = {
    "allowed_noop",
    "kill_switch_blocked",
    "lease_collision",
    "interrupted_before_receipt",
    "interrupted_after_receipt",
    "stale_lease_replay",
}


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def envelope_digest(material: str) -> str:
    return sha256_text(f"gov-envelope|{material}")[:16]


def replay_guard(material: str) -> str:
    return sha256_text(f"replay-guard|{material}")[:24]


def build_doc(args: argparse.Namespace, digest: str) -> dict:
    allowed = args.case in {"allowed_noop", "interrupted_after_receipt"}

    if args.case == "allowed_noop":
        blocked_reason = None
        final_outcome = "success"
        recovery_state = "clean_success"
        receipt_valid = True
        lease_valid = True
        replay_detected = False
        kill_switch_state = "clear"

    elif args.case == "kill_switch_blocked":
        blocked_reason = "kill_switch_active"
        final_outcome = "blocked"
        recovery_state = "clean_blocked"
        receipt_valid = True
        lease_valid = True
        replay_detected = False
        kill_switch_state = "active"

    elif args.case == "lease_collision":
        blocked_reason = "lease_collision"
        final_outcome = "blocked"
        recovery_state = "clean_blocked"
        receipt_valid = True
        lease_valid = False
        replay_detected = False
        kill_switch_state = "clear"

    elif args.case == "interrupted_before_receipt":
        blocked_reason = "interrupted_before_receipt"
        final_outcome = "blocked"
        recovery_state = "incomplete_before_receipt"
        receipt_valid = False
        lease_valid = True
        replay_detected = False
        kill_switch_state = "clear"

    elif args.case == "interrupted_after_receipt":
        blocked_reason = None
        final_outcome = "success"
        recovery_state = "clean_success"
        receipt_valid = True
        lease_valid = True
        replay_detected = False
        kill_switch_state = "clear"

    elif args.case == "stale_lease_replay":
        blocked_reason = "stale_lease"
        final_outcome = "blocked"
        recovery_state = "stale_lease"
        receipt_valid = True
        lease_valid = False
        replay_detected = True
        kill_switch_state = "clear"

    else:
        raise SystemExit(f"unknown case: {args.case}")

    material = "|".join([
        args.request_id,
        args.case,
        args.target,
        "phase4-noop-executor",
    ])

    return {
        "receipt_id": f"RECEIPT-{digest}",
        "created_at": utc_now(),
        "request_id": args.request_id,
        "execution_id": f"EXEC-{digest}",
        "lease_id": f"LEASE-{digest}",
        "envelope_id": f"ENV-{digest}",
        "envelope_hash": envelope_digest(material),
        "replay_guard": replay_guard(material),
        "phase": "4",
        "executor": "spot-core",
        "action_type": "noop",
        "target": args.target,
        "risk_class": "none",
        "approval_state": "not_required",
        "review_state": "pass",
        "backup_state": "not_required",
        "rollback_state": "not_required",
        "kill_switch_state": kill_switch_state,
        "case": args.case,
        "blocked_reason": blocked_reason,
        "mutation_performed": False,
        "execution_performed": allowed,
        "noop_performed": allowed,
        "rollback_required": False,
        "rollback_performed": False,
        "kill_switch_checked": True,
        "lease_checked": True,
        "lease_valid": lease_valid,
        "receipt_valid": receipt_valid,
        "replay_guard_checked": True,
        "replay_detected": replay_detected,
        "git_apply_performed": False,
        "service_restart_performed": False,
        "recovery_state": recovery_state,
        "final_outcome": final_outcome,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Phase 4 noop executor simulator.")
    ap.add_argument("--request-id", required=True)
    ap.add_argument("--case", required=True, choices=sorted(CASES))
    ap.add_argument("--target", default="phase4-noop-fixture")
    ap.add_argument("--out-dir", default="watch/phase4/runs")
    args = ap.parse_args()

    material = "|".join([
        args.request_id,
        args.case,
        args.target,
        "phase4-noop-executor",
    ])

    digest = sha256_text(material)[:12]
    doc = build_doc(args, digest)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    out = out_dir / f"{doc['receipt_id']}.json"
    out.write_text(json.dumps(doc, indent=2) + "\n")

    print(out)


if __name__ == "__main__":
    main()
