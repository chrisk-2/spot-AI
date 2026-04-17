# SPOT HANDOFF

Current goal:
Stage 2 - Spot Operator Ready. Build operator command layer starting with spot-ops.sh and clean fleet-validate.sh duplicate output.

Last action taken:
Completed Milestone A - Spot Core Trusted. Added audit write failure logging in app.py, fixed fleet-watch core_health writing, validated routing/smoke successfully, and pushed checkpoint commit bbe6831.

Current known-good state:
- strict role ownership verified
- routing audit persistence working
- fleet-watch writes core_health correctly
- fleet-remediate backup-first behavior working
- quarantine/unquarantine works live without restart
- fleet-validate.sh passes
- fleet-validate.sh --smoke passes
- checkpoint pushed to origin/main

Rules:
- no guessing ever
- use runtime file as source of truth first
- if file needed, read exact file with sed/cat or repo fetch before patching
- do not redesign system unless explicitly asked
- do not do ad hoc chaos edits
- use scripted validation going forward
- preserve current routing ownership:
  - general -> spot-worker-01
  - utility -> spot-worker-02
  - coding -> spot-worker-03
  - heavy -> spot-worker-04

Primary repo:
https://github.com/chrisk-2/spot-AI

Primary runtime paths:
- repo root: /home/ogre/spot-stack
- app: /home/ogre/spot-stack/spot-core/spotcore/app.py
- watch: /home/ogre/spot-stack/watch/fleet-watch.sh
- remediate: /home/ogre/spot-stack/watch/fleet-remediate.sh
- validator: /home/ogre/spot-stack/watch/fleet-validate.sh
- policy: /home/ogre/spot-stack/watch/fleet-policy.json
- state: /home/ogre/spot-stack/spot-core/STATE.md

Next recommended step:
Build /home/ogre/spot-stack/watch/spot-ops.sh with subcommands:
validate, smoke, health, routing, audit, quarantine, release, logs
