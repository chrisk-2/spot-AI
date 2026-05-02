# Spot Proposal P-20260502-035124-prepare-a-low-risk-diagnostic-only-plan-to-reduc

status: approved  
approved_utc: 20260502-035215
created_utc: 20260502-035124  
task: Prepare a low-risk diagnostic-only plan to reduce Spot utility-role latency by inspecting prompt assembly and durable-memory injection only. Do not change cluster_config.json, routing ownership, worker services, network, firewall, DNS, or model placement. Focus on locating where spot ask --role utility injects Durable Memory Context and why phi3.5 answers verbosely to 'reply with ok'. Include candidate files to inspect, exact read-only diagnostics, validation using spot ask --role utility 'reply with ok', raw worker-02 Ollama comparison, /stats/latency review, routing audit validation, backup requirements before any future mutation, and rollback plan.  
role: coding  
worker: spot-worker-03  
model: qwen2.5-coder:7b  
gpu: GTX 1070 8GB  

---

**SUMMARY**
- Prepare a diagnostic-only plan to reduce Spot utility-role latency.
- Inspect prompt assembly, durable-memory injection, and raw worker-02 Ollama comparison.
- Include candidate files for inspection and exact read-only diagnostics.
- Validate using `spot ask --role utility 'reply with ok'`.
- Review /stats/latency and routing audit validation.
- Document backup requirements before any future mutation.
- Provide a rollback plan.

**RISK_CLASS**
- Low risk, diagnostic-only, no changes to cluster configuration or worker services.

**FILES_AFFECTED**
- None

**VALIDATION_COMMANDS**
- spot ask "show current routing audit"
- spot ask "what is the current fleet status"
- python3 -m json.tool /home/ogre/spot-stack/spot-core/config/cluster_config.json >/dev/null
- ssh worker-02 cat /path/to/raw/ollama/output.txt

**ROLLBACK**
- No changes made.

**NEXT_SAFE_ACTION**
1. Inspect prompt assembly and durable-memory injection.
2. Compare raw worker-02 Ollama output with other instances.
3. Review `/stats/latency` to identify specific latency issues.
4. Validate routing audit using `spot ask "show current routing audit"`.
5. Document backup requirements before any future mutation.
6. Prepare rollback plan if necessary.

**DURABLE_MEMORY_CONTEXT**
- 20260501-214450 [session] execution handoff prepared from reviewed apply plan APPLY-P-20260501-133615-revise-routing-so-utility-role-remains-primary-o
