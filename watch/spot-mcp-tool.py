from __future__ import annotations

import argparse
import json
import sys

from spot_mcp_client import SpotClient


def print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Spot MCP-style operator wrapper")
    sub = parser.add_subparsers(dest="command", required=True)

    rlf = sub.add_parser("read-local-file")
    rlf.add_argument("--path", required=True)

    wlf = sub.add_parser("write-local-file")
    wlf.add_argument("--path", required=True)
    wlf.add_argument("--content-file", required=True)

    sub.add_parser("health")
    sub.add_parser("routing")
    sub.add_parser("fleet-ping")
    sub.add_parser("stats-latency")

    rd = sub.add_parser("recent-decisions")
    rd.add_argument("--limit", type=int, default=25)

    ra = sub.add_parser("routing-audit")
    ra.add_argument("--limit", type=int, default=200)

    rf = sub.add_parser("read-file")
    rf.add_argument("--worker", required=True)
    rf.add_argument("--path", required=True)

    val = sub.add_parser("validate")
    val.add_argument("--worker", required=True)
    val.add_argument("commands", nargs="+")

    wf = sub.add_parser("write-file")
    wf.add_argument("--worker", required=True)
    wf.add_argument("--path", required=True)
    wf.add_argument("--content-file", required=True)

    rs = sub.add_parser("restart-service")
    rs.add_argument("--worker", required=True)
    rs.add_argument("--service", required=True)

    q = sub.add_parser("quarantine")
    q.add_argument("--worker", required=True)
    q.add_argument("--seconds", type=int, default=1800)
    q.add_argument("--reason", default="manual_quarantine")

    rel = sub.add_parser("release")
    rel.add_argument("--worker", required=True)

    ex = sub.add_parser("exec")
    ex.add_argument("--role", required=True, choices=["general", "utility", "coding", "heavy", "watcher"])
    ex.add_argument("--prompt", required=True)
    ex.add_argument("--model")
    ex.add_argument("--worker")
    ex.add_argument("--gpu-lane")
    ex.add_argument("--priority")
    ex.add_argument("--queue-wait-ms", type=int)
    ex.add_argument("--queue-poll-ms", type=int)
    ex.add_argument("--no-fallback", action="store_true")
    ex.add_argument("--no-burst", action="store_true")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    client = SpotClient()

    if args.command == "read-local-file":
        print_json(client.read_local_file(path=args.path))
        return 0

    if args.command == "write-local-file":
        with open(args.content_file, "r", encoding="utf-8") as handle:
            content = handle.read()
        print_json(client.write_local_file(path=args.path, content=content))
        return 0

    if args.command == "health":
        print_json(client.health())
        return 0

    if args.command == "routing":
        print_json(client.routing())
        return 0

    if args.command == "fleet-ping":
        print_json(client.fleet_ping())
        return 0

    if args.command == "stats-latency":
        print_json(client.stats_latency())
        return 0

    if args.command == "recent-decisions":
        print_json(client.recent_decisions(limit=args.limit))
        return 0

    if args.command == "routing-audit":
        print_json(client.routing_audit(limit=args.limit))
        return 0

    if args.command == "read-file":
        print_json(client.read_file(worker=args.worker, path=args.path))
        return 0

    if args.command == "validate":
        print_json(client.validate(worker=args.worker, commands=args.commands))
        return 0

    if args.command == "write-file":
        with open(args.content_file, "r", encoding="utf-8") as handle:
            content = handle.read()
        print_json(client.write_file(worker=args.worker, path=args.path, content=content))
        return 0

    if args.command == "restart-service":
        print_json(client.restart_service(worker=args.worker, service=args.service))
        return 0

    if args.command == "quarantine":
        print_json(client.quarantine_worker(worker=args.worker, seconds=args.seconds, reason=args.reason))
        return 0

    if args.command == "release":
        print_json(client.release_worker(worker=args.worker))
        return 0

    if args.command == "exec":
        payload = {
            "prompt": args.prompt,
            "role": args.role,
            "model": args.model,
            "stream": False,
            "worker": args.worker,
            "gpu_lane": args.gpu_lane,
            "allow_fallback": not args.no_fallback,
            "allow_burst": not args.no_burst,
            "priority": args.priority,
            "queue_wait_ms": args.queue_wait_ms,
            "queue_poll_ms": args.queue_poll_ms,
        }
        print_json(client.exec(payload))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
