#!/usr/bin/env python3
import argparse
import json
import subprocess
import hashlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()

def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def run_cmd(cmd, timeout):
    try:
        r = subprocess.run(
            cmd,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout
        )
        return {
            "command": cmd,
            "returncode": r.returncode,
            "stdout_tail": r.stdout[-4000:],
            "stderr_tail": r.stderr[-4000:],
            "passed": r.returncode == 0,
            "timed_out": False
        }
    except subprocess.TimeoutExpired as e:
        return {
            "command": cmd,
            "returncode": None,
            "stdout_tail": (e.stdout or "")[-4000:] if isinstance(e.stdout, str) else "",
            "stderr_tail": (e.stderr or "")[-4000:] if isinstance(e.stderr, str) else "",
            "passed": False,
            "timed_out": True
        }

def main():
    ap = argparse.ArgumentParser(description="Run patch-bundle validators without mutation.")
    ap.add_argument("--patch-bundle", required=True)
    ap.add_argument("--apply-id", required=True)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--out-dir", default="watch/apply/validator-runs")
    args = ap.parse_args()

    patch = json.loads(Path(args.patch_bundle).read_text())
    validations = patch.get("validation", [])

    run_id_material = json.dumps({
        "patch_bundle_id": patch["patch_bundle_id"],
        "apply_id": args.apply_id,
        "validation": validations
    }, sort_keys=True)

    validation_run_id = f"VAL-{patch['request_id']}-{sha256_text(run_id_material)[:12]}"

    results = []
    for cmd in validations:
        results.append(run_cmd(cmd, args.timeout))

    passed = all(r["passed"] for r in results) if results else False

    record = {
        "schema_version": "1.0",
        "created_utc": utc_now(),
        "request_id": patch["request_id"],
        "patch_bundle_id": patch["patch_bundle_id"],
        "apply_id": args.apply_id,
        "validation_run_id": validation_run_id,
        "validation_count": len(results),
        "passed": passed,
        "mutation_performed": False,
        "execution_performed": False,
        "results": results
    }

    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{validation_run_id}.json"
    out.write_text(json.dumps(record, indent=2) + "\n")

    print(out)
    if passed:
        print("[PASS] validators passed")
    else:
        print("[FAIL] validators failed")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
