# Spot Proposal P-20260511-145957-design-the-operating-operator-portion-for-spot-u

status: pending_review  
created_utc: 20260511-145957  
task: Design the operating/operator portion for spot-ui-01 using only discovered existing files. Architecture/spec only. Known files: spot-core/spot-ui-01-dashboard-design.md, watch/spot-ui-01.sh, watch/spot-ui-readiness.sh, watch/spot-ui-render-html.sh, watch/spot-ui-render-risk.sh, watch/spot-ui-render-timeline.sh, watch/spot-ui-render-acks.sh, watch/spot-ui-history.sh, watch/spot-ui-ack.sh, watch/spot-ui-incident-ledger.sh, watch/spot-ui-publish.sh, watch/spot-ui-remediation-map.sh, watch/spot-ui-risk.json.jq. Use watch/spot-ui-readiness.sh as the primary read-only data source. Do not invent paths. Do not modify cluster_config.json. Do not use backup .bak paths. Define UI pages/sections, state model, read-only data flow, safety boundaries, governance/proposal/preflight views, validation commands, rollback for UI-only files, and phased implementation. Mark unknowns as NEEDS_DISCOVERY.  
role: heavy  
worker: spot-worker-04  
model: qwen3:32b  
gpu: Quadro P6000 24GB  

---

**SUMMARY**  
- Define UI pages/sections: dashboard, readiness, risk, timeline, incident ledger, remediation map, history.  
- Use `spot-ui-readiness.sh` as primary read-only data source for state transitions.  
- UI state model mirrors `readiness: not_ready` telemetry and routing audit violations.  
- Phased implementation: start with dashboard, add sections incrementally.  

**RISK_CLASS**  
- Low: UI-only changes, no config or service modifications.  
- Medium: Uncertainty in `spot-ui-readiness.sh` output structure (NEEDS_DISCOVERY).  
- Low: Safety boundaries enforced by read-only data flow and no cluster_config.json edits.  

**FILES_AFFECTED**  
- `/home/ogre/spot-stack/watch/spot-ui-*.sh`  
- `/home/ogre/spot-stack/watch/spot-ui-risk.json.jq`  
- `/home/ogre/spot-stack/spot-core/spot-ui-01-dashboard-design.md`  

**VALIDATION_COMMANDS**  
- `spot ask "show current routing audit"`  
- `spot validate`  
- `bash /home/ogre/spot-stack/watch/spot-ui-readiness.sh`  
- `jq -V` (validate jq syntax for `spot-ui-risk.json.jq`)  

**ROLLBACK**  
- Revert `spot-ui-*.sh` to prior git commit hash.  
- Restore `spot-ui-risk.json.jq` from Spot Core backup artifact.  
- No rollback needed for `.md` design files.  

**NEXT_SAFE_ACTION**  
- Execute `spot-ui-readiness.sh` to map output fields to UI state model.  
- Validate `jq` filters in `spot-ui-risk.json.jq` against sample telemetry.  
- Draft HTML rendering logic in `spot-ui-render-*.sh` scripts.  
- Confirm `spot-ui-01-dashboard-design.md` aligns with governance/proposal views.
