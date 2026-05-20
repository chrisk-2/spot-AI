# Review Warm Residency Policy

Status: DESIGN / DRY-RUN ONLY

## Purpose

Reduce `/review/local` latency by keeping primary reviewer models warm.

## Preferred Warm Targets

Primary:
- spot-worker-05
- qwen2.5-coder:32b

Secondary:
- spot-worker-05
- deepseek-r1:32b

Escalation:
- spot-worker-06
- qwen2.5:32b or deepseek-r1:32b

## Constraints

Warm policy may not:
- restart production services autonomously
- kill running inference jobs
- override operator-selected model placement
- change routing ownership
- authorize execution

## Future Implementation Direction

Future runtime manager may:
- check Ollama `/api/ps`
- issue non-mutating warm prompts
- track cold-load duration
- decay health scores based on latency
- notify operator before remediation
