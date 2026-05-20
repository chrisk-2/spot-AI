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


ACTION_MAP = {
    "remediate-fixture-start": "start",
    "remediate-fixture-stop": "stop",
    "remediate-fixture-restart": "restart",
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
        "schema": "phase10.remediation.v1",
        "ts": int(time.time()),
        "plan_id": plan.get("plan_id", "unknown"),
        "target": plan.get("target", "unknown"),
        "action": plan.get("action", "unknown"),
        "result": "blocked",
        "block_reason": reason,
        "mutation_scope": "none",
    }
    record["record_hash"] = sha256_text(canonical(record))
    append_jsonl(root / "journals" / "phase10-denied-remediations.jsonl", record)
    raise SystemExit(f"blocked: {reason}")


def execution_id(plan: dict[str, Any]) -> str:
    return "phase10-exec-" + sha256_text(canonical({
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


def validate_rollback_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema") != "phase10.rollback_manifest.v1":
        raise ValueError("invalid rollback manifest schema")
    if manifest.get("target") != "fixture-service":
        raise ValueError("rollback target must be fixture-service")
    if manifest.get("rollback_action") != "rollback":
        raise ValueError("rollback action must be rollback")
    if manifest.get("verified") is not True:
        raise ValueError("rollback manifest not verified")


def call_orch(root: Path, action: str, lease_file: Path, nonce: str, force_fail: bool = False) -> dict[str, Any]:
    orch = Path("watch/phase6/spot-fixture-service-orchestrator.py")
    cmd = [
        sys.executable,
        str(orch),
        "action",
        "--root",
        str(root / "fixture"),
        "--target",
        "fixture-service",
        "--action",
        action,
        "--lease-file",
        str(lease_file),
        "--nonce",
        nonce,
    ]
    if force_fail:
        cmd.append("--force-verify-fail")

    p = subprocess.run(cmd, text=True, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return json.loads(p.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 10 rollback-integrated fixture remediation wrapper")
    parser.add_argument("--root", required=True)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--lease-file", required=True)
    parser.add_argument("--rollback-manifest", required=True)
    parser.add_argument("--executor", default="spot-core")
    parser.add_argument("--force-verify-fail", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    plan = load_json(Path(args.plan_file), {})
    lease = load_json(Path(args.lease_file), {})
    manifest = load_json(Path(args.rollback_manifest), {})

    try:
        if args.executor != "spot-core":
            block(root, plan, "executor_not_spot_core")
        if plan.get("target") != "fixture-service":
            block(root, plan, "target_not_fixture_service")
        if plan.get("risk_class") != "low":
            block(root, plan, "risk_class_not_low")
        if plan.get("approval_state") != "approved":
            block(root, plan, "approval_required")
        if plan.get("backup_verified") is not True:
            block(root, plan, "backup_not_verified")
        if plan.get("validation_defined") is not True:
            block(root, plan, "validation_not_defined")
        if plan.get("action") not in ACTION_MAP:
            block(root, plan, "action_not_allowed")

        try:
            validate_rollback_manifest(manifest)
        except Exception:
            block(root, plan, "rollback_manifest_invalid")

        try:
            validate_lease(lease)
        except Exception:
            block(root, plan, "lease_invalid")

        eid = execution_id(plan)
        replay_path = root / "replay-guard.json"
        replay = load_json(replay_path, {"execution_ids": []})
        if eid in replay["execution_ids"]:
            block(root, plan, "replayed_execution_identity")

        receipt = call_orch(
            root=root,
            action=ACTION_MAP[plan["action"]],
            lease_file=Path(args.lease_file),
            nonce=eid,
            force_fail=args.force_verify_fail,
        )

        rollback_receipt = None
        result = "remediated"

        if receipt["result"] == "rolled_back":
            rollback_receipt = {
                "schema": "phase10.rollback_receipt.v1",
                "ts": int(time.time()),
                "plan_id": plan["plan_id"],
                "execution_id": eid,
                "rollback_manifest_id": manifest["rollback_manifest_id"],
                "rollback_result": "verified",
                "after_state": receipt["after_state"],
                "mutation_scope": "fixture_only",
            }
            rollback_receipt["record_hash"] = sha256_text(canonical(rollback_receipt))
            write_json(root / "rollbacks" / f"{eid}.json", rollback_receipt)
            append_jsonl(root / "journals" / "phase10-rollbacks.jsonl", rollback_receipt)
            result = "rolled_back"

        replay["execution_ids"].append(eid)
        write_json(replay_path, replay)

        record = {
            "schema": "phase10.remediation.v1",
            "ts": int(time.time()),
            "execution_id": eid,
            "plan_id": plan["plan_id"],
            "target": plan["target"],
            "action": plan["action"],
            "result": result,
            "receipt": receipt,
            "rollback_receipt": rollback_receipt,
            "mutation_scope": "fixture_only",
        }
        record["record_hash"] = sha256_text(canonical(record))

        write_json(root / "executions" / f"{eid}.json", record)
        append_jsonl(root / "journals" / "phase10-remediations.jsonl", record)

        print(json.dumps(record, sort_keys=True))

    except SystemExit:
        raise
    except Exception as exc:
        block(root, plan, f"unexpected_error:{type(exc).__name__}")


if __name__ == "__main__":
    main()
