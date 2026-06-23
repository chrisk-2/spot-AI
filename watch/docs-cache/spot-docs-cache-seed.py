#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "config" / "docs-cache-seed-manifest.json"
FETCHER = REPO_ROOT / "watch" / "docs-cache" / "spot-docs-cache.py"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    p.add_argument("--continue-on-error", action="store_true")
    args = p.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    docs = manifest.get("docs", [])

    ok = 0
    fail = 0

    for item in docs:
        tag = item["tag"]
        url = item["url"]
        cmd = [sys.executable, str(FETCHER), "--fetch-url", url, "--tag", tag]
        print(f"[FETCH] {tag} {url}", flush=True)

        proc = subprocess.run(cmd, text=True, capture_output=True, cwd=str(REPO_ROOT))
        if proc.returncode == 0:
            ok += 1
            print(proc.stdout.strip())
        else:
            fail += 1
            print(f"[FAIL] {tag} {url}", file=sys.stderr)
            print(proc.stderr.strip() or proc.stdout.strip(), file=sys.stderr)
            if not args.continue_on_error:
                break

    print(f"RESULT: {'PASS' if ok else 'FAIL'} fetched={ok} failed={fail} total={len(docs)}")
    if not ok:
        raise SystemExit(1)
    if fail and not args.continue_on_error:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
