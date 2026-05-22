#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import time
import uuid
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_GOVERNANCE_BUNDLE_ROOT", "/mnt/collective/logs/spot/governance-bundles"))
INDEX = ROOT / "index.jsonl"
ARTIFACTS = ROOT / "artifacts"

SOURCES = {
    "chain": Path(os.environ.get("SPOT_CHAIN_ROOT", "/mnt/collective/logs/spot/chains")) / "index.jsonl",
    "lease": Path(os.environ.get("SPOT_LEASE_ROOT", "/mnt/collective/logs/spot/leases")) / "index.jsonl",
    "rollback": Path(os.environ.get("SPOT_ROLLBACK_ROOT", "/mnt/collective/logs/spot/rollbacks")) / "index.jsonl",
    "receipt": Path(os.environ.get("SPOT_RECEIPT_ROOT", "/mnt/collective/logs/spot/receipts")) / "index.jsonl",
    "noop": Path(os.environ.get("SPOT_NOOP_EXEC_ROOT", "/mnt/collective/logs/spot/noop-executor")) / "index.jsonl"
}

def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def sha_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def load(path, cid):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("correlation_id") == cid:
            rows.append(rec)
    return rows

def append(path, rec):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")

def fail(msg):
    print(json.dumps({"ok": False, "reason": msg, "execution_allowed": False, "mutation_authority": False}, indent=2, sort_keys=True))
    raise SystemExit(1)

def main():
    ap = argparse.ArgumentParser(description="Write governance bundle manifest")
    ap.add_argument("--correlation-id", required=True)
    args = ap.parse_args()
    cid = args.correlation_id

    bundle_id = f"gbundle-{uuid.uuid4().hex}"
    ts = utc()

    sections = {name: load(path, cid) for name, path in SOURCES.items()}

    if not sections["chain"]:
        fail("missing chain records")
    if not sections["lease"]:
        fail("missing lease records")
    if not sections["rollback"]:
        fail("missing rollback records")
    if not sections["receipt"]:
        fail("missing receipt records")
    if not sections["noop"]:
        fail("missing noop records")

    for name, rows in sections.items():
        for rec in rows:
            if rec.get("execution_allowed") is not False:
                fail(f"{name} expands execution authority")
            if rec.get("mutation_authority") is not False:
                fail(f"{name} expands mutation authority")

    manifest = {
        "schema": "spot.governance_bundle.v1",
        "bundle_id": bundle_id,
        "ts": ts,
        "correlation_id": cid,
        "sections": sections,
        "counts": {k: len(v) for k, v in sections.items()},
        "authority": "governance_bundle_only",
        "execution_allowed": False,
        "mutation_authority": False,
        "replay_audit_ready": True
    }

    manifest_text = json.dumps(manifest, indent=2, sort_keys=True)
    digest = sha_text(manifest_text)

    out = ARTIFACTS / cid
    out.mkdir(parents=True, exist_ok=True)
    stored = out / f"{ts.replace(':','')}-{bundle_id}-{digest[:16]}.json"
    if stored.exists():
        fail(f"refusing overwrite: {stored}")
    stored.write_text(manifest_text, encoding="utf-8")

    rec = {
        "schema": "spot.governance_bundle.index.v1",
        "bundle_id": bundle_id,
        "ts": ts,
        "correlation_id": cid,
        "manifest_sha256": digest,
        "manifest_stored_path": str(stored),
        "counts": manifest["counts"],
        "authority": "governance_bundle_only",
        "execution_allowed": False,
        "mutation_authority": False,
        "replay_audit_ready": True
    }
    append(INDEX, rec)

    print(json.dumps({
        "ok": True,
        "bundle_id": bundle_id,
        "correlation_id": cid,
        "stored_path": str(stored),
        "counts": manifest["counts"],
        "execution_allowed": False,
        "mutation_authority": False,
        "replay_audit_ready": True
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
