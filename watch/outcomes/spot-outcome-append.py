#!/usr/bin/env python3
import argparse
import json
from spot_outcomes import append_decision_record
from spot_risk import resolve_risk

p = argparse.ArgumentParser()
p.add_argument("--action-type", required=True)
p.add_argument("--target", required=True)
p.add_argument("--risk", choices=["low", "medium", "high"])
p.add_argument("--decision", required=True, choices=["executed", "dismissed", "edited"])
p.add_argument("--params", default="{}")
p.add_argument("--immediate-result", default="null")
p.add_argument("--edited-delta", default="null")
args = p.parse_args()

params = json.loads(args.params)
risk = resolve_risk(args.action_type, args.target, params, args.risk)

print(json.dumps(append_decision_record(
    action_type=args.action_type,
    target=args.target,
    params=params,
    risk=risk,
    decision=args.decision,
    immediate_result=json.loads(args.immediate_result),
    edited_delta=json.loads(args.edited_delta),
), sort_keys=True))
