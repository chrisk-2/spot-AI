# Post-2.39 K21D Mapping Clarification Review

## Review boundary

Clarification of two Worker-05 findings only.
No source mutation, authorization, or installation is requested.

## Temporal distinction

The revocation reason describes the historical mapping defect that
existed before the current correction. It explains why the invalid
authorization was revoked. It is not a claim about current mappings.

Current K21C and K21D mappings were independently extracted from their
current validator sources, normalized into ordered triples, serialized
canonically, hashed, and compared below.

## Canonical equality proof

```json
{
  "schema": "starfleet.post239.k21d_mapping_equality_proof.v1",
  "comparison": "ordered_source_destination_mode_tuples",
  "k21c_representation": "dictionary",
  "k21d_representation": "ordered_list",
  "k21c_mapping_count": 8,
  "k21d_mapping_count": 8,
  "k21c_canonical_sha256": "fc8d965a5c2a963bec28f8ecca69a655b0eb22e37b08bb606e73d287d5366fe3",
  "k21d_canonical_sha256": "fc8d965a5c2a963bec28f8ecca69a655b0eb22e37b08bb606e73d287d5366fe3",
  "authoritative_mapping_equal": true,
  "k21c_normalized_mapping": [
    [
      "watch/observe/controlled-read-observe.py",
      "/usr/local/lib/spot/observe/controlled-read-observe.py",
      "0755"
    ],
    [
      "watch/observe/controlled_read_observe_validation_v1.py",
      "/usr/local/lib/spot/observe/controlled_read_observe_validation_v1.py",
      "0755"
    ],
    [
      "watch/observe/controlled-read-observe-request-validate.py",
      "/usr/local/lib/spot/observe/controlled-read-observe-request-validate.py",
      "0755"
    ],
    [
      "watch/observe/controlled-read-observe-evidence-validate.py",
      "/usr/local/lib/spot/observe/controlled-read-observe-evidence-validate.py",
      "0755"
    ],
    [
      "watch/observe/controlled-read-observe-allowlist-v1.json",
      "/etc/spot/observe/controlled-read-observe-allowlist-v1.json",
      "0644"
    ],
    [
      "watch/observe/controlled-read-observe-request-schema-v1.json",
      "/etc/spot/observe/controlled-read-observe-request-schema-v1.json",
      "0644"
    ],
    [
      "watch/observe/controlled-read-observe-evidence-schema-v1.json",
      "/etc/spot/observe/controlled-read-observe-evidence-schema-v1.json",
      "0644"
    ],
    [
      "watch/observe/controlled-read-observe.service",
      "/etc/systemd/system/spot-controlled-read-observe.service",
      "0644"
    ]
  ],
  "k21d_normalized_mapping": [
    [
      "watch/observe/controlled-read-observe.py",
      "/usr/local/lib/spot/observe/controlled-read-observe.py",
      "0755"
    ],
    [
      "watch/observe/controlled_read_observe_validation_v1.py",
      "/usr/local/lib/spot/observe/controlled_read_observe_validation_v1.py",
      "0755"
    ],
    [
      "watch/observe/controlled-read-observe-request-validate.py",
      "/usr/local/lib/spot/observe/controlled-read-observe-request-validate.py",
      "0755"
    ],
    [
      "watch/observe/controlled-read-observe-evidence-validate.py",
      "/usr/local/lib/spot/observe/controlled-read-observe-evidence-validate.py",
      "0755"
    ],
    [
      "watch/observe/controlled-read-observe-allowlist-v1.json",
      "/etc/spot/observe/controlled-read-observe-allowlist-v1.json",
      "0644"
    ],
    [
      "watch/observe/controlled-read-observe-request-schema-v1.json",
      "/etc/spot/observe/controlled-read-observe-request-schema-v1.json",
      "0644"
    ],
    [
      "watch/observe/controlled-read-observe-evidence-schema-v1.json",
      "/etc/spot/observe/controlled-read-observe-evidence-schema-v1.json",
      "0644"
    ],
    [
      "watch/observe/controlled-read-observe.service",
      "/etc/systemd/system/spot-controlled-read-observe.service",
      "0644"
    ]
  ]
}
```

## Binding

- original correction bundle: `watch/review/bundles/post239-k21d-mapping-correction-review-bundle-20260829T153201Z.md`
- original bundle SHA-256: `86d07c49df7a18769e6b34cc071113679283bbceb72e0c44bc6b10b858698a0d`
- canonical mapping SHA-256: `fc8d965a5c2a963bec28f8ecca69a655b0eb22e37b08bb606e73d287d5366fe3`
- revocation record: `watch/review/bundles/REVOKE-POST239-K21D-INSTALLATION-20260829T130152Z.json`
- revocation SHA-256: `254ed739940642221a508e8194623738743845b37f2c6805475cad77011430bb`

## Deterministic conclusions

- current K21C mapping count: 8
- current K21D mapping count: 8
- normalized ordered mappings equal: true
- canonical hashes equal: true
- K21C contract preserved by current mapping: true
- historical invalid authorization consumed: false
- fresh installation authorization required: true
- current system-path installation authorized: false
- installation performed: false
- daemon-reload performed: false
- activation authorized: false
- execution allowed: false
- mutation authority: false

## Original hash-bound correction evidence

# Post-2.39 K21D Mapping-Correction Review

## Boundary

Correction review only. No installation authority is granted.

## Repository

- host: `spot-core`
- baseline HEAD: `2a0b592ef0ac9c308fbb90c1d05602045790c499`
- origin/main: `2a0b592ef0ac9c308fbb90c1d05602045790c499`

## Correction

