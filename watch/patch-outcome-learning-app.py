#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import time

repo = Path.cwd()
app_path = repo / "spot-core" / "spotcore" / "app.py"
marker = "SPOT OUTCOME LEARNING LOOP: API WIRING BEGIN"

if not app_path.exists():
    print(f"RESULT: SKIP missing={app_path}")
    raise SystemExit(0)

text = app_path.read_text(encoding="utf-8")

if marker in text:
    print("RESULT: PASS app.py already patched")
    raise SystemExit(0)

if not re.search(r"\bapp\s*=\s*FastAPI\s*\(", text):
    print("RESULT: WARN app.py has no obvious `app = FastAPI(...)`; no API patch applied")
    raise SystemExit(0)

stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
shutil.copy2(app_path, app_path.with_suffix(app_path.suffix + f".bak-outcome-{stamp}"))

block = r'''

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
'''

app_path.write_text(text.rstrip() + block + "\n", encoding="utf-8")
print(f"RESULT: PASS patched={app_path}")
