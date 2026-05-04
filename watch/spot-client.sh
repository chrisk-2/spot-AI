#!/usr/bin/env bash
set -Eeuo pipefail

SPOT_BASE_URL="${SPOT_BASE_URL:-http://127.0.0.1:8787}"
CURL_TIMEOUT="${CURL_TIMEOUT:-240}"
BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
PROPOSAL_DIR="${PROPOSAL_DIR:-${BASE_DIR}/proposals}"
SPOT_MEMORY_DIR="${SPOT_MEMORY_DIR:-/mnt/collective/spot/memory}"

usage(){ cat <<'EOF'
Usage:
  spot-client.sh ask [--role ROLE] [--model MODEL] [--json] [--memory] <prompt>
  spot-client.sh propose [--role ROLE] [--json] [--save] <task>
  spot-client.sh proposals [count]
  spot-client.sh show-proposal <id-or-file>
  spot-client.sh approve <id-or-file>
  spot-client.sh reject <id-or-file>
  spot-client.sh proposal-status <id-or-file>
  spot-client.sh generate-apply-plan <id-or-file>
  spot-client.sh apply-plans [count]
  spot-client.sh show-apply-plan <id-or-file>
  spot-client.sh apply-plan-status <id-or-file>
  spot-client.sh apply-plan-check <id-or-file>
  spot-client.sh apply-plan-verify <id-or-file>
  spot-client.sh approve-apply-plan <id-or-file>
  spot-client.sh reject-apply-plan <id-or-file>
  spot-client.sh prepare-execution-handoff <id-or-file>
  spot-client.sh execution-handoffs [count]
  spot-client.sh show-execution-handoff <id-or-file>
  spot-client.sh execution-handoff-status <id-or-file>
  spot-client.sh execution-handoff-verify <id-or-file>
  spot-client.sh execute-handoff <id-or-file>
  spot-client.sh execution-runs [count]
  spot-client.sh show-execution-run <id-or-file>
  spot-client.sh execution-run-verify <id-or-file>
  spot-client.sh execution-run-status <id-or-file>
  spot-client.sh execution-run-audit <id-or-file>
  spot-client.sh execution-run-summary [count]
  spot-client.sh execution-run-approve <id-or-file>
  spot-client.sh execution-run-reject <id-or-file>
  spot-client.sh execution-run-close <id-or-file>
  spot-client.sh action-policy [--json]
  spot-client.sh action-policy-verify
  spot-client.sh plugin-registry [--json]
  spot-client.sh plugin-registry-verify
  spot-client.sh create-action-request <action_class> <target> <summary>
  spot-client.sh action-requests [count]
  spot-client.sh show-action-request <id-or-file>
  spot-client.sh action-request-verify <id-or-file>
  spot-client.sh action-request-status <id-or-file>
  spot-client.sh action-request-audit <id-or-file>
  spot-client.sh action-request-summary [count]
  spot-client.sh approve-action-request <id-or-file>
  spot-client.sh reject-action-request <id-or-file>
  spot-client.sh close-action-request <id-or-file>
  spot-client.sh prepare-action-handoff <action-request-id-or-file>
  spot-client.sh action-handoffs [count]
  spot-client.sh show-action-handoff <id-or-file>
  spot-client.sh action-handoff-status <id-or-file>
  spot-client.sh action-handoff-audit <id-or-file>
  spot-client.sh action-handoff-summary [count]
  spot-client.sh action-handoff-verify <id-or-file>
  spot-client.sh approve-action-handoff <id-or-file>
  spot-client.sh reject-action-handoff <id-or-file>
  spot-client.sh close-action-handoff <id-or-file>
  spot-client.sh generate-patch <id-or-file>   # legacy alias
  spot-client.sh remember <fact|decision|session|preference|roadmap> <text>
  spot-client.sh memory [count]
  spot-client.sh recall <keyword>
EOF
}

need_cmd(){ command -v "$1" >/dev/null 2>&1 || { echo "ERROR: required command not found: $1" >&2; exit 2; }; }
join_prompt(){ local IFS=' '; printf '%s' "$*"; }
lower(){ printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }
slug(){ printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//' | cut -c1-48; }

classify_role(){
  local p="$(lower "$1")"
  [[ "$p" =~ (python|bash|script|code|function|class|traceback|stacktrace|exception|dockerfile|compose|systemd|regex|json|yaml|bug|debug|compile|syntax|patch|diff|git|api|endpoint|config|configuration|worker|latency|fix) ]] && { echo coding; return; }
  [[ "$p" =~ (architecture|architectural|design|roadmap|strategy|analyze|analysis|long|plan|proposal|compare|tradeoff|risk|migration|topology) ]] && { echo heavy; return; }
  [[ "$p" =~ (classify|classification|extract|embed|embedding|tag|label|short|quick) ]] && { echo utility; return; }
  echo general
}

telemetry_intent(){
  local p="$(lower "$1")"
  if [[ "$p" =~ (^|[[:space:]])(why|how|what.do.we.know|explain|analyze|diagnose|recommend|should)([[:space:]]|$) ]]; then
    echo none
    return
  fi
  [[ "$p" =~ ^(show|get|current|what.is).*(fleet.status|spot.status|system.status|readiness|health)$ ]] && { echo readiness; return; }
  [[ "$p" =~ ^(show|get|current).*(routing|route|audit|fallback|violation) ]] && { echo audit; return; }
  [[ "$p" =~ ^(show|get|current).*(latency|performance|speed|tok/sec|tokens) ]] && { echo latency; return; }
  echo none
}

api_get(){ curl -fsS --connect-timeout 5 --max-time "$CURL_TIMEOUT" "${SPOT_BASE_URL}$1"; }

print_readiness_summary(){
  printf '%s
' "$1" | jq -r '"Spot readiness: \(.status)","Core: \(if .core.ok then "OK" else "FAIL" end) uptime=\(.core.uptime_sec)s","Routing: \(if .routing.ok then "OK" else "FAIL" end) primaries=\(.routing.primaries) fallbacks=\(.routing.fallbacks) violations=\(.routing.violations)","Fleet: workers=\(.fleet.worker_count) failures=\(.fleet.worker_failures) quarantined=\(.fleet.quarantined) degraded=\(.fleet.degraded)",(if (.fleet.slow_workers|length)>0 then "Warnings:\n" + (.fleet.slow_workers|map("- \(.worker): p50=\(.p50_total_ms)ms avg=\(.avg_total_ms)ms reason=\(.reason)")|join("\n")) else "Warnings: none" end)'
}
print_audit_summary(){ printf '%s
' "$1" | jq -r '"Routing audit: \(if .ok then "OK" else "FAIL" end)","Window: \(.window_count)","Primaries: \(.primaries)","Fallbacks: \(.fallbacks)","Violations: \(.violations)","Manual overrides: \(.manual_overrides)","Last violation: \(.last_violation_ts // "none")"'; }
print_latency_summary(){ printf '%s
' "$1" | jq -r 'to_entries|sort_by(.key)|map("\(.key): count=\(.value.count) avg=\(.value.avg_total_ms)ms p50=\(.value.p50_total_ms)ms tok_sec=\(.value.avg_tok_per_sec)")|join("\n")'; }
handle_telemetry_ask(){
  case "$1" in
    readiness) local d="$(api_get /operator/readiness)"; [[ "$2" == true ]] && printf '%s
' "$d"|jq . || print_readiness_summary "$d";;
    audit) local d="$(api_get '/stats/routing-audit?limit=200')"; [[ "$2" == true ]] && printf '%s
' "$d"|jq . || print_audit_summary "$d";;
    latency) local d="$(api_get /stats/latency)"; [[ "$2" == true ]] && printf '%s
' "$d"|jq . || print_latency_summary "$d";;
  esac
}

json_payload(){ [[ -n "$2" ]] && jq -n --arg role "$1" --arg model "$2" --arg prompt "$3" '{role:$role, model:$model, prompt:$prompt, stream:false}' || jq -n --arg role "$1" --arg prompt "$3" '{role:$role, prompt:$prompt, stream:false}'; }
call_exec(){ json_payload "$1" "$2" "$3" | curl -fsS --connect-timeout 5 --max-time "$CURL_TIMEOUT" -H 'Content-Type: application/json' -d @- "${SPOT_BASE_URL}/exec"; }

spot_context_block(){
  local r a ready slowp50 slowavg prim fall vio
  r="$(api_get /operator/readiness)"
  a="$(api_get '/stats/routing-audit?limit=200')"
  ready="$(printf '%s
' "$r"|jq -r '.status')"
  slowp50="$(printf '%s
' "$r"|jq -r '.fleet.slow_workers[0].p50_total_ms // "none"')"
  slowavg="$(printf '%s
' "$r"|jq -r '.fleet.slow_workers[0].avg_total_ms // "none"')"
  prim="$(printf '%s
' "$a"|jq -r '.primaries')"
  fall="$(printf '%s
' "$a"|jq -r '.fallbacks')"
  vio="$(printf '%s
' "$a"|jq -r '.violations')"
  cat <<EOF
CURRENT_SPOT_CONTEXT
- readiness: ${ready}
- routing audit: primaries=${prim} fallbacks=${fall} violations=${vio}
- worker-02 latency warning: p50=${slowp50}ms avg=${slowavg}ms
- worker-02 known condition: utility lane is slow; dual physical GPUs but single modeled ollama base_url
CANONICAL_PATHS
- cluster config: /home/ogre/spot-stack/spot-core/config/cluster_config.json
- client script: /home/ogre/spot-stack/watch/spot-client.sh
- operator wrapper: /home/ogre/spot-stack/watch/spot-ops.sh
ALLOWED_VALIDATION_COMMANDS
- python3 -m json.tool /home/ogre/spot-stack/spot-core/config/cluster_config.json >/dev/null
- spot validate
- spot ask "show worker latency"
- spot ask "what is the current fleet status"
- spot ask "show current routing audit"
FORBIDDEN_GUESSES
- /home/ogre/spot-stack/bin/spot
- /etc/config/worker-02.yaml
- worker-02.service
- spot-client.service
- spot-ops.service
- systemctl restart spot-client
- systemctl restart spot-ops
- assuming .bak exists unless the proposal explicitly creates it
RULES
- config changes should target cluster_config.json unless evidence says otherwise
- do not suggest unrelated network/sysctl tuning unless directly justified
- rollback should reference Spot Core backup artifacts or an explicit pre-change copy created by the plan
- do not include patch bodies, sample JSON, or file contents unless the user explicitly asks for a patch
EOF
}

