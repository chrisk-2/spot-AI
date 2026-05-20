#!/usr/bin/env python3

import json
from pathlib import Path

SRC = Path("watch/governance/dsl/governance-policy-v1.dsl")
OUT = Path("watch/governance/dsl/governance-policy-v1.compiled.json")

def main():
    text = SRC.read_text()
    rules = []
    invariants = []

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("INVARIANT "):
            invariants.append(line)
        if line.startswith("RULE "):
            rules.append(line)

    compiled = {
        "policy": "governance_v1",
        "compile_mode": "dryrun_only",
        "invariants": invariants,
        "rules": rules,
        "execution_allowed": False,
        "mutation_authority": False
    }

    OUT.write_text(json.dumps(compiled, indent=2))

    print("RESULT: PASS")
    print("dsl_compile_dryrun=pass")
    print(f"artifact={OUT}")

if __name__ == "__main__":
    main()
