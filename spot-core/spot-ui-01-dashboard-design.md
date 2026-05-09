# SPOT-UI-01 OPERATOR DASHBOARD DESIGN

## Human-Readable Fleet Operations Interface

Project: Starfleet / Spot Core
Status: Planning Draft
Target Phase: Post-Phase-2 Integration
Primary Goal: Replace raw operational noise with a simple, readable fleet command display

---

# Purpose

Spot-UI-01 is intended to become the primary operator-facing interface for the Starfleet fleet.

The goal is not to create another developer dashboard full of logs, tabs, JSON blobs, or endless menus.

The goal is:

* one readable screen
* one obvious status view
* one obvious place to understand fleet health
* details only when needed
* dangerous actions clearly separated from safe actions

Spot-UI-01 should feel closer to a ship operations panel than a Linux admin console.

---

# Core Design Philosophy

## The UI should translate technical state into human language

The system already contains:

* routing
* validation
* quarantine state
* remediation
* audit logs
* worker roles
* model inventories
* GPU state
* health endpoints

The problem is not lack of data.

The problem is that the data currently looks like:

* JSON
* shell output
* logs
* scripts
* metrics
* developer information

Spot-UI-01 exists to translate all of that into:

* healthy
* warning
* problem
* overloaded
* offline
* repairing
* quarantined

The operator should not need to mentally decode the backend.

---

# Primary UI Rule

## The entire fleet should be understandable from one screen.

No tab maze.

No endless scrolling.

No nested menus for normal operation.

If the fleet is healthy:

* the dashboard should remain calm
* the interface should remain compact
* no unnecessary details should be shown

If a problem appears:

* the affected component expands
* additional information becomes visible
* recommended actions appear

Normal systems remain collapsed.

Problems expand.

---

# Main Dashboard Layout

## Top Fleet Status Banner

This is the first thing visible.

Example:

```text
Fleet Status: HEALTHY
Workers Online: 6/6
Active Alerts: 0
Validation State: PASS
Last Fleet Check: 2 minutes ago
```

If warnings exist:

```text
Fleet Status: WARNING
Workers Online: 5/6
Active Alerts: 1
Validation State: WARNING
```

If critical problems exist:

```text
Fleet Status: CRITICAL
Workers Online: 4/6
Active Alerts: 3
Validation State: FAIL
```

---

# Worker Cards

Each worker appears as a simple horizontal status card.

## Example Healthy Card

```text
Worker-01  [GREEN]
Role: General Conversation
Status: Healthy
Current Load: Low
```

## Example Busy Card

```text
Worker-04  [YELLOW]
Role: Heavy Reasoning
Status: Busy
GPU Usage: High
```

## Example Failed Card

```text
Worker-06  [RED]
Role: Premium Reasoning
Status: Offline
Issue: Ollama Service Down
```

---

# Worker Detail Expansion

Healthy workers remain compact.

Clicking a warning or failure expands details.

## Expanded Example

```text
Worker-06
Status: Offline
Last Seen: 3 minutes ago
Problem Detected:
Ollama service not responding

Suggested Actions:
- Restart AI Service
- Quarantine Worker
- Ignore Alert

Last Validation:
FAILED
```

The system should not immediately dump raw logs.

The first level should always remain human-readable.

Advanced technical detail may exist under:

```text
Show Technical Details
```

for debugging.

---

# Color Logic

## Green

Normal operation.

Examples:

* worker online
* latency normal
* services responding
* validation passing

## Yellow

Warning state.

Examples:

* high load
* elevated latency
* fallback routing active
* nearing VRAM limits
* remediation in progress

## Red

Action required.

Examples:

* worker offline
* validation failure
* service crash
* quarantine active
* routing failure

---

# Dashboard Information Priority

The operator should immediately understand:

1. Is the fleet healthy?
2. Which workers are online?
3. Is anything broken?
4. Is Spot routing correctly?
5. Is remediation occurring?
6. Are any workers quarantined?

Everything else is secondary.

---

# Safe Operator Actions

The dashboard should expose only common safe actions first.

## Initial Safe Actions

* Run Fleet Validation
* Refresh Fleet Status
* Restart Worker AI Service
* Quarantine Worker
* Release Worker
* View Routing Audit

---

# Dangerous Actions

Dangerous actions must require confirmation.

Examples:

* delete data
* reconfigure routing
* alter network configuration
* change policy
* remove backups

The dashboard must clearly explain consequences before execution.

---

# Routing Visibility

The dashboard should explain routing in plain English.

Instead of:

```text
fallback_role_violation=true
```

Display:

```text
Request was redirected because Worker-04 was unavailable.
```

Instead of:

```text
eligible=false
```

Display:

```text
Worker temporarily blocked from receiving work.
```

---

# Quarantine Visibility

Quarantine must be visually obvious.

Example:

```text
Worker-03
QUARANTINED
Reason:
Repeated validation failures
```

The operator must understand:

* why quarantine occurred
* whether remediation is running
* whether release is safe

---

# Model Visibility

The dashboard should show models in simple terms.

Example:

```text
Worker-04
Models:
- qwen3:32b (Reasoning)
- qwen2.5-coder:32b (Coding)
- qwen2.5:14b (Fast Fallback)
```

Not just raw model IDs.

---

# Fleet Identity

The dashboard should reinforce that the fleet contains specialized workers.

Example role display:

| Worker    | Human Description           |
| --------- | --------------------------- |
| Worker-01 | Everyday conversation       |
| Worker-02 | Utility and repair          |
| Worker-03 | Engineering and coding      |
| Worker-04 | Heavy reasoning             |
| Worker-05 | Experimental processing lab |
| Worker-06 | Premium reasoning           |

This helps operators mentally understand how Spot Core routes requests.

---

# Integration With Spot Core

Spot-UI-01 should not replace Spot Core.

Spot Core remains:

* control plane
* routing authority
* policy authority
* remediation authority
* audit authority

Spot-UI-01 is only:

* visualization
* interaction
* simplified operational control

The UI reflects state.

It does not become the state authority.

---

# Codex Integration Concept

Future versions may allow controlled Codex-assisted actions.

Example:

```text
Problem Detected:
Validation failure in routing script

Suggested Resolution Available
Generated by Codex

[ Review Proposed Fix ]
```

However:

* no autonomous unsafe edits
* no bypass of backup policy
* no bypass of approval rules

The autonomy policy remains authoritative.

---

# Design Goals

## The dashboard should feel:

* calm
* readable
* operational
* trustworthy
* understandable at a glance

## The dashboard should NOT feel:

* cluttered
* developer-only
* overwhelming
* noisy
* dependent on reading raw logs

---

# Initial Technical Scope

## Phase 1

Read-only dashboard.

Features:

* worker health
* routing state
* quarantine state
* validation status
* model inventory
* GPU state
* recent alerts

No destructive actions.

---

# Phase 2

Safe operational controls.

Examples:

* restart service
* validate fleet
* quarantine worker
* release worker

All actions remain logged.

---

# Phase 3

Controlled remediation workflows.

Examples:

* guided rollback
* remediation approval
* Codex-generated fixes
* maintenance mode
* staged deployment approval

---

# Final Vision

The long-term goal is for Spot-UI-01 to become:

```text
The bridge display for the Starfleet environment.
```

Not merely a dashboard.

A readable operational surface where:

* fleet health
* AI routing
* remediation
* infrastructure state
* future automation

can all be understood quickly without reading backend code.

---

# Important Rule

If an operator must constantly open terminals to understand system state,
then Spot-UI-01 has failed its purpose.

The UI exists to reduce operational friction.

Not move the same complexity into a browser.
