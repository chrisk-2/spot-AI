from __future__ import annotations

import copy
import json
import os
import threading
import time
import uuid
from typing import Any

import requests
from fastapi import FastAPI
from pydantic import BaseModel

APP = FastAPI(title="spot-gateway")

REQUEST_TIMEOUT = float(os.environ.get("SPOT_GATEWAY_TIMEOUT", "15"))
JOBS_OUT_ROOT = os.environ.get("JOBS_OUT_ROOT", "/mnt/collective/jobs_out")

WORKERS = json.loads(
    os.environ.get(
        "WORKERS_JSON",
        json.dumps(
            {
                "spot_exec": {
                    "base_url": "http://127.0.0.1:8787",
                    "exec_token": "changeme0",
                    "enabled": True,
                    "capabilities": ["jobs", "llm"],
                    "preferred": True,
                    "weight": 100,
                },
                "m5_exec": {
                    "base_url": "http://192.168.10.11:8789",
                    "exec_token": "changeme6",
                    "enabled": True,
                    "capabilities": ["jobs", "llm"],
                    "preferred": False,
                    "weight": 80,
                },
                "m5_watch": {
                    "base_url": "http://192.168.10.11:8791",
                    "exec_token": "changeme8",
                    "enabled": True,
                    "capabilities": ["jobs"],
                    "preferred": False,
                    "weight": 50,
                },
                "daystrom_exec": {
                    "base_url": "http://192.168.10.13:8782",
                    "exec_token": "changeme2",
                    "enabled": True,
                    "capabilities": ["jobs", "llm"],
                    "preferred": False,
                    "weight": 110,
                },
                "daystrom_watch": {
                    "base_url": "http://192.168.10.13:8783",
                    "exec_token": "changeme3",
                    "enabled": True,
                    "capabilities": ["jobs", "llm"],
                    "preferred": False,
                    "weight": 80,
                },

            }
        ),
    )
)

MODEL_VRAM_REQUIREMENTS = {
    "qwen2.5:14b": 10000,
    "llama3.1:8b": 6000,
    "deepseek-coder:6.7b": 5000,
    "codellama:7b": 5000,
    "qwen2.5-coder:7b": 6000,
    "mistral:7b": 5000,
    "phi3.5:latest": 3000,
    "gemma3:4b": 4500,
    "bge-m3:latest": 2000,
    "nomic-embed-text:latest": 1000,
}

MODEL_POLICIES = {
    # flagship general / light chat
    "llama3.1:8b": {
        "preferred_order": [
            "spot_exec",
            "daystrom_exec",
            "m5_exec",
            "daystrom_watch",
            "m5_watch",
        ],
    },
    "mistral:7b": {
        "preferred_order": [
            "spot_exec",
            "daystrom_exec",
            "m5_exec",
            "daystrom_watch",
            "m5_watch",
        ],
    },

    # coder lane
    "deepseek-coder:6.7b": {
        "preferred_order": [
            "daystrom_exec",
            "spot_exec",
            "m5_exec",
            "daystrom_watch",
            "m5_watch",
        ],
    },
    "codellama:7b": {
        "preferred_order": [
            "daystrom_exec",
            "spot_exec",
            "m5_exec",
            "daystrom_watch",
            "m5_watch",
        ],
    },
    "qwen2.5-coder:7b": {
        "preferred_order": [
            "daystrom_exec",
            "spot_exec",
            "m5_exec",
            "daystrom_watch",
            "m5_watch",
        ],
    },

    # heavy / 14b: Spot first, Daystrom backup
    "qwen2.5:14b": {
        "preferred_order": [
            "spot_exec",
            "daystrom_exec",
        ],
    },

    # embeddings / utility
    "nomic-embed-text:latest": {
        "preferred_order": [
            "m5_exec",
            "daystrom_exec",
            "spot_exec",
            "daystrom_watch",
            "m5_watch",
        ],
    },
    "bge-m3:latest": {
        "preferred_order": [
            "m5_exec",
            "daystrom_exec",
            "spot_exec",
            "daystrom_watch",
            "m5_watch",
        ],
    },

    # tiny / heartbeat / watch lane
    "phi3.5:latest": {
        "preferred_order": [
            "m5_watch",
            "daystrom_watch",
            "m5_exec",
            "daystrom_exec",
            "spot_exec",
        ],
    },
    "gemma3:4b": {
        "preferred_order": [
            "m5_watch",
            "daystrom_watch",
            "m5_exec",
            "daystrom_exec",
            "spot_exec",
        ],
    },
}

class ExecBody(BaseModel):
    worker: str
    cmd: str
    args: dict[str, Any] = {}


class AutoExecBody(BaseModel):
    cmd: str
    args: dict[str, Any] = {}
    preferred_worker: str | None = None
    require_capability: str | None = None
    async_mode: bool = False


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    s = str(value).strip().replace("%", "").replace("W", "")
    try:
        return float(s)
    except Exception:
        return default


