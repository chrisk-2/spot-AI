Continuing Spot bridge / Stage 3 network ops work.

Repo:
https://github.com/chrisk-2/spot-AI

Run first:
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

Milestone status:
- Milestone A — Spot Core Trusted: COMPLETE
- Milestone B — Spot Operator Ready: NEXT
- Stage 3 network ops work remains read-only until explicitly changed

Current confirmed state:
- Stage 1 / Milestone A is now locked complete
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

Validation status:
- fleet-validate.sh passed on 2026-04-21
- result: PASS
- checks: 15
- warnings: 0
- failures: 0
- smoke mode was skipped on that run
- confirmed by runtime output:
  - routing audit file exists
  - role ownership validated
  - routing audit append validated
  - fleet status present and valid JSON
  - routing audit summary present and valid JSON
  - fleet-status core_health.ok is true
  - fleet-status hosts report ssh_ok/service_ok
  - fleet-status shows no quarantined hosts
  - /admin/validate returned expected JSON structure
  - /admin/read-file returned expected content

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

Important reality:
- 192.168.60.20 root web is NPM default site
- direct AdGuard #2 UI works on its direct AdGuard port
- DNS pair is now genuinely active and in sync
- Spot Core validation is now clean and passing
- current baseline should be treated as trusted until a new verified change is made

Current phase:
- Milestone B — Spot Operator Ready

Next task:
- add spot-ops reverse-proxy-check
- automate named-host checks for:
  - unifi.starfleet.local
  - adguard.starfleet.local
  - dashboard.starfleet.local
- report response codes and whether each route behaves as expected
- keep this read-only

Do not do next:
- do not redesign spot-core
- do not expand autonomy scope
- do not change network configuration as part of reverse-proxy-check work
- do not touch unrelated routes or validation logic unless required by the requested task

If moving to a new chat:
- run spot_save
- use HANDOFF.md + this STATE.md as the startup context
- treat this file as the current state source of truth

