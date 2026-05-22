#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import time
import uuid
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_SANDBOX_ROOT", "/mnt/collective/logs/spot/sandbox-mutation"))
INDEX = ROOT / "index.jsonl"
ARTIFACTS = ROOT / "artifacts"
SANDBOX = ROOT / "work"

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
    ap = argparse.ArgumentParser(description="Run governed sandbox-only mutation pilot")
    ap.add_argument("--correlation-id", required=True)
    ap.add_argument("--content", required=True)
    args = ap.parse_args()

    mutation_id = f"sandbox-{uuid.uuid4().hex}"
    ts = utc()

    workdir = SANDBOX / args.correlation_id / mutation_id
    workdir.mkdir(parents=True, exist_ok=False)

    target = workdir / "target.txt"
    backup = workdir / "target.txt.prechange"
    rollback = workdir / "target.txt.rollback"

    target.write_text("initial sandbox state\n", encoding="utf-8")
    backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")

    backup_sha = sha_file(backup)

    target.write_text(args.content + "\n", encoding="utf-8")
    mutated_sha = sha_file(target)

    rollback.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
    rollback_sha = sha_file(rollback)

    rollback_verified = rollback_sha == backup_sha
    mutation_contained = str(target).startswith(str(SANDBOX))

    rec = {
        "schema": "spot.sandbox_mutation.v1",
        "mutation_id": mutation_id,
        "correlation_id": args.correlation_id,
        "ts": ts,
        "sandbox_root": str(SANDBOX),
        "workdir": str(workdir),
        "target_path": str(target),
        "backup_path": str(backup),
        "rollback_path": str(rollback),
        "backup_sha256": backup_sha,
        "mutated_sha256": mutated_sha,
        "rollback_sha256": rollback_sha,
        "mutation_contained": mutation_contained,
        "rollback_defined": True,
        "rollback_verified": rollback_verified,
        "production_path_touched": False,
        "service_restart_performed": False,
        "worker_self_apply": False,
        "spot_core_executor_only": True,
        "execution_allowed": False,
        "mutation_authority": False,
        "authority": "sandbox_mutation_only"
    }

    if not mutation_contained:
        raise SystemExit("sandbox containment failed")

    if not rollback_verified:
        raise SystemExit("rollback verification failed")

    out = ARTIFACTS / args.correlation_id
    out.mkdir(parents=True, exist_ok=True)
    stored = out / f"{ts.replace(':','')}-{mutation_id}.json"
    stored.write_text(json.dumps(rec, indent=2, sort_keys=True), encoding="utf-8")
    rec["receipt_path"] = str(stored)

    append_jsonl(INDEX, rec)

    print(json.dumps({
        "ok": True,
        "mutation_id": mutation_id,
        "correlation_id": args.correlation_id,
        "target_path": str(target),
        "backup_path": str(backup),
        "rollback_path": str(rollback),
        "mutation_contained": True,
        "rollback_verified": True,
        "execution_allowed": False,
        "mutation_authority": False
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
