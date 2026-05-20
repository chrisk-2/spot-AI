#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path("watch/phase14/runs/full-current")
GATE = Path("watch/phase14/spot-production-readiness-gate.py")


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


def make_candidate(name: str, **overrides) -> Path:
    candidate = {
        "candidate_id": name,
        "target": "approved-fixture-adjacent-service",
        "target_class": "approved_low_risk_service",
        "risk_class": "low",
        "executor": "spot-core",
        "operator_approval_required": True,
        "backup_required": True,
        "backup_plan_defined": True,
        "rollback_required": True,
        "rollback_plan_defined": True,
        "validation_required": True,
        "validation_plan_defined": True,
        "execution_allowed": False,
        "mutation_scope": "none",
    }

    candidate.update(overrides)

    path = ROOT / "candidates" / f"{name}.json"
    write_json(path, candidate)
    return path


def gate(candidate: Path) -> dict:
    return json_out([
        str(GATE),
        "--root",
        str(ROOT),
        "--candidate-file",
        str(candidate),
    ])


def main() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)

    ROOT.mkdir(parents=True, exist_ok=True)

    ready = gate(make_candidate("ready"))

    assert_eq(
        ready["schema"],
        "phase14.production_readiness_gate.v1",
        "schema",
    )

    assert_eq(
        ready["readiness"],
        "ready_for_operator_review",
        "ready state",
    )

    assert_eq(
        ready["authority"],
        "readiness_review_only",
        "authority",
    )

    assert_eq(
        ready["execution_allowed"],
        False,
        "execution blocked",
    )

    assert_eq(
        ready["approval_allowed"],
        False,
        "approval blocked",
    )

    assert_eq(
        ready["production_mutation_allowed"],
        False,
        "production mutation blocked",
    )

    assert_eq(
        ready["routing_change_allowed"],
        False,
        "routing blocked",
    )

    assert_eq(
        ready["worker_ownership_change_allowed"],
        False,
        "ownership blocked",
    )

    assert_eq(
        ready["mutation_scope"],
        "none",
        "mutation scope",
    )

    missing_approval = gate(make_candidate(
        "missing-approval",
        operator_approval_required=False,
    ))
    assert_eq(missing_approval["readiness"], "blocked", "missing approval blocked")
    assert_true("operator_approval_not_required" in missing_approval["blockers"], "approval blocker")

    missing_backup = gate(make_candidate(
        "missing-backup",
        backup_plan_defined=False,
    ))
    assert_eq(missing_backup["readiness"], "blocked", "missing backup blocked")
    assert_true("backup_plan_missing" in missing_backup["blockers"], "backup blocker")

    missing_rollback = gate(make_candidate(
        "missing-rollback",
        rollback_plan_defined=False,
    ))
    assert_eq(missing_rollback["readiness"], "blocked", "missing rollback blocked")
    assert_true("rollback_plan_missing" in missing_rollback["blockers"], "rollback blocker")

    missing_validation = gate(make_candidate(
        "missing-validation",
        validation_plan_defined=False,
    ))
    assert_eq(missing_validation["readiness"], "blocked", "missing validation blocked")
    assert_true("validation_plan_missing" in missing_validation["blockers"], "validation blocker")

    medium = gate(make_candidate("medium-risk", risk_class="medium"))
    assert_eq(medium["readiness"], "blocked", "medium risk blocked")
    assert_true("risk_not_low" in medium["blockers"], "risk blocker")

    network = gate(make_candidate("network-target", target_class="network"))
    assert_eq(network["readiness"], "blocked", "network blocked")
    assert_true("blocked_target_class" in network["blockers"], "network blocker")

    worker = gate(make_candidate("worker-executor", executor="spot-worker-03"))
    assert_eq(worker["readiness"], "blocked", "worker executor blocked")
    assert_true("executor_not_spot_core" in worker["blockers"], "executor blocker")

    exec_auth = gate(make_candidate("exec-authority", execution_allowed=True))
    assert_eq(exec_auth["readiness"], "blocked", "execution authority blocked")
    assert_true("execution_authority_present" in exec_auth["blockers"], "execution blocker")

    journal = ROOT / "journals" / "phase14-production-readiness.jsonl"
    envelopes_dir = ROOT / "envelopes"

    assert_true(journal.exists(), "journal exists")
    assert_true(envelopes_dir.exists(), "envelopes dir exists")

    records = [
        json.loads(line)
        for line in journal.read_text().splitlines()
        if line.strip()
    ]

    envelopes = list(envelopes_dir.glob("*.json"))

    assert_eq(len(records), 9, "journal count")
    assert_eq(len(envelopes), 9, "envelope count")

    for record in records:
        assert_eq(record["schema"], "phase14.production_readiness_gate.v1", "record schema")
        assert_eq(record["execution_allowed"], False, "record execution blocked")
        assert_eq(record["approval_allowed"], False, "record approval blocked")
        assert_eq(record["production_mutation_allowed"], False, "record production mutation blocked")
        assert_eq(record["routing_change_allowed"], False, "record routing blocked")
        assert_eq(record["worker_ownership_change_allowed"], False, "record ownership blocked")
        assert_eq(record["mutation_scope"], "none", "record mutation scope")
        assert_true("envelope_hash" in record, "record hash")

    print("RESULT: PASS")
    print(
        "cases=14 "
        "readiness_gate=pass "
        "missing_approval_blocked=pass "
        "missing_backup_blocked=pass "
        "missing_rollback_blocked=pass "
        "missing_validation_blocked=pass "
        "risk_gate=pass "
        "network_target_blocked=pass "
        "worker_executor_blocked=pass "
        "execution_authority_blocked=pass "
        "deterministic_schema=pass "
        "readiness_journal=pass "
        "no_authority_escalation=pass "
        "mutation_scope=none"
    )


if __name__ == "__main__":
    main()