print_route(){ local result="$1"; printf '\n[route] role=%s worker=%s model=%s gpu=%s\n' "$(printf '%s
' "$result"|jq -r '.role_requested')" "$(printf '%s
' "$result"|jq -r '.worker')" "$(printf '%s
' "$result"|jq -r '.model')" "$(printf '%s
' "$result"|jq -r '.gpu_label')" >&2; }

save_proposal(){
  local task="$1" role="$2" result="$3" body="$4"
  mkdir -p "$PROPOSAL_DIR"
  local ts id s file worker model gpu
  ts="$(date -u +%Y%m%d-%H%M%S)"
  s="$(slug "$task")"; [[ -n "$s" ]] || s="proposal"
  id="P-${ts}-${s}"
  file="${PROPOSAL_DIR}/${id}.md"
  worker="$(printf '%s
' "$result"|jq -r '.worker')"
  model="$(printf '%s
' "$result"|jq -r '.model')"
  gpu="$(printf '%s
' "$result"|jq -r '.gpu_label')"
  cat > "$file" <<EOF
# Spot Proposal ${id}

status: pending_review  
created_utc: ${ts}  
task: ${task}  
role: ${role}  
worker: ${worker}  
model: ${model}  
gpu: ${gpu}  

---

${body}
EOF
  printf '\n[saved] id=%s\n[path] %s\n' "$id" "$file" >&2
}

resolve_proposal_file(){ local id="${1:-}"; [[ -n "$id" ]] || { echo "ERROR: proposal id/file required" >&2; exit 2; }; local file="$id"; [[ -f "$file" ]] || file="${PROPOSAL_DIR}/${id%.md}.md"; [[ -f "$file" ]] || { echo "ERROR: proposal not found: $id" >&2; exit 2; }; printf '%s' "$file"; }

set_proposal_status(){
  local file="$1" new_status="$2"
  python3 - "$file" "$new_status" <<'INNER'
from pathlib import Path
import sys, re
p = Path(sys.argv[1])
status = sys.argv[2]
txt = p.read_text()
txt = re.sub(r'^status:\s+.*$', f'status: {status}', txt, count=1, flags=re.M)
if f'{status}_utc:' not in txt:
    txt = txt.replace('status: ' + status, 'status: ' + status + '  \n' + f'{status}_utc: ' + __import__("datetime").datetime.utcnow().strftime("%Y%m%d-%H%M%S"), 1)
p.write_text(txt)
INNER
}

cmd_approve(){ local file id task; file="$(resolve_proposal_file "${1:-}")"; set_proposal_status "$file" approved; id="$(basename "$file" .md)"; task="$(grep '^task:' "$file" | cut -d':' -f2- | sed 's/^ //')"; memory_append decision "approved proposal ${id} for task ${task}"; memory_append session "proposal ${id} moved to approved state"; echo "[approved] $file"; }
cmd_reject(){ local file; file="$(resolve_proposal_file "${1:-}")"; set_proposal_status "$file" rejected; echo "[rejected] $file"; }
cmd_proposal_status(){ local file; file="$(resolve_proposal_file "${1:-}")"; grep -E '^(status:|approved_utc:|rejected_utc:|created_utc:|task:)' "$file"; }
proposal_is_approved(){ grep -q '^status: approved' "$1"; }

cmd_generate_apply_plan(){
  local file
  file="$(resolve_proposal_file "${1:-}")"
  if ! proposal_is_approved "$file"; then
    echo "ERROR: proposal is not approved; generate-apply-plan blocked" >&2
    exit 2
  fi

  python3 - "$file" "${BASE_DIR}/apply-plans" <<'PY'
from pathlib import Path
import re, sys
from datetime import datetime, UTC

proposal = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
text = proposal.read_text(errors="ignore")
id_ = proposal.stem

def meta(name, default=""):
    m = re.search(rf'^{re.escape(name)}:\s*(.+?)\s*$', text, re.M)
    return m.group(1).strip() if m else default

def section(name):
    m = re.search(rf'^{re.escape(name)}\s*\n(?P<body>.*?)(?=\n[A-Z_]+\s*\n|\Z)', text, re.M | re.S)
    return m.group('body').strip() if m else ""

def bullets(body):
    vals = []
    for line in body.splitlines():
        s = line.strip()
        if s.startswith('- '):
            vals.append(s[2:].strip())
        elif s and not s.endswith(':'):
            vals.append(s)
    return vals

def clean_risk(raw):
    raw = (raw or "").lower()
    if "high" in raw:
        return "high"
    if "low" in raw:
        return "low"
    if "medium" in raw:
        return "medium"
    return "medium"

task = meta("task", "unknown")
approved = meta("approved_utc", "unknown")
risk = clean_risk(section("RISK_CLASS") or meta("risk_class"))
targets = bullets(section("FILES_AFFECTED"))
if not targets:
    targets = ["/home/ogre/spot-stack/spot-core/config/cluster_config.json"]
default_validations = [
    "python3 -m json.tool /home/ogre/spot-stack/spot-core/config/cluster_config.json >/dev/null",
    "spot validate",
    'spot ask "show worker latency"',
    'spot ask "what is the current fleet status"',
    'spot ask "show current routing audit"',
]
proposal_validations = bullets(section("VALIDATION_COMMANDS"))
validations = []
for item in default_validations + proposal_validations:
    if item not in validations:
        validations.append(item)
rollback = bullets(section("ROLLBACK")) or ["Use the verified pre-change Spot Core backup artifact generated immediately before any future mutation."]
summary = bullets(section("SUMMARY")) or ["Derive exact future mutation steps from the approved proposal during manual review."]

plan_id = f"APPLY-{id_}"
out = out_dir / f"{plan_id}.md"
now = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")

def emit_list(items):
    return "\n".join(f"- {x}" for x in items)

content = f"""# Spot Apply Plan {plan_id}

linked_proposal: {id_}
approved_utc: {approved}
generated_utc: {now}
task: {task}
risk_class: {risk}
apply_status: pending_manual_review
mutation_allowed: false
backup_required: true
backup_bound: false
backup_artifact: pending
policy_class: supervised_apply_plan
autonomy_level: 1
execution_wrapper_required: true
executor: spot-core-controlled-wrapper
approval_gate: human_review_required
rollback_required: true
rollback_authority: recorded_prechange_backup_only

---

TARGET_FILES
{emit_list(targets)}

PRECHANGE_BACKUP_REQUIREMENTS
- Before any future mutation, Spot Core must create and verify a pre-change backup on Unimatrix.
- Required backup root: /mnt/collective/backups/<target>/<service>/<timestamp>/
- Backup path must be recorded in the action log before execution begins.
- If backup creation or verification fails, execution remains blocked.

PRECHECK_VALIDATION
{emit_list(validations)}

PLANNED_MUTATIONS
{emit_list(summary)}
- This apply plan does not execute mutations.
- Future execution must route through Spot Core policy/enforcement wrappers.

POST_APPLY_VALIDATION
{emit_list(validations)}

ROLLBACK_PLAN
{emit_list(rollback)}
- Rollback must use the recorded pre-change backup artifact.
- Rollback must be validated with the same post-apply validation commands.

HUMAN_REVIEW_GATE
- Confirm proposal is still approved and matches current runtime state.
- Confirm target files still exist and match expected live paths.
- Confirm risk class is correct under Spot Autonomy Policy.
- Confirm backup, validation, and rollback instructions are sufficient before any mutation.

NOTES
- Generated artifact is non-mutating.
- Memory and proposal history inform context but do not authorize execution.
- No high-risk network/firewall/DNS/DHCP/VLAN/routing mutation is authorized by this artifact.
"""
out.write_text(content)
print(out)
PY

  local rc=$?
  [[ $rc -eq 0 ]] || exit "$rc"
  local id plan_file
  id="$(basename "$file" .md)"
  plan_file="${BASE_DIR}/apply-plans/APPLY-${id}.md"
  memory_append roadmap "generated supervised apply plan APPLY-${id}"
  memory_append session "apply plan generated from approved proposal ${id}"
  echo "[apply-plan-generated] $plan_file"
}

cmd_generate_patch(){
  echo "[legacy-alias] generate-patch now generates a supervised apply plan" >&2
  cmd_generate_apply_plan "$@"
}

resolve_apply_plan_file(){
  local id="${1:-}"
  [[ -n "$id" ]] || { echo "ERROR: apply-plan id/file required" >&2; exit 2; }

  local file="$id"
  [[ -f "$file" ]] || file="${BASE_DIR}/apply-plans/${id%.md}.md"
  [[ -f "$file" ]] || file="${BASE_DIR}/apply-plans/APPLY-${id#APPLY-}.md"

  [[ -f "$file" ]] || { echo "ERROR: apply-plan not found: $id" >&2; exit 2; }
  printf '%s' "$file"
}

cmd_apply_plans(){
  local count="${1:-20}"
  mkdir -p "${BASE_DIR}/apply-plans"
  find "${BASE_DIR}/apply-plans" -maxdepth 1 -type f -name 'APPLY-*.md' -printf '%T@ %f\n' 2>/dev/null \
    | sort -nr \
    | head -n "$count" \
    | awk '{print $2}'
}

cmd_show_apply_plan(){
  local file
  file="$(resolve_apply_plan_file "${1:-}")"
  cat "$file"
}

cmd_apply_plan_status(){
  local file
  file="$(resolve_apply_plan_file "${1:-}")"
  grep -E '^(linked_proposal:|approved_utc:|generated_utc:|task:|risk_class:|apply_status:|mutation_allowed:|backup_required:|backup_bound:|backup_artifact:|policy_class:|autonomy_level:|execution_wrapper_required:|executor:|approval_gate:|rollback_required:|rollback_authority:)' "$file"
}

cmd_apply_plan_check(){
  local file
  file="$(resolve_apply_plan_file "${1:-}")"

  python3 - "$file" <<'PYINNER'
from pathlib import Path
import re, sys

path = Path(sys.argv[1])
text = path.read_text(errors="ignore")
fail = []
warn = []

def has_line(pattern):
    return re.search(pattern, text, re.M) is not None

def section(name):
    m = re.search(rf'^{re.escape(name)}\s*\n(?P<body>.*?)(?=\n[A-Z_]+\s*\n|\Z)', text, re.M | re.S)
    return m.group("body").strip() if m else ""

if not has_line(r'^mutation_allowed:\s*false\s*$'):
    fail.append("mutation_allowed must be false")

if not has_line(r'^apply_status:\s*pending_manual_review\s*$'):
    fail.append("apply_status must be pending_manual_review")

targets = section("TARGET_FILES")
if not targets:
    fail.append("TARGET_FILES section missing or empty")
else:
    for raw in targets.splitlines():
        item = raw.strip()
        if not item.startswith("- "):
            continue
        target = item[2:].strip().strip("`")
        if target.startswith("/") and not Path(target).exists():
            fail.append(f"target file missing: {target}")

validations = section("PRECHECK_VALIDATION")
if not validations:
    fail.append("PRECHECK_VALIDATION section missing or empty")
else:
    required = [
        "python3 -m json.tool /home/ogre/spot-stack/spot-core/config/cluster_config.json >/dev/null",
        "spot validate",
        'spot ask "show worker latency"',
        'spot ask "what is the current fleet status"',
        'spot ask "show current routing audit"',
    ]
    for cmd in required:
        if cmd not in validations:
            fail.append(f"required validation missing: {cmd}")

if not section("POST_APPLY_VALIDATION"):
    fail.append("POST_APPLY_VALIDATION section missing or empty")

if not section("ROLLBACK_PLAN"):
    fail.append("ROLLBACK_PLAN section missing or empty")

if not section("HUMAN_REVIEW_GATE"):
    fail.append("HUMAN_REVIEW_GATE section missing or empty")

if "Generated artifact is non-mutating" not in text:
    warn.append("non-mutating note missing")

for item in warn:
    print(f"[WARN] {item}")

for item in fail:
    print(f"[FAIL] {item}")

if fail:
    print(f"RESULT: FAIL fail={len(fail)} warn={len(warn)}")
    raise SystemExit(1)

print(f"RESULT: PASS fail=0 warn={len(warn)}")
PYINNER
}

cmd_apply_plan_verify(){
  local file
  file="$(resolve_apply_plan_file "${1:-}")"

  python3 - "$file" <<'PYINNER'
from pathlib import Path
import re, sys

path = Path(sys.argv[1])
text = path.read_text(errors="ignore")
fail = []
warn = []

def line_value(name):
    m = re.search(rf'^{re.escape(name)}:\s*(.+?)\s*$', text, re.M)
    return m.group(1).strip() if m else ""

def section(name):
    m = re.search(rf'^{re.escape(name)}\s*\n(?P<body>.*?)(?=\n[A-Z_]+\s*\n|\Z)', text, re.M | re.S)
    return m.group("body").strip() if m else ""

status = line_value("apply_status")
mutation_allowed = line_value("mutation_allowed")

if mutation_allowed != "false":
    fail.append("mutation_allowed must be false")

if line_value("backup_required") != "true":
    fail.append("backup_required must be true")

if line_value("backup_bound") != "false":
    fail.append("backup_bound must be false until a future Spot Core execution wrapper binds a verified backup")

if line_value("backup_artifact") != "pending":
    fail.append("backup_artifact must be pending before controlled execution")

expected_contract = {
    "policy_class": "supervised_apply_plan",
    "autonomy_level": "1",
    "execution_wrapper_required": "true",
    "executor": "spot-core-controlled-wrapper",
    "approval_gate": "human_review_required",
    "rollback_required": "true",
    "rollback_authority": "recorded_prechange_backup_only",
}

for k, v in expected_contract.items():
    if line_value(k) != v:
        fail.append(f"{k} must be {v}")

if status not in {"pending_manual_review", "review_approved"}:
    fail.append(f"apply_status must be pending_manual_review or review_approved, got: {status or '<missing>'}")

if status == "review_approved" and not line_value("review_approved_utc"):
    fail.append("review_approved_utc required when apply_status is review_approved")

required_sections = [
    "TARGET_FILES",
    "PRECHANGE_BACKUP_REQUIREMENTS",
    "PRECHECK_VALIDATION",
    "PLANNED_MUTATIONS",
    "POST_APPLY_VALIDATION",
    "ROLLBACK_PLAN",
    "HUMAN_REVIEW_GATE",
    "NOTES",
]

for name in required_sections:
    if not section(name):
        fail.append(f"{name} section missing or empty")

targets = section("TARGET_FILES")
for raw in targets.splitlines():
    item = raw.strip()
    if not item.startswith("- "):
        continue
    target = item[2:].strip().strip("`")
    if target.startswith("/") and not Path(target).exists():
        fail.append(f"target file missing: {target}")

validations = section("PRECHECK_VALIDATION")
required_validations = [
    "python3 -m json.tool /home/ogre/spot-stack/spot-core/config/cluster_config.json >/dev/null",
    "spot validate",
    'spot ask "show worker latency"',
    'spot ask "what is the current fleet status"',
    'spot ask "show current routing audit"',
]
for cmd in required_validations:
    if cmd not in validations:
        fail.append(f"required validation missing: {cmd}")

if "Spot Core must create and verify a pre-change backup" not in text:
    fail.append("backup-first requirement missing")

if "Generated artifact is non-mutating" not in text:
    warn.append("non-mutating note missing")

for item in warn:
    print(f"[WARN] {item}")

for item in fail:
    print(f"[FAIL] {item}")

if fail:
    print(f"RESULT: FAIL fail={len(fail)} warn={len(warn)}")
    raise SystemExit(1)

print(f"RESULT: PASS status={status} fail=0 warn={len(warn)}")
PYINNER
}

set_apply_plan_status(){
  local file="$1"
  local status="$2"
  local stamp_field="$3"

  python3 - "$file" "$status" "$stamp_field" <<'PYINNER'
from pathlib import Path
from datetime import datetime, UTC
import re, sys

path = Path(sys.argv[1])
status = sys.argv[2]
stamp_field = sys.argv[3]
text = path.read_text(errors="ignore")
now = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")

if not re.search(r'^mutation_allowed:\s*false\s*$', text, re.M):
    raise SystemExit("ERROR: refusing lifecycle update because mutation_allowed is not false")

m = re.search(r'^apply_status:\s*(.+?)\s*$', text, re.M)
current_status = m.group(1).strip() if m else "pending_manual_review"

allowed = {
    ("pending_manual_review", "review_approved"),
    ("pending_manual_review", "review_rejected"),
    ("review_approved", "handoff_prepared"),
}

if (current_status, status) not in allowed:
    raise SystemExit(f"ERROR: illegal apply-plan lifecycle transition {current_status} -> {status}")

if re.search(rf'^{re.escape(stamp_field)}:\s*.*$', text, re.M):
    raise SystemExit(f"ERROR: refusing lifecycle update because {stamp_field} already exists")

if re.search(r'^apply_status:\s*.*$', text, re.M):
    text = re.sub(r'^apply_status:\s*.*$', f'apply_status: {status}', text, count=1, flags=re.M)
else:
    text = text.replace('mutation_allowed: false', f'apply_status: {status}\nmutation_allowed: false', 1)

if re.search(rf'^{re.escape(stamp_field)}:\s*.*$', text, re.M):
    text = re.sub(rf'^{re.escape(stamp_field)}:\s*.*$', f'{stamp_field}: {now}', text, count=1, flags=re.M)
else:
    text = text.replace(f'apply_status: {status}', f'apply_status: {status}\n{stamp_field}: {now}', 1)

path.write_text(text)
print(path)
PYINNER
}

cmd_approve_apply_plan(){
  local file
  file="$(resolve_apply_plan_file "${1:-}")"
  cmd_apply_plan_check "$file" >/dev/null
  set_apply_plan_status "$file" review_approved review_approved_utc
  memory_append decision "review approved apply plan $(basename "$file" .md)"
  echo "[apply-plan-review-approved] $file"
}

cmd_reject_apply_plan(){
  local file
  file="$(resolve_apply_plan_file "${1:-}")"
  set_apply_plan_status "$file" review_rejected review_rejected_utc
  memory_append decision "review rejected apply plan $(basename "$file" .md)"
  echo "[apply-plan-review-rejected] $file"
}

cmd_prepare_execution_handoff(){
  local file
  file="$(resolve_apply_plan_file "${1:-}")"

  # Reviewed artifacts must pass general verification before a handoff is generated.
  cmd_apply_plan_verify "$file" >/dev/null

  python3 - "$file" "${BASE_DIR}/execution-handoffs" <<'PYINNER'
from pathlib import Path
from datetime import datetime, UTC
import re, sys

plan = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)

text = plan.read_text(errors="ignore")
plan_id = plan.stem
handoff_id = f"HANDOFF-{plan_id}"
out = out_dir / f"{handoff_id}.md"
now = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")

def line_value(name):
    m = re.search(rf'^{re.escape(name)}:\s*(.+?)\s*$', text, re.M)
    return m.group(1).strip() if m else ""

def section(name):
    m = re.search(rf'^{re.escape(name)}\s*\n(?P<body>.*?)(?=\n[A-Z_]+\s*\n|\Z)', text, re.M | re.S)
    return m.group("body").strip() if m else ""

def copy_section(name):
    body = section(name)
    return body if body else "- missing"

status = line_value("apply_status")
mutation_allowed = line_value("mutation_allowed")
backup_required = line_value("backup_required")
backup_bound = line_value("backup_bound")
backup_artifact = line_value("backup_artifact")

if status != "review_approved":
    raise SystemExit(f"ERROR: execution handoff requires apply_status review_approved, got {status or '<missing>'}")

if mutation_allowed != "false":
    raise SystemExit("ERROR: refusing handoff because mutation_allowed is not false")

if backup_required != "true" or backup_bound != "false" or backup_artifact != "pending":
    raise SystemExit("ERROR: backup binding metadata is not in pre-execution pending state")

content = f"""# Spot Execution Handoff {handoff_id}

linked_apply_plan: {plan_id}
linked_proposal: {line_value("linked_proposal")}
generated_utc: {now}
apply_status: {status}
risk_class: {line_value("risk_class")}
execution_allowed: false
mutation_allowed: false
backup_required: {backup_required}
backup_bound: {backup_bound}
backup_artifact: {backup_artifact}
policy_class: controlled_execution_handoff
autonomy_level: 1
execution_wrapper_required: true
executor: spot-core-controlled-wrapper
approval_gate: wrapper_execution_approval_required
rollback_required: true
rollback_authority: recorded_prechange_backup_only

---

PURPOSE
- Prepare reviewed apply-plan context for a future Spot Core controlled execution wrapper.
- This artifact does not authorize execution.
- This artifact does not mutate files.
- This artifact does not bind a backup.

FUTURE_EXECUTION_REQUIREMENTS
- Spot Core must create and verify a pre-change backup before mutation.
- Spot Core must record the verified backup artifact path before execution.
- Spot Core must execute through a controlled policy/enforcement wrapper.
- Spot Core must run post-apply validation.
- Spot Core must rollback from the recorded backup artifact if validation fails.

TARGET_FILES
{copy_section("TARGET_FILES")}

PRECHANGE_BACKUP_REQUIREMENTS
{copy_section("PRECHANGE_BACKUP_REQUIREMENTS")}

PRECHECK_VALIDATION
{copy_section("PRECHECK_VALIDATION")}

PLANNED_MUTATIONS
{copy_section("PLANNED_MUTATIONS")}

POST_APPLY_VALIDATION
{copy_section("POST_APPLY_VALIDATION")}

ROLLBACK_PLAN
{copy_section("ROLLBACK_PLAN")}

HUMAN_REVIEW_GATE
{copy_section("HUMAN_REVIEW_GATE")}

POLICY_GATES
- No backup, no change.
- Detect -> Analyze -> Classify -> Backup -> Plan -> Verify -> Execute -> Test/Rollback.
- Execution remains blocked until a future Spot Core wrapper binds backup_artifact and changes execution_allowed under policy.
- Memory and proposal history are context only, not authorization.

NOTES
- Generated from apply-plan: {plan.name}
- Current handoff state is non-executing.
"""
out.write_text(content)
print(out)
PYINNER

  local rc=$?
  [[ $rc -eq 0 ]] || exit "$rc"

  local id handoff_file
  id="$(basename "$file" .md)"
  handoff_file="${BASE_DIR}/execution-handoffs/HANDOFF-${id}.md"
  set_apply_plan_status "$file" handoff_prepared handoff_prepared_utc
  memory_append roadmap "prepared non-mutating execution handoff HANDOFF-${id}"
  memory_append session "execution handoff prepared from reviewed apply plan ${id}"
  echo "[execution-handoff-prepared] $handoff_file"
}

