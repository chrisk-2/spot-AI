# Spot Proposal P-20260501-133522-add-safe-utility-fallback-because-worker-02-late

status: rejected  
rejected_utc: 20260501-133608
created_utc: 20260501-133522  
task: add safe utility fallback because worker-02 latency causes intermittent validation 503  
role: coding  
worker: spot-worker-03  
model: qwen2.5-coder:7b  
gpu: GTX 1070 8GB  

---

**SUMMARY**
To mitigate the intermittent validation 503 errors caused by high latency on `worker-02`, a utility fallback will be added. This ensures that if primary workers are experiencing issues, the system can switch to using the utility worker for validations.

**RISK_CLASS**
Low to Medium

1. Introducing a utility fallback introduces an additional layer of redundancy but does not affect the primary functionality.
2. There is a slight risk of increased latency during peak times if all fallbacks are used simultaneously.

**FILES_AFFECTED**
- `/home/ogre/spot-stack/watch/spot-client.sh`
- `/home/ogre/spot-stack/config/cluster_config.json`

**VALIDATION_COMMANDS**
1. `python3 -m json.tool /home/ogre/spot-stack/spot-core/config/cluster_config.json >/dev/null` to verify configuration changes.
2. `spot ask "show current routing audit"` to confirm fallback worker is included in the routing.

**ROLLBACK**
1. If validation fails, restore `/home/ogre/spot-stack/watch/spot-client.sh` from a backup.
2. Revert the changes made to `/home/ogre/spot-stack/config/cluster_config.json`.

**NEXT_SAFE_ACTION**
1. Monitor the system's performance for 24 hours to ensure that the utility fallback is effective and does not introduce additional latency issues.
2. Schedule another audit to validate the reliability of the fallback mechanism.
