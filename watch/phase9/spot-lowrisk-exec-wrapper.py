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


ALLOWED_FIXTURE_ACTION_MAP = {
    "lowrisk-fixture-start": "start",
    "lowrisk-fixture-stop": "stop",
    "lowrisk-fixture-restart": "restart",
}


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


def block(root: Path, plan: dict[str, Any], reason: str) -> None:
    record = {
        "schema": "phase9.execution.v1",
        "ts": int(time.time()),
        "plan_id": plan.get("plan_id", "unknown"),
        "target": plan.get("target", "unknown"),
        "action": plan.get("action", "unknown"),
        "result": "blocked",
        "block_reason": reason,
        "mutation_scope": "none",
    }
    record["record_hash"] = sha256_text(canonical(record))
    append_jsonl(root / "journals" / "phase9-denied-executions.jsonl", record)
    raise SystemExit(f"blocked: {reason}")


def make_execution_id(plan: dict[str, Any]) -> str:
    return "exec-" + sha256_text(canonical({
        "plan_id": plan.get("plan_id"),
        "target": plan.get("target"),
        "action": plan.get("action"),
        "nonce": plan.get("nonce"),
    }))[:24]


def validate_lease(lease: dict[str, Any]) -> None:
    if lease.get("owner") != "spot-core":
        raise SystemExit("lease owner is not spot-core")
    if int(lease.get("expires_at", 0)) <= int(time.time()):
        raise SystemExit("execution lease expired")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 9 approval-gated low-risk fixture execution wrapper"
    )
    parser.add_argument("--root", required=True)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--lease-file", required=True)
    parser.add_argument("--executor", default="spot-core")
    args = parser.parse_args()

    root = Path(args.root)
    plan = load_json(Path(args.plan_file), {})
    lease = load_json(Path(args.lease_file), {})

    try:
        if args.executor != "spot-core":
            block(root, plan, "executor_not_spot_core")

        if plan.get("target") != "fixture-service":
            block(root, plan, "target_not_fixture_service")

        if plan.get("risk_class") != "low":
            block(root, plan, "risk_class_not_low")

        if plan.get("approval_state") != "approved":
            block(root, plan, "approval_required")

        if plan.get("execution_allowed") is not True:
            block(root, plan, "execution_not_allowed")

        if plan.get("backup_verified") is not True:
            block(root, plan, "backup_not_verified")

        if plan.get("rollback_defined") is not True:
            block(root, plan, "rollback_not_defined")

        if plan.get("validation_defined") is not True:
            block(root, plan, "validation_not_defined")

        if plan.get("action") not in ALLOWED_FIXTURE_ACTION_MAP:
            block(root, plan, "action_not_allowed")

        validate_lease(lease)

        execution_id = make_execution_id(plan)
        replay_path = root / "replay-guard.json"
        replay = load_json(replay_path, {"execution_ids": []})

        if execution_id in replay["execution_ids"]:
            block(root, plan, "replayed_execution_identity")

        orch = Path("watch/phase6/spot-fixture-service-orchestrator.py")
        fixture_action = ALLOWED_FIXTURE_ACTION_MAP[plan["action"]]

        p = subprocess.run([
            sys.executable,
            str(orch),
            "action",
            "--root",
            str(root / "fixture"),
            "--target",
            "fixture-service",
            "--action",
            fixture_action,
            "--lease-file",
            str(Path(args.lease_file)),
            "--nonce",
            execution_id,
        ], text=True, capture_output=True)

        if p.returncode != 0:
            block(root, plan, "fixture_execution_failed")

        receipt = json.loads(p.stdout)

        replay["execution_ids"].append(execution_id)
        write_json(replay_path, replay)

        record = {
            "schema": "phase9.execution.v1",
            "ts": int(time.time()),
            "execution_id": execution_id,
            "plan_id": plan["plan_id"],
            "target": plan["target"],
            "action": plan["action"],
            "fixture_action": fixture_action,
            "result": "executed",
            "receipt": receipt,
            "mutation_scope": "fixture_only",
        }
        record["record_hash"] = sha256_text(canonical(record))

        write_json(root / "executions" / f"{execution_id}.json", record)
        append_jsonl(root / "journals" / "phase9-executions.jsonl", record)

        print(json.dumps(record, sort_keys=True))

    except SystemExit:
        raise
    except Exception as exc:
        block(root, plan, f"unexpected_error:{type(exc).__name__}")


if __name__ == "__main__":
    main()
