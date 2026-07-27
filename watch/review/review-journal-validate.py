#!/usr/bin/env python3
import argparse
import hashlib
import json
import stat
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
    "review_bundle",
    "journal_path",
}

CORRELATED = REQUIRED
HEX_DIGITS = frozenset("0123456789abcdef")


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256_json(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def valid_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and set(value).issubset(HEX_DIGITS)
    )


def validate_record(path: Path, obj: object) -> list[str]:
    errors = []

    if not isinstance(obj, dict):
        return [f"{path}: record must be a JSON object"]

    missing = sorted(REQUIRED - set(obj))
    if missing:
        errors.append(f"{path}: missing required keys: {missing}")

    for key in ("review_bundle_sha256", "raw_response_sha256"):
        if not valid_sha256(obj.get(key)):
            errors.append(f"{path}: invalid {key}")

    bundle = obj.get("review_bundle")

    if not isinstance(bundle, dict):
        errors.append(f"{path}: review_bundle must be an object")
    else:
        expected_bundle_sha = obj.get("review_bundle_sha256")
        actual_bundle_sha = sha256_json(bundle)

        if expected_bundle_sha != actual_bundle_sha:
            errors.append(
                f"{path}: review_bundle_sha256 does not match review_bundle"
            )

        if bundle.get("request_id") != obj.get("request_id"):
            errors.append(
                f"{path}: review_bundle.request_id does not match request_id"
            )

        if bundle.get("review_type") != obj.get("review_type"):
            errors.append(
                f"{path}: review_bundle.review_type does not match review_type"
            )

    journal_path = obj.get("journal_path")
    if not isinstance(journal_path, str) or not journal_path:
        errors.append(f"{path}: journal_path must be a non-empty string")

    if (
        obj.get("authority") == "proposal_review_only"
        and obj.get("execution_allowed") is not False
    ):
        errors.append(
            f"{path}: proposal_review_only must have execution_allowed=false"
        )

    if obj.get("result_blocked") is not True:
        errors.append(f"{path}: result_blocked must be true")

    return errors


def validate_artifact(path: Path, obj: object) -> list[str]:
    errors = validate_record(path, obj)

    if not isinstance(obj, dict):
        return errors

    if obj.get("journal_path") != str(path):
        errors.append(
            f"{path}: journal_path does not match artifact path"
        )

    try:
        file_stat = path.stat()
    except OSError as exc:
        errors.append(
            f"{path}: unable to stat artifact: "
            f"{type(exc).__name__}: {exc}"
        )
    else:
        if not stat.S_ISREG(file_stat.st_mode):
            errors.append(f"{path}: artifact must be a regular file")

        mode = stat.S_IMODE(file_stat.st_mode)
        if mode & 0o222:
            errors.append(
                f"{path}: artifact must have no write bits, found {mode:04o}"
            )

    raw_response = obj.get("raw_response")

    if not isinstance(raw_response, dict):
        errors.append(f"{path}: raw_response must be an object")
    elif obj.get("raw_response_sha256") != sha256_json(raw_response):
        errors.append(
            f"{path}: raw_response_sha256 does not match raw_response"
        )

    return errors


LEGACY_INDEX_BUNDLE_COMPATIBILITY = {
    (
        "/mnt/collective/logs/spot/reviews/"
        "20260522T144126Z-review-20260522T144126Z.json"
    ): (
        "9714881452242ea790716d40b632bd1b9d654051f2f14b879"
        "4bccb916e985583"
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def normalize_legacy_index_record(
    obj: object,
    artifacts: dict[str, dict],
) -> object:
    """Hydrate only the pinned pre-Module-48 index row in memory."""

    if not isinstance(obj, dict) or "review_bundle" in obj:
        return obj

    journal_path = obj.get("journal_path")

    if not isinstance(journal_path, str):
        return obj

    expected_sha256 = LEGACY_INDEX_BUNDLE_COMPATIBILITY.get(
        journal_path
    )

    if expected_sha256 is None:
        return obj

    artifact = artifacts.get(journal_path)

    if not isinstance(artifact, dict):
        return obj

    try:
        actual_sha256 = sha256_file(Path(journal_path))
    except OSError:
        return obj

    if actual_sha256 != expected_sha256:
        return obj

    review_bundle = artifact.get("review_bundle")

    if not isinstance(review_bundle, dict):
        return obj

    normalized = dict(obj)
    normalized["review_bundle"] = review_bundle
    return normalized


def compare_index_record(
    source: Path,
    index_record: dict,
    artifact: dict,
) -> list[str]:
    errors = []

    for key in sorted(CORRELATED):
        if index_record.get(key) != artifact.get(key):
            errors.append(
                f"{source}: {key} does not match journal artifact"
            )

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Validate correlated Spot review journal artifacts."
    )
    ap.add_argument(
        "--journal-root",
        default="/mnt/collective/logs/spot/reviews",
    )
    ap.add_argument("--min-count", type=int, default=1)
    args = ap.parse_args()

    root = Path(args.journal_root)
    index = root / "index.jsonl"

    errors = []
    artifacts = {}
    index_counts = {}

    files = sorted(
        p for p in root.glob("*.json")
        if p.name != "index.json"
    )

    if len(files) < args.min_count:
        errors.append(
            f"{root}: expected at least {args.min_count} "
            f"journal json files, found {len(files)}"
        )

    for path in files:
        try:
            obj = load_json(path)
            errors.extend(validate_artifact(path, obj))

            if isinstance(obj, dict):
                artifacts[str(path)] = obj
        except Exception as exc:
            errors.append(
                f"{path}: unreadable json: "
                f"{type(exc).__name__}: {exc}"
            )

    if not index.exists():
        errors.append(f"{index}: missing index.jsonl")
    else:
        with index.open("r", encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                source = Path(f"{index}:{n}")

                try:
                    obj = json.loads(line)
                    obj = normalize_legacy_index_record(obj, artifacts)
                    errors.extend(validate_record(source, obj))

                    if not isinstance(obj, dict):
                        continue

                    journal_path = obj.get("journal_path")

                    if not isinstance(journal_path, str):
                        continue

                    index_counts[journal_path] = (
                        index_counts.get(journal_path, 0) + 1
                    )

                    artifact = artifacts.get(journal_path)

                    if artifact is None:
                        errors.append(
                            f"{source}: journal artifact not found: "
                            f"{journal_path}"
                        )
                        continue

                    errors.extend(
                        compare_index_record(source, obj, artifact)
                    )
                except Exception as exc:
                    errors.append(
                        f"{index}:{n}: invalid jsonl: "
                        f"{type(exc).__name__}: {exc}"
                    )

    for journal_path in sorted(artifacts):
        count = index_counts.get(journal_path, 0)

        if count != 1:
            errors.append(
                f"{journal_path}: expected exactly one index record, "
                f"found {count}"
            )

    if errors:
        for error in errors:
            print(f"[FAIL] {error}", file=sys.stderr)

        print(f"RESULT: FAIL count={len(errors)}")
        return 1

    print(
        f"RESULT: PASS journals={len(files)} "
        f"index={index} correlated={len(artifacts)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
