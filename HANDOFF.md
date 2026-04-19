Continuing Spot fleet work.

Repo:
https://github.com/chrisk-2/spot-AI

Current commit:
(use latest from spot-core via spot_save before handoff)

---

## RULES

- no guessing ever  
- use runtime file as source of truth first  
- read real files with sed/cat before patching  
- do not redesign system unless asked  
- no ad hoc edits  
- use scripted validation  

Routing ownership (LOCKED):
- general -> spot-worker-01  
- utility -> spot-worker-02  
- coding  -> spot-worker-03  
- heavy   -> spot-worker-04  

New chat flow:
- run spot_save first  
- read HANDOFF.md  
- read spot-core/STATE.md  
- use repo as source of truth  
- request runtime files if needed  

---

## PATHS

- repo: /home/ogre/spot-stack  
- app: /home/ogre/spot-stack/spot-core/spotcore/app.py  
- watch: /home/ogre/spot-stack/watch/fleet-watch.sh  
- remediate: /home/ogre/spot-stack/watch/fleet-remediate.sh  
- validator: /home/ogre/spot-stack/watch/fleet-validate.sh  
- policy: /home/ogre/spot-stack/watch/fleet-policy.json  
- state: /home/ogre/spot-stack/spot-core/STATE.md  

---

## CURRENT STATE

System stable and correct.

✔ routing deterministic  
✔ strict role ownership enforced  
✔ fallback working  
✔ audit + remediation working  
✔ admission control working  
✔ queueing implemented (bounded wait, retry, reject)  

---

## FLEET

- worker-01 → general + fallback  
- worker-02 → utility  
- worker-03 → coding primary + heavy fallback (gpu1 only)  
- worker-04 → heavy primary  

---

## BEHAVIOR (VERIFIED)

Failure (worker-04 down):
- heavy → worker-03 → worker-01 → reject  

Concurrency:
- fills 03 first  
- spills to 01  
- rejects excess cleanly  

---

## LIMITATION

Heavy capacity under failure ≈ 2–3 concurrent  

- worker-03 gpu1 → 1–2  
- worker-01 → 1  
- worker-04 → 0 (down case)  

8GB GPUs NOT used for heavy (intentional)

---

## DESIGN LOCK

Do NOT enable heavy on 8GB GPUs.

---

## CURRENT REALITY

System is:
- stable  
- correct  
- capacity-limited  

Not broken.

---

## CURRENT GOAL

Stage 2 — Operator layer

Do next:
- build ~/spot-stack/watch/spot-ops.sh  
- clean fleet-validate.sh output  

---

## OPTIONAL CLEANUP (SMALL)

- dedupe rejection failure output  
- normalize reason → role_not_allowed:heavy  

---

## LAST VERIFIED

- remediation stable  
- degraded clears correctly  
- routing distribution correct  
- rejection behavior correct  

---

END HANDOFF
