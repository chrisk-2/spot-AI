# Post-2.39 K21C Controlled Read/Observe Installation Rollback

## Status

ROLLBACK DESIGN ONLY

This document defines rollback boundaries and validation requirements. It does
not authorize installation, rollback execution, daemon-reload, activation,
scheduling, production observation, or service mutation.

## Fixed installation targets

Rollback is restricted to these exact destinations:

1. `/usr/local/lib/spot/observe/controlled-read-observe.py`
2. `/usr/local/lib/spot/observe/controlled_read_observe_validation_v1.py`
3. `/usr/local/lib/spot/observe/controlled-read-observe-request-validate.py`
4. `/usr/local/lib/spot/observe/controlled-read-observe-evidence-validate.py`
5. `/etc/spot/observe/controlled-read-observe-allowlist-v1.json`
6. `/etc/spot/observe/controlled-read-observe-request-schema-v1.json`
7. `/etc/spot/observe/controlled-read-observe-evidence-schema-v1.json`
8. `/etc/systemd/system/spot-controlled-read-observe.service`

Runtime paths are:

- `/var/lib/spot/controlled-read-observe/request.json`
- `/var/lib/spot/controlled-read-observe/evidence`

Evidence and archived receipts must never be deleted or overwritten by
rollback.

## Required pre-install backup

Before any future installation:

- create one immutable backup directory;
- inspect every fixed destination;
- copy every existing regular file while preserving its contents;
- calculate SHA-256 for every backup;
- record `missing_source=true` for every absent destination;
- write a machine-readable backup manifest;
- validate the backup manifest;
- bind the backup manifest to the reviewed source bundle;
- bind this rollback design to the same reviewed source bundle.

No verified backup and binding means no installation.

## Rollback trigger conditions

A separately authorized installation transaction must halt and enter rollback
if any of these conditions occur:

- source hash mismatch;
- destination hash mismatch;
- unexpected destination type;
- ownership or mode mismatch;
- unit parsing failure;
- observer active after installation;
- observer enabled after installation;
- observer scheduled after installation;
- timer unit detected;
- request dispatched;
- production evidence created;
- offline regression failure;
- journal or receipt write failure;
- unrelated service state change;
- authority flag expansion.

## Rollback sequence

Rollback execution, if separately authorized, must perform these operations in
order:

1. Record the rollback request and correlated installation identity.
2. Confirm Spot Core is the executing host.
3. Confirm the backup manifest and bindings validate.
4. Confirm the rollback target set exactly matches the fixed destination list.
5. If the observer is unexpectedly active, stop only
   `spot-controlled-read-observe.service`.
6. For each destination with `missing_source=false`, restore only the verified
   backup corresponding to that destination.
7. For each destination with `missing_source=true`, remove only the file
   recorded as newly installed by the installation receipt.
8. Run `systemctl daemon-reload` only if the systemd unit destination changed.
9. Do not delete the runtime evidence directory.
10. Do not delete or overwrite any review, authorization, backup, journal,
    receipt, or archive record.
11. Perform the rollback verification checks.
12. Append the final rollback outcome to immutable evidence.

No wildcard, recursive deletion, shell expansion, arbitrary path, arbitrary
service, or remote execution is permitted.

## Required rollback verification

After rollback:

- every restored destination SHA-256 equals its recorded backup SHA-256;
- every destination originally absent is absent again;
- `spot-controlled-read-observe.service` is inactive;
- `spot-controlled-read-observe.service` is disabled;
- no controlled-read-observe timer exists;
- no observer process remains;
- no production request was dispatched;
- no production observation occurred;
- runtime evidence remains preserved;
- unrelated service state is unchanged;
- K21A offline validation passes;
- K21B offline validation passes;
- K21C installation-contract validation passes against repository source;
- `execution_allowed=false`;
- `mutation_authority=false`.

## Rollback evidence

The immutable rollback receipt must contain:

- rollback ID;
- installation ID;
- operator authorization ID;
- Worker-05 review record and SHA-256;
- reviewed bundle and SHA-256;
- repository commit;
- backup manifest ID and SHA-256;
- backup binding ID;
- rollback binding ID;
- exact destination list;
- before and after hashes;
- service state before and after;
- whether daemon-reload was performed;
- validation results;
- final outcome;
- rollback failure details, if any.

## Fail-closed outcome

If backup validation, restoration, verification, or journaling fails:

- stop the rollback transaction;
- report `ROLLBACK_BLOCKED` or `ROLLBACK_FAILED`;
- do not report success;
- do not widen authority;
- leave the observer inactive, disabled, and unscheduled whenever safely
  possible;
- require operator intervention.

## Current authority

- installation artifact construction authorized: true
- system-path installation authorized: false
- rollback execution authorized: false
- daemon-reload authorized: false
- activation authorized: false
- scheduling authorized: false
- production observation authorized: false
- observer installed: false
- observer enabled: false
- observer scheduled: false
- execution allowed: false
- mutation authority: false
