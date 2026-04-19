Rules:
- no guessing ever
- use runtime file as source of truth first
- if file needed, read exact file with sed/cat or repo fetch before patching
- do not redesign system unless explicitly asked
- do not do ad hoc chaos edits
- use scripted validation going forward
- preserve current routing ownership:
  - general -> spot-worker-01
  - utility -> spot-worker-02
  - coding -> spot-worker-03
  - heavy -> spot-worker-04
- for every new chat move:
  - run spot_save first
  - read HANDOFF.md first
  - read spot-core/STATE.md second
  - use GitHub repo as source of truth first
  - if runtime verification is needed, ask for exact file contents from spot-core with sed/cat
  - do not assume local filesystem paths are mounted in your environment
  - do not patch anything without reading the real file first


Primary repo:
https://github.com/chrisk-2/spot-AI

Primary runtime paths:
- repo root: /home/ogre/spot-stack
- app: /home/ogre/spot-stack/spot-core/spotcore/app.py
- watch: /home/ogre/spot-stack/watch/fleet-watch.sh
- remediate: /home/ogre/spot-stack/watch/fleet-remediate.sh
- validator: /home/ogre/spot-stack/watch/fleet-validate.sh
- policy: /home/ogre/spot-stack/watch/fleet-policy.json
- state: /home/ogre/spot-stack/spot-core/STATE.md

Continuing Spot fleet work.

Repo:
https://github.com/chrisk-2/spot-AI

Current commit:
(use latest from spot-core via `spot_save` before handoff)

Source of truth:

* GitHub repo
* Runtime files only when explicitly provided via sed/cat

Read first:

* HANDOFF.md
* spot-core/STATE.md

---

## CURRENT SYSTEM STATE

### Fleet topology

spot-core:

* scheduler + routing API (:8787)

Workers:

spot-worker-01:

* role: general (primary), heavy fallback
* GPU: RTX 3060 12GB
* max_total: 1
* models: llama3.1:8b, mistral:7b, qwen2.5:14b

spot-worker-02:

* role: utility
* GPUs: M4000 8GB + GTX 1060 6GB
* models: embedding + phi3.5

spot-worker-03:

* role: coding primary, heavy fallback (gpu1 only)
* GPUs:

  * gpu0: GTX 1070 8GB (coding only)
  * gpu1: RTX 3060 12GB (coding + heavy)
* max_total: 2
* models: qwen2.5-coder:7b, qwen2.5:14b, codellama, deepseek

spot-worker-04:

* role: heavy primary
* GPU: TITAN Xp 12GB
* model: qwen2.5:14b

---

## ROUTING POLICY

STRICT ROLE OWNERSHIP

heavy:

1. spot-worker-04 (primary)
2. spot-worker-03 (fallback, gpu1 only)
3. spot-worker-01 (fallback)

coding:

* spot-worker-03 primary

general:

* spot-worker-01 only

utility:

* spot-worker-02

---

## SYSTEM CAPABILITIES (ALL WORKING)

✔ deterministic routing
✔ strict role ownership
✔ fallback routing
✔ routing audit system
✔ remediation engine
✔ degraded state tracking
✔ degraded penalty in scoring
✔ degraded persistence + decay (clean-run based)
✔ recent fallback window (time-based, not historical)
✔ multi-node fallback distribution (03 + 01)
✔ hard admission control (no overload thrashing)

---

## VERIFIED BEHAVIOR

### Failure scenario (worker-04 down)

* heavy routes to worker-03 first
* spills to worker-01 when 03 hits capacity
* excess requests are rejected (not queued)

### Concurrency test result

* worker-03 selected first (best capacity)
* worker-01 used as secondary fallback
* additional requests rejected with:

  * gpu_lane_at_capacity
  * worker_at_capacity

System is behaving correctly.

---

## CURRENT LIMITATION

Heavy capacity under failure:

* worker-03 gpu1: 1–2 concurrent (12GB)
* worker-01: 1 concurrent
* worker-04: 0 (down scenario)

Total effective heavy concurrency ≈ 2–3

Worker-03 gpu0 (8GB) is intentionally NOT used for heavy:

* insufficient VRAM for qwen2.5:14b
* avoiding unstable runtime behavior

---

## DESIGN DECISION (IMPORTANT)

Do NOT enable heavy on 8GB GPUs.

Reason:

* prevents unstable execution / OOM / thrashing
* maintains deterministic admission behavior

---

## CURRENT PROBLEM SPACE

System is now:

* stable
* correct
* capacity-limited under burst load

Not broken.

---

## NEXT PHASE OPTIONS

Choose one direction (do not mix blindly):

### Option A — Queueing (recommended next step)

* add short wait/queue before rejection
* improves UX under burst without lying about capacity

### Option B — Capacity expansion

* additional 12GB+ GPU nodes
* or redistribute heavy models

### Option C — Multi-model heavy tier

* introduce smaller heavy model for 8GB lanes
* requires explicit routing tier split

---

## RULES

* do not redesign architecture
* do not remove admission control
* do not assume capacity that does not exist
* use real runtime data, not assumptions
* prefer small, testable changes

---

## CURRENT GOAL

Implement controlled request queueing for heavy role:

* short wait window
* retry scheduling before hard rejection
* must respect existing admission + scoring system

---

## LAST VERIFIED STATE

* remediation-state.json stable
* degraded clears correctly
* recent_fallback_count_window working
* routing distributing across 03 + 01
* rejection behavior confirmed under load

---

END HANDOFF
