Continuing Spot admin bridge work.

Current confirmed state:

* only `spot-core` is the direct control node
* all A-1 fleet changes must be brokered through `spot-core`
* backup-first enforcement is active
* remote backup over SSH works
* rollback on failed verification works
* rollback logging was upgraded
* admin auth token is now active and enforced
* missing token returns 403
* wrong token returns 403 invalid admin token

Working endpoints:

* `/admin/read-file`
* `/admin/write-file`
* `/admin/restart-service`
* `/admin/validate`

Verified:

* `read-file` works against `spot-worker-01`
* `write-file` success path works
* `write-file` forced-failure path rolls back correctly
* `restart-service` for `ollama` works
* `validate` works for safe allowed commands
* auth token works when passed in payload

Important current rule:

* token is read from Docker env via:
  `ADMIN_API_TOKEN = os.environ.get("SPOTCORE_ADMIN_API_TOKEN", "").strip()`
* do NOT paste token literals into `app.py`
* token must live in docker compose env for `spot-core`

Need next:

* add Pydantic request models for admin endpoints
* replace raw `payload: dict` on:

  * `/admin/read-file`
  * `/admin/write-file`
  * `/admin/restart-service`
  * `/admin/validate`
* keep behavior the same, no redesign
* goal is clean 422 responses instead of sloppy bad-input handling

Use real file as source of truth.
Read current:

* `/home/ogre/spot-stack/spot-core/spotcore/app.py`
* active docker compose for `spot-core`

Do not recap. Just move to request models cleanly with exact placement and full replacement blocks where needed.
