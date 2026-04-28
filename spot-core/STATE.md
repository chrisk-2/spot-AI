# SPOT FLEET STATE

## Current confirmed runtime state

Spot rescue/hardening phase is complete enough to treat Milestone A — Spot Core Trusted as locked.

Confirmed working:

- spot-core control plane healthy
- MCP wrapper path healthy
- local and remote file mutation paths proven
- quarantine/release proven
- routing audit and latency stats working
- `spot` operator commands working
- `spot validate` and `spot validate-smoke` passing
- worker backup automation working on all four workers
- validator secret regression checks working
- worker home cleanup/archive pass completed
- worker-02 full legacy service/env/opt cleanup archived
- worker-02 now finalized as utility/watcher reserve node
- worker fleet runtime now effectively Ollama-only on port 11434
- worker-02 Quadro M4000 8GB pinned as utility Ollama lane
- worker-02 GTX1060 6GB left free for future monitoring/camera workloads
- utility role warm-model policy enabled
- latest validation passed clean
- fleet validator hardened and smoke cycle explicitly asserting quarantine/release state
- validator backup freshness checks passing on all four workers
- Spot UI cockpit renderer/publisher path verified honest on live host
- Spot Incident Engine IE-1 persistent promotion validated
- Spot Incident Engine IE-2 acknowledgement lifecycle validated
- Spot Incident Engine IE-3 remediation suggestions validated
- cockpit displays incident remediation guidance and capped history cleanly
- stale remediation violation memory root cause fixed
- routing audit persistence now explicitly hardened against write failure with logged exception path
- fleet risk returned to NORMAL (0)
- open incident queue cleared
- 2026-04-28 bare-metal spot-core restore completed after failed system SSD
- replacement Kingston SKC600 SATA SSD stress-tested and accepted for service
- fresh Ubuntu install restored from SPOTBACKUP rescue payload
- spot-core Docker container restored and healthy on port 8787
- Spot UI publisher restored and publishing non-empty dashboard artifacts under /var/www/html/spot
- worker SSH trust restored from existing worker key material
- ChatGPT/Spot MCP connector restored through existing user-level MCP stack on 127.0.0.1:8001
- duplicate restored system-level spot-mcp/cloudflared stack disabled to prevent /spot route conflicts

Latest checkpoint commit:

4b414b0 checkpoint: 2026-04-28-16:04:28

## 2026-04-28 Spot Core bare-metal recovery checkpoint

Incident:

- spot-core original system SSD failed
- replacement SSD installed
- Ubuntu reinstalled, static IP restored, updates completed
- backup restored from external SPOTBACKUP volume

Storage acceptance:

- replacement drive identified as KINGSTON SKC600 SATA SSD
- SMART showed no reallocated sectors, no uncorrectable errors, no UDMA CRC errors, and no ATA error log entries after testing
- drive is used/worn rather than pristine, but passed acceptance testing
- sequential fio write test completed at approximately 359 MiB/s with zero fio errors
- mixed random fio test completed at approximately 35k read IOPS and 35k write IOPS with zero fio errors
- post-test SMART remained clean
- accepted for service as interim control-plane disk; future fresh SSD/NVMe replacement still recommended

Restore results:

- root LV expanded and mounted cleanly with roughly 232G available
- SPOTBACKUP mounted read-only and spotcore_rescue payload restored surgically
- /home/ogre, spot-stack, spot-mcp, service files, docker/caddy/cron/systemd configs, and operational assets restored
- Docker package baseline rebuilt
- spot-core container started successfully from /home/ogre/spot-stack/docker-compose.yml
- /health endpoint confirmed healthy
- MCP wrapper fixed to use /home/ogre/spot-mcp/spot_mcp_wrapper.py
- systemd spot services restored and confirmed active

Post-reboot verified services:

- spot-bridge-api.service running
- spot-mcp.service running where applicable before duplicate cleanup
- spot-ui-publish.service running
- spot-monitor-alert-state.timer active
- spot-monitor-snapshot.timer active
- docker spot-core container running on 8787
- Spot UI output files regenerated and non-empty: index.html, spot.json, history.json, incidents.json, acks.json, meta.json

MCP/tunnel correction:

