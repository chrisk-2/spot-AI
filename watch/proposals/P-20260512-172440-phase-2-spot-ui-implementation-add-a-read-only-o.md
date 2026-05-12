# Spot Proposal P-20260512-172440-phase-2-spot-ui-implementation-add-a-read-only-o

status: approved  
approved_utc: 20260512-210302
created_utc: 20260512-172440  
task: Phase 2 Spot UI implementation: add a read-only Operator Command Panel to the Spot UI HTML dashboard. It must be proposal-only, no live writes, no service restarts, no routing changes, no network mutation. The panel should show safe operator commands for status, validation stamp, dashboard publish, self-heal audit, routing audit, and logs. It must preserve governance proposal_only_locked and mutation_performed=false execution_performed=false.  
role: heavy  
worker: spot-worker-04  
model: qwen3:32b  
gpu: Quadro P6000 24GB  

---

SUMMARY  
- Add read-only Operator Command Panel to Spot UI HTML dashboard showing safe commands for status, validation, publish, audit, and logs.  
- Preserve governance flags: proposal_only_locked, mutation_performed=false, execution_performed=false.  
- No live writes, service restarts, routing/network changes. Target files under /home/ogre/spot-stack/watch/spot-ui-*.  

RISK_CLASS  
- low: UI-only changes with no runtime or config mutations  

FILES_AFFECTED  
- /home/ogre/spot-stack/watch/spot-ui-render-html.sh  
- /home/ogre/spot-stack/watch/spot-ui-readiness.sh  
- /home/ogre/spot-stack/watch/spot-ui-risk.json.jq  

VALIDATION_COMMANDS  
- bash -n /home/ogre/spot-stack/watch/spot-ui-render-html.sh  
- jq -n -f /home/ogre/spot-stack/watch/spot-ui-risk.json.jq  
- bash /home/ogre/spot-stack/watch/spot-ui-readiness.sh | jq .  

ROLLBACK  
- git restore /home/ogre/spot-stack/watch/spot-ui-render-html.sh  
- git restore /home/ogre/spot-stack/watch/spot-ui-readiness.sh  
- git restore /home/ogre/spot-stack/watch/spot-ui-risk.json.jq  

NEXT_SAFE_ACTION  
- Validate shell script syntax and JSON templates  
- Confirm UI rendering smoke test passes without cluster_config.json changes
