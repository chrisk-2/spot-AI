#!/usr/bin/env python3
"""Patch app.py to add Spot memory, self-knowledge, and personality."""
import re
from pathlib import Path

APP = Path("/home/ogre/spot-stack/spot-core/spotcore/app.py")
src = APP.read_text(encoding="utf-8")
original = src

# ── 1. Add memory constants after RUNTIME_METRICS_LOG_ROOT ──────────────────
OLD1 = 'RUNTIME_METRICS_LOG_ROOT = Path(os.environ.get("SPOTCORE_RUNTIME_LOG_ROOT", "/mnt/collective/logs/spot"))'
NEW1 = OLD1 + '''

# Spot persistent memory
CHAT_HISTORY_PATH = Path(os.environ.get("SPOTCORE_CHAT_HISTORY", "/home/ogre/spot-stack/watch/logs/spot-chat-history.jsonl"))
CHAT_HISTORY_WINDOW = int(os.environ.get("SPOTCORE_CHAT_HISTORY_WINDOW", "20"))'''
assert OLD1 in src, "PATCH1 anchor not found"
src = src.replace(OLD1, NEW1, 1)

# ── 2. Add helper functions before build_spot_fleet_context ──────────────────
OLD2 = 'def build_spot_fleet_context() -> str:'
NEW2 = '''def load_chat_history(limit: int = CHAT_HISTORY_WINDOW) -> list[dict]:
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
            f.write(json.dumps({"ts": _now(), "role": role, "content": content}, sort_keys=True) + "\\n")
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
        return "\\n".join(parts)
    except Exception:
        return "  Action log unavailable."


def build_spot_identity() -> str:
    """Spot's fixed identity block."""
    uptime_sec = _now() - APP_START_TS
    return (
        "IDENTITY:\\n"
        "  Name: Spot\\n"
        "  Role: AI ops brain for Starfleet Command's private GPU cluster\\n"
        "  Operator: ogre (Chris)\\n"
        f"  Control plane uptime: {uptime_sec // 3600}h {(uptime_sec % 3600) // 60}m\\n"
        "  Style: terse, direct, no fluff. You know this fleet intimately.\\n"
        "  Known issues: W-03 is the weak node (GTX 1070 8GB, slow). W-06 has high p50.\\n"
        "  Authority: advisory only — propose actions, operator confirms execution."
    )


def build_spot_fleet_context() -> str:'''
assert OLD2 in src, "PATCH2 anchor not found"
src = src.replace(OLD2, NEW2, 1)

# ── 3. Add NFS + identity + recent actions to fleet context ─────────────────
OLD3 = '    # NFS status\n    lines.append("")\n    lines.append(f"NFS: {\'AVAILABLE\' if nfs_available() else \'OFFLINE - buffering to W-01\'}")\n\n    return "\\n".join(lines)'
NEW3 = '''    # NFS status
    lines.append("")
    lines.append(f"NFS: {\'AVAILABLE\' if nfs_available() else \'OFFLINE - buffering to W-01\'}")

    lines.append("")
    lines.append("RECENT ACTIONS:")
    lines.append(build_recent_actions_context(5))

    return "\\n".join(lines)'''
assert OLD3 in src, "PATCH3 anchor not found"
src = src.replace(OLD3, NEW3, 1)

# ── 4. Replace call_chat_direct to pass message history ─────────────────────
OLD4 = '''async def call_chat_direct(worker_url: str, model: str, system: str, user: str) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.post(f"{worker_url}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()'''
NEW4 = '''async def call_chat_direct(worker_url: str, model: str, system: str, user: str, history: list[dict] | None = None) -> dict:
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
        return resp.json()'''
assert OLD4 in src, "PATCH4 anchor not found"
src = src.replace(OLD4, NEW4, 1)

# ── 5. Replace chat_route to add identity, history load/save ────────────────
OLD5 = '''    fleet_context = build_spot_fleet_context()

    system_prompt = (
        "You are Spot, the AI operations assistant for Starfleet Command's private GPU cluster.\\n\\n"
        "RULES:\\n"
        "- Answer ONLY from the LIVE FLEET STATE data below. Do not invent or assume any node status.\\n"
        "- If a node is not listed or has no data, say so explicitly. Never guess.\\n"
        "- Infra nodes (starfleet-core, dns-core, starfleet-tower, unimatrix6, spot-ui-01) have no ollama service. ONLINE = SSH reachable and functional.\\n"
        "- Be concise and direct.\\n\\n"
        "LIVE FLEET STATE:\\n"
        + fleet_context
    )

    try:
        data = await call_chat_direct(CHAT_WORKER_URL, CHAT_MODEL, system_prompt, message)
        reply = data.get("message", {}).get("content", "")
        return ChatResult(
            ok=True, reply=reply,
            worker="spot-worker-04", model=CHAT_MODEL,
            role_requested=payload.role,
            execution_allowed=False, mutation_authority=False, mode="advisory",
            raw={"source": payload.source, "requested_mode": payload.mode, "direct_chat": True},
        )
    except Exception as exc:
        LOGGER.warning("chat_direct_failed falling back to exec: %r", exc)
        augmented = system_prompt + "\\n\\nOperator: " + message
        req = ExecRequest(prompt=augmented, role=payload.role, model=payload.model, stream=False, allow_fallback=True, allow_burst=True)
        result = await exec_route(req)
        return ChatResult(ok=bool(result.ok), reply=result.response, worker=result.worker, model=result.model, role_requested=result.role_requested, execution_allowed=False, mutation_authority=False, mode="advisory", raw={"source": payload.source, "requested_mode": payload.mode, "gpu_lane": result.gpu_lane, "gpu_label": result.gpu_label})'''
NEW5 = '''    fleet_context = build_spot_fleet_context()
    identity = build_spot_identity()
    history = load_chat_history()

    system_prompt = (
        "You are Spot, the AI brain for Starfleet Command's private GPU cluster.\\n\\n"
        + identity + "\\n\\n"
        "RULES:\\n"
        "- Answer ONLY from the LIVE FLEET STATE data below. Do not invent or assume any node status.\\n"
        "- If a node is not listed or has no data, say so explicitly. Never guess.\\n"
        "- Infra nodes (starfleet-core, dns-core, starfleet-tower, unimatrix6, spot-ui-01) have no ollama service. ONLINE = SSH reachable and functional.\\n"
        "- You have conversation history below — use it for continuity across turns.\\n"
        "- Be terse and direct.\\n\\n"
        "LIVE FLEET STATE:\\n"
        + fleet_context
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
        augmented = system_prompt + "\\n\\nOperator: " + message
        req = ExecRequest(prompt=augmented, role=payload.role, model=payload.model, stream=False, allow_fallback=True, allow_burst=True)
        result = await exec_route(req)
        reply = result.response
        append_chat_history("assistant", reply)
        return ChatResult(ok=bool(result.ok), reply=reply, worker=result.worker, model=result.model, role_requested=result.role_requested, execution_allowed=False, mutation_authority=False, mode="advisory", raw={"source": payload.source, "requested_mode": payload.mode, "gpu_lane": result.gpu_lane, "gpu_label": result.gpu_label})'''
assert OLD5 in src, "PATCH5 anchor not found"
src = src.replace(OLD5, NEW5, 1)

# ── Verify and write ─────────────────────────────────────────────────────────
import ast
try:
    ast.parse(src)
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")
    exit(1)

APP.write_text(src, encoding="utf-8")
print(f"OK patched {APP} ({len(src)} bytes, {src.count(chr(10))} lines)")
