from __future__ import annotations

import asyncio
import shlex
import json
import logging
import os
import statistics
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Awaitable, Callable, Literal
import hashlib
import shutil
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

APP_START_TS = int(time.time())
CONFIG_PATH = Path(os.environ.get("SPOTCORE_CONFIG", "/app/config/cluster_config.json"))
WATCH_STATE_PATH = Path(os.environ.get("SPOTCORE_WATCH_STATE", "/watch/state/fleet-status.json"))
EXEC_HISTORY_PATH = Path(os.environ.get("SPOTCORE_EXEC_HISTORY", "/app/shared_memory/exec-history.jsonl"))
DECISION_LOG_PATH = Path(os.environ.get("SPOTCORE_DECISION_LOG", "/app/shared_memory/decision-history.jsonl"))
ROUTING_AUDIT_PATH = Path(os.environ.get("SPOTCORE_ROUTING_AUDIT_LOG", "/watch/state/routing-audit.jsonl"))
REMEDIATION_STATE_PATH = Path(os.environ.get("SPOTCORE_REMEDIATION_STATE", "/watch/state/remediation-state.json"))
BACKUP_ROOT_PATH = Path(os.environ.get("SPOTCORE_BACKUP_ROOT", "/mnt/collective/backups"))
ACTION_LOG_ROOT = Path(os.environ.get("SPOTCORE_ACTION_LOG_ROOT", "/mnt/collective/logs/spot"))
AUTONOMY_ALLOW_HIGH_RISK = os.environ.get("SPOTCORE_ALLOW_HIGH_RISK_AUTONOMY", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

ALLOWED_REMOTE_SERVICES = {"ollama"}
SSH_USER = os.environ.get("SPOTCORE_SSH_USER", "ogre")
SSH_CONNECT_TIMEOUT = int(os.environ.get("SPOTCORE_SSH_CONNECT_TIMEOUT", "10"))
ADMIN_API_TOKEN = os.environ.get("SPOTCORE_ADMIN_API_TOKEN", "").strip()

HTTP_TIMEOUT = float(os.environ.get("SPOTCORE_HTTP_TIMEOUT", "240"))
LATENCY_WINDOW = int(os.environ.get("SPOTCORE_LATENCY_WINDOW", "100"))
DECISION_WINDOW = int(os.environ.get("SPOTCORE_DECISION_WINDOW", "200"))
ALTERNATE_DEBUG_LIMIT = int(os.environ.get("SPOTCORE_ALTERNATE_DEBUG_LIMIT", "10"))
ROUTING_AUDIT_WINDOW = int(os.environ.get("SPOTCORE_ROUTING_AUDIT_WINDOW", "500"))

ACTIVE_REQUESTS: dict[str, int] = {}
ACTIVE_GPU_REQUESTS: dict[str, dict[str, int]] = {}
ACTIVE_MODEL_REQUESTS: dict[str, dict[str, dict[str, int]]] = {}
WAITING_REQUESTS: dict[str, int] = defaultdict(int)
WARM_MODELS: dict[str, dict[str, int]] = defaultdict(dict)
LATENCY_HISTORY: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=LATENCY_WINDOW))
RECENT_DECISIONS: deque[dict[str, Any]] = deque(maxlen=DECISION_WINDOW)
RECENT_ROUTING_AUDIT: deque[dict[str, Any]] = deque(maxlen=ROUTING_AUDIT_WINDOW)
PENALTY_BOX: dict[str, dict[str, Any]] = {}
FAILURE_HISTORY: dict[str, deque[int]] = defaultdict(lambda: deque(maxlen=50))
ACTIVE_LOCK = asyncio.Lock()

CONFIG_CACHE: dict[str, Any] | None = None
CONFIG_MTIME: float | None = None

LOGGER = logging.getLogger("spotcore.app")

ROLE = Literal["heavy", "coding", "general", "utility", "watcher", "reasoning"]
ROLE_OWNERS: dict[str, str] = {
    "general": "spot-worker-01",
    "utility": "spot-worker-02",
    "coding": "spot-worker-03",
    "heavy": "spot-worker-04",
    "reasoning": "spot-worker-06"
}


class ExecRequest(BaseModel):
    prompt: str
    role: ROLE = "general"
    model: str | None = None
    stream: bool = False
    worker: str | None = None
    gpu_lane: str | None = None
    allow_fallback: bool = True
    allow_burst: bool = True
    priority: ROLE | None = None
    queue_wait_ms: int | None = None
    queue_poll_ms: int | None = None


class ExecResult(BaseModel):
    ok: bool
    worker: str
    worker_url: str
    gpu_lane: str
    gpu_label: str
    role_requested: str
    model: str
    response: str
    raw: dict[str, Any]


class OpenAIReviewRequest(BaseModel):
    prompt: str
    role: ROLE = "reasoning"
    model: str | None = None
    review_type: str = "policy_review"


class OpenAIReviewResult(BaseModel):
    ok: bool
    provider: str
    model: str
    role_requested: str
    review_type: str
    authority: str
    response: str
    raw: dict[str, Any]


class AdminValidateRequest(BaseModel):
    token: str
    worker: str
    commands: list[str]

class AdminRestartServiceRequest(BaseModel):
    token: str
    worker: str
    service: str


class AdminReadFileRequest(BaseModel):
    token: str
    worker: str
    path: str


class AdminWriteFileRequest(BaseModel):
    token: str
    worker: str
    path: str
    content: str

class AdminReadLocalFileRequest(BaseModel):
    token: str
    path: str


class AdminWriteLocalFileRequest(BaseModel):
    token: str
    path: str
    content: str

class AdminQuarantineRequest(BaseModel):
    token: str
    worker: str
    seconds: int = 1800
    reason: str = "manual_quarantine"

class AdminReleaseRequest(BaseModel):
    token: str
    worker: str

class AdminOperatorCommandRequest(BaseModel):
    token: str
    command: str


SPOT_CORE_ROOT = Path(os.environ.get("SPOTCORE_ROOT", "/srv/spot-core"))
SPOT_WATCH_ROOT = Path(os.environ.get("SPOTCORE_WATCH_ROOT", "/srv/watch"))
SPOT_HOST_STACK_ROOT = Path(os.environ.get("SPOTCORE_HOST_STACK_ROOT", "/home/ogre/spot-stack"))

OPERATOR_COMMANDS: dict[str, dict[str, Any]] = {
    "validate": {
    "argv": ["bash", str(SPOT_WATCH_ROOT / "fleet-validate.sh")],
    "cwd": str(SPOT_CORE_ROOT),
    "timeout": 300,
    "mutating": False,
    "env": {"SPOTCORE_ADMIN_API_TOKEN": ADMIN_API_TOKEN},
},
    "validate_smoke": {
    "argv": ["bash", str(SPOT_WATCH_ROOT / "fleet-validate.sh"), "--smoke"],
    "cwd": str(SPOT_CORE_ROOT),
    "timeout": 300,
    "mutating": True,
    "env": {"SPOTCORE_ADMIN_API_TOKEN": ADMIN_API_TOKEN},
},
    "save": {
        "argv": ["bash", str(SPOT_WATCH_ROOT / "spot-save.sh")],
        "cwd": str(SPOT_CORE_ROOT),
        "timeout": 300,
        "mutating": True,
    },
    "status": {
        "argv": ["bash", str(SPOT_WATCH_ROOT / "spot-ops.sh"), "status"],
        "cwd": str(SPOT_CORE_ROOT),
        "timeout": 120,
        "mutating": False,
    },
    "routing": {
        "argv": ["bash", str(SPOT_WATCH_ROOT / "spot-ops.sh"), "routing"],
        "cwd": str(SPOT_CORE_ROOT),
        "timeout": 120,
        "mutating": False,
    },
    "audit": {
        "argv": ["bash", str(SPOT_WATCH_ROOT / "spot-ops.sh"), "audit"],
        "cwd": str(SPOT_CORE_ROOT),
        "timeout": 120,
        "mutating": False,
    },
    "latency": {
        "argv": ["curl", "-fsS", "http://127.0.0.1:8787/stats/latency"],
        "cwd": str(SPOT_CORE_ROOT),
        "timeout": 120,
        "mutating": False,
    },
    "quarantine_state": {
        "argv": ["bash", str(SPOT_WATCH_ROOT / "spot-ops.sh"), "quarantine-state"],
        "cwd": str(SPOT_CORE_ROOT),
        "timeout": 120,
        "mutating": False,
    },
    "readiness": {
        "argv": ["curl", "-fsS", "http://127.0.0.1:8787/operator/readiness"],
        "cwd": str(SPOT_CORE_ROOT),
        "timeout": 120,
        "mutating": False,
    },
}


def _now() -> int:
    return int(time.time())

def require_admin_token(payload: dict) -> None:
    provided = str(payload.get("token", "")).strip()

    if not ADMIN_API_TOKEN:
        raise HTTPException(
            status_code=503,
            detail={"message": "admin api token is not configured"},
        )

    if provided != ADMIN_API_TOKEN:
        raise HTTPException(
            status_code=403,
            detail={"message": "invalid admin token"},
        )

def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True) + "\n")

def classify_action_risk(action_name: str, target: str, service: str, metadata: dict[str, Any] | None = None) -> str:
    metadata = metadata or {}

    # Read-only operator commands must not be escalated by words like
    # "routing" appearing in the command name. Mutation is controlled by
    # the OPERATOR_COMMANDS spec and the mutating flag.
    if action_name == "operator_command" and metadata.get("mutating") is False:
        return "low"

    text = " ".join(
        [
            action_name.lower(),
            target.lower(),
            service.lower(),
            json.dumps(metadata, sort_keys=True).lower(),
        ]
    )
    if any(
        token in text
        for token in ["firewall", "opnsense", "gateway", "vlan", "route", "routing", "dhcp", "dns", "acl"]
    ):
        return "high"
    if any(token in text for token in ["config", "deploy", "replace", "reload"]):
        return "medium"
    return "low"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def _copy_backup_source(src: Path, dest_root: Path, host: str | None = None) -> dict[str, Any]:
    """
    Supports:
    - local backup (existing behavior)
    - remote backup via SSH if host is provided
    """

    dest = dest_root / src.name

    # --- REMOTE BACKUP ---
    if host:
        # check existence remotely
        check = await run_ssh_command(host, f"test -e {shlex.quote(str(src))}")
        if check["returncode"] != 0:
            raise FileNotFoundError(f"remote backup source missing: {src} on {host}")

        # fetch file content
        result = await run_ssh_command(host, f"cat {shlex.quote(str(src))}")

        if result["returncode"] != 0:
            raise RuntimeError(f"failed to read remote file: {src} on {host}")

        # write locally into backup dir
        dest.write_text(result["stdout"], encoding="utf-8")

        return {
            "source": str(src),
            "dest": str(dest),
            "type": "remote_file",
            "host": host,
            "size": len(result["stdout"]),
            "sha256": hashlib.sha256(result["stdout"].encode()).hexdigest(),
        }

    # --- LOCAL BACKUP (existing behavior) ---
    if not src.exists():
        raise FileNotFoundError(f"backup source missing: {src}")

    if src.is_dir():
        shutil.copytree(src, dest, dirs_exist_ok=False)
        return {
            "source": str(src),
            "dest": str(dest),
            "type": "dir",
        }

    shutil.copy2(src, dest)
    return {
        "source": str(src),
        "dest": str(dest),
        "type": "file",
        "size": src.stat().st_size,
        "sha256": _sha256_file(dest),
    }

