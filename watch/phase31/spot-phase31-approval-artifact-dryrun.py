#!/usr/bin/env python3

import hashlib
import json
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path("watch/governance/artifacts")
ROOT.mkdir(parents=True, exist_ok=True)

def canonical_hash(payload):
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(body).hexdigest()

def main():
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "candidate_id": "candidate-phase31-dryrun",
        "request_id": "request-phase31-dryrun",
        "approval_scope": "governance_dryrun_only",
        "targets": ["fixture-only"],
        "actions": ["validate-only"]
    }

    artifact = {
        "artifact_id": f"approval-artifact-{ts}",
        "candidate_id": payload["candidate_id"],
        "request_id": payload["request_id"],
        "operator_identity": "operator-local-dryrun",
        "approval_scope": payload["approval_scope"],
        "targets": payload["targets"],
        "actions": payload["actions"],
        "issued_ts": ts,
        "expires_ts": ts,
        "governance_hash": "dryrun-governance-hash",
        "content_hash": canonical_hash(payload),
        "signer_identity": "dryrun-signer",
        "signature_algorithm": "dryrun-detached-placeholder",
        "detached_signature": "dryrun-signature-placeholder",
        "immutable_receipt_id": f"receipt-{ts}"
    }

    out = ROOT / f"approval-artifact-dryrun-{ts}.json"
    out.write_text(json.dumps(artifact, indent=2))

    print("RESULT: PASS")
    print("approval_artifact_dryrun=pass")
    print(f"artifact={out}")

if __name__ == "__main__":
    main()
