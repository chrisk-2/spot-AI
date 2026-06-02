#!/usr/bin/env python3
import subprocess
import sys

workers = [
    "spot-worker-01",
    "spot-worker-02",
    "spot-worker-03",
    "spot-worker-04",
    "spot-worker-05",
    "spot-worker-06",
]

errors = []

def run(cmd, timeout=8):
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )

for worker in workers:
    ping = run(["ping", "-c", "1", "-W", "1", worker], timeout=3)
    if ping.returncode != 0:
        errors.append(f"{worker}: ping failed")
        continue

    ssh = run([
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=5",
        worker,
        "hostname; systemctl is-active ssh ollama"
    ], timeout=10)

    if ssh.returncode != 0:
        errors.append(f"{worker}: ssh failed")
        continue

    lines = [x.strip() for x in ssh.stdout.splitlines() if x.strip()]

    if not lines or lines[0] != worker:
        errors.append(f"{worker}: hostname mismatch got={lines[0] if lines else 'missing'}")

    if "active" not in lines[1:]:
        errors.append(f"{worker}: ssh/ollama active state missing")

if errors:
    print("RESULT: FAIL")
    for error in errors:
        print(f"[FAIL] {error}")
    sys.exit(1)

print("RESULT: PASS")
for worker in workers:
    print(f"[PASS] {worker} reachable by ping and ssh")
