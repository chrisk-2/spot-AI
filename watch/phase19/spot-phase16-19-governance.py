#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


REQUIRED_PHASES = {
    "phase15_operator_approval_gate",
    "phase16_preexecution_lockout",
    "phase17_live_candidate_bundle",
    "phase18_governance_consolidation",
}


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def append_jsonl(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True) + "\n")


def evaluate(bundle: dict[str, Any]) -> dict[str, Any]:
    proofs = bundle.get("proofs", {})

    missing = sorted(REQUIRED_PHASES - set(proofs))

    failed = sorted(
        name
        for name, proof in proofs.items()
        if name in REQUIRED_PHASES and proof.get("result") != "pass"
    )

    ready = not missing and not failed

    envelope = {
        "schema": "phase19.autonomy_readiness.v1",
        "ts": int(time.time()),
        "bundle_id": bundle.get("bundle_id", "unknown"),
        "missing_proofs": missing,
        "failed_proofs": failed,
        "phase16_preexecution_lockout": ready,
        "phase17_live_candidate_bundle": ready,
        "phase18_governance_consolidation": ready,
        "phase19_autonomy_readiness_closeout": ready,
        "authority": "governance_only",
        "execution_allowed": False,
        "approval_bypass_allowed": False,
        "production_mutation_allowed": False,
        "routing_change_allowed": False,
        "worker_ownership_change_allowed": False,
        "mutation_scope": "none",
    }

    envelope["envelope_hash"] = sha256_text(canonical(envelope))
    return envelope


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase16-19 governance")
    parser.add_argument("--root", required=True)
    parser.add_argument("--bundle-file", required=True)
    args = parser.parse_args()

    root = Path(args.root)

    bundle = load_json(Path(args.bundle_file), {})

    env = evaluate(bundle)

    write_json(
        root / "envelopes" / f"{env['bundle_id']}.json",
        env,
    )

    append_jsonl(
        root / "journals" / "phase16-19-governance.jsonl",
        env,
    )

    print(json.dumps(env, sort_keys=True))


if __name__ == "__main__":
    main()
