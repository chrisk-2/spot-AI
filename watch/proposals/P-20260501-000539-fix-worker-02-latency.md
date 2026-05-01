# Spot Proposal P-20260501-000539-fix-worker-02-latency

status: approved  
approved_utc: 20260501-002053
created_utc: 20260501-000539  
task: fix worker-02 latency  
role: coding  
worker: spot-worker-03  
model: qwen2.5-coder:7b  
gpu: GTX 1070 8GB  

---

**SUMMARY**
The current worker-02 has high p50 and average latency, which may affect performance. The issue is related to the utility lane being slow despite having dual physical GPUs but a single modeled ollama base_url.

**RISK_CLASS**
Medium

**FILES_AFFECTED**
- `/home/ogre/spot-stack/spot-core/config/cluster_config.json`

**VALIDATION_COMMANDS**
- `spot ask "show worker latency"`

**ROLLBACK**
- Rollback will be performed by restoring the previous version of `cluster_config.json` from a backup if it exists.

**NEXT_SAFE_ACTION**
- Adjust the base_url to utilize both GPUs or reconfigure the worker for better performance.
