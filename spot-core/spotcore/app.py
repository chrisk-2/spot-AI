#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import statistics
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Literal

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

APP_START_TS = int(time.time())
CONFIG_PATH = Path(os.environ.get("SPOTCORE_CONFIG", "/app/config/cluster_config.json"))
WATCH_STATE_PATH = Path(os.environ.get("SPOTCORE_WATCH_STATE", "/watch/state/fleet-status.json"))
EXEC_HISTORY_PATH = Path(os.environ.get("SPOTCORE_EXEC_HISTORY", "/app/shared_memory/exec-history.jsonl"))
DECISION_LOG_PATH = Path(os.environ.get("SPOTCORE_DECISION_LOG", "/app/shared_memory/decision-history.jsonl"))

HTTP_TIMEOUT = float(os.environ.get("SPOTCORE_HTTP_TIMEOUT", "240"))
LATENCY_WINDOW = int(os.environ.get("SPOTCORE_LATENCY_WINDOW", "100"))
DECISION_WINDOW = int(os.environ.get("SPOTCORE_DECISION_WINDOW", "200"))

ACTIVE_REQUESTS: dict[str, int] = {}
ACTIVE_GPU_REQUESTS: dict[str, dict[str, int]] = {}
ACTIVE_MODEL_REQUESTS: dict[str, dict[str, dict[str, int]]] = {}
WAITING_REQUESTS: dict[str, int] = defaultdict(int)
WARM_MODELS: dict[str, dict[str, int]] = defaultdict(dict)
LATENCY_HISTORY: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=LATENCY_WINDOW))
RECENT_DECISIONS: deque[dict[str, Any]] = deque(maxlen=DECISION_WINDOW)
PENALTY_BOX: dict[str, dict[str, Any]] = {}
FAILURE_HISTORY: dict[str, deque[int]] = defaultdict(lambda: deque(maxlen=50))
ACTIVE_LOCK = asyncio.Lock()

CONFIG_CACHE: dict[str, Any] | None = None
CONFIG_MTIME: float | None = None

ROLE = Literal["heavy", "coding", "general", "utility", "watcher"]


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


def _now() -> int:
    return int(time.time())


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True) + "\n")


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


def worker_status(name: str) -> dict[str, Any]:
    return (load_watch_state().get("hosts") or {}).get(name, {})


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


def installed_models_for_worker(worker_name: str, cfg: dict[str, Any]) -> set[str]:
    status = worker_status(worker_name)
    watcher_models = watcher_installed_models(status)
    if watcher_models:
        return set(watcher_models)
    return set(cfg["workers"].get(worker_name, {}).get("installed_models", []))


def is_worker_healthy(worker_name: str, cfg: dict[str, Any]) -> tuple[bool, str]:
    status = worker_status(worker_name)
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


def select_preferred_models(
    cfg: dict[str, Any],
    worker_name: str,
    gpu_lane: str,
    role: str,
    requested_model: str | None,
    allow_fallback: bool,
) -> list[str]:
    prefs = list(cfg["workers"][worker_name]["gpu_routes"][gpu_lane].get("model_preferences", {}).get(role, []))
    if requested_model:
        return [requested_model] + [m for m in prefs if m != requested_model] if allow_fallback else [requested_model]
    return prefs


def model_concurrency_limit(cfg: dict[str, Any], worker_name: str, gpu_lane: str, model: str) -> int | None:
    limits = cfg["workers"][worker_name]["gpu_routes"][gpu_lane].get("model_limits", {})
    return int(limits[model]) if model in limits else None


def score_candidate(cfg: dict[str, Any], worker_name: str, gpu_lane: str, role: str, model: str, burst_mode: bool) -> float:
    status = worker_status(worker_name)
    weights = cfg.get("score_weights", {})
    score = 1000.0
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
    if req.worker:
        workers = [req.worker]
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
            models = select_preferred_models(cfg, worker_name, gpu_lane, req.role, req.model, req.allow_fallback)
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


def record_retry_note(events: list[dict[str, Any]], chosen: dict[str, Any], phase: str, note: str) -> None:
    events.append(
        {
            "ts": _now(),
            "phase": phase,
            "worker": chosen["worker"],
            "worker_url": chosen["worker_url"],
            "gpu_lane": chosen["gpu_lane"],
            "gpu_label": chosen["gpu_label"],
            "model": chosen["model"],
            "note": note,
        }
    )


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


