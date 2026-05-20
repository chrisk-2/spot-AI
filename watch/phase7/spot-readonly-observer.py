#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any


DENIED_VERBS = {
    "write",
    "modify",
    "delete",
    "remove",
    "restart",
    "reload",
    "start-service",
    "stop-service",
    "systemctl",
    "apply",
    "git-apply",
    "iptables",
    "nft",
    "pfctl",
    "opnsense",
    "dns-update",
    "dhcp-update",
    "route-add",
    "route-del",
}

DENIED_TARGET_MARKERS = (
    "/etc/",
    "/boot/",
    "/root/",
    "/usr/",
    "/srv/",
    "/var/lib/",
    "/var/run/",
    "/run/systemd/",
    "/mnt/collective/backups/",
)

ALLOWED_TARGETS = {
    "fleet-status",
    "routing-audit-summary",
    "phase6-fixture-journal",
    "phase7-synthetic-fixture",
}


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text())


def read_jsonl(path: Path, limit: int = 500) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(errors="replace").splitlines()[-limit:]:
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def append_jsonl(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True) + "\n")


def guard_request(target: str, requested_action: str, source_path: str) -> None:
    if target not in ALLOWED_TARGETS:
        raise SystemExit("blocked: observation target is not allowlisted")

    action_l = requested_action.lower()
    if action_l in DENIED_VERBS:
        raise SystemExit("blocked: denied mutation verb")

    source_l = source_path.lower()
    for marker in DENIED_TARGET_MARKERS:
        if marker in source_l:
            raise SystemExit("blocked: denied production target marker")


def summarize_fleet_status(path: Path) -> dict[str, Any]:
    data = load_json(path, {})
    hosts = data.get("hosts", {})
    if isinstance(hosts, list):
        host_count = len(hosts)
        unhealthy = [
            h.get("host") or h.get("name")
            for h in hosts
            if h.get("healthy") is False or h.get("ok") is False
        ]
    elif isinstance(hosts, dict):
        host_count = len(hosts)
        unhealthy = [
            name
            for name, h in hosts.items()
            if isinstance(h, dict)
            and (h.get("healthy") is False or h.get("ok") is False)
        ]
    else:
        host_count = 0
        unhealthy = []

    return {
        "target_type": "fleet_status",
        "host_count": host_count,
        "unhealthy_count": len(unhealthy),
        "unhealthy_hosts": sorted([x for x in unhealthy if x]),
        "status": "observe_only",
    }


def summarize_routing_audit(path: Path) -> dict[str, Any]:
    records = read_jsonl(path)
    role_counts: dict[str, int] = {}
    fallback_count = 0
    violation_count = 0

    for record in records:
        role = record.get("role") or record.get("requested_role") or "unknown"
        role_counts[role] = role_counts.get(role, 0) + 1
        if record.get("fallback") is True:
            fallback_count += 1
        if record.get("violation") is True:
            violation_count += 1

    return {
        "target_type": "routing_audit_summary",
        "records": len(records),
        "role_counts": dict(sorted(role_counts.items())),
        "fallback_count": fallback_count,
        "violation_count": violation_count,
        "status": "observe_only",
    }


def summarize_phase6_journal(path: Path) -> dict[str, Any]:
    records = read_jsonl(path)
    result_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}

    for record in records:
        result = record.get("result", "unknown")
        action = record.get("action", "unknown")
        result_counts[result] = result_counts.get(result, 0) + 1
        action_counts[action] = action_counts.get(action, 0) + 1

    return {
        "target_type": "phase6_fixture_journal",
        "records": len(records),
        "result_counts": dict(sorted(result_counts.items())),
        "action_counts": dict(sorted(action_counts.items())),
        "status": "observe_only",
    }


def summarize_synthetic_fixture(path: Path) -> dict[str, Any]:
    data = load_json(path, {"services": []})
    services = data.get("services", [])

    degraded = [
        svc.get("name")
        for svc in services
        if svc.get("state") in {"degraded", "failed"}
    ]

    incident_candidates = [
        {
            "service": svc.get("name"),
            "state": svc.get("state"),
            "severity": "medium" if svc.get("state") == "degraded" else "high",
            "recommendation": "observe_only_no_action",
        }
        for svc in services
        if svc.get("state") in {"degraded", "failed"}
    ]

    return {
        "target_type": "phase7_synthetic_fixture",
        "service_count": len(services),
        "degraded_or_failed_count": len(degraded),
        "incident_candidates": incident_candidates,
        "status": "observe_only",
    }


def observe(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    source = Path(args.source)
    guard_request(args.target, args.requested_action, str(source))

    if args.target == "fleet-status":
        summary = summarize_fleet_status(source)
    elif args.target == "routing-audit-summary":
        summary = summarize_routing_audit(source)
    elif args.target == "phase6-fixture-journal":
        summary = summarize_phase6_journal(source)
    elif args.target == "phase7-synthetic-fixture":
        summary = summarize_synthetic_fixture(source)
    else:
        raise SystemExit("blocked: unsupported observation target")

    report = {
        "schema": "phase7.readonly_observation.v1",
        "ts": int(time.time()),
        "target": args.target,
        "requested_action": args.requested_action,
        "source": str(source),
        "summary": summary,
        "mutation_scope": "none",
        "write_scope": "phase7_runs_only",
    }
    report["report_hash"] = sha256_text(canonical(report))

    out = root / "reports" / f"{args.target}.json"
    journal = root / "journals" / "phase7-readonly-observations.jsonl"

    write_json(out, report)
    append_jsonl(journal, report)

    return report


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Phase 7 read-only observer")
    p.add_argument("--root", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--requested-action", default="observe")
    return p


def main() -> None:
    args = build_parser().parse_args()
    report = observe(args)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
