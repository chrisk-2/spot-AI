#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path("watch/phase12/runs/full-current")
ENGINE = Path("watch/phase12/spot-advisory-learning-engine.py")


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


def make_input(name: str, target: str = "advisory-learning") -> Path:
    path = ROOT / "inputs" / f"{name}.json"

    write_json(path, {
        "target": target,
        "workers": [
            {
                "worker": "spot-worker-01",
                "success": 8,
                "rollback": 1,
                "blocked": 1,
            },
            {
                "worker": "spot-worker-03",
                "success": 5,
                "rollback": 3,
                "blocked": 2,
            },
            {
                "worker": "spot-worker-04",
                "success": 9,
                "rollback": 0,
                "blocked": 1,
            },
        ],
    })

    return path


def advise(input_file: Path, recommendation: str, expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
    return run([
        str(ENGINE),
        "--root",
        str(ROOT),
        "--input-file",
        str(input_file),
        "--recommendation",
        recommendation,
    ], expect_ok=expect_ok)


def main() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)

    ROOT.mkdir(parents=True, exist_ok=True)

    data = make_input("learning")

    stable = json.loads(
        advise(data, "prefer-stable-worker").stdout
    )

    assert_eq(
        stable["schema"],
        "phase12.advisory_learning.v1",
        "schema",
    )

    assert_eq(
        stable["authority"],
        "advisory_only",
        "authority",
    )

    assert_eq(
        stable["execution_allowed"],
        False,
        "execution blocked",
    )

    assert_eq(
        stable["approval_allowed"],
        False,
        "approval blocked",
    )

    assert_eq(
        stable["routing_change_allowed"],
        False,
        "routing blocked",
    )

    assert_eq(
        stable["worker_ownership_change_allowed"],
        False,
        "ownership blocked",
    )

    assert_eq(
        stable["mutation_scope"],
        "none",
        "mutation scope",
    )

    assert_eq(
        stable["recommended_worker"],
        "spot-worker-04",
        "top worker",
    )

    assert_true(
        len(stable["scores"]) == 3,
        "score count",
    )

    assert_eq(
        stable["scores"][0]["confidence"],
        "high",
        "confidence weighting",
    )

    review = json.loads(
        advise(data, "require-human-review").stdout
    )

    assert_eq(
        review["authority"],
        "advisory_only",
        "review authority",
    )

    observe = json.loads(
        advise(data, "observe-only").stdout
    )

    assert_eq(
        observe["mutation_scope"],
        "none",
        "observe mutation scope",
    )

    advise(data, "execute", expect_ok=False)
    advise(data, "approve", expect_ok=False)
    advise(data, "change-routing", expect_ok=False)
    advise(data, "change-worker-owner", expect_ok=False)
    advise(data, "restart-service", expect_ok=False)
    advise(data, "modify-firewall", expect_ok=False)

    prod_input = make_input("production", target="production-service")
    advise(prod_input, "prefer-stable-worker", expect_ok=False)

    reports_dir = ROOT / "reports"
    journal = ROOT / "journals" / "phase12-advisory-learning.jsonl"

    assert_true(reports_dir.exists(), "reports dir")
    assert_true(journal.exists(), "journal exists")

    reports = list(reports_dir.glob("*.json"))

    assert_eq(
        len(reports),
        3,
        "report count",
    )

    records = [
        json.loads(line)
        for line in journal.read_text().splitlines()
        if line.strip()
    ]

    assert_eq(
        len(records),
        3,
        "journal count",
    )

    for record in records:
        assert_eq(
            record["schema"],
            "phase12.advisory_learning.v1",
            "record schema",
        )

        assert_eq(
            record["authority"],
            "advisory_only",
            "record authority",
        )

        assert_eq(
            record["execution_allowed"],
            False,
            "record execution blocked",
        )

        assert_eq(
            record["approval_allowed"],
            False,
            "record approval blocked",
        )

        assert_eq(
            record["routing_change_allowed"],
            False,
            "record routing blocked",
        )

        assert_eq(
            record["worker_ownership_change_allowed"],
            False,
            "record ownership blocked",
        )

        assert_eq(
            record["mutation_scope"],
            "none",
            "record mutation scope",
        )

        assert_true(
            "report_hash" in record,
            "record hash",
        )

    print("RESULT: PASS")

    print(
        "cases=14 "
        "learning_ingest=pass "
        "advisory_scoring=pass "
        "confidence_weighting=pass "
        "recommendation_generation=pass "
        "self_approval_blocked=pass "
        "execution_blocked=pass "
        "routing_mutation_blocked=pass "
        "ownership_mutation_blocked=pass "
        "production_target_blocked=pass "
        "deterministic_schema=pass "
        "advisory_journal=pass "
        "no_authority_escalation=pass "
        "mutation_scope=none"
    )


if __name__ == "__main__":
    main()
