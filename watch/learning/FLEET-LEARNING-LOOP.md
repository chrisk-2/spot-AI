# Fleet Learning Loop

## Purpose

This document defines how Starfleet workers improve over time without unsafe self-modification.

Current phase: Phase 2.30 design review only.

This file defines process only. It does not authorize workers to rewrite their own authority, bypass review, mutate configuration, or change routing.

## Learning principle

The fleet may improve through evidence.

The fleet may not improve through hidden self-modification.

Every accepted lesson must trace back to one of:

- review finding
- failed validation
- incident
- rollback
- operator correction
- readiness checkpoint
- accepted design decision

## Authority

Workers may propose lessons.

Worker-05 reviews lessons.

Spot Core accepts or rejects lessons.

No worker may directly rewrite its own authority, role, routing, policy, or execution permissions.

## Required lesson files

Recommended files:

```text
watch/learning/worker-01-general-lessons.md
watch/learning/worker-02-utility-lessons.md
watch/learning/worker-03-coding-lessons.md
watch/learning/worker-04-heavy-lessons.md
watch/learning/worker-05-review-lessons.md
watch/learning/worker-06-reasoning-lessons.md
watch/learning/codex-lessons.md
watch/learning/openai-review-lessons.md
```

## Lesson entry format

Each lesson must use this structure:

```text
## <YYYY-MM-DD> - <short title>

Source:
- review_id:
- request_id:
- action_id:
- incident_id:
- checkpoint_id:

Observed problem:
-

Correction:
-

Validator impact:
- none | add check | update check

Review impact:
- none | update checklist | add defect example

Status:
- proposed | accepted | rejected | superseded
```

## Accepted lesson requirements

A lesson may be accepted only if:

- it has a traceable source
- it does not expand worker authority
- it does not bypass Spot Core
- it does not bypass W-5 review
- it does not weaken backup requirements
- it does not weaken rollback requirements
- it does not allow automatic OpenAI fallback
- it does not allow Codex mutation
- W-5 review passes
- Spot Core accepts it

## Rejected lesson examples

Reject lessons that say or imply:

- allow worker to apply directly
- skip review for speed
- skip backup for low-risk changes
- use OpenAI automatically
- let Codex write directly
- allow reviewer to execute
- allow operator approval to bypass rollback
- allow backup overwrite/delete
- reduce logging because task is simple

## Worker-specific learning targets

### Worker-01

Improve summaries, triage, operator-facing explanations, and low-risk request routing.

### Worker-02

Improve watcher checks, alert noise reduction, utility validation, and state collection.

### Worker-03

Improve local code proposals, shell/Python/script quality, validator additions, small patch discipline, and Codex staging quality.

### Worker-04

Improve practical remediation plans, system design, operational sequencing, and risk-aware implementation planning.

### Worker-05

Improve PASS/FIX/NO consistency, defect detection, policy matching, missing backup detection, missing rollback detection, and validation sufficiency review.

### Worker-06

Improve high-complexity reasoning, ambiguous risk classification, escalation quality, and second-opinion analysis.

### Codex

Improve complex patch proposal quality, diff discipline, validation command proposals, and staying proposal-only.

### OpenAI

Improve manual external review usefulness, second-opinion clarity, secret redaction discipline, and no-execution boundaries.

## Metrics

Spot Core should eventually track:

```text
tasks_assigned
tasks_completed
review_pass_rate
fix_rate
no_rate
repeat_defects
validation_failures
policy_violations
rollback_events
missed_defects
caught_defects
latency
fallbacks
manual_overrides
```

## Learning loop

Required process:

```text
work occurs
review occurs
validation occurs
outcome is journaled
lesson is proposed if useful
W-5 reviews lesson
Spot Core accepts or rejects
accepted lesson updates playbook/checklist
future review bundles include accepted lessons
```

## Phase 2.30 scope

Allowed:

- define learning process
- define lesson format
- define acceptance rules
- define rejection examples
- define worker-specific learning targets

Forbidden:

- automatic prompt rewriting
- automatic policy rewriting
- routing changes
- worker authority changes
- model fine-tuning
- self-modifying code
- unreviewed memory injection

## W-5 review requirements

Worker-05 must verify:

- learning is evidence-based
- lessons are reviewable
- workers cannot rewrite their own authority
- accepted lessons cannot bypass policy
- accepted lessons cannot authorize mutation
- Codex remains proposal-only
- OpenAI remains manual review-only
- Spot Core remains final authority

## Exit criteria

This learning loop design is complete when:

- W-5 returns PASS for design review
- lesson format is accepted
- accepted/rejected lesson rules are clear
- no implementation was added
