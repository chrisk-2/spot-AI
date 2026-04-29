# SPOT FLEET STATE

## Current confirmed runtime state

Spot rescue/hardening and 2026-04-28 bare-metal recovery closure are complete enough to treat Milestone A — Spot Core Trusted as locked.

Confirmed working:

- spot-core control plane healthy
- MCP wrapper path healthy
- local and remote file mutation paths proven
- quarantine/release proven
- routing audit and latency stats working
- `spot` operator commands working, including `spot self-heal audit|plan|dry-run|apply`
- `spot validate` and `spot validate-smoke` passing after 2026-04-28 restore closure
- worker backup automation restored and working on all four workers
- worker-local backup service/timer deployed on all four workers
- worker backup metadata visible to `spot_save` for all four workers
- scoped sudo maintenance drop-in installed and validated on all four workers for approved maintenance commands
- `/mnt/collective` mounted and usable by all four workers for backup writes
- spot-core container recreated after mount correction and healthy on port 8787
- spot-core host/container backup view restored enough for `spot_save` to see worker metadata
- validator secret regression checks working
- worker fleet runtime now effectively Ollama-only on port 11434
- worker-02 Quadro M4000 8GB pinned as utility Ollama lane
- worker-02 GTX1060 6GB left free for future monitoring/camera workloads
- latest routing audit window clean: primary routing OK, 0 fallbacks, 0 violations, 0 manual overrides
- Spot UI cockpit renderer/publisher path verified honest on live host
- Spot Incident Engine persistent incidents, acknowledgement lifecycle, and remediation suggestions validated
- cockpit displays incident remediation guidance, capped history, operator readiness, and validation freshness
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
- `operator-readiness.json` now includes Spot Core health, MCP local health, routing integrity, backup freshness, git dirty state, validation freshness, and self-heal status
- `watch/spot-validation-stamp.sh` records `spot validate` result, exit code, duration, log tail, and freshness metadata
- Self-Heal audit/plan/dry-run/apply modes added and validated
- Self-Heal allowlisted apply mode is present and limited to `republish_dashboard` and `restart_mcp`
- Self-Heal noop, apply_start, apply_finish, and apply_failure ledger events preserve full JSON payloads through file-backed writes
- Self-Heal `republish_dashboard` apply runs post-condition verification and only reports OK when dashboard metadata freshness verifies after execution
- Self-Heal `restart_mcp` apply is allowlisted, single-attempt, cooldown-controlled, ledgered, and verified against local MCP `/health`
- Self-Heal live MCP restart recovery test passed: service stopped, self-heal restarted `spot-mcp.service`, `/health` returned healthy, and systemd reported active
- Self-Heal deterministic test hook `SELF_HEAL_FORCE_VERIFY_FAIL=1` validated failure ledger without service disruption
- Self-Heal `refresh_validation_stamp` verifier is implemented but policy-gated and not apply-allowlisted
- Self-Heal policy now gates only `refresh_validation_stamp` outside the apply allowlist
- Self-Heal status is now embedded in `/var/www/html/spot/operator-readiness.json` under `.self_heal`
- DNS check now aligns with actual AdGuard hostnames: `adguard1.starfleet.local` -> 192.168.60.10 and `adguard2.starfleet.local` -> 192.168.60.20
- latest `spot dns-check` after hostname alignment passed with ok_count=6 / fail_count=0
- latest Spot health after MCP restart/connector work was healthy

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
- 83b3d18 add spot self heal operator command
- 9b5b013 checkpoint: 2026-04-29-17:01:10
- pending/local: expose self heal in operator readiness
- pending/local: align dns check with adguard hostnames if not yet committed
- pending/local: update state for readiness/dns/mcp manifest checkpoint

## 2026-04-29 Self-Heal checkpoint

Current self-heal file:

- /home/ogre/spot-stack/watch/spot-self-heal.sh

Operator wrapper:

- `spot self-heal audit`
- `spot self-heal plan`
- `spot self-heal dry-run`
- `spot self-heal apply`

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

Runtime state/log/readiness paths:

- self-heal state: /home/ogre/spot-stack/watch/state/self-heal-state.json
- action ledger: /mnt/collective/logs/spot/self-heal-actions.jsonl
- validation stamp: /home/ogre/spot-stack/watch/state/operator-validation.json
- operator readiness: /var/www/html/spot/operator-readiness.json

Readiness/self-heal visibility:

- `watch/spot-ui-readiness.sh` now runs `watch/spot-self-heal.sh audit` read-only and embeds `.self_heal`
- `.self_heal` includes ok, generated_at, mode, autonomy_level, apply_enabled, apply_allowlist, gated_not_allowlisted, action_count, actions, and checks
- validated published output showed `.self_heal.ok=true`, apply allowlist `["republish_dashboard", "restart_mcp"]`, gated `["refresh_validation_stamp"]`, and checks all true except repo dirty warning present as non-safe action

Validation performed:

