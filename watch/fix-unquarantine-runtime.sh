#!/usr/bin/env bash
set -euo pipefail

APP="/home/ogre/spot-stack/spot-core/spotcore/app.py"
BACKUP="${APP}.fix-quarantine-$(date +%s).bak"

if [[ ! -f "$APP" ]]; then
  echo "ERROR: app.py not found at $APP" >&2
  exit 1
fi

cp "$APP" "$BACKUP"
echo "Backup saved to $BACKUP"

python3 - <<'PY'
from pathlib import Path
import re
import sys

app_path = Path("/home/ogre/spot-stack/spot-core/spotcore/app.py")
text = app_path.read_text(encoding="utf-8")

routing_line = 'ROUTING_AUDIT_PATH = Path(os.environ.get("SPOTCORE_ROUTING_AUDIT_LOG", "/watch/state/routing-audit.jsonl"))\n'
remediation_line = 'REMEDIATION_STATE_PATH = Path(os.environ.get("SPOTCORE_REMEDIATION_STATE", "/watch/state/remediation-state.json"))\n'

if remediation_line not in text:
    if routing_line not in text:
        raise SystemExit("Could not find ROUTING_AUDIT_PATH line to insert REMEDIATION_STATE_PATH")
    text = text.replace(routing_line, routing_line + remediation_line)

helper_block = '''
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


'''

if "def update_watch_state_quarantine(" not in text:
    marker = 'def worker_status(name: str) -> dict[str, Any]:\n'
    if marker not in text:
        raise SystemExit("Could not find worker_status marker for helper insertion")
    text = text.replace(marker, helper_block + marker)

post_pattern = re.compile(
    r'@app\.post\("/quarantine/\{worker_name\}"\)\n'
    r'async def quarantine_worker\(worker_name: str, seconds: int = 1800, reason: str = "manual_quarantine"\) -> dict\[str, Any\]:\n'
    r'(?:    .*\n)+?'
    r'    return \{"ok": True, "worker": worker_name, "penalty": PENALTY_BOX\[worker_name\]\}\n',
    re.MULTILINE
)

post_replacement = '''@app.post("/quarantine/{worker_name}")
async def quarantine_worker(worker_name: str, seconds: int = 1800, reason: str = "manual_quarantine") -> dict[str, Any]:
    cfg = load_config()
    if worker_name not in cfg["workers"]:
        raise HTTPException(status_code=404, detail={"message": "unknown worker"})

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

    return {"ok": True, "worker": worker_name, "penalty": penalty}
'''

text, count = post_pattern.subn(post_replacement, text)
if count != 1:
    raise SystemExit(f"Expected to replace 1 quarantine POST block, replaced {count}")

delete_pattern = re.compile(
    r'@app\.delete\("/quarantine/\{worker_name\}"\)\n'
    r'async def unquarantine_worker\(worker_name: str\) -> dict\[str, Any\]:\n'
    r'(?:    .*\n)+?'
    r'    return \{"ok": True, "worker": worker_name\}\n',
    re.MULTILINE
)

delete_replacement = '''@app.delete("/quarantine/{worker_name}")
async def unquarantine_worker(worker_name: str) -> dict[str, Any]:
    removed_penalty = PENALTY_BOX.pop(worker_name, None)
    FAILURE_HISTORY.pop(worker_name, None)
    update_remediation_quarantine(worker_name, False, "manual_release")
    update_watch_state_quarantine(worker_name, False)
    return {"ok": True, "worker": worker_name, "removed_penalty": removed_penalty is not None}
'''

text, count = delete_pattern.subn(delete_replacement, text)
if count != 1:
    raise SystemExit(f"Expected to replace 1 quarantine DELETE block, replaced {count}")

app_path.write_text(text, encoding="utf-8")
print("Patched app.py successfully")
PY

echo
echo "Patch complete."
echo "Now run:"
echo "  cd ~/spot-stack"
echo "  spot_restart"
echo "  curl -s http://127.0.0.1:8787/quarantine/spot-worker-01?seconds=300\\&reason=test -X POST | jq"
echo "  curl -s http://127.0.0.1:8787/fleet/ping | jq '.[\"spot-worker-01\"]'"
echo "  curl -s http://127.0.0.1:8787/quarantine/spot-worker-01 -X DELETE | jq"
echo "  curl -s http://127.0.0.1:8787/fleet/ping | jq '.[\"spot-worker-01\"]'"
