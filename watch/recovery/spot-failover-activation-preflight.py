#!/usr/bin/env python3

import datetime
import json
import os
import pathlib
import subprocess
import tempfile

AUTHORITY_PATH = pathlib.Path("/etc/spot-failover/authority-state")
STATE_ROOT = pathlib.Path("/srv/spot-backup-data/failover-state")
REPLICA_ROOT = pathlib.Path("/srv/spot-backup-data/replica")
RELEASE_ROOT = REPLICA_ROOT / "releases"
CURRENT_LINK = REPLICA_ROOT / "current"
REPLICA_STATUS = STATE_ROOT / "replica-status.json"
RETENTION_STATUS = STATE_ROOT / "retention-status.json"
OUTPUT_PATH = STATE_ROOT / "activation-preflight-status.json"

MAX_REPLICA_STATUS_AGE = 1200


def utc_now():
    return datetime.datetime.now(
        datetime.timezone.utc
    ).replace(microsecond=0)


def normalize(value):
    if isinstance(value, bool):
        return "true" if value else "false"

    if value is None:
        return ""

    return str(value).strip().strip("'\"").lower()


def read_authority():
    if not AUTHORITY_PATH.is_file():
        return {}

    text = AUTHORITY_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    ).strip()

    if text.startswith("{"):
        try:
            data = json.loads(text)
            return {
                str(key).lower(): value
                for key, value in data.items()
            }
        except (OSError, ValueError, TypeError):
            return {}

    data = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        data[key.strip().lower()] = value.strip().strip("'\"")

    return data


def first_value(data, *keys):
    for key in keys:
        if key in data:
            return data[key]

    return None


def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError, TypeError):
        return {}


def run_command(command):
    try:
        result = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""

    return result.returncode, result.stdout.strip()


def timer_enabled(unit):
    returncode, output = run_command(
        ["systemctl", "is-enabled", unit]
    )

    return (
        returncode == 0
        and output in {"enabled", "enabled-runtime", "static"}
    )


def atomic_json_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_name = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(temporary_name, 0o644)
        os.replace(temporary_name, path)
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)


authority = read_authority()

standby_state = normalize(
    first_value(
        authority,
        "state",
        "default_state",
        "mode",
    )
)

authority_holder = normalize(
    first_value(
        authority,
        "authority_holder",
        "primary_authority",
        "authority",
    )
)

mutation_authority = normalize(
    first_value(authority, "mutation_authority")
)

execution_allowed = normalize(
    first_value(authority, "execution_allowed")
)

standby_locked = (
    standby_state == "standby"
    and authority_holder == "spot-core"
    and mutation_authority == "false"
    and execution_allowed == "false"
)

replica_data = load_json(REPLICA_STATUS)

replica_valid_raw = replica_data.get(
    "valid",
    replica_data.get("replica_valid"),
)

if replica_valid_raw is None:
    replica_valid_raw = (
        replica_data.get("manifest_valid") is True
        and replica_data.get("checksums_valid") is True
    )

replica_valid = replica_valid_raw is True

try:
    replica_status_age = max(
        0,
        int(utc_now().timestamp() - REPLICA_STATUS.stat().st_mtime),
    )
except OSError:
    replica_status_age = None

replica_status_fresh = (
    replica_status_age is not None
    and replica_status_age <= MAX_REPLICA_STATUS_AGE
)

current_is_symlink = CURRENT_LINK.is_symlink()

try:
    current_release = CURRENT_LINK.resolve(strict=True)
    current_release_exists = current_release.is_dir()
except (OSError, RuntimeError):
    current_release = None
    current_release_exists = False

release_within_root = False

if current_release is not None:
    try:
        release_within_root = (
            os.path.commonpath(
                [
                    str(current_release),
                    str(RELEASE_ROOT.resolve(strict=True)),
                ]
            )
            == str(RELEASE_ROOT.resolve(strict=True))
        )
    except (OSError, ValueError):
        release_within_root = False

observer_timer_enabled = timer_enabled(
    "spot-failover-observer.timer"
)

verifier_timer_enabled = timer_enabled(
    "spot-replica-verify.timer"
)

retention_timer_enabled = timer_enabled(
    "spot-replica-retention.timer"
)

docker_returncode, docker_output = run_command(
    ["docker", "ps", "-q"]
)

docker_runtime_available = docker_returncode == 0
no_running_containers = (
    docker_runtime_available
    and docker_output == ""
)

checks = {
    "authority_file_present": AUTHORITY_PATH.is_file(),
    "standby_locked": standby_locked,
    "current_is_symlink": current_is_symlink,
    "current_release_exists": current_release_exists,
    "release_within_release_root": release_within_root,
    "replica_status_present": REPLICA_STATUS.is_file(),
    "replica_status_fresh": replica_status_fresh,
    "replica_valid": replica_valid,
    "observer_timer_enabled": observer_timer_enabled,
    "verifier_timer_enabled": verifier_timer_enabled,
    "retention_timer_enabled": retention_timer_enabled,
    "retention_status_present": RETENTION_STATUS.is_file(),
    "docker_runtime_available": docker_runtime_available,
    "no_running_containers": no_running_containers,
}

required_checks = (
    "authority_file_present",
    "standby_locked",
    "current_is_symlink",
    "current_release_exists",
    "release_within_release_root",
    "replica_status_present",
    "replica_status_fresh",
    "replica_valid",
    "observer_timer_enabled",
    "verifier_timer_enabled",
    "retention_timer_enabled",
    "retention_status_present",
    "docker_runtime_available",
    "no_running_containers",
)

blockers = [
    check
    for check in required_checks
    if not checks[check]
]

preflight_pass = not blockers

payload = {
    "schema_version": 1,
    "generated_at": utc_now().isoformat().replace("+00:00", "Z"),
    "hostname": os.uname().nodename,
    "mode": "read-only",
    "authority": {
        "state": standby_state,
        "authority_holder": authority_holder,
        "mutation_authority": mutation_authority,
        "execution_allowed": execution_allowed,
        "standby_locked": standby_locked,
    },
    "replica": {
        "current_link": str(CURRENT_LINK),
        "current_release": (
            str(current_release)
            if current_release is not None
            else None
        ),
        "status_file": str(REPLICA_STATUS),
        "status_age_seconds": replica_status_age,
        "status_fresh": replica_status_fresh,
        "valid": replica_valid,
    },
    "checks": checks,
    "gate": {
        "preflight_pass": preflight_pass,
        "blockers": blockers,
        "activation_authorized": False,
        "promotion_permitted": False,
    },
}

atomic_json_write(OUTPUT_PATH, payload)

print(f"status: {OUTPUT_PATH}")
print(f"preflight_pass: {str(preflight_pass).lower()}")
print("activation_authorized: false")
print("promotion_permitted: false")

if blockers:
    print("blockers: " + ",".join(blockers))
    raise SystemExit(1)

print("blockers: none")
