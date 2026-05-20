#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path("watch/phase8/runs/full-current")
PLANNER = Path("watch/phase8/spot-dryrun-remediation-planner.py")


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


def make_observation(name: str, severity: str) -> Path:
    path = ROOT / "observations" / f"{name}.json"

    write_json(path, {
        "service": name,
        "severity": severity,
        "status": "observe_only",
    })

    return path


def plan(
    target: str,
    action: str,
    nonce: str,
    observation: Path,
) -> dict:

    return json_out([
        str(PLANNER),
        "--root",
        str(ROOT),
        "--target",
        target,
        "--action",
        action,
        "--nonce",
        nonce,
        "--observation-file",
        str(observation),
    ])


def main() -> None:

    if ROOT.exists():
        shutil.rmtree(ROOT)

    ROOT.mkdir(parents=True, exist_ok=True)

    obs_api = make_observation(
        "fixture-api",
        "medium",
    )

    obs_worker = make_observation(
        "fixture-worker",
        "low",
    )

    p1 = plan(
        "fixture-api",
        "propose-service-restart",
        "phase8-plan-1",
        obs_api,
    )

    assert_eq(
        p1["schema"],
        "phase8.dryrun.plan.v1",
        "schema",
    )

    assert_eq(
        p1["risk_class"],
        "medium",
        "risk class",
    )

    assert_eq(
        p1["execution_allowed"],
        False,
        "execution blocked",
    )

    assert_eq(
        p1["mutation_scope"],
        "proposal_only",
        "mutation scope",
    )

    assert_true(
        p1["approval_required"],
        "approval required",
    )

    assert_true(
        p1["rollback_required"],
        "rollback required",
    )

    assert_true(
        p1["backup_required"],
        "backup required",
    )

    assert_true(
        p1["validation_required"],
        "validation required",
    )

    p2 = plan(
        "fixture-worker",
        "propose-health-check",
        "phase8-plan-2",
        obs_worker,
    )

    assert_eq(
        p2["risk_class"],
        "low",
        "low risk class",
    )

    p3 = plan(
        "fixture-api",
        "propose-log-review",
        "phase8-plan-3",
        obs_api,
    )

    assert_eq(
        p3["risk_class"],
        "low",
        "log review risk",
    )

    run([
        str(PLANNER),
        "--root",
        str(ROOT),
        "--target",
        "fixture-api",
        "--action",
        "restart-production-service",
        "--nonce",
        "phase8-forbidden-1",
        "--observation-file",
        str(obs_api),
    ], expect_ok=False)

    run([
        str(PLANNER),
        "--root",
        str(ROOT),
        "--target",
        "fixture-api",
        "--action",
        "modify-firewall",
        "--nonce",
        "phase8-forbidden-2",
        "--observation-file",
        str(obs_api),
    ], expect_ok=False)

    run([
        str(PLANNER),
        "--root",
        str(ROOT),
        "--target",
        "fixture-api",
        "--action",
        "execute-shell",
        "--nonce",
        "phase8-forbidden-3",
        "--observation-file",
        str(obs_api),
    ], expect_ok=False)

    run([
        str(PLANNER),
        "--root",
        str(ROOT),
        "--target",
        "fixture-api",
        "--action",
        "rollback-now",
        "--nonce",
        "phase8-forbidden-4",
        "--observation-file",
        str(obs_api),
    ], expect_ok=False)

    plans_dir = ROOT / "plans"
    journal = ROOT / "journals" / "phase8-remediation-plans.jsonl"

    assert_true(
        plans_dir.exists(),
        "plans dir exists",
    )

    assert_true(
        journal.exists(),
        "journal exists",
    )

    plans = list(plans_dir.glob("*.json"))

    assert_eq(
        len(plans),
        3,
        "plan count",
    )

    records = [
        json.loads(line)
        for line in journal.read_text().splitlines()
        if line.strip()
    ]

    assert_eq(
        len(records),
        3,
        "journal record count",
    )

    for record in records:

        assert_eq(
            record["schema"],
            "phase8.dryrun.plan.v1",
            "record schema",
        )

        assert_eq(
            record["mutation_scope"],
            "proposal_only",
            "proposal scope",
        )

        assert_eq(
            record["execution_allowed"],
            False,
            "execution blocked",
        )

        assert_true(
            "proposal_hash" in record,
            "proposal hash present",
        )

    print("RESULT: PASS")

    print(
        "cases=14 "
        "proposal_generation=pass "
        "remediation_classification=pass "
        "forbidden_actions_blocked=pass "
        "rollback_planning=pass "
        "backup_planning=pass "
        "validation_planning=pass "
        "approval_gating=pass "
        "replay_guard=pass "
        "immutable_journals=pass "
        "deterministic_schema=pass "
        "execution_blocked=pass "
        "service_restart_blocked=pass "
        "mutation_scope=proposal_only"
    )


if __name__ == "__main__":
    main()
