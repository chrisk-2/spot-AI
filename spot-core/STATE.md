Continuing Spot fleet work.

Repo:
https://github.com/chrisk-2/spot-AI

Current area:
routing audit / observability / remediation

What is now working:
- strict role ownership routing is verified
- audit classification works:
  - primary
  - fallback
  - violation
- /stats/routing-audit works
- routing audit now persists to disk at:
  /home/ogre/spot-stack/watch/state/routing-audit.jsonl
- fleet-watch.sh ingests routing audit and writes it into:
  /home/ogre/spot-stack/watch/state/fleet-status.json
  /home/ogre/spot-stack/watch/state/routing-audit-summary.json
- fleet-remediate.sh works with backup-first behavior
- quarantine POST works live
- quarantine DELETE now clears runtime state live without requiring restart
- watch state + remediation state + fleet ping now stay aligned on quarantine/unquarantine

Important fixes completed:
1. Fixed permissions on ~/spot-stack/watch so routing-audit.jsonl persists correctly
2. Fixed remediation path to back up first and use routing audit summary
3. Fixed live quarantine release bug in spot-core/spotcore/app.py so DELETE /quarantine/<worker> immediately clears:
   - PENALTY_BOX
   - remediation-state.json
   - fleet-status.json host quarantine state

Known-good validation results:
- general -> spot-worker-01
- coding -> spot-worker-03
- heavy -> spot-worker-04
- utility -> spot-worker-02
- routing audit shows primaries correctly
- watcher shows routing_fallbacks=0 and routing_violations=0 in healthy state
- manual quarantine/unquarantine test on spot-worker-01 succeeded without restart

Files changed in this phase:
- ~/spot-stack/spot-core/spotcore/app.py
- ~/spot-stack/watch/fleet-watch.sh
- ~/spot-stack/watch/fleet-remediate.sh
- ~/spot-stack/watch/fleet-policy.json
- created helper script:
  ~/spot-stack/watch/fix-unquarantine-runtime.sh

Current state:
- system healthy
- spot-worker-01 eligible=true quarantined=false
- routing audit persistence works
- remediation loop works
- release path bug is fixed

Cleanup optionally still worth doing:
- remove stale test-era entry for spot-worker-01 from:
  ~/spot-stack/watch/state/remediation-state.json
  not required for function, only cleanup

Recommended next steps:
1. Commit/save current state
2. Build a dedicated one-command validation script that runs:
   - general/coding/heavy/utility routing checks
   - routing audit check
   - watcher check
   - optional quarantine apply/release smoke test
3. Add explicit audit write failure logging in app.py so file persistence issues never fail silently again
4. Optionally add a safe fail-open or guarded release policy if all workers for a role become quarantined
5. After validation tooling, return to routing policy hardening / full-chain regression tests

Caution:
- do not re-run chaos edits directly in app.py for fake violations unless explicitly needed
- use scripted tests going forward
