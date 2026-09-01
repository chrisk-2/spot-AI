# Post-2.39 K21D Live Executor Transaction-Binding Correction Review

## Review identity

- generated at: 2026-09-01T15:08:31Z
- host: spot-core
- repository head: eb8f38b9d2e2f1823117f3bead28e0222882c5a7
- reviewer: spot-worker-05
- reviewer authority: proposal_review_only
- model: qwen2.5-coder:32b
- phase: live-executor transaction-binding correction

## Intent

Independently review the repository-only correction made after the prior
Worker-05 PASS failed to detect that an installation authorization was not
bound to one exact transaction ID.

The corrected implementation must:

1. require transaction_id in the immutable authorization record;
2. require that authorization transaction_id equal transaction transaction_id;
3. reject authorization state with rollback_completed=true;
4. preserve same-transaction consumption and receipt collision denial;
5. deny reuse of one authorization under a changed transaction ID before
   consumption or mutation;
6. preserve the exact ordered eight-file mapping and all prior safety controls;
7. create no current installation authority.

The prior PASS is retained as historical evidence but must not be used as the
live-executor PASS binding for any future authorization. A strict PASS from
this correction review is required instead.

## Governance boundary

- Spot Core sole executor: true
- Worker self-apply allowed: false
- fresh installation authorization required: true
- K21D transaction authorized now: false
- system-path installation authorized now: false
- installation performed: false
- daemon-reload authorized now: false
- activation authorized: false
- enablement authorized: false
- scheduling authorized: false
- production observation authorized: false
- execution allowed: false
- mutation authority: false

## Corrected artifact identities

- live executor: watch/observe/controlled-read-observe-install-transaction.py
- live executor SHA-256: a3ff0e5af4be21b691995a2c2bbdc784a44655c47168bdf8be6351ed331e87b2
- execution test: watch/observe/controlled-read-observe-install-transaction-execution-test.py
- execution-test SHA-256: 7b2ff96d2f3fc2e80dd724ad8efb33a2bff0038b654c0730d8579ad45a7fd21e
- implementation validator: watch/observe/controlled-read-observe-install-transaction-implementation-validate.py
- implementation-validator SHA-256: 23e0c156f7bafcdeb2d0acda67a7c5bab80b530c77fffb088df030696042df6a
- unchanged failure test: watch/observe/controlled-read-observe-install-transaction-failure-test.py
- failure-test SHA-256: 92d23fcba169f634d2d05e65650631e84acd5a23afdc5f573d5b5d19117dc5d1

## Previous review being superseded for future authorization use

- prior PASS: watch/review/bundles/POST239-K21D-LIVE-EXECUTOR-PASS-20260901T132734Z.json
- prior PASS SHA-256: 1019b281db265964d24e785a46726949f86bd0883ada6888c36860bb87ad794c
- prior bundle: watch/review/bundles/post239-k21d-live-executor-review-bundle-20260901T132734Z.md
- prior bundle SHA-256: 6bf073fbd5857f31dc50d62bd1651c298432eb6ed4dca1767d1045ac08e2a93f

### Prior PASS record

~~~json
{
  "activation_authorized": false,
  "artifacts": {
    "execution_test": {
      "path": "watch/observe/controlled-read-observe-install-transaction-execution-test.py",
      "sha256": "6810b844fd3ebcbda8290e0cf0a224169ed479cd7577080f49cc25158336b330"
    },
    "implementation_validator": {
      "path": "watch/observe/controlled-read-observe-install-transaction-implementation-validate.py",
      "sha256": "c72b4a1c72029e7475ca3ed56cd5f2740f2a2407c5e0ba625c1d604aa5ded002"
    },
    "live_executor": {
      "path": "watch/observe/controlled-read-observe-install-transaction.py",
      "sha256": "2b30248eb2d5fb4583c0b96003616e204978144f8c2651efc4e6a1804927e325"
    }
  },
  "authority_basis": {
    "construction_authorization": {
      "path": "watch/review/bundles/AUTH-POST239-K21D-LIVE-EXECUTOR-CONSTRUCTION-20260829T170427Z.json",
      "sha256": "c42eb2118c530da1f0f6b6ad4d47e5cdd50dc0c08c775ffa0d13e6de7132c5a3"
    },
    "revocation": {
      "path": "watch/review/bundles/REVOKE-POST239-K21D-INSTALLATION-20260829T163721Z.json",
      "sha256": "ae403d76af62d60bdb03c344f8e446e6c3702c56dffd289a21e191b0547970f6"
    },
    "revoked_installation_authorization": {
      "path": "watch/review/bundles/AUTH-POST239-K21D-INSTALLATION-20260829T163721Z.json",
      "sha256": "b64054247a611e6f949f99cfaf4a275082aed5a81c457fab5f19e603edc91e1a"
    }
  },
  "authorization_boundary_preserved": true,
  "authorization_consumed": false,
  "backup_created": false,
  "correlated_reviews": {
    "blueprint_pass": {
      "path": "watch/review/bundles/POST239-K21D-BLUEPRINT-PASS-20260828T150447Z.json",
      "sha256": "ca9b109a863369a1874cf30ac6bf295664c2b8ad50135ab2e7528146a0218b2e"
    },
    "historical_dormant_implementation_pass": {
      "path": "watch/review/bundles/POST239-K21D-IMPLEMENTATION-PASS-20260828T222053Z.json",
      "sha256": "c5836d5b38cc97895e748c8b70ceb8b7420f467b4a18a02a33c84df79ab19673"
    },
    "mapping_correction_pass": {
      "path": "watch/review/bundles/POST239-K21D-MAPPING-CORRECTION-PASS-20260829T162201Z.json",
      "sha256": "7eda6a23447300e11ac660eb381dacf783190abb82c0cae5d38fc4a94cc172f0"
    }
  },
  "daemon_reload_authorized": false,
  "daemon_reload_performed": false,
  "enablement_authorized": false,
  "exact_mapping_preserved": true,
  "execution_allowed": false,
  "fresh_installation_authorization_required": true,
  "generated_at": "2026-09-01T13:27:34Z",
  "host": "spot-core",
  "installation_manifest_created": false,
  "installation_performed": false,
  "k21d_transaction_authorized": false,
  "live_executor_accepted": true,
  "mutation_authority": false,
  "production_observation_authorized": false,
  "repository": {
    "head": "ab6ae8cba093074482ab3aa9209c8a9c9ed3ab5b",
    "origin_main": "ab6ae8cba093074482ab3aa9209c8a9c9ed3ab5b"
  },
  "review": {
    "activation_authorized": false,
    "activation_prevented": true,
    "authorization_boundary_preserved": true,
    "backup_before_mutation_enforced": true,
    "blocking_findings": [],
    "conditional_daemon_reload_only": true,
    "confidence": "high",
    "daemon_reload_authorized": false,
    "daemon_reload_performed": false,
    "durable_consumption_before_mutation": true,
    "enablement_authorized": false,
    "exact_mapping_preserved": true,
    "execution_allowed": false,
    "fresh_installation_authorization_required": true,
    "installation_performed": false,
    "intent_match": "pass",
    "k21d_transaction_authorized": false,
    "live_executor_accepted": true,
    "mutation_authority": false,
    "notes": "The live executor candidate adheres to all required safety and governance boundaries, preserves the exact eight-file mapping, enforces single-use authorization, ensures durable consumption before mutation, verifies rollback, conditionally reloads daemon only when necessary, and prevents any form of activation or production observation. Offline tests confirm its correctness without touching live system paths.",
    "offline_tests_accepted": true,
    "phase_match": "pass",
    "policy_match": "pass",
    "production_observation_authorized": false,
    "required_fixes": [],
    "rollback_verified": true,
    "scheduling_authorized": false,
    "single_use_enforced": true,
    "system_path_installation_authorized": false,
    "verdict": "PASS"
  },
  "reviewed_bundle": "watch/review/bundles/post239-k21d-live-executor-review-bundle-20260901T132734Z.md",
  "reviewed_bundle_sha256": "6bf073fbd5857f31dc50d62bd1651c298432eb6ed4dca1767d1045ac08e2a93f",
  "reviewer": {
    "authority": "proposal_review_only",
    "host": "spot-worker-05",
    "model": "qwen2.5-coder:32b"
  },
  "scheduling_authorized": false,
  "schema": "starfleet.post239.k21d_live_executor_review.v1",
  "status": "PASS",
  "system_path_installation_authorized": false
}
~~~

## Accepted blueprint

~~~markdown
# Post-2.39 K21D Installation-Transaction Blueprint

DESIGN AND REVIEW ONLY

This blueprint does not authorize installation, daemon-reload, activation,
enablement, scheduling, production observation, service actions, remediation,
execution, or mutation.

## Purpose

Define the future, separately reviewed transaction that may install the accepted
K21C dormant read-only observer artifacts onto `spot-core`.

K21D separates five states:

1. transaction design;
2. independent review;
3. explicit operator authorization;
4. backup-bound installation-only execution;
5. post-install verification and closeout.

No later state may be inferred from completion of an earlier state.

## Locked current state

- host: `spot-core`
- Spot Core sole installation authority: true
- worker self-apply allowed: false
- K21C installation contract accepted: true
- K21D transaction authorized: false
- system-path installation authorized: false
- installation performed: false
- daemon-reload planned now: false
- daemon-reload authorized now: false
- daemon-reload performed: false
- observer installed: false
- observer enabled: false
- observer active: false
- observer scheduled: false
- production observation authorized: false
- service action authorized: false
- remediation authorized: false
- execution allowed: false
- mutation authority: false