resolve_execution_handoff_file(){
  local id="${1:-}"
  [[ -n "$id" ]] || { echo "ERROR: execution handoff id/file required" >&2; exit 2; }

  local file="$id"
  [[ -f "$file" ]] || file="${BASE_DIR}/execution-handoffs/${id%.md}.md"
  [[ -f "$file" ]] || file="${BASE_DIR}/execution-handoffs/HANDOFF-${id#HANDOFF-}.md"

  [[ -f "$file" ]] || { echo "ERROR: execution handoff not found: $id" >&2; exit 2; }
  printf '%s' "$file"
}

cmd_execution_handoff_verify(){
  local file
  file="$(resolve_execution_handoff_file "${1:-}")"

  python3 - "$file" "${BASE_DIR}" <<'PYINNER'
from pathlib import Path
import re, sys

handoff = Path(sys.argv[1])
base = Path(sys.argv[2])
text = handoff.read_text(errors="ignore")
fail = []
warn = []

def line_value(name):
    m = re.search(rf'^{re.escape(name)}:\s*(.+?)\s*$', text, re.M)
    return m.group(1).strip() if m else ""

def section(name):
    m = re.search(rf'^{re.escape(name)}\s*\n(?P<body>.*?)(?=\n[A-Z_]+\s*\n|\Z)', text, re.M | re.S)
    return m.group("body").strip() if m else ""

expected = {
    "execution_allowed": "false",
    "mutation_allowed": "false",
    "backup_required": "true",
    "backup_bound": "false",
    "policy_class": "controlled_execution_handoff",
    "autonomy_level": "1",
    "execution_wrapper_required": "true",
    "executor": "spot-core-controlled-wrapper",
    "approval_gate": "wrapper_execution_approval_required",
    "rollback_required": "true",
    "rollback_authority": "recorded_prechange_backup_only",
    "backup_artifact": "pending",
}

for key, value in expected.items():
    actual = line_value(key)
    if actual != value:
        fail.append(f"{key} must be {value}, got {actual or '<missing>'}")

apply_plan = line_value("linked_apply_plan")
proposal = line_value("linked_proposal")

if not apply_plan:
    fail.append("linked_apply_plan missing")
else:
    apply_path = base / "apply-plans" / f"{apply_plan}.md"
    if not apply_path.exists():
        fail.append(f"linked apply-plan missing: {apply_path}")

if not proposal:
    fail.append("linked_proposal missing")
else:
    proposal_path = base / "proposals" / f"{proposal}.md"
    if not proposal_path.exists():
        fail.append(f"linked proposal missing: {proposal_path}")

required_sections = [
    "PURPOSE",
    "FUTURE_EXECUTION_REQUIREMENTS",
    "TARGET_FILES",
    "PRECHANGE_BACKUP_REQUIREMENTS",
    "PRECHECK_VALIDATION",
    "PLANNED_MUTATIONS",
    "POST_APPLY_VALIDATION",
    "ROLLBACK_PLAN",
    "HUMAN_REVIEW_GATE",
    "POLICY_GATES",
    "NOTES",
]

for name in required_sections:
    if not section(name):
        fail.append(f"{name} section missing or empty")

validations = section("PRECHECK_VALIDATION")
required_validations = [
    "python3 -m json.tool /home/ogre/spot-stack/spot-core/config/cluster_config.json >/dev/null",
    "spot validate",
    'spot ask "show worker latency"',
    'spot ask "what is the current fleet status"',
    'spot ask "show current routing audit"',
]
for cmd in required_validations:
    if cmd not in validations:
        fail.append(f"required validation missing: {cmd}")

policy = section("POLICY_GATES")
for phrase in [
    "No backup, no change.",
    "Execution remains blocked",
    "Memory and proposal history are context only, not authorization.",
]:
    if phrase not in policy:
        fail.append(f"policy gate missing: {phrase}")

if "This artifact does not authorize execution." not in text:
    warn.append("explicit non-authorization sentence missing")

for item in warn:
    print(f"[WARN] {item}")

for item in fail:
    print(f"[FAIL] {item}")

if fail:
    print(f"RESULT: FAIL fail={len(fail)} warn={len(warn)}")
    raise SystemExit(1)

print(f"RESULT: PASS fail=0 warn={len(warn)}")
PYINNER
}

