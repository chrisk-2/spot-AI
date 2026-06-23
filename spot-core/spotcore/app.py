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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
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
REVIEW_LOG_ROOT = ACTION_LOG_ROOT / "reviews"
WORKER_RECOVER_LOG = Path(os.environ.get("SPOTCORE_WORKER_RECOVER_LOG", "/home/ogre/spot-stack/watch/logs/worker-recover.jsonl"))
AUTONOMY_ALLOW_HIGH_RISK = os.environ.get("SPOTCORE_ALLOW_HIGH_RISK_AUTONOMY", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# NFS buffer: W-01 is the local buffer when /mnt/collective is unavailable
NFS_MOUNT = Path("/mnt/collective")
NFS_BUFFER_HOST = os.environ.get("SPOTCORE_NFS_BUFFER_HOST", "192.168.10.10")
NFS_BUFFER_ROOT = os.environ.get("SPOTCORE_NFS_BUFFER_ROOT", "/home/ogre/spot-buffer")
NFS_CHECK_INTERVAL = int(os.environ.get("SPOTCORE_NFS_CHECK_INTERVAL", "10"))

_nfs_last_check: float = 0.0
_nfs_available: bool | None = None


def nfs_available() -> bool:
    """Check if /mnt/collective is mounted and writable. Cached for NFS_CHECK_INTERVAL seconds."""
    global _nfs_last_check, _nfs_available
    now = time.monotonic()
    if _nfs_available is not None and (now - _nfs_last_check) < NFS_CHECK_INTERVAL:
        return _nfs_available
    try:
        sentinel = NFS_MOUNT / ".spot-nfs-check"
        sentinel.touch()
        sentinel.unlink()
        _nfs_available = True
    except Exception:
        _nfs_available = False
    _nfs_last_check = now
    return _nfs_available


def nfs_relative(path: Path) -> str:
    """Return path relative to /mnt/collective, e.g. 'backups/spot-core/...'"""
    return str(path.relative_to(NFS_MOUNT))


async def buffer_append_jsonl(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Append a JSONL line to path on W-01 buffer, mirroring the NFS directory structure."""
    rel = nfs_relative(path)
    remote_path = f"{NFS_BUFFER_ROOT}/{rel}"
    line = json.dumps(payload, sort_keys=True)
    cmd = f"mkdir -p {shlex.quote(str(Path(remote_path).parent))} && printf '%s\\n' {shlex.quote(line)} >> {shlex.quote(remote_path)}"
    result = await run_ssh_command(NFS_BUFFER_HOST, cmd)
    return result


async def buffer_write_file(dest_path: Path, content: str) -> dict[str, Any]:
    """Write a file to W-01 buffer, mirroring the NFS directory structure."""
    rel = nfs_relative(dest_path)
    remote_path = f"{NFS_BUFFER_ROOT}/{rel}"
    cmd = f"mkdir -p {shlex.quote(str(Path(remote_path).parent))} && printf '%s' {shlex.quote(content)} > {shlex.quote(remote_path)}"
    result = await run_ssh_command(NFS_BUFFER_HOST, cmd)
    return result


def append_jsonl_nfs_aware(path: Path, payload: dict[str, Any]) -> None:
    """Append JSONL to an NFS path, falling back to W-01 buffer if NFS is unavailable.
    Falls back synchronously by scheduling the SSH write as a fire-and-forget task."""
    if nfs_available():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")
        return
    # NFS unavailable — schedule async buffer write without blocking
    LOGGER.warning("nfs_unavailable fallback_to_w01 path=%s", path)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_buffer_append_jsonl_task(path, payload))
        else:
            # Sync context: best-effort local fallback to watch/logs
            _sync_local_fallback_append(path, payload)
    except Exception as exc:
        LOGGER.error("nfs_fallback_schedule_failed path=%s error=%r", path, exc)


async def _buffer_append_jsonl_task(path: Path, payload: dict[str, Any]) -> None:
    try:
        result = await buffer_append_jsonl(path, payload)
        if result["returncode"] != 0:
            LOGGER.error("w01_buffer_append_failed path=%s stderr=%s", path, result.get("stderr", ""))
    except Exception as exc:
        LOGGER.error("w01_buffer_append_exception path=%s error=%r", path, exc)


def _sync_local_fallback_append(path: Path, payload: dict[str, Any]) -> None:
    """Last-resort sync fallback: write to local watch/logs/ mirror."""
    try:
        local_mirror = Path("/home/ogre/spot-stack/watch/logs/nfs-fallback") / nfs_relative(path)
        local_mirror.parent.mkdir(parents=True, exist_ok=True)
        with local_mirror.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")
    except Exception as exc:
        LOGGER.error("sync_local_fallback_failed path=%s error=%r", path, exc)


ALLOWED_REMOTE_SERVICES = {"ollama"}
SSH_USER = os.environ.get("SPOTCORE_SSH_USER", "ogre")
SSH_CONNECT_TIMEOUT = int(os.environ.get("SPOTCORE_SSH_CONNECT_TIMEOUT", "10"))
ADMIN_API_TOKEN = os.environ.get("SPOTCORE_ADMIN_API_TOKEN", "").strip()

HTTP_TIMEOUT = float(os.environ.get("SPOTCORE_HTTP_TIMEOUT", "240"))
LATENCY_WINDOW = int(os.environ.get("SPOTCORE_LATENCY_WINDOW", "100"))
DECISION_WINDOW = int(os.environ.get("SPOTCORE_DECISION_WINDOW", "200"))
ALTERNATE_DEBUG_LIMIT = int(os.environ.get("SPOTCORE_ALTERNATE_DEBUG_LIMIT", "10"))
ROUTING_AUDIT_WINDOW = int(os.environ.get("SPOTCORE_ROUTING_AUDIT_WINDOW", "500"))
SPOTCORE_CORS_ORIGINS = [item.strip() for item in os.environ.get("SPOTCORE_CORS_ORIGINS", "*").split(",") if item.strip()]

RUNTIME_QUEUE_RUNS_PATH = Path(os.environ.get("SPOTCORE_RUNTIME_QUEUE_RUNS", "watch/runtime/queue/runs"))
RUNTIME_METRICS_LOG_ROOT = Path(os.environ.get("SPOTCORE_RUNTIME_LOG_ROOT", "/mnt/collective/logs/spot"))

# Spot persistent memory
CHAT_HISTORY_PATH = Path(os.environ.get("SPOTCORE_CHAT_HISTORY", "/home/ogre/spot-stack/watch/logs/spot-chat-history.jsonl"))
CHAT_HISTORY_WINDOW = int(os.environ.get("SPOTCORE_CHAT_HISTORY_WINDOW", "20"))

# Spot Level-1 autonomy allowlist
SPOT_ACTION_ALLOWLIST: dict[str, dict[str, Any]] = {
    "restart_ollama":          {"risk":"low",    "confirm_required":False, "targets":"workers"},
    "quarantine_worker":       {"risk":"medium", "confirm_required":True,  "targets":"workers"},
    "release_worker":          {"risk":"low",    "confirm_required":False, "targets":"workers"},
    "nfs_sync":                {"risk":"low",    "confirm_required":False, "targets":None},
    "wake_worker":             {"risk":"low",    "confirm_required":False, "targets":"workers"},
    # ── Network actions (all require operator EXECUTE confirmation) ───────
    "opn_create_firewall_rule":{"risk":"high",   "confirm_required":True,  "targets":None},
    "opn_delete_firewall_rule":{"risk":"high",   "confirm_required":True,  "targets":None},
    "opn_create_vlan":         {"risk":"high",   "confirm_required":True,  "targets":None},
    "opn_create_alias":        {"risk":"medium", "confirm_required":True,  "targets":None},
    "opn_create_static_lease": {"risk":"medium", "confirm_required":True,  "targets":None},
    "opn_create_dns_override": {"risk":"medium", "confirm_required":True,  "targets":None},
    "opn_delete_dns_override": {"risk":"medium", "confirm_required":True,  "targets":None},
    "unifi_create_network":    {"risk":"high",   "confirm_required":True,  "targets":None},
    "unifi_set_port_profile":  {"risk":"medium", "confirm_required":True,  "targets":None},
    "unifi_block_client":      {"risk":"medium", "confirm_required":True,  "targets":None},
    "unifi_restart_device":    {"risk":"medium", "confirm_required":True,  "targets":None},
}

SPOT_WORKER_MACS: dict[str, str] = {
    "spot-worker-01":"d8:43:ae:a9:c2:4c",
    "spot-worker-02":"d8:cb:8a:3e:94:fa",
    "spot-worker-03":"b4:2e:99:a5:17:ef",
    "spot-worker-04":"d8:43:ae:1f:88:2b",
    "spot-worker-05":"04:d4:c4:54:cd:6f",
    "spot-worker-06":"04:d4:c4:48:43:48",
}

# ── OPNsense / UniFi direct clients ─────────────────────────────────────────
OPNSENSE_HOST   = os.environ.get("OPNSENSE_HOST",   "192.168.1.1")
OPNSENSE_KEY    = os.environ.get("OPNSENSE_KEY",    "")
OPNSENSE_SECRET = os.environ.get("OPNSENSE_SECRET", "")

UNIFI_HOST = os.environ.get("UNIFI_HOST", "192.168.60.20")
UNIFI_PORT = os.environ.get("UNIFI_PORT", "11443")
UNIFI_USER = os.environ.get("UNIFI_USER", "")
UNIFI_PASS = os.environ.get("UNIFI_PASS", "")
UNIFI_SITE = os.environ.get("UNIFI_SITE", "starfleet")


async def _opn(method: str, path: str, *, json_body=None):
    """Call OPNsense API (key/secret auth, LAN direct)."""
    url = f"https://{OPNSENSE_HOST}/api{path}"
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        resp = await client.request(method, url, auth=(OPNSENSE_KEY, OPNSENSE_SECRET), json=json_body)
    try:
        return resp.json()
    except Exception:
        return {"status": resp.status_code, "text": resp.text}


async def _unifi(method: str, path: str, *, json_body=None):
    """Call UniFi OS API (login/cookie/CSRF, LAN direct)."""
    base = f"https://{UNIFI_HOST}:{UNIFI_PORT}"
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        login = await client.post(f"{base}/api/auth/login",
                                  json={"username": UNIFI_USER, "password": UNIFI_PASS})
        csrf = login.headers.get("x-csrf-token", "")
        headers = {"x-csrf-token": csrf} if csrf else {}
        resp = await client.request(method,
                                    f"{base}/proxy/network/api/s/{UNIFI_SITE}{path}",
                                    json=json_body, headers=headers)
    try:
        return resp.json()
    except Exception:
        return {"status": resp.status_code, "text": resp.text}


async def opn_read_firewall_rules() -> dict:
    return await _opn("GET", "/firewall/filter/searchRule")

async def opn_read_aliases() -> dict:
    return await _opn("GET", "/firewall/alias/searchItem")

async def opn_read_vlans() -> dict:
    return await _opn("GET", "/interfaces/vlan/searchItem")

async def opn_read_dhcp_leases() -> dict:
    return await _opn("GET", "/dhcpv4/leases/searchLease")

async def opn_read_dns_overrides() -> dict:
    return await _opn("GET", "/unbound/settings/searchHostOverride")

async def opn_read_interfaces() -> dict:
    return await _opn("GET", "/interfaces/overview/interfacesInfo")

async def opn_read_gateways() -> dict:
    return await _opn("GET", "/routes/gateway/status")

async def opn_read_wireguard() -> dict:
    return await _opn("GET", "/wireguard/service/show")

async def unifi_read_devices() -> dict:
    return await _unifi("GET", "/stat/device")

async def unifi_read_clients() -> dict:
    return await _unifi("GET", "/stat/sta")

async def unifi_read_networks() -> dict:
    return await _unifi("GET", "/rest/networkconf")


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

ROLE = Literal["heavy", "coding", "general", "utility", "watcher", "reasoning", "review"]
ROLE_OWNERS: dict[str, str] = {
    "general": "spot-worker-01",
    "utility": "spot-worker-02",
    "coding": "spot-worker-03",
    "heavy": "spot-worker-04",
    "review": "spot-worker-05",
    "reasoning": "spot-worker-05",  # stand-in: canonical owner is spot-worker-06
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

class LocalReviewRequest(BaseModel):
    prompt: str
    review_type: str = "policy_review"
    worker: str = "spot-worker-05"
    model: str = "qwen2.5-coder:32b"


class LocalReviewResult(BaseModel):
    ok: bool
    reviewer: str
    model: str
    review_type: str
    verdict: str
    execution_allowed: bool
    result_blocked: bool
    authority: str
    confidence: str
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


class ChatRequest(BaseModel):
    message: str
    role: ROLE = "general"
    model: str | None = None
    source: str = "starfleet-ui"
    mode: str = "advisory"


class ChatResult(BaseModel):
    ok: bool
    reply: str
    worker: str | None = None
    model: str | None = None
    role_requested: str
    execution_allowed: bool = False
    mutation_authority: bool = False
    mode: str = "advisory"
    raw: dict[str, Any] = {}


class ChatExecuteRequest(BaseModel):
    token: str
    action: str
    target: str | None = None
    reason: str = ""
    confirmed: bool = False
    params: dict[str, Any] | None = None  # extra params for network actions


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
    "write_ui_file": {
        "argv": ["bash", str(SPOT_WATCH_ROOT / "spot-ops.sh"), "write-ui-file"],
        "cwd": str(SPOT_CORE_ROOT),
        "timeout": 60,
        "mutating": True,
    },
    "ui_build": {
        "argv": ["bash", str(SPOT_WATCH_ROOT / "spot-ops.sh"), "ui-build"],
        "cwd": str(SPOT_CORE_ROOT),
        "timeout": 120,
        "mutating": True,
    },
    "caddy_reload": {
        "argv": ["bash", str(SPOT_WATCH_ROOT / "spot-ops.sh"), "caddy-reload"],
        "cwd": str(SPOT_CORE_ROOT),
        "timeout": 30,
        "mutating": True,
    },
    "readiness": {
        "argv": ["curl", "-fsS", "http://127.0.0.1:8787/operator/readiness"],
        "cwd": str(SPOT_CORE_ROOT),
        "timeout": 120,
        "mutating": False,
    },
    "nfs_sync": {
        "argv": ["bash", str(SPOT_WATCH_ROOT / "spot-nfs-sync.sh")],
        "cwd": str(SPOT_CORE_ROOT),
        "timeout": 120,
        "mutating": True,
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
    """Append JSONL. If path is under /mnt/collective, use NFS-aware writer."""
    try:
        if str(path).startswith("/mnt/collective/"):
            append_jsonl_nfs_aware(path, payload)
            return
    except Exception:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True) + "\n")

def classify_action_risk(action_name: str, target: str, service: str, metadata: dict[str, Any] | None = None) -> str:
    metadata = metadata or {}

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
    dest = dest_root / src.name

    if host:
        check = await run_ssh_command(host, f"test -e {shlex.quote(str(src))}")
        if check["returncode"] != 0:
            raise FileNotFoundError(f"remote backup source missing: {src} on {host}")

        result = await run_ssh_command(host, f"cat {shlex.quote(str(src))}")

        if result["returncode"] != 0:
            raise RuntimeError(f"failed to read remote file: {src} on {host}")

        dest.write_text(result["stdout"], encoding="utf-8")

        return {
            "source": str(src),
            "dest": str(dest),
            "type": "remote_file",
            "host": host,
            "size": len(result["stdout"]),
            "sha256": hashlib.sha256(result["stdout"].encode()).hexdigest(),
        }

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

async def _copy_backup_source_buffered(src: Path, dest_root_rel: str, host: str | None = None) -> dict[str, Any]:
    """Write a backup artifact to W-01 buffer when NFS is unavailable."""
    if host:
        check = await run_ssh_command(host, f"test -e {shlex.quote(str(src))}")
        if check["returncode"] != 0:
            raise FileNotFoundError(f"remote backup source missing: {src} on {host}")
        result = await run_ssh_command(host, f"cat {shlex.quote(str(src))}")
        if result["returncode"] != 0:
            raise RuntimeError(f"failed to read remote file: {src} on {host}")
        content = result["stdout"]
    else:
        if not src.exists():
            raise FileNotFoundError(f"backup source missing: {src}")
        content = src.read_text(encoding="utf-8")

    remote_dest = f"{NFS_BUFFER_ROOT}/{dest_root_rel}/{src.name}"
    write_result = await run_ssh_command(
        NFS_BUFFER_HOST,
        f"mkdir -p {shlex.quote(str(Path(remote_dest).parent))} && printf '%s' {shlex.quote(content)} > {shlex.quote(remote_dest)}"
    )
    if write_result["returncode"] != 0:
        raise RuntimeError(f"w01 buffer write failed: {write_result.get('stderr', '')}")

    return {
        "source": str(src),
        "dest": f"w01:{remote_dest}",
        "type": "buffered_file",
        "buffered": True,
        "buffer_host": NFS_BUFFER_HOST,
        "size": len(content),
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
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
    rel_path = f"backups/{target}/{service}/{timestamp}-{unique_suffix}"
    host = metadata.get("host") if metadata else None
    artifacts: list[dict[str, Any]] = []

    if nfs_available():
        backup_dir = BACKUP_ROOT_PATH / target / service / f"{timestamp}-{unique_suffix}"
        backup_dir.mkdir(parents=True, exist_ok=False)
        for src in backup_sources:
            artifacts.append(await _copy_backup_source(src, backup_dir, host=host))
        marker = {
            "ts": _now(), "action": action_name, "target": target, "service": service,
            "backup_dir": str(backup_dir), "artifacts": artifacts,
            "metadata": metadata or {}, "verified": True, "buffered": False,
        }
        (backup_dir / "metadata.json").write_text(json.dumps(marker, indent=2, sort_keys=True), encoding="utf-8")
    else:
        LOGGER.warning("nfs_unavailable backup_to_w01 target=%s service=%s action=%s", target, service, action_name)
        for src in backup_sources:
            artifacts.append(await _copy_backup_source_buffered(src, rel_path, host=host))
        marker = {
            "ts": _now(), "action": action_name, "target": target, "service": service,
            "backup_dir": f"w01:{NFS_BUFFER_ROOT}/{rel_path}",
            "artifacts": artifacts, "metadata": metadata or {},
            "verified": True, "buffered": True, "buffer_host": NFS_BUFFER_HOST,
        }
        # Write metadata.json to W-01 buffer too
        meta_content = json.dumps(marker, indent=2, sort_keys=True)
        await run_ssh_command(
            NFS_BUFFER_HOST,
            f"mkdir -p {shlex.quote(f'{NFS_BUFFER_ROOT}/{rel_path}')} && "
            f"printf '%s' {shlex.quote(meta_content)} > {shlex.quote(f'{NFS_BUFFER_ROOT}/{rel_path}/metadata.json')}"
        )

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
    if text.startswith("starfleet-ui/"):
        return SPOT_HOST_STACK_ROOT / text
    if text.startswith("/home/ogre/"):
        return raw

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
    cutoff = _now() - 86400  # only seed from last 24 hours

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
        if ts < cutoff:
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
        "deep analysis", "architecture", "architect", "design review",
        "root cause", "multi-step", "compare options", "tradeoff",
        "risk analysis", "migration plan", "roadmap", "full plan",
        "large context", "complex",
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
        "deep analysis", "architecture", "architect", "design review",
        "root cause", "multi-step", "compare options", "tradeoff",
        "risk analysis", "migration plan", "roadmap", "full plan",
        "large context", "complex",
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
                failures.append({"worker": worker_name, "gpu_lane": gpu_lane, "reason": "unknown_gpu_lane", "stage": "candidate"})
                continue
            models = select_preferred_models(cfg, worker_name, gpu_lane, req.role, req.model, req.allow_fallback, req=req)
            if not models:
                failures.append({"worker": worker_name, "gpu_lane": gpu_lane, "reason": "no_model_preferences", "stage": "models"})
                continue
            for model in models:
                if model not in installed:
                    continue
                lane_ok, lane_reason = lane_admission_allowed(cfg, worker_name, gpu_lane, req.role, model, use_burst)
                if not lane_ok:
                    failures.append({"worker": worker_name, "gpu_lane": gpu_lane, "model": model, "reason": lane_reason, "stage": "gpu_admission"})
                    continue
                scored.append((
                    score_candidate(cfg, worker_name, gpu_lane, req.role, model, use_burst),
                    {
                        "worker": worker_name,
                        "worker_url": cfg["workers"][worker_name]["base_url"],
                        "gpu_lane": gpu_lane,
                        "gpu_label": lane_label(cfg, worker_name, gpu_lane),
                        "model": model,
                        "burst_mode": use_burst,
                    },
                ))
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
        candidate_requests.append(("same_model", clone_request(req, model=preferred_model, allow_fallback=False)))
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
            shortlist.append({
                "mode": mode, "score": score,
                "worker": candidate["worker"], "worker_url": candidate["worker_url"],
                "gpu_lane": candidate["gpu_lane"], "gpu_label": candidate["gpu_label"],
                "model": candidate["model"], "burst_mode": candidate["burst_mode"],
            })
            if len(shortlist) >= ALTERNATE_DEBUG_LIMIT:
                return shortlist

        if mode == "same_model" and not normal_scored and preferred_model:
            shortlist.append({
                "mode": mode, "reason": "no_same_model_candidates",
                "preferred_model": preferred_model,
                "excluded_workers": sorted(excluded_workers),
                "failure_sample": normal_failures[:5],
            })

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
    events.append({
        "ts": _now(), "phase": phase, "attempt": attempt,
        "worker": chosen["worker"], "worker_url": chosen["worker_url"],
        "gpu_lane": chosen["gpu_lane"], "gpu_label": chosen["gpu_label"],
        "model": chosen["model"], "error_type": type(exc).__name__, "error": repr(exc),
    })


def record_retry_note(events: list[dict[str, Any]], chosen: dict[str, Any], phase: str, note: str, **extra: Any) -> None:
    payload = {
        "ts": _now(), "phase": phase,
        "worker": chosen["worker"], "worker_url": chosen["worker_url"],
        "gpu_lane": chosen["gpu_lane"], "gpu_label": chosen["gpu_label"],
        "model": chosen["model"], "note": note,
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
        return {"owner_worker": None, "owner_known": False, "owner_healthy": False, "owner_admissible": False, "owner_has_model": False, "owner_reason": "no_owner_defined"}

    if owner_worker not in cfg.get("workers", {}):
        return {"owner_worker": owner_worker, "owner_known": False, "owner_healthy": False, "owner_admissible": False, "owner_has_model": False, "owner_reason": "owner_missing_from_config"}

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
                    lane_ok, lane_reason = lane_admission_allowed(cfg, owner_worker, gpu_lane, req.role, model, req.allow_burst)
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
        "owner_worker": owner_worker, "owner_known": True,
        "owner_healthy": healthy, "owner_admissible": owner_admissible,
        "owner_has_model": owner_has_model, "owner_reason": owner_reason,
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

def classify_route(cfg, req, initial_choice, final_choice, retry_events):
    owner_worker = role_owner(req.role)
    owner_state = evaluate_owner_state(cfg, req, owner_worker)
    selected_worker = final_choice["worker"]
    fallback_used = (selected_worker != initial_choice["worker"] or bool(retry_events) or bool(final_choice.get("burst_mode", False)))

    if req.worker:
        route_class = "manual_override"; ownership_ok = owner_worker is None or selected_worker == owner_worker; violation_reason = "manual_worker_override"
    elif owner_worker is None:
        route_class = "unowned"; ownership_ok = True; violation_reason = "no_owner_defined"
    elif selected_worker == owner_worker:
        route_class = "primary"; ownership_ok = True; violation_reason = "owner_selected"
    elif req.allow_fallback and (not owner_state["owner_healthy"] or not owner_state["owner_admissible"]):
        route_class = "fallback"; ownership_ok = True
        violation_reason = f"owner_unhealthy:{owner_state['owner_reason']}" if not owner_state["owner_healthy"] else f"owner_inadmissible:{owner_state['owner_reason']}"
    else:
        route_class = "violation"; ownership_ok = False
        if owner_state["owner_healthy"] and owner_state["owner_admissible"]:
            violation_reason = "selected_non_owner_while_owner_admissible"
        elif owner_state["owner_healthy"]:
            violation_reason = "selected_non_owner_while_owner_healthy"
        else:
            violation_reason = "selected_non_owner"

    return {
        "owner_worker": owner_worker, "selected_worker": selected_worker, "selected_model": final_choice["model"],
        "fallback_used": fallback_used, "fallback_allowed": bool(req.allow_fallback),
        "ownership_ok": ownership_ok, "route_class": route_class, "violation_reason": violation_reason,
        **owner_state,
    }


def read_recent_routing_audit(limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    items = list(RECENT_ROUTING_AUDIT)[-limit:]
    return list(reversed(items))


def summarize_routing_audit(window: int) -> dict[str, Any]:
    items = list(RECENT_ROUTING_AUDIT)[-window:] if window > 0 else list(RECENT_ROUTING_AUDIT)
    per_role: dict[str, dict[str, int]] = defaultdict(lambda: {"primary": 0, "fallback": 0, "violation": 0, "manual_override": 0})
    last_violation_ts = None
    primary = fallback = violations = manual_override = 0

    for item in items:
        role = str(item.get("role", "unknown"))
        route_class = str(item.get("route_class", "unknown"))
        if route_class == "primary":
            primary += 1; per_role[role]["primary"] += 1
        elif route_class == "fallback":
            fallback += 1; per_role[role]["fallback"] += 1
        elif route_class == "violation":
            violations += 1; per_role[role]["violation"] += 1
            ts = item.get("ts")
            if isinstance(ts, int):
                last_violation_ts = ts if last_violation_ts is None else max(last_violation_ts, ts)
        elif route_class == "manual_override":
            manual_override += 1; per_role[role]["manual_override"] += 1

    return {
        "ok": violations == 0, "window_count": len(items),
        "primaries": primary, "fallbacks": fallback,
        "violations": violations, "manual_overrides": manual_override,
        "last_violation_ts": last_violation_ts, "by_role": dict(per_role),
    }


async def claim_alternate_candidate(cfg, req, excluded_workers, preferred_model=None):
    if req.worker:
        return None, []
    shortlist = shortlist_candidates(cfg, req, excluded_workers, preferred_model=preferred_model)
    for item in shortlist:
        if item.get("reason"):
            continue
        if not alternate_worker_allowed(cfg, req, item["worker"]):
            continue
        return {"worker": item["worker"], "worker_url": item["worker_url"], "gpu_lane": item["gpu_lane"], "gpu_label": item["gpu_label"], "model": item["model"], "burst_mode": item["burst_mode"]}, shortlist
    return None, shortlist


async def switch_active_allocation(previous, new_choice):
    async with ACTIVE_LOCK:
        decrement_active(previous["worker"], previous["gpu_lane"], previous["model"])
        increment_active(new_choice["worker"], new_choice["gpu_lane"], new_choice["model"])


async def call_generate(worker_url, req, model):
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.post(f"{worker_url}/api/generate", json={"model": model, "prompt": req.prompt, "stream": req.stream})
        resp.raise_for_status()
        return resp.json()

async def call_generate_with_retry(cfg, chosen, req):
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
        next_choice, shortlist = await claim_alternate_candidate(cfg, req, attempted_workers, preferred_model=preferred_model)
        record_retry_note(retry_events, current_choice, "alternate_shortlist", "evaluated alternate candidates", shortlist=shortlist[:ALTERNATE_DEBUG_LIMIT], preferred_model=preferred_model)
        if not next_choice:
            break
        await switch_active_allocation(current_choice, next_choice)
        current_choice = dict(next_choice)
        attempted_workers.add(current_choice["worker"])
        record_retry_note(retry_events, current_choice, "alternate_claim", f"claimed alternate worker #{alt_attempt + 1}", preferred_model=preferred_model)
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
    raise HTTPException(status_code=503, detail={"message": "retry routing exhausted with no alternate worker available"})

async def call_embed(worker_url, req, model):
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.post(f"{worker_url}/api/embed", json={"model": model, "input": req.prompt})
        resp.raise_for_status()
        return resp.json()

async def execute_quarantine_worker(worker_name, seconds, reason):
    cfg = load_config()
    if worker_name not in cfg["workers"]:
        raise HTTPException(status_code=404, detail={"message": "unknown worker"})

    async def do_execute():
        penalty = {"reason": reason, "until": _now() + max(60, seconds), "ts": _now(), "quarantined": True, "failure_count_window": failure_window_count(worker_name, 3600)}
        PENALTY_BOX[worker_name] = penalty
        update_remediation_quarantine(worker_name, True, reason)
        update_watch_state_quarantine(worker_name, True)
        return {"worker": worker_name, "penalty": penalty}

    async def do_verify(execution_result):
        status = worker_status(worker_name)
        remediation = remediation_entry(worker_name)
        ok = status.get("quarantined") is True and remediation.get("quarantined") is True
        return ok, {"watch_quarantined": status.get("quarantined"), "watch_eligible": status.get("eligible"), "remediation_quarantined": remediation.get("quarantined")}

    async def do_rollback(backup_record, execution_result):
        remediation_backup = next(Path(item["dest"]) for item in backup_record["artifacts"] if item["source"] == str(REMEDIATION_STATE_PATH))
        watch_backup = next(Path(item["dest"]) for item in backup_record["artifacts"] if item["source"] == str(WATCH_STATE_PATH))
        shutil.copy2(remediation_backup, REMEDIATION_STATE_PATH)
        shutil.copy2(watch_backup, WATCH_STATE_PATH)
        PENALTY_BOX.pop(worker_name, None)
        return {"restored_files": [str(REMEDIATION_STATE_PATH), str(WATCH_STATE_PATH)], "cleared_penalty": True}

    return await execute_with_enforcement(
        action_name="quarantine_worker", target=worker_name, service="fleet_runtime_state",
        backup_sources=[REMEDIATION_STATE_PATH, WATCH_STATE_PATH],
        execute_fn=do_execute, verify_fn=do_verify, rollback_fn=do_rollback,
        metadata={"reason": reason, "seconds": seconds}, require_backup=True,
    )


async def execute_unquarantine_worker(worker_name):
    cfg = load_config()
    if worker_name not in cfg["workers"]:
        raise HTTPException(status_code=404, detail={"message": "unknown worker"})

    async def do_execute():
        removed_penalty = PENALTY_BOX.pop(worker_name, None)
        FAILURE_HISTORY.pop(worker_name, None)
        update_remediation_quarantine(worker_name, False, "manual_release")
        update_watch_state_quarantine(worker_name, False)
        return {"worker": worker_name, "removed_penalty": removed_penalty is not None}

    async def do_verify(execution_result):
        status = worker_status(worker_name)
        remediation = remediation_entry(worker_name)
        ok = status.get("quarantined") is False and remediation.get("quarantined") is False
        return ok, {"watch_quarantined": status.get("quarantined"), "watch_eligible": status.get("eligible"), "remediation_quarantined": remediation.get("quarantined")}

    async def do_rollback(backup_record, execution_result):
        remediation_backup = next(Path(item["dest"]) for item in backup_record["artifacts"] if item["source"] == str(REMEDIATION_STATE_PATH))
        watch_backup = next(Path(item["dest"]) for item in backup_record["artifacts"] if item["source"] == str(WATCH_STATE_PATH))
        shutil.copy2(remediation_backup, REMEDIATION_STATE_PATH)
        shutil.copy2(watch_backup, WATCH_STATE_PATH)
        return {"restored_files": [str(REMEDIATION_STATE_PATH), str(WATCH_STATE_PATH)], "cleared_penalty": False}

    return await execute_with_enforcement(
        action_name="unquarantine_worker", target=worker_name, service="fleet_runtime_state",
        backup_sources=[REMEDIATION_STATE_PATH, WATCH_STATE_PATH],
        execute_fn=do_execute, verify_fn=do_verify, rollback_fn=do_rollback,
        metadata={"reason": "manual_release"}, require_backup=True,
    )

app = FastAPI(title="Spot Core Control Plane", version="final-v6-routing-audit")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://spot.starfleetcore.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.post("/admin/validate")
async def admin_validate(payload: AdminValidateRequest):
    require_admin_token(payload.model_dump())
    cfg = load_config()
    worker = payload.worker
    commands = payload.commands
    if not isinstance(commands, list) or not commands:
        raise HTTPException(status_code=400, detail={"message": "commands must be a non-empty list"})
    host = worker_host(worker, cfg)
    allowed_prefixes = ["test ", "cat ", "ls ", "systemctl is-active ", "systemctl status ", "systemd-analyze verify ", "bash -n ", "python3 -m py_compile ", "docker compose config", "docker compose ps", "jq "]
    results: list[dict[str, Any]] = []
    for cmd in commands:
        if not isinstance(cmd, str) or not cmd.strip():
            results.append({"ok": False, "command": cmd, "error": "invalid_command"})
            continue
        if not any(cmd.startswith(prefix) for prefix in allowed_prefixes):
            results.append({"ok": False, "command": cmd, "error": "command_not_allowed"})
            continue
        res = await run_ssh_command(host, cmd)
        results.append({"ok": res["returncode"] == 0, "command": cmd, "result": res})
    return {"ok": all(item.get("ok") is True for item in results), "worker": worker, "results": results}

@app.post("/admin/restart-service")
async def admin_restart_service(payload: AdminRestartServiceRequest):
    require_admin_token(payload.model_dump())
    cfg = load_config()
    worker = payload.worker
    service = payload.service
    if service not in ALLOWED_REMOTE_SERVICES:
        raise HTTPException(status_code=403, detail={"message": "service not allowed", "worker": worker, "service": service})
    host = worker_host(worker, cfg)

    async def execute():
        before = await systemctl_show_service(host, service)
        restart = await run_ssh_command(host, f"sudo systemctl restart {shlex.quote(service)}")
        after = await systemctl_show_service(host, service)
        return {"worker": worker, "host": host, "service": service, "before": before, "restart": restart, "after": after}

    async def verify(result):
        restart_ok = result.get("restart", {}).get("returncode") == 0
        observed_ok, details = service_restart_verified(result.get("before", {}), result.get("after", {}))
        details["restart_returncode"] = result.get("restart", {}).get("returncode")
        details["restart_stderr"] = result.get("restart", {}).get("stderr", "")
        return restart_ok and observed_ok, details

    async def rollback(backup, result):
        return {"ok": False, "rollback": "not_applicable_for_service_restart", "backup_path": backup.get("backup_dir") if backup else None}

    return await execute_with_enforcement(
        action_name="restart_service", target=worker, service=service, backup_sources=[],
        execute_fn=execute, verify_fn=verify, rollback_fn=rollback,
        metadata={"worker": worker, "service": service, "host": host}, require_backup=False,
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
        raise HTTPException(status_code=503, detail={"message": "failed to read remote file", "worker": worker, "path": str(path), "ssh": result})
    return {"ok": True, "worker": worker, "path": str(path), "content": result["stdout"]}

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
        write_tmp = await run_ssh_command(host, f"printf %s {shlex.quote(content)} > {shlex.quote(tmp_path)}")
        if write_tmp["returncode"] != 0:
            return {"ok": False, "stage": "write_tmp", "tmp_path": tmp_path, "ssh": write_tmp}
        move_into_place = await run_ssh_command(host, f"mv {shlex.quote(tmp_path)} {shlex.quote(str(path))}")
        return {"ok": move_into_place["returncode"] == 0, "stage": "move_into_place", "tmp_path": tmp_path, "ssh": move_into_place}

    async def verify(result):
        check = await run_ssh_command(host, f"test -f {shlex.quote(str(path))}")
        return check["returncode"] == 0, {"exists": check["returncode"] == 0, "ssh": check, "preexisting_file": preexisting_file}

    async def rollback(backup, result):
        if not preexisting_file:
            delete_new = await run_ssh_command(host, f"rm -f {shlex.quote(str(path))}")
            return {"ok": delete_new["returncode"] == 0, "rollback": "removed_new_file", "ssh": delete_new}
        artifact = next((a for a in backup["artifacts"] if Path(a["source"]) == path), None)
        if not artifact:
            raise RuntimeError(f"No backup artifact found for {path}")
        restore = await run_ssh_command(host, f"cp {shlex.quote(artifact['dest'])} {shlex.quote(str(path))}")
        return {"ok": restore["returncode"] == 0, "rollback": "restored_prior_file", "ssh": restore}

    return await execute_with_enforcement(
        action_name="write_file", target=worker, service="filesystem",
        backup_sources=[path] if preexisting_file else [],
        execute_fn=execute, verify_fn=verify, rollback_fn=rollback,
        metadata={"path": str(path), "host": host, "preexisting_file": preexisting_file},
        require_backup=preexisting_file,
    )

@app.post("/admin/read-local-file")
async def admin_read_local_file(payload: AdminReadLocalFileRequest):
    require_admin_token(payload.model_dump())
    path = resolve_local_path(payload.path)
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"message": "failed to read local file", "path": str(path), "error": repr(exc)}) from exc
    return {"ok": True, "path": str(path), "content": content}


@app.post("/admin/write-local-file")
async def admin_write_local_file(payload: AdminWriteLocalFileRequest):
    require_admin_token(payload.model_dump())
    path = resolve_local_path(payload.path)
    content = payload.content
    preexisting_file = path.exists()

    async def execute():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(path), "bytes_written": len(content.encode("utf-8")), "preexisting_file": preexisting_file}

    async def verify(result):
        exists = path.is_file()
        return exists, {"exists": exists, "preexisting_file": preexisting_file, "size": path.stat().st_size if exists else None}

    async def rollback(backup, result):
        if not preexisting_file:
            try:
                path.unlink(missing_ok=True)
            except Exception as exc:
                return {"ok": False, "rollback": "remove_new_local_file_failed", "error": repr(exc)}
            return {"ok": True, "rollback": "removed_new_local_file", "path": str(path)}
        artifact = next((a for a in backup["artifacts"] if Path(a["source"]) == path), None)
        if not artifact:
            raise RuntimeError(f"No backup artifact found for {path}")
        shutil.copy2(Path(artifact["dest"]), path)
        return {"ok": True, "rollback": "restored_prior_local_file", "path": str(path), "backup_file": artifact["dest"]}

    return await execute_with_enforcement(
        action_name="write_local_file", target="spot-core", service="filesystem_local",
        backup_sources=[path] if preexisting_file else [],
        execute_fn=execute, verify_fn=verify, rollback_fn=rollback,
        metadata={"path": str(path), "preexisting_file": preexisting_file},
        require_backup=preexisting_file,
    )


@app.post("/admin/write-ui-file")
async def admin_write_ui_file(payload: dict):
    require_admin_token(payload)
    filename = str(payload.get("filename", "")).strip()
    content  = payload.get("content", "")
    if not filename or "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail={"message": "invalid filename"})
    dest = Path("/home/ogre/spot-stack/starfleet-ui/src") / filename
    dest.write_text(content, encoding="utf-8")
    trigger = Path("/home/ogre/spot-stack/starfleet-ui/src/.build-trigger")
    trigger.touch()
    return {"ok": True, "path": str(dest), "bytes": len(content.encode())}

@app.post("/admin/operator-command")
async def admin_operator_command(payload: AdminOperatorCommandRequest):
    require_admin_token(payload.model_dump())
    spec = OPERATOR_COMMANDS.get(payload.command)
    if not spec:
        raise HTTPException(status_code=403, detail={"message": "operator command not allowed", "command": payload.command, "allowed": sorted(OPERATOR_COMMANDS.keys())})

    async def run_local_command():
        cmd_env = os.environ.copy()
        cmd_env.update(spec.get("env", {}))
        proc = await asyncio.create_subprocess_exec(*spec["argv"], cwd=spec["cwd"], env=cmd_env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=int(spec.get("timeout", 120)))
        except asyncio.TimeoutError:
            proc.kill()
            stdout, stderr = await proc.communicate()
            return {"ok": False, "command": payload.command, "argv": spec["argv"], "cwd": spec["cwd"], "returncode": None, "timed_out": True, "stdout": stdout.decode("utf-8", errors="replace"), "stderr": stderr.decode("utf-8", errors="replace")}
        return {"ok": proc.returncode == 0, "command": payload.command, "argv": spec["argv"], "cwd": spec["cwd"], "returncode": proc.returncode, "timed_out": False, "stdout": stdout.decode("utf-8", errors="replace"), "stderr": stderr.decode("utf-8", errors="replace")}

    async def verify(result):
        return result.get("ok") is True, {"returncode": result.get("returncode"), "timed_out": result.get("timed_out"), "command": result.get("command")}

    return await execute_with_enforcement(
        action_name="operator_command", target="spot-core", service="operator", backup_sources=[],
        execute_fn=run_local_command, verify_fn=verify, rollback_fn=None,
        metadata={"command": payload.command, "argv": spec["argv"], "cwd": spec["cwd"], "mutating": bool(spec.get("mutating", False))},
        require_backup=False,
    )


@app.post("/admin/quarantine")
async def admin_quarantine_worker(payload: AdminQuarantineRequest):
    require_admin_token(payload.model_dump())
    return await execute_quarantine_worker(worker_name=payload.worker, seconds=payload.seconds, reason=payload.reason)

@app.post("/admin/release")
async def admin_release_worker(payload: AdminReleaseRequest):
    require_admin_token(payload.model_dump())
    return await execute_unquarantine_worker(worker_name=payload.worker)

@app.post("/chat/execute")
async def chat_execute(payload: ChatExecuteRequest):
    """Execute a Spot-proposed action (Level-1 autonomy)."""
    require_admin_token(payload.model_dump())
    action = payload.action.strip()
    target = (payload.target or "").strip()
    reason = payload.reason or "spot_proposed"
    spec = SPOT_ACTION_ALLOWLIST.get(action)
    if not spec:
        raise HTTPException(status_code=403, detail={"message": f"action not in allowlist: {action}", "allowed": sorted(SPOT_ACTION_ALLOWLIST.keys())})
    if spec["confirm_required"] and not payload.confirmed:
        return {"ok": False, "action": action, "target": target, "confirm_required": True,
                "message": f"Action requires confirmation. Resend with confirmed=true.", "risk": spec["risk"]}
    cfg = load_config()
    if spec["targets"] == "workers":
        if not target:
            raise HTTPException(status_code=400, detail={"message": "target worker required"})
        if target not in cfg.get("workers", {}):
            raise HTTPException(status_code=404, detail={"message": f"unknown worker: {target}"})

    result: dict[str, Any] = {}

    if action == "restart_ollama":
        host = worker_host(target, cfg)
        async def _do_restart():
            before = await systemctl_show_service(host, "ollama")
            restart = await run_ssh_command(host, "sudo systemctl restart ollama")
            after = await systemctl_show_service(host, "ollama")
            return {"worker": target, "host": host, "before": before, "restart": restart, "after": after}
        async def _verify_restart(r):
            ok1 = r.get("restart", {}).get("returncode") == 0
            ok2, details = service_restart_verified(r.get("before", {}), r.get("after", {}))
            return ok1 and ok2, details
        result = await execute_with_enforcement(
            action_name="restart_service", target=target, service="ollama", backup_sources=[],
            execute_fn=_do_restart, verify_fn=_verify_restart,
            metadata={"worker": target, "reason": reason, "initiated_by": "spot_chat"}, require_backup=False)

    elif action == "quarantine_worker":
        result = await execute_quarantine_worker(worker_name=target, seconds=1800, reason=f"spot_proposed:{reason}")

    elif action == "release_worker":
        result = await execute_unquarantine_worker(worker_name=target)

    elif action == "nfs_sync":
        async def _do_nfs_sync():
            proc = await asyncio.create_subprocess_exec(
                "bash", str(SPOT_WATCH_ROOT / "spot-nfs-sync.sh"),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            return {"ok": proc.returncode == 0, "stdout": stdout.decode("utf-8", errors="replace"), "returncode": proc.returncode}
        result = await execute_with_enforcement(
            action_name="nfs_sync", target="unimatrix6", service="nfs", backup_sources=[],
            execute_fn=_do_nfs_sync, verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"reason": reason, "initiated_by": "spot_chat"}, require_backup=False)

    elif action == "wake_worker":
        mac = SPOT_WORKER_MACS.get(target)
        if not mac:
            raise HTTPException(status_code=400, detail={"message": f"no WOL MAC for {target}"})
        async def _do_wake():
            proc = await asyncio.create_subprocess_exec(
                "bash", str(SPOT_WATCH_ROOT / "wake-worker.sh"), target, mac,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            return {"ok": proc.returncode == 0, "stdout": stdout.decode(), "stderr": stderr.decode()}
        result = await execute_with_enforcement(
            action_name="wake_worker", target=target, service="wol", backup_sources=[],
            execute_fn=_do_wake, verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"worker": target, "mac": mac, "reason": reason, "initiated_by": "spot_chat"}, require_backup=False)

    # ── OPNsense actions ──────────────────────────────────────────────────
    elif action == "opn_create_firewall_rule":
        params = payload.__dict__.get("params") or {}
        async def _do_opn_fw():
            rule_payload = {
                "rule": {
                    "enabled": "1",
                    "action": params.get("action", "pass"),
                    "interface": params.get("interface", "lan"),
                    "direction": params.get("direction", "in"),
                    "ipprotocol": "inet",
                    "protocol": params.get("protocol", "any"),
                    "source_net": params.get("source_net", "any"),
                    "destination_net": params.get("destination_net", "any"),
                    "destination_port": params.get("destination_port", "any"),
                    "description": params.get("description", reason),
                }
            }
            r = await _opn("POST", "/firewall/filter/addRule", json_body=rule_payload)
            await _opn("POST", "/firewall/filter/apply")
            return {"ok": "uuid" in r or r.get("result") == "saved", "opn": r}
        result = await execute_with_enforcement(
            action_name="opn_create_firewall_rule", target="opnsense", service="firewall",
            backup_sources=[], execute_fn=_do_opn_fw,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"params": params, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    elif action == "opn_delete_firewall_rule":
        params = payload.__dict__.get("params") or {}
        rule_uuid = params.get("rule_uuid", target)
        async def _do_opn_fw_del():
            r = await _opn("POST", f"/firewall/filter/delRule/{rule_uuid}")
            await _opn("POST", "/firewall/filter/apply")
            return {"ok": r.get("result") == "deleted", "opn": r}
        result = await execute_with_enforcement(
            action_name="opn_delete_firewall_rule", target="opnsense", service="firewall",
            backup_sources=[], execute_fn=_do_opn_fw_del,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"rule_uuid": rule_uuid, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    elif action == "opn_create_vlan":
        params = payload.__dict__.get("params") or {}
        async def _do_opn_vlan():
            vlan_payload = {"vlan": {"if": params.get("parent_interface", "igc0"), "tag": str(params.get("vlan_tag", 0)), "pcp": "0", "descr": params.get("description", reason)}}
            r = await _opn("POST", "/interfaces/vlan/addItem", json_body=vlan_payload)
            await _opn("POST", "/interfaces/vlan/reconfigure")
            return {"ok": "uuid" in r or r.get("result") == "saved", "opn": r}
        result = await execute_with_enforcement(
            action_name="opn_create_vlan", target="opnsense", service="vlan",
            backup_sources=[], execute_fn=_do_opn_vlan,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"params": params, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    elif action == "opn_create_alias":
        params = payload.__dict__.get("params") or {}
        async def _do_opn_alias():
            alias_payload = {"alias": {"enabled": "1", "name": params.get("name", ""), "type": params.get("alias_type", "host"), "content": "\n".join(params.get("content", [])), "description": params.get("description", reason)}}
            r = await _opn("POST", "/firewall/alias/addItem", json_body=alias_payload)
            await _opn("POST", "/firewall/alias/reconfigure")
            return {"ok": "uuid" in r or r.get("result") == "saved", "opn": r}
        result = await execute_with_enforcement(
            action_name="opn_create_alias", target="opnsense", service="firewall_alias",
            backup_sources=[], execute_fn=_do_opn_alias,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"params": params, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    elif action == "opn_create_static_lease":
        params = payload.__dict__.get("params") or {}
        async def _do_opn_lease():
            lease_payload = {"lease": {"interface": params.get("interface", "lan"), "mac": params.get("mac", ""), "ipaddr": params.get("ip", ""), "hostname": params.get("hostname", "")}}
            r = await _opn("POST", "/dhcpv4/settings/addStaticMap", json_body=lease_payload)
            return {"ok": "uuid" in r or r.get("result") == "saved", "opn": r}
        result = await execute_with_enforcement(
            action_name="opn_create_static_lease", target="opnsense", service="dhcp",
            backup_sources=[], execute_fn=_do_opn_lease,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"params": params, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    elif action == "opn_create_dns_override":
        params = payload.__dict__.get("params") or {}
        async def _do_opn_dns():
            dns_payload = {"host": {"enabled": "1", "hostname": params.get("hostname", ""), "domain": params.get("domain", ""), "rr": "A", "server": params.get("ip", ""), "description": params.get("description", reason)}}
            r = await _opn("POST", "/unbound/settings/addHostOverride", json_body=dns_payload)
            await _opn("POST", "/unbound/service/reconfigure")
            return {"ok": "uuid" in r or r.get("result") == "saved", "opn": r}
        result = await execute_with_enforcement(
            action_name="opn_create_dns_override", target="opnsense", service="dns",
            backup_sources=[], execute_fn=_do_opn_dns,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"params": params, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    elif action == "opn_delete_dns_override":
        params = payload.__dict__.get("params") or {}
        override_uuid = params.get("uuid", target)
        async def _do_opn_dns_del():
            r = await _opn("POST", f"/unbound/settings/delHostOverride/{override_uuid}")
            await _opn("POST", "/unbound/service/reconfigure")
            return {"ok": r.get("result") == "deleted", "opn": r}
        result = await execute_with_enforcement(
            action_name="opn_delete_dns_override", target="opnsense", service="dns",
            backup_sources=[], execute_fn=_do_opn_dns_del,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"uuid": override_uuid, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    # ── UniFi actions ─────────────────────────────────────────────────────
    elif action == "unifi_create_network":
        params = payload.__dict__.get("params") or {}
        async def _do_unifi_net():
            net_payload = {"name": params.get("name", ""), "purpose": params.get("purpose", "corporate"), "vlan_enabled": True, "vlan": params.get("vlan_id", 0)}
            if params.get("subnet"):
                net_payload["ip_subnet"] = params["subnet"]
                net_payload["dhcpd_enabled"] = False
            r = await _unifi("POST", "/rest/networkconf", json_body=net_payload)
            return {"ok": isinstance(r.get("data"), list) and len(r.get("data", [])) > 0, "unifi": r}
        result = await execute_with_enforcement(
            action_name="unifi_create_network", target="unifi", service="network",
            backup_sources=[], execute_fn=_do_unifi_net,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"params": params, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    elif action == "unifi_set_port_profile":
        params = payload.__dict__.get("params") or {}
        async def _do_unifi_port():
            port_payload = {"port_overrides": [{"port_idx": params.get("port_idx", 1), "portconf_id": params.get("port_profile_id", "")}]}
            r = await _unifi("PUT", f"/rest/device/{params.get('device_mac', '')}", json_body=port_payload)
            return {"ok": r.get("meta", {}).get("rc") == "ok", "unifi": r}
        result = await execute_with_enforcement(
            action_name="unifi_set_port_profile", target="unifi", service="switch_port",
            backup_sources=[], execute_fn=_do_unifi_port,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"params": params, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    elif action == "unifi_block_client":
        params = payload.__dict__.get("params") or {}
        client_mac = params.get("client_mac", target)
        async def _do_unifi_block():
            r = await _unifi("POST", "/cmd/stamgr", json_body={"cmd": "block-sta", "mac": client_mac})
            return {"ok": r.get("meta", {}).get("rc") == "ok", "unifi": r}
        result = await execute_with_enforcement(
            action_name="unifi_block_client", target="unifi", service="client_policy",
            backup_sources=[], execute_fn=_do_unifi_block,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"client_mac": client_mac, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    elif action == "unifi_restart_device":
        params = payload.__dict__.get("params") or {}
        device_mac = params.get("device_mac", target)
        async def _do_unifi_restart():
            r = await _unifi("POST", "/cmd/devmgr", json_body={"cmd": "restart", "mac": device_mac})
            return {"ok": r.get("meta", {}).get("rc") == "ok", "unifi": r}
        result = await execute_with_enforcement(
            action_name="unifi_restart_device", target="unifi", service="device_mgmt",
            backup_sources=[], execute_fn=_do_unifi_restart,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"device_mac": device_mac, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    summary = f"[EXECUTED] {action} → {target or 'fleet'}: {'OK' if result.get('ok') else 'FAILED'}"
    append_chat_history("system", summary)
    return {"ok": result.get("ok", False), "action": action, "target": target, "risk": spec["risk"], "result": result}


@app.get("/admin/nfs-status")
async def admin_nfs_status():
    """Live NFS availability check."""
    global _nfs_available, _nfs_last_check
    _nfs_last_check = 0.0  # force recheck
    available = nfs_available()
    return {
        "ok": available,
        "nfs_mount": str(NFS_MOUNT),
        "buffer_host": NFS_BUFFER_HOST,
        "buffer_root": NFS_BUFFER_ROOT,
        "available": available,
    }

@app.on_event("startup")
async def startup_event() -> None:
    load_config()
    seed_warm_models()
    seed_routing_audit()
    seed_recent_decisions()
    seed_latency_history()

@app.head("/")
async def dashboard_head():
    return {}

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    health_data = await health()
    routing_state = await routing()
    fleet = await fleet_ping()
    latency = await stats_latency()
    audit = await stats_routing_audit(limit=200)
    decisions = await stats_recent_decisions(limit=5)

    def esc(value):
        text = "" if value is None else str(value)
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    worker_rows = []
    for name, item in fleet.items():
        lat = item.get("latency") or {}
        status = "OK" if item.get("ok") else "BAD"
        worker_rows.append(f"<tr><td>{esc(name)}</td><td class='{status.lower()}'>{esc(status)}</td><td>{esc(item.get('primary_role'))}</td><td>{esc(item.get('reason'))}</td><td>{esc(item.get('quarantined'))}</td><td>{esc(item.get('degraded'))}</td><td>{esc(lat.get('p50_total_ms'))}</td><td>{esc(lat.get('avg_tok_per_sec'))}</td></tr>")

    return f"<!doctype html><html><head><title>Spot Core</title></head><body><h1>Spot Core</h1><p>Workers: {len(fleet)}</p></body></html>"

@app.get("/health")
async def health():
    return {"ok": True, "uptime_sec": _now() - APP_START_TS}


@app.get("/routing")
async def routing():
    cfg = load_config()
    return {
        "ok": True, "config_path": str(CONFIG_PATH), "watch_state_path": str(WATCH_STATE_PATH),
        "routing_audit_path": str(ROUTING_AUDIT_PATH), "active_requests": ACTIVE_REQUESTS,
        "active_gpu_requests": ACTIVE_GPU_REQUESTS, "active_model_requests": ACTIVE_MODEL_REQUESTS,
        "waiting_requests": WAITING_REQUESTS, "penalty_box": PENALTY_BOX, "warm_models": WARM_MODELS,
        "role_priority": cfg.get("role_priority", {}), "priority_order": cfg.get("priority_order", []),
        "queue_policy": cfg.get("queue_policy", {}), "retry_policy": cfg.get("retry_policy", {}),
        "burst_policy": {k: v.get("burst_gpu_routes", {}) for k, v in cfg.get("workers", {}).items()},
        "role_owners": ROLE_OWNERS,
    }


@app.get("/fleet/ping")
async def fleet_ping():
    cfg = load_config()
    out: dict[str, Any] = {}
    for name, worker_cfg in cfg["workers"].items():
        status = worker_status(name)
        healthy, reason = is_worker_healthy(name, cfg)
        remediation = remediation_entry(name)
        out[name] = {
            "ok": healthy, "reason": reason, "base_url": worker_cfg["base_url"],
            "primary_role": worker_cfg.get("primary_role"), "secondary_roles": worker_cfg.get("secondary_roles", []),
            "installed_models": sorted(installed_models_for_worker(name, cfg)),
            "eligible": healthy, "quarantined": bool(status.get("quarantined", False)),
            "alerts": status.get("alerts", []), "running_jobs": scheduler_running_jobs(name),
            "watcher_running_jobs": worker_metric_int(status, "running_jobs", 0),
            "running_gpu_jobs": ACTIVE_GPU_REQUESTS.get(name, {}), "warm_models": WARM_MODELS.get(name, {}),
            "latency": worker_latency_summary(name), "penalty": current_penalty(name),
            "degraded": bool(remediation.get("degraded", False)), "degraded_reason": remediation.get("degraded_reason"),
            "fallback_count_window": remediation.get("fallback_count_window", 0),
        }
    return out


@app.get("/stats/latency")
async def stats_latency():
    cfg = load_config()
    return {name: worker_latency_summary(name) for name in cfg["workers"].keys()}


@app.get("/operator/readiness")
async def operator_readiness():
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
            slow_workers.append({"worker": name, "p50_total_ms": p50_ms, "avg_total_ms": avg_ms, "reason": "p50_latency_ge_5000ms"})

        workers.append({
            "worker": name, "ok": worker_ok, "reason": item.get("reason"),
            "primary_role": item.get("primary_role"), "eligible": bool(item.get("eligible")),
            "quarantined": is_quarantined, "degraded": is_degraded,
            "degraded_reason": item.get("degraded_reason"), "latency": lat,
        })

    routing_ok = bool(audit.get("ok")) and int(audit.get("violations") or 0) == 0
    fleet_ok = worker_failures == 0 and quarantined == 0
    core_ok = bool(health_data.get("ok"))
    status = "ready" if core_ok and routing_ok and fleet_ok else "not_ready"
    if slow_workers and status == "ready":
        status = "ready_with_warnings"

    return {
        "ok": status in {"ready", "ready_with_warnings"},
        "status": status, "ts": _now(),
        "core": {"ok": core_ok, "uptime_sec": health_data.get("uptime_sec")},
        "routing": {
            "ok": routing_ok, "window_count": audit.get("window_count"),
            "primaries": audit.get("primaries"), "fallbacks": audit.get("fallbacks"),
            "violations": audit.get("violations"), "manual_overrides": audit.get("manual_overrides"),
            "last_violation_ts": audit.get("last_violation_ts"),
        },
        "fleet": {
            "worker_count": len(workers), "worker_failures": worker_failures,
            "quarantined": quarantined, "degraded": degraded,
            "slow_workers": slow_workers, "workers": workers,
        },
        "operator": {"readiness_source": "live", "readiness_endpoint": "/operator/readiness"},
    }


@app.get("/operator/alerts", response_class=PlainTextResponse)
async def operator_alerts(limit: int = 200):
    """Serve the worker recovery log as plain JSONL for the dashboard alerts tab."""
    # Try NFS path first, fall back to local
    log_paths = [
        Path("/mnt/collective/logs/spot/worker-recover.jsonl"),
        WORKER_RECOVER_LOG,
    ]
    for log_path in log_paths:
        try:
            if log_path.exists():
                lines = log_path.read_text(encoding="utf-8").splitlines()
                # Return last N lines
                tail = lines[-max(1, min(limit, 500)):]
                return "\n".join(tail)
        except Exception:
            continue
    return ""


@app.get("/stats/recent-decisions")
async def stats_recent_decisions(limit: int = 25):
    items = list(RECENT_DECISIONS)[-max(1, min(limit, 200)):]
    return {"count": len(items), "items": items}


@app.get("/stats/routing-audit")
async def stats_routing_audit(limit: int = 200):
    bounded = max(1, min(limit, ROUTING_AUDIT_WINDOW))
    summary = summarize_routing_audit(bounded)
    summary["items"] = read_recent_routing_audit(min(50, bounded))
    summary["role_owners"] = ROLE_OWNERS
    summary["routing_audit_path"] = str(ROUTING_AUDIT_PATH)
    return summary

@app.post("/quarantine/{worker_name}")
async def quarantine_worker(worker_name: str, seconds: int = 1800, reason: str = "manual_quarantine"):
    result = await execute_quarantine_worker(worker_name=worker_name, seconds=seconds, reason=reason)
    result["deprecated_route"] = True
    result["preferred_route"] = "/admin/quarantine"
    return result


@app.delete("/quarantine/{worker_name}")
async def unquarantine_worker(worker_name: str):
    result = await execute_unquarantine_worker(worker_name=worker_name)
    result["deprecated_route"] = True
    result["preferred_route"] = "/admin/release"
    return result


@app.post("/actions/restart-service/{worker_name}/{service_name}")
async def restart_service(worker_name: str, service_name: str):
    cfg = load_config()
    if worker_name not in cfg["workers"]:
        raise HTTPException(status_code=404, detail={"message": "unknown worker"})
    if service_name not in ALLOWED_REMOTE_SERVICES:
        raise HTTPException(status_code=403, detail={"message": "service not allowlisted", "service": service_name})
    host = worker_host(worker_name, cfg)

    async def do_execute():
        before = await systemctl_show_service(host, service_name)
        restart = await run_ssh_command(host, f"sudo systemctl restart {shlex.quote(service_name)}")
        after = await systemctl_show_service(host, service_name)
        return {"worker": worker_name, "host": host, "service": service_name, "before": before, "restart": restart, "after": after}

    async def do_verify(execution_result):
        status = worker_status(worker_name)
        restart_ok = execution_result.get("restart", {}).get("returncode") == 0
        observed_ok, details = service_restart_verified(execution_result.get("before", {}), execution_result.get("after", {}))
        ok = restart_ok and observed_ok and status.get("ssh_ok") is not False
        if service_name == "ollama":
            ok = ok and (status.get("service_ok") is True or details.get("active_after") is True)
        details.update({"restart_returncode": execution_result.get("restart", {}).get("returncode"), "restart_stderr": execution_result.get("restart", {}).get("stderr", ""), "watch_ssh_ok": status.get("ssh_ok"), "watch_service_ok": status.get("service_ok")})
        return ok, details

    async def do_rollback(backup_record, execution_result):
        return {"rollback": "not_applicable_for_service_restart", "backup_path": backup_record.get("backup_dir")}

    result = await execute_with_enforcement(
        action_name="restart_service", target=worker_name, service=service_name, backup_sources=[],
        execute_fn=do_execute, verify_fn=do_verify, rollback_fn=do_rollback,
        metadata={"worker": worker_name, "host": host, "service": service_name}, require_backup=False,
    )
    result["deprecated_route"] = True
    result["preferred_route"] = "/admin/restart-service"
    return result

ALLOWED_OPENAI_REVIEW_ROLES = {"general", "coding", "heavy", "reasoning"}
DENIED_OPENAI_REVIEW_ROLES = {"utility", "watcher", "network_ops", "secrets"}

def openai_provider_config(cfg):
    return cfg.get("providers", {}).get("openai", {}) or {}

def assert_openai_review_allowed(cfg, req):
    role = req.role
    if role in DENIED_OPENAI_REVIEW_ROLES or role not in ALLOWED_OPENAI_REVIEW_ROLES:
        raise HTTPException(status_code=403, detail={"message": f"OpenAI review denied for role: {role}"})
    provider = openai_provider_config(cfg)
    if not provider.get("enabled"):
        raise HTTPException(status_code=503, detail={"message": "OpenAI provider disabled"})
    api_key_env = provider.get("api_key_env", "OPENAI_API_KEY")
    api_key = os.environ.get(api_key_env, "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail={"message": f"missing OpenAI API key env: {api_key_env}"})
    model = req.model or provider.get("default_model") or "gpt-4.1-mini"
    return api_key, model

async def call_openai_review(cfg, req):
    api_key, model = assert_openai_review_allowed(cfg, req)
    system_prompt = "You are an external Spot project reviewer. Authority is proposal/review only. Do not approve execution. Check project fit, policy fit, backup-first alignment, and worker role ownership. Return concise PASS/FAIL with reasons."
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.post("https://api.openai.com/v1/responses", headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json={"model": model, "input": [{"role": "system", "content": system_prompt}, {"role": "user", "content": req.prompt}]})
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail={"message": "OpenAI upstream request failed", "status_code": e.response.status_code, "response": e.response.text[:4000]}) from e
        data = resp.json()
    text = ""
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                text += content.get("text", "")
    return {"provider": "openai", "model": model, "authority": "proposal_and_review_only", "response": text.strip(), "raw": data}

async def call_local_review(cfg, req):
    worker_cfg = cfg.get("workers", {}).get(req.worker)
    if not worker_cfg:
        raise HTTPException(status_code=404, detail={"message": f"unknown review worker: {req.worker}"})
    if worker_cfg.get("primary_role") != "review":
        raise HTTPException(status_code=403, detail={"message": f"worker is not review role: {req.worker}"})
    if not worker_cfg.get("routing_enabled", False):
        raise HTTPException(status_code=503, detail={"message": f"review worker disabled: {req.worker}"})
    base_url = worker_cfg.get("base_url")
    if not base_url:
        raise HTTPException(status_code=503, detail={"message": f"review worker missing base_url: {req.worker}"})
    system_prompt = "You are Spot local reviewer. Proposal-review only. Return STRICT JSON only with keys: verdict, confidence, notes. verdict must be PASS, FIX, or NO."
    payload = {"model": req.model, "prompt": f"{system_prompt}\n\nREVIEW_TYPE: {req.review_type}\n\n{req.prompt}", "stream": False}
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.post(f"{base_url}/api/generate", json=payload)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=502, detail={"message": "local review upstream request failed", "worker": req.worker, "status_code": exc.response.status_code, "response": exc.response.text[:4000]}) from exc
        data = resp.json()
    response_text = str(data.get("response") or "").strip()
    if not response_text:
        raise HTTPException(status_code=502, detail={"message": "local review returned empty response"})
    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail={"message": "local review returned invalid JSON", "response": response_text[:4000]}) from exc
    verdict = str(parsed.get("verdict", "FIX")).upper()
    if verdict not in {"PASS", "FIX", "NO"}:
        raise HTTPException(status_code=502, detail={"message": "local review returned invalid verdict", "verdict": verdict})
    return {"reviewer": req.worker, "model": req.model, "review_type": req.review_type, "verdict": verdict, "execution_allowed": False, "result_blocked": True, "authority": "proposal_review_only", "confidence": str(parsed.get("confidence", "low")), "response": response_text, "raw": parsed}

@app.post("/review/openai", response_model=OpenAIReviewResult)
async def openai_review_route(req: OpenAIReviewRequest):
    cfg = load_config()
    started = _now()
    data = await call_openai_review(cfg, req)
    append_jsonl(EXEC_HISTORY_PATH, {"ts": started, "provider": "openai", "role_requested": req.role, "review_type": req.review_type, "model_requested": req.model, "model_used": data["model"], "authority": data["authority"], "prompt_chars": len(req.prompt), "response_chars": len(data["response"]), "proposal_only": True, "external_review": True})
    return OpenAIReviewResult(ok=True, provider="openai", model=data["model"], role_requested=req.role, review_type=req.review_type, authority=data["authority"], response=data["response"], raw={"provider": "openai", "model": data["model"], "authority": data["authority"], "proposal_only": True, "external_review": True})

@app.post("/review/local", response_model=LocalReviewResult)
async def review_local(req: LocalReviewRequest):
    cfg = load_config()
    started = _now()
    result = await call_local_review(cfg, req)
    append_jsonl(REVIEW_LOG_ROOT / "local-review-history.jsonl", {"ts": started, "provider": "local", "review_type": req.review_type, "worker": req.worker, "model": req.model, "verdict": result["verdict"], "authority": result["authority"], "execution_allowed": False, "result_blocked": True, "proposal_only": True, "local_review": True})
    return LocalReviewResult(ok=True, reviewer=result["reviewer"], model=result["model"], review_type=result["review_type"], verdict=result["verdict"], execution_allowed=False, result_blocked=True, authority="proposal_review_only", confidence=result["confidence"], response=result["response"], raw=result["raw"])


def load_chat_history(limit: int = CHAT_HISTORY_WINDOW) -> list[dict]:
    """Load last N turns from persistent chat history."""
    try:
        if not CHAT_HISTORY_PATH.exists():
            return []
        lines = CHAT_HISTORY_PATH.read_text(encoding="utf-8").splitlines()
        turns = []
        for line in lines[-(limit * 2):]:
            try:
                turns.append(json.loads(line))
            except Exception:
                continue
        return turns[-limit:]
    except Exception:
        return []


def append_chat_history(role: str, content: str) -> None:
    """Append a turn to persistent chat history."""
    try:
        CHAT_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CHAT_HISTORY_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": _now(), "role": role, "content": content}, sort_keys=True) + "\n")
    except Exception as exc:
        LOGGER.warning("chat_history_append_failed error=%r", exc)


def build_recent_actions_context(limit: int = 5) -> str:
    """Last N action log entries for Spot's self-knowledge."""
    try:
        action_log = ACTION_LOG_ROOT / "actions.jsonl"
        if not action_log.exists():
            return "  No recent actions logged."
        lines = action_log.read_text(encoding="utf-8").splitlines()
        entries = []
        for line in lines[-(limit * 2):]:
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
        entries = entries[-limit:]
        if not entries:
            return "  No recent actions logged."
        parts = []
        for e in reversed(entries):
            age_min = max(0, (_now() - int(e.get("ts", _now()))) // 60)
            parts.append(f"  [{age_min}m ago] {e.get('action','?')} → {e.get('target','')} [{e.get('status','')}] risk={e.get('risk_class','')}")
        return "\n".join(parts)
    except Exception:
        return "  Action log unavailable."


def build_spot_identity() -> str:
    """Spot's fixed identity block."""
    uptime_sec = _now() - APP_START_TS
    return (
        "IDENTITY:\n"
        "  Name: Spot\n"
        "  Role: AI ops brain for Starfleet Command's private GPU cluster\n"
        "  Operator: ogre (Chris)\n"
        f"  Control plane uptime: {uptime_sec // 3600}h {(uptime_sec % 3600) // 60}m\n"
        "  Style: terse, direct, no fluff. You know this fleet intimately.\n"
        "  Known issues: W-03 is the weak node (GTX 1070 8GB, slow). W-06 has high p50.\n"
        "  Authority: advisory only — propose actions, operator confirms execution."
    )


def build_spot_fleet_context() -> str:
    """Build a grounded, factual fleet context block for Spot's system prompt."""
    try:
        watch = load_watch_state()
        hosts = watch.get("hosts", {})
        ts = watch.get("timestamp", "unknown")
        cfg = load_config()
        worker_names = set(cfg.get("workers", {}).keys())
    except Exception:
        return "  Fleet data unavailable (watch state read error)"

    lines = [f"[as of {ts}]", "", "GPU WORKERS:"]

    for wname in sorted(worker_names):
        winfo = hosts.get(wname)
        if not isinstance(winfo, dict):
            lines.append(f"  {wname}: UNKNOWN (not in watch state)")
            continue
        ssh_ok = winfo.get("ssh_ok")
        svc_ok = winfo.get("service_ok")
        alerts = winfo.get("alerts") or []
        quarantined = winfo.get("quarantined", False)
        if ssh_ok is False:
            status = "OFFLINE (ssh down)"
        elif svc_ok is False:
            status = "DEGRADED (ollama down)"
        elif quarantined:
            status = "QUARANTINED"
        elif alerts:
            status = f"ALERT:{','.join(alerts)}"
        else:
            status = "ONLINE"
        models = winfo.get("models") or []
        gpu_free = winfo.get("gpu_free_mb_max")
        gpu_total = winfo.get("gpu_vram_total_mb_max")
        load = winfo.get("load_1")
        jobs = winfo.get("running_jobs", 0)
        gpu_str = ""
        if gpu_total:
            free_gb = round((gpu_free or 0) / 1024, 1)
            total_gb = round(gpu_total / 1024, 1)
            gpu_str = f" GPU:{free_gb}/{total_gb}GB-free"
        load_str = f" load:{load}" if load is not None else ""
        jobs_str = f" jobs:{jobs}" if jobs else ""
        models_str = f" models:[{','.join(models[:4])}{',...' if len(models) > 4 else ''}]" if models else ""
        lines.append(f"  {wname}: {status}{gpu_str}{load_str}{jobs_str}{models_str}")

    infra_roles = {
        "spot-core": "control_plane",
        "starfleet-core": "npm/unifi/dns/ntp",
        "dns-core": "dns/adguard",
        "starfleet-tower": "observability/ntfy",
        "unimatrix6": "nas/nfs",
        "spot-ui-01": "dashboard/kiosk",
    }
    lines.append("")
    lines.append("INFRASTRUCTURE:")
    infra_names = sorted(set([n for n in hosts if n not in worker_names] + list(infra_roles.keys())))
    for iname in infra_names:
        role_label = infra_roles.get(iname, "unknown")
        iinfo = hosts.get(iname)
        if not isinstance(iinfo, dict):
            lines.append(f"  {iname} [{role_label}]: UNKNOWN (not in watch state)")
            continue
        ssh_ok = iinfo.get("ssh_ok")
        alerts = iinfo.get("alerts") or []
        status = "ONLINE" if ssh_ok is True else ("OFFLINE (ssh down)" if ssh_ok is False else "UNKNOWN")
        alert_str = f" ALERTS:{alerts}" if alerts else ""
        lines.append(f"  {iname} [{role_label}]: {status}{alert_str}")

    lines.append("")
    lines.append("ROUTING AUDIT (last 200):")
    try:
        audit = summarize_routing_audit(200)
        lines.append(f"  primaries:{audit['primaries']} fallbacks:{audit['fallbacks']} violations:{audit['violations']}")
    except Exception:
        lines.append("  unavailable")

    # NFS status
    lines.append("")
    lines.append(f"NFS: {'AVAILABLE' if nfs_available() else 'OFFLINE - buffering to W-01'}")

    lines.append("")
    lines.append("RECENT ACTIONS:")
    lines.append(build_recent_actions_context(5))

    return "\n".join(lines)


async def call_chat_direct(worker_url: str, model: str, system: str, user: str, history: list[dict] | None = None) -> dict:
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for turn in (history or []):
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user})
    payload = {"model": model, "messages": messages, "stream": False}
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.post(f"{worker_url}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()


CHAT_MODEL = "qwen2.5:14b"
CHAT_WORKER_URL = "http://192.168.10.14:11434"


@app.post("/chat", response_model=ChatResult)
async def chat_route(payload: ChatRequest):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail={"message": "empty chat message"})

    fleet_context = build_spot_fleet_context()
    identity = build_spot_identity()
    history = load_chat_history()

    # Live network snapshot for Spot
    network_context = ""
    try:
        gw = await opn_read_gateways()
        items = gw.get("items") or []
        gw_lines = [f"  {g.get('name','?')}: {g.get('status','?')} loss={g.get('loss','?')} rtt={g.get('delay','?')}" for g in items[:6]]
        wg = await opn_read_wireguard()
        peers = (wg.get("rows") or wg.get("items") or [])
        wg_lines = [f"  {p.get('name','?')}: {'up' if p.get('status') == 'up' else 'down'} endpoint={p.get('endpoint','?')}" for p in peers[:6]]
        unifi_devs = await unifi_read_devices()
        devs = (unifi_devs.get("data") or [])
        dev_lines = [f"  {d.get('name') or d.get('mac','?')}: {d.get('state',0)} uptime={d.get('uptime','?')}" for d in devs[:8]]
        network_context = (
            "\nNETWORK STATE:\n"
            "OPNsense Gateways:\n" + ("\n".join(gw_lines) or "  none") + "\n"
            "WireGuard Peers:\n" + ("\n".join(wg_lines) or "  none") + "\n"
            "UniFi Devices:\n" + ("\n".join(dev_lines) or "  none") + "\n"
            "Use opn_read_firewall_rules/opn_read_aliases/opn_read_dhcp_leases/opn_read_dns_overrides/unifi_read_clients/unifi_read_networks for deeper data."
        )
    except Exception as _net_exc:
        network_context = f"\nNETWORK STATE: unavailable ({_net_exc})"

    system_prompt = (
        "You are Spot, the AI brain for Starfleet Command's private GPU cluster.\n\n"
        + identity + "\n\n"
        "RULES:\n"
        "- Answer ONLY from the LIVE FLEET STATE data below. Do not invent or assume any node status.\n"
        "- If a node is not listed or has no data, say so explicitly. Never guess.\n"
        "- Infra nodes (starfleet-core, dns-core, starfleet-tower, unimatrix6, spot-ui-01) have no ollama service. ONLINE = SSH reachable and functional.\n"
        "- You have conversation history — use it for continuity.\n"
        "- Be terse and direct.\n\n"
        "STARFLEET NETWORK TOPOLOGY:\n"
        "  WAN: 72.211.5.7 (Cloudflare tunnel: mcp.starfleetcore.com, spot.starfleetcore.com, ntfy.starfleetcore.com)\n"
        "  Router/Firewall: OPNsense at 192.168.1.1\n"
        "  Subnets:\n"
        "    192.168.1.0/24   — LAN (main)\n"
        "    192.168.10.0/24  — GPU Workers (W-01 through W-06)\n"
        "    192.168.50.0/24  — NAS/Storage (unimatrix6 NAS at 192.168.50.10)\n"
        "    192.168.60.0/24  — Infrastructure (spot-core .30, starfleet-core .20, UniFi .20:11443)\n"
        "    10.6.0.0/24      — WireGuard office VPN (wg0, port 51830)\n"
        "    10.7.0.0/24      — WireGuard phone VPN (wg1, port 51820)\n"
        "  UniFi controller: 192.168.60.20:11443 (site: starfleet)\n"
        "  DNS/NTP: dns-core (AdGuard), starfleet-core\n\n"
        "OPNSENSE FIREWALL RULES — CRITICAL KNOWLEDGE:\n"
        "  - Rules are processed TOP-DOWN, first match wins. Order matters.\n"
        "  - Always create ALLOW rules BEFORE BLOCK rules for the same traffic.\n"
        "  - To allow SSH only and block everything else: (1) create pass rule for TCP port 22, (2) create block rule for all, in that order.\n"
        "  - Interface names: WAN=igb0 (or WAN), LAN=igb1 (or LAN), worker subnet uses LAN or a VLAN interface.\n"
        "  - For WAN inbound rules, direction=in, interface=WAN.\n"
        "  - For inter-VLAN rules, use the source interface direction=in.\n"
        "  - After creating rules, always apply them (apply is called automatically by the action handler).\n"
        "  - When proposing multi-rule changes, propose each rule as a separate spot_action block sequentially.\n"
        "  - Risk: firewall rules are HIGH risk — always explain what the rule does before proposing.\n\n"
        "WORKER IPs:\n"
        "  W-01: 192.168.10.10 (RTX 3060 12GB) — general\n"
        "  W-02: 192.168.10.11 (TITAN Xp 12GB + M4000 8GB) — utility\n"
        "  W-03: 192.168.10.13 (GTX 1070 8GB + RTX 3060 12GB) — coding\n"
        "  W-04: 192.168.10.14 (P6000 24GB) — heavy\n"
        "  W-05: 192.168.10.15 (2x P100 16GB) — reasoning (stand-in, canonical=W-06)\n"
        "  W-06: 192.168.10.16 (P6000 24GB) — reasoning (canonical, currently offline)\n\n"
        "STARFLEET NETWORK TOPOLOGY:\n"
        "  WAN: 72.211.5.7 (Cloudflare tunnel: mcp.starfleetcore.com, spot.starfleetcore.com, ntfy.starfleetcore.com)\n"
        "  Router/Firewall: OPNsense at 192.168.1.1\n"
        "  Subnets:\n"
        "    192.168.1.0/24   — LAN (main)\n"
        "    192.168.10.0/24  — GPU Workers (W-01 through W-06)\n"
        "    192.168.50.0/24  — NAS/Storage (unimatrix6 NAS at 192.168.50.10)\n"
        "    192.168.60.0/24  — Infrastructure (spot-core .30, starfleet-core .20, UniFi .20:11443)\n"
        "    10.6.0.0/24      — WireGuard office VPN (wg0, port 51830)\n"
        "    10.7.0.0/24      — WireGuard phone VPN (wg1, port 51820)\n"
        "  UniFi controller: 192.168.60.20:11443 (site: starfleet)\n"
        "  DNS/NTP: dns-core (AdGuard), starfleet-core\n\n"
        "OPNSENSE FIREWALL RULES — CRITICAL KNOWLEDGE:\n"
        "  - Rules are processed TOP-DOWN, first match wins. Order matters.\n"
        "  - Always create ALLOW rules BEFORE BLOCK rules for the same traffic.\n"
        "  - To allow SSH only and block everything else: (1) create pass rule for TCP port 22, (2) create block rule for all, in that order.\n"
        "  - Interface names: WAN=igb0 (or WAN), LAN=igb1 (or LAN), worker subnet uses LAN or a VLAN interface.\n"
        "  - For WAN inbound rules, direction=in, interface=WAN.\n"
        "  - For inter-VLAN rules, use the source interface direction=in.\n"
        "  - After creating rules, always apply them (apply is called automatically by the action handler).\n"
        "  - When proposing multi-rule changes, propose each rule as a separate spot_action block sequentially.\n"
        "  - Risk: firewall rules are HIGH risk — always explain what the rule does before proposing.\n\n"
        "WORKER IPs:\n"
        "  W-01: 192.168.10.10 (RTX 3060 12GB) — general\n"
        "  W-02: 192.168.10.11 (TITAN Xp 12GB + M4000 8GB) — utility\n"
        "  W-03: 192.168.10.13 (GTX 1070 8GB + RTX 3060 12GB) — coding\n"
        "  W-04: 192.168.10.14 (P6000 24GB) — heavy\n"
        "  W-05: 192.168.10.15 (2x P100 16GB) — reasoning (stand-in, canonical=W-06)\n"
        "  W-06: 192.168.10.16 (P6000 24GB) — reasoning (canonical, currently offline)\n\n"
        "EXECUTION AUTHORITY (Level 1 — propose only, operator confirms):\n"
        "When you detect a fixable problem, end your reply with:\n"
        '```spot_action\n'
        '{"action":"<name>","target":"<worker|null>","reason":"<why>"}\n'
        '```\n'
        "Actions (fleet): restart_ollama, quarantine_worker, release_worker, nfs_sync, wake_worker\n"
        "Actions (network/OPNsense): opn_create_firewall_rule, opn_delete_firewall_rule, opn_create_vlan, opn_create_alias, opn_create_static_lease, opn_create_dns_override, opn_delete_dns_override\n"
        "Actions (network/UniFi): unifi_create_network, unifi_set_port_profile, unifi_block_client, unifi_restart_device\n"
        "Network action params go in a params key in the spot_action JSON block.\n"
        "One action per reply. Only propose when clearly needed. No block for healthy systems.\n\n"
        "LIVE FLEET STATE:\n"
        + fleet_context
        + network_context
    )

    append_chat_history("user", message)

    try:
        data = await call_chat_direct(CHAT_WORKER_URL, CHAT_MODEL, system_prompt, message, history=history)
        reply = data.get("message", {}).get("content", "")
        append_chat_history("assistant", reply)
        return ChatResult(
            ok=True, reply=reply,
            worker="spot-worker-04", model=CHAT_MODEL,
            role_requested=payload.role,
            execution_allowed=False, mutation_authority=False, mode="advisory",
            raw={"source": payload.source, "requested_mode": payload.mode, "direct_chat": True},
        )
    except Exception as exc:
        LOGGER.warning("chat_direct_failed falling back to exec: %r", exc)
        augmented = system_prompt + "\n\nOperator: " + message
        req = ExecRequest(prompt=augmented, role=payload.role, model=payload.model, stream=False, allow_fallback=True, allow_burst=True)
        result = await exec_route(req)
        reply = result.response
        append_chat_history("assistant", reply)
        return ChatResult(ok=bool(result.ok), reply=reply, worker=result.worker, model=result.model, role_requested=result.role_requested, execution_allowed=False, mutation_authority=False, mode="advisory", raw={"source": payload.source, "requested_mode": payload.mode, "gpu_lane": result.gpu_lane, "gpu_label": result.gpu_label})

@app.post("/exec", response_model=ExecResult)
async def exec_route(req: ExecRequest):
    if req.stream:
        raise HTTPException(status_code=400, detail={"message": "stream=true not supported"})
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
        append_decision({"ts": started, "worker": final_choice["worker"], "gpu_lane": final_choice["gpu_lane"], "model": final_choice["model"], "role": req.role, "priority": priority_of_request(req), "burst_mode": final_choice["burst_mode"], "status": "error", "error": repr(exc), "failures_seen": failures[-20:], "retry_events": retry_events[-20:], "penalty": current_penalty(final_choice["worker"]), "request_tier": request_tier, "premium_escalated": request_tier in ("premium", "reasoning"), "premium_reason": premium_reason, "routing_audit": routing_audit})
        append_routing_audit({"ts": started, "status": "error", "role": req.role, "priority": priority_of_request(req), "requested_model": req.model, "initial_worker": initial_choice["worker"], "final_worker": final_choice["worker"], "final_gpu_lane": final_choice["gpu_lane"], "final_gpu_label": final_choice["gpu_label"], "final_model": final_choice["model"], "retry_events": retry_events[-20:], **routing_audit})
        raise
    finally:
        async with ACTIVE_LOCK:
            decrement_active(final_choice["worker"], final_choice["gpu_lane"], final_choice["model"])

    mark_model_warm(final_choice["worker"], final_choice["model"])
    record_latency(final_choice["worker"], final_choice["gpu_lane"], final_choice["model"], req.role, data)
    routing_audit = classify_route(cfg, req, initial_choice, final_choice, retry_events)

    append_jsonl(EXEC_HISTORY_PATH, {"ts": started, "worker": final_choice["worker"], "worker_url": final_choice["worker_url"], "gpu_lane": final_choice["gpu_lane"], "gpu_label": final_choice["gpu_label"], "role_requested": req.role, "priority": priority_of_request(req), "model_requested": req.model, "model_used": final_choice["model"], "burst_mode": final_choice["burst_mode"], "prompt_chars": len(req.prompt), "response_chars": len(response_text), "total_duration": data.get("total_duration"), "load_duration": data.get("load_duration"), "prompt_eval_count": data.get("prompt_eval_count"), "eval_count": data.get("eval_count"), "retry_events": retry_events, "request_tier": request_tier, "premium_escalated": request_tier in ("premium", "reasoning"), "premium_reason": premium_reason, "routing_audit": routing_audit})
    append_decision({"ts": started, "worker": final_choice["worker"], "gpu_lane": final_choice["gpu_lane"], "gpu_label": final_choice["gpu_label"], "model": final_choice["model"], "role": req.role, "priority": priority_of_request(req), "burst_mode": final_choice["burst_mode"], "status": "ok", "failures_seen": failures[-20:], "retry_events": retry_events[-20:], "latency": worker_latency_summary(final_choice["worker"]), "request_tier": request_tier, "premium_escalated": request_tier in ("premium", "reasoning"), "premium_reason": premium_reason, "routing_audit": routing_audit})
    append_routing_audit({"ts": started, "status": "ok", "role": req.role, "priority": priority_of_request(req), "requested_model": req.model, "initial_worker": initial_choice["worker"], "final_worker": final_choice["worker"], "final_gpu_lane": final_choice["gpu_lane"], "final_gpu_label": final_choice["gpu_label"], "final_model": final_choice["model"], "retry_events": retry_events[-20:], **routing_audit})

    return ExecResult(ok=True, worker=final_choice["worker"], worker_url=final_choice["worker_url"], gpu_lane=final_choice["gpu_lane"], gpu_label=final_choice["gpu_label"], role_requested=req.role, model=final_choice["model"], response=response_text, raw=data)


@app.get("/stats/runtime")
async def stats_runtime():
    return spotcore_runtime_metrics_snapshot()

@app.get("/stats/runtime/health")
async def stats_runtime_health():
    return spotcore_runtime_health_snapshot()

@app.get("/stats/runtime/queue")
async def stats_runtime_queue():
    return spotcore_runtime_metrics_snapshot()["queue"]

@app.get("/stats/runtime/governance")
async def stats_runtime_governance():
    metrics = spotcore_runtime_metrics_snapshot()
    return {"schema": "runtime_governance_metrics_v1", "scope": "read_only", "mutation_authority": False, "governance": metrics["governance"], "archive": metrics["archive"], "validation": metrics["validation"], "routing": metrics["routing"]}

@app.get("/stats/runtime/telemetry")
async def runtime_telemetry():
    cfg = load_config()
    watch = load_watch_state()
    hosts = watch.get("hosts") or {}
    workers = {}
    for name, worker in (cfg.get("workers") or {}).items():
        status = hosts.get(name, {}) if isinstance(hosts, dict) else {}
        workers[name] = {"role": worker.get("primary_role") or worker.get("role"), "eligible": bool(worker.get("eligible", True)), "health": status.get("health") or status.get("status") or "unknown", "active_requests": ACTIVE_REQUESTS.get(name, 0), "warm_models": WARM_MODELS.get(name, {}), "latency_samples": len(LATENCY_HISTORY.get(name, [])), "models": status.get("models") or []}
    return {"ok": True, "ts": _now(), "executor": "spot-core", "mutation_authority": False, "worker_self_apply_allowed": False, "workers": workers, "active_requests": dict(ACTIVE_REQUESTS), "waiting_requests": dict(WAITING_REQUESTS)}

@app.get("/stats/runtime/journals")
def stats_runtime_journals(limit: int = 5):
    return _spot_runtime_journal_summary(limit=max(1, min(int(limit), 25)))

@app.get("/stats/runtime/review-lease")
def stats_runtime_review_lease():
    return _spot_review_lease_telemetry()

@app.get("/stats/runtime/governance-events")
def stats_runtime_governance_events(limit: int = 100):
    return _spot_governance_events(limit=limit)


def spotcore_runtime_count_queue_runs(queue_runs):
    result = {"total": 0, "pending": 0, "leased": 0, "completed": 0, "denied": 0, "expired": 0, "stale_leases": 0, "receipt_count": 0, "runs": 0, "malformed_runs": 0}
    now = int(time.time())
    if not queue_runs.exists():
        return result
    for state_path in queue_runs.glob("*/queue-state.json"):
        result["runs"] += 1
        try:
            state = json.loads(state_path.read_text())
        except Exception:
            result["malformed_runs"] += 1
            continue
        for candidate in state.get("candidates", {}).values():
            result["total"] += 1
            state_name = candidate.get("state", "unknown")
            if state_name in result:
                result[state_name] += 1
            lease = candidate.get("lease") or {}
            if state_name == "leased" and lease.get("expires_ts", 0) <= now:
                result["stale_leases"] += 1
            result["receipt_count"] += len(candidate.get("receipts", []))
    return result


def spotcore_runtime_count_logs(root):
    result = {"root_exists": root.exists(), "review_logs": 0, "action_logs": 0, "backup_logs": 0, "rollback_logs": 0, "learning_logs": 0, "archive_logs": 0}
    if not root.exists():
        return result
    for dirname, field in [("reviews","review_logs"),("actions","action_logs"),("backups","backup_logs"),("rollbacks","rollback_logs"),("learning","learning_logs"),("archive","archive_logs")]:
        d = root / dirname
        if d.exists():
            result[field] = sum(1 for item in d.rglob("*") if item.is_file())
    return result


def spotcore_runtime_metrics_snapshot():
    queue = spotcore_runtime_count_queue_runs(RUNTIME_QUEUE_RUNS_PATH)
    routing = summarize_routing_audit(ROUTING_AUDIT_WINDOW)
    logs = spotcore_runtime_count_logs(RUNTIME_METRICS_LOG_ROOT)
    return {"schema": "runtime_metrics_v1", "generated_at": _now(), "scope": "read_only", "mutation_authority": False, "queue": queue, "routing": {"exists": ROUTING_AUDIT_PATH.exists(), "lines": routing.get("window_count", 0), "malformed_lines": routing.get("malformed_lines", 0), "fallback_count": routing.get("fallbacks", 0), "violation_count": routing.get("violations", 0), "summary": routing}, "governance": {"deny_count": logs["action_logs"], "review_log_count": logs["review_logs"], "log_root_exists": logs["root_exists"]}, "archive": {"archive_log_count": logs["archive_logs"]}, "validation": {"latest_known_result": "external", "integrated_validator": False}, "raw_log_counts": logs}


def spotcore_runtime_health_snapshot():
    metrics = spotcore_runtime_metrics_snapshot()
    queue = metrics["queue"]
    routing = metrics["routing"]
    status = "ok"
    findings = []
    if queue["stale_leases"] > 0:
        status = "warn"; findings.append(f"stale_leases={queue['stale_leases']}")
    if routing["malformed_lines"] > 0:
        status = "warn"; findings.append(f"routing_malformed_lines={routing['malformed_lines']}")
    if routing["violation_count"] > 0:
        status = "warn"; findings.append(f"routing_violations={routing['violation_count']}")
    return {"schema": "runtime_health_summary_v1", "scope": "read_only", "mutation_authority": False, "status": status, "findings": findings, "queue_total": queue["total"], "queue_pending": queue["pending"], "queue_leased": queue["leased"], "queue_completed": queue["completed"], "queue_receipts": queue["receipt_count"], "routing_audit_lines": routing["lines"], "routing_fallback_count": routing["fallback_count"]}


def _spot_runtime_journal_summary(limit=5):
    import json as _json
    from pathlib import Path as _Path
    from datetime import datetime as _datetime, timezone as _timezone
    roots = [_Path("/mnt/collective/logs/spot"), _Path("/watch/state"), _Path("/watch/apply/journals")]
    categories = ["reviews", "actions", "backups", "rollbacks", "learning", "runtime"]
    def _validate_file(path):
        try:
            if path.suffix == ".json": _json.loads(path.read_text(errors="replace"))
            elif path.suffix == ".jsonl":
                for line in path.read_text(errors="replace").splitlines():
                    if line.strip(): _json.loads(line)
            return True, None
        except Exception as exc: return False, str(exc)
    def _summarize(path):
        files = [x for x in path.glob("*") if x.is_file()] if path.exists() else []
        recent = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:limit]
        invalid = []
        for f in files:
            if f.suffix not in {".json", ".jsonl"}: continue
            ok, err = _validate_file(f)
            if not ok: invalid.append({"file": str(f), "error": err})
        return {"path": str(path), "exists": path.exists(), "file_count": len(files), "invalid_count": len(invalid), "invalid": invalid[:25], "recent": [{"file": str(f), "size": f.stat().st_size} for f in recent]}
    primary = roots[0]
    return {"ts": _datetime.now(_timezone.utc).isoformat(), "mode": "read_only", "mutation_authority": False, "executor": "spot-core", "roots": {str(root): _summarize(root) for root in roots}, "categories": {name: _summarize(primary / name) for name in categories}}


