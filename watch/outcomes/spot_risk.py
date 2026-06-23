#!/usr/bin/env python3
import json
from pathlib import Path

RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
RISK_NAMES = {0: "low", 1: "medium", 2: "high"}

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = REPO_ROOT / "config" / "spot-action-risk-rules.json"
POLICY_PATH = REPO_ROOT / "watch" / "policy" / "action-policy.json"

DEFAULT_RULES = {
    "default_risk": "low",
    "risk_floor_rules": [
        {"minimum": "medium", "match": ["firewall", "wan", "opnsense", "unifi", "vlan", "routing", "dhcp", "dns", "nat", "gateway"]},
        {"minimum": "high", "match": ["lockout", "management", "worker_subnet", "default_route", "ssh", "interface_down", "deny_all"]},
    ],
}

def _load_json(path, fallback):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return fallback

def _risk_max(a, b):
    return RISK_NAMES[max(RISK_ORDER.get(a, 0), RISK_ORDER.get(b, 0))]

def _text_blob(action_type="", target="", params=None):
    params = params or {}
    try:
        p = json.dumps(params, sort_keys=True)
    except Exception:
        p = str(params)
    return f"{action_type} {target} {p}".lower()

def risk_floor(action_type="", target="", params=None):
    rules = _load_json(RULES_PATH, DEFAULT_RULES)
    risk = rules.get("default_risk", "low")
    blob = _text_blob(action_type, target, params)
    for rule in rules.get("risk_floor_rules", []):
        minimum = rule.get("minimum", "low")
        for term in rule.get("match", []):
            if str(term).lower() in blob:
                risk = _risk_max(risk, minimum)
    return risk

def _walk_policy(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk_policy(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_policy(item)

def policy_risk(action_type="", target="", params=None):
    policy = _load_json(POLICY_PATH, {})
    needle = str(action_type or "").lower()
    best = None

    for entry in _walk_policy(policy):
        risk = entry.get("risk") or entry.get("risk_class")
        if risk not in RISK_ORDER:
            continue

        names = [
            entry.get("action_type"),
            entry.get("action"),
            entry.get("name"),
            entry.get("id"),
            entry.get("type"),
        ]
        names = [str(x).lower() for x in names if x]
        if needle and any(needle == n or needle in n or n in needle for n in names):
            best = risk if best is None else _risk_max(best, risk)

    return best

def resolve_risk(action_type="", target="", params=None, supplied=None):
    risk = supplied if supplied in RISK_ORDER else None
    policy = policy_risk(action_type, target, params)
    floor = risk_floor(action_type, target, params)

    out = risk or policy or "low"
    out = _risk_max(out, floor)
    return out
