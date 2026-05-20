#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path("watch/phase6/runs/full-current")
ORCH = Path("watch/phase6/spot-fixture-service-orchestrator.py")
QUEUE = Path("watch/phase6/spot-governed-apply-queue.py")
BASE_VALIDATE = Path("watch/phase6/spot-fixture-service-validate.py")


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


def enqueue(
    nonce: str,
    action: str,
    backup_id: str = "backup-phase6",
    rollback_id: str = "rollback-phase6",
    validation_id: str = "validation-phase6",
    force_fail: bool = False,
) -> dict:

    cmd = [
        str(QUEUE),
        "enqueue",
        "--root",
        str(ROOT),
        "--target",
        "fixture-service",
        "--action",
        action,
        "--nonce",
        nonce,
        "--backup-id",
        backup_id,
        "--rollback-id",
        rollback_id,
        "--validation-id",
        validation_id,
    ]

    if force_fail:
        cmd.append("--force-verify-fail")

    return json_out(cmd)


def approve(plan_id: str) -> dict:
    return json_out([
        str(QUEUE),
        "approve",
        "--root",
        str(ROOT),
        "--plan-id",
        plan_id,
        "--approved-by",
        "spot-core",
    ])


def reject(plan_id: str) -> dict:
    return json_out([
        str(QUEUE),
        "reject",
        "--root",
        str(ROOT),
        "--plan-id",
        plan_id,
        "--rejected-by",
        "operator",
        "--reason",
        "phase6 validation rejection test",
    ])


def dispatch(
    plan_id: str,
    lease: Path,
    expect_ok: bool = True,
    executor: str = "spot-core",
) -> subprocess.CompletedProcess[str]:

    return run([
        str(QUEUE),
        "dispatch",
        "--root",
        str(ROOT),
        "--plan-id",
        plan_id,
        "--lease-file",
        str(lease),
        "--executor",
        executor,
    ], expect_ok=expect_ok)


def assert_eq(got, want, label: str) -> None:
    if got != want:
        raise SystemExit(
            f"ASSERT FAIL {label}: got={got!r} want={want!r}"
        )