def _spot_review_lease_telemetry():
    import json as _json, statistics as _statistics
    from pathlib import Path as _Path
    from datetime import datetime as _datetime, timezone as _timezone
    roots = [_Path("/mnt/collective/logs/spot/reviews"), _Path("/mnt/collective/logs/spot/runtime"), _Path("/watch/state"), _Path("/watch/apply/journals")]
    def _load(path):
        try:
            if path.suffix == ".json": return [_json.loads(path.read_text(errors="replace"))]
            if path.suffix == ".jsonl":
                out = []
                for line in path.read_text(errors="replace").splitlines():
                    if line.strip(): out.append(_json.loads(line))
                return out
        except Exception: return []
        return []
    rows = []
    for root in roots:
        if not root.exists(): continue
        for f in root.rglob("*"):
            if f.is_file() and f.suffix in {".json", ".jsonl"}:
                for row in _load(f):
                    if isinstance(row, dict): row["_source_file"] = str(f); rows.append(row)
    def _signal(row, terms):
        text = _json.dumps(row, sort_keys=True, default=str).lower()
        return any(x in text for x in terms)
    reviews = [r for r in rows if _signal(r, ["review", "worker-05", "verdict", "review_type"])]
    leases = [r for r in rows if _signal(r, ["lease", "lease_id", "lease_owner", "lease_ttl", "owner"])]
    latency_values = []
    for r in reviews:
        for key in ["latency_ms","duration_ms","review_latency_ms","elapsed_ms","runtime_ms","queue_latency_ms","total_ms"]:
            if key in r:
                try: latency_values.append(float(r[key]))
                except Exception: pass
                break
    latency_values = sorted(latency_values)
    if latency_values:
        p95_index = min(len(latency_values)-1, int(round((len(latency_values)-1)*0.95)))
        latency = {"count": len(latency_values), "min_ms": round(latency_values[0],3), "max_ms": round(latency_values[-1],3), "avg_ms": round(_statistics.mean(latency_values),3), "p50_ms": round(_statistics.median(latency_values),3), "p95_ms": round(latency_values[p95_index],3)}
    else:
        latency = {"count": 0, "min_ms": None, "max_ms": None, "avg_ms": None, "p50_ms": None, "p95_ms": None}
    verdicts = {}
    for r in reviews:
        verdict = str(r.get("verdict") or r.get("decision") or "unknown").upper()
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
    owners = {}
    for r in leases:
        owner = str(r.get("lease_owner") or r.get("owner") or r.get("worker") or "unknown")
        owners[owner] = owners.get(owner, 0) + 1
    return {"ts": _datetime.now(_timezone.utc).isoformat(), "mode": "read_only", "mutation_authority": False, "executor": "spot-core", "records_scanned": len(rows), "review": {"records": len(reviews), "verdicts": verdicts, "latency": latency}, "lease": {"records": len(leases), "owners": owners}}


