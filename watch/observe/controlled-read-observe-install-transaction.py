#!/usr/bin/env python3
"""Dormant K21D installer boundary.

This artifact cannot install files. It validates offline inputs and denies every
execution request until a separately reviewed implementation replaces this
dormant boundary.
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--offline-self-test",
        action="store_true",
        help="Confirm the installer remains dormant.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Always denied in the dormant construction phase.",
    )
    args = parser.parse_args()

    if args.execute:
        print(
            "[DENY] K21D installation execution is not implemented or authorized",
            file=sys.stderr,
        )
        print("installation_performed=false", file=sys.stderr)
        print("daemon_reload_performed=false", file=sys.stderr)
        print("execution_allowed=false", file=sys.stderr)
        print("mutation_authority=false", file=sys.stderr)
        return 2

    if not args.offline_self_test:
        print(
            "[DENY] dormant installer requires --offline-self-test",
            file=sys.stderr,
        )
        return 2

    print("[PASS] K21D installer is dormant")
    print("system_path_installation_authorized=false")
    print("backup_created=false")
    print("installation_manifest_created=false")
    print("authorization_consumed=false")
    print("installation_performed=false")
    print("daemon_reload_performed=false")
    print("activation_authorized=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
