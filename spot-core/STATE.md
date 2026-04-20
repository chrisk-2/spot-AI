Continuing Spot bridge work.

Run first:
- spot_save
- read /home/ogre/spot-stack/HANDOFF.md
- read /home/ogre/spot-stack/spot-core/STATE.md
- read /home/ogre/spot-stack/spot-core/spotcore/app.py
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
- validate with python3 -m py_compile before restart

Current commit:
60f2709 checkpoint: 2026-04-20-23:17:28
fleet-validate.sh now validates:

routing ownership
audit append
watch health
admin token fetch from container
/admin/validate
/admin/read-file

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
- container SPOTCORE_ADMIN_API_TOKEN is set and was length 64
- admin route worked only when using the token read from inside the container
- do not treat earlier invalid admin token response as an app.py bug

Important runtime compose detail:
- active compose file is /home/ogre/spot-stack/docker-compose.yml
- root compose contains SPOTCORE_ADMIN_API_TOKEN in environment for spot-core
- /home/ogre/spot-stack/spot-core/docker-compose.yml was not present during verification

Key code facts already verified in runtime app.py:
- admin restart route has:
  - backup_sources=[]
  - require_backup=False
  - rollback backup_path uses: backup.get("backup_dir") if backup else None
- action restart route has:
  - backup_sources=[]
  - require_backup=False
- no further app.py surgery is needed unless a newly requested task requires it

What was verified live:
- POST /actions/restart-service/spot-worker-01/ollama returned ok:true
- POST /admin/restart-service returned ok:true when using container token
- app.py compiled and spot-core restarted cleanly

Next recommended task:
- build a scripted admin endpoint validation pass
- preferably in watch layer, either:
  - extend /home/ogre/spot-stack/watch/fleet-validate.sh
  - or add a dedicated /home/ogre/spot-stack/watch/spot-admin-validate.sh
- script should pull token from container, not assume host shell token exists

Task for this chat:
- inspect current validation scripts first
- identify safest place to add admin endpoint validation
- keep changes minimal
- do not redesign validation framework
- use runtime files only
