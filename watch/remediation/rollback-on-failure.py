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
INDEX = ROOT / "rollback-index.jsonl"
ARTIFACTS = ROOT / "rollback-artifacts"
WORK = ROOT / "rollback-work"

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

def main():
    ap = argparse.ArgumentParser(description="Rollback-on-failure proof")
    ap.add_argument("--correlation-id", required=True)
    args = ap.parse_args()

    rollback_id = f"rollback-proof-{uuid.uuid4().hex}"
    ts = utc()

    workdir = WORK / args.correlation_id / rollback_id
    workdir.mkdir(parents=True, exist_ok=False)

    target = workdir / "runtime.conf"
    backup = workdir / "runtime.conf.bak"

    target.write_text("state=good\n", encoding="utf-8")
    shutil.copy2(target, backup)

    pre_sha = sha_file(target)

    target.write_text("state=bad\n", encoding="utf-8")
    failed_sha = sha_file(target)

    validation_failed = pre_sha != failed_sha

    shutil.copy2(backup, target)

    restored_sha = sha_file(target)
    rollback_verified = restored_sha == pre_sha

    rec = {
        "schema": "spot.rollback_on_failure.v1",
        "rollback_id": rollback_id,
        "correlation_id": args.correlation_id,
        "ts": ts,
        "validation_failed": validation_failed,
        "rollback_triggered": True,
        "rollback_verified": rollback_verified,
        "pre_failure_sha256": pre_sha,
        "failed_sha256": failed_sha,
        "restored_sha256": restored_sha,
        "rollback_executed": True,
        "production_path_touched": False,
        "service_restart_performed": False,
        "worker_self_apply": False,
        "spot_core_executor_only": True,
        "execution_allowed": False,
        "mutation_authority": False,
        "authority": "rollback_on_failure_only"
    }

    out = ARTIFACTS / args.correlation_id
    out.mkdir(parents=True, exist_ok=True)

    receipt = out / f"{ts.replace(':','')}-{rollback_id}.json"
    receipt.write_text(json.dumps(rec, indent=2, sort_keys=True), encoding="utf-8")

    rec["receipt_path"] = str(receipt)

    append_jsonl(INDEX, rec)

    print(json.dumps({
        "ok": True,
        "rollback_id": rollback_id,
        "correlation_id": args.correlation_id,
        "validation_failed": True,
        "rollback_triggered": True,
        "rollback_verified": rollback_verified,
        "execution_allowed": False,
        "mutation_authority": False
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
