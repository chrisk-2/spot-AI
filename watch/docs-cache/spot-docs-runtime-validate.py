#!/usr/bin/env python3
import json
import subprocess
import sys

payload = {
    "message": "Use cached docs: summarize Home Assistant MQTT and Linux systemd. Do not propose actions.",
    "role": "general",
    "mode": "advisory",
}

proc = subprocess.run(
    [
        "curl",
        "-fsS",
        "-H",
        "Content-Type: application/json",
        "-d",
        json.dumps(payload),
        "http://127.0.0.1:8787/chat",
    ],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    timeout=300,
)

if proc.returncode != 0:
    print(proc.stderr)
    print("RESULT: FAIL chat request failed")
    sys.exit(1)

try:
    data = json.loads(proc.stdout)
except Exception as exc:
    print(proc.stdout[:1000])
    print(f"RESULT: FAIL bad json: {exc}")
    sys.exit(1)

raw = data.get("raw") or {}
ok = data.get("ok") is True
docs_ok = raw.get("docs_cache_context") is True
chars = int(raw.get("docs_cache_context_chars") or 0)

if not ok:
    print(json.dumps(data, indent=2))
    print("RESULT: FAIL chat returned ok=false")
    sys.exit(1)

if not docs_ok or chars <= 0:
    print(json.dumps(raw, indent=2))
    print("RESULT: FAIL docs cache not injected into /chat")
    sys.exit(1)

print(f"RESULT: PASS docs_cache_context=true chars={chars}")
