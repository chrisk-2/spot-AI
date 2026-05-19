# Structured Diff Review Spec

Phase: 3.0

## Purpose

Define the evidence bundle W-5 must review before Spot Core can apply code/config mutations.

## Required Review Inputs

Each review bundle must include:

- original request
- request_id
- patch_bundle_id
- current phase
- risk class
- target host/service
- changed file list
- unified diff
- validation commands
- rollback strategy
- backup requirements
- forbidden behaviors
- expected verdict schema

## Required Verdict

{
  "verdict": "PASS|FIX|NO",
  "execution_allowed": true,
  "confidence": "low|medium|high",
  "intent_match": "pass|fix|fail",
  "code_match": "pass|fix|fail|not_applicable",
  "policy_match": "pass|fix|fail",
  "phase_match": "pass|fix|fail",
  "backup_required": true,
  "backup_verified": false,
  "rollback_defined": true,
  "validation_defined": true,
  "required_fixes": [],
  "blocking_findings": [],
  "notes": ""
}

## Hard Rule

W-5 review PASS does not authorize execution by itself.
Spot Core still requires backup binding, rollback, replay protection, and validation.
