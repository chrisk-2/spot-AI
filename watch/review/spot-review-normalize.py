#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

def normalized_no(reason):
    return {
        "provider": "",
        "reviewer": "",
        "review_id": "",
        "patch_bundle_id": "",
        "verdict": "NO",
        "execution_allowed": False,
        "confidence": "low",
        "intent_match": "fail",
        "code_match": "not_applicable",
        "policy_match": "fail",
        "phase_match": "fail",
        "backup_required": True,
        "backup_verified": False,
        "rollback_defined": False,
        "validation_defined": False,
        "required_fixes": [],
        "blocking_findings": [reason],
        "notes": reason
    }

def main():
    ap = argparse.ArgumentParser(description="Normalize model review JSON into Spot review contract.")
    ap.add_argument("input")
    args = ap.parse_args()

    try:
        raw = json.loads(Path(args.input).read_text())
    except Exception as e:
        print(json.dumps(normalized_no(f"invalid_json: {e}"), indent=2))
        return

    out = normalized_no("default_no")
    out.update({k: raw.get(k, out[k]) for k in out.keys() if k in raw})

    if out["verdict"] not in ["PASS", "FIX", "NO"]:
        out = normalized_no("invalid_verdict")

    if out["verdict"] == "PASS":
        gates = [
            out.get("execution_allowed") is True,
            out.get("policy_match") == "pass",
            out.get("phase_match") == "pass",
            out.get("rollback_defined") is True,
            out.get("validation_defined") is True,
        ]
        if not all(gates):
            out["verdict"] = "NO"
            out["execution_allowed"] = False
            out.setdefault("blocking_findings", []).append("pass_missing_required_gates")

    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
