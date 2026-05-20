#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path("watch/phase11/runs/full-current")
CHAIN = Path("watch/phase11/spot-supervised-chain-orchestrator.py")
ORCH = Path("watch/phase6/spot-fixture-service-orchestrator.py")


def run(cmd: list[str], expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(cmd, text=True, capture_output=True)

    if expect_ok and p.returncode != 0:
        print("COMMAND FAILED:", " ".join(cmd))
        print(p.stdout)
        print(p.stderr)
        raise SystemExit(1)

    if not expect_ok and p.returncode == 0:
        print("COMMAND SHOULD HAVE FAILED:", " ".join(cmd))
        print(p.stdout)
        print(p.stderr)
        raise SystemExit(1)

    return p


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def assert_eq(got, want, label: str) -> None:
    if got != want:
        raise SystemExit(f"ASSERT FAIL {label}: got={got!r} want={want!r}")


def assert_true(value: bool, label: str) -> None:
    if not value:
        raise SystemExit(f"ASSERT FAIL {label}")


def make_lease(name: str, ttl: int = 60) -> Path:
    path = ROOT / "leases" / f"{name}.json"
    run([
        str(ORCH),
        "lease",
        "--owner",
        "spot-core",
        "--ttl",
        str(ttl),
        "--output",
        str(path),
    ])
    return path


def make_chain(
    name: str,
    owner: str = "spot-core",
    target: str = "fixture-service",
    risk: str = "low",
    approved: bool = True,
    backup_verified: bool = True,
    rollback_verified: bool = True,
    validation_defined: bool = True,
) -> Path:
    chain = {
        "schema": "phase11.chain_request.v1",
        "chain_id": f"phase11-{name}",
        "owner": owner,
        "target": target,
        "risk_class": risk,
        "approval_state": "approved" if approved else "pending",
        "backup_verified": backup_verified,
        "rollback_verified": rollback_verified,
        "validation_defined": validation_defined,
        "nonce": name,
    }

    path = ROOT / "chains" / f"{name}.json"
    write_json(path, chain)
    return path


def execute(
    chain_file: Path,
    lease: Path,
    expect_ok: bool = True,
    force_fail: bool = False,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        str(CHAIN),
        "--root",
        str(ROOT),
        "--chain-file",
        str(chain_file),
        "--lease-file",
        str(lease),
    ]

    if force_fail:
        cmd.append("--force-verify-fail")

    return run(cmd, expect_ok=expect_ok)


def main() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)

    ROOT.mkdir(parents=True, exist_ok=True)

    lease = make_lease("valid")

    ok = execute(make_chain("success"), lease)
    ok_obj = json.loads(ok.stdout)

    assert_eq(ok_obj["result"], "completed", "successful chain")
    assert_eq(ok_obj["mutation_scope"], "fixture_only", "success mutation scope")
    assert_eq(ok_obj["steps"]["observation"]["mutation_scope"], "none", "observation scope")
    assert_eq(ok_obj["steps"]["planning"]["mutation_scope"], "proposal_only", "planning scope")
    assert_eq(ok_obj["steps"]["execution"]["after_state"], "running", "execution state")

    rb = execute(make_chain("rollback"), lease, force_fail=True)
    rb_obj = json.loads(rb.stdout)

    assert_eq(rb_obj["result"], "rolled_back", "rollback chain")
    assert_eq(rb_obj["steps"]["execution"]["result"], "rolled_back", "rollback receipt")
    assert_eq(rb_obj["steps"]["execution"]["after_state"], "rollback_restored", "rollback state")

    replay = make_chain("replay")
    execute(replay, lease)
    execute(replay, lease, expect_ok=False)

    execute(
        make_chain("unapproved", approved=False),
        lease,
        expect_ok=False,
    )

    execute(
        make_chain("medium-risk", risk="medium"),
        lease,
        expect_ok=False,
    )

    execute(
        make_chain("wrong-owner", owner="spot-worker-03"),
        lease,
        expect_ok=False,
    )

    execute(
        make_chain("production-target", target="production-service"),
        lease,
        expect_ok=False,
    )

    execute(
        make_chain("missing-backup", backup_verified=False),
        lease,
        expect_ok=False,
    )

    execute(
        make_chain("missing-rollback", rollback_verified=False),
        lease,
        expect_ok=False,
    )

    execute(
        make_chain("missing-validation", validation_defined=False),
        lease,
        expect_ok=False,
    )

    expired = make_lease("expired", ttl=-1)

    execute(
        make_chain("expired-lease"),
        expired,
        expect_ok=False,
    )

    chain_journal = ROOT / "journals" / "phase11-chains.jsonl"
    denied_journal = ROOT / "journals" / "phase11-denied-chains.jsonl"
    receipts_dir = ROOT / "receipts"

    assert_true(chain_journal.exists(), "chain journal exists")
    assert_true(denied_journal.exists(), "denied chain journal exists")
    assert_true(receipts_dir.exists(), "receipts dir exists")

    chains = [
        json.loads(line)
        for line in chain_journal.read_text().splitlines()
        if line.strip()
    ]

    denied = [
        json.loads(line)
        for line in denied_journal.read_text().splitlines()
        if line.strip()
    ]

    receipts = list(receipts_dir.glob("*.json"))

    assert_eq(len(chains), 3, "chain journal count")
    assert_true(len(denied) >= 8, "denied chain count")
    assert_eq(len(receipts), 3, "receipt count")

    for record in chains:
        assert_eq(record["schema"], "phase11.chain.v1", "chain schema")
        assert_eq(record["mutation_scope"], "fixture_only", "chain scope")
        assert_true("record_hash" in record, "chain hash")
        assert_true("observation" in record["steps"], "observation step")
        assert_true("planning" in record["steps"], "planning step")
        assert_true("execution" in record["steps"], "execution step")

    for record in denied:
        assert_eq(record["schema"], "phase11.chain.v1", "denied schema")
        assert_eq(record["result"], "blocked", "denied result")
        assert_eq(record["mutation_scope"], "none", "denied scope")
        assert_true("record_hash" in record, "denied hash")

    print("RESULT: PASS")
    print(
        "cases=17 "
        "supervised_chain=pass "
        "rollback_chain=pass "
        "chain_replay_guard=pass "
        "unapproved_blocked=pass "
        "risk_gate=pass "
        "owner_gate=pass "
        "production_target_blocked=pass "
        "backup_gate=pass "
        "rollback_gate=pass "
        "validation_gate=pass "
        "lease_expiration=pass "
        "observation_step=pass "
        "planning_step=pass "
        "execution_step=pass "
        "chain_journal=pass "
        "chain_receipts=pass "
        "mutation_scope=fixture_only"
    )


if __name__ == "__main__":
    main()
