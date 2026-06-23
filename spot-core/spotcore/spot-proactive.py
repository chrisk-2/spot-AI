#!/usr/bin/env python3
"""
spot-proactive.py — Spot's autonomous fleet assessment loop.
Runs inside the spot-core container alongside uvicorn.
Every INTERVAL seconds, asks Spot to assess the fleet and logs findings.
"""
import asyncio
import json
import logging
import os
import time
from pathlib import Path

import httpx

INTERVAL      = int(os.environ.get("SPOT_PROACTIVE_INTERVAL", "300"))   # 5 min default
DEDUP_WINDOW  = int(os.environ.get("SPOT_PROACTIVE_DEDUP", "1800"))     # 30 min dedup
CORE_URL      = os.environ.get("SPOT_CORE_URL", "http://127.0.0.1:8787")
ALERT_LOG     = Path(os.environ.get("SPOTCORE_WORKER_RECOVER_LOG",
                    "/home/ogre/spot-stack/watch/logs/worker-recover.jsonl"))
PROACTIVE_LOG = Path(os.environ.get("SPOT_PROACTIVE_LOG",
                    "/home/ogre/spot-stack/watch/logs/spot-proactive.jsonl"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [proactive] %(message)s")
log = logging.getLogger("spot.proactive")

# Dedup: track last notification time per action+target key
_last_notified: dict[str, float] = {}

ASSESSMENT_PROMPT = (
    "Perform a silent fleet assessment. Check for: offline workers, ollama service down, "
    "NFS offline, routing violations, workers with latency spiking above their normal baseline. "
    "If everything is healthy, reply with exactly: NOMINAL\n"
    "If you find one issue worth acting on, describe it in one sentence then propose an action. "
    "Do not propose actions for known slow workers (W-03, W-06) unless their latency has "
    "significantly worsened. Do not propose quarantine for workers already quarantined."
)


def dedup_key(action: dict) -> str:
    return f"{action.get('action','?')}:{action.get('target','fleet')}"


def is_deduped(key: str) -> bool:
    last = _last_notified.get(key, 0)
    return (time.time() - last) < DEDUP_WINDOW


def mark_notified(key: str) -> None:
    _last_notified[key] = time.time()


def append_log(path: Path, payload: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")
    except Exception as exc:
        log.warning("log_write_failed path=%s error=%r", path, exc)


def parse_spot_action(text: str) -> dict | None:
    import re
    m = re.search(r"```spot_action\s*([\s\S]*?)```", text)
    if not m:
        return None
    try:
        return json.loads(m.group(1).strip())
    except Exception:
        return None


def strip_spot_action(text: str) -> str:
    import re
    return re.sub(r"```spot_action[\s\S]*?```", "", text).strip()


async def wait_for_core(timeout: int = 60) -> bool:
    """Wait for spot-core API to be ready before starting loop."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{CORE_URL}/health")
                if r.status_code == 200:
                    return True
        except Exception:
            pass
        await asyncio.sleep(3)
    return False


async def assess_fleet() -> None:
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{CORE_URL}/chat", json={
                "message": ASSESSMENT_PROMPT,
                "role": "general",
                "source": "spot-proactive",
                "mode": "advisory",
            })
            r.raise_for_status()
            data = r.json()

        reply = data.get("reply", "").strip()
        action = parse_spot_action(reply)
        clean = strip_spot_action(reply)

        # Log full assessment
        append_log(PROACTIVE_LOG, {
            "ts": ts,
            "event": "spot_assessment",
            "reply": clean,
            "action": action,
            "worker": data.get("worker"),
            "model": data.get("model"),
        })

        if reply.upper().startswith("NOMINAL") and not action:
            log.info("assessment=NOMINAL")
            return

        log.info("assessment=%r action=%r", clean[:120], action)

        # Write to alert log for dashboard if there's an action or non-nominal finding
        if action:
            key = dedup_key(action)
            if is_deduped(key):
                log.info("deduped key=%s", key)
                return
            mark_notified(key)
            append_log(ALERT_LOG, {
                "ts": ts,
                "event": "spot_assessment",
                "worker": action.get("target") or "fleet",
                "detail": clean[:200],
                "action": action.get("action"),
                "reason": action.get("reason", ""),
                "risk": action.get("risk", "low"),
                "proposed_action": action,
            })
        elif clean and not clean.upper().startswith("NOMINAL"):
            # Non-nominal finding but no action — still surface it
            append_log(ALERT_LOG, {
                "ts": ts,
                "event": "spot_assessment",
                "worker": "fleet",
                "detail": clean[:200],
                "action": None,
                "reason": "advisory",
            })

    except Exception as exc:
        log.error("assessment_failed error=%r", exc)
        append_log(PROACTIVE_LOG, {
            "ts": ts,
            "event": "spot_assessment_error",
            "error": repr(exc),
        })


# --- SPOT OUTCOME RESOLVER HOOK BEGIN ---
def spot_outcome_resolver_tick():
    """Deferred outcome resolver. Safe: appends outcome_update records only."""
    import subprocess
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    resolver = repo_root / "watch" / "outcomes" / "spot-outcome-resolve.py"
    if resolver.exists():
        subprocess.run(
            [sys.executable, str(resolver), "--min-age-seconds", "180", "--limit", "25"],
            cwd=str(repo_root),
            timeout=45,
            check=False
        )
# --- SPOT OUTCOME RESOLVER HOOK END ---


async def main() -> None:
    log.info("proactive_loop_starting interval=%ds dedup=%ds", INTERVAL, DEDUP_WINDOW)

    # Wait for core to be ready
    ready = await wait_for_core(timeout=120)
    if not ready:
        log.error("core_not_ready after 120s — exiting")
        return

    log.info("core_ready — starting assessment loop")

    # Stagger first run by 60s to let core fully settle
    await asyncio.sleep(60)

    while True:
        await assess_fleet()
        await asyncio.to_thread(spot_outcome_resolver_tick)
        await asyncio.sleep(INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
