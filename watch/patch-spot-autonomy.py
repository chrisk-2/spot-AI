#!/usr/bin/env python3
"""Patch app.py for Spot Level-1 autonomy execution endpoint."""
import ast
from pathlib import Path

APP = Path("/home/ogre/spot-stack/spot-core/spotcore/app.py")
src = APP.read_text(encoding="utf-8")

# ── 1. Add SPOT_ACTION_ALLOWLIST after CHAT_HISTORY_WINDOW ──────────────────
OLD1 = 'CHAT_HISTORY_WINDOW = int(os.environ.get("SPOTCORE_CHAT_HISTORY_WINDOW", "20"))'
assert OLD1 in src, "PATCH1 anchor not found"
if "SPOT_ACTION_ALLOWLIST" not in src:
    NEW1 = OLD1 + '''

# Spot Level-1 autonomy allowlist
SPOT_ACTION_ALLOWLIST: dict[str, dict[str, Any]] = {
    "restart_ollama":   {"risk":"low",    "confirm_required":False, "targets":"workers"},
    "quarantine_worker":{"risk":"medium", "confirm_required":True,  "targets":"workers"},
    "release_worker":   {"risk":"low",    "confirm_required":False, "targets":"workers"},
    "nfs_sync":         {"risk":"low",    "confirm_required":False, "targets":None},
    "wake_worker":      {"risk":"low",    "confirm_required":False, "targets":"workers"},
}

SPOT_WORKER_MACS: dict[str, str] = {
    "spot-worker-01":"d8:43:ae:a9:c2:4c",
    "spot-worker-02":"d8:cb:8a:3e:94:fa",
    "spot-worker-03":"b4:2e:99:a5:17:ef",
    "spot-worker-04":"d8:43:ae:1f:88:2b",
    "spot-worker-05":"04:d4:c4:54:cd:6f",
    "spot-worker-06":"04:d4:c4:48:43:48",
}'''
    src = src.replace(OLD1, NEW1, 1)
    print("PATCH1 applied")
else:
    print("PATCH1 already applied, skipping")

# ── 2. Add ChatExecuteRequest model ─────────────────────────────────────────
OLD2 = 'SPOT_CORE_ROOT = Path(os.environ.get("SPOTCORE_ROOT", "/srv/spot-core"))'
assert OLD2 in src, "PATCH2 anchor not found"
if "ChatExecuteRequest" not in src:
    NEW2 = '''class ChatExecuteRequest(BaseModel):
    token: str
    action: str
    target: str | None = None
    reason: str = ""
    confirmed: bool = False


''' + OLD2
    src = src.replace(OLD2, NEW2, 1)
    print("PATCH2 applied")
else:
    print("PATCH2 already applied, skipping")

# ── 3. Add /chat/execute + helpers before /admin/nfs-status ─────────────────
OLD3 = '@app.get("/admin/nfs-status")'
assert OLD3 in src, "PATCH3 anchor not found"
if "/chat/execute" not in src:
    NEW3 = '''@app.post("/chat/execute")
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

    summary = f"[EXECUTED] {action} → {target or 'fleet'}: {'OK' if result.get('ok') else 'FAILED'}"
    append_chat_history("system", summary)
    return {"ok": result.get("ok", False), "action": action, "target": target, "risk": spec["risk"], "result": result}


''' + OLD3
    src = src.replace(OLD3, NEW3, 1)
    print("PATCH3 applied")
else:
    print("PATCH3 already applied, skipping")

# ── 4. Update system prompt with execution authority instructions ────────────
OLD4 = (
    '        "- You have conversation history below — use it for continuity across turns.\\n"\n'
    '        "- Be terse and direct.\\n\\n"'
)
assert OLD4 in src, "PATCH4 anchor not found"
if "EXECUTION AUTHORITY" not in src:
    NEW4 = (
        '        "- You have conversation history — use it for continuity.\\n"\n'
        '        "- Be terse and direct.\\n\\n"\n'
        '        "EXECUTION AUTHORITY (Level 1 — propose only, operator confirms):\\n"\n'
        '        "When you detect a fixable problem, end your reply with:\\n"\n'
        "        '```spot_action\\n'\n"
        '        \'{"action":"<name>","target":"<worker|null>","reason":"<why>"}\\n\'\n'
        "        '```\\n'\n"
        '        "Actions: restart_ollama, quarantine_worker, release_worker, nfs_sync, wake_worker\\n"\n'
        '        "One action per reply. Only propose when clearly needed. No block for healthy systems.\\n\\n"'
    )
    src = src.replace(OLD4, NEW4, 1)
    print("PATCH4 applied")
else:
    print("PATCH4 already applied, skipping")

# ── Validate and write ───────────────────────────────────────────────────────
try:
    ast.parse(src)
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")
    exit(1)

APP.write_text(src, encoding="utf-8")
print(f"OK patched {APP} ({len(src)} bytes, {src.count(chr(10))} lines)")
