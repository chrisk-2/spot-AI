# Spot Apply Plan APPLY-P-20260502-035124-prepare-a-low-risk-diagnostic-only-plan-to-reduc

linked_proposal: P-20260502-035124-prepare-a-low-risk-diagnostic-only-plan-to-reduc
approved_utc: 20260502-035215
generated_utc: 20260502-035215
task: Prepare a low-risk diagnostic-only plan to reduce Spot utility-role latency by inspecting prompt assembly and durable-memory injection only. Do not change cluster_config.json, routing ownership, worker services, network, firewall, DNS, or model placement. Focus on locating where spot ask --role utility injects Durable Memory Context and why phi3.5 answers verbosely to 'reply with ok'. Include candidate files to inspect, exact read-only diagnostics, validation using spot ask --role utility 'reply with ok', raw worker-02 Ollama comparison, /stats/latency review, routing audit validation, backup requirements before any future mutation, and rollback plan.
risk_class: low
apply_status: review_approved
review_approved_utc: 20260502-035440
mutation_allowed: false
backup_required: true
backup_bound: false
backup_artifact: pending

---

TARGET_FILES
- /home/ogre/spot-stack/watch/spot-client.sh
- /home/ogre/spot-stack/spot-core/spotcore/app.py
- /home/ogre/spot-stack/spot-core/config/cluster_config.json

PRECHANGE_BACKUP_REQUIREMENTS
- Before any future mutation, Spot Core must create and verify a pre-change backup on Unimatrix.
- Required backup root: /mnt/collective/backups/<target>/<service>/<timestamp>/
- Backup path must be recorded in the action log before execution begins.
- If backup creation or verification fails, execution remains blocked.

PRECHECK_VALIDATION
- python3 -m json.tool /home/ogre/spot-stack/spot-core/config/cluster_config.json >/dev/null
- spot validate
- spot ask "show worker latency"
- spot ask "what is the current fleet status"
- spot ask --role utility "reply with ok"
- curl -fsS http://127.0.0.1:8787/stats/latency | jq .
- curl -fsS 'http://127.0.0.1:8787/stats/recent-decisions?limit=10' | jq .
- spot ask "show current routing audit"

PLANNED_MUTATIONS
- No planned mutations.
- Inspect prompt assembly and durable-memory injection paths only.
- Determine why utility-role requests inject Durable Memory Context for minimal prompts.
- Determine whether spot-client.sh or Spot Core app.py assembles role-specific prompt context.
- Determine whether utility prompts can be diagnosed without changing routing ownership or worker services.
- This apply plan does not execute mutations.
- Future execution, if any, must require a separate approved proposal and backup-bound apply plan.

POST_APPLY_VALIDATION
- spot validate
- spot ask "show worker latency"
- spot ask "what is the current fleet status"
- spot ask --role utility "reply with ok"
- curl -fsS http://127.0.0.1:8787/stats/latency | jq .
- spot ask "show current routing audit"

ROLLBACK_PLAN
- No rollback required for this diagnostic-only apply plan because no mutation is authorized.
- If a future mutation proposal is created, rollback must use a verified pre-change backup artifact.

HUMAN_REVIEW_GATE
- Confirm proposal is still approved and matches current runtime state.
- Confirm target files still exist and match expected live paths.
- Confirm risk class is correct under Spot Autonomy Policy.
- Confirm backup, validation, and rollback instructions are sufficient before any mutation.

NOTES
- Generated artifact is non-mutating.
- Memory and proposal history inform context but do not authorize execution.
- No high-risk network/firewall/DNS/DHCP/VLAN/routing mutation is authorized by this artifact.
