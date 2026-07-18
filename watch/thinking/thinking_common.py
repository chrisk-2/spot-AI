#!/usr/bin/env python3
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
THINKING_ROOT = Path(
    os.environ.get(
        "SPOT_THINKING_ROOT",
        "/mnt/collective/memory/spot/thinking",
    )
)


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def record_id(category: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (
        f"{category}-{socket.gethostname().split('.')[0]}-"
        f"{stamp}-{os.getpid()}"
    )


def require_thinking_root() -> None:
    collective = Path("/mnt/collective")

    if not collective.is_dir():
        raise RuntimeError("/mnt/collective is unavailable")

    THINKING_ROOT.mkdir(parents=True, exist_ok=True)

    if not os.access(THINKING_ROOT, os.W_OK):
        raise RuntimeError(
            f"thinking root is not writable: {THINKING_ROOT}"
        )


def run(
    argv: list[str],
    timeout: int = 120,
) -> dict[str, Any]:
    try:
        result = subprocess.run(
            argv,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )

        return {
            "argv": argv,
            "returncode": result.returncode,
            "timed_out": False,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv,
            "returncode": None,
            "timed_out": True,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def append_json_line(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")

    with lock_path.open("a", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)

        with path.open("a", encoding="utf-8") as index_handle:
            index_handle.write(
                json.dumps(
                    value,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n"
            )
            index_handle.flush()
            os.fsync(index_handle.fileno())

        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def write_record(
    category: str,
    record: dict[str, Any],
) -> dict[str, str]:
    require_thinking_root()

    category_root = THINKING_ROOT / category
    category_root.mkdir(parents=True, exist_ok=True)

    rid = str(record.get("record_id") or record_id(category))
    artifact = category_root / f"{rid}.json"
    checksum = artifact.with_suffix(".json.sha256")
    index = category_root / "index.jsonl"

    record["record_id"] = rid
    record.setdefault("timestamp", utc_now())

    encoded = (
        json.dumps(record, indent=2, sort_keys=True)
        + "\n"
    )

    with artifact.open("x", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())

    digest = hashlib.sha256(
        artifact.read_bytes()
    ).hexdigest()

    with checksum.open("x", encoding="utf-8") as handle:
        handle.write(f"{digest}  {artifact}\n")
        handle.flush()
        os.fsync(handle.fileno())

    append_json_line(
        index,
        {
            "timestamp": utc_now(),
            "record_id": rid,
            "category": category,
            "artifact": str(artifact),
            "checksum": str(checksum),
            "sha256": digest,
            "append_only": True,
            "mutation_authority": False,
            "execution_allowed": False,
        },
    )

    return {
        "artifact": str(artifact),
        "checksum": str(checksum),
        "index": str(index),
        "sha256": digest,
    }


def latest_record(category: str) -> dict[str, Any] | None:
    index = THINKING_ROOT / category / "index.jsonl"

    if not index.is_file():
        return None

    try:
        lines = [
            line.strip()
            for line in index.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]

        if not lines:
            return None

        index_record = json.loads(lines[-1])
        artifact = Path(index_record["artifact"])
        return read_json(artifact)
    except (
        OSError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ):
        return None
