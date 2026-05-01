#!/usr/bin/env bash
set -Eeuo pipefail

SPOT_BASE_URL="${SPOT_BASE_URL:-http://127.0.0.1:8787}"
CURL_TIMEOUT="${CURL_TIMEOUT:-240}"
BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
PROPOSAL_DIR="${PROPOSAL_DIR:-${BASE_DIR}/proposals}"
SPOT_MEMORY_DIR="${SPOT_MEMORY_DIR:-/mnt/collective/spot/memory}"

usage(){ cat <<'EOF'
Usage:
  spot-client.sh ask [--role ROLE] [--model MODEL] [--json] <prompt>
  spot-client.sh propose [--role ROLE] [--json] [--save] <task>
  spot-client.sh proposals [count]
  spot-client.sh show-proposal <id-or-file>
  spot-client.sh approve <id-or-file>
  spot-client.sh reject <id-or-file>
  spot-client.sh proposal-status <id-or-file>
  spot-client.sh generate-patch <id-or-file>
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

  # Reasoning questions should go to the LLM with memory context, not raw telemetry.
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
  printf '%s\n' "$1" | jq -r '"Spot readiness: \(.status)","Core: \(if .core.ok then "OK" else "FAIL" end) uptime=\(.core.uptime_sec)s","Routing: \(if .routing.ok then "OK" else "FAIL" end) primaries=\(.routing.primaries) fallbacks=\(.routing.fallbacks) violations=\(.routing.violations)","Fleet: workers=\(.fleet.worker_count) failures=\(.fleet.worker_failures) quarantined=\(.fleet.quarantined) degraded=\(.fleet.degraded)",(if (.fleet.slow_workers|length)>0 then "Warnings:\n" + (.fleet.slow_workers|map("- \(.worker): p50=\(.p50_total_ms)ms avg=\(.avg_total_ms)ms reason=\(.reason)")|join("\n")) else "Warnings: none" end)'
}
print_audit_summary(){
  printf '%s\n' "$1" | jq -r '"Routing audit: \(if .ok then "OK" else "FAIL" end)","Window: \(.window_count)","Primaries: \(.primaries)","Fallbacks: \(.fallbacks)","Violations: \(.violations)","Manual overrides: \(.manual_overrides)","Last violation: \(.last_violation_ts // "none")"'
}
print_latency_summary(){
  printf '%s\n' "$1" | jq -r 'to_entries|sort_by(.key)|map("\(.key): count=\(.value.count) avg=\(.value.avg_total_ms)ms p50=\(.value.p50_total_ms)ms tok_sec=\(.value.avg_tok_per_sec)")|join("\n")'
}
handle_telemetry_ask(){
  case "$1" in
    readiness) local d="$(api_get /operator/readiness)"; [[ "$2" == true ]] && printf '%s\n' "$d"|jq . || print_readiness_summary "$d";;
    audit) local d="$(api_get '/stats/routing-audit?limit=200')"; [[ "$2" == true ]] && printf '%s\n' "$d"|jq . || print_audit_summary "$d";;
    latency) local d="$(api_get /stats/latency)"; [[ "$2" == true ]] && printf '%s\n' "$d"|jq . || print_latency_summary "$d";;
  esac
}

json_payload(){
  [[ -n "$2" ]] && jq -n --arg role "$1" --arg model "$2" --arg prompt "$3" '{role:$role, model:$model, prompt:$prompt, stream:false}' || jq -n --arg role "$1" --arg prompt "$3" '{role:$role, prompt:$prompt, stream:false}'
}
call_exec(){ json_payload "$1" "$2" "$3" | curl -fsS --connect-timeout 5 --max-time "$CURL_TIMEOUT" -H 'Content-Type: application/json' -d @- "${SPOT_BASE_URL}/exec"; }

