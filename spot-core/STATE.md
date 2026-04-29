# SPOT FLEET STATE

## Current confirmed runtime state

Spot rescue/hardening and 2026-04-28 bare-metal recovery closure are complete enough to treat Milestone A — Spot Core Trusted as locked.

Confirmed working:

- spot-core control plane healthy
- MCP wrapper path healthy
- local and remote file mutation paths proven
- quarantine/release proven
- routing audit and latency stats working
- `spot` operator commands working
- `spot validate` and `spot validate-smoke` passing after 2026-04-28 restore closure
- worker backup automation restored and working on all four workers
- worker-local backup service/timer deployed on all four workers
- worker backup metadata visible to `spot_save` for all four workers
- scoped sudo maintenance drop-in installed and validated on all four workers for approved maintenance commands
- `/mnt/collective` mounted and usable by all four workers for backup writes
- spot-core container recreated after mount correction and healthy on port 8787
- spot-core host/container backup view restored enough for `spot_save` to see worker metadata
- validator secret regression checks working
- worker home cleanup/archive pass completed
- worker-02 full legacy service/env/opt cleanup archived
- worker-02 now finalized as utility/watcher reserve node
- worker fleet runtime now effectively Ollama-only on port 11434
- worker-02 Quadro M4000 8GB pinned as utility Ollama lane
- worker-02 GTX1060 6GB left free for future monitoring/camera workloads
- utility role warm-model policy enabled
- latest routing audit window clean: 200 primary routes, 0 fallbacks, 0 violations, 0 manual overrides
- fleet validator hardened and smoke cycle explicitly asserting quarantine/release state
- validator backup freshness checks passing on all four workers from prior baseline and backup gate now restored after recovery
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
- user-level Cloudflare MCP tunnel corrected from stale localhost:8000 origin to canonical localhost:8001
- ChatGPT-to-MCP health path restored after tunnel correction
- `admin_operator_command` added to Spot MCP wrapper and confirmed in live FastMCP tool manager
- `admin_operator_command` confirmed visible over local streamable HTTP endpoint at http://127.0.0.1:8001/spot/
- Operator Readiness v2 completed: readiness feed generated, published, rendered, advertised to humans in cockpit footer, and advertised to machines in meta.json
- `operator-readiness.json` now includes Spot Core health, MCP local health, routing integrity, backup freshness, git dirty state, and validation freshness
- `watch/spot-validation-stamp.sh` added and validated; it records `spot validate` result, exit code, duration, log tail, and freshness metadata
- cockpit Control Surface card now displays validation status and validation age
- Self-Heal v1 audit mode added, committed, and validated
- Self-Heal v1.1 plan state and per-action cooldown scaffolding added, committed, and validated
- Self-Heal dry-run preview added, committed, and validated
- Self-Heal action ledger scaffolding added and ledger policy path fixed
- Self-Heal noop, apply_start, apply_finish, and apply_failure ledger events now preserve full JSON payloads through file-backed writes
- Self-Heal `republish_dashboard` apply now runs post-condition verification and only reports OK when dashboard metadata freshness verifies after execution
- Self-Heal `restart_mcp` apply is now allowlisted, single-attempt, cooldown-controlled, ledgered, and verified against local MCP `/health`
- Self-Heal live MCP restart recovery test passed: service stopped, self-heal restarted `spot-mcp.service`, `/health` returned healthy, and systemd reported active
- Self-Heal failure path emits explicit `apply_failure` ledger entries when command execution or post-condition verification fails
- Self-Heal deterministic test hook `SELF_HEAL_FORCE_VERIFY_FAIL=1` validated the failure ledger without service disruption
- Self-Heal `refresh_validation_stamp` verifier is implemented but policy-gated and not apply-allowlisted
- Self-Heal policy now gates only `refresh_validation_stamp` outside the apply allowlist
- `watch/spot-self-heal.sh apply` currently reports policy `level_1_assisted_allowlisted`, `apply_enabled=true`, allowlist `["republish_dashboard", "restart_mcp"]`, and verified OK/NOOP/FAIL paths work as expected
- latest `spot validate` after self-heal MCP restart work passed: 19 pass / 0 fail

Latest checkpoint commits:

