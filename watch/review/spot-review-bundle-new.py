#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()

def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def main():
    ap = argparse.ArgumentParser(description="Create a structured W-5 review bundle from a patch bundle.")
    ap.add_argument("--patch-bundle", required=True)
    ap.add_argument("--out-dir", default="watch/review/bundles")
    args = ap.parse_args()

    pb_path = Path(args.patch_bundle)
    patch = json.loads(pb_path.read_text())

    review_bundle_id = f"RB-{patch['patch_bundle_id']}"
    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    review = {
        "schema_version": "1.0",
        "review_bundle_id": review_bundle_id,
        "created_utc": utc_now(),
        "reviewer": "spot-worker-05",
        "review_type": "structured_diff_review",
        "patch_bundle": patch,
        "required_verdict_schema": {
            "verdict": "PASS|FIX|NO",
            "execution_allowed": False,
            "confidence": "low|medium|high",
            "intent_match": "pass|fix|fail",
            "code_match": "pass|fix|fail|not_applicable",
            "policy_match": "pass|fix|fail",
            "phase_match": "pass|fix|fail",
            "backup_required": True,
            "backup_verified": False,
            "rollback_defined": True,
            "validation_defined": True,
            "required_fixes": [],
            "blocking_findings": [],
            "notes": ""
        },
        "hard_rules": [
            "W-5 review PASS does not authorize execution by itself.",
            "Spot Core must verify backup binding before apply.",
            "Spot Core must verify rollback before apply.",
            "Spot Core must verify replay protection before apply.",
            "Codex and workers cannot apply patches."
        ]
    }

    out = out_dir / f"{review_bundle_id}.json"
    out.write_text(json.dumps(review, indent=2) + "\n")
    print(out)

if __name__ == "__main__":
    main()
