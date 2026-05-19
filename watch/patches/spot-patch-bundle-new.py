#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()

def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def sha256_file(path):
    p = ROOT / path
    if not p.exists() or not p.is_file():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser(description="Create a proposal-only Spot patch bundle.")
    ap.add_argument("--request-id", required=True)
    ap.add_argument("--intent", required=True)
    ap.add_argument("--risk-class", choices=["low", "medium", "high"], required=True)
    ap.add_argument("--target-host", default="spot-core")
    ap.add_argument("--target-repo", default="~/spot-stack")
    ap.add_argument("--target-service", default="spot-core")
    ap.add_argument("--file", action="append", default=[])
    ap.add_argument("--validation", action="append", default=[])
    ap.add_argument("--out-dir", default="watch/patches/bundles")
    args = ap.parse_args()

    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    patch_bundle_id = f"PB-{args.request_id}"
    files = []
    for f in args.file:
        files.append({
            "path": f,
            "operation": "modify",
            "sha256_before": sha256_file(f),
            "sha256_after_expected": ""
        })

    bundle = {
        "schema_version": "1.0",
        "request_id": args.request_id,
        "patch_bundle_id": patch_bundle_id,
        "phase": "3.1",
        "created_utc": utc_now(),
        "generated_by": {
            "worker": "spot-worker-03",
            "provider": "local-generator",
            "model": "none"
        },
        "target": {
            "host": args.target_host,
            "repo": args.target_repo,
            "service": args.target_service
        },
        "risk_class": args.risk_class,
        "intent": args.intent,
        "files": files,
        "diff_artifacts": [],
        "validation": args.validation,
        "rollback": {
            "required": True,
            "strategy": "restore-bound-backup",
            "commands": []
        },
        "review_required": True,
        "execution_allowed": False
    }

    out = out_dir / f"{patch_bundle_id}.json"
    out.write_text(json.dumps(bundle, indent=2) + "\n")
    print(out)

if __name__ == "__main__":
    main()