- 0a677e1 fix restore validation secret regression
- 4f51f4b checkpoint: 2026-04-28-17:39:05
- 37e6fdc add self heal audit mode
- 1782abb add self heal plan state cooldowns
- fbeeb5c add self heal dry run preview
- 6bf2c2b add self heal action ledger scaffolding
- 648cc49 fix self heal ledger policy path
- 062b996 fix self heal noop ledger payload
- 7377c5b checkpoint self heal verification hardening
- 6893539 gate self heal mcp restart verifier
- edab45c harden self heal apply failure ledger
- 98c3d3e update state for self heal failure ledger
- bf10a93 gate self heal validation refresh
- b61363a allow self heal mcp restart
- pending/local: update state for self heal mcp restart

## 2026-04-29 Self-Heal checkpoint

Current self-heal file:

- /home/ogre/spot-stack/watch/spot-self-heal.sh

Modes:

- `watch/spot-self-heal.sh audit`
- `watch/spot-self-heal.sh plan`
- `watch/spot-self-heal.sh dry-run`
- `watch/spot-self-heal.sh apply`

Current apply behavior:

- apply is level 1 assisted/allowlisted only
- allowlisted actions are `republish_dashboard` and `restart_mcp`
- `republish_dashboard` command is `SPOT_UI_ONCE=1 bash watch/spot-ui-publish.sh --once`
- `restart_mcp` command is `systemctl --user restart spot-mcp.service`
- `restart_mcp` is single-attempt only, then verify-or-escalate; no restart loop
- `restart_mcp` verifier checks `http://127.0.0.1:8001/health`
- `refresh_validation_stamp` has a verifier and policy metadata but remains `safe_apply=false`
- `refresh_validation_stamp` is listed under `policy.gated_not_allowlisted`
- routing rewrites remain forbidden
- backup-gate failures remain escalation only
- repo dirty remains warning only and safe_apply=false
- apply_noop ledger entries preserve `{ok, actions, would_apply, blocked_or_skipped}` payloads
- apply_start ledger entries preserve the selected action payload
- apply_finish ledger entries preserve execution metadata, command log, and verification payload
- apply_failure ledger entries preserve action_id, FAIL status, policy_note, and full finish payload
- republish_dashboard verification checks `/var/www/html/spot/meta.json` `published_at` freshness after execution
- refresh_validation_stamp verification checks operator-validation.json status PASS, exit_code 0, command `spot validate`, and freshness <= `VALIDATION_MAX_AGE_SECONDS`
- apply result is FAIL if command exit code is nonzero or post-condition verification fails
- `SELF_HEAL_FORCE_VERIFY_FAIL=1` can force verifier failure for safe self-heal failure-path validation

Runtime state/log paths:

- self-heal state: /home/ogre/spot-stack/watch/state/self-heal-state.json
- action ledger: /mnt/collective/logs/spot/self-heal-actions.jsonl
- validation stamp: /home/ogre/spot-stack/watch/state/operator-validation.json

Validation performed:

- `bash -n watch/spot-self-heal.sh` passed after ledger and verification changes
- `watch/spot-self-heal.sh apply` NOOP path produced populated apply_noop payload
- forced stale dashboard metadata test triggered `republish_dashboard`
- apply_start ledger payload was populated with selected action details
- apply_finish ledger payload was populated with exit_code, command log, and verifier result
- verifier returned `verify_ok=true` and `age_seconds=1` after dashboard republish during normal success validation
- apply_result returned `status=OK` only after verification succeeded
- forced verifier-failure test with `SELF_HEAL_COOLDOWN_SECONDS=0 SELF_HEAL_FORCE_VERIFY_FAIL=1` produced populated apply_failure payload
- failure validation returned apply_result `status=FAIL` with full finish payload embedded in failure ledger
- `watch/spot-self-heal.sh audit` showed `refresh_validation_stamp` verifier implemented and not apply-allowlisted
- `watch/spot-self-heal.sh audit` showed policy gated_not_allowlisted contains `refresh_validation_stamp`
- `watch/spot-self-heal.sh audit` showed `restart_mcp` apply_allowlisted=true and max_attempts=1
- live MCP restart test stopped `spot-mcp.service`, ran self-heal apply, logged apply_start/apply_finish for `restart_mcp`, verified MCP health, and returned apply_result `status=OK`
- direct post-test checks returned `{"status":"healthy"}` from MCP health and `active` from systemd
- `spot validate` passed after self-heal MCP restart work with 19 pass / 0 fail

Known issue / next cleanup:

- Commit and checkpoint this STATE update if local git still shows changes.
- Keep `refresh_validation_stamp` gated until its apply execution policy is intentionally approved.
- Next recommended implementation task after checkpoint: make the self-heal status visible in the cockpit/operator readiness feed or add a simple operator command wrapper for self-heal audit/apply.

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
- restored SPOTCORE_ADMIN_API_TOKEN confirmed token-value identical to old backup, running container, and MCP env consumer
- stale restored compose backup containing placeholder token reference removed from tracked repo
- validator secret-regression rule corrected to detect literal token assignment without flagging safe env-var references
- `spot validate` passed after restore closure with 19 pass / 0 fail
- `spot validate-smoke` passed after restore closure with 25 pass / 0 fail
- restore validation cleanup committed and pushed as 0a677e1

Post-reboot verified services:

- spot-bridge-api.service running
- spot-mcp.service running through canonical user-level service
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
  - MCP streamable HTTP mounted at /spot/
- restored system-level duplicate stack was disabled:
  - /etc/systemd/system/spot-mcp.service
  - /etc/systemd/system/cloudflared.service
- reason: duplicate system-level stack listened on 8000 and returned 404 for /spot, causing intermittent connector failures
- user-level Cloudflare config at /home/ogre/.cloudflared/config.yml was corrected so mcp.starfleetcore.com points to http://localhost:8001 instead of stale http://localhost:8000
- /etc/cloudflared/config.yml still contains the old 8000 value but is not used by the active user-level mcp-tunnel.service; update separately only if system-level tunnel is intentionally re-enabled
- after tunnel correction, ChatGPT MCP health calls succeeded again
- `admin_operator_command` exists server-side, but current ChatGPT tool manifest may remain stale until connector/schema cache refreshes

Worker backup restoration after recovery:

- `scripts/spot-worker-backup.sh` was deployed to all four workers under /home/ogre/bin/spot-worker-backup.sh
- per-worker user systemd units were installed:
  - /home/ogre/.config/systemd/user/spot-worker-backup.service
  - /home/ogre/.config/systemd/user/spot-worker-backup.timer
- timer cadence configured with OnBootSec=2min, OnUnitActiveSec=6h, Persistent=true
- scoped sudo drop-in installed on workers for approved maintenance commands:
  - /etc/sudoers.d/spot-maintenance
- sudoers validation passed with visudo on workers 01, 03, and 04; worker 02 already had working maintenance sudo
- allowed-command sudo test passed on all four workers using `sudo -n /usr/bin/mkdir -p /tmp/spot-sudo-test`
- worker-01 and worker-04 backup failures were traced to `/mnt/collective` not being mounted after recovery
- `/mnt/collective` was mounted from the affected units and backup reruns succeeded
- all four workers produced worker-config backup metadata:
  - spot-worker-01: 20260428T162815Z
  - spot-worker-02: 20260428T162815Z
  - spot-worker-03: 20260428T162816Z
  - spot-worker-04: 20260428T162817Z
- `spot_save` now reports worker backup status OK for all four workers

Current confirmed routing ownership:

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

1. commit/checkpoint current self-heal MCP restart STATE update
2. when ChatGPT connector schema refreshes, verify `admin_operator_command` from ChatGPT directly
3. resolve Homer/tower offline separately
4. keep SPOTBACKUP/sdb2 read-only until recovery archive policy is decided

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
- ROADMAP.md may now be writable depending on current docker-compose.yml and container recreation state; treat doctrine mutation as operator-gated

Spot Core enforcement hardening applied:

- execute_with_enforcement catches execute-stage exceptions and returns structured 503 details after backup instead of raw 500
- rollback status normalization respects rollback functions returning {"ok": true}
- read-only bind mount failures return backup-preserved structured denial instead of silent corruption

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
- 2026-04-28 restore cleanup corrected secret-regression grep so safe env-var references are allowed while literal token assignments remain blocked

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
- /var/www/html/spot/operator-readiness.json
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
- readiness feed `operator-readiness.json` wired into top cockpit strip and published feed metadata
- both risk/html renderers rebuilt to use temp files + jq `--slurpfile` to eliminate kernel argv `Argument list too long` failures under large history payloads
- Incident Timeline renders open incidents, recent history, and remediation suggestions
- dashboard trend and latency history output capped to last 20 snapshots
- generated dashboard includes live telemetry, incident banner, fleet risk score, incident timeline, acknowledgements, anomalies, remediation/autonomy state, workers, trends, worker latency history, and operator readiness

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

1. commit/checkpoint current self-heal MCP restart STATE update
2. expose self-heal status in cockpit/operator readiness or add a simple operator command wrapper for self-heal audit/apply
3. resolve Homer/tower offline at 192.168.30.5 separately
