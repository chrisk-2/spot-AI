# Spot Proposal P-20260502-034657-prepare-a-low-risk-plan-to-reduce-spot-utility-r

status: pending_review  
created_utc: 20260502-034657  
task: Prepare a low-risk plan to reduce Spot utility-role latency without changing routing ownership. Diagnose and adjust only prompt/context behavior for utility requests so simple utility prompts do not inject excessive durable memory or produce verbose responses. Include validation using spot ask --role utility 'reply with ok', raw worker-02 Ollama comparison, /stats/latency review, routing audit validation, and rollback. Do not mutate network, worker services, or cluster ownership.  
role: coding  
worker: spot-worker-03  
model: qwen2.5-coder:7b  
gpu: GTX 1070 8GB  

---

**SUMMARY**
1. Adjust prompt/context behavior for utility requests on worker-02 to reduce latency.
2. Validate changes using `spot ask --role utility 'reply with ok'` and `/stats/latency`.
3. Review routing audit to ensure no changes to role ownership.

**RISK_CLASS**
Low

**FILES_AFFECTED**
1. /home/ogre/spot-stack/spot-core/config/cluster_config.json
2. /home/ogre/spot-stack/watch/spot-client.sh

**VALIDATION_COMMANDS**
1. `spot ask --role utility 'reply with ok'`
2. `python3 -m json.tool /home/ogre/spot-stack/spot-core/config/cluster_config.json >/dev/null`
3. `/stats/latency`
4. `spot ask "show current routing audit"`

**ROLLBACK**
1. Revert changes to cluster_config.json using backup from 20260501-134024.
2. No action needed for spot-client.sh as it is a shell script.

**NEXT_SAFE_ACTION**
1. Execute the prepared non-mutating execution handoff from HANDOFF-APPLY-P-20260501-133615-revise-routing-so-utility-role-remains-primary-o.
2. Monitor worker-02 latency post-execution using `/stats/latency`.