cmd_execution_handoffs(){
  local count="${1:-20}"
  mkdir -p "${BASE_DIR}/execution-handoffs"
  find "${BASE_DIR}/execution-handoffs" -maxdepth 1 -type f -name 'HANDOFF-*.md' -printf '%T@ %f\n' 2>/dev/null \
    | sort -nr \
    | head -n "$count" \
    | awk '{print $2}'
}

cmd_show_execution_handoff(){
  local file
  file="$(resolve_execution_handoff_file "${1:-}")"
  cat "$file"
}

cmd_execution_handoff_status(){
  local file
  file="$(resolve_execution_handoff_file "${1:-}")"
  grep -E '^(linked_apply_plan:|linked_proposal:|generated_utc:|apply_status:|risk_class:|execution_allowed:|mutation_allowed:|backup_required:|backup_bound:|backup_artifact:|policy_class:|autonomy_level:|execution_wrapper_required:|executor:|approval_gate:|rollback_required:|rollback_authority:)' "$file"
}


cmd_execute_handoff(){
  local apply_wrapper="${BASE_DIR}/spot-apply.sh"
  [[ -f "$apply_wrapper" ]] || { echo "ERROR: spot apply wrapper missing: $apply_wrapper" >&2; exit 2; }
  bash "$apply_wrapper" execute-handoff "$@"
}

cmd_execution_runs(){
  local apply_wrapper="${BASE_DIR}/spot-apply.sh"
  [[ -f "$apply_wrapper" ]] || { echo "ERROR: spot apply wrapper missing: $apply_wrapper" >&2; exit 2; }
  bash "$apply_wrapper" runs "$@"
}

cmd_show_execution_run(){
  local apply_wrapper="${BASE_DIR}/spot-apply.sh"
  [[ -f "$apply_wrapper" ]] || { echo "ERROR: spot apply wrapper missing: $apply_wrapper" >&2; exit 2; }
  bash "$apply_wrapper" show-run "$@"
}

cmd_execution_run_verify(){
  local apply_wrapper="${BASE_DIR}/spot-apply.sh"
  [[ -f "$apply_wrapper" ]] || { echo "ERROR: spot apply wrapper missing: $apply_wrapper" >&2; exit 2; }
  bash "$apply_wrapper" verify-run "$@"
}

cmd_execution_run_status(){
  local apply_wrapper="${BASE_DIR}/spot-apply.sh"
  [[ -f "$apply_wrapper" ]] || { echo "ERROR: spot apply wrapper missing: $apply_wrapper" >&2; exit 2; }
  bash "$apply_wrapper" status-run "$@"
}

cmd_execution_run_audit(){
  local apply_wrapper="${BASE_DIR}/spot-apply.sh"
  [[ -f "$apply_wrapper" ]] || { echo "ERROR: spot apply wrapper missing: $apply_wrapper" >&2; exit 2; }
  bash "$apply_wrapper" audit-run "$@"
}

cmd_execution_run_summary(){
  local apply_wrapper="${BASE_DIR}/spot-apply.sh"
  [[ -f "$apply_wrapper" ]] || { echo "ERROR: spot apply wrapper missing: $apply_wrapper" >&2; exit 2; }
  bash "$apply_wrapper" summary-runs "$@"
}

cmd_execution_run_approve(){
  local apply_wrapper="${BASE_DIR}/spot-apply.sh"
  [[ -f "$apply_wrapper" ]] || { echo "ERROR: spot apply wrapper missing: $apply_wrapper" >&2; exit 2; }
  bash "$apply_wrapper" approve-run "$@"
}

cmd_execution_run_reject(){
  local apply_wrapper="${BASE_DIR}/spot-apply.sh"
  [[ -f "$apply_wrapper" ]] || { echo "ERROR: spot apply wrapper missing: $apply_wrapper" >&2; exit 2; }
  bash "$apply_wrapper" reject-run "$@"
}

resolve_action_request_file(){
  local id="${1:-}"
  [[ -n "$id" ]] || { echo "ERROR: action request id/file required" >&2; exit 2; }

  local dir="${BASE_DIR}/action-requests"
  local file="$id"
  [[ -f "$file" ]] || file="${dir}/${id%.json}.json"
  [[ -f "$file" ]] || file="${dir}/ACTION-${id#ACTION-}.json"

  [[ -f "$file" ]] || { echo "ERROR: action request not found: $id" >&2; exit 2; }
  printf '%s' "$file"
}

cmd_create_action_request(){
  local action_class="${1:-}"
  local target="${2:-}"
  shift 2 || true
  local summary="$*"

  [[ -n "$action_class" ]] || { echo "ERROR: action_class required" >&2; exit 2; }
  [[ -n "$target" ]] || { echo "ERROR: target required" >&2; exit 2; }
  [[ -n "$summary" ]] || { echo "ERROR: summary required" >&2; exit 2; }

  local policy_file="${BASE_DIR}/policy/action-policy.json"
  [[ -f "$policy_file" ]] || { echo "ERROR: action policy missing: $policy_file" >&2; exit 2; }

  mkdir -p "${BASE_DIR}/action-requests"

  python3 - "$policy_file" "${BASE_DIR}/action-requests" "$action_class" "$target" "$summary" <<'PYINNER'
import json
import re
import sys
from pathlib import Path
from datetime import datetime, UTC

policy_file, out_dir, action_class, target, summary = sys.argv[1:]
policy = json.loads(Path(policy_file).read_text())
classes = policy.get("action_classes", {})

if action_class not in classes:
    raise SystemExit(f"ERROR: action class not defined in policy: {action_class}")

spec = classes[action_class]
if spec.get("status") in {"forbidden", "restricted_disabled"}:
    raise SystemExit(f"ERROR: action class is not requestable: {action_class} status={spec.get('status')}")

now = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
safe = re.sub(r"[^a-zA-Z0-9_.-]+", "-", f"{action_class}-{target}")[:80].strip("-") or action_class
request_id = f"ACTION-{now}-{safe}"
out = Path(out_dir) / f"{request_id}.json"

request = {
    "schema": "spot.action_request.v1",
    "request_id": request_id,
    "created_utc": now,
    "action_class": action_class,
    "target": target,
    "summary": summary,
    "risk_class": spec.get("risk_class"),
    "request_status": "draft_non_executing",
    "policy_status": policy.get("policy_status"),
    "primary_rule": policy.get("primary_rule"),
    "autonomy_level": policy.get("autonomy_level_current"),
    "mutation_plugins_enabled": policy.get("mutation_plugins_enabled"),
    "execution_allowed": False,
    "mutation_allowed": False,
    "mutation_performed": False,
    "backup_required": spec.get("backup_required"),
    "backup_bound": False,
    "backup_artifact": "pending",
    "approval_required": spec.get("approval_required"),
    "rollback_required": action_class not in {"read_only_diagnostic"},
    "rollback_authority": "recorded_prechange_backup_only",
    "source_policy": policy.get("source_policy"),
    "execution_chain_required": policy.get("execution_chain_required"),
    "notes": [
        "This artifact is a request only.",
        "This artifact does not authorize execution.",
        "This artifact does not perform mutation.",
        "Future execution requires policy verification, backup binding, and explicit wrapper gating."
    ]
}

out.write_text(json.dumps(request, indent=2) + "\n")
print(out)
PYINNER
}

cmd_action_requests(){
  local count="${1:-20}"
  local dir="${BASE_DIR}/action-requests"
  mkdir -p "$dir"
  find "$dir" -maxdepth 1 -type f -name 'ACTION-*.json' -printf '%T@ %f\n' 2>/dev/null \
    | sort -nr \
    | head -n "$count" \
    | awk '{print $2}'
}

cmd_show_action_request(){
  local file
  file="$(resolve_action_request_file "${1:-}")"
  python3 -m json.tool "$file"
}