def main() -> None:

    run([str(BASE_VALIDATE)])

    if ROOT.exists():
        shutil.rmtree(ROOT)

    ROOT.mkdir(parents=True, exist_ok=True)

    lease = make_lease("valid")

    p_pending = enqueue("phase6-queue-pending", "start")
    dispatch(p_pending["plan_id"], lease, expect_ok=False)

    p_start = enqueue("phase6-queue-start", "start")
    approve(p_start["plan_id"])

    d_start = dispatch(p_start["plan_id"], lease)
    start_obj = json.loads(d_start.stdout)

    assert_eq(
        start_obj["state"],
        "dispatched",
        "start dispatched state",
    )

    assert_eq(
        start_obj["receipt"]["after_state"],
        "running",
        "start after_state",
    )

    p_stop = enqueue("phase6-queue-stop", "stop")
    approve(p_stop["plan_id"])

    d_stop = dispatch(p_stop["plan_id"], lease)
    stop_obj = json.loads(d_stop.stdout)

    assert_eq(
        stop_obj["state"],
        "dispatched",
        "stop dispatched state",
    )

    assert_eq(
        stop_obj["receipt"]["after_state"],
        "stopped",
        "stop after_state",
    )

    p_restart = enqueue("phase6-queue-restart", "restart")
    approve(p_restart["plan_id"])

    d_restart = dispatch(p_restart["plan_id"], lease)
    restart_obj = json.loads(d_restart.stdout)

    assert_eq(
        restart_obj["state"],
        "dispatched",
        "restart dispatched state",
    )

    assert_eq(
        restart_obj["receipt"]["after_state"],
        "running",
        "restart after_state",
    )

    p_reject = enqueue("phase6-queue-rejected", "start")
    reject(p_reject["plan_id"])

    dispatch(
        p_reject["plan_id"],
        lease,
        expect_ok=False,
    )

    p_worker = enqueue("phase6-worker-self-apply", "start")
    approve(p_worker["plan_id"])

    dispatch(
        p_worker["plan_id"],
        lease,
        expect_ok=False,
        executor="spot-worker-03",
    )

    expired = make_lease("expired", ttl=-1)

    p_expired = enqueue(
        "phase6-expired-lease",
        "start",
    )

    approve(p_expired["plan_id"])

    dispatch(
        p_expired["plan_id"],
        expired,
        expect_ok=False,
    )

    run([
        str(QUEUE),
        "enqueue",
        "--root",
        str(ROOT),
        "--target",
        "fixture-service",
        "--action",
        "start",
        "--nonce",
        "phase6-missing-backup",
        "--backup-id",
        "missing",
        "--rollback-id",
        "rollback-phase6",
        "--validation-id",
        "validation-phase6",
    ], expect_ok=False)

    run([
        str(QUEUE),
        "enqueue",
        "--root",
        str(ROOT),
        "--target",
        "fixture-service",
        "--action",
        "start",
        "--nonce",
        "phase6-missing-rollback",
        "--backup-id",
        "backup-phase6",
        "--rollback-id",
        "missing",
        "--validation-id",
        "validation-phase6",
    ], expect_ok=False)

    run([
        str(QUEUE),
        "enqueue",
        "--root",
        str(ROOT),
        "--target",
        "fixture-service",
        "--action",
        "start",
        "--nonce",
        "phase6-missing-validation",
        "--backup-id",
        "backup-phase6",
        "--rollback-id",
        "rollback-phase6",
        "--validation-id",
        "missing",
    ], expect_ok=False)

    run([
        str(QUEUE),
        "enqueue",
        "--root",
        str(ROOT),
        "--target",
        "../not-fixture",
        "--action",
        "start",
        "--nonce",
        "phase6-target-escape",
        "--backup-id",
        "backup-phase6",
        "--rollback-id",
        "rollback-phase6",
        "--validation-id",
        "validation-phase6",
    ], expect_ok=False)

    p_rollback = enqueue(
        "phase6-queue-rollback-continuity",
        "restart",
        force_fail=True,
    )

    approve(p_rollback["plan_id"])

    d_rollback = dispatch(
        p_rollback["plan_id"],
        lease,
    )

    rollback_obj = json.loads(d_rollback.stdout)

    assert_eq(
        rollback_obj["state"],
        "rolled_back",
        "queue rollback state",
    )

    assert_eq(
        rollback_obj["receipt"]["result"],
        "rolled_back",
        "receipt rollback result",
    )

    assert_eq(
        rollback_obj["receipt"]["after_state"],
        "rollback_restored",
        "receipt rollback after_state",
    )

    p_replay = enqueue(
        "phase6-queue-replay",
        "start",
    )

    approve(p_replay["plan_id"])

    dispatch(
        p_replay["plan_id"],
        lease,
    )

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
        "phase6-queue-replay",
    ], expect_ok=False)

    fixture_journal = (
        ROOT / "journals" / "phase6-fixture-service.jsonl"
    )

    queue_journal = (
        ROOT / "journals" / "phase6-governed-apply-queue.jsonl"
    )

    fixture_records = [
        json.loads(x)
        for x in fixture_journal.read_text().splitlines()
        if x.strip()
    ]

    queue_records = [
        json.loads(x)
        for x in queue_journal.read_text().splitlines()
        if x.strip()
    ]

    if not fixture_records:
        raise SystemExit(
            "ASSERT FAIL fixture journal missing"
        )

    if not queue_records:
        raise SystemExit(
            "ASSERT FAIL queue journal missing"
        )

    if any(
        r["mutation_scope"] != "fixture_only"
        for r in fixture_records
    ):
        raise SystemExit(
            "ASSERT FAIL fixture mutation scope"
        )

    if any(
        r["mutation_scope"] != "fixture_only"
        for r in queue_records
    ):
        raise SystemExit(
            "ASSERT FAIL queue mutation scope"
        )

    print("RESULT: PASS")

    print(
        "cases=15 "
        "fixture_service_lifecycle=pass "
        "supervised_state_transitions=pass "
        "governed_apply_queue=pass "
        "backup_gate=pass "
        "rollback_gate=pass "
        "validation_gate=pass "
        "rollback_continuity=pass "
        "lease_expiration=pass "
        "replay_guard=pass "
        "target_escape=pass "
        "worker_self_apply=pass "
        "journal_records=pass "
        "mutation_scope=fixture_only"
    )


if __name__ == "__main__":
    main()
