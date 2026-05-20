#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

CASES = {
    "sandbox_mutation_success",
    "sandbox_verification_failed_rollback",
    "sandbox_backup_missing_blocked",
    "sandbox_rollback_missing_blocked",
    "sandbox_replay_blocked",
    "sandbox_target_escape_blocked",
}

RUN_ROOT = Path("watch/phase5/runs")


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def safe_target(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def write_receipt(out_dir: Path, doc: dict) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{doc['receipt_id']}.json"
    out.write_text(json.dumps(doc, indent=2) + "\n")
    return out


def build_doc(args: argparse.Namespace) -> dict:
    material = "|".join([args.request_id, args.case, args.target, "phase5-sandbox-mutation"])
    digest = sha256_text(material)[:12]

    out_dir = Path(args.out_dir)
    sandbox_root = out_dir / "sandbox"
    backup_root = out_dir / "backups"
    target = Path(args.target)

    if not target.is_absolute():
        target = sandbox_root / target

    receipt_id = f"RECEIPT-{digest}"
    execution_id = f"EXEC-{digest}"
    lease_id = f"LEASE-{digest}"
    envelope_id = f"ENV-{digest}"
    replay_guard = sha256_text(f"replay|{material}")[:24]

    common = {
        "receipt_id": receipt_id,
        "created_at": utc_now(),
        "request_id": args.request_id,
        "execution_id": execution_id,
        "lease_id": lease_id,
        "envelope_id": envelope_id,
        "replay_guard": replay_guard,
        "phase": "5",
        "executor": "spot-core",
        "action_type": "sandbox_mutation",
        "risk_class": "sandbox",
        "case": args.case,
        "target": str(target),
        "sandbox_root": str(sandbox_root),
        "backup_path": None,
        "rollback_path": None,
        "blocked_reason": None,
        "backup_created": False,
        "backup_verified": False,
        "rollback_defined": False,
        "mutation_performed": False,
        "verification_performed": False,
        "verification_passed": False,
        "rollback_performed": False,
        "rollback_verified": False,
        "replay_guard_checked": True,
        "replay_detected": False,
        "target_escape_detected": False,
        "git_apply_performed": False,
        "service_restart_performed": False,
        "worker_execution_performed": False,
        "final_outcome": "blocked",
    }

    sandbox_root.mkdir(parents=True, exist_ok=True)
    backup_root.mkdir(parents=True, exist_ok=True)

    if args.case == "sandbox_target_escape_blocked":
        target = Path("/tmp/spot-phase5-forbidden-target.txt")
        common["target"] = str(target)

    if not safe_target(target, sandbox_root):
        common["target_escape_detected"] = True
        common["blocked_reason"] = "target_escape"
        return common

    target.parent.mkdir(parents=True, exist_ok=True)
    original_content = "phase5-original\n"
    mutated_content = "phase5-mutated\n"

    target.write_text(original_content)
    original_hash = sha256_file(target)

    if args.case == "sandbox_backup_missing_blocked":
        common["blocked_reason"] = "backup_missing"
        return common

    backup_path = backup_root / f"{target.name}.{digest}.bak"
    shutil.copy2(target, backup_path)
    common["backup_path"] = str(backup_path)
    common["backup_created"] = True
    common["backup_verified"] = backup_path.exists() and sha256_file(backup_path) == original_hash

    if args.case == "sandbox_rollback_missing_blocked":
        common["blocked_reason"] = "rollback_missing"
        return common

    common["rollback_path"] = str(backup_path)
    common["rollback_defined"] = True

    if args.case == "sandbox_replay_blocked":
        common["blocked_reason"] = "replay_detected"
        common["replay_detected"] = True
        return common

    target.write_text(mutated_content)
    common["mutation_performed"] = True
    common["verification_performed"] = True

    if args.case == "sandbox_verification_failed_rollback":
        common["verification_passed"] = False
        shutil.copy2(backup_path, target)
        common["rollback_performed"] = True
        common["rollback_verified"] = sha256_file(target) == original_hash
        common["final_outcome"] = "rolled_back"
        return common

    common["verification_passed"] = target.read_text() == mutated_content
    common["final_outcome"] = "success" if common["verification_passed"] else "failed"
    return common


def main() -> None:
    ap = argparse.ArgumentParser(description="Phase 5 sandbox mutation simulator.")
    ap.add_argument("--request-id", required=True)
    ap.add_argument("--case", required=True, choices=sorted(CASES))
    ap.add_argument("--target", default="fixture.txt")
    ap.add_argument("--out-dir", default=str(RUN_ROOT))
    args = ap.parse_args()

    doc = build_doc(args)
    out = write_receipt(Path(args.out_dir), doc)
    print(out)


if __name__ == "__main__":
    main()
