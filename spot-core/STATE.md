Continuing Spot bridge / Stage 3 network ops work.

Repo:
https://github.com/chrisk-2/spot-AI

Run first:
- read /home/ogre/spot-stack/HANDOFF.md
- read /home/ogre/spot-stack/spot-core/STATE.md
- read /home/ogre/spot-stack/watch/spot-ops.sh
- do not run spot_save unless preparing for another chat move

Rules:
- no guessing
- read real runtime files before patching
- use runtime as source of truth
- fallback to GitHub only if runtime unavailable
- do not redesign system
- minimal changes only
- preserve current working behavior
- keep network work read-only unless explicitly asked otherwise

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
  - quarantine-state
  - remediation
  - quarantine
  - release
  - logs

Network checks completed:
- spot-ops endpoints passed
- spot-ops dns-check initially exposed real DNS drift
- primary DNS .60.10 now resolves:
  - unifi.starfleet.local -> 192.168.60.20
  - adguard.starfleet.local -> 192.168.60.10
  - dashboard.starfleet.local -> 192.168.30.5
- secondary DNS .60.20 was broken due to AdGuard version mismatch:
  - starfleet-core had AdGuard v0.107.73
  - config schema was 34
  - dns-core had AdGuard v0.107.74 with schema 34
- AdGuard on .60.20 was fixed and now port 53 is listening
- spot-ops dns-check now passes 6/6
- AdGuard sync is working and the new rewrites replicated to AdGuard #2

Reverse proxy checks completed:
- raw http://192.168.60.20 opens Nginx Proxy Manager default site only
- that is expected and not proof of proxy host mapping
- unifi.starfleet.local via named host check works
- adguard backend works directly on AdGuard port
- dashboard.starfleet.local proxy path works and backend 192.168.30.5:7575 returns expected /board redirect

Fleet watcher / DNS work completed:
- ~/spot-stack/watch/fleet-dns-audit.sh now validates mixed DNS modes across the fleet
- DNS across workers and infra was audited and normalized
- fleet-watch.sh now uses inventory IPs for SSH instead of relying on hostnames resolving
- fleet-watch.sh now embeds per-host DNS state into fleet-status.json:
  - dns.ok
  - dns.servers
  - dns.mode
- SSH key-based automation was verified for:
  - spot-worker-01
  - spot-worker-02
  - spot-worker-03
  - spot-worker-04
  - spot-ui-01
  - starfleet-tower
  - unimatrix6
  - starfleet-core
  - dns-core
- fleet-watch.sh now detects dns_bad and queues DNS remediation safely after writing state
- DNS auto-remediation is verified working:
  - intentionally broke spot-worker-02 /etc/resolv.conf
  - fleet-watch.sh detected dns_bad
  - ~/spot-stack/watch/fix-dns.sh restored:
    - nameserver 192.168.60.10
    - nameserver 192.168.60.20
    - search starfleet.local
- fleet-watch.sh passes bash -n
- fleet-status.json is valid JSON after remediation changes

Routing audit reality:
- live role routing is currently correct:
  - general -> spot-worker-01
  - utility -> spot-worker-02
  - coding -> spot-worker-03
  - heavy -> spot-worker-04
- direct /exec tests confirmed correct worker selection for all four roles
- /stats/routing-audit?limit=5 returned a clean recent window:
  - violations = 0
  - fallbacks = 0
  - window_count = 5
- fleet-watch.sh still reports:
  - routing_audit:violations=6
  - routing_audit:fallbacks=33
  - routing_audit:last_violation_ts=1776569769
- treat current routing issue as audit/history/window behavior, not active role misrouting
- next routing task is to inspect watcher alert policy versus API audit window, not to redesign scheduler routing

Important reality:
- 192.168.60.20 root web is NPM default site
- direct AdGuard #2 UI works on its direct AdGuard port
- DNS pair is now genuinely active and in sync
- fleet DNS control loop is now real:
  - detect drift
  - report drift
  - auto-fix drift
- current routing looks healthy in live tests
- remaining routing alert noise is likely retained audit history / summary-window behavior

Next task:
- add spot-ops reverse-proxy-check
- automate named-host checks for:
  - unifi.starfleet.local
  - adguard.starfleet.local
  - dashboard.starfleet.local
- report response codes and whether each route behaves as expected
- keep this read-only

After that:
- inspect routing audit alert behavior in fleet-watch.sh versus /stats/routing-audit API window
- do not redesign scheduler unless live routing is proven wrong again

Do not do next:
- do not redesign spot-core
- do not expand autonomy scope beyond what is already working
- do not change network configuration as part of reverse-proxy-check work
- do not touch unrelated routes or validation logic unless required by the requested task

If moving to a new chat:
- run spot_save only when actually handing off
- use HANDOFF.md + this STATE.md as startup context
- treat this file as the current runtime state source of truth
