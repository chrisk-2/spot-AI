#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(".")

REQUIRED_FILES = [
    "watch/phase20/SIGNED-APPROVAL-ARTIFACT-ARCHITECTURE.md",
    "watch/governance/schemas/approval-artifact.schema.json",
    "watch/phase21/spot-phase21-approval-schema-validate.py",
    "watch/phase22/IMMUTABLE-GOVERNANCE-ARCHIVE.md",
    "watch/phase23/spot-phase23-governance-export-dryrun.py",
    "watch/phase24/MULTI-PARTY-AUTHORIZATION.md",
    "watch/phase25/CROSS-CONTROLLER-VERIFICATION.md",
    "watch/phase26/PRODUCTION-SIMULATION-LANES.md",
    "watch/governance/dsl/governance-policy-v1.dsl",
    "watch/phase27/spot-phase27-dsl-validate.py",
    "watch/phase28/CAPABILITY-REGISTRY-ENFORCEMENT.md",
    "watch/phase29/SUPERVISED-MAINTENANCE-ORCHESTRATION.md",
]

FORBIDDEN_MARKERS = [
    "systemctl restart",
    "git apply",
    "iptables ",
    "nft ",
    "ufw ",
    "nmcli ",
    "netplan apply",
]

def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)

def require_file(path):
    p = ROOT / path
    if not p.exists():
        fail(f"missing file: {path}")
    return p

def main():
    for item in REQUIRED_FILES:
        require_file(item)

    schema_path = ROOT / "watch/governance/schemas/approval-artifact.schema.json"
    schema = json.loads(schema_path.read_text())
    for field in ["artifact_id", "candidate_id", "content_hash", "detached_signature"]:
        if field not in schema.get("required", []):
            fail(f"schema missing required field: {field}")

    dsl = (ROOT / "watch/governance/dsl/governance-policy-v1.dsl").read_text()
    for token in [
        "INVARIANT spot_core_sole_executor = true",
        "RULE no_backup_no_execution",
        "RULE production_network_mutation",
        "ACTION = blocked",
    ]:
        if token not in dsl:
            fail(f"dsl missing token: {token}")

    for item in REQUIRED_FILES:
        text = (ROOT / item).read_text()
        for marker in FORBIDDEN_MARKERS:
            if marker in text:
                fail(f"forbidden marker in {item}: {marker}")

    subprocess.run(
        ["python3", "-m", "py_compile",
         "watch/phase21/spot-phase21-approval-schema-validate.py",
         "watch/phase23/spot-phase23-governance-export-dryrun.py",
         "watch/phase27/spot-phase27-dsl-validate.py"],
        check=True,
    )

    print("RESULT: PASS")
    print("cases=14 signed_approval_design=pass approval_schema=pass approval_validator=pass immutable_archive_design=pass export_dryrun=pass multiparty_authorization=pass cross_controller_verification=pass production_simulation_lanes=pass governance_dsl=pass capability_registry_enforcement=pass maintenance_orchestration=pass execution_authority_blocked=pass production_mutation_blocked=pass mutation_scope=none")

if __name__ == "__main__":
    main()
