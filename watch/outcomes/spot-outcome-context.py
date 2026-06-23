#!/usr/bin/env python3
import argparse
from spot_outcomes import summarize_outcomes

p = argparse.ArgumentParser()
p.add_argument("--action-type")
p.add_argument("--target")
p.add_argument("--limit", type=int, default=20)
args = p.parse_args()

print(summarize_outcomes(args.action_type, args.target, args.limit))