async def create_verified_backup(
    *,
    target: str,
    service: str,
    action_name: str,
    backup_sources: list[Path],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    timestamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    unique_suffix = str(time.time_ns())
    backup_dir = BACKUP_ROOT_PATH / target / service / f"{timestamp}-{unique_suffix}"
    backup_dir.mkdir(parents=True, exist_ok=False)

    artifacts: list[dict[str, Any]] = []
    host = metadata.get("host") if metadata else None

    for src in backup_sources:
        artifacts.append(await _copy_backup_source(src, backup_dir, host=host))

    marker = {
        "ts": _now(),
        "action": action_name,
        "target": target,
        "service": service,
        "backup_dir": str(backup_dir),
        "artifacts": artifacts,
        "metadata": metadata or {},
        "verified": True,
    }
    (backup_dir / "metadata.json").write_text(json.dumps(marker, indent=2, sort_keys=True), encoding="utf-8")
    return marker


def append_action_log(payload: dict[str, Any]) -> None:
    append_jsonl(ACTION_LOG_ROOT / "actions.jsonl", payload)


async def execute_with_enforcement(
    *,
    action_name: str,
    target: str,
    service: str,
    backup_sources: list[Path],
    execute_fn: Callable[[], Awaitable[dict[str, Any]]],
    verify_fn: Callable[[dict[str, Any]], Awaitable[tuple[bool, dict[str, Any]]]],
    rollback_fn: Callable[[dict[str, Any], dict[str, Any]], Awaitable[dict[str, Any]]] | None = None,
    metadata: dict[str, Any] | None = None,
    require_backup: bool = True,
) -> dict[str, Any]:
    started_ts = _now()
    risk_class = classify_action_risk(action_name, target, service, metadata)

    if risk_class == "high" and not AUTONOMY_ALLOW_HIGH_RISK:
        append_action_log(
            {
                "ts": started_ts,
                "status": "blocked",
                "action": action_name,
                "target": target,
                "service": service,
                "risk_class": risk_class,
                "reason": "high_risk_requires_explicit_approval",
                "metadata": metadata or {},
            }
        )
        raise HTTPException(
            status_code=403,
            detail={"message": "high-risk action blocked by policy", "action": action_name},
        )

    backup_record = None
    if require_backup:
        try:
            backup_record = await create_verified_backup(
                target=target,
                service=service,
                action_name=action_name,
                backup_sources=backup_sources,
                metadata=metadata,
            )
        except Exception as exc:
            append_action_log(
                {
                    "ts": started_ts,
                    "status": "blocked",
                    "action": action_name,
                    "target": target,
                    "service": service,
                    "risk_class": risk_class,
                    "reason": "backup_failed",
                    "error": repr(exc),
                    "metadata": metadata or {},
                }
            )
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "backup gate failed; action blocked",
                    "action": action_name,
                    "error": repr(exc),
                },
            ) from exc

    append_action_log(
        {
            "ts": started_ts,
            "status": "starting",
            "action": action_name,
            "target": target,
            "service": service,
            "risk_class": risk_class,
            "backup_path": backup_record["backup_dir"] if backup_record else None,
            "metadata": metadata or {},
        }
    )

    try:
        execution_result = await execute_fn()
    except HTTPException:
        raise
    except Exception as exc:
        try:
            append_action_log(
                {
                    "ts": _now(),
                    "status": "execute_failed",
                    "action": action_name,
                    "target": target,
                    "service": service,
                    "risk_class": risk_class,
                    "backup_path": backup_record["backup_dir"] if backup_record else None,
                    "error": repr(exc),
                    "metadata": metadata or {},
                }
            )
        except Exception as log_exc:
            LOGGER.exception(
                "action_log_write_failed_during_execute_failure action=%s target=%s service=%s error=%r",
                action_name,
                target,
                service,
                log_exc,
            )

        raise HTTPException(
            status_code=503,
            detail={
                "message": "execution failed after backup",
                "action": action_name,
                "target": target,
                "service": service,
                "backup_path": backup_record["backup_dir"] if backup_record else None,
                "error": repr(exc),
            },
        ) from exc

    verify_ok = False
    verify_data: dict[str, Any] = {}
    rollback_data: dict[str, Any] | None = None

    try:
        verify_ok, verify_data = await verify_fn(execution_result)
    except Exception as exc:
        verify_ok = False
        verify_data = {"error": repr(exc), "stage": "verify_exception"}

    if not verify_ok:
        if rollback_fn is not None and risk_class in {"low", "medium"} and backup_record is not None:
            try:
                raw = await rollback_fn(backup_record, execution_result)
                rollback_data = {
                    "ok": bool(raw.get("ok")) if "ok" in raw else raw.get("returncode", 1) == 0,
                    "restored_from": backup_record.get("backup_dir"),
                    "artifacts": backup_record.get("artifacts", []),
                    "ssh": raw,
                }
            except Exception as exc:
                rollback_data = {
                    "ok": False,
                    "error": repr(exc),
                    "stage": "rollback_exception",
                }

        append_action_log(
            {
                "ts": _now(),
                "status": "failed_verification",
                "action": action_name,
                "target": target,
                "service": service,
                "risk_class": risk_class,
                "backup_path": backup_record["backup_dir"] if backup_record else None,
                "verification": verify_data,
                "rollback": rollback_data,
                "metadata": metadata or {},
            }
        )

        raise HTTPException(
            status_code=503,
            detail={
                "message": "post-change verification failed",
                "action": action_name,
                "verification": verify_data,
                "rollback": rollback_data,
            },
        )

    append_action_log(
        {
            "ts": _now(),
            "status": "ok",
            "action": action_name,
            "target": target,
            "service": service,
            "risk_class": risk_class,
            "backup_path": backup_record["backup_dir"] if backup_record else None,
            "verification": verify_data,
            "metadata": metadata or {},
        }
    )

    return {
        "ok": True,
        "action": action_name,
        "risk_class": risk_class,
        "backup": backup_record,
        "verification": verify_data,
        "result": execution_result,
    }

def load_config() -> dict[str, Any]:
    global CONFIG_CACHE, CONFIG_MTIME
    try:
        mtime = CONFIG_PATH.stat().st_mtime
    except FileNotFoundError as exc:
        raise RuntimeError(f"Missing config file: {CONFIG_PATH}") from exc
    if CONFIG_CACHE is None or CONFIG_MTIME != mtime:
        CONFIG_CACHE = json.loads(CONFIG_PATH.read_text())
        CONFIG_MTIME = mtime
    return CONFIG_CACHE


def get_retry_policy() -> dict[str, Any]:
    try:
        cfg = load_config()
        return cfg.get(
            "retry_policy",
            {
                "same_worker_retries": 1,
                "alternate_worker_retries": 1,
                "retryable_errors": [],
            },
        )
    except Exception:
        return {
            "same_worker_retries": 1,
            "alternate_worker_retries": 1,
            "retryable_errors": [],
        }


def load_watch_state() -> dict[str, Any]:
    return read_json(WATCH_STATE_PATH, {"timestamp": None, "hosts": {}})



def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def load_remediation_state() -> dict[str, Any]:
    data = read_json(REMEDIATION_STATE_PATH, {})
    return data if isinstance(data, dict) else {}


def save_remediation_state(data: dict[str, Any]) -> None:
    write_json_atomic(REMEDIATION_STATE_PATH, data)

def remediation_entry(worker_name: str) -> dict[str, Any]:
    state = load_remediation_state()
    entry = state.get(worker_name, {})
    return entry if isinstance(entry, dict) else {}

def update_remediation_quarantine(worker_name: str, quarantined: bool, reason: str | None = None) -> None:
    state = load_remediation_state()
    entry = state.get(worker_name, {})
    if not isinstance(entry, dict):
        entry = {}

    entry["quarantined"] = quarantined
    entry["last_updated_ts"] = _now()
    entry["last_updated_by"] = "spot-core-api"

    if reason is not None:
        entry["reason"] = reason

    if quarantined:
        entry["since_ts"] = entry.get("since_ts", _now())
    else:
        entry["release_ts"] = _now()

    state[worker_name] = entry

    meta = state.get("_meta", {})
    if not isinstance(meta, dict):
        meta = {}
    meta["last_runtime_quarantine_update_ts"] = _now()
    state["_meta"] = meta

    save_remediation_state(state)


def update_watch_state_quarantine(worker_name: str, quarantined: bool) -> None:
    state = load_watch_state()
    hosts = state.get("hosts")

    if not isinstance(hosts, dict):
        return
    if worker_name not in hosts:
        return
    if not isinstance(hosts[worker_name], dict):
        return

    host = hosts[worker_name]
    host["quarantined"] = quarantined
    host["eligible"] = False if quarantined else bool(host.get("ssh_ok")) and (host.get("service_ok") is True) and not host.get("alerts")
    hosts[worker_name] = host
    state["hosts"] = hosts

    if "timestamp" not in state or state["timestamp"] is None:
        state["timestamp"] = _now()

    write_json_atomic(WATCH_STATE_PATH, state)


def worker_status(name: str) -> dict[str, Any]:
    return (load_watch_state().get("hosts") or {}).get(name, {})

def worker_host(worker_name: str, cfg: dict[str, Any]) -> str:
    worker = cfg["workers"].get(worker_name)
    if not worker:
        raise HTTPException(status_code=404, detail={"message": "unknown worker"})
    base_url = str(worker.get("base_url", ""))
    if "://" in base_url:
        hostport = base_url.split("://", 1)[1]
    else:
        hostport = base_url
    return hostport.split(":", 1)[0]

def resolve_local_path(path_str: str) -> Path:
    raw = Path(path_str)
    text = str(raw)
    candidates = [raw]

    path_aliases = [
        ("/home/ogre/spot-stack/watch/", SPOT_WATCH_ROOT),
        ("/home/ogre/spot-stack/spot-core/", SPOT_CORE_ROOT),
        ("/home/ogre/spot-stack/", Path("/home/ogre/spot-stack")),
        ("/srv/watch/", SPOT_WATCH_ROOT),
        ("/srv/spot-core/", SPOT_CORE_ROOT),
    ]

    for prefix, target_root in path_aliases:
        if text.startswith(prefix):
            rel = text.removeprefix(prefix)
            candidates.append(target_root / rel)

    if text == "/home/ogre/spot-stack/spot-core":
        candidates.append(SPOT_CORE_ROOT)
    if text == "/home/ogre/spot-stack/watch":
        candidates.append(SPOT_WATCH_ROOT)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[-1] if len(candidates) > 1 else candidates[0]

async def systemctl_show_service(host: str, service: str) -> dict[str, Any]:
    fields = [
        "Id",
        "ActiveState",
        "SubState",
        "MainPID",
        "ExecMainPID",
        "ActiveEnterTimestampMonotonic",
        "InactiveEnterTimestampMonotonic",
        "NRestarts",
    ]
    cmd = "systemctl show " + shlex.quote(service) + " --property=" + ",".join(fields)
    result = await run_ssh_command(host, cmd)

    parsed: dict[str, str] = {}
    if result["returncode"] == 0:
        for line in result["stdout"].splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                parsed[key] = value

    return {
        "ok": result["returncode"] == 0,
        "raw": result,
        "fields": parsed,
    }


