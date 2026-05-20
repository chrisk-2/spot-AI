#!/usr/bin/env python3

import json
import sys
from pathlib import Path

REQUIRED = {
    "artifact_id",
    "candidate_id",
    "request_id",
    "operator_identity",
    "approval_scope",
    "targets",
    "actions",
    "issued_ts",
    "expires_ts",
    "governance_hash",
    "content_hash",
    "signer_identity",
    "signature_algorithm",
    "detached_signature",
    "immutable_receipt_id",
}

def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)

def main():
    if len(sys.argv) != 2:
        fail("usage: validator <artifact.json>")

    path = Path(sys.argv[1])

    if not path.exists():
        fail("artifact missing")

    data = json.loads(path.read_text())

    missing = sorted(REQUIRED - set(data.keys()))

    if missing:
        fail(f"missing fields: {','.join(missing)}")

    print("RESULT: PASS")
    print("approval_artifact_schema=valid")

if __name__ == "__main__":
    main()