## Correlated K21C baseline

The future transaction must bind all of the following:

- repository commit
  `87bf1b3b375639ed4e90b6be46a4d381f115e4db`;
- Worker-05 K21C PASS record;
- corrected review bundle and SHA-256;
- accepted K21C source identities;
- K21D Worker-05 transaction-design PASS;
- explicit K21D operator authorization;
- verified backup manifest and binding;
- rollback document and binding;
- installation manifest and digest;
- installation receipt and verification results.

A missing, changed, stale, or mismatched binding denies installation.

## Fixed installation sources and destinations

The installation transaction may address exactly these eight mappings:

1. `watch/observe/controlled-read-observe.py`
   to `/usr/local/lib/spot/observe/controlled-read-observe.py`
2. `watch/observe/controlled_read_observe_validation_v1.py`
   to `/usr/local/lib/spot/observe/controlled_read_observe_validation_v1.py`
3. `watch/observe/controlled-read-observe-request-validate.py`
   to `/usr/local/lib/spot/observe/controlled-read-observe-request-validate.py`
4. `watch/observe/controlled-read-observe-evidence-validate.py`
   to `/usr/local/lib/spot/observe/controlled-read-observe-evidence-validate.py`
5. `watch/observe/controlled-read-observe-allowlist-v1.json`
   to `/etc/spot/observe/controlled-read-observe-allowlist-v1.json`
6. `watch/observe/controlled-read-observe-request-schema-v1.json`
   to `/etc/spot/observe/controlled-read-observe-request-schema-v1.json`
7. `watch/observe/controlled-read-observe-evidence-schema-v1.json`
   to `/etc/spot/observe/controlled-read-observe-evidence-schema-v1.json`
8. `watch/observe/controlled-read-observe.service`
   to `/etc/systemd/system/spot-controlled-read-observe.service`

No source substitution, destination substitution, path traversal,
symlink redirection, wildcard expansion, directory-wide copy, or
additional file is permitted.
## Transaction identity

A K21D installation transaction requires:

- one unique transaction ID;
- one exact repository commit;
- one exact installation manifest digest;
- one authorization ID and digest;
- one Worker-05 review record and digest;
- one backup manifest ID and digest;
- one backup binding ID;
- one rollback binding ID;
- one installation receipt path;
- one replay identity derived from the immutable transaction inputs.

Reuse of a transaction ID with changed material inputs is denied.

A successfully completed or rolled-back transaction cannot be replayed.

## Separate authorization boundary

K21D design review does not authorize installation.

After Worker-05 accepts this design, a separate operator authorization record
must explicitly state:

- exact transaction ID;
- exact repository commit;
- exact reviewed K21D bundle digest;
- exact eight source and destination mappings;
- system-path installation authorized: true;
- daemon-reload authorized only if the unit file changes: true;
- activation authorized: false;
- enablement authorized: false;
- scheduling authorized: false;
- production observation authorized: false;
- execution allowed: false;
- mutation authority: false;
- expiration time;
- single-use authorization: true.

The installation executor must reject missing, expired, reused, mismatched, or
expanded authorization.

## K21C-to-K21D schema transition

The accepted K21C manifest schema intentionally locks these fields false:

- `system_path_installation_authorized`
- `daemon_reload_planned`

K21D must not weaken or rewrite the accepted K21C schema.

After K21D design review, a distinct versioned K21D transaction schema may be
constructed. That future schema may require authorization and reload fields to
be true only when correlated to the separate single-use authorization record.

Creating or reviewing that future schema does not itself grant authority.

## Backup transaction

Before installation, the installer must inspect all eight destinations without
changing them.

For every destination it must record:

- destination path;
- whether it exists;
- whether it is a regular file or symlink;
- owner and group;
- mode;
- SHA-256 when it is a regular file;
- verified backup path when it exists;
- expected post-install source digest.

Existing symlinks, non-regular files, unexpected owners, or paths outside the
fixed mapping fail closed.

Every existing regular file must be copied to the fixed K21D backup root and
verified byte-for-byte before installation.

Missing destinations must be recorded explicitly as absent.

No verified backup manifest and binding means no installation.

## Installation-only transaction

The future authorized transaction may:

1. revalidate repository identity and cleanliness;
2. revalidate every correlated record and digest;
3. acquire an installation lock;
4. verify that the authorization is unexpired and unused;
5. create and verify the backup transaction;
6. install only the eight fixed files with reviewed owners, groups, and modes;
7. run `systemctl daemon-reload` only if the unit file changed;
8. verify installed hashes, modes, owners, and groups;
9. verify the unit remains disabled and inactive;
10. verify no timer exists;
11. write an immutable installation receipt;
12. mark the single-use authorization consumed.

The transaction must not start, enable, restart, reload, try-restart, or invoke
the observer service.

## Required installed state

Successful installation-only verification requires:

- all eight installed paths match reviewed source SHA-256 values;
- all owners and groups match the manifest;
- all modes match the manifest;
- service `LoadState=loaded`;
- service `UnitFileState=disabled`;
- service `ActiveState=inactive`;
- service `SubState=dead`;
- no timer unit exists;
- no request file was dispatched;
- no production evidence was created;
- no service action occurred;
- no production observation occurred;
- execution allowed remains false;
- mutation authority remains false.

Installation does not imply activation.

## Failure and rollback

Any failure after the first destination changes triggers rollback within the
same authorized transaction.

Rollback may:

- stop only `controlled-read-observe.service` if unexpectedly active;
- restore verified preexisting files;
- remove only files recorded as newly installed by this transaction;
- run `systemctl daemon-reload` only if the unit file changed;
- verify the service is absent or inactive, disabled, and unscheduled;
- preserve transaction, backup, rollback, and failure evidence.

Rollback must not affect unrelated paths or services.

If rollback verification fails, the transaction ends failed and requires manual
operator intervention. It must not retry installation automatically.

## Explicitly forbidden

K21D forbids:

- worker installation or self-apply;
- installation before separate authorization;
- installation from a dirty or mismatched repository;
- installation without verified backup and rollback bindings;
- arbitrary source or destination paths;
- activation or enablement;
- timer creation or scheduling;
- request dispatch;
- production observation;
- service diagnosis or remediation;
- package installation;
- network access by the observer;
- credential access;
- shell expansion from manifest data;
- widening execution allowed or mutation authority;
- automatic retry after failure;
- reuse of consumed authorization.

## Required independent review

Worker-05 must review the K21D design before any transaction schema, installer,
authorization, backup, manifest, or installation receipt is constructed.

Worker-05 must return PASS, FIX, or NO.

A PASS accepts only the design boundary. It grants no installation authority.

## Exit state for this design block

- K21D blueprint present: true
- K21D blueprint reviewed: false
- K21D transaction schema constructed: false
- K21D installer constructed: false
- K21D authorization created: false
- system-path installation authorized: false
- installation performed: false
- daemon-reload performed: false
- observer installed: false
- observer enabled: false
- observer active: false
- observer scheduled: false
- production observation authorized: false
- execution allowed: false
- mutation authority: false
~~~

## Exact repository correction

