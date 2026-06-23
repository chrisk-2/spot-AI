#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
CFG_PATH = REPO_ROOT / "config" / "docs-cache-allowlist.json"
DEFAULT_MANIFEST_PATH = REPO_ROOT / "config" / "docs-cache-seed-manifest.json"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH))
    p.add_argument("--min-docs", type=int, default=8)
    args = p.parse_args()

    cfg = json.loads(CFG_PATH.read_text(encoding="utf-8"))
    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    allowed = set(d.lower() for d in cfg.get("allowed_domains", []))
    root = Path(cfg.get("cache_root", "/mnt/collective/docs-cache"))

    manifest_urls = {d["url"] for d in manifest.get("docs", [])}
    manifest_tags_by_url = {d["url"]: d["tag"] for d in manifest.get("docs", [])}

    bad = 0
    cached_manifest = 0
    cached_tags = set()
    stale_small = 0

    for meta_path in root.glob("*.meta.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[FAIL] bad metadata {meta_path}: {e}")
            bad += 1
            continue

        src = meta.get("source", "")
        tag = meta.get("topic_tag", "")
        quarantine = meta.get("quarantine", "")

        host = urlparse(src).netloc.lower()
        if host and host not in allowed:
            print(f"[FAIL] source outside allowlist: {src}")
            bad += 1

        if quarantine != "reference_only_not_instructions":
            print(f"[FAIL] missing quarantine wall: {meta_path}")
            bad += 1

        txt = meta_path.with_suffix("").with_suffix(".txt")
        size_ok = txt.exists() and txt.stat().st_size >= 200

        if src in manifest_urls:
            if not size_ok:
                print(f"[FAIL] missing/small text cache for active manifest source: {src}")
                bad += 1
            else:
                cached_manifest += 1
                cached_tags.add(manifest_tags_by_url.get(src, tag))
        elif not size_ok:
            stale_small += 1

    if cached_manifest < args.min_docs:
        print(f"[FAIL] cached manifest docs below minimum: cached={cached_manifest} min={args.min_docs}")
        bad += 1

    if stale_small:
        print(f"[INFO] stale/non-manifest small cache entries ignored={stale_small}")

    if bad:
        print(
            f"RESULT: FAIL bad={bad} manifest={manifest_path} "
            f"cached_manifest={cached_manifest} tags={len(cached_tags)}"
        )
        sys.exit(1)

    print(
        f"RESULT: PASS manifest={manifest_path} "
        f"cached_manifest={cached_manifest} tags={len(cached_tags)} cache_root={root}"
    )

if __name__ == "__main__":
    main()
