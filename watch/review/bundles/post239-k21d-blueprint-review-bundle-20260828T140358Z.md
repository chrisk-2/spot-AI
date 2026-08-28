# Post-2.39 K21D Installation-Transaction Blueprint Review

## Review authority

Worker-05 reviews design only.

This review must not authorize installation, daemon-reload, activation,
enablement, scheduling, production observation, execution, or mutation.

## Repository identity

- repository commit: `87bf1b3b375639ed4e90b6be46a4d381f115e4db`
- repository equals origin/main: true
- generated UTC: `2026-08-28T14:03:58Z`

## Correlated accepted K21C contract

- K21C PASS record: `watch/review/bundles/POST239-K21C-INSTALLATION-CONTRACT-PASS-20260827T231024Z.json`
- K21C PASS SHA-256: `67db3b240e7639e192d2466ccc4ca73ccb2c7e9339a54ec106fadc04c08f59f7`
- K21C installation contract accepted: true
- current system-path installation authorized: false
- current daemon-reload planned: false
- current daemon-reload authorized: false
- current installation performed: false
- current activation authorized: false
- current scheduling authorized: false
- current production observation authorized: false
- current execution_allowed: false
- current mutation_authority: false

## K21D blueprint identity

- blueprint: `watch/observe/POST239-K21D-INSTALLATION-TRANSACTION-BLUEPRINT.md`
- blueprint SHA-256: `d3d922f1f133f5ab70cb04202af64933a2947eebda583a306b940524a16bcf1c`

## Required PASS conditions

- design, review, authorization, installation, and activation are separate
- exactly eight fixed source-to-destination mappings are defined
- K21C schema remains unchanged and locked false
- any future K21D schema is separately versioned
- explicit, expiring, single-use operator authorization is required
- repository, review, authorization, backup, rollback, and manifest bind
- installation fails closed on any stale or mismatched identity
- backup verification precedes the first destination change
- installation cannot start, enable, or schedule the observer
- daemon-reload is limited to a changed unit file
- installed state must remain disabled, inactive, and unscheduled
- failure after mutation triggers bounded rollback
- workers cannot install or self-apply
- no production observation is authorized
- execution_allowed remains false
- mutation_authority remains false

## Required review response

Return PASS, FIX, or NO.

A PASS accepts only this design boundary and grants no authority.

## Blueprint

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
   to `/usr/local/lib/spot/controlled-read-observe.py`
2. `watch/observe/controlled-read-observe-runner.sh`
   to `/usr/local/lib/spot/controlled-read-observe-runner.sh`
3. `watch/observe/controlled-read-observe-allowlist.json`
   to `/usr/local/lib/spot/controlled-read-observe-allowlist.json`
4. `watch/observe/controlled-read-observe-request.schema.json`
   to `/usr/local/lib/spot/controlled-read-observe-request.schema.json`
5. `watch/observe/controlled-read-observe-evidence.schema.json`
   to `/usr/local/lib/spot/controlled-read-observe-evidence.schema.json`
6. `watch/observe/controlled-read-observe-validate.py`
   to `/usr/local/lib/spot/controlled-read-observe-validate.py`
7. `watch/observe/controlled-read-observe-replay-bounds-validate.py`
   to `/usr/local/lib/spot/controlled-read-observe-replay-bounds-validate.py`
8. `watch/observe/controlled-read-observe.service`
   to `/etc/systemd/system/controlled-read-observe.service`

No source substitution, destination substitution, path traversal, symlink
redirection, wildcard expansion, directory-wide copy, or additional file is
permitted.

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
