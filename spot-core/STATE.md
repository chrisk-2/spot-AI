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
- one-shot publish succeeds
- browser dashboard renders successfully
- Caddy now exposes the dashboard over LAN HTTP
- temporary Python server test proved static artifact validity
- generated dashboard includes live telemetry, incident banner, fleet risk score, incident timeline, anomalies, remediation/autonomy state, workers, trends, and worker latency history

Current LAN cockpit URL:

- http://192.168.60.30/spot/

DNS/Cloudflare checkpoint

~/spot-stack/NETWORK_DNS_CHECKPOINT.md

Caddy exposure:

- /etc/caddy/Caddyfile now keeps existing `spotapi.starfleet.local` reverse proxy
- added HTTP-only LAN static file block for `http://192.168.60.30` serving `/var/www/html`

Publisher daemon:

- spot-ui-publish.service needed to be created on the real host because prior MCP-created unit existed only in container namespace
- user reported service/deployment seems good after host-side correction

Important implementation note:

- MCP-created Spot UI files initially landed in container overlay namespace, not the real host repo
- files were copied from Docker overlay into `/home/ogre/spot-stack/watch/`
- future file edits should target the real host path or confirm namespace mapping before editing

Remaining known UI gap:

- `spot-ui-render-acks.sh` exists and `acks.json` is published
- acknowledgement card injection into `spot-ui-render-html.sh` may still need final visual confirmation after next publish

## Immediate next objective

1. confirm `spot-ui-publish.service` status on real host
2. confirm dashboard auto-refresh updates `meta.json` every 60s
3. visually confirm acknowledgement card appears after renderer injection/publish
4. run `spot_save`
5. checkpoint repo drift if desired
6. continue wiring Codex into practical Spot engineering workflow
7. begin Spot Incident Engine autonomy layer
