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

USER_AGENT = "Starfleet-Spot-DocsCache/1.0 (+manual-refresh; reference-only)"

class TextOnlyParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip = True

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip = False

    def handle_data(self, data):
        if self.skip:
            return
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

def clean_text(raw):
    if "<html" in raw[:1000].lower() or "</" in raw[:4000]:
        parser = TextOnlyParser()
        parser.feed(raw)
        raw = parser.text()

    raw = re.sub(r"\r\n?", "\n", raw)
    raw = re.sub(r"[ \t]+", " ", raw)
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

def fetch_url(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,text/plain,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        status = getattr(r, "status", 200)
        if status >= 400:
            raise RuntimeError(f"HTTP {status}")
        ctype = r.headers.get("content-type", "")
        raw = r.read().decode("utf-8", errors="replace")
        return raw, ctype

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
        raw, ctype = fetch_url(args.fetch_url)
        source = args.fetch_url
    elif args.ingest_file:
        path = Path(args.ingest_file).resolve()
        if not allowed_local(path, cfg):
            raise SystemExit(f"REFUSED: file outside allowed local repos: {path}")
        raw = path.read_text(encoding="utf-8", errors="replace")
        ctype = "local-file"
        source = args.source or str(path)
    else:
        raise SystemExit("Need --fetch-url or --ingest-file")

    txt, meta = write_doc(clean_text(raw), source, args.tag, cfg)
    print(json.dumps({
        "ok": True,
        "text": str(txt),
        "meta": str(meta),
        "source": source,
        "tag": args.tag,
        "content_type": ctype
    }, sort_keys=True))

if __name__ == "__main__":
    main()