cmd_action_request_verify(){
  local file policy_file
  file="$(resolve_action_request_file "${1:-}")"
  policy_file="${BASE_DIR}/policy/action-policy.json"
  [[ -f "$policy_file" ]] || { echo "ERROR: action policy missing: $policy_file" >&2; exit 2; }

  python3 - "$file" "$policy_file" <<'PYINNER'
import json
import sys
from pathlib import Path

request = json.loads(Path(sys.argv[1]).read_text())
policy = json.loads(Path(sys.argv[2]).read_text())
fail = []
warn = []

def expect(path, actual, expected):
    if actual != expected:
        fail.append(f"{path} must be {expected!r}, got {actual!r}")

expect("schema", request.get("schema"), "spot.action_request.v1")
if request.get("request_status") not in {
    "draft_non_executing",
    "review_approved_non_executing",
    "review_rejected",
    "closed_no_execution",
}:
    fail.append(f"request_status invalid: {request.get('request_status')!r}")
expect("primary_rule", request.get("primary_rule"), "no_backup_no_change")
expect("policy_status", request.get("policy_status"), "locked")
expect("mutation_plugins_enabled", request.get("mutation_plugins_enabled"), False)
expect("execution_allowed", request.get("execution_allowed"), False)
expect("mutation_allowed", request.get("mutation_allowed"), False)
expect("mutation_performed", request.get("mutation_performed"), False)
expect("backup_bound", request.get("backup_bound"), False)
expect("backup_artifact", request.get("backup_artifact"), "pending")
expect("rollback_authority", request.get("rollback_authority"), "recorded_prechange_backup_only")

action_class = request.get("action_class")
classes = policy.get("action_classes", {})
spec = classes.get(action_class)

if not action_class:
    fail.append("action_class missing")
elif spec is None:
    fail.append(f"action_class not present in policy: {action_class}")
else:
    if spec.get("status") in {"forbidden", "restricted_disabled"}:
        fail.append(f"request uses non-requestable action_class: {action_class} status={spec.get('status')}")
    if request.get("risk_class") != spec.get("risk_class"):
        fail.append(f"risk_class must match policy class {action_class}: {spec.get('risk_class')}")
    if request.get("backup_required") != spec.get("backup_required"):
        fail.append(f"backup_required must match policy class {action_class}: {spec.get('backup_required')!r}")
    if request.get("approval_required") != spec.get("approval_required"):
        fail.append(f"approval_required must match policy class {action_class}: {spec.get('approval_required')!r}")

if policy.get("mutation_plugins_enabled") is not False:
    fail.append("source policy has mutation_plugins_enabled != false")

if request.get("source_policy") != policy.get("source_policy"):
    fail.append("source_policy mismatch")

if request.get("execution_chain_required") != policy.get("execution_chain_required"):
    fail.append("execution_chain_required mismatch")

notes = "\n".join(request.get("notes", []))
for phrase in [
    "request only",
    "does not authorize execution",
    "does not perform mutation",
]:
    if phrase not in notes:
        fail.append(f"required safety note missing: {phrase}")

for item in warn:
    print(f"[WARN] {item}")
for item in fail:
    print(f"[FAIL] {item}")

if fail:
    print(f"RESULT: FAIL fail={len(fail)} warn={len(warn)}")
    raise SystemExit(1)

print(f"RESULT: PASS request={request.get('request_id')} fail=0 warn={len(warn)}")
PYINNER
}

set_action_request_status(){
  local file="$1" new_status="$2" stamp_key="$3"

  python3 - "$file" "$new_status" "$stamp_key" <<'PYINNER'
import json
import sys
from pathlib import Path
from datetime import datetime, UTC

path = Path(sys.argv[1])
new_status = sys.argv[2]
stamp_key = sys.argv[3]

data = json.loads(path.read_text())
old_status = data.get("request_status")

allowed = {
    ("draft_non_executing", "review_approved_non_executing"),
    ("draft_non_executing", "review_rejected"),
    ("review_approved_non_executing", "closed_no_execution"),
    ("review_rejected", "closed_no_execution"),
}

if (old_status, new_status) not in allowed:
    raise SystemExit(f"ERROR: illegal action-request lifecycle transition {old_status} -> {new_status}")

if data.get("execution_allowed") is not False:
    raise SystemExit("ERROR: refusing lifecycle update because execution_allowed is not false")
if data.get("mutation_allowed") is not False:
    raise SystemExit("ERROR: refusing lifecycle update because mutation_allowed is not false")
if data.get("mutation_performed") is not False:
    raise SystemExit("ERROR: refusing lifecycle update because mutation_performed is not false")
if data.get(stamp_key):
    raise SystemExit(f"ERROR: refusing lifecycle update because {stamp_key} already exists")

data["request_status"] = new_status
data[stamp_key] = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
data.setdefault("lifecycle_history", []).append({
    "utc": data[stamp_key],
    "from": old_status,
    "to": new_status
})

path.write_text(json.dumps(data, indent=2) + "\n")
print(path)
PYINNER
}

cmd_action_request_status(){
  local file
  file="$(resolve_action_request_file "${1:-}")"
  python3 - "$file" <<'PYINNER'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())

keys = [
    "request_id",
    "created_utc",
    "action_class",
    "target",
    "risk_class",
    "request_status",
    "execution_allowed",
    "mutation_allowed",
    "mutation_performed",
    "backup_required",
    "backup_bound",
    "backup_artifact",
    "approval_required",
    "review_approved_utc",
    "review_rejected_utc",
    "closed_utc"
]

for key in keys:
    if key in data:
        print(f"{key}: {data[key]}")
PYINNER
}

cmd_approve_action_request(){
  local file
  file="$(resolve_action_request_file "${1:-}")"

  cmd_action_request_verify "$file" >/dev/null
  set_action_request_status "$file" "review_approved_non_executing" "review_approved_utc" >/dev/null

  echo "RESULT: APPROVED request=$(basename "$file" .json)"
}

cmd_reject_action_request(){
  local file
  file="$(resolve_action_request_file "${1:-}")"

  cmd_action_request_verify "$file" >/dev/null
  set_action_request_status "$file" "review_rejected" "review_rejected_utc" >/dev/null

  echo "RESULT: REJECTED request=$(basename "$file" .json)"
}

cmd_close_action_request(){
  local file
  file="$(resolve_action_request_file "${1:-}")"

  cmd_action_request_verify "$file" >/dev/null
  set_action_request_status "$file" "closed_no_execution" "closed_utc" >/dev/null

  echo "RESULT: CLOSED request=$(basename "$file" .json)"
}

cmd_action_request_audit(){
  local file
  file="$(resolve_action_request_file "${1:-}")"

  python3 - "$file" <<'PYINNER'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())

print("ACTION_REQUEST_AUDIT")
print(f"request_id: {data.get('request_id')}")
print(f"created_utc: {data.get('created_utc')}")
print(f"action_class: {data.get('action_class')}")
print(f"target: {data.get('target')}")
print(f"risk_class: {data.get('risk_class')}")
print(f"request_status: {data.get('request_status')}")
print(f"policy_status: {data.get('policy_status')}")
print(f"primary_rule: {data.get('primary_rule')}")
print(f"autonomy_level: {data.get('autonomy_level')}")
print(f"mutation_plugins_enabled: {str(data.get('mutation_plugins_enabled')).lower()}")
print(f"execution_allowed: {str(data.get('execution_allowed')).lower()}")
print(f"mutation_allowed: {str(data.get('mutation_allowed')).lower()}")
print(f"mutation_performed: {str(data.get('mutation_performed')).lower()}")
print(f"backup_required: {data.get('backup_required')}")
print(f"backup_bound: {str(data.get('backup_bound')).lower()}")
print(f"backup_artifact: {data.get('backup_artifact')}")
print(f"approval_required: {data.get('approval_required')}")
print(f"rollback_required: {data.get('rollback_required')}")
print(f"rollback_authority: {data.get('rollback_authority')}")
print(f"review_approved_utc: {data.get('review_approved_utc', '')}")
print(f"review_rejected_utc: {data.get('review_rejected_utc', '')}")
print(f"closed_utc: {data.get('closed_utc', '')}")

history = data.get("lifecycle_history", [])
print(f"lifecycle_events: {len(history)}")
for idx, item in enumerate(history, 1):
    print(f"- event_{idx}: utc={item.get('utc')} from={item.get('from')} to={item.get('to')}")
PYINNER
}

cmd_action_request_summary(){
  local count="${1:-10}"
  local dir="${BASE_DIR}/action-requests"
  mkdir -p "$dir"

  find "$dir" -maxdepth 1 -type f -name 'ACTION-*.json' -printf '%T@ %p\n' 2>/dev/null \
    | sort -nr \
    | head -n "$count" \
    | while read -r _ file; do
        python3 - "$file" <<'PYINNER'
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
data = json.loads(p.read_text())
print(
    f"{p.name} | "
    f"status={data.get('request_status')} | "
    f"class={data.get('action_class')} | "
    f"risk={data.get('risk_class')} | "
    f"target={data.get('target')} | "
    f"exec={str(data.get('execution_allowed')).lower()} | "
    f"mutation={str(data.get('mutation_allowed')).lower()}"
)
PYINNER
      done
}

resolve_action_handoff_file(){
  local id="${1:-}"
  [[ -n "$id" ]] || { echo "ERROR: action handoff id/file required" >&2; exit 2; }

  local dir="${BASE_DIR}/action-handoffs"
  local file="$id"
  [[ -f "$file" ]] || file="${dir}/${id%.json}.json"
  [[ -f "$file" ]] || file="${dir}/ACTION-HANDOFF-${id#ACTION-HANDOFF-}.json"

  [[ -f "$file" ]] || { echo "ERROR: action handoff not found: $id" >&2; exit 2; }
  printf '%s' "$file"
}

cmd_prepare_action_handoff(){
  local request_file policy_file
  request_file="$(resolve_action_request_file "${1:-}")"
  policy_file="${BASE_DIR}/policy/action-policy.json"
  [[ -f "$policy_file" ]] || { echo "ERROR: action policy missing: $policy_file" >&2; exit 2; }

  cmd_action_request_verify "$request_file" >/dev/null
  cmd_action_policy_verify >/dev/null

  mkdir -p "${BASE_DIR}/action-handoffs"

  python3 - "$request_file" "$policy_file" "${BASE_DIR}/action-handoffs" <<'PYINNER'
import json
import re
import sys
from pathlib import Path
from datetime import datetime, UTC

request_file, policy_file, out_dir = sys.argv[1:]
request = json.loads(Path(request_file).read_text())
policy = json.loads(Path(policy_file).read_text())

fail = []

if request.get("request_status") != "review_approved_non_executing":
    fail.append(f"request_status must be review_approved_non_executing, got {request.get('request_status')!r}")
if request.get("execution_allowed") is not False:
    fail.append("execution_allowed must be false")
if request.get("mutation_allowed") is not False:
    fail.append("mutation_allowed must be false")
if request.get("mutation_performed") is not False:
    fail.append("mutation_performed must be false")
if policy.get("mutation_plugins_enabled") is not False:
    fail.append("mutation_plugins_enabled must be false")
if request.get("action_class") not in policy.get("action_classes", {}):
    fail.append("action_class missing from policy")
else:
    spec = policy["action_classes"][request["action_class"]]
    if spec.get("status") in {"forbidden", "restricted_disabled"}:
        fail.append(f"action_class is not handoff-eligible: {request['action_class']} status={spec.get('status')}")

if fail:
    for item in fail:
        print(f"[FAIL] {item}", file=sys.stderr)
    raise SystemExit(1)

now = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
safe = re.sub(r"[^a-zA-Z0-9_.-]+", "-", request["request_id"])[:96].strip("-")
handoff_id = f"ACTION-HANDOFF-{now}-{safe}"
out = Path(out_dir) / f"{handoff_id}.json"

handoff = {
    "schema": "spot.action_handoff.v1",
    "handoff_id": handoff_id,
    "created_utc": now,
    "linked_action_request": request["request_id"],
    "action_class": request.get("action_class"),
    "target": request.get("target"),
    "summary": request.get("summary"),
    "risk_class": request.get("risk_class"),
    "handoff_status": "prepared_non_executing",
    "request_status_at_handoff": request.get("request_status"),
    "policy_status": policy.get("policy_status"),
    "primary_rule": policy.get("primary_rule"),
    "autonomy_level": policy.get("autonomy_level_current"),
    "mutation_plugins_enabled": policy.get("mutation_plugins_enabled"),
    "execution_allowed": False,
    "mutation_allowed": False,
    "mutation_performed": False,
    "backup_required": request.get("backup_required"),
    "backup_bound": False,
    "backup_artifact": "pending",
    "approval_required": request.get("approval_required"),
    "rollback_required": request.get("rollback_required"),
    "rollback_authority": "recorded_prechange_backup_only",
    "source_policy": policy.get("source_policy"),
    "execution_chain_required": policy.get("execution_chain_required"),
    "next_allowed_action": "manual_review_only",
    "notes": [
        "This artifact is a non-executing handoff candidate.",
        "This artifact does not authorize execution.",
        "This artifact does not perform mutation.",
        "Mutation plugin dispatch remains disabled.",
        "Future execution requires separate policy-approved wrapper gating and backup binding."
    ]
}

out.write_text(json.dumps(handoff, indent=2) + "\n")
print(out)
PYINNER
}

