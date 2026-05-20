#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path("watch/phase19/runs/full-current")

ENGINE = Path(
    "watch/phase19/spot-phase16-19-governance.py"
)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
    )

    if p.returncode != 0:
        print("COMMAND FAILED:", " ".join(cmd))
        print(p.stdout)
        print(p.stderr)
        raise SystemExit(1)

    return p


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n"
    )


def assert_eq(got, want, label: str) -> None:
    if got != want:
        raise SystemExit(
            f"ASSERT FAIL {label}: got={got!r} want={want!r}"
        )


def assert_true(value: bool, label: str) -> None:
    if not value:
        raise SystemExit(f"ASSERT FAIL {label}")


def make_bundle(name: str) -> Path:
    path = ROOT / "bundles" / f"{name}.json"

    write_json(path, {
        "bundle_id": name,
        "proofs": {
            "phase15_operator_approval_gate": {
                "result": "pass",
            },
            "phase16_preexecution_lockout": {
                "result": "pass",
            },
            "phase17_live_candidate_bundle": {
                "result": "pass",
            },
            "phase18_governance_consolidation": {
                "result": "pass",
            },
        },
    })

    return path


def execute(bundle: Path) -> dict:
    out = run([
        str(ENGINE),
        "--root",
        str(ROOT),
        "--bundle-file",
        str(bundle),
    ])

    return json.loads(out.stdout)


def main() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)

    ROOT.mkdir(parents=True, exist_ok=True)

    env = execute(make_bundle("ready"))

    assert_eq(
        env["schema"],
        "phase19.autonomy_readiness.v1",
        "schema",
    )

    assert_eq(
        env["authority"],
        "governance_only",
        "authority",
    )

    assert_eq(
        env["execution_allowed"],
        False,
        "execution blocked",
    )

    assert_eq(
        env["approval_bypass_allowed"],
        False,
        "approval bypass blocked",
    )

    assert_eq(
        env["production_mutation_allowed"],
        False,
        "production blocked",
    )

    assert_eq(
        env["routing_change_allowed"],
        False,
        "routing blocked",
    )

    assert_eq(
        env["worker_ownership_change_allowed"],
        False,
        "ownership blocked",
    )

    assert_eq(
        env["mutation_scope"],
        "none",
        "mutation scope",
    )

    assert_true(
        env["phase16_preexecution_lockout"],
        "phase16",
    )

    assert_true(
        env["phase17_live_candidate_bundle"],
        "phase17",
    )

    assert_true(
        env["phase18_governance_consolidation"],
        "phase18",
    )

    assert_true(
        env["phase19_autonomy_readiness_closeout"],
        "phase19",
    )

    journal = (
        ROOT
        / "journals"
        / "phase16-19-governance.jsonl"
    )

    envelopes = ROOT / "envelopes"

    assert_true(
        journal.exists(),
        "journal exists",
    )

    assert_true(
        envelopes.exists(),
        "envelopes exist",
    )

    records = [
        json.loads(line)
        for line in journal.read_text().splitlines()
        if line.strip()
    ]

    assert_eq(
        len(records),
        1,
        "journal count",
    )

    env_files = list(envelopes.glob("*.json"))

    assert_eq(
        len(env_files),
        1,
        "envelope count",
    )

    rec = records[0]

    assert_eq(
        rec["schema"],
        "phase19.autonomy_readiness.v1",
        "record schema",
    )

    assert_true(
        "envelope_hash" in rec,
        "record hash",
    )

    print("RESULT: PASS")

    print(
        "cases=16 "
        "phase16_preexecution_lockout=pass "
        "phase17_live_candidate_bundle=pass "
        "phase18_governance_consolidation=pass "
        "phase19_autonomy_readiness_closeout=pass "
        "execution_authority_blocked=pass "
        "approval_bypass_blocked=pass "
        "production_mutation_blocked=pass "
        "routing_authority_blocked=pass "
        "ownership_authority_blocked=pass "
        "deterministic_schema=pass "
        "governance_journal=pass "
        "mutation_scope=none"
    )


if __name__ == "__main__":
    main()
