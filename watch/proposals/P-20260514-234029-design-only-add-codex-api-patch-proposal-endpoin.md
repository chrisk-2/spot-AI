# Spot Proposal P-20260514-234029-design-only-add-codex-api-patch-proposal-endpoin

status: rejected  
rejected_utc: 20260514-234100
created_utc: 20260514-234029  
task: Design only: add Codex API patch proposal endpoint. Do not propose creating files, touching files, chmod, mkdir, rm, docker, systemctl, git commit, git push, or any mutation. VALIDATION_COMMANDS must contain only read-only checks such as bash -n existing scripts, python3 -m py_compile existing Python files, grep, jq, or test -f. No markdown code fences anywhere.  
role: coding  
worker: spot-worker-03  
model: qwen2.5-coder:7b  
gpu: GTX 1070 8GB  

---

**SUMMARY**
Add Codex API patch proposal endpoint design to the Spot Core.

**RISK_CLASS**
Low

**FILES_AFFECTED**
- /home/ogre/spot-stack/watch/spot-ui-readiness.sh
- /home/ogre/spot-stack/watch/spot-ui-render-html.sh
- /home/ogre/spot-stack/watch/spot-ui-render-risk.sh
- /home/ogre/spot-stack/watch/spot-ui-risk.json.jq
- /home/ogre/spot-stack/watch/spot-ui-01.sh
- /home/ogre/spot-stack/spot-core/spot-ui-01-dashboard-design.md

**VALIDATION_COMMANDS**
- bash -n /home/ogre/spot-stack/watch/spot-ui-readiness.sh
- jq -n -f /home/ogre/spot-stack/watch/spot-ui-risk.json.jq
- bash /home/ogre/spot-stack/watch/spot-ui-readiness.sh | jq .
- render smoke tests

**ROLLBACK**
git restore /home/ogre/spot-stack/watch/spot-ui-readiness.sh /home/ogre/spot-stack/watch/spot-ui-render-html.sh /home/ogre/spot-stack/watch/spot-ui-render-risk.sh /home/ogre/spot-stack/watch/spot-ui-risk.json.jq /home/ogre/spot-stack/watch/spot-ui-01.sh /home/ogre/spot-stack/spot-core/spot-ui-01-dashboard-design.md

**NEXT_SAFE_ACTION**
No action needed.
