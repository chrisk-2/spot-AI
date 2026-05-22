#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


REQUIRED = {
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
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_record(path: Path, obj: dict) -> list[str]:
    errors = []
    missing = sorted(REQUIRED - set(obj))
    if missing:
        errors.append(f"{path}: missing required keys: {missing}")

    for key in ("review_bundle_sha256", "raw_response_sha256"):
        value = obj.get(key)
        if not isinstance(value, str) or len(value) != 64:
            errors.append(f"{path}: invalid {key}")

    if obj.get("authority") == "proposal_review_only" and obj.get("execution_allowed") is not False:
        errors.append(f"{path}: proposal_review_only must have execution_allowed=false")

    if obj.get("result_blocked") is not True:
        errors.append(f"{path}: result_blocked must be true")

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate Spot review journal artifacts.")
    ap.add_argument("--journal-root", default="/mnt/collective/logs/spot/reviews")
    ap.add_argument("--min-count", type=int, default=1)
    args = ap.parse_args()

    root = Path(args.journal_root)
    index = root / "index.jsonl"

    errors = []
    files = sorted(p for p in root.glob("*.json") if p.name != "index.json")

    if len(files) < args.min_count:
        errors.append(f"{root}: expected at least {args.min_count} journal json files, found {len(files)}")

    for path in files:
        try:
            obj = load_json(path)
            errors.extend(validate_record(path, obj))
        except Exception as e:
            errors.append(f"{path}: unreadable json: {type(e).__name__}: {e}")

    if not index.exists():
        errors.append(f"{index}: missing index.jsonl")
    else:
        with index.open("r", encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    errors.extend(validate_record(Path(f"{index}:{n}"), obj))
                except Exception as e:
                    errors.append(f"{index}:{n}: invalid jsonl: {type(e).__name__}: {e}")

    if errors:
        for e in errors:
            print(f"[FAIL] {e}", file=sys.stderr)
        print(f"RESULT: FAIL count={len(errors)}")
        return 1

    print(f"RESULT: PASS journals={len(files)} index={index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
