Continuing Spot bridge work.

Run first:
- spot_save
- read /home/ogre/spot-stack/HANDOFF.md
- read /home/ogre/spot-stack/spot-core/STATE.md
- read /home/ogre/spot-stack/spot-core/spotcore/app.py
- read /home/ogre/spot-stack/watch/fleet-remediate.sh
- read /home/ogre/spot-stack/watch/fleet-validate.sh
- read /home/ogre/spot-stack/docker-compose.yml

Rules:
- no guessing
- read real runtime files before patching
- use runtime as source of truth
- fallback to GitHub only if runtime unavailable
- do not redesign system
- minimal changes only
- preserve auth and payload formats
- do not invent endpoints or models
- do not modify unrelated code
- enforce backup-first policy where applicable
- validate with the correct tool for the file type before restart

Current confirmed state:
- admin endpoints in app.py already use Pydantic request models
- /admin/validate uses AdminValidateRequest
- /admin/restart-service uses AdminRestartServiceRequest
- /admin/read-file uses AdminReadFileRequest
- /admin/write-file uses AdminWriteFileRequest
- /actions/restart-service/{worker_name}/{service_name} is working
- /admin/restart-service is working
- app.py compiles
- spot-core container restarts cleanly
- all workers eligible
- no workers quarantined

Validator status:
- fleet-validate.sh passes clean
- latest result:
  - pass=17
  - warn=0
  - fail=0
  - result=PASS

Admin validation coverage in fleet-validate.sh:
- routing ownership
- audit append
- watch health
- no quarantined hosts
- admin token fetch from container
- /admin/validate
- /admin/read-file

Exact current /admin endpoints from runtime app.py:
- POST /admin/validate
- POST /admin/restart-service
- POST /admin/read-file
- POST /admin/write-file

Exact current auth mechanism from runtime app.py:
- token is read from env:
  ADMIN_API_TOKEN = os.environ.get("SPOTCORE_ADMIN_API_TOKEN", "").strip()
- auth is payload token auth via require_admin_token(payload)
- /admin/restart-service, /admin/read-file, /admin/write-file require token in JSON body
- /admin/validate currently does NOT require token
- do not change that unless explicitly asked

Exact current request fields:
- /admin/validate:
  - worker
  - commands
- /admin/restart-service:
  - token
  - worker
  - service
- /admin/read-file:
  - token
  - worker
  - path
- /admin/write-file:
  - token
  - worker
  - path
  - content

Important verified token detail:
- host shell SPOTCORE_ADMIN_API_TOKEN was empty
- container SPOTCORE_ADMIN_API_TOKEN is set
- admin route worked only when using the token read from inside the container
- do not treat earlier invalid admin token response as an app.py bug

Important runtime compose detail:
- active compose file is /home/ogre/spot-stack/docker-compose.yml
- root compose contains SPOTCORE_ADMIN_API_TOKEN in environment for spot-core
- /home/ogre/spot-stack/spot-core/docker-compose.yml was not present during verification

Routing fix verified:
- alternate retry path in app.py now respects owner locking for owned roles
- recent routing audit window shows:
  - primaries only
  - no fresh fallbacks
  - no fresh violations
- latest /stats/routing-audit?limit=20 returned:
  - ok=true
  - violations=0
  - fallbacks=0

Remediation fix verified:
- fleet-remediate.sh was fully repaired after heredoc/indent damage
- stale historical routing violations no longer re-quarantine workers after manual release
- remediation now ignores violation entries older than release_ts when deciding fresh quarantine
- remediation script now uses non-interactive overwrite for remediation-state writes
- latest remediation run reported:
  - REMEDIATE no_remediation_changes | unchanged=0

Open follow-up items:
- update HANDOFF new-chat block because it still contains older Pydantic-task language if not already refreshed
- consider pruning or rotating old routing-audit history if desired, but not required for current correctness
- consider moving SPOTCORE_ADMIN_API_TOKEN out of plaintext docker-compose environment later, but not part of current break-fix

Next recommended task:
- stabilize handoff/state docs
- save checkpoint
- then choose the next functional target outside break-fix:
  - Spot UI / operator UX cleanup
  - routing observability polish
  - network monitor integration
  - controlled autonomy expansion