- legacy working user-level MCP stack is canonical:
  - /home/ogre/.config/systemd/user/spot-mcp.service
  - /home/ogre/.config/systemd/user/mcp-tunnel.service
  - uvicorn app:app on 127.0.0.1:8001
- restored system-level duplicate stack was disabled:
  - /etc/systemd/system/spot-mcp.service
  - /etc/systemd/system/cloudflared.service
- reason: duplicate system-level stack listened on 8000 and returned 404 for /spot, causing intermittent connector failures
- after disabling duplicate stack, connector routing calls succeeded again

Confirmed current routing ownership:

- general: spot-worker-01
- utility: spot-worker-02
- coding: spot-worker-03
- heavy: spot-worker-04

Known remaining external issue:

- Homer/tower at 192.168.30.5:7575 is still offline
- curl to / and /b timed out
- ping to 192.168.30.5 showed 100 percent packet loss
- this is outside restored spot-core stack and requires physical/network inspection of tower

Current recommended next checks:

1. run `spot validate` and `spot validate-smoke` after final recovery cleanup
2. run `spot_save` once this STATE.md recovery section is committed
3. inspect worker backup status because recovery checkpoint showed worker backup status as MISSING even though previous baseline had backup freshness passing
4. resolve Homer/tower offline separately

## Strategic alignment

Spot is now treated as:

Starfleet OS subsystem — fleet control / worker dispatch / validation / autonomy layer

Spot is not the final product.

Spot must be finished enough to help build everything that follows.

Canonical forward build doctrine now lives in:

- /home/ogre/spot-stack/ROADMAP.md

Current active roadmap phase:

PHASE 1 — SPOT OPERATOR READY / ENGINEERING WORKFLOW POLISH

## Integration planning added

Dedicated integration handoff docs now exist:

- /home/ogre/spot-stack/HANDOFF-CODEX-INTEGRATION.md
- /home/ogre/spot-stack/HANDOFF-SPOT-INTEGRATION.md

Main HANDOFF now references these docs for architectural/phased integration work.

## Verified control-plane mutation fix

Spot Core existing-file local write path has been verified end-to-end through the admin/MCP route.

Verified behavior:

- pre-change backup created under /mnt/collective/backups
- backup metadata written and marked verified
- existing HANDOFF.md write completed through Spot Core
- post-write verification passed
- structured success response returned

Root cause of prior HANDOFF.md write failure:

- docker-compose.yml mounted HANDOFF.md into spot-core as read-only
- mount was changed from :ro to :rw for HANDOFF.md only
- ROADMAP.md remains read-only

Spot Core enforcement hardening applied:

- execute_with_enforcement catches execute-stage exceptions and returns structured 503 details after backup instead of raw 500
- rollback status normalization respects rollback functions returning {"ok": true}
- read-only bind mount failures now return backup-preserved structured denial instead of silent corruption

This confirms the Codex/Spot controlled apply model is viable:

Codex/assistant proposes; Spot Core backs up, writes, verifies, and logs.

## Spot validator hardening (2026-04-25)

Live host file verified and edited on:

- /home/ogre/spot-stack/watch/fleet-validate.sh

Confirmed not edited on `/mnt/collective` share namespace.

Validator changes completed:

- duplicate/noisy pass chatter removed
- role route validation preserved
- routing audit append validation preserved
- `/stats/routing-audit` primary mapping validation preserved
- admin validate/read-file checks preserved
- smoke quarantine cycle explicitly asserts quarantined=true eligible=false and release restoration without restart
- backup freshness verification added for all four workers
- strict-mode shell parser and nounset bugs corrected after live validation

Host validation rerun results:

- `bash -n /home/ogre/spot-stack/watch/fleet-validate.sh` PASS
- `spot validate` PASS
- `spot validate-smoke` PASS

## Spot UI / Cockpit status

Spot UI Phase 1 through Phase 7 foundation is live on the real spot-core host filesystem.

Confirmed host files under:

- /home/ogre/spot-stack/watch/

Published browser artifacts under:

- /var/www/html/spot/index.html
- /var/www/html/spot/spot.json
- /var/www/html/spot/history.json
- /var/www/html/spot/incidents.json
- /var/www/html/spot/acks.json
- /var/www/html/spot/meta.json