def _worker_post(
    name: str,
    cmd: str,
    args: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    cfg = WORKERS.get(name)
    if not cfg or not cfg.get("enabled", False):
        return {"ok": False, "error": "worker_disabled", "worker": name}

    try:
        r = requests.post(
            f"{cfg['base_url']}/exec",
            json={"cmd": cmd, "args": args or {}},
            headers={"x-exec-token": cfg["exec_token"]},
            timeout=timeout or REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"ok": False, "error": "gateway_error", "worker": name, "detail": str(exc)}


def _worker_get_health(name: str) -> dict[str, Any]:
    cfg = WORKERS.get(name)
    if not cfg or not cfg.get("enabled", False):
        return {"ok": False, "error": "worker_disabled", "worker": name}

    try:
        r = requests.get(f"{cfg['base_url']}/health", timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"ok": False, "error": "unreachable", "worker": name, "detail": str(exc)}


def _extract_model(cmd: str, args: dict[str, Any]) -> str | None:
    if cmd != "run_job":
        return None

    params = args.get("params") or {}
    return (
        params.get("model")
        or args.get("model")
        or params.get("llm_model")
        or args.get("llm_model")
    )


def _min_vram_for_model(model: str | None) -> int | None:
    if not model:
        return None
    return MODEL_VRAM_REQUIREMENTS.get(model)


def _policy_for_model(model: str | None) -> dict[str, Any]:
    if not model:
        return {}
    return MODEL_POLICIES.get(model, {})

def pick_worker_in_order(
    worker_names: list[str],
    capability: str = "jobs",
    min_vram_mb: int | None = None,
) -> dict[str, Any] | None:
    for name in worker_names:
        cfg = WORKERS.get(name)
        if not cfg:
            continue

        if not cfg.get("enabled"):
            continue

        if capability not in cfg.get("capabilities", []):
            continue

        health = _worker_get_health(name)
        if not health.get("ok"):
            continue

        gpu = _worker_post(name, "gpu_status", {})
        if not gpu.get("ok"):
            continue

        selected = gpu.get("selected_gpu") or {}
        free_vram = int(selected.get("vram_free_mb", 0) or 0)

        if min_vram_mb is not None and free_vram < min_vram_mb:
            continue

        gpu_util = _to_float(selected.get("util_gpu"), 0.0)
        temp_c = _to_float(selected.get("temp_c"), 0.0)

        return {
            "worker": name,
            "policy": "preferred_order",
            "reason": "preferred_order_first_match",
            "free_vram_mb": free_vram,
            "gpu_util": gpu_util,
            "temp_c": temp_c,
            "health": health,
            "gpu_status": gpu,
        }

    return None

def pick_worker(
    capability: str = "jobs",
    min_vram_mb: int | None = None,
    preferred_order: list[str] | None = None,
    allowed_workers: list[str] | None = None,
) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []

    for name, cfg in WORKERS.items():

        if allowed_workers and name not in allowed_workers:
            continue

        if not cfg.get("enabled"):
            continue

        if capability not in cfg.get("capabilities", []):
            continue

        health = _worker_get_health(name)
        if not health.get("ok"):
            continue

        gpu = _worker_post(name, "gpu_status", {})
        if not gpu.get("ok"):
            continue

        selected = gpu.get("selected_gpu") or {}
        free_vram = int(selected.get("vram_free_mb", 0) or 0)

        if min_vram_mb is not None and free_vram < min_vram_mb:
            continue

        gpu_util = _to_float(selected.get("util_gpu"), 0.0)
        temp_c = _to_float(selected.get("temp_c"), 0.0)

        preferred_bonus = 1500 if cfg.get("preferred") else 0
        weight_bonus = int(cfg.get("weight", 0)) * 10

        order_bonus = 0
        if preferred_order and name in preferred_order:
            order_bonus = (len(preferred_order) - preferred_order.index(name)) * 1000

        watch_penalty = 0
        if name == "m5_watch" and capability != "watch":
            watch_penalty = 2500

        score = (
            (free_vram * 2)
            + weight_bonus
            + preferred_bonus
            + order_bonus
            - watch_penalty
            - int(gpu_util * 10)
            - int(temp_c * 2)
        )

        candidates.append(
            {
                "worker": name,
                "score": score,
                "free_vram_mb": free_vram,
                "gpu_util": gpu_util,
                "temp_c": temp_c,
                "health": health,
                "gpu_status": gpu,
            }
        )

    if not candidates:
        return None

    candidates.sort(key=lambda x: x["score"], reverse=True)
    winner = candidates[0]
    winner["policy"] = "scored_best_fit"
    winner["reason"] = "highest_score"
    return winner


def _prepare_async_job_args(
    cmd: str,
    args: dict[str, Any],
    picked_worker: str,
) -> tuple[dict[str, Any], str | None, str | None]:
    args2 = copy.deepcopy(args or {})
    if cmd != "run_job":
        return args2, None, None

    job_name = args2.get("job")
    params = args2.setdefault("params", {})

    if not job_name:
        return args2, None, None

    if "job_id" in params:
        job_id = str(params["job_id"])
    else:
        job_id = uuid.uuid4().hex[:12]
        params["job_id"] = job_id

    out_dir = params.get("out_dir")
    if not out_dir:
        out_dir = f"{JOBS_OUT_ROOT}/{job_name}/{job_id}"
        params["out_dir"] = out_dir

    params["JOB_ID"] = job_id
    params["OUT_DIR"] = out_dir
    params.setdefault("LLM_NODE_NAME", picked_worker)

    return args2, job_id, out_dir


def _launch_async_worker_call(worker_name: str, cmd: str, args: dict[str, Any]) -> None:
    def runner() -> None:
        try:
            _worker_post(worker_name, cmd, args, timeout=3600)
        except Exception:
            pass

    threading.Thread(target=runner, daemon=True).start()


def _forced_worker_for_request(cmd: str, args: dict[str, Any]) -> str | None:
    model = _extract_model(cmd, args)
    policy = _policy_for_model(model)
    return policy.get("forced_worker")


def _preferred_order_for_request(
    cmd: str,
    args: dict[str, Any],
    preferred_worker: str | None = None,
) -> list[str]:
    model = _extract_model(cmd, args)
    policy = _policy_for_model(model)

    if preferred_worker:
        return [preferred_worker]

    base = list(policy.get("preferred_order", []))
    return base

@APP.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "spot-gateway", "ts": int(time.time())}


