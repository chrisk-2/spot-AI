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


def block(root: Path, chain: dict[str, Any], reason: str) -> None:
    record = {
        "schema": "phase11.chain.v1",
        "ts": int(time.time()),
        "chain_id": chain.get("chain_id", "unknown"),
        "target": chain.get("target", "unknown"),
        "result": "blocked",
        "block_reason": reason,
        "mutation_scope": "none",
    }
    record["record_hash"] = sha256_text(canonical(record))
    append_jsonl(root / "journals" / "phase11-denied-chains.jsonl", record)
    raise SystemExit(f"blocked: {reason}")


def chain_execution_id(chain: dict[str, Any]) -> str:
    return "chain-exec-" + sha256_text(canonical({
        "chain_id": chain.get("chain_id"),
        "target": chain.get("target"),
        "nonce": chain.get("nonce"),
    }))[:24]


def validate_chain(chain: dict[str, Any]) -> None:
    if chain.get("owner") != "spot-core":
        raise ValueError("owner_not_spot_core")
    if chain.get("target") != "fixture-service":
        raise ValueError("target_not_fixture_service")
    if chain.get("risk_class") != "low":
        raise ValueError("risk_class_not_low")
    if chain.get("approval_state") != "approved":
        raise ValueError("approval_required")
    if chain.get("backup_verified") is not True:
        raise ValueError("backup_not_verified")
    if chain.get("rollback_verified") is not True:
        raise ValueError("rollback_not_verified")
    if chain.get("validation_defined") is not True:
        raise ValueError("validation_not_defined")


def validate_lease(lease: dict[str, Any]) -> None:
    if lease.get("owner") != "spot-core":
        raise ValueError("lease_owner_not_spot_core")
    if int(lease.get("expires_at", 0)) <= int(time.time()):
        raise ValueError("lease_expired")


def run_cmd(cmd: list[str]) -> dict[str, Any]:
    p = subprocess.run(cmd, text=True, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return json.loads(p.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 11 supervised chain orchestrator")
    parser.add_argument("--root", required=True)
    parser.add_argument("--chain-file", required=True)
    parser.add_argument("--lease-file", required=True)
    parser.add_argument("--force-verify-fail", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    chain = load_json(Path(args.chain_file), {})
    lease = load_json(Path(args.lease_file), {})

    try:
        try:
            validate_chain(chain)
        except Exception as exc:
            block(root, chain, str(exc))

        try:
            validate_lease(lease)
        except Exception as exc:
            block(root, chain, str(exc))

        eid = chain_execution_id(chain)
        replay_path = root / "replay-guard.json"
        replay = load_json(replay_path, {"execution_ids": []})

        if eid in replay["execution_ids"]:
            block(root, chain, "replayed_chain_identity")

        observation = {
            "schema": "phase11.observation.v1",
            "target": chain["target"],
            "status": "observe_only",
            "incident_candidates": [
                {
                    "service": "fixture-service",
                    "severity": "low",
                    "recommendation": "supervised_chain_only",
                }
            ],
            "mutation_scope": "none",
        }

        plan = {
            "schema": "phase11.plan.v1",
            "target": chain["target"],
            "risk_class": "low",
            "approval_state": "approved",
            "execution_allowed": True,
            "backup_verified": True,
            "rollback_verified": True,
            "validation_defined": True,
            "mutation_scope": "proposal_only",
        }

        orch = Path("watch/phase6/spot-fixture-service-orchestrator.py")
        action = "restart"

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
            str(Path(args.lease_file)),
            "--nonce",
            eid,
        ]

        if args.force_verify_fail:
            cmd.append("--force-verify-fail")

        receipt = run_cmd(cmd)
        result = "rolled_back" if receipt["result"] == "rolled_back" else "completed"

        replay["execution_ids"].append(eid)
        write_json(replay_path, replay)

        record = {
            "schema": "phase11.chain.v1",
            "ts": int(time.time()),
            "chain_execution_id": eid,
            "chain_id": chain["chain_id"],
            "target": chain["target"],
            "result": result,
            "steps": {
                "observation": observation,
                "planning": plan,
                "execution": receipt,
            },
            "mutation_scope": "fixture_only",
        }
        record["record_hash"] = sha256_text(canonical(record))

        write_json(root / "receipts" / f"{eid}.json", record)
        append_jsonl(root / "journals" / "phase11-chains.jsonl", record)

        print(json.dumps(record, sort_keys=True))

    except SystemExit:
        raise
    except Exception as exc:
        block(root, chain, f"unexpected_error:{type(exc).__name__}")


if __name__ == "__main__":
    main()