Current LAN cockpit URL:

- http://192.168.60.30/spot/

Confirmed working:

- all Spot UI shell scripts pass `bash -n`
- `spot-ui-publish.service` confirmed active as real system service on host
- meta.json and index.html advance on publish cycle
- browser dashboard renders successfully from live publish path
- Fleet Risk card renders successfully
- Incident Timeline renders successfully
- Operator Acknowledgements card renders successfully
- acknowledgement feed `acks.json` wired into main HTML renderer
- both risk/html renderers rebuilt to use temp files + jq `--slurpfile` to eliminate kernel argv `Argument list too long` failures under large history payloads
- Incident Timeline renders open incidents, recent history, and remediation suggestions
- dashboard trend and latency history output capped to last 20 snapshots
- generated dashboard includes live telemetry, incident banner, fleet risk score, incident timeline, acknowledgements, anomalies, remediation/autonomy state, workers, trends, and worker latency history

## Spot Incident Engine status

IE-1 persistent promotion completed and committed:

- commit: bef3ef1 feat: add persistent spot incident engine
- incident engine state file: /home/ogre/spot-stack/watch/state/incident-engine-state.json
- incident ledger file: /home/ogre/spot-stack/watch/state/spot-ui-incidents.jsonl
- repeated factor promotion validated
- deterministic incident IDs validated
- open-signature dedupe validated

IE-2 acknowledgement lifecycle completed and committed:

- commit: b46e946 feat: wire acknowledgements into incident lifecycle
- incident ack_state transitions validated: open -> acknowledged -> resolved
- resolved incident sets remediation_state=closed
- resolved incident clears open signature from incident-engine-state.json so recurrence can reopen cleanly

IE-3 remediation suggestion queue completed and committed:

- commit: 277fceb feat: add incident remediation suggestions
- remediation mapper: /home/ogre/spot-stack/watch/spot-ui-remediation-map.sh
- new incidents receive advisory remediation object at creation
- remediation output includes risk_class, backup_required, autonomy, state, and policy_note

Cockpit rendering for IE-3 completed and committed:

- commit: 1c500b5 feat: render incident guidance and cap dashboard history
- Incident Timeline shows open incidents and suggested actions
- live dashboard confirmed showing ledger_cleanup, backup_required=true, autonomy=advisory_only
- dashboard trend/latency sections capped to last 20 snapshots

Stale remediation memory fix completed and committed:

- commit: b80bf42 fix: decay stale remediation violation memory
- root cause: fleet-remediate.sh set violation_count_window when fresh violations existed but did not zero old counters after the current audit window became clean
- affected stale values were spot-worker-01 violation_count_window=3 and spot-worker-03 violation_count_window=2
- current routing audit window showed zero active violations
- fleet-remediate.sh now decays stale per-worker violation_count_window to 0 when no fresh violation exists in the current audit window
- last_route_class normalizes from violation to primary for decayed stale entries
- INC-3 resolved with note: stale remediation violation memory cleared by fleet-remediate decay fix
- incident-engine open_signatures cleared
- open_incidents now empty
- dashboard shows Fleet Risk NORMAL (0), No risk factors active, No anomalies detected

## Current worker role map / hardware snapshot

Locked roles:

- spot-worker-01: general
- spot-worker-02: utility
- spot-worker-03: coding
- spot-worker-04: heavy

## Policy posture

Spot Autonomy Policy remains locked:

- primary rule: no backup, no change
- mutating autonomous actions must follow Detect -> Analyze -> Classify -> Backup -> Plan -> Verify -> Execute -> Test/Rollback
- Spot may create/read backup artifacts but must not delete/overwrite/alter existing backups
- high-risk network/firewall/VLAN/DNS/DHCP changes remain gated

## Immediate next objective

1. run `spot validate` and `spot validate-smoke` after the 2026-04-28 recovery
2. investigate worker backup status reported as MISSING during recovery checkpoint
3. commit this STATE.md recovery update with `spot_save`
4. resolve Homer/tower offline at 192.168.30.5 separately
5. resume Spot Operator Ready / workflow polish after recovery closure
