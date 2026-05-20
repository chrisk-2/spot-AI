#!/usr/bin/env python3
import argparse
import json
import time
from pathlib import Path

def now_ts():
    return int(time.time())

def receipt(root, candidate_id, event, data):
    import hashlib
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    args = ap.parse_args()

    p = Path(args.root) / "queue-state.json"
    state = json.loads(p.read_text())

    recovered = []
    for cid, c in state["candidates"].items():
        if c["state"] == "leased":
            lease = c.get("lease") or {}
            if lease.get("expires_ts", 0) <= now_ts():
                c["state"] = "pending"
                c["lease"] = None
                c["updated_ts"] = now_ts()
                c["receipts"].append(receipt(args.root, cid, "recover_stale_lease", {"recovered_to": "pending"}))
                recovered.append(cid)

    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    tmp.replace(p)

    print(json.dumps({"ok": True, "recovered": recovered}, sort_keys=True))

if __name__ == "__main__":
    main()
