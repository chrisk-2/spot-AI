#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


FORBIDDEN_RECOMMENDATIONS = {
    "execute",
    "approve",
    "change-routing",
    "change-worker-owner",
    "restart-service",
    "modify-firewall",
    "modify-dns",
    "modify-dhcp",
    "modify-network",
    "apply-config",
}

ALLOWED_RECOMMENDATIONS = {
    "prefer-stable-worker",
    "increase-validation-depth",
    "require-human-review",
    "lower-confidence",
    "observe-only",
}


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def append_jsonl(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True) + "\n")


def block(reason: str) -> None:
    raise SystemExit(f"blocked: {reason}")


def score_worker(record: dict[str, Any]) -> dict[str, Any]:
    name = record["worker"]
    success = int(record.get("success", 0))
    rollback = int(record.get("rollback", 0))
    blocked = int(record.get("blocked", 0))
    total = max(success + rollback + blocked, 1)

    stability = round((success - rollback - blocked) / total, 4)
    confidence = "high" if total >= 5 and stability >= 0.6 else "medium" if stability >= 0.2 else "low"

    return {
        "worker": name,
        "total_events": total,
        "success": success,
        "rollback": rollback,
        "blocked": blocked,
        "stability_score": stability,
        "confidence": confidence,
    }


def build_report(input_data: dict[str, Any], recommendation: str) -> dict[str, Any]:
    if recommendation in FORBIDDEN_RECOMMENDATIONS:
        block("forbidden recommendation authority")
    if recommendation not in ALLOWED_RECOMMENDATIONS:
        block("unknown recommendation type")

    target = input_data.get("target", "advisory-learning")
    if target not in {"advisory-learning", "fixture-service"}:
        block("production target not allowed")

    workers = input_data.get("workers", [])
    scores = [score_worker(w) for w in workers]
    scores = sorted(scores, key=lambda x: (-x["stability_score"], x["worker"]))

    top_worker = scores[0]["worker"] if scores else None

    report = {
        "schema": "phase12.advisory_learning.v1",
        "ts": int(time.time()),
        "target": target,
        "recommendation_type": recommendation,
        "recommended_worker": top_worker,
        "scores": scores,
        "authority": "advisory_only",
        "execution_allowed": False,
        "approval_allowed": False,
        "routing_change_allowed": False,
        "worker_ownership_change_allowed": False,
        "mutation_scope": "none",
    }

    report["report_hash"] = sha256_text(canonical(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 12 advisory learning engine")
    parser.add_argument("--root", required=True)
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--recommendation", required=True)
    args = parser.parse_args()

    root = Path(args.root)
    input_data = load_json(Path(args.input_file), {})
    report = build_report(input_data, args.recommendation)

    out = root / "reports" / f"{report['recommendation_type']}.json"
    journal = root / "journals" / "phase12-advisory-learning.jsonl"

    write_json(out, report)
    append_jsonl(journal, report)

    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
