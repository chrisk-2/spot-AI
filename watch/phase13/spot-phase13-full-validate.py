#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path("watch/phase13/runs/full-current")
FABRIC = Path("watch/phase13/spot-operational-intelligence-fabric.py")


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


def make_input(name: str, missing: bool = False, failed: bool = False) -> Path:
    proofs = {
        "phase7_readonly_observation": {"result": "pass"},
        "phase8_dryrun_planning": {"result": "pass"},
        "phase9_lowrisk_wrapper": {"result": "pass"},
        "phase10_rollback_integrated": {"result": "pass"},
        "phase11_supervised_chain": {"result": "pass"},
        "phase12_advisory_learning": {"result": "pass"},
    }

    if missing:
        proofs.pop("phase10_rollback_integrated")

    if failed:
        proofs["phase11_supervised_chain"] = {"result": "fail"}

    path = ROOT / "inputs" / f"{name}.json"

    write_json(path, {
        "fabric_id": name,
        "proofs": proofs,
    })

    return path


def fabric(input_file: Path) -> dict:
    return json_out([
        str(FABRIC),
        "--root",
        str(ROOT),
        "--input-file",
        str(input_file),
    ])


def main() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)

    ROOT.mkdir(parents=True, exist_ok=True)

    ready = fabric(make_input("ready"))

    assert_eq(
        ready["schema"],
        "phase13.operational_intelligence.v1",
        "schema",
    )

    assert_eq(
        ready["readiness"],
        "ready_for_operator_review",
        "ready classification",
    )

    assert_eq(
        ready["authority"],
        "advisory_only",
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
        ready["production_mutation_allowed"],
        False,
        "production mutation blocked",
    )

    assert_eq(
        ready["mutation_scope"],
        "none",
        "mutation scope",
    )

    assert_true(
        "require_operator_review_before_any_live_scope" in ready["recommendations"],
        "operator review recommendation",
    )

    missing = fabric(make_input("missing", missing=True))

    assert_eq(
        missing["readiness"],
        "blocked_missing_proof",
        "missing proof classification",
    )

    assert_true(
        "phase10_rollback_integrated" in missing["missing_proofs"],
        "missing proof listed",
    )

    assert_true(
        "do_not_advance_phase" in missing["recommendations"],
        "missing blocks advance",
    )

    failed = fabric(make_input("failed", failed=True))

    assert_eq(
        failed["readiness"],
        "blocked_failed_proof",
        "failed proof classification",
    )

    assert_true(
        "phase11_supervised_chain" in failed["failed_proofs"],
        "failed proof listed",
    )

    assert_true(
        "do_not_advance_phase" in failed["recommendations"],
        "failed blocks advance",
    )

    envelopes_dir = ROOT / "envelopes"
    journal = ROOT / "journals" / "phase13-operational-intelligence.jsonl"

    assert_true(envelopes_dir.exists(), "envelopes dir")
    assert_true(journal.exists(), "journal exists")

    envelopes = list(envelopes_dir.glob("*.json"))

    assert_eq(
        len(envelopes),
        3,
        "envelope count",
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
            "phase13.operational_intelligence.v1",
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
            record["production_mutation_allowed"],
            False,
            "record production mutation blocked",
        )

        assert_eq(
            record["mutation_scope"],
            "none",
            "record mutation scope",
        )

        assert_true(
            "envelope_hash" in record,
            "envelope hash",
        )

    print("RESULT: PASS")

    print(
        "cases=15 "
        "fabric_aggregation=pass "
        "readiness_classification=pass "
        "advisory_recommendations=pass "
        "execution_authority_blocked=pass "
        "approval_authority_blocked=pass "
        "routing_authority_blocked=pass "
        "ownership_authority_blocked=pass "
        "production_mutation_blocked=pass "
        "missing_proof_blocked=pass "
        "failed_proof_blocked=pass "
        "deterministic_schema=pass "
        "fabric_journal=pass "
        "no_authority_escalation=pass "
        "mutation_scope=none"
    )


if __name__ == "__main__":
    main()
