#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


VALID_ACTIONS = {"start", "stop", "restart", "degrade", "fail", "rollback"}
VALID_STATES = {"pending", "approved", "rejected", "dispatched", "blocked", "rolled_back"}


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def append_jsonl(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True) + "\n")


def queue_file(root: Path) -> Path:
    return root / "queue.json"


def queue_journal(root: Path) -> Path:
    return root / "journals" / "phase6-governed-apply-queue.jsonl"


def load_queue(root: Path) -> dict[str, Any]:
    return load_json(queue_file(root), {"plans": {}})


def save_queue(root: Path, queue: dict[str, Any]) -> None:
    write_json(queue_file(root), queue)


def require_fixture_target(target: str) -> None:
    if target != "fixture-service":
        raise SystemExit("blocked: target must be fixture-service")


def require_gate_ids(backup_id: str, rollback_id: str, validation_id: str) -> None:
    if not backup_id.startswith("backup-"):
        raise SystemExit("blocked: missing or invalid backup_id")
    if not rollback_id.startswith("rollback-"):
        raise SystemExit("blocked: missing or invalid rollback_id")
    if not validation_id.startswith("validation-"):
        raise SystemExit("blocked: missing or invalid validation_id")


def make_plan_id(target: str, action: str, nonce: str) -> str:
    return "plan-" + sha256_text(canonical({
        "target": target,
        "action": action,
        "nonce": nonce,
    }))[:24]


def journal(root: Path, event: str, plan: dict[str, Any], extra: dict[str, Any] | None = None) -> None:
    record = {
        "ts": int(time.time()),
        "event": event,
        "plan_id": plan["plan_id"],
        "target": plan["target"],
        "action": plan["action"],
        "state": plan["state"],
        "mutation_scope": "fixture_only",
    }
    if extra:
        record.update(extra)
    record["record_hash"] = sha256_text(canonical(record))
    append_jsonl(queue_journal(root), record)


def cmd_enqueue(args: argparse.Namespace) -> None:
    root = Path(args.root)
    require_fixture_target(args.target)

    if args.action not in VALID_ACTIONS:
        raise SystemExit("blocked: invalid fixture action")

    require_gate_ids(args.backup_id, args.rollback_id, args.validation_id)

    queue = load_queue(root)
    plan_id = make_plan_id(args.target, args.action, args.nonce)

    if plan_id in queue["plans"]:
        raise SystemExit("blocked: duplicate plan_id")

    plan = {
        "plan_id": plan_id,
        "target": args.target,
        "action": args.action,
        "nonce": args.nonce,
        "requested_by": args.requested_by,
        "backup_id": args.backup_id,
        "rollback_id": args.rollback_id,
        "validation_id": args.validation_id,
        "force_verify_fail": bool(args.force_verify_fail),
        "state": "pending",
        "created_at": int(time.time()),
    }

    queue["plans"][plan_id] = plan
    save_queue(root, queue)
    journal(root, "enqueue", plan)
    print(json.dumps(plan, sort_keys=True))


def cmd_approve(args: argparse.Namespace) -> None:
    root = Path(args.root)
    queue = load_queue(root)
    plan = queue["plans"].get(args.plan_id)
    if not plan:
        raise SystemExit("blocked: missing plan")
    if plan["state"] != "pending":
        raise SystemExit("blocked: only pending plans can be approved")
    if args.approved_by != "spot-core":
        raise SystemExit("blocked: approval authority must be spot-core")

    plan["state"] = "approved"
    plan["approved_by"] = args.approved_by
    plan["approved_at"] = int(time.time())
    save_queue(root, queue)
    journal(root, "approve", plan)
    print(json.dumps(plan, sort_keys=True))


def cmd_reject(args: argparse.Namespace) -> None:
    root = Path(args.root)
    queue = load_queue(root)
    plan = queue["plans"].get(args.plan_id)
    if not plan:
        raise SystemExit("blocked: missing plan")
    if plan["state"] != "pending":
        raise SystemExit("blocked: only pending plans can be rejected")

    plan["state"] = "rejected"
    plan["rejected_by"] = args.rejected_by
    plan["rejected_at"] = int(time.time())
    plan["reject_reason"] = args.reason
    save_queue(root, queue)
    journal(root, "reject", plan)
    print(json.dumps(plan, sort_keys=True))


def cmd_dispatch(args: argparse.Namespace) -> None:
    root = Path(args.root)
    queue = load_queue(root)
    plan = queue["plans"].get(args.plan_id)

    if not plan:
        raise SystemExit("blocked: missing plan")
    if args.executor != "spot-core":
        raise SystemExit("blocked: executor must be spot-core")
    if plan["state"] != "approved":
        raise SystemExit(f"blocked: plan state is {plan['state']}")
    if plan["target"] != "fixture-service":
        raise SystemExit("blocked: target must be fixture-service")

    orch = Path(__file__).with_name("spot-fixture-service-orchestrator.py")

    cmd = [
        sys.executable,
        str(orch),
        "action",
        "--root",
        str(root),
        "--target",
        plan["target"],
        "--action",
        plan["action"],
        "--lease-file",
        args.lease_file,
        "--nonce",
        plan["nonce"],
    ]

    if plan.get("force_verify_fail"):
        cmd.append("--force-verify-fail")

    p = subprocess.run(cmd, text=True, capture_output=True)

    if p.returncode != 0:
        plan["state"] = "blocked"
        plan["dispatch_error"] = p.stderr.strip() or p.stdout.strip()
        save_queue(root, queue)
        journal(root, "dispatch_blocked", plan, {"error": plan["dispatch_error"]})
        raise SystemExit(plan["dispatch_error"])

    receipt = json.loads(p.stdout)
    plan["receipt"] = receipt
    plan["state"] = "rolled_back" if receipt["result"] == "rolled_back" else "dispatched"
    plan["dispatched_at"] = int(time.time())
    save_queue(root, queue)
    journal(root, "dispatch", plan, {"receipt_id": receipt["receipt_id"], "result": receipt["result"]})
    print(json.dumps(plan, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Phase 6 governed fixture apply queue")
    sub = p.add_subparsers(required=True)

    enqueue = sub.add_parser("enqueue")
    enqueue.add_argument("--root", required=True)
    enqueue.add_argument("--target", required=True)
    enqueue.add_argument("--action", required=True)
    enqueue.add_argument("--nonce", required=True)
    enqueue.add_argument("--requested-by", default="operator")
    enqueue.add_argument("--backup-id", required=True)
    enqueue.add_argument("--rollback-id", required=True)
    enqueue.add_argument("--validation-id", required=True)
    enqueue.add_argument("--force-verify-fail", action="store_true")
    enqueue.set_defaults(func=cmd_enqueue)

    approve = sub.add_parser("approve")
    approve.add_argument("--root", required=True)
    approve.add_argument("--plan-id", required=True)
    approve.add_argument("--approved-by", default="spot-core")
    approve.set_defaults(func=cmd_approve)

    reject = sub.add_parser("reject")
    reject.add_argument("--root", required=True)
    reject.add_argument("--plan-id", required=True)
    reject.add_argument("--rejected-by", default="operator")
    reject.add_argument("--reason", default="operator rejected")
    reject.set_defaults(func=cmd_reject)

    dispatch = sub.add_parser("dispatch")
    dispatch.add_argument("--root", required=True)
    dispatch.add_argument("--plan-id", required=True)
    dispatch.add_argument("--lease-file", required=True)
    dispatch.add_argument("--executor", default="spot-core")
    dispatch.set_defaults(func=cmd_dispatch)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
