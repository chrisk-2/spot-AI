# SPOT FLEET STATE

## Current Focus
Routing audit / observability / remediation

## Status
- Routing ownership: VERIFIED
- Audit classification: VERIFIED
- Audit persistence: VERIFIED
- Watch integration: VERIFIED
- Remediation loop: VERIFIED
- Live quarantine apply/release: VERIFIED
- System state: HEALTHY

## Known-Good Role Ownership
- general -> spot-worker-01
- coding  -> spot-worker-03
- heavy   -> spot-worker-04
- utility -> spot-worker-02

## Verified Behavior
- /stats/routing-audit works
- routing audit persists to:
  - /home/ogre/spot-stack/watch/state/routing-audit.jsonl
- fleet-watch.sh updates:
  - /home/ogre/spot-stack/watch/state/fleet-status.json
  - /home/ogre/spot-stack/watch/state/routing-audit-summary.json
- fleet-remediate.sh performs backup-first remediation
- POST /quarantine/<worker> works live
- DELETE /quarantine/<worker> now clears runtime state live without restart
- watch state, remediation state, and fleet ping remain aligned

## Important Fixes Completed
1. Fixed permissions on ~/spot-stack/watch so routing-audit.jsonl persists correctly
2. Fixed remediation path to back up first and use routing audit summary
3. Fixed live quarantine release bug in spot-core/spotcore/app.py so DELETE /quarantine/<worker> immediately clears:
   - PENALTY_BOX
   - remediation-state.json
   - fleet-status.json host quarantine state

## Files Modified
- ~/spot-stack/spot-core/spotcore/app.py
- ~/spot-stack/watch/fleet-watch.sh
- ~/spot-stack/watch/fleet-remediate.sh
- ~/spot-stack/watch/fleet-policy.json
- ~/spot-stack/watch/fix-unquarantine-runtime.sh

## Current State
- spot-worker-01 eligible=true quarantined=false
- routing audit persistence works
- remediation loop works
- release path bug is fixed

## Next Steps
1. Save/commit current healthy state
2. Build one-command fleet validation script that checks:
   - general/coding/heavy/utility routing
   - /stats/routing-audit
   - fleet-watch.sh healthy output
   - optional quarantine apply/release smoke test
3. Add explicit audit write failure logging in app.py
4. Optionally add guarded fail-open / safe release logic if all workers for a role become quarantined

## Caution
- Do not re-run chaos edits directly in app.py unless explicitly needed
