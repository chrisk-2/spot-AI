# SPOT FLEET STATE

## Current confirmed runtime state

Spot rescue/hardening phase is effectively complete and the current incident-engine chain is closed.

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
- fleet risk returned to NORMAL (0)
- open incident queue cleared

Latest checkpoint commit:

b80bf42 fix: decay stale remediation violation memory

## Strategic alignment

Spot is now treated as:

Starfleet OS subsystem — fleet control / worker dispatch / validation / autonomy layer

Spot is not the final product.

Spot must be finished enough to help build everything that follows.

Canonical forward build doctrine now lives in:

- /home/ogre/spot-stack/ROADMAP.md

Current active roadmap phase:

PHASE 1 — FINISH SPOT FOUNDATION / operator-autonomy bridge

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

Worker context from uploaded inventory snapshots:

- spot-worker-01: Ubuntu 22.04.5, AMD EPYC 4245P, 30GiB RAM, RTX 3060 12GB, IP 192.168.10.10, Ollama 0.18.2, models mistral:7b and llama3.1:8b
- spot-worker-02: Ubuntu 24.04.4, Xeon E5-1620 v2, 31GiB RAM, Quadro M4000 8GB plus GTX 1060 6GB, IP 192.168.10.11, Ollama 0.18.2, models bge-m3, nomic-embed-text, phi3.5
- spot-worker-03: Ubuntu 24.04.4, Ryzen 7 2700X, 31GiB RAM, GTX 1070 8GB plus RTX 3060 12GB, IP 192.168.10.13, Ollama 0.18.2, models qwen2.5-coder:7b, codellama:7b, deepseek-coder:6.7b, qwen2.5:14b
- spot-worker-04: Ubuntu 24.04.4, i7-13700KF, 62GiB RAM, TITAN Xp 12GB, IP 192.168.10.14, Ollama 0.20.6, model qwen2.5:14b

## Policy posture

Spot Autonomy Policy remains locked:

- primary rule: no backup, no change
- mutating autonomous actions must follow Detect -> Analyze -> Classify -> Backup -> Plan -> Verify -> Execute -> Test/Rollback
- Spot may create/read backup artifacts but must not delete/overwrite/alter existing backups
- high-risk network/firewall/VLAN/DNS/DHCP changes remain gated

## Immediate next objective

1. run `git status --short` and confirm the tree is clean after commit b80bf42
2. run `spot validate` and `spot validate-smoke` as a final health checkpoint if not already done after the stale-memory fix
3. run `spot_save` if desired for final project checkpoint
4. next engineering lane: either audit write failure hardening in app.py or transition into Spot Operator Ready polish
