# Module — Governed Remediation Automation

## Scope

This module adds a governed remediation policy surface.

## Added

- watch/remediation/governed-remediation-policy.py
- watch/remediation/governed-remediation-policy-validate.py
- operator command: remediation-policy
- operator command: remediation-policy-validate

## Current Boundary

This module does not enable live remediation.

Current state:
- remediation_allowed_now=false
- live_mutation_allowed_now=false
- execution_allowed=false
- mutation_authority=false

## Required Remediation Chain

- detect
- classify
- backup required
- rollback required
- review required
- preflight required
- Spot Core execution only
- verify required
- journal required

## Policy

- No backup means no change.
- No rollback means no execution.
- No review means no apply.
- Workers do not self-apply.
- Spot Core remains sole executor.
- High-risk actions require approval.

## Purpose

This module prepares the governance surface for future controlled remediation automation without expanding live execution authority.
