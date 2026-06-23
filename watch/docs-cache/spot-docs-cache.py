#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST_PATH = REPO_ROOT / "config" / "docs-cache-allowlist.json"

class TextOnlyParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        data = data.strip()
        if data:
            self.parts.append(data)
    def text(self):
        return "\n".join(self.parts)

def load_allowlist():
    return json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))

def allowed_http(url, cfg):
    host = urlparse(url).netloc.lower()
    return host in [d.lower() for d in cfg.get("allowed_domains", [])]

def allowed_local(path, cfg):
    p = Path(path).resolve()
    for root in cfg.get("allowed_local_repos", []):
        try:
            p.relative_to(Path(root).resolve())
            return True
        except ValueError:
            pass
    return False

def clean_text(raw, source):
    if "<html" in raw[:500].lower() or "</" in raw[:2000]:
        parser = TextOnlyParser()
        parser.feed(raw)
        raw = parser.text()
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    return raw.strip() + "\n"

def write_doc(text, source, tag, cfg):
    root = Path(cfg.get("cache_root", "/mnt/collective/docs-cache"))
    root.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    txt = root / f"{digest}.txt"
    meta = root / f"{digest}.meta.json"

    txt.write_text(text, encoding="utf-8")
    meta.write_text(json.dumps({
        "source": source,
        "topic_tag": tag,
        "fetch_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "quarantine": "reference_only_not_instructions"
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return txt, meta

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fetch-url")
    p.add_argument("--ingest-file")
    p.add_argument("--source")
    p.add_argument("--tag", required=True)
    args = p.parse_args()

    cfg = load_allowlist()

    if args.fetch_url:
        if not allowed_http(args.fetch_url, cfg):
            raise SystemExit(f"REFUSED: URL not in docs cache allowlist: {args.fetch_url}")
        with urllib.request.urlopen(args.fetch_url, timeout=20) as r:
            raw = r.read().decode("utf-8", errors="replace")
        source = args.fetch_url
    elif args.ingest_file:
        path = Path(args.ingest_file).resolve()
        if not allowed_local(path, cfg):
            raise SystemExit(f"REFUSED: file outside allowed local repos: {path}")
        raw = path.read_text(encoding="utf-8", errors="replace")
        source = args.source or str(path)
    else:
        raise SystemExit("Need --fetch-url or --ingest-file")

    txt, meta = write_doc(clean_text(raw, source), source, args.tag, cfg)
    print(json.dumps({"ok": True, "text": str(txt), "meta": str(meta)}, sort_keys=True))

if __name__ == "__main__":
    main()