cmd_action_handoffs(){
  local count="${1:-20}"
  local dir="${BASE_DIR}/action-handoffs"
  mkdir -p "$dir"
  find "$dir" -maxdepth 1 -type f -name 'ACTION-HANDOFF-*.json' -printf '%T@ %f\n' 2>/dev/null \
    | sort -nr \
    | head -n "$count" \
    | awk '{print $2}'
}

cmd_show_action_handoff(){
  local file
  file="$(resolve_action_handoff_file "${1:-}")"
  python3 -m json.tool "$file"
}

cmd_action_handoff_status(){
  local file
  file="$(resolve_action_handoff_file "${1:-}")"
  python3 - "$file" <<'PYINNER'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
keys = [
    "handoff_id",
    "created_utc",
    "linked_action_request",
    "action_class",
    "target",
    "risk_class",
    "handoff_status",
    "request_status_at_handoff",
    "execution_allowed",
    "mutation_allowed",
    "mutation_performed",
    "backup_required",
    "backup_bound",
    "backup_artifact",
    "approval_required",
    "rollback_required",
    "next_allowed_action"
]
for key in keys:
    if key in data:
        print(f"{key}: {data[key]}")
PYINNER
}

cmd_action_handoff_verify(){
  local file policy_file req_file
  file="$(resolve_action_handoff_file "${1:-}")"
  policy_file="${BASE_DIR}/policy/action-policy.json"
  [[ -f "$policy_file" ]] || { echo "ERROR: action policy missing: $policy_file" >&2; exit 2; }

  python3 - "$file" "$policy_file" "${BASE_DIR}/action-requests" <<'PYINNER'
import json
import sys
from pathlib import Path

handoff = json.loads(Path(sys.argv[1]).read_text())
policy = json.loads(Path(sys.argv[2]).read_text())
request_dir = Path(sys.argv[3])
fail = []
warn = []

def expect(path, actual, expected):
    if actual != expected:
        fail.append(f"{path} must be {expected!r}, got {actual!r}")

expect("schema", handoff.get("schema"), "spot.action_handoff.v1")
if handoff.get("handoff_status") not in {
    "prepared_non_executing",
    "review_approved_non_executing",
    "review_rejected",
    "closed_no_execution",
}:
    fail.append(f"handoff_status invalid: {handoff.get('handoff_status')!r}")
expect("request_status_at_handoff", handoff.get("request_status_at_handoff"), "review_approved_non_executing")
expect("primary_rule", handoff.get("primary_rule"), "no_backup_no_change")
expect("policy_status", handoff.get("policy_status"), "locked")
expect("mutation_plugins_enabled", handoff.get("mutation_plugins_enabled"), False)
expect("execution_allowed", handoff.get("execution_allowed"), False)
expect("mutation_allowed", handoff.get("mutation_allowed"), False)
expect("mutation_performed", handoff.get("mutation_performed"), False)
expect("backup_bound", handoff.get("backup_bound"), False)
expect("backup_artifact", handoff.get("backup_artifact"), "pending")
expect("rollback_authority", handoff.get("rollback_authority"), "recorded_prechange_backup_only")
expect("next_allowed_action", handoff.get("next_allowed_action"), "manual_review_only")

if policy.get("mutation_plugins_enabled") is not False:
    fail.append("source policy mutation_plugins_enabled must be false")

action_class = handoff.get("action_class")
spec = policy.get("action_classes", {}).get(action_class)
if not spec:
    fail.append(f"action_class missing from policy: {action_class}")
else:
    if spec.get("status") in {"forbidden", "restricted_disabled"}:
        fail.append(f"action_class not handoff-eligible: {action_class} status={spec.get('status')}")
    if handoff.get("risk_class") != spec.get("risk_class"):
        fail.append("risk_class does not match policy")
    if handoff.get("backup_required") != spec.get("backup_required"):
        fail.append("backup_required does not match policy")
    if handoff.get("approval_required") != spec.get("approval_required"):
        fail.append("approval_required does not match policy")

linked = handoff.get("linked_action_request")
if not linked:
    fail.append("linked_action_request missing")
else:
    req_path = request_dir / f"{linked}.json"
    if not req_path.exists():
        fail.append(f"linked action request missing: {req_path}")
    else:
        req = json.loads(req_path.read_text())
        if req.get("request_status") != "review_approved_non_executing":
            warn.append(f"linked request current status is {req.get('request_status')!r}; handoff captured {handoff.get('request_status_at_handoff')!r}")

if handoff.get("execution_chain_required") != policy.get("execution_chain_required"):
    fail.append("execution_chain_required mismatch")

notes = "\n".join(handoff.get("notes", []))
for phrase in [
    "non-executing handoff candidate",
    "does not authorize execution",
    "does not perform mutation",
    "Mutation plugin dispatch remains disabled",
]:
    if phrase not in notes:
        fail.append(f"required safety note missing: {phrase}")

for item in warn:
    print(f"[WARN] {item}")
for item in fail:
    print(f"[FAIL] {item}")

if fail:
    print(f"RESULT: FAIL fail={len(fail)} warn={len(warn)}")
    raise SystemExit(1)

print(f"RESULT: PASS handoff={handoff.get('handoff_id')} fail=0 warn={len(warn)}")
PYINNER
}

set_action_handoff_status(){
  local file="$1" new_status="$2" stamp_key="$3"

  python3 - "$file" "$new_status" "$stamp_key" <<'PYINNER'
import json
import sys
from pathlib import Path
from datetime import datetime, UTC

path = Path(sys.argv[1])
new_status = sys.argv[2]
stamp_key = sys.argv[3]

data = json.loads(path.read_text())
old_status = data.get("handoff_status")

allowed = {
    ("prepared_non_executing", "review_approved_non_executing"),
    ("prepared_non_executing", "review_rejected"),
    ("review_approved_non_executing", "closed_no_execution"),
    ("review_rejected", "closed_no_execution"),
}

if (old_status, new_status) not in allowed:
    raise SystemExit(f"ERROR: illegal action-handoff lifecycle transition {old_status} -> {new_status}")

for key in ("execution_allowed", "mutation_allowed", "mutation_performed"):
    if data.get(key) is not False:
        raise SystemExit(f"ERROR: refusing lifecycle update because {key} is not false")

if data.get("mutation_plugins_enabled") is not False:
    raise SystemExit("ERROR: refusing lifecycle update because mutation_plugins_enabled is not false")

if data.get(stamp_key):
    raise SystemExit(f"ERROR: refusing lifecycle update because {stamp_key} already exists")

data["handoff_status"] = new_status
data[stamp_key] = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
data.setdefault("lifecycle_history", []).append({
    "utc": data[stamp_key],
    "from": old_status,
    "to": new_status
})

path.write_text(json.dumps(data, indent=2) + "\n")
print(path)
PYINNER
}

cmd_action_handoff_audit(){
  local file
  file="$(resolve_action_handoff_file "${1:-}")"

  python3 - "$file" <<'PYINNER'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())

print("ACTION_HANDOFF_AUDIT")
for key in [
    "handoff_id",
    "created_utc",
    "linked_action_request",
    "action_class",
    "target",
    "risk_class",
    "handoff_status",
    "request_status_at_handoff",
    "policy_status",
    "primary_rule",
    "autonomy_level",
    "mutation_plugins_enabled",
    "execution_allowed",
    "mutation_allowed",
    "mutation_performed",
    "backup_required",
    "backup_bound",
    "backup_artifact",
    "approval_required",
    "rollback_required",
    "rollback_authority",
    "next_allowed_action",
    "review_approved_utc",
    "review_rejected_utc",
    "closed_utc",
]:
    if key in data:
        v = data.get(key)
        if isinstance(v, bool):
            v = str(v).lower()
        print(f"{key}: {v}")

history = data.get("lifecycle_history", [])
print(f"lifecycle_events: {len(history)}")
for idx, item in enumerate(history, 1):
    print(f"- event_{idx}: utc={item.get('utc')} from={item.get('from')} to={item.get('to')}")
PYINNER
}

cmd_action_handoff_summary(){
  local count="${1:-10}"
  local dir="${BASE_DIR}/action-handoffs"
  mkdir -p "$dir"

  find "$dir" -maxdepth 1 -type f -name 'ACTION-HANDOFF-*.json' -printf '%T@ %p\n' 2>/dev/null \
    | sort -nr \
    | head -n "$count" \
    | while read -r _ file; do
        python3 - "$file" <<'PYINNER'
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
data = json.loads(p.read_text())
print(
    f"{p.name} | "
    f"status={data.get('handoff_status')} | "
    f"class={data.get('action_class')} | "
    f"risk={data.get('risk_class')} | "
    f"target={data.get('target')} | "
    f"exec={str(data.get('execution_allowed')).lower()} | "
    f"mutation={str(data.get('mutation_allowed')).lower()}"
)
PYINNER
      done
}

cmd_approve_action_handoff(){
  local file
  file="$(resolve_action_handoff_file "${1:-}")"

  cmd_action_handoff_verify "$file" >/dev/null
  set_action_handoff_status "$file" "review_approved_non_executing" "review_approved_utc" >/dev/null

  echo "RESULT: APPROVED handoff=$(basename "$file" .json)"
}

cmd_reject_action_handoff(){
  local file
  file="$(resolve_action_handoff_file "${1:-}")"

  cmd_action_handoff_verify "$file" >/dev/null
  set_action_handoff_status "$file" "review_rejected" "review_rejected_utc" >/dev/null

  echo "RESULT: REJECTED handoff=$(basename "$file" .json)"
}

cmd_close_action_handoff(){
  local file
  file="$(resolve_action_handoff_file "${1:-}")"

  cmd_action_handoff_verify "$file" >/dev/null
  set_action_handoff_status "$file" "closed_no_execution" "closed_utc" >/dev/null

  echo "RESULT: CLOSED handoff=$(basename "$file" .json)"
}

cmd_plugin_registry(){
  local registry_file="${BASE_DIR}/policy/plugin-registry.json"
  [[ -f "$registry_file" ]] || { echo "ERROR: plugin registry missing: $registry_file" >&2; exit 2; }

  if [[ "${1:-}" == "--json" ]]; then
    python3 -m json.tool "$registry_file"
    return 0
  fi

  python3 - "$registry_file" <<'PYINNER'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())

print(f"Plugin registry: {data['schema']}")
print(f"Status: {data['registry_status']}")
print(f"Primary rule: {data['primary_rule']}")
print(f"Mutation plugins enabled: {str(data['mutation_plugins_enabled']).lower()}")
print(f"Plugin execution enabled: {str(data['plugin_execution_enabled']).lower()}")
print()
print("Global guards:")
for k, v in data["global_guards"].items():
    print(f"- {k}: {v}")
