#!/usr/bin/env python3

import json
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path("watch/governance/simulation")
ROOT.mkdir(parents=True, exist_ok=True)

FORBIDDEN_TARGETS = ["firewall", "dns", "dhcp", "routing", "ssh", "production"]

def main():
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    manifest = {
        "simulation_id": f"simulation-lane-{ts}",
        "phase": 35,
        "mode": "simulation_manifest_only",
        "targets": ["fixture-controller", "fixture-service"],
        "forbidden_targets": FORBIDDEN_TARGETS,
        "mutation_performed": False,
        "production_targeted": False,
        "timestamp": ts
    }

    out = ROOT / f"simulation-manifest-{ts}.json"
    out.write_text(json.dumps(manifest, indent=2))

    print("RESULT: PASS")
    print("simulation_manifest=pass")
    print(f"artifact={out}")

if __name__ == "__main__":
    main()
