#!/usr/bin/env python3
import argparse
import hashlib
import json
import time
from pathlib import Path

TERMINAL_STATES = {"completed", "denied", "expired"}

def now_ts():
    return int(time.time())

def load_state(root):
    return json.loads((Path(root) / "queue-state.json").read_text())

def write_state(root, state):
    p = Path(root) / "queue-state.json"
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
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
    rid = hashlib.sha256(json.dumps(base, sort_keys=True).encode()).hexdigest()[:16]
    out = rdir / f"{ts}-{candidate_id}-{event}-{rid}.json"
    out.write_text(json.dumps(base, indent=2, sort_keys=True) + "\n")
    return str(out)

def require_candidate(state, cid):
    if cid not in state["candidates"]:
        raise SystemExit(json.dumps({
            "ok": False,
            "blocked": "missing_candidate",
            "candidate_id": cid
        }, sort_keys=True))
    return state["candidates"][cid]

def cmd_lease(args):
    state = load_state(args.root)
    c = require_candidate(state, args.candidate_id)

    if args.owner != "spot-core":
        print(json.dumps({
            "ok": False,
            "blocked": "owner_gate",
            "required_owner": "spot-core"
        }, sort_keys=True))
        return 2

    if c["state"] in TERMINAL_STATES:
        print(json.dumps({
            "ok": False,
            "blocked": "terminal_state",
            "state": c["state"]
        }, sort_keys=True))
        return 2

    if c["state"] == "leased" and c.get("lease") and c["lease"].get("expires_ts", 0) > now_ts():
        print(json.dumps({
            "ok": False,
            "blocked": "active_lease",
            "candidate_id": args.candidate_id
        }, sort_keys=True))
        return 2

    lease = {
        "owner": args.owner,
        "lease_ts": now_ts(),
        "expires_ts": now_ts() + args.ttl,
    }

    c["state"] = "leased"
    c["lease"] = lease
    c["updated_ts"] = now_ts()
    c["receipts"].append(receipt(args.root, args.candidate_id, "lease", lease))
    write_state(args.root, state)

    print(json.dumps({
        "ok": True,
        "candidate_id": args.candidate_id,
        "lease": lease
    }, sort_keys=True))
    return 0

def cmd_complete(args):
    state = load_state(args.root)
    c = require_candidate(state, args.candidate_id)

    if c["state"] != "leased":
        print(json.dumps({
            "ok": False,
            "blocked": "not_leased",
            "state": c["state"]
        }, sort_keys=True))
        return 2

    lease = c.get("lease") or {}

    if lease.get("owner") != "spot-core":
        print(json.dumps({
            "ok": False,
            "blocked": "owner_gate"
        }, sort_keys=True))
        return 2

    if lease.get("expires_ts", 0) <= now_ts():
        print(json.dumps({
            "ok": False,
            "blocked": "expired_lease"
        }, sort_keys=True))
        return 2

    c["state"] = "completed"
    c["updated_ts"] = now_ts()
    c["receipts"].append(receipt(args.root, args.candidate_id, "complete", {
        "result": "simulated_fixture_success"
    }))
    write_state(args.root, state)

    print(json.dumps({
        "ok": True,
        "candidate_id": args.candidate_id,
        "state": "completed"
    }, sort_keys=True))
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    sub = ap.add_subparsers(dest="cmd", required=True)

    lease = sub.add_parser("lease")
    lease.add_argument("--candidate-id", required=True)
    lease.add_argument("--owner", required=True)
    lease.add_argument("--ttl", type=int, default=30)

    complete = sub.add_parser("complete")
    complete.add_argument("--candidate-id", required=True)

    args = ap.parse_args()

    if args.cmd == "lease":
        return cmd_lease(args)
    if args.cmd == "complete":
        return cmd_complete(args)

    return 1

if __name__ == "__main__":
    raise SystemExit(main())
