#!/usr/bin/env python3
import argparse
import hashlib
import json
import time
from pathlib import Path

VALID_STATES = {"pending", "leased", "completed", "denied", "expired"}
TERMINAL_STATES = {"completed", "denied", "expired"}

def now_ts():
    return int(time.time())

def stable_id(payload):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()[:24]

def load_json(path, default):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text())

def write_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    tmp.replace(p)

def receipt(root, candidate_id, event, data):
    rdir = Path(root) / "receipts"
    rdir.mkdir(parents=True, exist_ok=True)
    ts = now_ts()
    base = {
        "ts": ts,
        "candidate_id": candidate_id,
        "event": event,
        "scope": "fixture_only",
        "mutation_authority": False,
        "data": data,
    }
    rid = stable_id(base)
    out = rdir / f"{ts}-{candidate_id}-{event}-{rid}.json"
    out.write_text(json.dumps(base, indent=2, sort_keys=True) + "\n")
    return str(out)

def state_path(root):
    return Path(root) / "queue-state.json"

def cmd_init(args):
    state = {
        "schema": "runtime_queue_state_v1",
        "scope": "fixture_only",
        "created_ts": now_ts(),
        "candidates": {},
    }
    write_json(state_path(args.root), state)
    print(json.dumps({"ok": True, "state": str(state_path(args.root))}, sort_keys=True))

def cmd_enqueue(args):
    state = load_json(state_path(args.root), {
        "schema": "runtime_queue_state_v1",
        "scope": "fixture_only",
        "created_ts": now_ts(),
        "candidates": {},
    })

    payload = {
        "target": args.target,
        "action": args.action,
        "risk_class": args.risk_class,
        "scope": "fixture_only",
    }
    cid = stable_id(payload)

    existing = state["candidates"].get(cid)
    if existing and existing["state"] in TERMINAL_STATES:
        print(json.dumps({"ok": False, "blocked": "terminal_replay", "candidate_id": cid}, sort_keys=True))
        return 2

    if not existing:
        state["candidates"][cid] = {
            "candidate_id": cid,
            "state": "pending",
            "payload": payload,
            "created_ts": now_ts(),
            "updated_ts": now_ts(),
            "lease": None,
            "receipts": [],
        }
        rp = receipt(args.root, cid, "enqueue", payload)
        state["candidates"][cid]["receipts"].append(rp)
        write_json(state_path(args.root), state)

    print(json.dumps({"ok": True, "candidate_id": cid, "state": state["candidates"][cid]["state"]}, sort_keys=True))
    return 0

def cmd_show(args):
    state = load_json(state_path(args.root), {})
    print(json.dumps(state, indent=2, sort_keys=True))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="watch/runtime/queue/runs/default")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")

    enq = sub.add_parser("enqueue")
    enq.add_argument("--target", required=True)
    enq.add_argument("--action", required=True)
    enq.add_argument("--risk-class", default="low")

    sub.add_parser("show")

    args = ap.parse_args()
    if args.cmd == "init":
        return cmd_init(args)
    if args.cmd == "enqueue":
        return cmd_enqueue(args)
    if args.cmd == "show":
        return cmd_show(args)
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
