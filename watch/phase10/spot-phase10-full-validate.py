#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path("watch/phase10/runs/full-current")
WRAPPER = Path("watch/phase10/spot-rollback-remediation-wrapper.py")
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


def make_plan(
    name: str,
    action: str = "remediate-fixture-start",
    target: str = "fixture-service",
    risk: str = "low",
    approved: bool = True,
    backup_verified: bool = True,
    validation_defined: bool = True,
) -> Path:

    plan = {
        "schema": "phase10.remediation.plan.v1",
        "plan_id": f"phase10-{name}",
        "target": target,
        "action": action,
        "risk_class": risk,
        "approval_state": "approved" if approved else "pending",
        "backup_verified": backup_verified,
        "validation_defined": validation_defined,
        "nonce": name,
        "mutation_scope": "fixture_only",
    }

    path = ROOT / "plans" / f"{name}.json"
    write_json(path, plan)
    return path


def make_manifest(name: str, valid: bool = True, verified: bool = True) -> Path:
    manifest = {
        "schema": "phase10.rollback_manifest.v1" if valid else "bad.schema",
        "rollback_manifest_id": f"rollback-manifest-{name}",
        "target": "fixture-service",
        "rollback_action": "rollback",
        "verified": verified,
    }

    path = ROOT / "rollback-manifests" / f"{name}.json"
    write_json(path, manifest)
    return path


def execute(
    plan: Path,
    lease: Path,
    manifest: Path,
    expect_ok: bool = True,
    executor: str = "spot-core",
    force_fail: bool = False,
) -> subprocess.CompletedProcess[str]:

    cmd = [
        str(WRAPPER),
        "--root",
        str(ROOT),
        "--plan-file",
        str(plan),
        "--lease-file",
        str(lease),
        "--rollback-manifest",
        str(manifest),
        "--executor",
        executor,
    ]

    if force_fail:
        cmd.append("--force-verify-fail")

    return run(cmd, expect_ok=expect_ok)


def main() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)

    ROOT.mkdir(parents=True, exist_ok=True)

    lease = make_lease("valid")
    manifest = make_manifest("valid")

    ok = execute(make_plan("approved"), lease, manifest)
    ok_obj = json.loads(ok.stdout)

    assert_eq(ok_obj["result"], "remediated", "approved remediation")
    assert_eq(ok_obj["mutation_scope"], "fixture_only", "approved scope")

    fail = execute(
        make_plan("verify-fail"),
        lease,
        manifest,
        force_fail=True,
    )

    fail_obj = json.loads(fail.stdout)

    assert_eq(fail_obj["result"], "rolled_back", "rollback result")

    assert_true(
        fail_obj["rollback_receipt"] is not None,
        "rollback receipt present",
    )

    assert_eq(
        fail_obj["rollback_receipt"]["rollback_result"],
        "verified",
        "rollback verified",
    )

    execute(
        make_plan("invalid-manifest"),
        lease,
        make_manifest("invalid", valid=False),
        expect_ok=False,
    )

    execute(
        make_plan("unverified-manifest"),
        lease,
        make_manifest("unverified", verified=False),
        expect_ok=False,
    )

    execute(
        make_plan("unapproved", approved=False),
        lease,
        manifest,
        expect_ok=False,
    )

    execute(
        make_plan("medium-risk", risk="medium"),
        lease,
        manifest,
        expect_ok=False,
    )

    execute(
        make_plan("worker-self-apply"),
        lease,
        manifest,
        expect_ok=False,
        executor="spot-worker-03",
    )

    execute(
        make_plan("missing-validation", validation_defined=False),
        lease,
        manifest,
        expect_ok=False,
    )

    expired = make_lease("expired", ttl=-1)

    execute(
        make_plan("expired-lease"),
        expired,
        manifest,
        expect_ok=False,
    )

    replay_plan = make_plan("replay")
    execute(replay_plan, lease, manifest)
    execute(replay_plan, lease, manifest, expect_ok=False)

    execute(
        make_plan("production-target", target="production-service"),
        lease,
        manifest,
        expect_ok=False,
    )

    remediation_journal = ROOT / "journals" / "phase10-remediations.jsonl"
    denied_journal = ROOT / "journals" / "phase10-denied-remediations.jsonl"
    rollback_journal = ROOT / "journals" / "phase10-rollbacks.jsonl"

    assert_true(remediation_journal.exists(), "remediation journal exists")
    assert_true(denied_journal.exists(), "denied journal exists")
    assert_true(rollback_journal.exists(), "rollback journal exists")

    remediations = [
        json.loads(line)
        for line in remediation_journal.read_text().splitlines()
        if line.strip()
    ]

    denied = [
        json.loads(line)
        for line in denied_journal.read_text().splitlines()
        if line.strip()
    ]

    rollbacks = [
        json.loads(line)
        for line in rollback_journal.read_text().splitlines()
        if line.strip()
    ]

    assert_eq(len(remediations), 3, "remediation count")
    assert_true(len(denied) >= 8, "denied count")
    assert_eq(len(rollbacks), 1, "rollback count")

    for record in remediations:
        assert_eq(record["schema"], "phase10.remediation.v1", "remediation schema")
        assert_eq(record["mutation_scope"], "fixture_only", "remediation scope")
        assert_true("record_hash" in record, "remediation hash")

    for record in denied:
        assert_eq(record["schema"], "phase10.remediation.v1", "denied schema")
        assert_eq(record["result"], "blocked", "denied result")
        assert_eq(record["mutation_scope"], "none", "denied scope")
        assert_true("record_hash" in record, "denied hash")

    for record in rollbacks:
        assert_eq(record["schema"], "phase10.rollback_receipt.v1", "rollback schema")
        assert_eq(record["rollback_result"], "verified", "rollback verified")
        assert_eq(record["mutation_scope"], "fixture_only", "rollback scope")

    print("RESULT: PASS")
    print(
        "cases=16 "
        "approved_remediation=pass "
        "verification_failure_rollback=pass "
        "rollback_receipt=pass "
        "rollback_journal=pass "
        "rollback_manifest_gate=pass "
        "invalid_manifest_blocked=pass "
        "unapproved_blocked=pass "
        "risk_gate=pass "
        "worker_self_apply=pass "
        "lease_expiration=pass "
        "replay_guard=pass "
        "production_target_blocked=pass "
        "validation_gate=pass "
        "execution_journal=pass "
        "denied_journal=pass "
        "mutation_scope=fixture_only"
    )


if __name__ == "__main__":
    main()
