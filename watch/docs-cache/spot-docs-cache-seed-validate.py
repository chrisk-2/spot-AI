#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
CFG_PATH = REPO_ROOT / "config" / "docs-cache-allowlist.json"
MANIFEST_PATH = REPO_ROOT / "config" / "docs-cache-seed-manifest.json"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--min-docs", type=int, default=8)
    args = p.parse_args()

    cfg = json.loads(CFG_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    allowed = set(d.lower() for d in cfg.get("allowed_domains", []))
    root = Path(cfg.get("cache_root", "/mnt/collective/docs-cache"))

    bad = 0
    metas = list(root.glob("*.meta.json"))

    manifest_urls = {d["url"] for d in manifest.get("docs", [])}
    cached_manifest = 0
    tags = set()

    for meta_path in metas:
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[FAIL] bad metadata {meta_path}: {e}")
            bad += 1
            continue

        src = meta.get("source", "")
        tag = meta.get("topic_tag", "")
        quarantine = meta.get("quarantine", "")

        if src in manifest_urls:
            cached_manifest += 1
            tags.add(tag)

        host = urlparse(src).netloc.lower()
        if host and host not in allowed:
            print(f"[FAIL] source outside allowlist: {src}")
            bad += 1

        if quarantine != "reference_only_not_instructions":
            print(f"[FAIL] missing quarantine wall: {meta_path}")
            bad += 1

        txt = meta_path.with_suffix("").with_suffix(".txt")
        if not txt.exists() or txt.stat().st_size < 200:
            print(f"[FAIL] missing/small text cache for {meta_path}")
            bad += 1

    if cached_manifest < args.min_docs:
        print(f"[FAIL] cached manifest docs below minimum: cached={cached_manifest} min={args.min_docs}")
        bad += 1

    if bad:
        print(f"RESULT: FAIL bad={bad} cached_manifest={cached_manifest} tags={len(tags)}")
        sys.exit(1)

    print(f"RESULT: PASS cached_manifest={cached_manifest} tags={len(tags)} cache_root={root}")

if __name__ == "__main__":
    main()