spot_context_block(){
  local r a ready slowp50 slowavg prim fall vio
  r="$(api_get /operator/readiness)"
  a="$(api_get '/stats/routing-audit?limit=200')"
  ready="$(printf '%s\n' "$r"|jq -r '.status')"
  slowp50="$(printf '%s\n' "$r"|jq -r '.fleet.slow_workers[0].p50_total_ms // "none"')"
  slowavg="$(printf '%s\n' "$r"|jq -r '.fleet.slow_workers[0].avg_total_ms // "none"')"
  prim="$(printf '%s\n' "$a"|jq -r '.primaries')"
  fall="$(printf '%s\n' "$a"|jq -r '.fallbacks')"
  vio="$(printf '%s\n' "$a"|jq -r '.violations')"
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

print_route(){
  local result="$1"
  printf '\n[route] role=%s worker=%s model=%s gpu=%s\n' \
    "$(printf '%s\n' "$result"|jq -r '.role_requested')" \
    "$(printf '%s\n' "$result"|jq -r '.worker')" \
    "$(printf '%s\n' "$result"|jq -r '.model')" \
    "$(printf '%s\n' "$result"|jq -r '.gpu_label')" >&2
}

save_proposal(){
  local task="$1" role="$2" result="$3" body="$4"
  mkdir -p "$PROPOSAL_DIR"
  local ts id s file worker model gpu
  ts="$(date -u +%Y%m%d-%H%M%S)"
  s="$(slug "$task")"; [[ -n "$s" ]] || s="proposal"
  id="P-${ts}-${s}"
  file="${PROPOSAL_DIR}/${id}.md"
  worker="$(printf '%s\n' "$result"|jq -r '.worker')"
  model="$(printf '%s\n' "$result"|jq -r '.model')"
  gpu="$(printf '%s\n' "$result"|jq -r '.gpu_label')"
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

resolve_proposal_file(){
  local id="${1:-}"; [[ -n "$id" ]] || { echo "ERROR: proposal id/file required" >&2; exit 2; }
  local file="$id"
  [[ -f "$file" ]] || file="${PROPOSAL_DIR}/${id%.md}.md"
  [[ -f "$file" ]] || { echo "ERROR: proposal not found: $id" >&2; exit 2; }
  printf '%s' "$file"
}

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

cmd_approve(){
  local file id task
  file="$(resolve_proposal_file "${1:-}")"
  set_proposal_status "$file" approved
  id="$(basename "$file" .md)"
  task="$(grep '^task:' "$file" | cut -d':' -f2- | sed 's/^ //')"
  memory_append decision "approved proposal ${id} for task ${task}"
  memory_append session "proposal ${id} moved to approved state"
  echo "[approved] $file"
}

cmd_reject(){
  local file
  file="$(resolve_proposal_file "${1:-}")"
  set_proposal_status "$file" rejected
  echo "[rejected] $file"
}

cmd_proposal_status(){
  local file
  file="$(resolve_proposal_file "${1:-}")"
  grep -E '^(status:|approved_utc:|rejected_utc:|created_utc:|task:)' "$file"
}

proposal_is_approved(){
  local file="$1"
  grep -q '^status: approved' "$file"
}

cmd_generate_patch(){
  local file id approved task patch_dir patch_file
  file="$(resolve_proposal_file "${1:-}")"
  if ! proposal_is_approved "$file"; then
    echo "ERROR: proposal is not approved; generate-patch blocked" >&2
    exit 2
  fi

  id="$(basename "$file" .md)"
  approved="$(grep '^approved_utc:' "$file" | awk '{print $2}')"
  task="$(grep '^task:' "$file" | cut -d':' -f2- | sed 's/^ //')"

  patch_dir="${BASE_DIR}/patches"
  mkdir -p "$patch_dir"
  patch_file="${patch_dir}/PATCH-${id}.md"

  cat > "$patch_file" <<EOF
# Spot Patch Artifact PATCH-${id}

linked_proposal: ${id}
approved_utc: ${approved}
task: ${task}
apply_status: pending_manual_apply

---

TARGET_FILES
- /home/ogre/spot-stack/spot-core/config/cluster_config.json

INTENDED_MODIFICATION_SUMMARY
- derive exact cluster_config.json adjustments from approved proposal
- do not apply automatically
- require human review before file mutation

VALIDATION_CHECKLIST
- python3 -m json.tool /home/ogre/spot-stack/spot-core/config/cluster_config.json >/dev/null
- spot validate
- spot ask "show worker latency"
- spot ask "what is the current fleet status"
- spot ask "show current routing audit"

MANUAL_REVIEW_REQUIRED
- confirm approved proposal still matches current fleet condition
- confirm worker-02 latency issue still present
- confirm no conflicting hardware changes pending
EOF

  memory_append roadmap "generated supervised patch artifact PATCH-${id}"
  memory_append session "patch artifact generated from approved proposal ${id}"
  echo "[patch-generated] $patch_file"
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

entry = {
    "ts": datetime.now(UTC).strftime("%Y%m%d-%H%M%S"),
    "type": kind,
    "text": msg
}

with p.open("a") as f:
    f.write(json.dumps(entry) + "\n")
INNER

  local rc=$?
  if [[ $rc -eq 10 ]]; then
    echo "[memory-skip-duplicate:$kind] $msg"
  else
    echo "[remembered:$kind] $msg"
  fi
}

cmd_remember(){
  local kind="${1:-}"; shift || true
  case "$kind" in fact|decision|session|preference|roadmap) ;; *)
    echo "ERROR: remember type must be fact|decision|session|preference|roadmap" >&2; exit 2;;
  esac
  [[ $# -gt 0 ]] || { echo "ERROR: remember text required" >&2; exit 2; }
  memory_append "$kind" "$*"
}

cmd_memory(){
  local count="${1:-20}"
  local mem_dir="${SPOT_MEMORY_DIR}"
  mkdir -p "$mem_dir"
  python3 - "$count" "$mem_dir" <<'INNER'
import sys, json
from pathlib import Path

count = int(sys.argv[1])
mem_dir = Path(sys.argv[2])
rows = []

for path in sorted(mem_dir.glob("*.jsonl")):
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    except FileNotFoundError:
        pass

rows.sort(key=lambda x: x.get("ts", ""), reverse=True)

for row in rows[:count]:
    print(f'{row.get("ts")} [{row.get("type")}] {row.get("text")}')
INNER
}

cmd_recall(){
  local q="${*:-}"
  [[ -n "$q" ]] || { echo "ERROR: recall keyword required" >&2; exit 2; }
  local mem_dir="${SPOT_MEMORY_DIR}"
  mkdir -p "$mem_dir"
  python3 - "$q" "$mem_dir" <<'INNER'
import sys, json
from pathlib import Path

q = sys.argv[1].lower()
mem_dir = Path(sys.argv[2])
rows = []

for path in sorted(mem_dir.glob("*.jsonl")):
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                blob = f'{row.get("type","")} {row.get("text","")}'.lower()
                if q in blob:
                    rows.append(row)
            except Exception:
                pass
    except FileNotFoundError:
        pass

rows.sort(key=lambda x: x.get("ts",""), reverse=True)

if not rows:
    print(f'no memory matches for: {q}')
else:
    for row in rows:
        print(f'{row.get("ts")} [{row.get("type")}] {row.get("text")}')
INNER
}

memory_context_for_prompt(){
  local q="${*:-}"
  local mem_dir="${SPOT_MEMORY_DIR}"
  mkdir -p "$mem_dir"
  python3 - "$q" "$mem_dir" <<'INNER'
import sys, json, re
from pathlib import Path

q = sys.argv[1].lower()
mem_dir = Path(sys.argv[2])

tokens = [t for t in re.split(r'[^a-zA-Z0-9_.-]+', q) if len(t) >= 3]
rows = []

for path in sorted(mem_dir.glob("*.jsonl")):
    try:
        for line in path.read_text().splitlines():
            try:
                row = json.loads(line)
            except Exception:
                continue
            blob = f'{row.get("type","")} {row.get("text","")}'.lower()
            score = sum(1 for t in tokens if t.lower() in blob)
            if score:
                rows.append((score, row))
    except FileNotFoundError:
        pass

rows.sort(key=lambda x: (x[0], x[1].get("ts","")), reverse=True)
rows = rows[:8]

if rows:
    print("RELEVANT_SPOT_MEMORY")
    for _, row in rows:
        print(f'- {row.get("ts")} [{row.get("type")}] {row.get("text")}')
INNER
}

with_memory_prompt(){
  local user_prompt="$1"
  local memory
  memory="$(memory_context_for_prompt "$user_prompt" || true)"
  if [[ -n "$memory" ]]; then
    cat <<EOF
You are Spot assistant mode. Durable prior Spot memory is provided below.
Use this memory when answering unless live telemetry or the current prompt clearly contradicts it.
If memory affects the answer, explicitly mention the relevant remembered fact or decision.

DURABLE_MEMORY_CONTEXT
${memory}

CURRENT_USER_PROMPT
${user_prompt}
EOF
  else
    printf '%s' "$user_prompt"
  fi
}

proposal_context_for_task(){
  local q="${*:-}"
  python3 - "$q" "${PROPOSAL_DIR}" "${BASE_DIR}/patches" <<'INNER'
import sys, re
from pathlib import Path

q = sys.argv[1].lower()
proposal_dir = Path(sys.argv[2])
patch_dir = Path(sys.argv[3])

tokens = [t for t in re.split(r'[^a-zA-Z0-9_.-]+', q) if len(t) >= 3]

def score_blob(blob):
    blob = blob.lower()
    return sum(1 for t in tokens if t in blob)

prop_hits = []
for p in sorted(proposal_dir.glob("P-*.md")):
    txt = p.read_text(errors="ignore")
    s = score_blob(txt + " " + p.name)
    if s:
        status = "unknown"
        for line in txt.splitlines():
            if line.startswith("status:"):
                status = line.split(":",1)[1].strip()
                break
        prop_hits.append((s, p.name, status))

patch_hits = []
for p in sorted(patch_dir.glob("PATCH-*.md")):
    txt = p.read_text(errors="ignore")
    s = score_blob(txt + " " + p.name)
    if s:
        patch_hits.append((s, p.name))

prop_hits.sort(reverse=True)
patch_hits.sort(reverse=True)

if prop_hits:
    print("RELATED_PROPOSALS")
    for _, name, status in prop_hits[:5]:
        print(f'- {name} [{status}]')

if patch_hits:
    print("RELATED_PATCHES")
    for _, name in patch_hits[:5]:
        print(f'- {name}')
INNER
}

cmd_ask(){
  need_cmd jq; need_cmd curl
  local role="auto" model="" json_out=false args=()
  while [[ $# -gt 0 ]]; do case "$1" in --role) role="${2:-}"; shift 2;; --model) model="${2:-}"; shift 2;; --json) json_out=true; shift;; -h|--help) usage; exit 0;; --) shift; args+=("$@"); break;; *) args+=("$1"); shift;; esac; done
  local prompt="$(join_prompt "${args[@]}")"; [[ -n "$prompt" ]] || { echo "ERROR: prompt required" >&2; exit 2; }
  local intent="$(telemetry_intent "$prompt")"
  [[ "$intent" != none && "$role" == auto && -z "$model" ]] && { handle_telemetry_ask "$intent" "$json_out"; return 0; }
  [[ "$role" == auto ]] && role="$(classify_role "$prompt")"
  local llm_prompt
  llm_prompt="$(with_memory_prompt "$prompt")"
  local result="$(call_exec "$role" "$model" "$llm_prompt")"
  [[ "$json_out" == true ]] && printf '%s\n' "$result"|jq . || { printf '%s\n' "$result"|jq -r '.response'; print_route "$result"; }
}

proposal_guardrail_check(){
  local body="$1"
  local bad=0

  while IFS= read -r forbidden; do
    [[ -z "$forbidden" ]] && continue
    if printf '%s\n' "$body" | grep -Fq "$forbidden"; then
      echo "[proposal-warning] forbidden invented operation/path detected: $forbidden" >&2
      bad=1
    fi
  done <<'EOF'
systemctl restart spot-client
systemctl restart spot-ops
spot-client.service
spot-ops.service
/home/ogre/spot-stack/bin/spot
/etc/config/worker-02.yaml
/home/ogre/spot-stack/config/cluster_config.json
EOF

  return "$bad"
}

cmd_propose(){
  need_cmd jq; need_cmd curl
  local role="auto" json_out=false save=false args=()
  while [[ $# -gt 0 ]]; do case "$1" in --role) role="${2:-}"; shift 2;; --json) json_out=true; shift;; --save) save=true; shift;; -h|--help) usage; exit 0;; --) shift; args+=("$@"); break;; *) args+=("$1"); shift;; esac; done
  local task="$(join_prompt "${args[@]}")"; [[ -n "$task" ]] || { echo "ERROR: task required" >&2; exit 2; }
  local mem
  mem="$(memory_context_for_prompt "$task" || true)"
  local related
  related="$(proposal_context_for_task "$task" || true)"
  local prompt="You are Spot proposal mode. Do not apply changes. Durable memory context and related historical engineering artifacts may be provided below. You must incorporate them when relevant unless contradicted by live telemetry. Avoid duplicating already-approved plans when a related approved proposal exists. Use exactly these section headers: SUMMARY, RISK_CLASS, FILES_AFFECTED, VALIDATION_COMMANDS, ROLLBACK, NEXT_SAFE_ACTION. Put 1-4 concrete bullets or lines under every section. Use canonical paths only. Use only allowed validation commands. Avoid every forbidden guess. Do not include DETAILS, PROPOSAL_CONTENT, sample JSON, or patch bodies unless explicitly asked.\n\n$(spot_context_block)\n\n${related}\n\nDURABLE_MEMORY_CONTEXT\n${mem}\n\nTASK: ${task}"
  [[ "$role" == auto ]] && role="$(classify_role "$task")"
  local result body
  result="$(call_exec "$role" "" "$prompt")"
  body="$(printf '%s\n' "$result"|jq -r '.response')"
  proposal_guardrail_check "$body" || true
  if [[ "$json_out" == true ]]; then
    printf '%s\n' "$result"|jq .
  else
    printf '%s\n' "$body"
    print_route "$result"
  fi
  [[ "$save" == true ]] && save_proposal "$task" "$role" "$result" "$body"
}

cmd_proposals(){
  local count="${1:-20}"
  mkdir -p "$PROPOSAL_DIR"
  find "$PROPOSAL_DIR" -maxdepth 1 -type f -name 'P-*.md' -printf '%T@ %f\n' 2>/dev/null | sort -nr | head -n "$count" | awk '{print $2}'
}
cmd_show_proposal(){
  local id="${1:-}"; [[ -n "$id" ]] || { echo "ERROR: proposal id/file required" >&2; exit 2; }
  local file="$id"
  [[ -f "$file" ]] || file="${PROPOSAL_DIR}/${id%.md}.md"
  [[ -f "$file" ]] || { echo "ERROR: proposal not found: $id" >&2; exit 2; }
  cat "$file"
}

main(){ local cmd="${1:-}"; shift || true; case "$cmd" in ask) cmd_ask "$@";; propose) cmd_propose "$@";; proposals) cmd_proposals "$@";; show-proposal) cmd_show_proposal "$@";; approve) cmd_approve "$@";; reject) cmd_reject "$@";; proposal-status) cmd_proposal_status "$@";; generate-patch) cmd_generate_patch "$@";; remember) cmd_remember "$@";; memory) cmd_memory "$@";; recall) cmd_recall "$@";; -h|--help|"") usage;; *) usage; exit 2;; esac; }
main "$@"
