#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


FORBIDDEN_ACTIONS = {
    "restart-production-service",
    "modify-firewall",
    "modify-routing",
    "modify-dns",
    "modify-dhcp",
    "apply-config",
    "execute-shell",
    "rollback-now",
}

ALLOWED_ACTIONS = {
    "propose-service-restart",
    "propose-config-review",
    "propose-health-check",
    "propose-container-redeploy",
    "propose-log-review",
}

RISK_MAP = {
    "propose-health-check": "low",
    "propose-log-review": "low",
    "propose-service-restart": "medium",
    "propose-container-redeploy": "medium",
    "propose-config-review": "medium",
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


def make_plan_id(target: str, action: str, nonce: str) -> str:
    return "proposal-" + sha256_text(
        canonical({
            "target": target,
            "action": action,
            "nonce": nonce,
        })
    )[:24]


def classify(action: str) -> str:
    return RISK_MAP.get(action, "forbidden")


def build_plan(
    target: str,
    action: str,
    nonce: str,
    observation: dict[str, Any],
) -> dict[str, Any]:

    if action in FORBIDDEN_ACTIONS:
        raise SystemExit("blocked: forbidden remediation action")

    if action not in ALLOWED_ACTIONS:
        raise SystemExit("blocked: unknown remediation action")

    risk = classify(action)

    plan = {
        "schema": "phase8.dryrun.plan.v1",
        "plan_id": make_plan_id(target, action, nonce),
        "target": target,
        "action": action,
        "risk_class": risk,
        "approval_required": True,
        "execution_allowed": False,
        "mutation_scope": "proposal_only",
        "rollback_required": True,
        "backup_required": True,
        "validation_required": True,
        "rollback_plan": {
            "strategy": "predefined_required_before_execution",
            "status": "not_executed",
        },
        "backup_plan": {
            "strategy": "verified_backup_required_before_execution",
            "status": "not_executed",
        },
        "validation_plan": {
            "strategy": "post_change_validation_required",
            "status": "not_executed",
        },
        "observation_summary": observation,
        "execution_state": "proposal_only",
        "ts": int(time.time()),
    }

    plan["proposal_hash"] = sha256_text(canonical(plan))

    return plan


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 8 dry-run remediation planner"
    )

    parser.add_argument("--root", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--observation-file", required=True)

    args = parser.parse_args()

    root = Path(args.root)

    observation = load_json(
        Path(args.observation_file),
        {},
    )

    plan = build_plan(
        target=args.target,
        action=args.action,
        nonce=args.nonce,
        observation=observation,
    )

    out = root / "plans" / f"{plan['plan_id']}.json"
    journal = root / "journals" / "phase8-remediation-plans.jsonl"

    write_json(out, plan)
    append_jsonl(journal, plan)

    print(json.dumps(plan, sort_keys=True))


if __name__ == "__main__":
    main()