def _spot_governance_events(limit=100):
    import json as _json, subprocess as _subprocess
    from datetime import datetime as _datetime, timezone as _timezone
    safe_limit = max(1, min(int(limit), 500))
    cmd = ["/watch/runtime/spot-governance-event-normalize.py", "--limit", str(safe_limit)]
    proc = _subprocess.run(cmd, check=False, stdout=_subprocess.PIPE, stderr=_subprocess.PIPE, text=True)
    events = []
    invalid = 0
    if proc.returncode == 0:
        for line in proc.stdout.splitlines():
            if not line.strip(): continue
            try: events.append(_json.loads(line))
            except Exception: invalid += 1
    return {"ts": _datetime.now(_timezone.utc).isoformat(), "mode": "read_only", "mutation_authority": False, "executor": "spot-core", "limit": safe_limit, "count": len(events), "invalid_lines": invalid, "normalizer_returncode": proc.returncode, "stderr": proc.stderr[-1000:] if proc.stderr else "", "events": events}

# --- SPOT OUTCOME LEARNING LOOP: API WIRING BEGIN ---
# Reference-only learning: logs outcomes and feedback. Does not authorize execution.
try:
    import json as _spot_json
    import sys as _spot_sys
    from pathlib import Path as _SpotPath
    from fastapi import Request as _SpotOutcomeRequest, Body as _SpotOutcomeBody

    _SPOT_REPO_ROOT = _SpotPath(__file__).resolve().parents[2]
    _SPOT_OUTCOME_LIB = _SPOT_REPO_ROOT / "watch" / "outcomes"
    if str(_SPOT_OUTCOME_LIB) not in _spot_sys.path:
        _spot_sys.path.insert(0, str(_SPOT_OUTCOME_LIB))

    from spot_outcomes import append_decision_record as _spot_append_decision_record
    from spot_outcomes import summarize_outcomes as _spot_summarize_outcomes
    from spot_risk import resolve_risk as _spot_resolve_risk

    def _spot_payload_field(payload, *names, default=None):
        if not isinstance(payload, dict):
            return default
        for name in names:
            if name in payload and payload[name] not in (None, ""):
                return payload[name]
        return default

    def _spot_payload_dict(body_bytes):
        try:
            if not body_bytes:
                return {}
            parsed = _spot_json.loads(body_bytes.decode("utf-8"))
            return parsed if isinstance(parsed, dict) else {"payload": parsed}
        except Exception:
            return {}

    def _spot_is_execute_path(path):
        path = str(path).lower()
        if "feedback" in path or "outcome-context" in path:
            return False
        tokens = ("/execute", "/actions/run", "/action/execute", "/remediate")
        return any(t in path for t in tokens)

    @app.middleware("http")
    async def _spot_outcome_execute_middleware(request: _SpotOutcomeRequest, call_next):
        body_bytes = b""
        payload = {}
        should_log = request.method.upper() == "POST" and _spot_is_execute_path(request.url.path)

        if should_log:
            body_bytes = await request.body()
            payload = _spot_payload_dict(body_bytes)

            async def receive():
                return {"type": "http.request", "body": body_bytes, "more_body": False}

            request = _SpotOutcomeRequest(request.scope, receive)

        response = await call_next(request)

        if should_log:
            action_type = _spot_payload_field(payload, "action_type", "action", "type", default=str(request.url.path).strip("/").replace("/", "_"))
            target = _spot_payload_field(payload, "target", "worker", "host", "node", default="unknown")
            params = _spot_payload_field(payload, "params", default=payload)
            risk = _spot_resolve_risk(action_type, target, params, _spot_payload_field(payload, "risk", "risk_class"))

            _spot_append_decision_record(
                action_type=action_type,
                target=target,
                params=params if isinstance(params, dict) else {"value": params},
                risk=risk,
                decision="executed",
                immediate_result={
                    "dispatch_observed": True,
                    "http_status": response.status_code,
                    "path": str(request.url.path)
                }
            )

        return response

    @app.post("/actions/feedback")
    async def spot_action_feedback(payload: dict = _SpotOutcomeBody(...)):
        action_type = _spot_payload_field(payload, "action_type", "action", "type", default="unknown")
        target = _spot_payload_field(payload, "target", "worker", "host", "node", default="unknown")
        params = _spot_payload_field(payload, "params", default={})
        decision = _spot_payload_field(payload, "decision", default="dismissed")
        if decision not in ("dismissed", "edited"):
            decision = "dismissed"
        risk = _spot_resolve_risk(action_type, target, params, _spot_payload_field(payload, "risk", "risk_class"))

        return _spot_append_decision_record(
            action_type=action_type,
            target=target,
            params=params if isinstance(params, dict) else {"value": params},
            risk=risk,
            decision=decision,
            immediate_result={"dispatch": "not_run", "source": "operator_feedback"},
            edited_delta=_spot_payload_field(payload, "edited_delta", "delta")
        )

    @app.get("/actions/outcome-context")
    async def spot_action_outcome_context(action_type: str = "", target: str = "", limit: int = 20):
        return {
            "context": _spot_summarize_outcomes(
                action_type=action_type or None,
                target=target or None,
                limit=limit
            )
        }

    try:
        _spot_original_build_recent_actions_context = build_recent_actions_context

        def build_recent_actions_context(*args, **kwargs):
            base = _spot_original_build_recent_actions_context(*args, **kwargs)
            extra = _spot_summarize_outcomes(limit=20)
            if extra and isinstance(base, str):
                return base + "\n\n" + extra
            return base
    except NameError:
        pass

except Exception as _spot_outcome_patch_error:
    print(f"[SPOT_OUTCOME_LEARNING_DISABLED] {_spot_outcome_patch_error}")
# --- SPOT OUTCOME LEARNING LOOP: API WIRING END ---
