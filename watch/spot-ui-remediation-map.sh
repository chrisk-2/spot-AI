#!/usr/bin/env bash
set -Eeuo pipefail

need_cmd(){ command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing command: $1" >&2; exit 2; }; }
need_cmd jq

usage(){ echo "Usage: $(basename "$0") '<json-array-of-factors>'"; }

FACTORS_JSON="${1:-}"
[[ -n "$FACTORS_JSON" ]] || { usage >&2; exit 2; }

jq -c -n --argjson factors "$FACTORS_JSON" '
  def lower: tostring | ascii_downcase;
  def has($needle): any($factors[]?; (lower | contains($needle)));
  def base($class; $suggestion; $risk; $backup; $autonomy): {
    class:$class,
    suggestion:$suggestion,
    risk_class:$risk,
    backup_required:$backup,
    autonomy:$autonomy,
    state:"advisory",
    policy_note:"advisory only; any future mutating path must use Spot Core backup-first policy"
  };

  if has("remediation violation") or has("remediation violation memory") then
    base(
      "ledger_cleanup";
      "Inspect remediation-state memory and confirm whether remembered routing debt is still valid.";
      "LOW";
      true;
      "advisory_only"
    )
  elif has("routing violation") or has("audit violation") then
    base(
      "routing_audit_review";
      "Review routing audit entries for owner mismatch, fallback misuse, or stale route-class violations.";
      "MEDIUM";
      true;
      "approval_required"
    )
  elif has("fallback") then
    base(
      "fallback_investigation";
      "Inspect recent decisions and worker health to determine why fallback routing is occurring.";
      "LOW";
      false;
      "advisory_only"
    )
  elif has("latency") then
    base(
      "worker_performance_check";
      "Inspect worker latency history, GPU process state, Ollama health, and model load state.";
      "LOW";
      false;
      "advisory_only"
    )
  elif has("quarantine") then
    base(
      "quarantine_review";
      "Inspect quarantine reason and recent worker health before changing quarantine state.";
      "LOW";
      false;
      "assisted_only"
    )
  elif has("core health") or has("core failing") then
    base(
      "core_health_review";
      "Inspect spot-core health, container status, and recent logs.";
      "MEDIUM";
      true;
      "approval_required"
    )
  elif has("publisher stale") or has("feed stale") then
    base(
      "publisher_health_check";
      "Check publisher service status, render script syntax, and published timestamp freshness.";
      "LOW";
      false;
      "assisted_only"
    )
  elif has("worker failure") or has("worker offline") then
    base(
      "worker_health_check";
      "Check worker reachability, Ollama service health, GPU state, disk pressure, and recent logs.";
      "LOW";
      false;
      "assisted_only"
    )
  else
    base(
      "general_investigation";
      "Review incident factors, current fleet status, routing audit, and recent decisions.";
      "LOW";
      false;
      "advisory_only"
    )
  end
  | .factors = $factors
'