~~~diff
diff --git a/watch/observe/controlled-read-observe-install-transaction-execution-test.py b/watch/observe/controlled-read-observe-install-transaction-execution-test.py
index 6e82bef..63ce963 100755
--- a/watch/observe/controlled-read-observe-install-transaction-execution-test.py
+++ b/watch/observe/controlled-read-observe-install-transaction-execution-test.py
@@ -210,6 +210,7 @@ class Fixture:
         payload = {
             "schema": self.module.AUTH_SCHEMA,
             "authorization_id": self.authorization_id,
+            "transaction_id": self.transaction_id,
             "generated_at": (self.now - timedelta(minutes=10)).isoformat(),
             "expires_at": (self.now + timedelta(hours=2)).isoformat(),
             "authorized_by": {
@@ -451,7 +452,7 @@ def positive_install(module: Any) -> None:
         print("[PASS] positive installation confined to offline fixture")
 
         expect_denied(
-            "single-use authorization replay",
+            "same-transaction replay",
             lambda: module.execute_transaction(fixture.context(), fixture.transaction_path),
             module,
         )
@@ -459,6 +460,61 @@ def positive_install(module: Any) -> None:
         fixture.close()
 
 
+def changed_transaction_id_authorization_reuse(module: Any) -> None:
+    fixture = Fixture(module)
+    try:
+        changed_id = "INSTALL-POST239-K21D-OFFLINE0002"
+        transaction = json.loads(fixture.transaction_path.read_text(encoding="utf-8"))
+        transaction["transaction_id"] = changed_id
+        changed_path = fixture.physical(module.EVIDENCE_BASE) / f"{changed_id}.json"
+        write_json(changed_path, transaction)
+
+        try:
+            module.execute_transaction(fixture.context(), changed_path)
+        except module.ExecutionError as exc:
+            assert "authorization transaction ID mismatch" in str(exc)
+            print("[PASS] denied: authorization reuse under changed transaction ID")
+        else:
+            raise AssertionError("changed transaction ID reused one authorization")
+
+        evidence = fixture.physical(module.EVIDENCE_BASE)
+        assert not (evidence / f"{changed_id}.consumption.json").exists()
+        assert not (evidence / f"{changed_id}.receipt.json").exists()
+    finally:
+        fixture.close()
+
+
+def completed_rollback_authorization(module: Any) -> None:
+    fixture = Fixture(module)
+    try:
+        authorization = json.loads(fixture.authorization_path.read_text(encoding="utf-8"))
+        authorization["replay_control"]["rollback_completed"] = True
+        write_json(fixture.authorization_path, authorization)
+        authorization_sha = sha(fixture.authorization_path)
+
+        manifest = json.loads(fixture.manifest_path.read_text(encoding="utf-8"))
+        manifest["authorization_sha256"] = authorization_sha
+        write_json(fixture.manifest_path, manifest, 0o400)
+
+        transaction = json.loads(fixture.transaction_path.read_text(encoding="utf-8"))
+        transaction["operator_authorization"]["record_sha256"] = authorization_sha
+        transaction["backup"]["manifest_sha256"] = sha(fixture.manifest_path)
+        write_json(fixture.transaction_path, transaction)
+
+        try:
+            module.execute_transaction(fixture.context(), fixture.transaction_path)
+        except module.ExecutionError as exc:
+            assert "authorization rollback already completed" in str(exc)
+            print("[PASS] denied: authorization with completed rollback")
+        else:
+            raise AssertionError("completed rollback authorization was accepted")
+
+        assert not fixture.consumption_path().exists()
+        assert not fixture.receipt_path().exists()
+    finally:
+        fixture.close()
+
+
 def source_tamper(module: Any) -> None:
     fixture = Fixture(module)
     try:
@@ -609,6 +665,8 @@ def main() -> int:
     module = load_executor()
     module.offline_self_test()
     positive_install(module)
+    changed_transaction_id_authorization_reuse(module)
+    completed_rollback_authorization(module)
     source_tamper(module)
     backup_tamper(module)
     symlink_destination(module)
@@ -618,7 +676,7 @@ def main() -> int:
     revoked_authorization(module)
     receipt_collision(module)
     print("positive_tests=3")
-    print("negative_tests=7")
+    print("negative_tests=9")
     print("live_system_paths_touched=false")
     print("installation_performed=false")
     print("daemon_reload_performed=false")
diff --git a/watch/observe/controlled-read-observe-install-transaction-implementation-validate.py b/watch/observe/controlled-read-observe-install-transaction-implementation-validate.py
index 2b8840b..5fc2dcf 100755
--- a/watch/observe/controlled-read-observe-install-transaction-implementation-validate.py
+++ b/watch/observe/controlled-read-observe-install-transaction-implementation-validate.py
@@ -33,10 +33,10 @@ FAILURE_TEST = (
 )
 
 INSTALLER_SHA256 = (
-    "2b30248eb2d5fb4583c0b96003616e204978144f8c2651efc4e6a1804927e325"
+    "a3ff0e5af4be21b691995a2c2bbdc784a44655c47168bdf8be6351ed331e87b2"
 )
 EXECUTION_TEST_SHA256 = (
-    "6810b844fd3ebcbda8290e0cf0a224169ed479cd7577080f49cc25158336b330"
+    "7b2ff96d2f3fc2e80dd724ad8efb33a2bff0038b654c0730d8579ad45a7fd21e"
 )
 
 FILE_MAP = [
diff --git a/watch/observe/controlled-read-observe-install-transaction.py b/watch/observe/controlled-read-observe-install-transaction.py
index 4db7f36..150a6c8 100755
--- a/watch/observe/controlled-read-observe-install-transaction.py
+++ b/watch/observe/controlled-read-observe-install-transaction.py
@@ -366,6 +366,7 @@ def validate_authorization(
         {
             "schema",
             "authorization_id",
+            "transaction_id",
             "generated_at",
             "expires_at",
             "authorized_by",
@@ -385,6 +386,10 @@ def validate_authorization(
         authorization.get("authorization_id") == operator["authorization_id"],
         "authorization ID mismatch",
     )
+    require(
+        authorization.get("transaction_id") == transaction["transaction_id"],
+        "authorization transaction ID mismatch",
+    )
     require(authorization.get("status") == "AUTHORIZED_FOR_SINGLE_K21D_INSTALLATION_ONLY", "authorization status invalid")
 
     generated = parse_time(authorization.get("generated_at"), "authorization generated_at")
@@ -507,6 +512,7 @@ def validate_authorization(
     require(replay.get("single_use") is True, "authorization is not single-use")
     require(replay.get("consumed") is False, "authorization already consumed")
     require(replay.get("installation_completed") is False, "authorization already completed")
+    require(replay.get("rollback_completed") is False, "authorization rollback already completed")
 
     governance = exact_keys(
         authorization.get("governance"),
~~~

## Corrected authorization and consumption boundary

~~~python
# validate_authorization: lines 356-547
def validate_authorization(
    context: ExecutionContext,
    transaction: dict[str, Any],
    authorization_path: Path,
    authorization_sha256: str,
) -> dict[str, Any]:
    authorization = read_json(authorization_path, "installation authorization")
    require(digest_file(authorization_path) == authorization_sha256, "authorization digest mismatch")
    exact_keys(
        authorization,
        {
            "schema",
            "authorization_id",
            "transaction_id",
            "generated_at",
            "expires_at",
            "authorized_by",
            "repository",
            "correlated_reviews",
            "fixed_mappings",
            "scope",
            "replay_control",
            "governance",
            "status",
        },
        "installation authorization",
    )
    operator = transaction["operator_authorization"]
    require(authorization.get("schema") == AUTH_SCHEMA, "wrong authorization schema")
    require(
        authorization.get("authorization_id") == operator["authorization_id"],
        "authorization ID mismatch",
    )
    require(
        authorization.get("transaction_id") == transaction["transaction_id"],
        "authorization transaction ID mismatch",
    )
    require(authorization.get("status") == "AUTHORIZED_FOR_SINGLE_K21D_INSTALLATION_ONLY", "authorization status invalid")

    generated = parse_time(authorization.get("generated_at"), "authorization generated_at")
    expires = parse_time(authorization.get("expires_at"), "authorization expires_at")
    now = context.now().astimezone(timezone.utc)
    require(generated < expires, "authorization is not forward-expiring")
    require(generated <= now < expires, "authorization expired or not yet valid")
    require(parse_time(transaction["expires_at"], "transaction expires_at") <= expires, "transaction outlives authorization")

    authorized_by = exact_keys(
        authorization.get("authorized_by"),
        {"role", "identity", "authority"},
        "authorized_by",
    )
    require(authorized_by["role"] == "operator", "authorization role mismatch")
    require(isinstance(authorized_by["identity"], str) and authorized_by["identity"], "authorization identity missing")
    require(authorized_by["authority"] == "single_use_installation_only", "authorization authority mismatch")

    repository = exact_keys(
        authorization.get("repository"),
        {"host", "branch", "head", "required_clean_except_runtime_drift"},
        "authorization repository",
    )
    require(repository.get("host") == "spot-core", "authorization host mismatch")
    require(repository.get("branch") == "main", "authorization branch mismatch")
    require(repository.get("head") == transaction["repository_head"], "authorization head mismatch")
    require(repository.get("required_clean_except_runtime_drift") == RUNTIME_DRIFT, "authorization drift boundary mismatch")

    reviews = exact_keys(
        authorization.get("correlated_reviews"),
        {
            "blueprint_pass_path",
            "blueprint_pass_sha256",
            "implementation_pass_path",
            "implementation_pass_sha256",
            "mapping_correction_pass_path",
            "mapping_correction_pass_sha256",
            "live_executor_pass_path",
            "live_executor_pass_sha256",
            "worker05_verdict",
        },
        "correlated reviews",
    )
    require(reviews["worker05_verdict"] == "PASS", "Worker-05 review not PASS")
    for prefix in (
        "blueprint_pass",
        "implementation_pass",
        "mapping_correction_pass",
        "live_executor_pass",
    ):
        relative = reviews[f"{prefix}_path"]
        expected_digest = reviews[f"{prefix}_sha256"]
        require(isinstance(relative, str) and relative.startswith("watch/review/bundles/"), f"bad {prefix} path")
        review_path = (context.repository / relative).resolve()
        require(context.repository in review_path.parents, f"{prefix} path escapes repository")
        require(digest_file(review_path, prefix) == expected_digest, f"{prefix} digest mismatch")
    live_review = read_json(
        (context.repository / reviews["live_executor_pass_path"]).resolve(),
        "live executor PASS",
    )
    require(live_review.get("verdict") == "PASS", "live executor verdict not PASS")
    require(live_review.get("live_executor_accepted") is True, "live executor not accepted")
    require(live_review.get("system_path_installation_authorized") is False, "review record improperly authorizes installation")

    mappings = authorization.get("fixed_mappings")
    require(mappings == expected_mapping(transaction), "authorization mapping mismatch")

    scope = exact_keys(
        authorization.get("scope"),
        {
            "k21d_transaction_authorized",
            "backup_creation_authorized",
            "installation_manifest_creation_authorized",
            "system_path_installation_authorized",
            "installation_receipt_creation_authorized",
            "authorization_consumption_authorized",
            "daemon_reload_if_unit_changed_authorized",
            "rollback_execution_authorized",
            "rollback_stop_if_unexpected_active_authorized",
            "unconditional_daemon_reload_authorized",
            "activation_authorized",
            "enablement_authorized",
            "scheduling_authorized",
            "request_dispatch_authorized",
            "production_observation_authorized",
            "service_action_authorized",
            "remediation_authorized",
        },
        "authorization scope",
    )
    for field in (
        "k21d_transaction_authorized",
        "backup_creation_authorized",
        "installation_manifest_creation_authorized",
        "system_path_installation_authorized",
        "installation_receipt_creation_authorized",
        "authorization_consumption_authorized",
        "daemon_reload_if_unit_changed_authorized",
        "rollback_execution_authorized",
        "rollback_stop_if_unexpected_active_authorized",
    ):
        require(scope.get(field) is True, f"required authority absent: {field}")
    for field in (
        "unconditional_daemon_reload_authorized",
        "activation_authorized",
        "enablement_authorized",
        "scheduling_authorized",
        "request_dispatch_authorized",
        "production_observation_authorized",
        "service_action_authorized",
        "remediation_authorized",
    ):
        require(scope.get(field) is False, f"unsafe authority present: {field}")

    replay = exact_keys(
        authorization.get("replay_control"),
        {"single_use", "consumed", "installation_completed", "rollback_completed"},
        "replay control",
    )
    require(replay.get("single_use") is True, "authorization is not single-use")
    require(replay.get("consumed") is False, "authorization already consumed")
    require(replay.get("installation_completed") is False, "authorization already completed")
    require(replay.get("rollback_completed") is False, "authorization rollback already completed")

    governance = exact_keys(
        authorization.get("governance"),
        {
            "spot_core_sole_authority",
            "worker_self_apply_allowed",
            "live_executor_enabled",
            "execution_allowed",
            "mutation_authority",
        },
        "authorization governance",
    )
    require(governance.get("spot_core_sole_authority") is True, "Spot Core authority missing")
    for field in (
        "worker_self_apply_allowed",
        "live_executor_enabled",
        "execution_allowed",
        "mutation_authority",
    ):
        require(governance.get(field) is False, f"unsafe governance state: {field}")

    review_dir = context.repository / "watch/review/bundles"
    for revocation_path in review_dir.glob("REVOKE-POST239-K21D-INSTALLATION-*.json"):
        revocation = read_json(revocation_path, "authorization revocation")
        if (
            revocation.get("revoked_authorization_path")
            == operator["record_path"]
            or revocation.get("revoked_authorization_sha256")
            == authorization_sha256
        ):
            raise ExecutionError(f"authorization revoked: {revocation_path.name}")
    return authorization

# consumption_and_receipt_paths: lines 884-889
def consumption_and_receipt_paths(context: ExecutionContext, transaction_id: str) -> tuple[Path, Path]:
    evidence = context.absolute(EVIDENCE_BASE)
    return (
        evidence / f"{transaction_id}.consumption.json",
        evidence / f"{transaction_id}.receipt.json",
    )

# execute_transaction: lines 892-1082
def execute_transaction(context: ExecutionContext, transaction_path: Path) -> dict[str, Any]:
    context.repository = context.repository.resolve()
    transaction = read_json(transaction_path, "installation transaction")
    validator = load_transaction_validator(context.repository)
    try:
        validator.validate_transaction(transaction, context.repository, verify_references=True)
    except Exception as exc:  # validator owns its exception type
        raise ExecutionError(f"transaction validation failed: {exc}") from exc

    require(transaction.get("host") == "spot-core", "transaction host mismatch")
    require(context.hostname() == "spot-core", "wrong execution host")
    now = context.now().astimezone(timezone.utc)
    require(parse_time(transaction["generated_at"], "transaction generated_at") <= now, "transaction not yet valid")
    require(now < parse_time(transaction["expires_at"], "transaction expires_at"), "transaction expired")
    validate_repository(context, transaction["repository_head"])

    expected_transaction = context.absolute(EVIDENCE_BASE) / f"{transaction['transaction_id']}.json"
    require(transaction_path.resolve() == expected_transaction, "transaction path is not canonical")
    transaction_sha256 = digest_file(transaction_path)

    operator = transaction["operator_authorization"]
    authorization_path = context.repository / operator["record_path"]
    authorization = validate_authorization(
        context,
        transaction,
        authorization_path,
        operator["record_sha256"],
    )
    _backup_manifest, backup_entries = validate_backup(context, transaction, authorization)

    for index, item in enumerate(transaction["files"], start=1):
        source = context.repository / item["source"]
        require(digest_file(source, f"source {index}") == item["source_sha256"], f"source digest mismatch at {index}")
        destination_state(context, item, backup_entries[index - 1], index)

    consumption_path, receipt_path = consumption_and_receipt_paths(context, transaction["transaction_id"])
    require(not os.path.lexists(consumption_path), "authorization consumption record already exists")
    require(not os.path.lexists(receipt_path), "installation receipt already exists")

    request_before = snapshot_path(context.absolute(RUNTIME_REQUEST))
    evidence_before = snapshot_path(context.absolute(RUNTIME_EVIDENCE))
    services_before = running_services(context)
    service_before = assert_service_safe(context, unit_must_exist=False)

    lock_path = context.lock_path
    require(lock_path.parent.is_dir(), f"lock directory missing: {lock_path.parent}")
    lock_flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        lock_flags |= os.O_NOFOLLOW
    lock_descriptor = os.open(lock_path, lock_flags, 0o600)
    try:
        fcntl.flock(lock_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(lock_descriptor)
        raise ExecutionError("another K21D installation transaction holds the lock") from exc

    installed_indices: list[int] = []
    created_directories: list[Path] = []
    unit_changed = False
    daemon_reload_performed = False
    consumption_written = False
    try:
        require(not os.path.lexists(consumption_path), "authorization consumed while waiting for lock")
        require(not os.path.lexists(receipt_path), "receipt appeared while waiting for lock")
        consumption = {
            "schema": CONSUMPTION_SCHEMA,
            "transaction_id": transaction["transaction_id"],
            "transaction_sha256": transaction_sha256,
            "authorization_id": authorization["authorization_id"],
            "authorization_path": operator["record_path"],
            "authorization_sha256": operator["record_sha256"],
            "consumed_at": utc_text(now),
            "single_use": True,
            "consumed_before_mutation": True,
            "status": "CONSUMED_FOR_ONE_INSTALLATION_ATTEMPT",
        }
        atomic_json_exclusive(consumption_path, consumption)
        consumption_written = True

        unit_item = transaction["files"][-1]
        unit_destination = context.absolute(unit_item["destination"])
        unit_changed = (
            not unit_item["destination_preexisting"]
            or digest_file(unit_destination) != unit_item["source_sha256"]
        )

        for index, item in enumerate(transaction["files"], start=1):
            source = context.repository / item["source"]
            destination = context.absolute(item["destination"])
            atomic_install(
                context,
                source,
                destination,
                item["mode"],
                created_directories,
                item["source_sha256"],
            )
            installed_indices.append(index)
            require(digest_file(destination) == item["source_sha256"], f"immediate install verification failed at {index}")

        if unit_changed:
            run_checked(context, ["systemctl", "daemon-reload"], "conditional daemon-reload")
            daemon_reload_performed = True

        verify_installed(context, transaction)
        unit_physical = context.absolute("/etc/systemd/system/spot-controlled-read-observe.service")
        run_checked(context, ["systemd-analyze", "verify", str(unit_physical)], "unit verification")
        service_after = assert_service_safe(context, unit_must_exist=True)
        regressions = run_offline_regressions(context)
        require(snapshot_path(context.absolute(RUNTIME_REQUEST)) == request_before, "runtime request changed")
        require(snapshot_path(context.absolute(RUNTIME_EVIDENCE)) == evidence_before, "runtime observation evidence changed")
        require(running_services(context) == services_before, "unrelated running-service state changed")

        receipt = {
            "schema": RECEIPT_SCHEMA,
            "transaction_id": transaction["transaction_id"],
            "transaction_sha256": transaction_sha256,
            "authorization_id": authorization["authorization_id"],
            "authorization_sha256": operator["record_sha256"],
            "backup_manifest_id": transaction["backup"]["manifest_id"],
            "backup_manifest_sha256": transaction["backup"]["manifest_sha256"],
            "backup_binding_id": transaction["backup"]["binding_id"],
            "rollback_binding_id": transaction["rollback"]["binding_id"],
            "repository_head": transaction["repository_head"],
            "completed_at": utc_text(context.now()),
            "installed_files": [
                {
                    "destination": item["destination"],
                    "sha256": item["source_sha256"],
                    "mode": item["mode"],
                    "owner": "root",
                    "group": "root",
                }
                for item in transaction["files"]
            ],
            "service_state_before": service_before,
            "service_state_after": service_after,
            "unit_changed": unit_changed,
            "daemon_reload_performed": daemon_reload_performed,
            "offline_regressions": regressions,
            "request_state_unchanged": True,
            "runtime_evidence_unchanged": True,
            "unrelated_running_services_unchanged": True,
            "activation_performed": False,
            "enablement_performed": False,
            "scheduling_performed": False,
            "production_observation_performed": False,
            "execution_allowed": False,
            "mutation_authority": False,
            "outcome": "INSTALLED_DORMANT",
        }
        atomic_json_exclusive(receipt_path, receipt)
        return receipt
    except (OSError, ExecutionError) as exc:
        rollback = rollback_installation(
            context,
            transaction,
            authorization,
            backup_entries,
            installed_indices,
            created_directories,
            unit_changed and bool(installed_indices),
        ) if installed_indices else {"restored": [], "failures": [], "succeeded": True}
        failure_receipt = {
            "schema": RECEIPT_SCHEMA,
            "transaction_id": transaction["transaction_id"],
            "transaction_sha256": transaction_sha256,
            "authorization_id": authorization["authorization_id"],
            "authorization_sha256": operator["record_sha256"],
            "failed_at": utc_text(context.now()),
            "failure": str(exc),
            "authorization_consumed": consumption_written,
            "rollback": rollback,
            "daemon_reload_performed_before_failure": daemon_reload_performed,
            "activation_performed": False,
            "enablement_performed": False,
            "scheduling_performed": False,
            "production_observation_performed": False,
            "execution_allowed": False,
            "mutation_authority": False,
            "outcome": "ROLLED_BACK" if rollback["succeeded"] else "ROLLBACK_FAILED",
        }
        if consumption_written and not os.path.lexists(receipt_path):
            try:
                atomic_json_exclusive(receipt_path, failure_receipt)
            except (OSError, ExecutionError) as journal_exc:
                raise ExecutionError(f"{exc}; rollback={rollback}; receipt failure={journal_exc}") from journal_exc
        raise ExecutionError(f"{exc}; rollback_succeeded={rollback['succeeded']}") from exc
    finally:
        fcntl.flock(lock_descriptor, fcntl.LOCK_UN)
        os.close(lock_descriptor)

~~~

## Complete corrected execution-test source

~~~python
#!/usr/bin/env python3
"""Offline execution and rollback tests for the K21D live executor."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
EXECUTOR = HERE / "controlled-read-observe-install-transaction.py"
VALIDATOR = HERE / "controlled-read-observe-install-transaction-validate.py"


def load_executor() -> Any:
    spec = importlib.util.spec_from_file_location("k21d_executor", EXECUTOR)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load executor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha(path: Path) -> str:
    value = hashlib.sha256()
    value.update(path.read_bytes())
    return value.hexdigest()


def write_json(path: Path, payload: dict[str, Any], mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(mode)


@dataclass
class FakeCommands:
    module: Any
    fail_verify_once: bool = False
    calls: list[tuple[str, ...]] = field(default_factory=list)

    def __call__(self, arguments: Sequence[str], cwd: Path | None) -> Any:
        command = tuple(arguments)
        self.calls.append(command)
        if command[:2] == ("systemctl", "is-active"):
            return self.module.CommandResult(3, "inactive\n", "")
        if command[:2] == ("systemctl", "is-enabled"):
            return self.module.CommandResult(1, "disabled\n", "")
        if command[:2] == ("systemctl", "show"):
            return self.module.CommandResult(0, "0\n", "")
        if command[:2] == ("systemctl", "list-unit-files"):
            return self.module.CommandResult(0, "", "")
        if command[:2] == ("systemctl", "list-units"):
            return self.module.CommandResult(
                0,
                "ssh.service loaded active running OpenSSH server\n",
                "",
            )
        if command == ("systemctl", "daemon-reload"):
            return self.module.CommandResult(0, "", "")
        if command[:2] == ("systemd-analyze", "verify"):
            if self.fail_verify_once:
                self.fail_verify_once = False
                return self.module.CommandResult(1, "", "injected unit verification failure")
            return self.module.CommandResult(0, "", "")
        if command and command[0] == "python3":
            return self.module.CommandResult(0, "offline PASS\n", "")
        return self.module.CommandResult(1, "", f"unexpected command: {command}")

    def count(self, *command: str) -> int:
        return sum(item == tuple(command) for item in self.calls)


class Fixture:
    def __init__(self, module: Any, *, preexisting: set[int] | None = None) -> None:
        self.module = module
        self.temp = tempfile.TemporaryDirectory(prefix="spot-k21d-live-executor-")
        self.base = Path(self.temp.name)
        self.repository = self.base / "repository"
        self.system_root = self.base / "system-root"
        self.now = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)
        self.head = "a" * 40
        self.transaction_id = "INSTALL-POST239-K21D-OFFLINE0001"
        self.authorization_id = "AUTH-POST239-K21D-INSTALLATION-OFFLINE0001"
        self.backup_id = "BACKUP-POST239-K21D-OFFLINE0001"
        self.backup_binding = "BACKUP-BINDING-POST239-K21D-OFFLINE0001"
        self.rollback_binding = "ROLLBACK-BINDING-POST239-K21D-OFFLINE0001"
        self.preexisting = preexisting or set()
        self.command_runner = FakeCommands(module)

        (self.repository / "watch/observe").mkdir(parents=True)
        (self.repository / "watch/review/bundles").mkdir(parents=True)
        for base in (
            "/usr/local/lib/spot",
            "/etc/spot",
            "/etc/systemd/system",
            "/usr/lib/systemd/system",
            "/lib/systemd/system",
            "/run/lock",
            "/mnt/collective/logs/spot/actions/post239-k21d",
            "/mnt/collective/backups/spot-core/post239-k21d",
        ):
            self.physical(base).mkdir(parents=True, exist_ok=True)
            self.physical(base).chmod(0o755)

        shutil.copy2(VALIDATOR, self.repository / self.module.TRANSACTION_VALIDATOR)
        self._create_sources()
        self._create_references()
        self._create_destinations()
        self._create_authorization()
        self._create_backup_and_transaction()

    def close(self) -> None:
        self.temp.cleanup()

    def physical(self, absolute: str | Path) -> Path:
        return self.system_root / str(absolute).lstrip("/")

    def _create_sources(self) -> None:
        for index, (source, _destination, mode) in enumerate(self.module.FILE_MAP, start=1):
            path = self.repository / source
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"K21D fixture source {index}\n".encode())
            path.chmod(int(mode, 8) if index != 2 else 0o644)
        for name in (
            "controlled_read_observe_validation_v1.py",
            "controlled-read-observe-replay-bounds-validate.py",
            "controlled-read-observe-install-validate.py",
            "controlled-read-observe-install-transaction-failure-test.py",
        ):
            path = self.repository / "watch/observe" / name
            if not path.exists():
                path.write_text("raise SystemExit(0)\n", encoding="utf-8")

    def _create_references(self) -> None:
        self.review_rel = Path(
            "watch/review/bundles/POST239-K21D-BLUEPRINT-PASS-20260828T150447Z.json"
        )
        write_json(self.repository / self.review_rel, {"review": {"verdict": "PASS"}})
        self.implementation_rel = Path(
            "watch/review/bundles/POST239-K21D-IMPLEMENTATION-PASS-20260828T222053Z.json"
        )
        self.mapping_rel = Path(
            "watch/review/bundles/POST239-K21D-MAPPING-CORRECTION-PASS-20260829T162201Z.json"
        )
        self.live_rel = Path(
            "watch/review/bundles/POST239-K21D-LIVE-EXECUTOR-PASS-OFFLINE0001.json"
        )
        write_json(self.repository / self.implementation_rel, {"verdict": "PASS"})
        write_json(self.repository / self.mapping_rel, {"verdict": "PASS"})
        write_json(
            self.repository / self.live_rel,
            {
                "verdict": "PASS",
                "live_executor_accepted": True,
                "system_path_installation_authorized": False,
            },
        )
        self.rollback_rel = Path("watch/observe/controlled-read-observe-install-rollback.md")
        rollback = self.repository / self.rollback_rel
        rollback.write_text("K21D fixed eight-file rollback fixture\n", encoding="utf-8")
        rollback.chmod(0o600)

    def _create_destinations(self) -> None:
        self.original: dict[int, bytes] = {}
        for index, (_source, destination, mode) in enumerate(self.module.FILE_MAP, start=1):
            if index not in self.preexisting:
                continue
            physical = self.physical(destination)
            physical.parent.mkdir(parents=True, exist_ok=True)
            content = f"preexisting destination {index}\n".encode()
            physical.write_bytes(content)
            physical.chmod(int(mode, 8))
            self.original[index] = content

    def _mapping_records(self) -> list[dict[str, Any]]:
        result = []
        for source, destination, mode in self.module.FILE_MAP:
            result.append(
                {
                    "source": source,
                    "source_sha256": sha(self.repository / source),
                    "destination": destination,
                    "mode": mode,
                    "owner": "root",
                    "group": "root",
                }
            )
        return result

    def _create_authorization(self) -> None:
        self.authorization_rel = Path(
            f"watch/review/bundles/{self.authorization_id}.json"
        )
        self.authorization_path = self.repository / self.authorization_rel
        payload = {
            "schema": self.module.AUTH_SCHEMA,
            "authorization_id": self.authorization_id,
            "transaction_id": self.transaction_id,
            "generated_at": (self.now - timedelta(minutes=10)).isoformat(),
            "expires_at": (self.now + timedelta(hours=2)).isoformat(),
            "authorized_by": {
                "role": "operator",
                "identity": "offline-fixture",
                "authority": "single_use_installation_only",
            },
            "repository": {
                "host": "spot-core",
                "branch": "main",
                "head": self.head,
                "required_clean_except_runtime_drift": self.module.RUNTIME_DRIFT,
            },
            "correlated_reviews": {
                "blueprint_pass_path": str(self.review_rel),
                "blueprint_pass_sha256": sha(self.repository / self.review_rel),
                "implementation_pass_path": str(self.implementation_rel),
                "implementation_pass_sha256": sha(self.repository / self.implementation_rel),
                "mapping_correction_pass_path": str(self.mapping_rel),
                "mapping_correction_pass_sha256": sha(self.repository / self.mapping_rel),
                "live_executor_pass_path": str(self.live_rel),
                "live_executor_pass_sha256": sha(self.repository / self.live_rel),
                "worker05_verdict": "PASS",
            },
            "fixed_mappings": self._mapping_records(),
            "scope": {
                "k21d_transaction_authorized": True,
                "backup_creation_authorized": True,
                "installation_manifest_creation_authorized": True,
                "system_path_installation_authorized": True,
                "installation_receipt_creation_authorized": True,
                "authorization_consumption_authorized": True,
                "daemon_reload_if_unit_changed_authorized": True,
                "rollback_execution_authorized": True,
                "rollback_stop_if_unexpected_active_authorized": True,
                "unconditional_daemon_reload_authorized": False,
                "activation_authorized": False,
                "enablement_authorized": False,
                "scheduling_authorized": False,
                "request_dispatch_authorized": False,
                "production_observation_authorized": False,
                "service_action_authorized": False,
                "remediation_authorized": False,
            },
            "replay_control": {
                "single_use": True,
                "consumed": False,
                "installation_completed": False,
                "rollback_completed": False,
            },
            "governance": {
                "spot_core_sole_authority": True,
                "worker_self_apply_allowed": False,
                "live_executor_enabled": False,
                "execution_allowed": False,
                "mutation_authority": False,
            },
            "status": "AUTHORIZED_FOR_SINGLE_K21D_INSTALLATION_ONLY",
        }
        write_json(self.authorization_path, payload)

    def _create_backup_and_transaction(self) -> None:
        files = []
        backup_files = []
        backup_live_dir = self.module.BACKUP_BASE / f"{self.backup_id}-files"
        backup_physical_dir = self.physical(backup_live_dir)
        backup_physical_dir.mkdir(parents=True, exist_ok=True)
        backup_physical_dir.chmod(0o700)
        for index, (source, destination, mode) in enumerate(self.module.FILE_MAP, start=1):
            source_sha = sha(self.repository / source)
            if index in self.preexisting:
                backup_live = backup_live_dir / f"{index:02d}-{Path(destination).name}.backup"
                backup_physical = self.physical(backup_live)
                if backup_physical.exists():
                    backup_physical.unlink()
                backup_physical.write_bytes(self.original[index])
                backup_physical.chmod(0o400)
                backup_sha: str | None = sha(backup_physical)
                backup_path: str | None = str(backup_live)
                preexisting = True
                before_type = "regular"
                destination_info = self.physical(destination).stat()
                mode_before: str | None = f"{stat.S_IMODE(destination_info.st_mode):04o}"
                uid_before: int | None = destination_info.st_uid
                gid_before: int | None = destination_info.st_gid
            else:
                backup_sha = None
                backup_path = None
                preexisting = False
                before_type = "absent"
                mode_before = None
                uid_before = None
                gid_before = None
            files.append(
                {
                    "source": source,
                    "destination": destination,
                    "source_sha256": source_sha,
                    "mode": mode,
                    "owner": "root",
                    "group": "root",
                    "destination_preexisting": preexisting,
                    "destination_type_before": before_type,
                    "backup_sha256": backup_sha,
                }
            )
            backup_files.append(
                {
                    "source": source,
                    "destination": destination,
                    "destination_preexisting": preexisting,
                    "destination_type_before": before_type,
                    "backup_path": backup_path,
                    "backup_sha256": backup_sha,
                    "mode_before": mode_before,
                    "uid_before": uid_before,
                    "gid_before": gid_before,
                }
            )

        manifest = {
            "schema": self.module.BACKUP_SCHEMA,
            "manifest_id": self.backup_id,
            "generated_at": (self.now - timedelta(minutes=5)).isoformat(),
            "host": "spot-core",
            "repository_head": self.head,
            "authorization_id": self.authorization_id,
            "authorization_sha256": sha(self.authorization_path),
            "binding_id": self.backup_binding,
            "files": backup_files,
            "verified": True,
            "status": "VERIFIED_PREINSTALL_BACKUP",
        }
        self.manifest_live = self.module.BACKUP_BASE / f"{self.backup_id}.json"
        self.manifest_path = self.physical(self.manifest_live)
        write_json(self.manifest_path, manifest, 0o400)

        transaction = {
            "schema": "starfleet.post239.k21d_install_transaction.v1",
            "transaction_id": self.transaction_id,
            "generated_at": (self.now - timedelta(minutes=4)).isoformat(),
            "expires_at": (self.now + timedelta(hours=1)).isoformat(),
            "host": "spot-core",
            "repository_head": self.head,
            "design_review": {
                "record_path": str(self.review_rel),
                "record_sha256": sha(self.repository / self.review_rel),
                "verdict": "PASS",
            },
            "operator_authorization": {
                "authorization_id": self.authorization_id,
                "record_path": str(self.authorization_rel),
                "record_sha256": sha(self.authorization_path),
                "system_path_installation_authorized": True,
                "single_use": True,
                "consumed": False,
            },
            "backup": {
                "manifest_id": self.backup_id,
                "manifest_path": str(self.manifest_live),
                "manifest_sha256": sha(self.manifest_path),
                "binding_id": self.backup_binding,
                "verified": True,
            },
            "rollback": {
                "document_path": str(self.rollback_rel),
                "document_sha256": sha(self.repository / self.rollback_rel),
                "binding_id": self.rollback_binding,
                "verified": True,
            },
            "files": files,
            "planned_service_state": {
                "daemon_reload_if_unit_changed": True,
                "unconditional_daemon_reload": False,
                "service_start_planned": False,
                "service_enablement_planned": False,
                "timer_installation_planned": False,
                "request_dispatch_planned": False,
                "production_observation_planned": False,
            },
            "governance": {
                "spot_core_sole_authority": True,
                "worker_self_apply_allowed": False,
                "activation_authorized": False,
                "enablement_authorized": False,
                "scheduling_authorized": False,
                "production_observation_authorized": False,
                "service_action_authorized": False,
                "live_executor_enabled": False,
                "execution_allowed": False,
                "mutation_authority": False,
            },
            "status": "READY_FOR_SEPARATELY_AUTHORIZED_INSTALLATION_ONLY",
        }
        self.transaction_path = self.physical(self.module.EVIDENCE_BASE) / f"{self.transaction_id}.json"
        write_json(self.transaction_path, transaction)

    def context(self) -> Any:
        return self.module.ExecutionContext(
            repository=self.repository,
            system_root=self.system_root,
            lock_path=self.physical(self.module.LOCK_PATH),
            command_runner=self.command_runner,
            now=lambda: self.now,
            hostname=lambda: "spot-core",
            live=False,
        )

    def receipt_path(self) -> Path:
        return self.physical(self.module.EVIDENCE_BASE) / f"{self.transaction_id}.receipt.json"

    def consumption_path(self) -> Path:
        return self.physical(self.module.EVIDENCE_BASE) / f"{self.transaction_id}.consumption.json"


def expect_denied(label: str, action: Any, module: Any) -> None:
    try:
        action()
    except module.ExecutionError:
        print(f"[PASS] denied: {label}")
        return
    raise AssertionError(f"unsafe case accepted: {label}")


def positive_install(module: Any) -> None:
    fixture = Fixture(module)
    try:
        receipt = module.execute_transaction(fixture.context(), fixture.transaction_path)
        assert receipt["outcome"] == "INSTALLED_DORMANT"
        assert fixture.consumption_path().is_file()
        assert fixture.receipt_path().is_file()
        for source, destination, mode in module.FILE_MAP:
            installed = fixture.physical(destination)
            assert sha(installed) == sha(fixture.repository / source)
            assert stat.S_IMODE(installed.stat().st_mode) == int(mode, 8)
        assert fixture.command_runner.count("systemctl", "daemon-reload") == 1
        forbidden = {"start", "enable", "restart", "try-restart"}
        assert not any(len(call) > 1 and call[0] == "systemctl" and call[1] in forbidden for call in fixture.command_runner.calls)
        print("[PASS] positive installation confined to offline fixture")

        expect_denied(
            "same-transaction replay",
            lambda: module.execute_transaction(fixture.context(), fixture.transaction_path),
            module,
        )
    finally:
        fixture.close()


def changed_transaction_id_authorization_reuse(module: Any) -> None:
    fixture = Fixture(module)
    try:
        changed_id = "INSTALL-POST239-K21D-OFFLINE0002"
        transaction = json.loads(fixture.transaction_path.read_text(encoding="utf-8"))
        transaction["transaction_id"] = changed_id
        changed_path = fixture.physical(module.EVIDENCE_BASE) / f"{changed_id}.json"
        write_json(changed_path, transaction)

        try:
            module.execute_transaction(fixture.context(), changed_path)
        except module.ExecutionError as exc:
            assert "authorization transaction ID mismatch" in str(exc)
            print("[PASS] denied: authorization reuse under changed transaction ID")
        else:
            raise AssertionError("changed transaction ID reused one authorization")

        evidence = fixture.physical(module.EVIDENCE_BASE)
        assert not (evidence / f"{changed_id}.consumption.json").exists()
        assert not (evidence / f"{changed_id}.receipt.json").exists()
    finally:
        fixture.close()


def completed_rollback_authorization(module: Any) -> None:
    fixture = Fixture(module)
    try:
        authorization = json.loads(fixture.authorization_path.read_text(encoding="utf-8"))
        authorization["replay_control"]["rollback_completed"] = True
        write_json(fixture.authorization_path, authorization)
        authorization_sha = sha(fixture.authorization_path)

        manifest = json.loads(fixture.manifest_path.read_text(encoding="utf-8"))
        manifest["authorization_sha256"] = authorization_sha
        write_json(fixture.manifest_path, manifest, 0o400)

        transaction = json.loads(fixture.transaction_path.read_text(encoding="utf-8"))
        transaction["operator_authorization"]["record_sha256"] = authorization_sha
        transaction["backup"]["manifest_sha256"] = sha(fixture.manifest_path)
        write_json(fixture.transaction_path, transaction)

        try:
            module.execute_transaction(fixture.context(), fixture.transaction_path)
        except module.ExecutionError as exc:
            assert "authorization rollback already completed" in str(exc)
            print("[PASS] denied: authorization with completed rollback")
        else:
            raise AssertionError("completed rollback authorization was accepted")

        assert not fixture.consumption_path().exists()
        assert not fixture.receipt_path().exists()
    finally:
        fixture.close()


def source_tamper(module: Any) -> None:
    fixture = Fixture(module)
    try:
        source = fixture.repository / module.FILE_MAP[0][0]
        source.write_text("tampered\n", encoding="utf-8")
        expect_denied(
            "source digest tamper",
            lambda: module.execute_transaction(fixture.context(), fixture.transaction_path),
            module,
        )
        assert not fixture.consumption_path().exists()
    finally:
        fixture.close()


def backup_tamper(module: Any) -> None:
    fixture = Fixture(module, preexisting={1})
    try:
        manifest = json.loads(fixture.manifest_path.read_text(encoding="utf-8"))
        backup_path = fixture.physical(manifest["files"][0]["backup_path"])
        backup_path.chmod(0o600)
        backup_path.write_text("tampered backup\n", encoding="utf-8")
        expect_denied(
            "backup content tamper",
            lambda: module.execute_transaction(fixture.context(), fixture.transaction_path),
            module,
        )
        assert fixture.physical(module.FILE_MAP[0][1]).read_bytes() == fixture.original[1]
        assert not fixture.consumption_path().exists()
    finally:
        fixture.close()


def symlink_destination(module: Any) -> None:
    fixture = Fixture(module)
    try:
        target = fixture.base / "outside-target"
        target.write_text("do not alter\n", encoding="utf-8")
        destination = fixture.physical(module.FILE_MAP[0][1])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(target)
        expect_denied(
            "destination symlink",
            lambda: module.execute_transaction(fixture.context(), fixture.transaction_path),
            module,
        )
        assert target.read_text(encoding="utf-8") == "do not alter\n"
        assert not fixture.consumption_path().exists()
    finally:
        fixture.close()


def rollback_after_failure(module: Any) -> None:
    fixture = Fixture(module, preexisting={1, 8})
    try:
        fixture.command_runner.fail_verify_once = True
        expect_denied(
            "post-install failure triggers rollback",
            lambda: module.execute_transaction(fixture.context(), fixture.transaction_path),
            module,
        )
        for index, (_source, destination, _mode) in enumerate(module.FILE_MAP, start=1):
            physical = fixture.physical(destination)
            if index in fixture.preexisting:
                assert physical.read_bytes() == fixture.original[index]
            else:
                assert not os.path.lexists(physical)
        receipt = json.loads(fixture.receipt_path().read_text(encoding="utf-8"))
        assert receipt["outcome"] == "ROLLED_BACK"
        assert receipt["rollback"]["succeeded"] is True
        assert fixture.consumption_path().is_file()
        assert fixture.command_runner.count("systemctl", "daemon-reload") == 2
        print("[PASS] verified rollback restores exact pre-install state")
    finally:
        fixture.close()


def unchanged_unit_no_reload(module: Any) -> None:
    fixture = Fixture(module, preexisting={8})
    try:
        unit_source = fixture.repository / module.FILE_MAP[7][0]
        unit_destination = fixture.physical(module.FILE_MAP[7][1])
        unit_destination.write_bytes(unit_source.read_bytes())
        unit_destination.chmod(0o644)
        fixture.original[8] = unit_source.read_bytes()
        fixture._create_backup_and_transaction()
        module.execute_transaction(fixture.context(), fixture.transaction_path)
        assert fixture.command_runner.count("systemctl", "daemon-reload") == 0
        print("[PASS] daemon-reload omitted when unit content is unchanged")
    finally:
        fixture.close()


def expired_authorization(module: Any) -> None:
    fixture = Fixture(module)
    try:
        authorization = json.loads(fixture.authorization_path.read_text(encoding="utf-8"))
        authorization["expires_at"] = (fixture.now - timedelta(seconds=1)).isoformat()
        write_json(fixture.authorization_path, authorization)
        transaction = json.loads(fixture.transaction_path.read_text(encoding="utf-8"))
        transaction["operator_authorization"]["record_sha256"] = sha(fixture.authorization_path)
        transaction["expires_at"] = (fixture.now - timedelta(seconds=1)).isoformat()
        write_json(fixture.transaction_path, transaction)
        expect_denied(
            "expired authorization",
            lambda: module.execute_transaction(fixture.context(), fixture.transaction_path),
            module,
        )
    finally:
        fixture.close()


def revoked_authorization(module: Any) -> None:
    fixture = Fixture(module)
    try:
        revocation = {
            "schema": "starfleet.post239.k21d_installation_authorization_revocation.v1",
            "revoked_authorization_path": str(fixture.authorization_rel),
            "revoked_authorization_sha256": sha(fixture.authorization_path),
            "status": "REVOKED_BEFORE_USE",
        }
        path = fixture.repository / "watch/review/bundles/REVOKE-POST239-K21D-INSTALLATION-OFFLINE0001.json"
        write_json(path, revocation)
        expect_denied(
            "revoked authorization",
            lambda: module.execute_transaction(fixture.context(), fixture.transaction_path),
            module,
        )
    finally:
        fixture.close()


def receipt_collision(module: Any) -> None:
    fixture = Fixture(module)
    try:
        fixture.receipt_path().write_text("existing immutable receipt\n", encoding="utf-8")
        expect_denied(
            "receipt collision",
            lambda: module.execute_transaction(fixture.context(), fixture.transaction_path),
            module,
        )
        assert not fixture.consumption_path().exists()
    finally:
        fixture.close()


def main() -> int:
    module = load_executor()
    module.offline_self_test()
    positive_install(module)
    changed_transaction_id_authorization_reuse(module)
    completed_rollback_authorization(module)
    source_tamper(module)
    backup_tamper(module)
    symlink_destination(module)
    rollback_after_failure(module)
    unchanged_unit_no_reload(module)
    expired_authorization(module)
    revoked_authorization(module)
    receipt_collision(module)
    print("positive_tests=3")
    print("negative_tests=9")
    print("live_system_paths_touched=false")
    print("installation_performed=false")
    print("daemon_reload_performed=false")
    print("activation_authorized=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    print("RESULT: POST-2.39 K21D LIVE EXECUTOR OFFLINE TEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
~~~

## Hash-pinned implementation-validator source

~~~python
#!/usr/bin/env python3
"""Offline integration validation for the reviewed K21D live executor candidate.

This validator never invokes the executor's live ``--execute`` path. It checks
the hash-pinned repository candidate, runs its static self-test, and runs the
disposable execution and transaction-contract regression suites.
"""

from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


SCRIPT = Path(__file__).resolve()
REPOSITORY = SCRIPT.parents[2]
OBSERVE = REPOSITORY / "watch" / "observe"

INSTALLER = OBSERVE / "controlled-read-observe-install-transaction.py"
EXECUTION_TEST = (
    OBSERVE / "controlled-read-observe-install-transaction-execution-test.py"
)
TRANSACTION_VALIDATOR = (
    OBSERVE / "controlled-read-observe-install-transaction-validate.py"
)
FAILURE_TEST = (
    OBSERVE / "controlled-read-observe-install-transaction-failure-test.py"
)

INSTALLER_SHA256 = (
    "a3ff0e5af4be21b691995a2c2bbdc784a44655c47168bdf8be6351ed331e87b2"
)
EXECUTION_TEST_SHA256 = (
    "7b2ff96d2f3fc2e80dd724ad8efb33a2bff0038b654c0730d8579ad45a7fd21e"
)

FILE_MAP = [
    (
        "watch/observe/controlled-read-observe.py",
        "/usr/local/lib/spot/observe/controlled-read-observe.py",
        "0755",
    ),
    (
        "watch/observe/controlled_read_observe_validation_v1.py",
        "/usr/local/lib/spot/observe/controlled_read_observe_validation_v1.py",
        "0755",
    ),
    (
        "watch/observe/controlled-read-observe-request-validate.py",
        "/usr/local/lib/spot/observe/controlled-read-observe-request-validate.py",
        "0755",
    ),
    (
        "watch/observe/controlled-read-observe-evidence-validate.py",
        "/usr/local/lib/spot/observe/controlled-read-observe-evidence-validate.py",
        "0755",
    ),
    (
        "watch/observe/controlled-read-observe-allowlist-v1.json",
        "/etc/spot/observe/controlled-read-observe-allowlist-v1.json",
        "0644",
    ),
    (
        "watch/observe/controlled-read-observe-request-schema-v1.json",
        "/etc/spot/observe/controlled-read-observe-request-schema-v1.json",
        "0644",
    ),
    (
        "watch/observe/controlled-read-observe-evidence-schema-v1.json",
        "/etc/spot/observe/controlled-read-observe-evidence-schema-v1.json",
        "0644",
    ),
    (
        "watch/observe/controlled-read-observe.service",
        "/etc/systemd/system/spot-controlled-read-observe.service",
        "0644",
    ),
]

LIVE_PATHS = tuple(Path(entry[1]) for entry in FILE_MAP)


class ValidationError(RuntimeError):
    """Fail-closed validation error."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def assignment(tree: ast.Module, name: str) -> Any:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets
            ):
                return ast.literal_eval(node.value)
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            return ast.literal_eval(node.value)
    raise ValidationError(f"{name} assignment absent")


def normalize_mapping(value: Any, label: str) -> list[tuple[str, str, str]]:
    require(isinstance(value, (list, tuple)), f"{label} must be ordered")
    normalized: list[tuple[str, str, str]] = []
    for entry in value:
        require(
            isinstance(entry, (list, tuple)) and len(entry) == 3,
            f"{label} entry malformed",
        )
        source, destination, mode = entry
        require(
            all(isinstance(item, str) for item in entry),
            f"{label} entry must contain strings",
        )
        normalized.append((source, destination, mode))
    return normalized


def assert_no_live_paths() -> None:
    for path in LIVE_PATHS:
        require(
            not path.exists() and not path.is_symlink(),
            f"live path unexpectedly present: {path}",
        )


def run(command: list[str], label: str, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command,
        cwd=REPOSITORY,
        env=environment,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    require(result.returncode == 0, f"{label} failed:\n{result.stdout}{result.stderr}")
    return result


def repository_status() -> str:
    result = run(
        ["git", "status", "--porcelain=v1", "-uall"],
        "repository status",
        timeout=30,
    )
    return result.stdout


def validate_static_contract() -> None:
    required_files = (
        INSTALLER,
        EXECUTION_TEST,
        TRANSACTION_VALIDATOR,
        FAILURE_TEST,
    )
    for path in required_files:
        require(path.is_file(), f"required file absent: {path}")
        require(not path.is_symlink(), f"required file is symlink: {path}")

    require(digest(INSTALLER) == INSTALLER_SHA256, "live executor digest mismatch")
    require(
        digest(EXECUTION_TEST) == EXECUTION_TEST_SHA256,
        "execution-test digest mismatch",
    )

    installer_source = INSTALLER.read_text(encoding="utf-8")
    validator_source = TRANSACTION_VALIDATOR.read_text(encoding="utf-8")
    installer_tree = ast.parse(installer_source, filename=str(INSTALLER))
    validator_tree = ast.parse(validator_source, filename=str(TRANSACTION_VALIDATOR))

    installer_map = normalize_mapping(
        assignment(installer_tree, "FILE_MAP"),
        "executor FILE_MAP",
    )
    validator_map = normalize_mapping(
        assignment(validator_tree, "FILE_MAP"),
        "transaction-validator FILE_MAP",
    )
    require(installer_map == FILE_MAP, "executor mapping differs from K21C/K21D")
    require(validator_map == FILE_MAP, "validator mapping differs from K21C/K21D")

    constants = {
        node.value
        for node in ast.walk(installer_tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    require("--offline-self-test" in constants, "offline self-test option absent")
    require("--execute" in constants, "live execute option absent")

    for stale in (
        "This artifact cannot install files",
        "installation execution is not implemented or authorized",
        "K21D installer is dormant",
    ):
        require(stale not in installer_source, f"stale dormant control present: {stale}")

    imported_roots: set[str] = set()
    for node in ast.walk(installer_tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    require(
        imported_roots.isdisjoint({"requests", "httpx", "urllib"}),
        "network client imported by executor",
    )

    for node in ast.walk(installer_tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            require(node.func.id not in {"eval", "exec"}, "dynamic execution API present")
        if isinstance(node.func, ast.Attribute):
            require(
                not (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "os"
                    and node.func.attr in {"system", "popen"}
                ),
                "shell execution API present",
            )
        for keyword in node.keywords:
            if keyword.arg == "shell":
                require(
                    not (
                        isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is True
                    ),
                    "shell=True present",
                )


def main() -> int:
    try:
        assert_no_live_paths()
        status_before = repository_status()

        validate_static_contract()
        print("[PASS] hash-pinned live executor and exact mapping")

        self_test = run(
            [sys.executable, str(INSTALLER), "--offline-self-test"],
            "executor static self-test",
        )
        require(
            "[PASS] K21D live executor static self-test" in self_test.stdout,
            "unexpected executor self-test result",
        )
        print("[PASS] live executor static self-test")

        execution = run(
            [sys.executable, str(EXECUTION_TEST)],
            "disposable execution tests",
            timeout=600,
        )
        require(
            "RESULT: POST-2.39 K21D LIVE EXECUTOR OFFLINE TEST PASS"
            in execution.stdout,
            "execution-test PASS marker absent",
        )
        print("[PASS] disposable execution and rollback tests")

        contract = run(
            [sys.executable, str(FAILURE_TEST)],
            "transaction-contract regression",
            timeout=600,
        )
        require(
            "RESULT: POST-2.39 K21D FAILURE TEST PASS" in contract.stdout,
            "transaction-contract PASS marker absent",
        )
        print("[PASS] transaction-contract regression")

        assert_no_live_paths()
        require(repository_status() == status_before, "repository changed during validation")
        print("[PASS] live paths absent and repository unchanged")

    except (OSError, SyntaxError, ValueError, ValidationError, subprocess.TimeoutExpired) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        print("installation_performed=false", file=sys.stderr)
        print("daemon_reload_performed=false", file=sys.stderr)
        print("activation_authorized=false", file=sys.stderr)
        print("execution_allowed=false", file=sys.stderr)
        print("mutation_authority=false", file=sys.stderr)
        return 1

    print("pass=5 fail=0")
    print("system_path_installation_authorized=false")
    print("backup_created=false")
    print("installation_manifest_created=false")
    print("authorization_consumed=false")
    print("installation_performed=false")
    print("daemon_reload_performed=false")
    print("activation_authorized=false")
    print("scheduling_authorized=false")
    print("production_observation_authorized=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    print("RESULT: POST-2.39 K21D LIVE IMPLEMENTATION VALIDATION PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
~~~

## Fresh live-implementation validation

~~~text
[PASS] hash-pinned live executor and exact mapping
[PASS] live executor static self-test
[PASS] disposable execution and rollback tests
[PASS] transaction-contract regression
[PASS] live paths absent and repository unchanged
pass=5 fail=0
system_path_installation_authorized=false
backup_created=false
installation_manifest_created=false
authorization_consumed=false
installation_performed=false
daemon_reload_performed=false
activation_authorized=false
scheduling_authorized=false
production_observation_authorized=false
execution_allowed=false
mutation_authority=false
RESULT: POST-2.39 K21D LIVE IMPLEMENTATION VALIDATION PASS
~~~

## Fresh disposable execution tests

~~~text
[PASS] positive installation confined to offline fixture
[PASS] denied: same-transaction replay
[PASS] denied: authorization reuse under changed transaction ID
[PASS] denied: authorization with completed rollback
[PASS] denied: source digest tamper
[PASS] denied: backup content tamper
[PASS] denied: destination symlink
[PASS] denied: post-install failure triggers rollback
[PASS] verified rollback restores exact pre-install state
[PASS] daemon-reload omitted when unit content is unchanged
[PASS] denied: expired authorization
[PASS] denied: revoked authorization
[PASS] denied: receipt collision
positive_tests=3
negative_tests=9
live_system_paths_touched=false
installation_performed=false
daemon_reload_performed=false
activation_authorized=false
execution_allowed=false
mutation_authority=false
RESULT: POST-2.39 K21D LIVE EXECUTOR OFFLINE TEST PASS
~~~

## Fresh transaction-contract regression

~~~text
[PASS] valid offline K21D transaction accepted
[PASS] rejected: unexpected field
[PASS] rejected: wrong host
[PASS] rejected: expired transaction
[PASS] rejected: review not PASS
[PASS] rejected: installation authorization false
[PASS] rejected: authorization not single-use
[PASS] rejected: authorization consumed
[PASS] rejected: backup not verified
[PASS] rejected: backup path escape
[PASS] rejected: rollback not verified
[PASS] rejected: file omitted
[PASS] rejected: source substituted
[PASS] rejected: destination substituted
[PASS] rejected: mode expanded
[PASS] rejected: unconditional daemon-reload
[PASS] rejected: service start planned
[PASS] rejected: service enablement planned
[PASS] rejected: timer installation planned
[PASS] rejected: request dispatch planned
[PASS] rejected: production observation planned
[PASS] rejected: worker self-apply
[PASS] rejected: activation authority expanded
[PASS] rejected: execution authority expanded
[PASS] rejected: mutation authority expanded
positive_tests=1
negative_tests=24
installation_manifest_created=false
backup_created=false
installation_performed=false
daemon_reload_performed=false
execution_allowed=false
mutation_authority=false
RESULT: POST-2.39 K21D FAILURE TEST PASS
~~~

## Required reviewer decision

Return PASS only if the changed-transaction-ID authorization reuse path is
closed before consumption and mutation, completed rollback state is denied,
the tests would fail without those controls, and all existing governance and
mapping boundaries remain intact.

This review cannot authorize installation, daemon-reload, activation,
enablement, scheduling, request dispatch, production observation, execution,
or mutation. Return only the requested JSON object.
