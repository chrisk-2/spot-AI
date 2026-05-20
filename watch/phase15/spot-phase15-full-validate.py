#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path("watch/phase15/runs/full-current")
GATE = Path("watch/phase15/spot-operator-approval-gate.py")


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


def make_candidate(name: str) -> Path:
    path = ROOT / "candidates" / f"{name}.json"
    write_json(path, {
        "candidate_id": name,
        "target": "approved-fixture-adjacent-service",
        "action": "review-low-risk-service-action",
        "risk_class": "low",
    })
    return path


def make_token(name: str, **overrides) -> Path:
    now = int(time.time())
    token = {
        "schema": "phase15.operator_approval.v1",
        "approval_id": f"approval-{name}",
        "candidate_id": name,
        "approved_by": "operator",
        "approval_scope": "low_risk_service_review_only",
        "approved_at": now,
        "expires_at": now + 300,
        "approved_action": "review-low-risk-service-action",
        "approved_target": "approved-fixture-adjacent-service",
        "operator_confirmed": True,
    }
    token.update(overrides)
    path = ROOT / "tokens" / f"{name}.json"
    write_json(path, token)
    return path


def gate(candidate: Path, token: Path, expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
    return run([
        str(GATE),
        "--root",
        str(ROOT),
        "--candidate-file",
        str(candidate),
        "--approval-token-file",
        str(token),
    ], expect_ok=expect_ok)


def main() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)

    ROOT.mkdir(parents=True, exist_ok=True)

    candidate = make_candidate("valid")
    token = make_token("valid")

    ok = gate(candidate, token)
    ok_obj = json.loads(ok.stdout)

    assert_eq(ok_obj["schema"], "phase15.approval_gate.v1", "schema")
    assert_eq(ok_obj["result"], "accepted_for_review_handoff", "accepted")
    assert_eq(ok_obj["authority"], "approval_gate_only", "authority")
    assert_eq(ok_obj["execution_allowed"], False, "execution blocked")
    assert_eq(ok_obj["approval_bypass_allowed"], False, "approval bypass blocked")
    assert_eq(ok_obj["production_mutation_allowed"], False, "production blocked")
    assert_eq(ok_obj["mutation_scope"], "none", "mutation scope")

    missing_token = ROOT / "tokens" / "missing.json"
    gate(make_candidate("missing-token"), missing_token, expect_ok=False)

    expired = make_token("expired", expires_at=int(time.time()) - 1)
    gate(make_candidate("expired"), expired, expect_ok=False)

    mismatch = make_token("candidate-mismatch", candidate_id="wrong-candidate")
    gate(make_candidate("candidate-mismatch"), mismatch, expect_ok=False)

    target_mismatch = make_token("target-mismatch", approved_target="wrong-target")
    gate(make_candidate("target-mismatch"), target_mismatch, expect_ok=False)

    action_mismatch = make_token("action-mismatch", approved_action="wrong-action")
    gate(make_candidate("action-mismatch"), action_mismatch, expect_ok=False)

    scope_mismatch = make_token("scope-mismatch", approval_scope="execute_now")
    gate(make_candidate("scope-mismatch"), scope_mismatch, expect_ok=False)

    unconfirmed = make_token("unconfirmed", operator_confirmed=False)
    gate(make_candidate("unconfirmed"), unconfirmed, expect_ok=False)

    wrong_approver = make_token("wrong-approver", approved_by="spot-core")
    gate(make_candidate("wrong-approver"), wrong_approver, expect_ok=False)

    accepted_journal = ROOT / "journals" / "phase15-accepted-approvals.jsonl"
    denied_journal = ROOT / "journals" / "phase15-denied-approvals.jsonl"
    approvals_dir = ROOT / "approvals"

    assert_true(accepted_journal.exists(), "accepted journal exists")
    assert_true(denied_journal.exists(), "denied journal exists")
    assert_true(approvals_dir.exists(), "approvals dir exists")

    accepted = [
        json.loads(line)
        for line in accepted_journal.read_text().splitlines()
        if line.strip()
    ]

    denied = [
        json.loads(line)
        for line in denied_journal.read_text().splitlines()
        if line.strip()
    ]

    approvals = list(approvals_dir.glob("*.json"))

    assert_eq(len(accepted), 1, "accepted count")
    assert_true(len(denied) >= 8, "denied count")
    assert_eq(len(approvals), 1, "approval artifact count")

    for record in accepted:
        assert_eq(record["schema"], "phase15.approval_gate.v1", "accepted schema")
        assert_eq(record["execution_allowed"], False, "accepted execution blocked")
        assert_eq(record["approval_bypass_allowed"], False, "accepted bypass blocked")
        assert_eq(record["production_mutation_allowed"], False, "accepted production blocked")
        assert_eq(record["mutation_scope"], "none", "accepted mutation scope")
        assert_true("record_hash" in record, "accepted hash")

    for record in denied:
        assert_eq(record["schema"], "phase15.approval_gate.v1", "denied schema")
        assert_eq(record["result"], "blocked", "denied result")
        assert_eq(record["execution_allowed"], False, "denied execution blocked")
        assert_eq(record["mutation_scope"], "none", "denied mutation scope")
        assert_true("record_hash" in record, "denied hash")

    print("RESULT: PASS")
    print(
        "cases=15 "
        "approval_token_acceptance=pass "
        "missing_token_blocked=pass "
        "expired_token_blocked=pass "
        "candidate_mismatch_blocked=pass "
        "target_mismatch_blocked=pass "
        "action_mismatch_blocked=pass "
        "scope_mismatch_blocked=pass "
        "operator_confirmation_blocked=pass "
        "approver_gate=pass "
        "execution_authority_blocked=pass "
        "deterministic_schema=pass "
        "approval_journal=pass "
        "denied_journal=pass "
        "mutation_scope=none"
    )


if __name__ == "__main__":
    main()