print()
print("Plugins:")
for name, spec in data["plugins"].items():
    print(
        f"- {name}: "
        f"status={spec['status']} "
        f"class={spec['action_class']} "
        f"risk={spec['risk_class']} "
        f"exec={str(spec['execution_allowed']).lower()} "
        f"mutation={str(spec['mutation_allowed']).lower()}"
    )
PYINNER
}

cmd_plugin_registry_verify(){
  local registry_file="${BASE_DIR}/policy/plugin-registry.json"
  local policy_file="${BASE_DIR}/policy/action-policy.json"

  [[ -f "$registry_file" ]] || { echo "ERROR: plugin registry missing: $registry_file" >&2; exit 2; }
  [[ -f "$policy_file" ]] || { echo "ERROR: action policy missing: $policy_file" >&2; exit 2; }

  python3 - "$registry_file" "$policy_file" <<'PYINNER'
import json
import sys
from pathlib import Path

registry = json.loads(Path(sys.argv[1]).read_text())
policy = json.loads(Path(sys.argv[2]).read_text())
fail = []
warn = []

def expect(path, actual, expected):
    if actual != expected:
        fail.append(f"{path} must be {expected!r}, got {actual!r}")

expect("schema", registry.get("schema"), "spot.plugin_registry.v1")
expect("registry_status", registry.get("registry_status"), "locked_non_executing")
expect("primary_rule", registry.get("primary_rule"), "no_backup_no_change")
expect("mutation_plugins_enabled", registry.get("mutation_plugins_enabled"), False)
expect("plugin_execution_enabled", registry.get("plugin_execution_enabled"), False)

if policy.get("mutation_plugins_enabled") is not False:
    fail.append("linked action policy mutation_plugins_enabled must be false")

guards = registry.get("global_guards", {})
required_guards = {
    "backup_required_before_mutation": True,
    "backup_binding_required": True,
    "precheck_required": True,
    "postcheck_required": True,
    "rollback_contract_required": True,
    "append_only_action_log_required": True,
    "freeform_shell_forbidden": True,
    "network_mutation_forbidden": True,
    "backup_delete_allowed": False,
    "backup_overwrite_allowed": False,
}
for key, expected in required_guards.items():
    expect(f"global_guards.{key}", guards.get(key), expected)

plugins = registry.get("plugins", {})
if not plugins:
    fail.append("plugins map must not be empty")

policy_classes = policy.get("action_classes", {})

for name, spec in plugins.items():
    status = spec.get("status")
    action_class = spec.get("action_class")

    if action_class not in policy_classes:
        fail.append(f"{name}.action_class not found in action policy: {action_class}")
        continue

    policy_spec = policy_classes[action_class]

    if spec.get("risk_class") != policy_spec.get("risk_class"):
        fail.append(f"{name}.risk_class must match action policy class {action_class}")

    if spec.get("mutation_allowed") is not False:
        fail.append(f"{name}.mutation_allowed must be false")

    if spec.get("execution_allowed") is not False:
        fail.append(f"{name}.execution_allowed must be false")

    if status not in {"disabled", "forbidden"}:
        fail.append(f"{name}.status must be disabled or forbidden, got {status!r}")

    if policy_spec.get("status") in {"forbidden", "restricted_disabled"} and status != "forbidden":
        fail.append(f"{name}.status must be forbidden because action policy class {action_class} is {policy_spec.get('status')}")

for required in [
    "read_only_status_probe",
    "safe_service_restart",
    "controlled_config_write",
    "restore_from_backup",
    "network_change",
    "freeform_shell_mutation",
    "backup_delete_or_overwrite",
]:
    if required not in plugins:
        fail.append(f"required plugin placeholder missing: {required}")

for item in warn:
    print(f"[WARN] {item}")
for item in fail:
    print(f"[FAIL] {item}")

if fail:
    print(f"RESULT: FAIL fail={len(fail)} warn={len(warn)}")
    raise SystemExit(1)

print(f"RESULT: PASS fail=0 warn={len(warn)}")
PYINNER
}

cmd_action_policy_verify(){
  local policy_file="${BASE_DIR}/policy/action-policy.json"
  [[ -f "$policy_file" ]] || { echo "ERROR: action policy missing: $policy_file" >&2; exit 2; }

  python3 - "$policy_file" <<'PYINNER'
import json
import sys
from pathlib import Path

policy = json.loads(Path(sys.argv[1]).read_text())
fail = []
warn = []

def expect(path, actual, expected):
    if actual != expected:
        fail.append(f"{path} must be {expected!r}, got {actual!r}")

expect("schema", policy.get("schema"), "spot.action_policy.v1")
expect("policy_status", policy.get("policy_status"), "locked")
expect("primary_rule", policy.get("primary_rule"), "no_backup_no_change")
expect("mutation_plugins_enabled", policy.get("mutation_plugins_enabled"), False)

guards = policy.get("global_guards", {})
expect("global_guards.backup_required_before_mutation", guards.get("backup_required_before_mutation"), True)
expect("global_guards.backup_delete_allowed", guards.get("backup_delete_allowed"), False)
expect("global_guards.backup_overwrite_allowed", guards.get("backup_overwrite_allowed"), False)
expect("global_guards.logs_append_only", guards.get("logs_append_only"), True)
expect("global_guards.rollback_requires_recorded_artifact", guards.get("rollback_requires_recorded_artifact"), True)
expect("global_guards.high_risk_requires_approval", guards.get("high_risk_requires_approval"), True)

chain = policy.get("execution_chain_required", [])
required_chain = [
    "detect",
    "analyze",
    "classify",
    "backup",
    "plan",
    "verify",
    "execute",
    "test_or_rollback",
]
if chain != required_chain:
    fail.append(f"execution_chain_required must exactly match {required_chain!r}, got {chain!r}")

classes = policy.get("action_classes", {})

required_classes = [
    "read_only_diagnostic",
    "supervised_dry_run",
    "safe_service_restart",
    "controlled_config_write",
    "restore_from_backup",
    "network_change",
    "backup_delete_or_overwrite",
    "freeform_shell_mutation",
]
for name in required_classes:
    if name not in classes:
        fail.append(f"action class missing: {name}")

for name, spec in classes.items():
    if spec.get("mutation_allowed") is not False:
        fail.append(f"{name}.mutation_allowed must be false")

for name in ("backup_delete_or_overwrite", "freeform_shell_mutation"):
    spec = classes.get(name, {})
    if spec.get("status") != "forbidden":
        fail.append(f"{name}.status must be forbidden")
    if spec.get("approval_required") != "not_supported":
        fail.append(f"{name}.approval_required must be not_supported")

network = classes.get("network_change", {})
if network.get("status") not in {"restricted_disabled", "forbidden"}:
    fail.append("network_change.status must be restricted_disabled or forbidden")
if network.get("risk_class") != "high":
    fail.append("network_change.risk_class must be high")
if network.get("approval_required") is not True:
    fail.append("network_change.approval_required must be true")

if classes.get("read_only_diagnostic", {}).get("status") != "allowed":
    fail.append("read_only_diagnostic.status must be allowed")
if classes.get("supervised_dry_run", {}).get("status") != "allowed":
    fail.append("supervised_dry_run.status must be allowed")

for item in warn:
    print(f"[WARN] {item}")
for item in fail:
    print(f"[FAIL] {item}")

if fail:
    print(f"RESULT: FAIL fail={len(fail)} warn={len(warn)}")
    raise SystemExit(1)

print(f"RESULT: PASS fail=0 warn={len(warn)}")
PYINNER
}

cmd_action_policy(){
  local policy_file="${BASE_DIR}/policy/action-policy.json"
  [[ -f "$policy_file" ]] || { echo "ERROR: action policy missing: $policy_file" >&2; exit 2; }

  if [[ "${1:-}" == "--json" ]]; then
    python3 -m json.tool "$policy_file"
    return 0
  fi

  python3 - "$policy_file" <<'PYINNER'
import json, sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())

print(f"Action policy: {data['schema']}")
print(f"Status: {data['policy_status']}")
print(f"Primary rule: {data['primary_rule']}")
print(f"Current autonomy level: {data['autonomy_level_current']}")
print(f"Mutation plugins enabled: {str(data['mutation_plugins_enabled']).lower()}")
print()
print("Global guards:")
for k, v in data["global_guards"].items():
    print(f"- {k}: {v}")
print()
print("Action classes:")
for name, spec in data["action_classes"].items():
    print(f"- {name}: status={spec['status']} risk={spec['risk_class']} mutation_allowed={spec['mutation_allowed']} approval_required={spec['approval_required']}")
PYINNER
}

cmd_execution_run_close(){
  local apply_wrapper="${BASE_DIR}/spot-apply.sh"
  [[ -f "$apply_wrapper" ]] || { echo "ERROR: spot apply wrapper missing: $apply_wrapper" >&2; exit 2; }
  bash "$apply_wrapper" close-run "$@"
}

memory_append(){
  local kind="$1"; shift
  local msg="$*"
  local mem_dir="${SPOT_MEMORY_DIR}"
  mkdir -p "$mem_dir"
  local file="${mem_dir}/${kind}s.jsonl"
  python3 - "$file" "$kind" "$msg" <<'INNER'
from pathlib import Path
import sys, json
from datetime import datetime, UTC
p = Path(sys.argv[1])
kind = sys.argv[2]
msg = sys.argv[3]
if p.exists():
    for line in p.read_text().splitlines():
        try:
            row = json.loads(line)
            if row.get("type") == kind and row.get("text") == msg:
                raise SystemExit(10)
        except Exception:
            pass
entry = {"ts": datetime.now(UTC).strftime("%Y%m%d-%H%M%S"), "type": kind, "text": msg}
with p.open("a") as f:
    f.write(json.dumps(entry) + "\n")
INNER
  local rc=$?
  if [[ $rc -eq 10 ]]; then echo "[memory-skip-duplicate:$kind] $msg"; else echo "[remembered:$kind] $msg"; fi
}