@APP.get("/cluster/status")
def cluster_status() -> dict[str, Any]:
    workers = {name: _worker_get_health(name) for name in WORKERS}
    return {"ok": True, "ts": int(time.time()), "workers": workers}


@APP.get("/cluster/gpu_status")
def cluster_gpu_status() -> dict[str, Any]:
    workers = {name: _worker_post(name, "gpu_status", {}) for name in WORKERS}
    return {"ok": True, "ts": int(time.time()), "workers": workers}


@APP.post("/tool/exec")
def tool_exec(body: ExecBody) -> dict[str, Any]:
    timeout = 3600 if body.cmd == "run_job" else REQUEST_TIMEOUT
    return _worker_post(body.worker, body.cmd, body.args, timeout=timeout)

@APP.post("/cluster/auto_exec")
def cluster_auto_exec(body: AutoExecBody) -> dict[str, Any]:
    capability = body.require_capability or "jobs"
    args = body.args or {}
    cmd = body.cmd
    model = _extract_model(cmd, args)

    forced = _forced_worker_for_request(cmd, args)
    preferred_order = None
    min_vram_mb = _min_vram_for_model(model)

    if forced:
        picked_name = forced
        best = {
            "worker": forced,
            "reason": "forced_worker_policy",
            "model": model,
            "capability": capability,
            "min_vram_mb": min_vram_mb,
            "preferred_order": [],
        }
    else:
        preferred_order = _preferred_order_for_request(
            cmd=cmd,
            args=args,
            preferred_worker=body.preferred_worker,
        )

        best = None

        if preferred_order:
            best = pick_worker_in_order(
                worker_names=preferred_order,
                capability=capability,
                min_vram_mb=min_vram_mb,
            )

        if not best:
            best = pick_worker(
                capability=capability,
                min_vram_mb=min_vram_mb,
                preferred_order=preferred_order,
            )

        if not best:
            return {
                "ok": False,
                "error": "no_candidates",
                "cmd": cmd,
                "model": model,
                "required_capability": capability,
                "min_vram_mb": min_vram_mb,
                "preferred_order": preferred_order,
                "route_policy": "no_match",
                "route_reason": "no_candidates",
            }

        picked_name = best["worker"]

    timeout = 3600 if cmd == "run_job" else REQUEST_TIMEOUT
    result = _worker_post(picked_name, cmd, args, timeout=timeout)

    if not isinstance(result, dict):
        return {
            "ok": False,
            "error": "invalid_worker_response",
            "picked_worker": picked_name,
            "cmd": cmd,
            "model": model,
            "required_capability": capability,
            "min_vram_mb": min_vram_mb,
            "preferred_order": preferred_order,
            "best": best,
            "route_policy": (best or {}).get("policy", "unknown"),
            "route_reason": (best or {}).get("reason", "worker_returned_non_dict"),
        }

    route_reason = (best or {}).get("reason", "picked_worker")
    route_policy = (best or {}).get("policy")

    if not route_policy:
        if route_reason == "forced_worker_policy":
            route_policy = "forced_worker"
        elif preferred_order:
            route_policy = "preferred_order"
        elif min_vram_mb and min_vram_mb > 0:
            route_policy = "best_vram_fit"
        else:
            route_policy = "default"

    result.setdefault("picked_worker", picked_name)
    result.setdefault("best", best)
    result.setdefault("model", model)

    result.setdefault("route_policy", route_policy)
    result.setdefault("route_reason", route_reason)
    result.setdefault("required_capability", capability)
    result.setdefault("min_vram_mb", min_vram_mb)
    result.setdefault("preferred_order", preferred_order or [])
    result.setdefault("forced_worker", forced)
    result.setdefault("scheduler_cmd", cmd)

    return result