K21D now exactly matches the accepted K21C eight-file mapping.
Repository source modes and required installed destination modes are
distinct values. The transaction installer must apply each declared
destination mode during any future authorized installation.

## Revocation

- invalid authorization: `watch/review/bundles/AUTH-POST239-K21D-INSTALLATION-20260829T130152Z.json`
- invalid authorization SHA-256: `8a720850bb2e9298452fe4ab628abd2357d9efc238945b6a8435d003bbaa574c`
- revocation: `watch/review/bundles/REVOKE-POST239-K21D-INSTALLATION-20260829T130152Z.json`
- revocation SHA-256: `254ed739940642221a508e8194623738743845b37f2c6805475cad77011430bb`

```json
{
  "schema": "starfleet.post239.k21d_installation_authorization_revocation.v1",
  "generated_at": "2026-08-29T14:10:05Z",
  "host": "spot-core",
  "repository_head": "2a0b592ef0ac9c308fbb90c1d05602045790c499",
  "revoked_authorization_path": "watch/review/bundles/AUTH-POST239-K21D-INSTALLATION-20260829T130152Z.json",
  "revoked_authorization_sha256": "8a720850bb2e9298452fe4ab628abd2357d9efc238945b6a8435d003bbaa574c",
  "reason": "K21D mappings diverged from the accepted K21C authoritative mapping",
  "backup_created": false,
  "installation_manifest_created": false,
  "authorization_consumed": false,
  "installation_performed": false,
  "daemon_reload_performed": false,
  "activation_authorized": false,
  "scheduling_authorized": false,
  "production_observation_authorized": false,
  "execution_allowed": false,
  "mutation_authority": false,
  "status": "REVOKED_BEFORE_USE"
}
```

## Authoritative mappings and source identities

```text
mapping=1
source=watch/observe/controlled-read-observe.py
source_mode=0755
source_sha256=b7df48a2ba4277cbf496aee58d7376ba2d95fa7a45e0a16eced58bbcb2771b2f
destination=/usr/local/lib/spot/observe/controlled-read-observe.py
required_destination_mode=0755

mapping=2
source=watch/observe/controlled_read_observe_validation_v1.py
source_mode=0644
source_sha256=23482e7cd0118909fa6d591515dcf3298ae1011a15637a42978a9a5fa3a4890c
destination=/usr/local/lib/spot/observe/controlled_read_observe_validation_v1.py
required_destination_mode=0755

mapping=3
source=watch/observe/controlled-read-observe-request-validate.py
source_mode=0755
source_sha256=6ace18174fd7dcd5ce1c563d084eed338040254053d683a6220bde5b446e4667
destination=/usr/local/lib/spot/observe/controlled-read-observe-request-validate.py
required_destination_mode=0755

mapping=4
source=watch/observe/controlled-read-observe-evidence-validate.py
source_mode=0755
source_sha256=c18ba77dbcfbda0649ec6a3aa83ef0a2991dd18e1cfbf2b179cecde18e3f02b8
destination=/usr/local/lib/spot/observe/controlled-read-observe-evidence-validate.py
required_destination_mode=0755

mapping=5
source=watch/observe/controlled-read-observe-allowlist-v1.json
source_mode=0644
source_sha256=1315e4b0345d8d1b2925afa8ae8db99caba5256e1d0e7b7a3d4a7ff6bea4025c
destination=/etc/spot/observe/controlled-read-observe-allowlist-v1.json
required_destination_mode=0644

mapping=6
source=watch/observe/controlled-read-observe-request-schema-v1.json
source_mode=0644
source_sha256=bfc9f80a244d5021858d49d7693f15f4f32b07af0dd5fe2675c0b666306cd78b
destination=/etc/spot/observe/controlled-read-observe-request-schema-v1.json
required_destination_mode=0644

mapping=7
source=watch/observe/controlled-read-observe-evidence-schema-v1.json
source_mode=0644
source_sha256=9f11ed5b354e8f964ac2317155869dc67fec9e558d5223f12cb233adc5d6607d
destination=/etc/spot/observe/controlled-read-observe-evidence-schema-v1.json
required_destination_mode=0644

mapping=8
source=watch/observe/controlled-read-observe.service
source_mode=0644
source_sha256=083b27278ec0d502e2e6f4865ba4fa6c495bbe6d00c5d20485297e6c95dc14b7
destination=/etc/systemd/system/spot-controlled-read-observe.service
required_destination_mode=0644
```

## Changed source scope

```text
 ...T239-K21D-INSTALLATION-TRANSACTION-BLUEPRINT.md | 35 ++++++++-------
 ...-install-transaction-implementation-validate.py | 25 +++++++++++
 ...read-observe-install-transaction-schema-v1.json | 36 ++++++++--------
 ...ed-read-observe-install-transaction-validate.py | 50 +++++++++++-----------
 4 files changed, 84 insertions(+), 62 deletions(-)
```

## Fresh adversarial validation

```text
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
```

## Fresh dormant implementation validation

```text
[PASS] complete K21D dormant toolchain
pass=4 fail=0
system_path_installation_authorized=false
backup_created=false
installation_manifest_created=false
authorization_consumed=false
installation_performed=false
daemon_reload_performed=false
activation_authorized=false
execution_allowed=false
mutation_authority=false
RESULT: POST-2.39 K21D IMPLEMENTATION VALIDATION PASS
```

## Current state

- invalid authorization consumed: false
- backup created: false
- installation manifest created: false
- installation performed: false
- daemon-reload performed: false
- activation authorized: false
- scheduling authorized: false
- production observation authorized: false
- execution allowed: false
- mutation authority: false

A fresh single-use installation authorization is required only after
this correction passes review and is committed.