cmd_remember(){ local kind="${1:-}"; shift || true; case "$kind" in fact|decision|session|preference|roadmap) ;; *) echo "ERROR: remember type must be fact|decision|session|preference|roadmap" >&2; exit 2;; esac; [[ $# -gt 0 ]] || { echo "ERROR: remember text required" >&2; exit 2; }; memory_append "$kind" "$*"; }
cmd_memory(){ local count="${1:-20}"; local mem_dir="${SPOT_MEMORY_DIR}"; mkdir -p "$mem_dir"; python3 - "$count" "$mem_dir" <<'INNER'
import sys, json
from pathlib import Path
count = int(sys.argv[1]); mem_dir = Path(sys.argv[2]); rows = []
for path in sorted(mem_dir.glob("*.jsonl")):
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line: continue
            try: rows.append(json.loads(line))
            except Exception: pass
    except FileNotFoundError: pass
rows.sort(key=lambda x: x.get("ts", ""), reverse=True)
for row in rows[:count]: print(f'{row.get("ts")} [{row.get("type")}] {row.get("text")}')
INNER
}
cmd_recall(){ local q="${*:-}"; [[ -n "$q" ]] || { echo "ERROR: recall keyword required" >&2; exit 2; }; local mem_dir="${SPOT_MEMORY_DIR}"; mkdir -p "$mem_dir"; python3 - "$q" "$mem_dir" <<'INNER'
import sys, json
from pathlib import Path
q = sys.argv[1].lower(); mem_dir = Path(sys.argv[2]); rows = []
for path in sorted(mem_dir.glob("*.jsonl")):
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line: continue
            try:
                row = json.loads(line)
                if q in f'{row.get("type","")} {row.get("text","")}'.lower(): rows.append(row)
            except Exception: pass
    except FileNotFoundError: pass
rows.sort(key=lambda x: x.get("ts",""), reverse=True)
if not rows: print(f'no memory matches for: {q}')
else:
    for row in rows: print(f'{row.get("ts")} [{row.get("type")}] {row.get("text")}')
INNER
}

memory_context_for_prompt(){ local q="${*:-}"; local mem_dir="${SPOT_MEMORY_DIR}"; mkdir -p "$mem_dir"; python3 - "$q" "$mem_dir" <<'INNER'
import sys, json, re
from pathlib import Path
q = sys.argv[1].lower(); mem_dir = Path(sys.argv[2]); tokens = [t for t in re.split(r'[^a-zA-Z0-9_.-]+', q) if len(t) >= 3]; rows = []
for path in sorted(mem_dir.glob("*.jsonl")):
    try:
        for line in path.read_text().splitlines():
            try: row = json.loads(line)
            except Exception: continue
            blob = f'{row.get("type","")} {row.get("text","")}'.lower(); score = sum(1 for t in tokens if t.lower() in blob)
            if score: rows.append((score, row))
    except FileNotFoundError: pass
rows.sort(key=lambda x: (x[0], x[1].get("ts","")), reverse=True)
if rows:
    print("RELEVANT_SPOT_MEMORY")
    for _, row in rows[:8]: print(f'- {row.get("ts")} [{row.get("type")}] {row.get("text")}')
INNER
}
with_memory_prompt(){ local user_prompt="$1"; local memory; memory="$(memory_context_for_prompt "$user_prompt" || true)"; if [[ -n "$memory" ]]; then cat <<EOF
You are Spot assistant mode. Durable prior Spot memory is provided below.
Use this memory when answering unless live telemetry or the current prompt clearly contradicts it.
If memory affects the answer, explicitly mention the relevant remembered fact or decision.

DURABLE_MEMORY_CONTEXT
${memory}

CURRENT_USER_PROMPT
${user_prompt}
EOF
else printf '%s' "$user_prompt"; fi; }

proposal_context_for_task(){ local q="${*:-}"; python3 - "$q" "${PROPOSAL_DIR}" "${BASE_DIR}/patches" "${BASE_DIR}/apply-plans" <<'INNER'
import sys, re
from pathlib import Path
q = sys.argv[1].lower(); proposal_dir = Path(sys.argv[2]); patch_dir = Path(sys.argv[3]); apply_dir = Path(sys.argv[4])
tokens = [t for t in re.split(r'[^a-zA-Z0-9_.-]+', q) if len(t) >= 3]
def score_blob(blob):
    blob = blob.lower(); return sum(1 for t in tokens if t in blob)
prop_hits=[]
for p in sorted(proposal_dir.glob("P-*.md")):
    txt=p.read_text(errors="ignore"); s=score_blob(txt+" "+p.name)
    if s:
        status="unknown"
        for line in txt.splitlines():
            if line.startswith("status:"): status=line.split(":",1)[1].strip(); break
        prop_hits.append((s,p.name,status))
patch_hits=[]
for d, prefix in [(patch_dir,"PATCH"),(apply_dir,"APPLY")]:
    for p in sorted(d.glob(f"{prefix}-*.md")):
        txt=p.read_text(errors="ignore"); s=score_blob(txt+" "+p.name)
        if s: patch_hits.append((s,p.name))
prop_hits.sort(reverse=True); patch_hits.sort(reverse=True)
if prop_hits:
    print("RELATED_PROPOSALS")
    for _, name, status in prop_hits[:5]: print(f'- {name} [{status}]')
if patch_hits:
    print("RELATED_ARTIFACTS")
    for _, name in patch_hits[:5]: print(f'- {name}')
INNER
}

cmd_ask(){
  need_cmd jq
  need_cmd curl

  local role="auto" model="" json_out=false use_memory=false args=()

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --role) role="${2:-}"; shift 2;;
      --model) model="${2:-}"; shift 2;;
      --json) json_out=true; shift;;
      --memory) use_memory=true; shift;;
      -h|--help) usage; exit 0;;
      --) shift; args+=("$@"); break;;
      *) args+=("$1"); shift;;
    esac
  done

  local prompt="$(join_prompt "${args[@]}")"
  [[ -n "$prompt" ]] || { echo "ERROR: prompt required" >&2; exit 2; }

  local intent="$(telemetry_intent "$prompt")"
  [[ "$intent" != none && "$role" == auto && -z "$model" ]] && {
    handle_telemetry_ask "$intent" "$json_out"
    return 0
  }

  [[ "$role" == auto ]] && role="$(classify_role "$prompt")"

  local llm_prompt result
  if [[ "$use_memory" == true ]]; then
    llm_prompt="$(with_memory_prompt "$prompt")"
  else
    llm_prompt="$prompt"
  fi

  result="$(call_exec "$role" "$model" "$llm_prompt")"
  [[ "$json_out" == true ]] && printf '%s
' "$result"|jq . || {
    printf '%s
' "$result"|jq -r '.response'
    print_route "$result"
  }
}

proposal_guardrail_check(){ local body="$1" bad=0; while IFS= read -r forbidden; do [[ -z "$forbidden" ]] && continue; if printf '%s
' "$body" | grep -Fq "$forbidden"; then echo "[proposal-warning] forbidden invented operation/path detected: $forbidden" >&2; bad=1; fi; done <<'EOF'
systemctl restart spot-client
systemctl restart spot-ops
spot-client.service
spot-ops.service
/home/ogre/spot-stack/bin/spot
/etc/config/worker-02.yaml
/home/ogre/spot-stack/config/cluster_config.json
EOF
return "$bad"; }

cmd_propose(){ need_cmd jq; need_cmd curl; local role="auto" json_out=false save=false args=(); while [[ $# -gt 0 ]]; do case "$1" in --role) role="${2:-}"; shift 2;; --json) json_out=true; shift;; --save) save=true; shift;; -h|--help) usage; exit 0;; --) shift; args+=("$@"); break;; *) args+=("$1"); shift;; esac; done; local task="$(join_prompt "${args[@]}")"; [[ -n "$task" ]] || { echo "ERROR: task required" >&2; exit 2; }; local mem related prompt result body; mem="$(memory_context_for_prompt "$task" || true)"; related="$(proposal_context_for_task "$task" || true)"; prompt="You are Spot proposal mode. Do not apply changes. Durable memory context and related historical engineering artifacts may be provided below. You must incorporate them when relevant unless contradicted by live telemetry. Avoid duplicating already-approved plans when a related approved proposal exists. Use exactly these section headers: SUMMARY, RISK_CLASS, FILES_AFFECTED, VALIDATION_COMMANDS, ROLLBACK, NEXT_SAFE_ACTION. Put 1-4 concrete bullets or lines under every section. Use canonical paths only. Use only allowed validation commands. Avoid every forbidden guess. Do not include DETAILS, PROPOSAL_CONTENT, sample JSON, or patch bodies unless explicitly asked.\n\n$(spot_context_block)\n\n${related}\n\nDURABLE_MEMORY_CONTEXT\n${mem}\n\nTASK: ${task}"; [[ "$role" == auto ]] && role="$(classify_role "$task")"; result="$(call_exec "$role" "" "$prompt")"; body="$(printf '%s
' "$result"|jq -r '.response')"; proposal_guardrail_check "$body" || true; if [[ "$json_out" == true ]]; then printf '%s
' "$result"|jq .; else printf '%s
' "$body"; print_route "$result"; fi; [[ "$save" == true ]] && save_proposal "$task" "$role" "$result" "$body"; }

cmd_proposals(){ local count="${1:-20}"; mkdir -p "$PROPOSAL_DIR"; find "$PROPOSAL_DIR" -maxdepth 1 -type f -name 'P-*.md' -printf '%T@ %f
' 2>/dev/null | sort -nr | head -n "$count" | awk '{print $2}'; }
cmd_show_proposal(){ local id="${1:-}"; [[ -n "$id" ]] || { echo "ERROR: proposal id/file required" >&2; exit 2; }; local file="$id"; [[ -f "$file" ]] || file="${PROPOSAL_DIR}/${id%.md}.md"; [[ -f "$file" ]] || { echo "ERROR: proposal not found: $id" >&2; exit 2; }; cat "$file"; }

main(){ local cmd="${1:-}"; shift || true; case "$cmd" in ask) cmd_ask "$@";; propose) cmd_propose "$@";; proposals) cmd_proposals "$@";; show-proposal) cmd_show_proposal "$@";; approve) cmd_approve "$@";; reject) cmd_reject "$@";; proposal-status) cmd_proposal_status "$@";; generate-apply-plan) cmd_generate_apply_plan "$@";; apply-plans) cmd_apply_plans "$@";; show-apply-plan) cmd_show_apply_plan "$@";; apply-plan-status) cmd_apply_plan_status "$@";; apply-plan-check) cmd_apply_plan_check "$@";; apply-plan-verify) cmd_apply_plan_verify "$@";; approve-apply-plan) cmd_approve_apply_plan "$@";; reject-apply-plan) cmd_reject_apply_plan "$@";; prepare-execution-handoff) cmd_prepare_execution_handoff "$@";; execution-handoffs) cmd_execution_handoffs "$@";; show-execution-handoff) cmd_show_execution_handoff "$@";; execution-handoff-status) cmd_execution_handoff_status "$@";; execution-handoff-verify) cmd_execution_handoff_verify "$@";; execute-handoff) cmd_execute_handoff "$@";; execution-runs) cmd_execution_runs "$@";; show-execution-run) cmd_show_execution_run "$@";; execution-run-verify) cmd_execution_run_verify "$@";; execution-run-status) cmd_execution_run_status "$@";; execution-run-audit) cmd_execution_run_audit "$@";; execution-run-summary) cmd_execution_run_summary "$@";; execution-run-approve) cmd_execution_run_approve "$@";; execution-run-reject) cmd_execution_run_reject "$@";; execution-run-close) cmd_execution_run_close "$@";; action-policy) cmd_action_policy "$@";; action-policy-verify) cmd_action_policy_verify "$@";; plugin-registry) cmd_plugin_registry "$@";; plugin-registry-verify) cmd_plugin_registry_verify "$@";; create-action-request) cmd_create_action_request "$@";; action-requests) cmd_action_requests "$@";; show-action-request) cmd_show_action_request "$@";; action-request-verify) cmd_action_request_verify "$@";; action-request-status) cmd_action_request_status "$@";; action-request-audit) cmd_action_request_audit "$@";; action-request-summary) cmd_action_request_summary "$@";; approve-action-request) cmd_approve_action_request "$@";; reject-action-request) cmd_reject_action_request "$@";; close-action-request) cmd_close_action_request "$@";; prepare-action-handoff) cmd_prepare_action_handoff "$@";; action-handoffs) cmd_action_handoffs "$@";; show-action-handoff) cmd_show_action_handoff "$@";; action-handoff-status) cmd_action_handoff_status "$@";; action-handoff-audit) cmd_action_handoff_audit "$@";; action-handoff-summary) cmd_action_handoff_summary "$@";; action-handoff-verify) cmd_action_handoff_verify "$@";; approve-action-handoff) cmd_approve_action_handoff "$@";; reject-action-handoff) cmd_reject_action_handoff "$@";; close-action-handoff) cmd_close_action_handoff "$@";; generate-patch) cmd_generate_patch "$@";; remember) cmd_remember "$@";; memory) cmd_memory "$@";; recall) cmd_recall "$@";; -h|--help|"") usage;; *) usage; exit 2;; esac; }
main "$@"
