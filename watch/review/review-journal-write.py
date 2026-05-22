#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


REQUIRED_TOP_LEVEL = [
    "ts",
    "request_id",
    "provider",
    "reviewer",
    "model",
    "review_type",
    "verdict",
    "execution_allowed",
    "result_blocked",
    "authority",
    "confidence",
    "review_bundle_sha256",
    "raw_response_sha256",
    "journal_path",
]


def sha256_json(obj) -> str:
    data = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def atomic_write_new(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SystemExit(f"[FAIL] refusing to overwrite existing journal: {path}")

    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with tmp.open("x", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())

    os.rename(tmp, path)


def append_index(index_path: Path, record: dict) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    fd = os.open(index_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def post_json(url: str, payload: dict, timeout: int) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"[FAIL] HTTP {e.code}: {detail}") from e
    except Exception as e:
        raise SystemExit(f"[FAIL] review request failed: {type(e).__name__}: {e}") from e


def main() -> int:
    ap = argparse.ArgumentParser(description="Write immutable Spot review journal artifact.")
    ap.add_argument("--base-url", default=os.environ.get("SPOT_BASE_URL", "http://127.0.0.1:8787"))
    ap.add_argument("--journal-root", default=os.environ.get("SPOT_REVIEW_JOURNAL_ROOT", "/mnt/collective/logs/spot/reviews"))
    ap.add_argument("--request-id", default="")
    ap.add_argument("--review-type", default="policy_review")
    ap.add_argument("--prompt", default="Review proposal only: confirm policy gate blocks execution authority.")
    ap.add_argument("--timeout", type=int, default=90)
    args = ap.parse_args()

    ts_epoch = int(time.time())
    ts_utc = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(ts_epoch))
    request_id = args.request_id.strip() or f"review-{ts_utc}"

    bundle = {
        "request_id": request_id,
        "review_type": args.review_type,
        "prompt": args.prompt,
        "policy": {
            "execution_authority": "proposal_review_only",
            "spot_core_only_executor": True,
            "no_backup_no_change": True,
            "no_review_no_apply": True,
            "no_rollback_no_execution": True,
        },
    }

    response = post_json(
        f"{args.base_url.rstrip('/')}/review/local",
        {"prompt": args.prompt, "review_type": args.review_type},
        args.timeout,
    )

    raw_response_sha = sha256_json(response)
    bundle_sha = sha256_json(bundle)

    root = Path(args.journal_root)
    journal_path = root / f"{ts_utc}-{request_id}.json"
    index_path = root / "index.jsonl"

    journal = {
        "ts": ts_epoch,
        "ts_utc": ts_utc,
        "request_id": request_id,
        "provider": response.get("provider", "local"),
        "reviewer": response.get("reviewer"),
        "model": response.get("model"),
        "review_type": response.get("review_type", args.review_type),
        "verdict": response.get("verdict"),
        "execution_allowed": response.get("execution_allowed"),
        "result_blocked": response.get("result_blocked"),
        "authority": response.get("authority"),
        "confidence": response.get("confidence"),
        "review_bundle_sha256": bundle_sha,
        "raw_response_sha256": raw_response_sha,
        "review_bundle": bundle,
        "raw_response": response,
        "journal_path": str(journal_path),
    }

    missing = [k for k in REQUIRED_TOP_LEVEL if k not in journal]
    if missing:
        raise SystemExit(f"[FAIL] internal journal schema missing keys: {missing}")

    atomic_write_new(journal_path, journal)

    index_record = {k: journal[k] for k in REQUIRED_TOP_LEVEL}
    append_index(index_path, index_record)

    print(json.dumps({"ok": True, "journal_path": str(journal_path), "index_path": str(index_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