- `bash -n watch/spot-self-heal.sh` passed after ledger and verification changes
- `watch/spot-self-heal.sh apply` NOOP path produced populated apply_noop payload
- forced stale dashboard metadata test triggered `republish_dashboard`
- apply_start/apply_finish ledger payloads populated with selected action details, exit code, command log, and verifier result
- forced verifier-failure test with `SELF_HEAL_COOLDOWN_SECONDS=0 SELF_HEAL_FORCE_VERIFY_FAIL=1` produced populated apply_failure payload
- `watch/spot-self-heal.sh audit` showed `refresh_validation_stamp` verifier implemented and not apply-allowlisted
- `watch/spot-self-heal.sh audit` showed `restart_mcp` apply_allowlisted=true and max_attempts=1
- live MCP restart test stopped `spot-mcp.service`, ran self-heal apply, logged apply_start/apply_finish for `restart_mcp`, verified MCP health, and returned apply_result `status=OK`
- direct post-test checks returned `{"status":"healthy"}` from MCP health and `active` from systemd
- `spot self-heal audit`, `spot self-heal dry-run`, `spot status`, and `spot validate` passed after operator wrapper addition
- `watch/spot-ui-readiness.sh` generated populated `.self_heal`
- `SPOT_UI_ONCE=1 bash watch/spot-ui-publish.sh --once` published populated `.self_heal` to `/var/www/html/spot/operator-readiness.json`

## DNS / local network checkpoint

DNS check now matches actual configured AdGuard rewrite names:

- `adguard1.starfleet.local` -> 192.168.60.10
- `adguard2.starfleet.local` -> 192.168.60.20
- `dashboard.starfleet.local` -> 192.168.30.5

Latest validation after check alignment:

- `bash -n watch/spot-ops.sh` passed
- `spot dns-check` returned ok_count=6 / fail_count=0

Known remaining external issue:

- Homer/tower at 192.168.30.5:7575 remains offline/unreachable from endpoint check
- this is outside restored spot-core stack and requires physical/network inspection of tower or service recovery on that host

## MCP / ChatGPT connector checkpoint

Active user-level MCP stack remains canonical:

- service: /home/ogre/.config/systemd/user/spot-mcp.service
- command: `/home/ogre/spot-mcp/.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8001`
- app: /home/ogre/spot-mcp/app.py
- wrapper: /home/ogre/spot-mcp/spot_mcp_wrapper.py
- streamable HTTP mounted at /spot
- user-level Cloudflare tunnel points mcp.starfleetcore.com to localhost:8001

Server-side `admin_operator_command` status:

- `/home/ogre/spot-mcp/spot_mcp_wrapper.py` contains `@mcp.tool()` immediately above `async def admin_operator_command(command: str)`
- `admin_operator_command` posts to `/admin/operator-command`
- `/home/ogre/spot-mcp/app.py` imports `mcp` from `spot_mcp_wrapper` and mounts it at `/spot`
- `systemctl --user restart spot-mcp.service` completed cleanly
- `curl -fsS http://127.0.0.1:8001/health` returned `{"status":"healthy"}`

ChatGPT-side status before switching chats:

- current chat/session still did not expose `admin_operator_command` in the available tool surface
- exposed tools remained health, routing/fleet/stats, admin_read/write local/file, admin_validate, admin_restart_service, admin_quarantine, and admin_release
- likely remaining issue is ChatGPT connector schema/tool manifest cache for the current session
- next chat should verify whether `admin_operator_command` appears after connector refresh/new session

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
- systemd spot services restored and confirmed active
- restored SPOTCORE_ADMIN_API_TOKEN confirmed token-value identical to old backup, running container, and MCP env consumer
- stale restored compose backup containing placeholder token reference removed from tracked repo
- validator secret-regression rule corrected to detect literal token assignment without flagging safe env-var references
- `spot validate` passed after restore closure with 19 pass / 0 fail
- `spot validate-smoke` passed after restore closure with 25 pass / 0 fail

Post-reboot verified services:

- spot-bridge-api.service running
- spot-mcp.service running through canonical user-level service
- spot-ui-publish.service running
- spot-monitor-alert-state.timer active
- spot-monitor-snapshot.timer active
- docker spot-core container running on 8787
- Spot UI output files regenerated and non-empty

## Strategic alignment

Spot is now treated as:

Starfleet OS subsystem — fleet control / worker dispatch / validation / autonomy layer

Spot is not the final product.

Spot must be finished enough to help build everything that follows.

Canonical forward build doctrine now lives in:

- /home/ogre/spot-stack/ROADMAP.md

Current active roadmap phase:

PHASE 1 — SPOT OPERATOR READY / ENGINEERING WORKFLOW POLISH

## Policy posture

Spot Autonomy Policy remains locked:

- primary rule: no backup, no change
- mutating autonomous actions must follow Detect -> Analyze -> Classify -> Backup -> Plan -> Verify -> Execute -> Test/Rollback
- Spot may create/read backup artifacts but must not delete/overwrite/alter existing backups
- high-risk network/firewall/VLAN/DNS/DHCP changes remain gated

## Immediate next objective

1. commit/checkpoint current STATE update plus pending readiness/DNS changes if not already committed
2. switch chats and verify whether `admin_operator_command` appears in ChatGPT MCP tool surface
3. keep `refresh_validation_stamp` gated until readiness self-heal visibility has aged through normal publish cycles
4. resolve Homer/tower offline at 192.168.30.5:7575 separately
