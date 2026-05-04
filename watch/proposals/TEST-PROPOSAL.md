# Spot Proposal TEST-PROPOSAL

status: approved
approved_utc: 20260503-041538
task: phase17 lifecycle test
risk_class: low

---

SUMMARY
- Validate supervised execution dry-run lifecycle.

RISK_CLASS
- low

FILES_AFFECTED
- /home/ogre/spot-stack/watch/spot-client.sh

VALIDATION_COMMANDS
- python3 -m json.tool /home/ogre/spot-stack/spot-core/config/cluster_config.json >/dev/null
- spot validate
- spot ask "show worker latency"
- spot ask "what is the current fleet status"
- spot ask "show current routing audit"

ROLLBACK
- Use the verified pre-change backup artifact generated immediately before any future mutation.

NEXT_SAFE_ACTION
- Execute non-mutating dry-run wrapper.
