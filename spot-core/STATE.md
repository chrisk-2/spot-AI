# SPOT FLEET STATE

## Current confirmed runtime state

Spot rescue/hardening phase is effectively complete.

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
- Spot UI cockpit renderer/publisher path now verified honest on live host

Latest checkpoint commit:

01da8b1 tune: finalize worker cleanup and utility lane warmup

## Strategic alignment

Spot is now treated as:

Starfleet OS subsystem — fleet control / worker dispatch / validation / autonomy layer

Spot is not the final product.

Spot must be finished enough to help build everything that follows.

Canonical forward build doctrine now lives in:

- /home/ogre/spot-stack/ROADMAP.md

Current active roadmap phase:

PHASE 1 — FINISH SPOT FOUNDATION

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

Verified backup artifact:

- /mnt/collective/backups/spot-core/filesystem_local/20260425-032201-1777087321245017714

Root cause of prior HANDOFF.md write failure:

- docker-compose.yml mounted HANDOFF.md into spot-core as read-only
- mount was changed from :ro to :rw for HANDOFF.md only
- ROADMAP.md remains read-only

Spot Core enforcement hardening applied:

- execute_with_enforcement now catches execute-stage exceptions and returns structured 503 details after backup instead of raw 500
- rollback status normalization now respects rollback functions returning {"ok": true}

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
- smoke quarantine cycle now explicitly asserts quarantined=true eligible=false and release restoration without restart
- backup freshness verification added for all four workers
- strict-mode shell parser and nounset bugs corrected after live validation

Host validation rerun results:

- `bash -n /home/ogre/spot-stack/watch/fleet-validate.sh` PASS
- `spot validate` PASS
- `spot validate-smoke` PASS

Validation backup artifacts:

- /mnt/collective/backups/spot-core/filesystem_local/20260425-160236-1777132956687295108
- /mnt/collective/backups/spot-core/filesystem_local/20260425-161303-1777133583866491294

## Spot UI / Cockpit status

Spot UI Phase 1 through Phase 7 foundation is now live on the real spot-core host filesystem.

Confirmed host files under:

- /home/ogre/spot-stack/watch/

UI/operator files present:

- spot-ui-01.sh
- spot-ui-publish.sh
- spot-ui-history.sh
- spot-ui-incident-ledger.sh
- spot-ui-ack.sh
- spot-ui-render-html.sh
- spot-ui-render-risk.sh
- spot-ui-render-timeline.sh
- spot-ui-render-acks.sh
- spot-ui-risk.json.jq

Published browser artifacts under:

- /var/www/html/spot/index.html
- /var/www/html/spot/spot.json
- /var/www/html/spot/history.json
- /var/www/html/spot/incidents.json
- /var/www/html/spot/acks.json
- /var/www/html/spot/meta.json

Confirmed working:

- all Spot UI shell scripts pass `bash -n`
- `spot-ui-publish.service` confirmed active as real system service on host
- meta.json and index.html advance on publish cycle
- browser dashboard renders successfully from live publish path
- Fleet Risk card renders successfully
- Incident Timeline renders successfully
- Operator Acknowledgements card now renders successfully
- acknowledgement feed `acks.json` confirmed wired into main HTML renderer
- both risk/html renderers rebuilt to use temp files + jq `--slurpfile` to eliminate kernel argv `Argument list too long` failures under large history payloads
- generated dashboard includes live telemetry, incident banner, fleet risk score, incident timeline, acknowledgements, anomalies, remediation/autonomy state, workers, trends, and worker latency history

Current LAN cockpit URL:

- http://192.168.60.30/spot/

Important implementation note:

- MCP-created Spot UI files initially landed in container overlay namespace, not the real host repo
- files were copied from Docker overlay into `/home/ogre/spot-stack/watch/`
- future file edits should target the real host path or confirm namespace mapping before editing

## Immediate next objective

1. run `spot_save`
2. checkpoint repo drift if desired
3. begin Spot Incident Engine autonomy layer
4. implement anomaly -> incident creation thresholds
5. implement remediation suggestion queue
6. implement acknowledgement/autonomy transition logic
