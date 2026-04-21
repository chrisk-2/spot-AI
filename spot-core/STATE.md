Current confirmed state:
- Stage 1 / Milestone A is effectively locked
- Stage 2 operator shell is working
- spot-ops.sh now provides:
  - status
  - validate
  - validate-smoke
  - health
  - routing
  - audit
  - net-basics
  - endpoints
  - dns-check
  - reverse-proxy-check
  - quarantine-state
  - remediation
  - quarantine
  - release
  - logs

Reverse proxy checks completed:
- spot-ops reverse-proxy-check added and validated
- named-host checks now verify reverse proxy behavior through 192.168.60.20 using host-aware HTTPS checks
- current results:
  - unifi.starfleet.local -> OK
  - adguard.starfleet.local -> OK
  - dashboard.starfleet.local -> OK
- command is read-only and now included in --help output

Routing audit alert reality resolved:
- fleet-watch.sh routing alert behavior was tightened so it no longer alerts on fallback count alone or stale timestamp alone
- routing-audit.jsonl on disk was empty while spot-core API still showed historical violations/fallbacks
- root cause was stale in-memory RECENT_ROUTING_AUDIT state inside long-running spot-core container
- restarting spot-core cleared stale in-memory routing audit state
- current routing audit state is now clean:
  - ok: true
  - window_count: 0
  - primaries: 0
  - fallbacks: 0
  - violations: 0
  - last_violation_ts: null
- fleet-watch.sh now reports:
  - OK fleet healthy | routing clean

Important reality:
- live routing tests had already been correct
- routing issue was not active scheduler misrouting
- problem was watcher alert policy plus stale in-memory audit state, not current role ownership failure

Next task:
- update STATE.md with completed reverse-proxy-check and routing-audit cleanup
- then save checkpoint for clean handoff
- after that, next read-only network/operator work can continue from this cleaner baseline

Do not do next:
- do not redesign scheduler routing
- do not change spot-core routing logic based on stale audit history
- do not treat historical log lines as current routing failure
