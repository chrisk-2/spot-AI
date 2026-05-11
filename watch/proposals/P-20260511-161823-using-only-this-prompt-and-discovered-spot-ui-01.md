# Spot Proposal P-20260511-161823-using-only-this-prompt-and-discovered-spot-ui-01

status: pending_review  
created_utc: 20260511-161823  
task: Using only this prompt and discovered spot-ui-01 files, produce a coding implementation proposal only. Target exact files only: watch/spot-ui-readiness.sh, watch/spot-ui-render-html.sh, watch/spot-ui-render-risk.sh, watch/spot-ui-risk.json.jq, watch/spot-ui-01.sh, spot-core/spot-ui-01-dashboard-design.md. Primary data source shape includes generated_at, git.dirty, health.spot_core, health.mcp_local, routing.ok, backups.workers_ok, validation.fresh, self_heal.actions, and status. Do not modify cluster_config.json. Do not use wildcard FILES_AFFECTED. Do not use backup .bak paths. Rollback must be git restore of exact UI files only. Validation must include bash -n for shell scripts, jq -n -f watch/spot-ui-risk.json.jq syntax validation, bash watch/spot-ui-readiness.sh | jq ., and render smoke tests. Proposal only; no code.  
role: coding  
worker: spot-worker-03  
model: qwen2.5-coder:7b  
gpu: GTX 1070 8GB  

---

**SUMMARY**
Propose a coding implementation for UI readiness and rendering based on the provided files and current Spot context. Ensure that the implementation targets specific UI scripts and adheres to the given rules.

**RISK_CLASS**
Low

**FILES_AFFECTED**
- watch/spot-ui-readiness.sh
- watch/spot-ui-render-html.sh
- watch/spot-ui-render-risk.sh
- watch/spot-ui-risk.json.jq
- watch/spot-ui-01.sh
- spot-core/spot-ui-01-dashboard-design.md

**VALIDATION_COMMANDS**
```bash
bash -n watch/spot-ui-readiness.sh
jq -n -f watch/spot-ui-risk.json.jq
bash watch/spot-ui-readiness.sh | jq .
```

**ROLLBACK**
```bash
git restore watch/spot-ui-readiness.sh watch/spot-ui-render-html.sh watch/spot-ui-render-risk.sh watch/spot-ui-risk.json.jq watch/spot-ui-01.sh spot-core/spot-ui-01-dashboard-design.md
```

**NEXT_SAFE_ACTION**
Deploy the proposed changes and perform smoke tests to ensure functionality.
