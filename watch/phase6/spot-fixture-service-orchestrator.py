#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


VALID_STATES = {
    "stopped",
    "starting",
    "running",
    "degraded",
    "failed",
    "rollback_restored",
}

VALID_ACTIONS = {
    "start",
    "stop",
    "restart",
    "degrade",
    "fail",
    "rollback",
}

FORBIDDEN_TARGET_MARKERS = (
    "..",
    "/etc/",
    "/boot/",
    "/root/",
    "/home/",
    "/mnt/collective/",
    "/srv/",
    "/var/lib/",
    "/usr/",
)


@dataclass(frozen=True)
class Lease:
    lease_id: str
    owner: str
    issued_at: int
    expires_at: int


@dataclass(frozen=True)
class Receipt:
    receipt_id: str
    execution_id: str
    target: str
    action: str
    before_state: str
    after_state: str
    backup_state: str
    rollback_state: str
    lease_id: str
    result: str
    mutation_scope: str
    ts: int


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


def ensure_fixture_target(root: Path, target: str) -> Path:
    if target != "fixture-service":
        raise SystemExit("blocked: target must be fixture-service")

    for marker in FORBIDDEN_TARGET_MARKERS:
        if marker in target:
            raise SystemExit("blocked: target escape marker detected")

    target_path = (root / target).resolve()
    root_resolved = root.resolve()

    if root_resolved not in target_path.parents and target_path != root_resolved:
        raise SystemExit("blocked: target escapes phase6 sandbox")

    return target_path


def new_lease(owner: str, ttl_seconds: int) -> Lease:
    now = int(time.time())
    return Lease(
        lease_id=f"lease-{uuid.uuid4()}",
        owner=owner,
        issued_at=now,
        expires_at=now + ttl_seconds,
    )


def validate_lease(lease: Lease, now: int | None = None) -> None:
    now = int(time.time()) if now is None else now
    if lease.owner != "spot-core":
        raise SystemExit("blocked: lease owner is not spot-core")
    if lease.expires_at <= now:
        raise SystemExit("blocked: execution lease expired")


def transition(before: str, action: str) -> str:
    if before not in VALID_STATES:
        raise SystemExit(f"blocked: invalid before_state={before}")
    if action not in VALID_ACTIONS:
        raise SystemExit(f"blocked: invalid action={action}")

    if action == "start":
        return "running"
    if action == "stop":
        return "stopped"
    if action == "restart":
        return "running"
    if action == "degrade":
        return "degraded"
    if action == "fail":
        return "failed"
    if action == "rollback":
        return "rollback_restored"

    raise SystemExit("blocked: unknown action")


def verify_state(action: str, after: str) -> bool:
    if action in {"start", "restart"}:
        return after == "running"
    if action == "stop":
        return after == "stopped"
    if action == "degrade":
        return after == "degraded"
    if action == "fail":
        return False
    if action == "rollback":
        return after == "rollback_restored"
    return False


def execution_id(target: str, action: str, nonce: str) -> str:
    return sha256_text(canonical({"target": target, "action": action, "nonce": nonce}))


def run_action(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    target_path = ensure_fixture_target(root, args.target)
    target_path.mkdir(parents=True, exist_ok=True)

    state_path = target_path / "state.json"
    journal_path = root / "journals" / "phase6-fixture-service.jsonl"
    replay_path = root / "replay-guard.json"

    state = load_json(state_path, {"state": "stopped"})
    replay = load_json(replay_path, {"execution_ids": []})

    eid = execution_id(args.target, args.action, args.nonce)
    if eid in replay["execution_ids"]:
        raise SystemExit("blocked: replayed execution identity")

    lease = Lease(**load_json(Path(args.lease_file), {}))
    validate_lease(lease)

    before = state["state"]
    backup_state = before
    planned_after = transition(before, args.action)

    if args.force_verify_fail:
        verified = False
    else:
        verified = verify_state(args.action, planned_after)

    if verified:
        after = planned_after
        rollback_state = backup_state
        result = "applied"
    else:
        after = "rollback_restored"
        rollback_state = backup_state
        result = "rolled_back"

    receipt = Receipt(
        receipt_id=f"receipt-{uuid.uuid4()}",
        execution_id=eid,
        target=args.target,
        action=args.action,
        before_state=before,
        after_state=after,
        backup_state=backup_state,
        rollback_state=rollback_state,
        lease_id=lease.lease_id,
        result=result,
        mutation_scope="fixture_only",
        ts=int(time.time()),
    )

    state["state"] = after
    state["last_receipt"] = asdict(receipt)
    write_json(state_path, state)

    replay["execution_ids"].append(eid)
    write_json(replay_path, replay)

    record = asdict(receipt)
    record["record_hash"] = sha256_text(canonical(record))
    append_jsonl(journal_path, record)

    return record


def cmd_lease(args: argparse.Namespace) -> None:
    lease = new_lease(owner=args.owner, ttl_seconds=args.ttl)
    write_json(Path(args.output), asdict(lease))
    print(json.dumps(asdict(lease), sort_keys=True))


def cmd_action(args: argparse.Namespace) -> None:
    record = run_action(args)
    print(json.dumps(record, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Phase 6 fixture service orchestrator")
    sub = p.add_subparsers(required=True)

    lease = sub.add_parser("lease")
    lease.add_argument("--owner", default="spot-core")
    lease.add_argument("--ttl", type=int, default=60)
    lease.add_argument("--output", required=True)
    lease.set_defaults(func=cmd_lease)

    action = sub.add_parser("action")
    action.add_argument("--root", required=True)
    action.add_argument("--target", required=True)
    action.add_argument("--action", required=True)
    action.add_argument("--lease-file", required=True)
    action.add_argument("--nonce", required=True)
    action.add_argument("--force-verify-fail", action="store_true")
    action.set_defaults(func=cmd_action)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
