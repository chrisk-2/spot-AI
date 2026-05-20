#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path("watch/phase7/runs/full-current")
OBSERVER = Path("watch/phase7/spot-readonly-observer.py")


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


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in records)
    )


def assert_eq(got, want, label: str) -> None:
    if got != want:
        raise SystemExit(f"ASSERT FAIL {label}: got={got!r} want={want!r}")


def assert_true(value: bool, label: str) -> None:
    if not value:
        raise SystemExit(f"ASSERT FAIL {label}")


def observe(target: str, source: Path, action: str = "observe") -> dict:
    return json_out([
        str(OBSERVER),
        "--root",
        str(ROOT),
        "--target",
        target,
        "--source",
        str(source),
        "--requested-action",
        action,
    ])


def main() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)

    ROOT.mkdir(parents=True, exist_ok=True)

    fixture_dir = ROOT / "fixtures"
    fleet_status = fixture_dir / "fleet-status.json"
    routing_audit = fixture_dir / "routing-audit.jsonl"
    phase6_journal = fixture_dir / "phase6-fixture-service.jsonl"
    synthetic = fixture_dir / "phase7-synthetic.json"

    write_json(fleet_status, {
        "hosts": {
            "spot-worker-01": {"healthy": True},
            "spot-worker-02": {"healthy": True},
            "spot-worker-03": {"healthy": True},
            "spot-worker-04": {"healthy": True},
            "spot-worker-05": {"healthy": True},
            "spot-worker-06": {"healthy": True},
        }
    })

    write_jsonl(routing_audit, [
        {"role": "general", "worker": "spot-worker-01"},
        {"role": "utility", "worker": "spot-worker-02"},
        {"role": "coding", "worker": "spot-worker-03"},
        {"role": "heavy", "worker": "spot-worker-04"},
        {"role": "reasoning", "worker": "spot-worker-06"},
    ])

    write_jsonl(phase6_journal, [
        {
            "action": "start",
            "result": "applied",
            "mutation_scope": "fixture_only",
        },
        {
            "action": "restart",
            "result": "rolled_back",
            "mutation_scope": "fixture_only",
        },
    ])

    write_json(synthetic, {
        "services": [
            {"name": "fixture-api", "state": "running"},
            {"name": "fixture-worker", "state": "degraded"},
            {"name": "fixture-cache", "state": "failed"},
        ]
    })

    fleet = observe("fleet-status", fleet_status)
    assert_eq(fleet["schema"], "phase7.readonly_observation.v1", "schema")
    assert_eq(fleet["mutation_scope"], "none", "fleet mutation scope")
    assert_eq(fleet["write_scope"], "phase7_runs_only", "fleet write scope")
    assert_eq(fleet["summary"]["host_count"], 6, "fleet host count")
    assert_eq(fleet["summary"]["unhealthy_count"], 0, "fleet unhealthy count")

    routing = observe("routing-audit-summary", routing_audit)
    assert_eq(routing["summary"]["records"], 5, "routing records")
    assert_eq(routing["summary"]["fallback_count"], 0, "routing fallback count")
    assert_eq(routing["summary"]["violation_count"], 0, "routing violation count")

    phase6 = observe("phase6-fixture-journal", phase6_journal)
    assert_eq(phase6["summary"]["records"], 2, "phase6 journal records")
    assert_eq(phase6["summary"]["result_counts"]["applied"], 1, "phase6 applied count")
    assert_eq(phase6["summary"]["result_counts"]["rolled_back"], 1, "phase6 rollback count")

    synthetic_report = observe("phase7-synthetic-fixture", synthetic)
    assert_eq(
        synthetic_report["summary"]["service_count"],
        3,
        "synthetic service count",
    )
    assert_eq(
        synthetic_report["summary"]["degraded_or_failed_count"],
        2,
        "synthetic incident count",
    )
    assert_eq(
        len(synthetic_report["summary"]["incident_candidates"]),
        2,
        "incident candidates",
    )

    run([
        str(OBSERVER),
        "--root",
        str(ROOT),
        "--target",
        "phase7-synthetic-fixture",
        "--source",
        str(synthetic),
        "--requested-action",
        "restart",
    ], expect_ok=False)

    run([
        str(OBSERVER),
        "--root",
        str(ROOT),
        "--target",
        "phase7-synthetic-fixture",
        "--source",
        str(synthetic),
        "--requested-action",
        "systemctl",
    ], expect_ok=False)

    run([
        str(OBSERVER),
        "--root",
        str(ROOT),
        "--target",
        "phase7-synthetic-fixture",
        "--source",
        str(synthetic),
        "--requested-action",
        "iptables",
    ], expect_ok=False)

    run([
        str(OBSERVER),
        "--root",
        str(ROOT),
        "--target",
        "production-service",
        "--source",
        str(synthetic),
        "--requested-action",
        "observe",
    ], expect_ok=False)

    run([
        str(OBSERVER),
        "--root",
        str(ROOT),
        "--target",
        "phase7-synthetic-fixture",
        "--source",
        "/etc/passwd",
        "--requested-action",
        "observe",
    ], expect_ok=False)

    reports_dir = ROOT / "reports"
    journal = ROOT / "journals" / "phase7-readonly-observations.jsonl"

    assert_true(reports_dir.exists(), "reports dir exists")
    assert_true(journal.exists(), "journal exists")

    reports = list(reports_dir.glob("*.json"))
    assert_eq(len(reports), 4, "report count")

    records = [
        json.loads(line)
        for line in journal.read_text().splitlines()
        if line.strip()
    ]

    assert_eq(len(records), 4, "journal record count")

    for record in records:
        assert_eq(record["schema"], "phase7.readonly_observation.v1", "record schema")
        assert_eq(record["mutation_scope"], "none", "record mutation scope")
        assert_eq(record["write_scope"], "phase7_runs_only", "record write scope")
        assert_true("report_hash" in record, "record hash present")

    print("RESULT: PASS")
    print(
        "cases=12 "
        "readonly_observation=pass "
        "mutation_verbs_blocked=pass "
        "production_targets_blocked=pass "
        "fleet_status_summary=pass "
        "routing_audit_summary=pass "
        "phase6_journal_summary=pass "
        "incident_candidates=pass "
        "deterministic_schema=pass "
        "write_scope=phase7_runs_only "
        "service_restart_blocked=pass "
        "network_mutation_blocked=pass "
        "mutation_scope=none"
    )


if __name__ == "__main__":
    main()