async def claim_alternate_candidate(
    cfg: dict[str, Any],
    req: ExecRequest,
    excluded_workers: set[str],
    preferred_model: str | None = None,
) -> dict[str, Any] | None:
    if req.worker:
        return None

    candidate_requests: list[ExecRequest] = []

    # First try to keep the same model across alternates.
    if preferred_model:
        candidate_requests.append(clone_request(req, model=preferred_model, allow_fallback=False))

    # Then fall back to the normal request behavior.
    candidate_requests.append(req)

    for candidate_req in candidate_requests:
        normal_scored, _ = gather_candidates(cfg, candidate_req, False)
        for _, candidate in normal_scored:
            if candidate["worker"] not in excluded_workers:
                return candidate

        if candidate_req.allow_burst:
            burst_scored, _ = gather_candidates(cfg, candidate_req, True)
            for _, candidate in burst_scored:
                if candidate["worker"] not in excluded_workers:
                    return candidate

    return None


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
        next_choice = await claim_alternate_candidate(
            cfg,
            req,
            attempted_workers,
            preferred_model=preferred_model,
        )
        if not next_choice:
            break

        await switch_active_allocation(current_choice, next_choice)
        current_choice = dict(next_choice)
        attempted_workers.add(current_choice["worker"])
        record_retry_note(retry_events, current_choice, "alternate_claim", f"claimed alternate worker #{alt_attempt + 1}")

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
        resp = await client.post(f"{worker_url}/api/embed", json={"model": model, "input": req.prompt})
        resp.raise_for_status()
        return resp.json()


app = FastAPI(title="Spot Core Control Plane", version="final-v4-smart-fallback")


@app.on_event("startup")
async def startup_event() -> None:
    load_config()
    seed_warm_models()


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
    }


@app.get("/fleet/ping")
async def fleet_ping() -> dict[str, Any]:
    cfg = load_config()
    out: dict[str, Any] = {}
    for name, worker_cfg in cfg["workers"].items():
        status = worker_status(name)
        healthy, reason = is_worker_healthy(name, cfg)
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
        }
    return out


@app.get("/stats/latency")
async def stats_latency() -> dict[str, Any]:
    cfg = load_config()
    return {name: worker_latency_summary(name) for name in cfg["workers"].keys()}


@app.get("/stats/recent-decisions")
async def stats_recent_decisions(limit: int = 25) -> dict[str, Any]:
    items = list(RECENT_DECISIONS)[-max(1, min(limit, 200)):]
    return {"count": len(items), "items": items}


@app.post("/quarantine/{worker_name}")
async def quarantine_worker(worker_name: str, seconds: int = 1800, reason: str = "manual_quarantine") -> dict[str, Any]:
    cfg = load_config()
    if worker_name not in cfg["workers"]:
        raise HTTPException(status_code=404, detail={"message": "unknown worker"})
    PENALTY_BOX[worker_name] = {
        "reason": reason,
        "until": _now() + max(60, seconds),
        "ts": _now(),
        "quarantined": True,
        "failure_count_window": failure_window_count(worker_name, 3600),
    }
    return {"ok": True, "worker": worker_name, "penalty": PENALTY_BOX[worker_name]}


@app.delete("/quarantine/{worker_name}")
async def unquarantine_worker(worker_name: str) -> dict[str, Any]:
    PENALTY_BOX.pop(worker_name, None)
    FAILURE_HISTORY.pop(worker_name, None)
    return {"ok": True, "worker": worker_name}


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
    final_choice = dict(chosen)
    embed_mode = is_embed_request(req.role, chosen["model"])

    try:
        if embed_mode:
            data = await call_embed(chosen["worker_url"], req, chosen["model"])
            response_text = f"Embedding request completed with model {chosen['model']}."
        else:
            final_choice, data, retry_events = await call_generate_with_retry(cfg, chosen, req)
            response_text = data.get("response", "")
    except Exception as exc:
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
            }
        )
        raise
    finally:
        async with ACTIVE_LOCK:
            decrement_active(final_choice["worker"], final_choice["gpu_lane"], final_choice["model"])

    mark_model_warm(final_choice["worker"], final_choice["model"])
    record_latency(final_choice["worker"], final_choice["gpu_lane"], final_choice["model"], req.role, data)

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
