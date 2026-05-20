#!/usr/bin/env python3
import argparse
import time
from pathlib import Path
import subprocess

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="watch/runtime/metrics/runs")
    args = ap.parse_args()

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = out_dir / f"runtime-metrics-{ts}.json"
    summary_path = out_dir / f"runtime-health-summary-{ts}.json"

    subprocess.run([
        "watch/runtime/metrics/runtime-metrics-aggregate.py",
        "--output", str(metrics_path)
    ], check=True)

    summary = subprocess.run([
        "watch/runtime/metrics/runtime-health-summary.py",
        "--metrics", str(metrics_path)
    ], text=True, capture_output=True, check=True)

    summary_path.write_text(summary.stdout)

    print(f"metrics={metrics_path}")
    print(f"summary={summary_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
