# Spot Patch Artifact PATCH-P-20260501-000539-fix-worker-02-latency

linked_proposal: P-20260501-000539-fix-worker-02-latency
approved_utc: 20260501-002053
task: fix worker-02 latency  
apply_status: pending_manual_apply

---

TARGET_FILES
- /home/ogre/spot-stack/spot-core/config/cluster_config.json

INTENDED_MODIFICATION_SUMMARY
- derive exact cluster_config.json adjustments from approved proposal
- do not apply automatically
- require human review before file mutation

VALIDATION_CHECKLIST
- python3 -m json.tool /home/ogre/spot-stack/spot-core/config/cluster_config.json >/dev/null
- spot validate
- spot ask "show worker latency"
- spot ask "what is the current fleet status"
- spot ask "show current routing audit"

MANUAL_REVIEW_REQUIRED
- confirm approved proposal still matches current fleet condition
- confirm worker-02 latency issue still present
- confirm no conflicting hardware changes pending
