#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path("watch/phase9/runs/full-current")
WRAPPER = Path("watch/phase9/spot-lowrisk-exec-wrapper.py")
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


def json_out(cmd: list[str]) -> dict:
    p = run(cmd)
    return json.loads(p.stdout)


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


def make_plan(
    name: str,
    action: str = "lowrisk-fixture-start",
    target: str = "fixture-service",
    risk: str = "low",
    approved: bool = True,
    execution_allowed: bool = True,
    backup_verified: bool = True,
    rollback_defined: bool = True,
    validation_defined: bool = True,
) -> Path:

    plan = {
        "schema": "phase9.lowrisk.plan.v1",
        "plan_id": f"phase9-{name}",
        "target": target,
        "action": action,
        "risk_class": risk,
        "approval_state": "approved" if approved else "pending",
        "execution_allowed": execution_allowed,
        "backup_verified": backup_verified,
        "rollback_defined": rollback_defined,
        "validation_defined": validation_defined,
        "nonce": name,
        "mutation_scope": "fixture_only",
    }

    path = ROOT / "plans" / f"{name}.json"
    write_json(path, plan)
    return path


def execute(
    plan: Path,
    lease: Path,
    expect_ok: bool = True,
    executor: str = "spot-core",
) -> subprocess.CompletedProcess[str]:

    return run([
        str(WRAPPER),
        "--root",
        str(ROOT),
        "--plan-file",
        str(plan),
        "--lease-file",
        str(lease),
        "--executor",
        executor,
    ], expect_ok=expect_ok)


def main() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True, exist_ok=True)

    lease = make_lease("valid")

    ok_plan = make_plan("approved-lowrisk-start")
    ok = execute(ok_plan, lease)
    ok_obj = json.loads(ok.stdout)

    assert_eq(ok_obj["result"], "executed", "approved execution result")
    assert_eq(ok_obj["mutation_scope"], "fixture_only", "approved mutation scope")
    assert_eq(ok_obj["receipt"]["after_state"], "running", "fixture after state")

    execute(
        make_plan("unapproved", approved=False),
        lease,
        expect_ok=False,
    )

    execute(
        make_plan("medium-risk", risk="medium"),
        lease,
        expect_ok=False,
    )

    execute(
        make_plan("worker-self-apply"),
        lease,
        expect_ok=False,
        executor="spot-worker-03",
    )

    execute(
        make_plan("missing-backup", backup_verified=False),
        lease,
        expect_ok=False,
    )

    execute(
        make_plan("missing-rollback", rollback_defined=False),
        lease,
        expect_ok=False,
    )

    execute(
        make_plan("missing-validation", validation_defined=False),
        lease,
        expect_ok=False,
    )

    expired = make_lease("expired", ttl=-1)

    execute(
        make_plan("expired-lease"),
        expired,
        expect_ok=False,
    )

    replay_plan = make_plan("replay")
    execute(replay_plan, lease)
    execute(replay_plan, lease, expect_ok=False)

    execute(
        make_plan("production-target", target="production-service"),
        lease,
        expect_ok=False,
    )

    execute(
        make_plan("service-restart", action="restart-production-service"),
        lease,
        expect_ok=False,
    )

    exec_journal = ROOT / "journals" / "phase9-executions.jsonl"
    denied_journal = ROOT / "journals" / "phase9-denied-executions.jsonl"

    assert_true(exec_journal.exists(), "execution journal exists")
    assert_true(denied_journal.exists(), "denied journal exists")

    exec_records = [
        json.loads(line)
        for line in exec_journal.read_text().splitlines()
        if line.strip()
    ]

    denied_records = [
        json.loads(line)
        for line in denied_journal.read_text().splitlines()
        if line.strip()
    ]

    assert_eq(len(exec_records), 2, "execution journal count")
    assert_true(len(denied_records) >= 9, "denied journal count")

    for record in exec_records:
        assert_eq(record["schema"], "phase9.execution.v1", "exec schema")
        assert_eq(record["result"], "executed", "exec result")
        assert_eq(record["mutation_scope"], "fixture_only", "exec mutation scope")
        assert_true("record_hash" in record, "exec hash present")

    for record in denied_records:
        assert_eq(record["schema"], "phase9.execution.v1", "denied schema")
        assert_eq(record["result"], "blocked", "denied result")
        assert_eq(record["mutation_scope"], "none", "denied mutation scope")
        assert_true("record_hash" in record, "denied hash present")

    print("RESULT: PASS")
    print(
        "cases=15 "
        "approved_low_risk_execution=pass "
        "unapproved_blocked=pass "
        "risk_gate=pass "
        "worker_self_apply=pass "
        "backup_gate=pass "
        "rollback_gate=pass "
        "validation_gate=pass "
        "lease_expiration=pass "
        "replay_guard=pass "
        "production_target_blocked=pass "
        "service_restart_blocked=pass "
        "execution_journal=pass "
        "denied_journal=pass "
        "mutation_scope=fixture_only"
    )


if __name__ == "__main__":
    main()
