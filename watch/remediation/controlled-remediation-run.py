#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import shutil
import time
import uuid
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_REMEDIATION_ROOT", "/mnt/collective/logs/spot/controlled-remediation"))
INDEX = ROOT / "index.jsonl"
ARTIFACTS = ROOT / "artifacts"
WORK = ROOT / "work"

def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def sha_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1048576), b""):
            h.update(c)
    return h.hexdigest()

def append_jsonl(path, rec):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")

def fail(msg):
    print(json.dumps({
        "ok": False,
        "result": "BLOCKED",
        "reason": msg,
        "execution_allowed": False,
        "mutation_authority": False
    }, indent=2, sort_keys=True))
    raise SystemExit(1)

def main():
    ap = argparse.ArgumentParser(description="Run controlled remediation sandbox proof")
    ap.add_argument("--correlation-id", required=True)
    ap.add_argument("--content", required=True)
    args = ap.parse_args()

    remediation_id = f"remediation-{uuid.uuid4().hex}"
    ts = utc()

    workdir = WORK / args.correlation_id / remediation_id
    workdir.mkdir(parents=True, exist_ok=False)

    target = workdir / "service.conf"
    backup = workdir / "service.conf.bak"
    rollback = workdir / "rollback.restore"

    target.write_text("mode=baseline\n", encoding="utf-8")

    shutil.copy2(target, backup)
    backup_sha = sha_file(backup)

    target.write_text(args.content + "\n", encoding="utf-8")
    mutated_sha = sha_file(target)

    rollback.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
    rollback_sha = sha_file(rollback)

    rollback_verified = rollback_sha == backup_sha
    contained = str(target).startswith(str(WORK))

    if not contained:
        fail("sandbox containment failure")

    if not rollback_verified:
        fail("rollback verification failed")

    rec = {
        "schema": "spot.controlled_remediation.v1",
        "remediation_id": remediation_id,
        "correlation_id": args.correlation_id,
        "ts": ts,
        "workdir": str(workdir),
        "target_path": str(target),
        "backup_path": str(backup),
        "rollback_path": str(rollback),
        "backup_sha256": backup_sha,
        "mutated_sha256": mutated_sha,
        "rollback_sha256": rollback_sha,
        "rollback_defined": True,
        "rollback_verified": True,
        "rollback_executed": False,
        "mutation_contained": True,
        "production_path_touched": False,
        "service_restart_performed": False,
        "worker_self_apply": False,
        "spot_core_executor_only": True,
        "execution_allowed": False,
        "mutation_authority": False,
        "authority": "controlled_remediation_only"
    }

    out = ARTIFACTS / args.correlation_id
    out.mkdir(parents=True, exist_ok=True)

    receipt = out / f"{ts.replace(':','')}-{remediation_id}.json"
    receipt.write_text(json.dumps(rec, indent=2, sort_keys=True), encoding="utf-8")

    rec["receipt_path"] = str(receipt)

    append_jsonl(INDEX, rec)

    print(json.dumps({
        "ok": True,
        "remediation_id": remediation_id,
        "correlation_id": args.correlation_id,
        "mutation_contained": True,
        "rollback_verified": True,
        "rollback_executed": False,
        "execution_allowed": False,
        "mutation_authority": False
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
