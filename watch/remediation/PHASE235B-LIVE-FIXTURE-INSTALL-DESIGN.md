# Phase 2.35B — Live Fixture Install Design

## Status
DESIGN REVIEW ONLY

## Goal
Define the controlled installation path for the remediation fixture through Spot Core only.

## Scope
This phase defines:
- installation workflow
- backup binding requirements
- rollback workflow
- journal requirements
- executor boundaries

No live installation occurs in this phase.

## Explicitly Forbidden
- no systemctl enable
- no systemctl start
- no daemon-reload
- no live backup writes
- no service mutation
- no executor dispatch
- no worker-side apply authority

## Required Future Live Chain
Review PASS
-> backup artifact creation
-> backup verification
-> binding record creation
-> Spot Core executor validation
-> controlled install
-> verification
-> rollback-or-success journal

## Install Targets
Future install targets only:
- /etc/systemd/system/spot-remediation-fixture.service
- /usr/local/lib/spot/spot-remediation-fixture.sh

## Verification Requirements
- unit hash matches reviewed artifact
- script hash matches reviewed artifact
- fixture service remains isolated/sandboxed
- no unrelated unit changes
- journal records complete chain

## Authority
Spot Core remains sole future execution authority.
Worker-05 remains proposal_review_only.
execution_allowed remains false.
