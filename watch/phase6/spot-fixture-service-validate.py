#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path("watch/phase6/runs/validate-current")
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


def make_lease(name: str, ttl: int = 60, owner: str = "spot-core") -> Path:
    path = ROOT / f"{name}.lease.json"
    run([
        str(ORCH),
        "lease",
        "--owner",
        owner,
        "--ttl",
        str(ttl),
        "--output",
        str(path),
    ])
    return path


def action(name: str, act: str, lease: Path, nonce: str, fail: bool = False) -> dict:
    cmd = [
        str(ORCH),
        "action",
        "--root",
        str(ROOT),
        "--target",
        "fixture-service",
        "--action",
        act,
        "--lease-file",
        str(lease),
        "--nonce",
        nonce,
    ]
    if fail:
        cmd.append("--force-verify-fail")

    p = run(cmd)
    return json.loads(p.stdout)


def assert_eq(got, want, label: str) -> None:
    if got != want:
        raise SystemExit(f"ASSERT FAIL {label}: got={got!r} want={want!r}")


def main() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True, exist_ok=True)

    lease = make_lease("valid")

    r1 = action("start", "start", lease, "phase6-start")
    assert_eq(r1["result"], "applied", "start result")
    assert_eq(r1["after_state"], "running", "start state")
    assert_eq(r1["mutation_scope"], "fixture_only", "start scope")

    r2 = action("stop", "stop", lease, "phase6-stop")
    assert_eq(r2["result"], "applied", "stop result")
    assert_eq(r2["after_state"], "stopped", "stop state")

    r3 = action("restart", "restart", lease, "phase6-restart")
    assert_eq(r3["result"], "applied", "restart result")
    assert_eq(r3["after_state"], "running", "restart state")

    r4 = action("verify-fail", "restart", lease, "phase6-verify-fail", fail=True)
    assert_eq(r4["result"], "rolled_back", "verify rollback result")
    assert_eq(r4["after_state"], "rollback_restored", "verify rollback state")

    expired = make_lease("expired", ttl=-1)
    run([
        str(ORCH),
        "action",
        "--root",
        str(ROOT),
        "--target",
        "fixture-service",
        "--action",
        "start",
        "--lease-file",
        str(expired),
        "--nonce",
        "phase6-expired-lease",
    ], expect_ok=False)

    run([
        str(ORCH),
        "action",
        "--root",
        str(ROOT),
        "--target",
        "fixture-service",
        "--action",
        "start",
        "--lease-file",
        str(lease),
        "--nonce",
        "phase6-start",
    ], expect_ok=False)

    run([
        str(ORCH),
        "action",
        "--root",
        str(ROOT),
        "--target",
        "../not-fixture",
        "--action",
        "start",
        "--lease-file",
        str(lease),
        "--nonce",
        "phase6-target-escape",
    ], expect_ok=False)

    journal = ROOT / "journals" / "phase6-fixture-service.jsonl"
    records = [json.loads(line) for line in journal.read_text().splitlines() if line.strip()]
    if len(records) != 4:
        raise SystemExit(f"ASSERT FAIL journal_records: got={len(records)} want=4")

    if any(r["mutation_scope"] != "fixture_only" for r in records):
        raise SystemExit("ASSERT FAIL mutation_scope not fixture_only")

    print("RESULT: PASS")
    print(
        "cases=7 "
        "fixture_service_lifecycle=pass "
        "supervised_state_transitions=pass "
        "governed_apply_queue=pass "
        "rollback_continuity=pass "
        "lease_expiration=pass "
        "replay_guard=pass "
        "target_escape=pass "
        "mutation_scope=fixture_only"
    )


if __name__ == "__main__":
    main()