def service_restart_verified(before: dict[str, Any], after: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    before_fields = before.get("fields") or {}
    after_fields = after.get("fields") or {}

    active_after = after_fields.get("ActiveState") == "active"

    changed_fields = []
    for field in ["MainPID", "ExecMainPID", "ActiveEnterTimestampMonotonic", "InactiveEnterTimestampMonotonic", "NRestarts"]:
        if str(before_fields.get(field, "")) != str(after_fields.get(field, "")):
            changed_fields.append(field)

    restart_observed = bool(changed_fields)

    return active_after and restart_observed, {
        "active_after": active_after,
        "restart_observed": restart_observed,
        "changed_fields": changed_fields,
        "before": before,
        "after": after,
    }


async def run_ssh_command(host: str, remote_cmd: str) -> dict[str, Any]:
    proc = await asyncio.create_subprocess_exec(
        "ssh",
        "-o",
        f"ConnectTimeout={SSH_CONNECT_TIMEOUT}",
        "-o",
        "BatchMode=yes",
        f"{SSH_USER}@{host}",
        remote_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return {
        "returncode": proc.returncode,
        "stdout": stdout.decode("utf-8", errors="replace"),
        "stderr": stderr.decode("utf-8", errors="replace"),
    }

def worker_metric_int(status: dict[str, Any], key: str, default: int = 0) -> int:
    try:
        value = status.get(key, default)
        return default if value is None else int(value)
    except Exception:
        return default


def worker_metric_float(status: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        value = status.get(key, default)
        return default if value is None else float(value)
    except Exception:
        return default


def scheduler_running_jobs(worker_name: str) -> int:
    return ACTIVE_REQUESTS.get(worker_name, 0)


def gpu_running_jobs(worker_name: str, gpu_lane: str) -> int:
    return ACTIVE_GPU_REQUESTS.get(worker_name, {}).get(gpu_lane, 0)


def model_running_jobs(worker_name: str, gpu_lane: str, model: str) -> int:
    return ACTIVE_MODEL_REQUESTS.get(worker_name, {}).get(gpu_lane, {}).get(model, 0)


def watcher_installed_models(status: dict[str, Any]) -> list[str]:
    models = status.get("models") or []
    return [str(m) for m in models] if isinstance(models, list) else []


def mark_model_warm(worker_name: str, model: str) -> None:
    WARM_MODELS[worker_name][model] = _now()


def seed_warm_models() -> None:
    if not EXEC_HISTORY_PATH.exists():
        return
    for line in EXEC_HISTORY_PATH.read_text(encoding="utf-8").splitlines()[-500:]:
        try:
            item = json.loads(line)
        except Exception:
            continue
        worker = item.get("worker")
        model = item.get("model_used") or item.get("model")
        if worker and model:
            WARM_MODELS[str(worker)][str(model)] = int(item.get("ts", _now()))


def seed_routing_audit() -> None:
    if not ROUTING_AUDIT_PATH.exists():
        return
    for line in ROUTING_AUDIT_PATH.read_text(encoding="utf-8").splitlines()[-ROUTING_AUDIT_WINDOW:]:
        try:
            RECENT_ROUTING_AUDIT.append(json.loads(line))
        except Exception:
            continue

def seed_recent_decisions() -> None:
    if not DECISION_LOG_PATH.exists():
        return
    for line in DECISION_LOG_PATH.read_text(encoding="utf-8").splitlines()[-DECISION_WINDOW:]:
        try:
            RECENT_DECISIONS.append(json.loads(line))
        except Exception:
            continue


def build_decision_latency_index() -> dict[tuple[int, str, str, str], float]:
    index: dict[tuple[int, str, str, str], float] = {}
    if not DECISION_LOG_PATH.exists():
        return index

    for line in DECISION_LOG_PATH.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except Exception:
            continue

        ts = int(item.get("ts") or 0)
        worker = str(item.get("worker") or "")
        gpu_lane = str(item.get("gpu_lane") or "")
        model = str(item.get("model") or "")
        latency = item.get("latency") or {}
        tok_per_sec = latency.get("avg_tok_per_sec")

        if ts and worker and gpu_lane and model and tok_per_sec is not None:
            try:
                index[(ts, worker, gpu_lane, model)] = float(tok_per_sec)
            except Exception:
                continue

    return index


def seed_latency_history() -> None:
    if not EXEC_HISTORY_PATH.exists():
        return

    decision_latency_index = build_decision_latency_index()

    for line in EXEC_HISTORY_PATH.read_text(encoding="utf-8").splitlines()[-1000:]:
        try:
            item = json.loads(line)
        except Exception:
            continue

        worker = str(item.get("worker") or "")
        gpu_lane = str(item.get("gpu_lane") or "unknown")
        model = str(item.get("model_used") or item.get("model") or "")
        role = str(item.get("role_requested") or item.get("role") or "unknown")
        ts = int(item.get("ts") or _now())

        if not worker or not model:
            continue

        total_duration = int(item.get("total_duration") or 0)
        eval_count = int(item.get("eval_count") or 0)
        eval_duration = int(item.get("eval_duration") or 0)

        tok_per_sec = 0.0

        if eval_count > 0 and eval_duration > 0:
            tok_per_sec = eval_count / (eval_duration / 1_000_000_000)
        else:
            tok_per_sec = decision_latency_index.get((ts, worker, gpu_lane, model), 0.0)
            if tok_per_sec <= 0 and eval_count > 0 and total_duration > 0:
                tok_per_sec = eval_count / (total_duration / 1_000_000_000)

        LATENCY_HISTORY[worker].append(
            {
                "ts": ts,
                "gpu_lane": gpu_lane,
                "model": model,
                "role": role,
                "total_duration_ns": total_duration,
                "tok_per_sec": tok_per_sec,
            }
        )

def current_penalty(worker_name: str) -> dict[str, Any] | None:
    penalty = PENALTY_BOX.get(worker_name)
    if not penalty:
        return None
    if penalty.get("until", 0) <= _now():
        PENALTY_BOX.pop(worker_name, None)
        return None
    return penalty


def append_failure(worker_name: str) -> None:
    FAILURE_HISTORY[worker_name].append(_now())


def failure_window_count(worker_name: str, window_sec: int) -> int:
    cutoff = _now() - window_sec
    hist = FAILURE_HISTORY[worker_name]
    while hist and hist[0] < cutoff:
        hist.popleft()
    return len(hist)


def record_failure(worker_name: str, reason: str, cfg: dict[str, Any]) -> None:
    policy = cfg.get("penalty_policy", {})
    cooldown = int(policy.get("cooldown_sec", 120))
    quarantine_after = int(policy.get("quarantine_after_failures", 3))
    quarantine_window = int(policy.get("quarantine_window_sec", 600))
    quarantine_sec = int(policy.get("quarantine_sec", 1800))
    append_failure(worker_name)
    count = failure_window_count(worker_name, quarantine_window)
    penalty_reason = reason
    until = _now() + cooldown
    quarantined = False
    if count >= quarantine_after:
        penalty_reason = f"auto_quarantine:{reason}"
        until = _now() + quarantine_sec
        quarantined = True
    PENALTY_BOX[worker_name] = {
        "reason": penalty_reason,
        "until": until,
        "ts": _now(),
        "quarantined": quarantined,
        "failure_count_window": count,
    }


def record_latency(worker_name: str, gpu_lane: str, model: str, role: str, data: dict[str, Any]) -> None:
    total_duration = int(data.get("total_duration") or 0)
    eval_count = int(data.get("eval_count") or 0)
    eval_duration = int(data.get("eval_duration") or 0)
    tok_per_sec = eval_count / (eval_duration / 1_000_000_000) if eval_count > 0 and eval_duration > 0 else 0.0
    LATENCY_HISTORY[worker_name].append(
        {
            "ts": _now(),
            "gpu_lane": gpu_lane,
            "model": model,
            "role": role,
            "total_duration_ns": total_duration,
            "tok_per_sec": tok_per_sec,
        }
    )


def worker_latency_summary(worker_name: str) -> dict[str, Any]:
    items = list(LATENCY_HISTORY.get(worker_name, []))
    if not items:
        return {"count": 0, "avg_total_ms": None, "p50_total_ms": None, "avg_tok_per_sec": None}
    total_ms = [round(i["total_duration_ns"] / 1_000_000, 2) for i in items if i["total_duration_ns"] > 0]
    toks = [i["tok_per_sec"] for i in items if i["tok_per_sec"] > 0]
    return {
        "count": len(items),
        "avg_total_ms": round(sum(total_ms) / len(total_ms), 2) if total_ms else None,
        "p50_total_ms": round(statistics.median(total_ms), 2) if total_ms else None,
        "avg_tok_per_sec": round(sum(toks) / len(toks), 2) if toks else None,
    }


def append_decision(payload: dict[str, Any]) -> None:
    RECENT_DECISIONS.append(payload)
    append_jsonl(DECISION_LOG_PATH, payload)


def append_routing_audit(payload: dict[str, Any]) -> None:
    RECENT_ROUTING_AUDIT.append(payload)
    try:
        append_jsonl(ROUTING_AUDIT_PATH, payload)
    except Exception as exc:
        LOGGER.exception(
            "routing_audit_write_failed path=%s ts=%s role=%s status=%s worker=%s error=%r",
            str(ROUTING_AUDIT_PATH),
            payload.get("ts"),
            payload.get("role"),
            payload.get("status"),
            payload.get("final_worker") or payload.get("selected_worker") or payload.get("worker"),
            exc,
        )

def installed_models_for_worker(worker_name: str, cfg: dict[str, Any]) -> set[str]:
    status = worker_status(worker_name)
    watcher_models = set(watcher_installed_models(status))
    config_models = set(cfg["workers"].get(worker_name, {}).get("installed_models", []))
    return watcher_models | config_models


def is_worker_healthy(worker_name: str, cfg: dict[str, Any]) -> tuple[bool, str]:
    status = worker_status(name=worker_name)
    if not status:
        return False, "missing_watch_status"
    penalty = current_penalty(worker_name)
    if penalty:
        return False, penalty["reason"]
    if status.get("quarantined") is True:
        return False, "quarantined"
    if status.get("ssh_ok") is False:
        return False, "ssh_down"
    if status.get("service_ok") is False:
        return False, "service_down"
    bad_alerts = set(cfg.get("health_policy", {}).get("blocking_alerts", []))
    for alert in status.get("alerts") or []:
        if alert in bad_alerts:
            return False, f"alert:{alert}"
    return True, "ok"


def allowed_roles_for_lane(cfg: dict[str, Any], worker_name: str, gpu_lane: str, allow_burst: bool) -> set[str]:
    allowed = set(cfg["workers"][worker_name]["gpu_routes"][gpu_lane].get("classes", []))
    if allow_burst:
        allowed.update(cfg["workers"][worker_name].get("burst_gpu_routes", {}).get(gpu_lane, {}).get("classes", []))
    return allowed


def lane_label(cfg: dict[str, Any], worker_name: str, gpu_lane: str) -> str:
    return cfg["workers"][worker_name]["gpu_routes"][gpu_lane].get("label", gpu_lane)


def role_priority(cfg: dict[str, Any], role: str) -> list[str]:
    return list(cfg.get("role_priority", {}).get(role, []))


def queue_defaults(cfg: dict[str, Any], role: str, req: ExecRequest) -> tuple[int, int]:
    queue_cfg = cfg.get("queue_policy", {})
    per_role = queue_cfg.get("per_role", {}).get(role, {})
    wait_ms = (
        req.queue_wait_ms
        if req.queue_wait_ms is not None
        else int(per_role.get("queue_wait_ms", queue_cfg.get("queue_wait_ms", 1500)))
    )
    poll_ms = (
        req.queue_poll_ms
        if req.queue_poll_ms is not None
        else int(per_role.get("queue_poll_ms", queue_cfg.get("queue_poll_ms", 200)))
    )
    return wait_ms, poll_ms


def burst_after_ms(cfg: dict[str, Any], role: str) -> int:
    queue_cfg = cfg.get("queue_policy", {})
    per_role = queue_cfg.get("per_role", {}).get(role, {})
    return int(per_role.get("burst_after_ms", queue_cfg.get("burst_after_ms", 500)))


def priority_of_request(req: ExecRequest) -> str:
    return req.priority or req.role


def higher_priority_waiting(cfg: dict[str, Any], priority: str) -> bool:
    order = list(cfg.get("priority_order", ["heavy", "coding", "general", "utility", "watcher"]))
    try:
        idx = order.index(priority)
    except ValueError:
        return False
    return any(WAITING_REQUESTS.get(p, 0) > 0 for p in order[:idx])


def classify_request_tier(req: ExecRequest) -> tuple[str, str | None]:
    text = req.prompt.lower()

    if req.role == "reasoning":
        return ("reasoning", "role_reasoning")

    if len(req.prompt) >= 4000:
        return ("premium", "prompt_length")

    premium_markers = [
        "deep analysis",
        "architecture",
        "architect",
        "design review",
        "root cause",
        "multi-step",
        "compare options",
        "tradeoff",
        "risk analysis",
        "migration plan",
        "roadmap",
        "full plan",
        "large context",
        "complex",
    ]

    for marker in premium_markers:
        if marker in text:
            return ("premium", f"marker:{marker}")

    if req.model:
        model = req.model.lower()
        if "32b" in model or "30b" in model or "24b" in model or "deepseek-r1" in model:
            return ("premium", "explicit_model")

    return ("normal", None)


def prompt_needs_premium_model(req: ExecRequest) -> bool:
    text = req.prompt.lower()
    if req.role == "reasoning":
        return True
    if len(req.prompt) >= 4000:
        return True
    premium_markers = [
        "deep analysis",
        "architecture",
        "architect",
        "design review",
        "root cause",
        "multi-step",
        "compare options",
        "tradeoff",
        "risk analysis",
        "migration plan",
        "roadmap",
        "full plan",
        "large context",
        "complex",
    ]
    return any(marker in text for marker in premium_markers)


def select_preferred_models(
    cfg: dict[str, Any],
    worker_name: str,
    gpu_lane: str,
    role: str,
    requested_model: str | None,
    allow_fallback: bool,
    req: ExecRequest | None = None,
) -> list[str]:
    prefs = list(cfg["workers"][worker_name]["gpu_routes"][gpu_lane].get("model_preferences", {}).get(role, []))
    if requested_model:
        return [requested_model] + [m for m in prefs if m != requested_model] if allow_fallback else [requested_model]

    if req is not None and prompt_needs_premium_model(req):
        premium = [
            m for m in prefs
            if ":32b" in m or "32b" in m or "30b" in m or "24b" in m or "deepseek-r1" in m
        ]
        if premium:
            preferred_premium = sorted(
                premium,
                key=lambda m: (
                    0 if "30b" in m else
                    1 if "32b" in m else
                    2 if "24b" in m else
                    3
                ),
            )
            return [preferred_premium[0]] if not allow_fallback else preferred_premium + [m for m in prefs if m not in preferred_premium]

    return prefs


def model_concurrency_limit(cfg: dict[str, Any], worker_name: str, gpu_lane: str, model: str) -> int | None:
    limits = cfg["workers"][worker_name]["gpu_routes"][gpu_lane].get("model_limits", {})
    return int(limits[model]) if model in limits else None


def score_candidate(cfg: dict[str, Any], worker_name: str, gpu_lane: str, role: str, model: str, burst_mode: bool) -> float:
    status = worker_status(worker_name)
    weights = cfg.get("score_weights", {})
    score = 1000.0
    prefs = (
        cfg["workers"]
        .get(worker_name, {})
        .get("gpu_routes", {})
        .get(gpu_lane, {})
        .get("model_preferences", {})
        .get(role, [])
    )

    if model in prefs:
        pref_index = prefs.index(model)
        pref_bonus = max(0, (len(prefs) - pref_index)) * 120
        score += pref_bonus
    rp = role_priority(cfg, role)
    if worker_name in rp:
        score += max(0, (len(rp) - rp.index(worker_name))) * float(weights.get("role_rank_bonus", 30))
    gpu_free_mb = worker_metric_int(status, "gpu_free_mb_max", 0)
    gpu_vram_total_mb = max(1, worker_metric_int(status, "gpu_vram_total_mb_max", 1))
    load_1 = worker_metric_float(status, "load_1", 0.0)
    score += (gpu_free_mb / gpu_vram_total_mb) * float(weights.get("gpu_free_ratio_bonus", 200))
    score -= load_1 * float(weights.get("load_penalty", 18))
    score -= scheduler_running_jobs(worker_name) * float(weights.get("worker_active_penalty", 25))
    score -= gpu_running_jobs(worker_name, gpu_lane) * float(weights.get("lane_active_penalty", 45))
    score -= model_running_jobs(worker_name, gpu_lane, model) * float(weights.get("model_active_penalty", 60))
    warm_ts = WARM_MODELS.get(worker_name, {}).get(model)
    if warm_ts:
        max_age = int(cfg.get("warm_model_policy", {}).get("warm_seconds", 3600))
        age = max(1, _now() - warm_ts)
        if age <= max_age:
            score += float(weights.get("warm_model_bonus", 80)) * (1 - (age / max_age))
    lat = worker_latency_summary(worker_name)
    if lat.get("avg_total_ms"):
        score += max(0.0, 1500 - float(lat["avg_total_ms"])) / 100.0 * float(weights.get("latency_bonus", 8))
    if current_penalty(worker_name):
        score -= float(weights.get("penalty_box_penalty", 500))

    remediation = remediation_entry(worker_name)
    if remediation.get("degraded") is True:
        fallback_count_window = 0
        try:
            fallback_count_window = int(remediation.get("fallback_count_window", 0) or 0)
        except Exception:
            fallback_count_window = 0

        degraded_penalty = float(weights.get("degraded_worker_penalty", 180))
        degraded_step_penalty = float(weights.get("degraded_fallback_step_penalty", 20))
        score -= degraded_penalty
        score -= fallback_count_window * degraded_step_penalty

    if burst_mode:
        score -= float(weights.get("burst_penalty", 125))
    return round(score, 4)

def increment_active(worker_name: str, gpu_lane: str, model: str) -> None:
    ACTIVE_REQUESTS[worker_name] = ACTIVE_REQUESTS.get(worker_name, 0) + 1
    ACTIVE_GPU_REQUESTS.setdefault(worker_name, {})
    ACTIVE_GPU_REQUESTS[worker_name][gpu_lane] = ACTIVE_GPU_REQUESTS[worker_name].get(gpu_lane, 0) + 1
    ACTIVE_MODEL_REQUESTS.setdefault(worker_name, {})
    ACTIVE_MODEL_REQUESTS[worker_name].setdefault(gpu_lane, {})
    ACTIVE_MODEL_REQUESTS[worker_name][gpu_lane][model] = (
        ACTIVE_MODEL_REQUESTS[worker_name][gpu_lane].get(model, 0) + 1
    )


def decrement_active(worker_name: str, gpu_lane: str, model: str) -> None:
    if worker_name in ACTIVE_REQUESTS:
        ACTIVE_REQUESTS[worker_name] -= 1
        if ACTIVE_REQUESTS[worker_name] <= 0:
            ACTIVE_REQUESTS.pop(worker_name, None)
    if worker_name in ACTIVE_GPU_REQUESTS and gpu_lane in ACTIVE_GPU_REQUESTS[worker_name]:
        ACTIVE_GPU_REQUESTS[worker_name][gpu_lane] -= 1
        if ACTIVE_GPU_REQUESTS[worker_name][gpu_lane] <= 0:
            del ACTIVE_GPU_REQUESTS[worker_name][gpu_lane]
        if not ACTIVE_GPU_REQUESTS[worker_name]:
            ACTIVE_GPU_REQUESTS.pop(worker_name, None)
    if worker_name in ACTIVE_MODEL_REQUESTS and gpu_lane in ACTIVE_MODEL_REQUESTS[worker_name]:
        bucket = ACTIVE_MODEL_REQUESTS[worker_name][gpu_lane]
        if model in bucket:
            bucket[model] -= 1
            if bucket[model] <= 0:
                del bucket[model]
        if not bucket:
            del ACTIVE_MODEL_REQUESTS[worker_name][gpu_lane]
        if not ACTIVE_MODEL_REQUESTS[worker_name]:
            ACTIVE_MODEL_REQUESTS.pop(worker_name, None)


def worker_admission_allowed(cfg: dict[str, Any], worker_name: str, role: str) -> tuple[bool, str]:
    worker_cfg = cfg["workers"][worker_name]
    if scheduler_running_jobs(worker_name) >= int(worker_cfg.get("max_total", 0)):
        return False, "worker_at_capacity"
    if int(worker_cfg.get("class_limits", {}).get(role, 0)) <= 0:
        return False, f"role_not_allowed:{role}"
    return True, "ok"


def lane_admission_allowed(
    cfg: dict[str, Any],
    worker_name: str,
    gpu_lane: str,
    role: str,
    model: str,
    allow_burst: bool,
) -> tuple[bool, str]:
    lane_cfg = cfg["workers"][worker_name]["gpu_routes"][gpu_lane]
    if gpu_running_jobs(worker_name, gpu_lane) >= int(lane_cfg.get("max_total", 0)):
        return False, "gpu_lane_at_capacity"
    if role not in allowed_roles_for_lane(cfg, worker_name, gpu_lane, allow_burst):
        return False, f"role_not_allowed:{role}"
    model_limit = model_concurrency_limit(cfg, worker_name, gpu_lane, model)
    if model_limit is not None and model_running_jobs(worker_name, gpu_lane, model) >= model_limit:
        return False, "model_at_capacity"
    return True, "ok"


def gather_candidates(cfg: dict[str, Any], req: ExecRequest, use_burst: bool) -> tuple[list[tuple[float, dict[str, Any]]], list[dict[str, Any]]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    failures: list[dict[str, Any]] = []
    workers = role_priority(cfg, req.role)

    owner_worker = role_owner(req.role)
    if req.worker:
        workers = [req.worker]
    elif owner_worker in workers:
        if not req.allow_fallback:
            workers = [owner_worker]
        else:
            owner_state = evaluate_owner_state(cfg, req, owner_worker)
            if owner_state.get("owner_healthy") is True and owner_state.get("owner_admissible") is True:
                workers = [owner_worker]
    for worker_name in workers:
        if worker_name not in cfg["workers"]:
            failures.append({"worker": worker_name, "reason": "unknown_worker", "stage": "candidate"})
            continue
        healthy, health_reason = is_worker_healthy(worker_name, cfg)
        if not healthy:
            failures.append({"worker": worker_name, "reason": health_reason, "stage": "health"})
            continue
        allowed, reason = worker_admission_allowed(cfg, worker_name, req.role)
        if not allowed:
            failures.append({"worker": worker_name, "reason": reason, "stage": "admission"})
            continue
        installed = installed_models_for_worker(worker_name, cfg)
        if not installed:
            failures.append({"worker": worker_name, "reason": "no_installed_models_visible", "stage": "models"})
            continue
        lane_names = [req.gpu_lane] if req.gpu_lane else list(cfg["workers"][worker_name]["gpu_routes"].keys())
        for gpu_lane in lane_names:
            if gpu_lane not in cfg["workers"][worker_name]["gpu_routes"]:
                failures.append(
                    {
                        "worker": worker_name,
                        "gpu_lane": gpu_lane,
                        "reason": "unknown_gpu_lane",
                        "stage": "candidate",
                    }
                )
                continue
            models = select_preferred_models(cfg, worker_name, gpu_lane, req.role, req.model, req.allow_fallback, req=req)
            if not models:
                failures.append(
                    {
                        "worker": worker_name,
                        "gpu_lane": gpu_lane,
                        "reason": "no_model_preferences",
                        "stage": "models",
                    }
                )
                continue
            for model in models:
                if model not in installed:
                    continue
                lane_ok, lane_reason = lane_admission_allowed(cfg, worker_name, gpu_lane, req.role, model, use_burst)
                if not lane_ok:
                    failures.append(
                        {
                            "worker": worker_name,
                            "gpu_lane": gpu_lane,
                            "model": model,
                            "reason": lane_reason,
                            "stage": "gpu_admission",
                        }
                    )
                    continue
                scored.append(
                    (
                        score_candidate(cfg, worker_name, gpu_lane, req.role, model, use_burst),
                        {
                            "worker": worker_name,
                            "worker_url": cfg["workers"][worker_name]["base_url"],
                            "gpu_lane": gpu_lane,
                            "gpu_label": lane_label(cfg, worker_name, gpu_lane),
                            "model": model,
                            "burst_mode": use_burst,
                        },
                    )
                )
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored, failures


def shortlist_candidates(
    cfg: dict[str, Any],
    req: ExecRequest,
    excluded_workers: set[str],
    preferred_model: str | None = None,
) -> list[dict[str, Any]]:
    shortlist: list[dict[str, Any]] = []

    candidate_requests: list[tuple[str, ExecRequest]] = []
    if preferred_model:
        candidate_requests.append(
            (
                "same_model",
                clone_request(req, model=preferred_model, allow_fallback=False),
            )
        )
    candidate_requests.append(("flex_model", req))

    seen_keys: set[tuple[str, str, str]] = set()

    for mode, candidate_req in candidate_requests:
        normal_scored, normal_failures = gather_candidates(cfg, candidate_req, False)
        burst_scored: list[tuple[float, dict[str, Any]]] = []
        if candidate_req.allow_burst:
            burst_scored, _ = gather_candidates(cfg, candidate_req, True)

        for score, candidate in normal_scored + burst_scored:
            if candidate["worker"] in excluded_workers:
                continue
            key = (candidate["worker"], candidate["gpu_lane"], candidate["model"])
            if key in seen_keys:
                continue
            seen_keys.add(key)
            shortlist.append(
                {
                    "mode": mode,
                    "score": score,
                    "worker": candidate["worker"],
                    "worker_url": candidate["worker_url"],
                    "gpu_lane": candidate["gpu_lane"],
                    "gpu_label": candidate["gpu_label"],
                    "model": candidate["model"],
                    "burst_mode": candidate["burst_mode"],
                }
            )
            if len(shortlist) >= ALTERNATE_DEBUG_LIMIT:
                return shortlist

        if mode == "same_model" and not normal_scored and preferred_model:
            shortlist.append(
                {
                    "mode": mode,
                    "reason": "no_same_model_candidates",
                    "preferred_model": preferred_model,
                    "excluded_workers": sorted(excluded_workers),
                    "failure_sample": normal_failures[:5],
                }
            )

    return shortlist


async def choose_worker_and_model(cfg: dict[str, Any], req: ExecRequest) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    failures: list[dict[str, Any]] = []
    priority = priority_of_request(req)
    wait_ms, poll_ms = queue_defaults(cfg, req.role, req)
    burst_ms = burst_after_ms(cfg, req.role)
    WAITING_REQUESTS[priority] += 1
    started = time.monotonic()
    try:
        while True:
            if higher_priority_waiting(cfg, priority):
                await asyncio.sleep(poll_ms / 1000.0)
                if ((time.monotonic() - started) * 1000) >= wait_ms:
                    break
                continue
            elapsed_ms = int((time.monotonic() - started) * 1000)
            scored, batch_failures = gather_candidates(cfg, req, False)
            failures.extend(batch_failures)
            if scored:
                return scored[0][1], failures
            if req.allow_burst and elapsed_ms >= burst_ms:
                burst_scored, burst_failures = gather_candidates(cfg, req, True)
                failures.extend(burst_failures)
                if burst_scored:
                    return burst_scored[0][1], failures
            if elapsed_ms >= wait_ms:
                break
            await asyncio.sleep(poll_ms / 1000.0)
    finally:
        WAITING_REQUESTS[priority] = max(0, WAITING_REQUESTS.get(priority, 0) - 1)
    raise HTTPException(
        status_code=503,
        detail={
            "message": f"no healthy eligible workers with an admissible lane/model for role '{req.role}'",
            "failures": failures[-50:],
        },
    )


def retryable_error_names(cfg: dict[str, Any]) -> set[str]:
    retry = cfg.get("retry_policy", {})
    names = retry.get("retryable_errors", []) or []
    return {str(name) for name in names}


def is_retryable_exception(cfg: dict[str, Any], exc: Exception) -> bool:
    allowed = retryable_error_names(cfg)
    if not allowed:
        return False
    for cls in type(exc).mro():
        if cls.__name__ in allowed:
            return True
    return False


def is_embed_request(role: str, model: str) -> bool:
    return role == "utility" and any(token in model for token in ["embed", "bge-"])


def request_to_dict(req: ExecRequest) -> dict[str, Any]:
    if hasattr(req, "model_dump"):
        return req.model_dump()
    return req.dict()


def clone_request(req: ExecRequest, **updates: Any) -> ExecRequest:
    data = request_to_dict(req)
    data.update(updates)
    return ExecRequest(**data)


def record_retry_event(events: list[dict[str, Any]], chosen: dict[str, Any], exc: Exception, phase: str, attempt: int) -> None:
    events.append(
        {
            "ts": _now(),
            "phase": phase,
            "attempt": attempt,
            "worker": chosen["worker"],
            "worker_url": chosen["worker_url"],
            "gpu_lane": chosen["gpu_lane"],
            "gpu_label": chosen["gpu_label"],
            "model": chosen["model"],
            "error_type": type(exc).__name__,
            "error": repr(exc),
        }
    )


def record_retry_note(events: list[dict[str, Any]], chosen: dict[str, Any], phase: str, note: str, **extra: Any) -> None:
    payload = {
        "ts": _now(),
        "phase": phase,
        "worker": chosen["worker"],
        "worker_url": chosen["worker_url"],
        "gpu_lane": chosen["gpu_lane"],
        "gpu_label": chosen["gpu_label"],
        "model": chosen["model"],
        "note": note,
    }
    payload.update(extra)
    events.append(payload)


def should_skip_same_worker_retry(cfg: dict[str, Any], worker_name: str, exc: Exception) -> tuple[bool, str]:
    status = worker_status(worker_name)
    if status.get("quarantined") is True:
        return True, "watch_quarantined"
    if status.get("ssh_ok") is False:
        return True, "watch_ssh_down"
    if status.get("service_ok") is False:
        return True, "watch_service_down"
    if isinstance(exc, httpx.ConnectError):
        return True, "connect_error"
    return False, ""


def role_owner(role: str) -> str | None:
    return ROLE_OWNERS.get(role)


def evaluate_owner_state(cfg: dict[str, Any], req: ExecRequest, owner_worker: str | None) -> dict[str, Any]:
    if not owner_worker:
        return {
            "owner_worker": None,
            "owner_known": False,
            "owner_healthy": False,
            "owner_admissible": False,
            "owner_has_model": False,
            "owner_reason": "no_owner_defined",
        }

    if owner_worker not in cfg.get("workers", {}):
        return {
            "owner_worker": owner_worker,
            "owner_known": False,
            "owner_healthy": False,
            "owner_admissible": False,
            "owner_has_model": False,
            "owner_reason": "owner_missing_from_config",
        }

    healthy, health_reason = is_worker_healthy(owner_worker, cfg)
    installed = installed_models_for_worker(owner_worker, cfg)
    owner_has_model = True if req.model is None else (req.model in installed)

    owner_admissible = False
    owner_reason = health_reason if not healthy else "owner_not_admissible"

    if healthy:
        worker_ok, worker_reason = worker_admission_allowed(cfg, owner_worker, req.role)
        if not worker_ok:
            owner_reason = worker_reason
        else:
            lane_reasons: list[str] = []
            lane_found = False
            for gpu_lane in cfg["workers"][owner_worker]["gpu_routes"].keys():
                models = select_preferred_models(cfg, owner_worker, gpu_lane, req.role, req.model, req.allow_fallback, req=req)
                if not models:
                    lane_reasons.append("no_model_preferences")
                    continue
                for model in models:
                    if model not in installed:
                        lane_reasons.append(f"missing_model:{model}")
                        continue
                    lane_found = True
                    lane_ok, lane_reason = lane_admission_allowed(
                        cfg,
                        owner_worker,
                        gpu_lane,
                        req.role,
                        model,
                        req.allow_burst,
                    )
                    if lane_ok:
                        owner_admissible = True
                        owner_reason = "ok"
                        break
                    lane_reasons.append(lane_reason)
                if owner_admissible:
                    break
            if not owner_admissible and owner_reason == "owner_not_admissible":
                if req.model and not owner_has_model:
                    owner_reason = "requested_model_missing"
                elif lane_reasons:
                    owner_reason = lane_reasons[0]
                elif not lane_found:
                    owner_reason = "no_matching_lane_model"

    return {
        "owner_worker": owner_worker,
        "owner_known": True,
        "owner_healthy": healthy,
        "owner_admissible": owner_admissible,
        "owner_has_model": owner_has_model,
        "owner_reason": owner_reason,
    }

def alternate_worker_allowed(cfg: dict[str, Any], req: ExecRequest, candidate_worker: str) -> bool:
    if req.worker:
        return candidate_worker == req.worker

    owner_worker = role_owner(req.role)
    if owner_worker is None:
        return True

    if candidate_worker == owner_worker:
        return True

    owner_state = evaluate_owner_state(cfg, req, owner_worker)
    if not owner_state["owner_healthy"]:
        return True
    if not owner_state["owner_admissible"]:
        return True

    return False

def classify_route(
    cfg: dict[str, Any],
    req: ExecRequest,
    initial_choice: dict[str, Any],
    final_choice: dict[str, Any],
    retry_events: list[dict[str, Any]],
) -> dict[str, Any]:
    owner_worker = role_owner(req.role)
    owner_state = evaluate_owner_state(cfg, req, owner_worker)
    selected_worker = final_choice["worker"]
    fallback_used = (
        selected_worker != initial_choice["worker"]
        or bool(retry_events)
        or bool(final_choice.get("burst_mode", False))
    )

    if req.worker:
        route_class = "manual_override"
        ownership_ok = owner_worker is None or selected_worker == owner_worker
        violation_reason = "manual_worker_override"
    elif owner_worker is None:
        route_class = "unowned"
        ownership_ok = True
        violation_reason = "no_owner_defined"
    elif selected_worker == owner_worker:
        route_class = "primary"
        ownership_ok = True
        violation_reason = "owner_selected"
    elif req.allow_fallback and (not owner_state["owner_healthy"] or not owner_state["owner_admissible"]):
        route_class = "fallback"
        ownership_ok = True
        if not owner_state["owner_healthy"]:
            violation_reason = f"owner_unhealthy:{owner_state['owner_reason']}"
        else:
            violation_reason = f"owner_inadmissible:{owner_state['owner_reason']}"
    else:
        route_class = "violation"
        ownership_ok = False
        if owner_state["owner_healthy"] and owner_state["owner_admissible"]:
            violation_reason = "selected_non_owner_while_owner_admissible"
        elif owner_state["owner_healthy"]:
            violation_reason = "selected_non_owner_while_owner_healthy"
        else:
            violation_reason = "selected_non_owner"

    return {
        "owner_worker": owner_worker,
        "selected_worker": selected_worker,
        "selected_model": final_choice["model"],
        "fallback_used": fallback_used,
        "fallback_allowed": bool(req.allow_fallback),
        "ownership_ok": ownership_ok,
        "route_class": route_class,
        "violation_reason": violation_reason,
        **owner_state,
    }


def read_recent_routing_audit(limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    items = list(RECENT_ROUTING_AUDIT)[-limit:]
    return list(reversed(items))


def summarize_routing_audit(window: int) -> dict[str, Any]:
    items = list(RECENT_ROUTING_AUDIT)[-window:] if window > 0 else list(RECENT_ROUTING_AUDIT)
    per_role: dict[str, dict[str, int]] = defaultdict(
        lambda: {"primary": 0, "fallback": 0, "violation": 0, "manual_override": 0}
    )
    last_violation_ts = None

    primary = fallback = violations = manual_override = 0

    for item in items:
        role = str(item.get("role", "unknown"))
        route_class = str(item.get("route_class", "unknown"))
        if route_class == "primary":
            primary += 1
            per_role[role]["primary"] += 1
        elif route_class == "fallback":
            fallback += 1
            per_role[role]["fallback"] += 1
        elif route_class == "violation":
            violations += 1
            per_role[role]["violation"] += 1
            ts = item.get("ts")
            if isinstance(ts, int):
                last_violation_ts = ts if last_violation_ts is None else max(last_violation_ts, ts)
        elif route_class == "manual_override":
            manual_override += 1
            per_role[role]["manual_override"] += 1

    return {
        "ok": violations == 0,
        "window_count": len(items),
        "primaries": primary,
        "fallbacks": fallback,
        "violations": violations,
        "manual_overrides": manual_override,
        "last_violation_ts": last_violation_ts,
        "by_role": dict(per_role),
    }


async def claim_alternate_candidate(
    cfg: dict[str, Any],
    req: ExecRequest,
    excluded_workers: set[str],
    preferred_model: str | None = None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if req.worker:
        return None, []

    shortlist = shortlist_candidates(cfg, req, excluded_workers, preferred_model=preferred_model)

    for item in shortlist:
        if item.get("reason"):
            continue
        if not alternate_worker_allowed(cfg, req, item["worker"]):
            continue
        return {
            "worker": item["worker"],
            "worker_url": item["worker_url"],
            "gpu_lane": item["gpu_lane"],
            "gpu_label": item["gpu_label"],
            "model": item["model"],
            "burst_mode": item["burst_mode"],
        }, shortlist

    return None, shortlist


async def switch_active_allocation(previous: dict[str, Any], new_choice: dict[str, Any]) -> None:
    async with ACTIVE_LOCK:
        decrement_active(previous["worker"], previous["gpu_lane"], previous["model"])
        increment_active(new_choice["worker"], new_choice["gpu_lane"], new_choice["model"])


async def call_generate(worker_url: str, req: ExecRequest, model: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.post(
            f"{worker_url}/api/generate",
            json={"model": model, "prompt": req.prompt, "stream": req.stream},
        )
        resp.raise_for_status()
        return resp.json()

async def call_generate_with_retry(
    cfg: dict[str, Any],
    chosen: dict[str, Any],
    req: ExecRequest,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    retry = get_retry_policy()
    same_worker_retries = max(0, int(retry.get("same_worker_retries", 1)))
    alternate_worker_retries = max(0, int(retry.get("alternate_worker_retries", 1)))

    current_choice = dict(chosen)
    retry_events: list[dict[str, Any]] = []
    attempted_workers = {current_choice["worker"]}
    preferred_model = current_choice["model"]
    last_exc: Exception | None = None

    for attempt in range(same_worker_retries + 1):
        try:
            data = await call_generate(current_choice["worker_url"], req, current_choice["model"])
            return current_choice, data, retry_events
        except Exception as exc:
            last_exc = exc
            record_failure(current_choice["worker"], type(exc).__name__, cfg)
            record_retry_event(retry_events, current_choice, exc, "same_worker", attempt)

            if not is_retryable_exception(cfg, exc):
                raise

            if attempt >= same_worker_retries:
                break

            skip_retry, reason = should_skip_same_worker_retry(cfg, current_choice["worker"], exc)
            if skip_retry:
                record_retry_note(retry_events, current_choice, "same_worker_skip", reason)
                break

    for alt_attempt in range(alternate_worker_retries):
        next_choice, shortlist = await claim_alternate_candidate(
            cfg,
            req,
            attempted_workers,
            preferred_model=preferred_model,
        )
        record_retry_note(
            retry_events,
            current_choice,
            "alternate_shortlist",
            "evaluated alternate candidates",
            shortlist=shortlist[:ALTERNATE_DEBUG_LIMIT],
            preferred_model=preferred_model,
        )

        if not next_choice:
            break

        await switch_active_allocation(current_choice, next_choice)
        current_choice = dict(next_choice)
        attempted_workers.add(current_choice["worker"])
        record_retry_note(
            retry_events,
            current_choice,
            "alternate_claim",
            f"claimed alternate worker #{alt_attempt + 1}",
            preferred_model=preferred_model,
        )

        try:
            data = await call_generate(current_choice["worker_url"], req, current_choice["model"])
            return current_choice, data, retry_events
        except Exception as exc:
            last_exc = exc
            record_failure(current_choice["worker"], type(exc).__name__, cfg)
            record_retry_event(retry_events, current_choice, exc, "alternate_worker", alt_attempt)

            if not is_retryable_exception(cfg, exc):
                raise

    if last_exc is not None:
        raise last_exc

    raise HTTPException(
        status_code=503,
        detail={"message": "retry routing exhausted with no alternate worker available"},
    )

async def call_embed(worker_url: str, req: ExecRequest, model: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.post(
            f"{worker_url}/api/embed",
            json={"model": model, "input": req.prompt}
        )
        resp.raise_for_status()
        return resp.json()

async def execute_quarantine_worker(worker_name: str, seconds: int, reason: str) -> dict[str, Any]:
    cfg = load_config()
    if worker_name not in cfg["workers"]:
        raise HTTPException(status_code=404, detail={"message": "unknown worker"})

    async def do_execute() -> dict[str, Any]:
        penalty = {
            "reason": reason,
            "until": _now() + max(60, seconds),
            "ts": _now(),
            "quarantined": True,
            "failure_count_window": failure_window_count(worker_name, 3600),
        }
        PENALTY_BOX[worker_name] = penalty
        update_remediation_quarantine(worker_name, True, reason)
        update_watch_state_quarantine(worker_name, True)
        return {"worker": worker_name, "penalty": penalty}

    async def do_verify(execution_result: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        status = worker_status(worker_name)
        remediation = remediation_entry(worker_name)
        ok = status.get("quarantined") is True and remediation.get("quarantined") is True
        return ok, {
            "watch_quarantined": status.get("quarantined"),
            "watch_eligible": status.get("eligible"),
            "remediation_quarantined": remediation.get("quarantined"),
        }

    async def do_rollback(backup_record: dict[str, Any], execution_result: dict[str, Any]) -> dict[str, Any]:
        remediation_backup = next(
            Path(item["dest"])
            for item in backup_record["artifacts"]
            if item["source"] == str(REMEDIATION_STATE_PATH)
        )
        watch_backup = next(
            Path(item["dest"])
            for item in backup_record["artifacts"]
            if item["source"] == str(WATCH_STATE_PATH)
        )

        shutil.copy2(remediation_backup, REMEDIATION_STATE_PATH)
        shutil.copy2(watch_backup, WATCH_STATE_PATH)
        PENALTY_BOX.pop(worker_name, None)

        return {
            "restored_files": [str(REMEDIATION_STATE_PATH), str(WATCH_STATE_PATH)],
            "cleared_penalty": True,
        }

    return await execute_with_enforcement(
        action_name="quarantine_worker",
        target=worker_name,
        service="fleet_runtime_state",
        backup_sources=[REMEDIATION_STATE_PATH, WATCH_STATE_PATH],
        execute_fn=do_execute,
        verify_fn=do_verify,
        rollback_fn=do_rollback,
        metadata={"reason": reason, "seconds": seconds},
        require_backup=True,
    )


async def execute_unquarantine_worker(worker_name: str) -> dict[str, Any]:
    cfg = load_config()
    if worker_name not in cfg["workers"]:
        raise HTTPException(status_code=404, detail={"message": "unknown worker"})

    async def do_execute() -> dict[str, Any]:
        removed_penalty = PENALTY_BOX.pop(worker_name, None)
        FAILURE_HISTORY.pop(worker_name, None)
        update_remediation_quarantine(worker_name, False, "manual_release")
        update_watch_state_quarantine(worker_name, False)
        return {"worker": worker_name, "removed_penalty": removed_penalty is not None}

    async def do_verify(execution_result: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        status = worker_status(worker_name)
        remediation = remediation_entry(worker_name)
        ok = status.get("quarantined") is False and remediation.get("quarantined") is False
        return ok, {
            "watch_quarantined": status.get("quarantined"),
            "watch_eligible": status.get("eligible"),
            "remediation_quarantined": remediation.get("quarantined"),
        }

    async def do_rollback(backup_record: dict[str, Any], execution_result: dict[str, Any]) -> dict[str, Any]:
        remediation_backup = next(
            Path(item["dest"])
            for item in backup_record["artifacts"]
            if item["source"] == str(REMEDIATION_STATE_PATH)
        )
        watch_backup = next(
            Path(item["dest"])
            for item in backup_record["artifacts"]
            if item["source"] == str(WATCH_STATE_PATH)
        )

        shutil.copy2(remediation_backup, REMEDIATION_STATE_PATH)
        shutil.copy2(watch_backup, WATCH_STATE_PATH)

        return {
            "restored_files": [str(REMEDIATION_STATE_PATH), str(WATCH_STATE_PATH)],
            "cleared_penalty": False,
        }

    return await execute_with_enforcement(
        action_name="unquarantine_worker",
        target=worker_name,
        service="fleet_runtime_state",
        backup_sources=[REMEDIATION_STATE_PATH, WATCH_STATE_PATH],
        execute_fn=do_execute,
        verify_fn=do_verify,
        rollback_fn=do_rollback,
        metadata={"reason": "manual_release"},
        require_backup=True,
    )

app = FastAPI(title="Spot Core Control Plane", version="final-v6-routing-audit")

@app.post("/admin/validate")
async def admin_validate(payload: AdminValidateRequest):
    require_admin_token(payload.model_dump())
    cfg = load_config()

    worker = payload.worker
    commands = payload.commands

    if not isinstance(commands, list) or not commands:
        raise HTTPException(
            status_code=400,
            detail={"message": "commands must be a non-empty list"},
        )

    host = worker_host(worker, cfg)

    allowed_prefixes = [
        "test ",
        "cat ",
        "ls ",
        "systemctl is-active ",
        "systemctl status ",
        "systemd-analyze verify ",
        "bash -n ",
        "python3 -m py_compile ",
        "docker compose config",
        "docker compose ps",
        "jq ",
    ]

    results: list[dict[str, Any]] = []

    for cmd in commands:
        if not isinstance(cmd, str) or not cmd.strip():
            results.append(
                {
                    "ok": False,
                    "command": cmd,
                    "error": "invalid_command",
                }
            )
            continue

        if not any(cmd.startswith(prefix) for prefix in allowed_prefixes):
            results.append(
                {
                    "ok": False,
                    "command": cmd,
                    "error": "command_not_allowed",
                }
            )
            continue

        res = await run_ssh_command(host, cmd)
        results.append(
            {
                "ok": res["returncode"] == 0,
                "command": cmd,
                "result": res,
            }
        )

    overall_ok = all(item.get("ok") is True for item in results)

    return {
        "ok": overall_ok,
        "worker": worker,
        "results": results,
    }

@app.post("/admin/restart-service")
async def admin_restart_service(payload: AdminRestartServiceRequest):
    require_admin_token(payload.model_dump())
    cfg = load_config()

    worker = payload.worker
    service = payload.service

    if service not in ALLOWED_REMOTE_SERVICES:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "service not allowed",
                "worker": worker,
                "service": service,
            },
        )

    host = worker_host(worker, cfg)

    async def execute():
        before = await systemctl_show_service(host, service)
        restart = await run_ssh_command(host, f"sudo systemctl restart {shlex.quote(service)}")
        after = await systemctl_show_service(host, service)

        return {
            "worker": worker,
            "host": host,
            "service": service,
            "before": before,
            "restart": restart,
            "after": after,
        }

    async def verify(result):
        restart_ok = result.get("restart", {}).get("returncode") == 0
        observed_ok, details = service_restart_verified(
            result.get("before", {}),
            result.get("after", {}),
        )
        details["restart_returncode"] = result.get("restart", {}).get("returncode")
        details["restart_stderr"] = result.get("restart", {}).get("stderr", "")
        return restart_ok and observed_ok, details

    async def rollback(backup, result):
        return {
            "ok": False,
            "rollback": "not_applicable_for_service_restart",
            "backup_path": backup.get("backup_dir") if backup else None,
        }

    return await execute_with_enforcement(
        action_name="restart_service",
        target=worker,
        service=service,
        backup_sources=[],
        execute_fn=execute,
        verify_fn=verify,
        rollback_fn=rollback,
        metadata={
            "worker": worker,
            "service": service,
            "host": host,
        },
        require_backup=False,
    )

@app.post("/admin/read-file")
async def admin_read_file(payload: AdminReadFileRequest):
    require_admin_token(payload.model_dump())
    cfg = load_config()

    worker = payload.worker
    path = Path(payload.path)

    host = worker_host(worker, cfg)
    result = await run_ssh_command(host, f"cat {shlex.quote(str(path))}")

    if result["returncode"] != 0:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "failed to read remote file",
                "worker": worker,
                "path": str(path),
                "ssh": result,
            },
        )

    return {
        "ok": True,
        "worker": worker,
        "path": str(path),
        "content": result["stdout"],
    }

@app.post("/admin/write-file")
async def admin_write_file(payload: AdminWriteFileRequest):
    require_admin_token(payload.model_dump())
    cfg = load_config()

    worker = payload.worker
    path = Path(payload.path)
    content = payload.content

    host = worker_host(worker, cfg)

    tmp_path = f"/tmp/spot_write_{int(time.time())}.tmp"

    exists_check = await run_ssh_command(host, f"test -e {shlex.quote(str(path))}")
    preexisting_file = exists_check["returncode"] == 0

    async def execute():
        write_tmp = await run_ssh_command(
            host,
            f"printf %s {shlex.quote(content)} > {shlex.quote(tmp_path)}"
        )
        if write_tmp["returncode"] != 0:
            return {
                "ok": False,
                "stage": "write_tmp",
                "tmp_path": tmp_path,
                "ssh": write_tmp,
            }

        move_into_place = await run_ssh_command(
            host,
            f"mv {shlex.quote(tmp_path)} {shlex.quote(str(path))}"
        )

        return {
            "ok": move_into_place["returncode"] == 0,
            "stage": "move_into_place",
            "tmp_path": tmp_path,
            "ssh": move_into_place,
        }

    async def verify(result):
        check = await run_ssh_command(host, f"test -f {shlex.quote(str(path))}")
        return (
            check["returncode"] == 0,
            {
                "exists": check["returncode"] == 0,
                "ssh": check,
                "preexisting_file": preexisting_file,
            },
        )

    async def rollback(backup, result):
        if not preexisting_file:
            delete_new = await run_ssh_command(
                host,
                f"rm -f {shlex.quote(str(path))}"
            )
            return {
                "ok": delete_new["returncode"] == 0,
                "rollback": "removed_new_file",
                "ssh": delete_new,
            }

        artifact = next(
            (a for a in backup["artifacts"] if Path(a["source"]) == path),
            None
        )

        if not artifact:
            raise RuntimeError(f"No backup artifact found for {path}")

        backup_file = artifact["dest"]

        restore = await run_ssh_command(
            host,
            f"cp {shlex.quote(backup_file)} {shlex.quote(str(path))}"
        )

        return {
            "ok": restore["returncode"] == 0,
            "rollback": "restored_prior_file",
            "ssh": restore,
        }

    return await execute_with_enforcement(
        action_name="write_file",
        target=worker,
        service="filesystem",
        backup_sources=[path] if preexisting_file else [],
        execute_fn=execute,
        verify_fn=verify,
        rollback_fn=rollback,
        metadata={
            "path": str(path),
            "host": host,
            "preexisting_file": preexisting_file,
        },
        require_backup=preexisting_file,
    )

@app.post("/admin/read-local-file")
async def admin_read_local_file(payload: AdminReadLocalFileRequest):
    require_admin_token(payload.model_dump())

    path = resolve_local_path(payload.path)

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "failed to read local file",
                "path": str(path),
                "error": repr(exc),
            },
        ) from exc

    return {
        "ok": True,
        "path": str(path),
        "content": content,
    }


@app.post("/admin/write-local-file")
async def admin_write_local_file(payload: AdminWriteLocalFileRequest):
    require_admin_token(payload.model_dump())

    path = resolve_local_path(payload.path)
    content = payload.content
    preexisting_file = path.exists()

    async def execute():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {
            "ok": True,
            "path": str(path),
            "bytes_written": len(content.encode("utf-8")),
            "preexisting_file": preexisting_file,
        }

    async def verify(result):
        exists = path.is_file()
        return (
            exists,
            {
                "exists": exists,
                "preexisting_file": preexisting_file,
                "size": path.stat().st_size if exists else None,
            },
        )

    async def rollback(backup, result):
        if not preexisting_file:
            try:
                path.unlink(missing_ok=True)
            except Exception as exc:
                return {
                    "ok": False,
                    "rollback": "remove_new_local_file_failed",
                    "error": repr(exc),
                }
            return {
                "ok": True,
                "rollback": "removed_new_local_file",
                "path": str(path),
            }

        artifact = next(
            (a for a in backup["artifacts"] if Path(a["source"]) == path),
            None,
        )
        if not artifact:
            raise RuntimeError(f"No backup artifact found for {path}")

        backup_file = Path(artifact["dest"])
        shutil.copy2(backup_file, path)

        return {
            "ok": True,
            "rollback": "restored_prior_local_file",
            "path": str(path),
            "backup_file": str(backup_file),
        }

    return await execute_with_enforcement(
        action_name="write_local_file",
        target="spot-core",
        service="filesystem_local",
        backup_sources=[path] if preexisting_file else [],
        execute_fn=execute,
        verify_fn=verify,
        rollback_fn=rollback,
        metadata={
            "path": str(path),
            "preexisting_file": preexisting_file,
        },
        require_backup=preexisting_file,
    )

@app.post("/admin/operator-command")
async def admin_operator_command(payload: AdminOperatorCommandRequest):
    require_admin_token(payload.model_dump())

    spec = OPERATOR_COMMANDS.get(payload.command)
    if not spec:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "operator command not allowed",
                "command": payload.command,
                "allowed": sorted(OPERATOR_COMMANDS.keys()),
            },
        )

    async def run_local_command() -> dict[str, Any]:
        cmd_env = os.environ.copy()
        cmd_env.update(spec.get("env", {}))

        proc = await asyncio.create_subprocess_exec(
            *spec["argv"],
            cwd=spec["cwd"],
            env=cmd_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=int(spec.get("timeout", 120)),
            )
        except asyncio.TimeoutError:
            proc.kill()
            stdout, stderr = await proc.communicate()
            return {
                "ok": False,
                "command": payload.command,
                "argv": spec["argv"],
                "cwd": spec["cwd"],
                "returncode": None,
                "timed_out": True,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }

        return {
            "ok": proc.returncode == 0,
            "command": payload.command,
            "argv": spec["argv"],
            "cwd": spec["cwd"],
            "returncode": proc.returncode,
            "timed_out": False,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
        }

    async def verify(result: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        return result.get("ok") is True, {
            "returncode": result.get("returncode"),
            "timed_out": result.get("timed_out"),
            "command": result.get("command"),
        }

    return await execute_with_enforcement(
        action_name="operator_command",
        target="spot-core",
        service="operator",
        backup_sources=[],
        execute_fn=run_local_command,
        verify_fn=verify,
        rollback_fn=None,
        metadata={
            "command": payload.command,
            "argv": spec["argv"],
            "cwd": spec["cwd"],
            "mutating": bool(spec.get("mutating", False)),
        },
        require_backup=False,
    )


@app.post("/admin/quarantine")
async def admin_quarantine_worker(payload: AdminQuarantineRequest):
    require_admin_token(payload.model_dump())
    return await execute_quarantine_worker(
        worker_name=payload.worker,
        seconds=payload.seconds,
        reason=payload.reason,
    )

@app.post("/admin/release")
async def admin_release_worker(payload: AdminReleaseRequest):
    require_admin_token(payload.model_dump())
    return await execute_unquarantine_worker(worker_name=payload.worker)

@app.on_event("startup")
async def startup_event() -> None:
    load_config()
    seed_warm_models()
    seed_routing_audit()
    seed_recent_decisions()
    seed_latency_history()

@app.head("/")
async def dashboard_head() -> dict[str, Any]:
    return {}

@app.get("/", response_class=HTMLResponse)
async def dashboard() -> str:
    health = {"ok": True, "uptime_sec": _now() - APP_START_TS}
    routing_state = await routing()
    fleet = await fleet_ping()
    latency = await stats_latency()
    audit = await stats_routing_audit(limit=200)
    decisions = await stats_recent_decisions(limit=5)

    def esc(value: Any) -> str:
        text = "" if value is None else str(value)
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    worker_rows = []
    for name, item in fleet.items():
        lat = item.get("latency") or {}
        status = "OK" if item.get("ok") else "BAD"
        worker_rows.append(
            "<tr>"
            f"<td>{esc(name)}</td>"
            f"<td class='{status.lower()}'>{esc(status)}</td>"
            f"<td>{esc(item.get('primary_role'))}</td>"
            f"<td>{esc(item.get('reason'))}</td>"
            f"<td>{esc(item.get('quarantined'))}</td>"
            f"<td>{esc(item.get('degraded'))}</td>"
            f"<td>{esc(lat.get('p50_total_ms'))}</td>"
            f"<td>{esc(lat.get('avg_tok_per_sec'))}</td>"
            "</tr>"
        )

    owner_rows = []
    role_owners = routing_state.get("role_owners") or {}
    for role, worker in role_owners.items():
        owner_rows.append(
            "<tr>"
            f"<td>{esc(role)}</td>"
            f"<td>{esc(worker)}</td>"
            "</tr>"
        )

    decision_rows = []
    for item in decisions.get("items", []):
        decision_rows.append(
            "<tr>"
            f"<td>{esc(item.get('ts'))}</td>"
            f"<td>{esc(item.get('role'))}</td>"
            f"<td>{esc(item.get('worker'))}</td>"
            f"<td>{esc(item.get('model'))}</td>"
            f"<td>{esc(item.get('status'))}</td>"
            "</tr>"
        )

    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="30">
  <title>Spot Core</title>
  <style>
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0b1020;
      color: #e8edf7;
    }}
    header {{
      padding: 22px 28px;
      background: #111936;
      border-bottom: 1px solid #263252;
    }}
    h1 {{
      margin: 0;
      font-size: 28px;
    }}
    main {{
      padding: 24px 28px;
      display: grid;
      gap: 20px;
    }}
    section {{
      background: #111936;
      border: 1px solid #263252;
      border-radius: 12px;
      padding: 18px;
    }}
    h2 {{
      margin-top: 0;
      font-size: 18px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      padding: 9px 10px;
      border-bottom: 1px solid #263252;
      text-align: left;
      font-size: 14px;
    }}
    th {{
      color: #9fb3d9;
      font-weight: 600;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
    }}
    .card {{
      background: #0b1020;
      border: 1px solid #263252;
      border-radius: 10px;
      padding: 14px;
    }}
    .label {{
      color: #9fb3d9;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .08em;
    }}
    .value {{
      margin-top: 6px;
      font-size: 22px;
      font-weight: 700;
    }}
    .ok {{
      color: #74e39a;
      font-weight: 700;
    }}
    .bad {{
      color: #ff7676;
      font-weight: 700;
    }}
    a {{
      color: #8ab4ff;
    }}
    footer {{
      color: #9fb3d9;
      font-size: 12px;
      padding: 0 28px 24px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Spot Core Operator Dashboard</h1>
    <div>Read-only fleet status · auto-refresh 30s</div>
  </header>

  <main>
    <section>
      <div class="cards">
        <div class="card">
          <div class="label">Core</div>
          <div class="value">{esc("OK" if health.get("ok") else "BAD")}</div>
        </div>
        <div class="card">
          <div class="label">Uptime seconds</div>
          <div class="value">{esc(health.get("uptime_sec"))}</div>
        </div>
        <div class="card">
          <div class="label">Workers</div>
          <div class="value">{esc(len(fleet))}</div>
        </div>
        <div class="card">
          <div class="label">Routing violations</div>
          <div class="value">{esc(audit.get("violations"))}</div>
        </div>
        <div class="card">
          <div class="label">Fallbacks</div>
          <div class="value">{esc(audit.get("fallbacks"))}</div>
        </div>
      </div>
    </section>

    <section>
      <h2>Fleet</h2>
      <table>
        <tr>
          <th>Worker</th>
          <th>Status</th>
          <th>Role</th>
          <th>Reason</th>
          <th>Quarantined</th>
          <th>Degraded</th>
          <th>P50 ms</th>
          <th>Tok/sec</th>
        </tr>
        {''.join(worker_rows)}
      </table>
    </section>

    <section>
      <h2>Role owners</h2>
      <table>
        <tr><th>Role</th><th>Owner</th></tr>
        {''.join(owner_rows)}
      </table>
    </section>

    <section>
      <h2>Recent decisions</h2>
      <table>
        <tr>
          <th>TS</th>
          <th>Role</th>
          <th>Worker</th>
          <th>Model</th>
          <th>Status</th>
        </tr>
        {''.join(decision_rows)}
      </table>
    </section>

    <section>
      <h2>Raw endpoints</h2>
      <p>
        <a href="/health">/health</a> ·
        <a href="/routing">/routing</a> ·
        <a href="/fleet/ping">/fleet/ping</a> ·
        <a href="/stats/latency">/stats/latency</a> ·
        <a href="/stats/routing-audit">/stats/routing-audit</a>
      </p>
    </section>
  </main>

  <footer>
    Spot Core read-only dashboard. No admin actions exposed here.
  </footer>
</body>
</html>
"""

@app.get("/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "uptime_sec": _now() - APP_START_TS}


@app.get("/routing")
async def routing() -> dict[str, Any]:
    cfg = load_config()
    return {
        "ok": True,
        "config_path": str(CONFIG_PATH),
        "watch_state_path": str(WATCH_STATE_PATH),
        "routing_audit_path": str(ROUTING_AUDIT_PATH),
        "active_requests": ACTIVE_REQUESTS,
        "active_gpu_requests": ACTIVE_GPU_REQUESTS,
        "active_model_requests": ACTIVE_MODEL_REQUESTS,
        "waiting_requests": WAITING_REQUESTS,
        "penalty_box": PENALTY_BOX,
        "warm_models": WARM_MODELS,
        "role_priority": cfg.get("role_priority", {}),
        "priority_order": cfg.get("priority_order", []),
        "queue_policy": cfg.get("queue_policy", {}),
        "retry_policy": cfg.get("retry_policy", {}),
        "burst_policy": {k: v.get("burst_gpu_routes", {}) for k, v in cfg.get("workers", {}).items()},
        "role_owners": ROLE_OWNERS,
    }


@app.get("/fleet/ping")
async def fleet_ping() -> dict[str, Any]:
    cfg = load_config()
    out: dict[str, Any] = {}
    for name, worker_cfg in cfg["workers"].items():
        status = worker_status(name)
        healthy, reason = is_worker_healthy(name, cfg)
        remediation = remediation_entry(name)
        out[name] = {
            "ok": healthy,
            "reason": reason,
            "base_url": worker_cfg["base_url"],
            "primary_role": worker_cfg.get("primary_role"),
            "secondary_roles": worker_cfg.get("secondary_roles", []),
            "installed_models": sorted(installed_models_for_worker(name, cfg)),
            "eligible": healthy,
            "quarantined": bool(status.get("quarantined", False)),
            "alerts": status.get("alerts", []),
            "running_jobs": scheduler_running_jobs(name),
            "watcher_running_jobs": worker_metric_int(status, "running_jobs", 0),
            "running_gpu_jobs": ACTIVE_GPU_REQUESTS.get(name, {}),
            "warm_models": WARM_MODELS.get(name, {}),
            "latency": worker_latency_summary(name),
            "penalty": current_penalty(name),
            "degraded": bool(remediation.get("degraded", False)),
            "degraded_reason": remediation.get("degraded_reason"),
            "fallback_count_window": remediation.get("fallback_count_window", 0),
        }
    return out


@app.get("/stats/latency")
async def stats_latency() -> dict[str, Any]:
    cfg = load_config()
    return {name: worker_latency_summary(name) for name in cfg["workers"].keys()}


@app.get("/operator/readiness")
async def operator_readiness() -> dict[str, Any]:
    health_data = await health()
    fleet = await fleet_ping()
    audit = await stats_routing_audit(limit=200)
    latency = await stats_latency()

    workers = []
    worker_failures = 0
    quarantined = 0
    degraded = 0
    slow_workers = []

    for name, item in fleet.items():
        lat = latency.get(name, {}) or {}
        p50_ms = lat.get("p50_total_ms")
        avg_ms = lat.get("avg_total_ms")

        worker_ok = bool(item.get("ok"))
        is_quarantined = bool(item.get("quarantined"))
        is_degraded = bool(item.get("degraded"))

        if not worker_ok:
            worker_failures += 1
        if is_quarantined:
            quarantined += 1
        if is_degraded:
            degraded += 1

        if isinstance(p50_ms, (int, float)) and p50_ms >= 5000:
            slow_workers.append(
                {
                    "worker": name,
                    "p50_total_ms": p50_ms,
                    "avg_total_ms": avg_ms,
                    "reason": "p50_latency_ge_5000ms",
                }
            )

        workers.append(
            {
                "worker": name,
                "ok": worker_ok,
                "reason": item.get("reason"),
                "primary_role": item.get("primary_role"),
                "eligible": bool(item.get("eligible")),
                "quarantined": is_quarantined,
                "degraded": is_degraded,
                "degraded_reason": item.get("degraded_reason"),
                "latency": lat,
            }
        )

    routing_ok = bool(audit.get("ok")) and int(audit.get("violations") or 0) == 0
    fleet_ok = worker_failures == 0 and quarantined == 0
    core_ok = bool(health_data.get("ok"))

    status = "ready" if core_ok and routing_ok and fleet_ok else "not_ready"
    if slow_workers and status == "ready":
        status = "ready_with_warnings"

    return {
        "ok": status in {"ready", "ready_with_warnings"},
        "status": status,
        "ts": _now(),
        "core": {
            "ok": core_ok,
            "uptime_sec": health_data.get("uptime_sec"),
        },
        "routing": {
            "ok": routing_ok,
            "window_count": audit.get("window_count"),
            "primaries": audit.get("primaries"),
            "fallbacks": audit.get("fallbacks"),
            "violations": audit.get("violations"),
            "manual_overrides": audit.get("manual_overrides"),
            "last_violation_ts": audit.get("last_violation_ts"),
        },
        "fleet": {
            "worker_count": len(workers),
            "worker_failures": worker_failures,
            "quarantined": quarantined,
            "degraded": degraded,
            "slow_workers": slow_workers,
            "workers": workers,
        },
        "operator": {
            "readiness_source": "live",
            "readiness_endpoint": "/operator/readiness",
        },
    }


@app.get("/stats/recent-decisions")
async def stats_recent_decisions(limit: int = 25) -> dict[str, Any]:
    items = list(RECENT_DECISIONS)[-max(1, min(limit, 200)):]
    return {"count": len(items), "items": items}


@app.get("/stats/routing-audit")
async def stats_routing_audit(limit: int = 200) -> dict[str, Any]:
    bounded = max(1, min(limit, ROUTING_AUDIT_WINDOW))
    summary = summarize_routing_audit(bounded)
    summary["items"] = read_recent_routing_audit(min(50, bounded))
    summary["role_owners"] = ROLE_OWNERS
    summary["routing_audit_path"] = str(ROUTING_AUDIT_PATH)
    return summary

@app.post("/quarantine/{worker_name}")
async def quarantine_worker(worker_name: str, seconds: int = 1800, reason: str = "manual_quarantine") -> dict[str, Any]:
    result = await execute_quarantine_worker(
        worker_name=worker_name,
        seconds=seconds,
        reason=reason,
    )
    result["deprecated_route"] = True
    result["preferred_route"] = "/admin/quarantine"
    return result


@app.delete("/quarantine/{worker_name}")
async def unquarantine_worker(worker_name: str) -> dict[str, Any]:
    result = await execute_unquarantine_worker(worker_name=worker_name)
    result["deprecated_route"] = True
    result["preferred_route"] = "/admin/release"
    return result


@app.post("/actions/restart-service/{worker_name}/{service_name}")
async def restart_service(worker_name: str, service_name: str) -> dict[str, Any]:
    cfg = load_config()

    if worker_name not in cfg["workers"]:
        raise HTTPException(status_code=404, detail={"message": "unknown worker"})

    if service_name not in ALLOWED_REMOTE_SERVICES:
        raise HTTPException(
            status_code=403,
            detail={"message": "service not allowlisted", "service": service_name},
        )

    host = worker_host(worker_name, cfg)

    async def do_execute() -> dict[str, Any]:
        before = await systemctl_show_service(host, service_name)

        restart = await run_ssh_command(
            host,
            f"sudo systemctl restart {shlex.quote(service_name)}",
        )

        after = await systemctl_show_service(host, service_name)

        return {
            "worker": worker_name,
            "host": host,
            "service": service_name,
            "before": before,
            "restart": restart,
            "after": after,
        }

    async def do_verify(execution_result: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        status = worker_status(worker_name)
        ssh_ok = status.get("ssh_ok")
        service_ok = status.get("service_ok")

        restart_ok = execution_result.get("restart", {}).get("returncode") == 0
        observed_ok, details = service_restart_verified(
            execution_result.get("before", {}),
            execution_result.get("after", {}),
        )

        ok = restart_ok and observed_ok and ssh_ok is not False

        if service_name == "ollama":
            ok = ok and (service_ok is True or details.get("active_after") is True)

        details.update(
            {
                "restart_returncode": execution_result.get("restart", {}).get("returncode"),
                "restart_stderr": execution_result.get("restart", {}).get("stderr", ""),
                "watch_ssh_ok": ssh_ok,
                "watch_service_ok": service_ok,
            }
        )

        return ok, details

    async def do_rollback(backup_record: dict[str, Any], execution_result: dict[str, Any]) -> dict[str, Any]:
        return {
            "rollback": "not_applicable_for_service_restart",
            "backup_path": backup_record.get("backup_dir"),
        }

    result = await execute_with_enforcement(
        action_name="restart_service",
        target=worker_name,
        service=service_name,
        backup_sources=[],
        execute_fn=do_execute,
        verify_fn=do_verify,
        rollback_fn=do_rollback,
        metadata={"worker": worker_name, "host": host, "service": service_name},
        require_backup=False,
    )
    result["deprecated_route"] = True
    result["preferred_route"] = "/admin/restart-service"
    return result

ALLOWED_OPENAI_REVIEW_ROLES = {"general", "coding", "heavy", "reasoning"}
DENIED_OPENAI_REVIEW_ROLES = {"utility", "watcher", "network_ops", "secrets"}


def openai_provider_config(cfg: dict[str, Any]) -> dict[str, Any]:
    return cfg.get("providers", {}).get("openai", {}) or {}


def assert_openai_review_allowed(cfg: dict[str, Any], req: OpenAIReviewRequest) -> tuple[str, str]:
    role = req.role
    if role in DENIED_OPENAI_REVIEW_ROLES or role not in ALLOWED_OPENAI_REVIEW_ROLES:
        raise HTTPException(
            status_code=403,
            detail={"message": f"OpenAI review denied for role: {role}"},
        )

    provider = openai_provider_config(cfg)
    if not provider.get("enabled"):
        raise HTTPException(status_code=503, detail={"message": "OpenAI provider disabled"})

    api_key_env = provider.get("api_key_env", "OPENAI_API_KEY")
    api_key = os.environ.get(api_key_env, "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail={"message": f"missing OpenAI API key env: {api_key_env}"})

    model = req.model or provider.get("default_model") or "gpt-4.1-mini"
    return api_key, model


async def call_openai_review(cfg: dict[str, Any], req: OpenAIReviewRequest) -> dict[str, Any]:
    api_key, model = assert_openai_review_allowed(cfg, req)

    system_prompt = (
        "You are an external Spot project reviewer. "
        "Authority is proposal/review only. "
        "Do not approve execution. Do not claim final authority. "
        "Check project fit, policy fit, backup-first alignment, and worker role ownership. "
        "Return concise PASS/FAIL with reasons."
    )

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": req.prompt},
                ],
            },
        )
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            detail = {
                "message": "OpenAI upstream request failed",
                "status_code": e.response.status_code,
                "response": e.response.text[:4000],
            }

            raise HTTPException(
                status_code=502,
                detail=detail,
            ) from e

        data = resp.json()

    text = ""
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                text += content.get("text", "")

    return {
        "provider": "openai",
        "model": model,
        "authority": "proposal_and_review_only",
        "response": text.strip(),
        "raw": data,
    }


@app.post("/review/openai", response_model=OpenAIReviewResult)
async def openai_review_route(req: OpenAIReviewRequest) -> OpenAIReviewResult:
    cfg = load_config()
    started = _now()
    data = await call_openai_review(cfg, req)

    append_jsonl(
        EXEC_HISTORY_PATH,
        {
            "ts": started,
            "provider": "openai",
            "role_requested": req.role,
            "review_type": req.review_type,
            "model_requested": req.model,
            "model_used": data["model"],
            "authority": data["authority"],
            "prompt_chars": len(req.prompt),
            "response_chars": len(data["response"]),
            "proposal_only": True,
            "external_review": True,
        },
    )

    return OpenAIReviewResult(
        ok=True,
        provider="openai",
        model=data["model"],
        role_requested=req.role,
        review_type=req.review_type,
        authority=data["authority"],
        response=data["response"],
        raw={
            "provider": "openai",
            "model": data["model"],
            "authority": data["authority"],
            "proposal_only": True,
            "external_review": True,
        },
    )


@app.post("/exec", response_model=ExecResult)
async def exec_route(req: ExecRequest) -> ExecResult:
    if req.stream:
        raise HTTPException(status_code=400, detail={"message": "stream=true not supported by this control plane; use stream=false"})

    cfg = load_config()
    async with ACTIVE_LOCK:
        chosen, failures = await choose_worker_and_model(cfg, req)
        increment_active(chosen["worker"], chosen["gpu_lane"], chosen["model"])

    data: dict[str, Any] = {}
    response_text = ""
    started = _now()
    retry_events: list[dict[str, Any]] = []
    initial_choice = dict(chosen)
    final_choice = dict(chosen)
    embed_mode = is_embed_request(req.role, chosen["model"])
    request_tier, premium_reason = classify_request_tier(req)

    try:
        if embed_mode:
            data = await call_embed(chosen["worker_url"], req, chosen["model"])
            response_text = f"Embedding request completed with model {chosen['model']}."
        else:
            final_choice, data, retry_events = await call_generate_with_retry(cfg, chosen, req)
            response_text = data.get("response", "")
    except Exception as exc:
        routing_audit = classify_route(cfg, req, initial_choice, final_choice, retry_events)
        if embed_mode:
            record_failure(chosen["worker"], type(exc).__name__, cfg)

        append_decision(
            {
                "ts": started,
                "worker": final_choice["worker"],
                "gpu_lane": final_choice["gpu_lane"],
                "model": final_choice["model"],
                "role": req.role,
                "priority": priority_of_request(req),
                "burst_mode": final_choice["burst_mode"],
                "status": "error",
                "error": repr(exc),
                "failures_seen": failures[-20:],
                "retry_events": retry_events[-20:],
                "penalty": current_penalty(final_choice["worker"]),
                "request_tier": request_tier,
                "premium_escalated": request_tier in ("premium", "reasoning"),
                "premium_reason": premium_reason,
                "routing_audit": routing_audit,
            }
        )
        append_routing_audit(
            {
                "ts": started,
                "status": "error",
                "role": req.role,
                "priority": priority_of_request(req),
                "requested_model": req.model,
                "initial_worker": initial_choice["worker"],
                "final_worker": final_choice["worker"],
                "final_gpu_lane": final_choice["gpu_lane"],
                "final_gpu_label": final_choice["gpu_label"],
                "final_model": final_choice["model"],
                "retry_events": retry_events[-20:],
                **routing_audit,
            }
        )
        raise
    finally:
        async with ACTIVE_LOCK:
            decrement_active(final_choice["worker"], final_choice["gpu_lane"], final_choice["model"])

    mark_model_warm(final_choice["worker"], final_choice["model"])
    record_latency(final_choice["worker"], final_choice["gpu_lane"], final_choice["model"], req.role, data)
    routing_audit = classify_route(cfg, req, initial_choice, final_choice, retry_events)

    append_jsonl(
        EXEC_HISTORY_PATH,
        {
            "ts": started,
            "worker": final_choice["worker"],
            "worker_url": final_choice["worker_url"],
            "gpu_lane": final_choice["gpu_lane"],
            "gpu_label": final_choice["gpu_label"],
            "role_requested": req.role,
            "priority": priority_of_request(req),
            "model_requested": req.model,
            "model_used": final_choice["model"],
            "burst_mode": final_choice["burst_mode"],
            "prompt_chars": len(req.prompt),
            "response_chars": len(response_text),
            "total_duration": data.get("total_duration"),
            "load_duration": data.get("load_duration"),
            "prompt_eval_count": data.get("prompt_eval_count"),
            "eval_count": data.get("eval_count"),
            "retry_events": retry_events,
            "request_tier": request_tier,
            "premium_escalated": request_tier in ("premium", "reasoning"),
            "premium_reason": premium_reason,
            "routing_audit": routing_audit,
        },
    )

    append_decision(
        {
            "ts": started,
            "worker": final_choice["worker"],
            "gpu_lane": final_choice["gpu_lane"],
            "gpu_label": final_choice["gpu_label"],
            "model": final_choice["model"],
            "role": req.role,
            "priority": priority_of_request(req),
            "burst_mode": final_choice["burst_mode"],
            "status": "ok",
            "failures_seen": failures[-20:],
            "retry_events": retry_events[-20:],
            "latency": worker_latency_summary(final_choice["worker"]),
            "request_tier": request_tier,
            "premium_escalated": request_tier in ("premium", "reasoning"),
            "premium_reason": premium_reason,
            "routing_audit": routing_audit,
        }
    )

    append_routing_audit(
        {
            "ts": started,
            "status": "ok",
            "role": req.role,
            "priority": priority_of_request(req),
            "requested_model": req.model,
            "initial_worker": initial_choice["worker"],
            "final_worker": final_choice["worker"],
            "final_gpu_lane": final_choice["gpu_lane"],
            "final_gpu_label": final_choice["gpu_label"],
            "final_model": final_choice["model"],
            "retry_events": retry_events[-20:],
            **routing_audit,
        }
    )

    return ExecResult(
        ok=True,
        worker=final_choice["worker"],
        worker_url=final_choice["worker_url"],
        gpu_lane=final_choice["gpu_lane"],
        gpu_label=final_choice["gpu_label"],
        role_requested=req.role,
        model=final_choice["model"],
        response=response_text,
        raw=data,
    )
