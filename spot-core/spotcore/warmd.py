#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

CONFIG_PATH = Path(os.environ.get("SPOTCORE_CONFIG", "/srv/spot-core/config/cluster_config.json"))
EXEC_HISTORY_PATH = Path(os.environ.get("SPOTCORE_EXEC_HISTORY", "/srv/spot-core/shared_memory/exec-history.jsonl"))
STATE_PATH = Path(os.environ.get("SPOTCORE_WARMD_STATE", "/srv/spot-core/shared_memory/warmd-state.json"))
ROUTING_URL = os.environ.get("SPOTCORE_ROUTING_URL", "http://spot-core:8787/routing")
HTTP_TIMEOUT = float(os.environ.get("SPOTCORE_WARMD_HTTP_TIMEOUT", "20"))


def now_ts() -> int:
    return int(time.time())


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_config() -> dict[str, Any]:
    return load_json(CONFIG_PATH, {})


def load_state() -> dict[str, Any]:
    state = load_json(STATE_PATH, {})
    state.setdefault("refreshed", {})
    state.setdefault("models", {})
    state.setdefault("evicted", {})
    return state


def tail_jsonl(path: Path, max_lines: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[-max_lines:]
    except Exception:
        return []

    items: list[dict[str, Any]] = []
    for line in lines:
        try:
            items.append(json.loads(line))
        except Exception:
            continue
    return items


def explicit_targets(cfg: dict[str, Any]) -> list[dict[str, str]]:
    policy = cfg.get("warm_model_policy", {})
    out: list[dict[str, str]] = []
    for item in policy.get("targets", []):
        worker = str(item.get("worker", "")).strip()
        model = str(item.get("model", "")).strip()
        reason = str(item.get("reason", "explicit")).strip() or "explicit"
        if worker and model:
            out.append({"worker": worker, "model": model, "reason": reason})
    return out


def recent_targets(cfg: dict[str, Any]) -> list[dict[str, str]]:
    policy = cfg.get("warm_model_policy", {})
    warm_seconds = int(policy.get("warm_seconds", 3600))
    history_lines = int(policy.get("history_lines", 500))
    max_recent_targets = int(policy.get("max_recent_targets", 4))
    recent_roles = set(policy.get("recent_roles", ["coding", "heavy", "general"]))

    cutoff = now_ts() - warm_seconds
    items = tail_jsonl(EXEC_HISTORY_PATH, history_lines)

    out: list[dict[str, str]] = []
    seen: set[str] = set()

    for item in reversed(items):
        ts = int(item.get("ts", 0))
        if ts < cutoff:
            continue

        role = str(item.get("role_requested") or item.get("role") or "")
        worker = str(item.get("worker") or "")
        model = str(item.get("model_used") or item.get("model") or "")

        if not worker or not model or role not in recent_roles:
            continue

        key = f"{worker}:{model}"
        if key in seen:
            continue

        seen.add(key)
        out.append({"worker": worker, "model": model, "reason": f"recent_{role}"})

        if len(out) >= max_recent_targets:
            break

    return out


def combined_targets(cfg: dict[str, Any]) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen: set[str] = set()

    for item in explicit_targets(cfg) + recent_targets(cfg):
        key = f"{item['worker']}:{item['model']}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)

    return merged


async def fetch_routing() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(ROUTING_URL)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return {}


def active_model_keys(routing: dict[str, Any]) -> set[str]:
    active: set[str] = set()
    buckets = routing.get("active_model_requests") or {}
    for worker_name, lanes in buckets.items():
        if not isinstance(lanes, dict):
            continue
        for _, models in lanes.items():
            if not isinstance(models, dict):
                continue
            for model_name, count in models.items():
                try:
                    if int(count) > 0:
                        active.add(f"{worker_name}:{model_name}")
                except Exception:
                    continue
    return active


async def warm_target(
    client: httpx.AsyncClient,
    cfg: dict[str, Any],
    policy: dict[str, Any],
    state: dict[str, Any],
    target: dict[str, str],
) -> None:
    worker = target["worker"]
    model = target["model"]
    key = f"{worker}:{model}"

    refresh_seconds = int(policy.get("refresh_seconds", 300))
    keep_alive = policy.get("keep_alive", "30m")
    last = int(state["refreshed"].get(key, 0))

    if now_ts() - last < refresh_seconds:
        return

    worker_cfg = cfg.get("workers", {}).get(worker)
    if not worker_cfg:
        return

    url = worker_cfg["base_url"].rstrip("/") + "/api/generate"
    payload = {"model": model, "keep_alive": keep_alive}

    resp = await client.post(url, json=payload)
    resp.raise_for_status()

    state["refreshed"][key] = now_ts()
    state["models"][key] = {
        "worker": worker,
        "model": model,
        "reason": target.get("reason", "unknown"),
        "last_warm_ts": now_ts(),
    }

    print(f"[warmd] warmed {key} reason={target.get('reason', 'unknown')}", flush=True)


async def evict_stale(
    client: httpx.AsyncClient,
    cfg: dict[str, Any],
    policy: dict[str, Any],
    state: dict[str, Any],
    desired_keys: set[str],
    active_keys: set[str],
) -> None:
    if not bool(policy.get("evict_enabled", True)):
        return

    warm_seconds = int(policy.get("warm_seconds", 3600))

    for key, meta in list(state.get("models", {}).items()):
        if key in desired_keys:
            continue
        if key in active_keys:
            continue

        last = int(state["refreshed"].get(key, 0))
        if now_ts() - last < warm_seconds:
            continue

        worker = meta.get("worker")
        model = meta.get("model")
        worker_cfg = cfg.get("workers", {}).get(worker)
        if not worker or not model or not worker_cfg:
            continue

        url = worker_cfg["base_url"].rstrip("/") + "/api/generate"
        payload = {"model": model, "keep_alive": 0}

        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            state["evicted"][key] = now_ts()
            state["models"].pop(key, None)
            state["refreshed"].pop(key, None)
            print(f"[warmd] evicted {key}", flush=True)
        except Exception as exc:
            print(f"[warmd] evict_failed {key}: {exc!r}", flush=True)


async def loop_forever() -> None:
    while True:
        cfg = load_config()
        policy = cfg.get("warm_model_policy", {})

        if not bool(policy.get("enabled", True)):
            await asyncio.sleep(60)
            continue

        state = load_state()
        routing = await fetch_routing()
        active_keys = active_model_keys(routing)

        targets = combined_targets(cfg)
        desired_keys = {f"{t['worker']}:{t['model']}" for t in targets}

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                for target in targets:
                    await warm_target(client, cfg, policy, state, target)

                await evict_stale(client, cfg, policy, state, desired_keys, active_keys)

            save_json(STATE_PATH, state)
        except Exception as exc:
            print(f"[warmd] loop_error: {exc!r}", flush=True)

        await asyncio.sleep(int(policy.get("tick_seconds", 45)))


if __name__ == "__main__":
    asyncio.run(loop_forever())
