#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
STATE_DIR="${STATE_DIR:-${BASE_DIR}/state}"
CONTRACT_DIR="${CONTRACT_DIR:-${BASE_DIR}/codex-proposal-contracts}"
SUMMARY_FILE="${SUMMARY_FILE:-${STATE_DIR}/codex-proposal-contract-summary.json}"

usage() {
  cat <<'USAGE'
Usage:
  spot-codex-proposal-contract.sh create
  spot-codex-proposal-contract.sh verify <contract-id-or-file>
  spot-codex-proposal-contract.sh show <contract-id-or-file>
  spot-codex-proposal-contract.sh list [count]
  spot-codex-proposal-contract.sh summary

Phase 2 external AI client governance:
- Codex may propose only
- Codex may not execute, mutate, restart services, write configs, change network state, bind backups, or dispatch executors
USAGE
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $1" >&2
    exit 2
  }
}

stamp() { date -u +%Y%m%d-%H%M%S; }

resolve_file() {
  local id="${1:-}"
  [[ -n "$id" ]] || { echo "ERROR: contract id/file required" >&2; exit 2; }

  local file="$id"
  [[ -f "$file" ]] || file="${CONTRACT_DIR}/${id%.json}.json"
  [[ -f "$file" ]] || file="${CONTRACT_DIR}/CODEX-PROPOSAL-CONTRACT-${id#CODEX-PROPOSAL-CONTRACT-}.json"

  [[ -f "$file" ]] || {
    echo "ERROR: contract not found: $id" >&2
    exit 2
  }

  printf '%s' "$file"
}

json_get() {
  local file="$1" expr="$2"
  python3 - "$file" "$expr" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
cur = data
for part in sys.argv[2].split("."):
    if not part:
        continue
    if isinstance(cur, dict) and part in cur:
        cur = cur[part]
    else:
        print("")
        raise SystemExit(0)
if isinstance(cur, bool):
    print("true" if cur else "false")
elif cur is None:
    print("null")
else:
    print(cur)
PY
}

assert_eq() {
  local actual="$1" expected="$2" label="$3"
  [[ "$actual" == "$expected" ]] || {
    echo "ERROR: ${label}: expected ${expected}, got ${actual:-<missing>}" >&2
    exit 2
  }
}

assert_true() { assert_eq "$1" "true" "$2"; }
assert_false() { assert_eq "$1" "false" "$2"; }

cmd_create() {
  need_cmd python3
  mkdir -p "$CONTRACT_DIR" "$STATE_DIR"

  local ts out
  ts="$(stamp)"
  out="${CONTRACT_DIR}/CODEX-PROPOSAL-CONTRACT-${ts}.json"

  python3 - "$out" <<'PY'
import json, sys
from pathlib import Path
from datetime import datetime, UTC

out = Path(sys.argv[1])
artifact = {
    "schema": "spot.codex_proposal_contract.v1",
    "phase": "2.external-ai-governance",
    "created_utc": datetime.now(UTC).strftime("%Y%m%d-%H%M%S"),
    "client": "codex",
    "target_worker": "spot-worker-03",
    "worker_role": "coding",
    "mode": "proposal_only",
    "contract_status": "active_non_mutating_governance",
    "authority": {
        "may_read_repo_context": True,
        "may_generate_proposals": True,
        "may_generate_patch_artifacts": True,
        "may_request_validation": True,
        "may_request_spot_core_apply": True,
        "spot_core_is_apply_authority": True,
        "operator_approval_required_for_apply": True
    },
    "hard_gates": {
        "execution_allowed": False,
        "mutation_allowed": False,
        "mutation_performed": False,
        "executor_dispatch_allowed": False,
        "service_restart_allowed": False,
        "config_write_allowed": False,
        "network_mutation_allowed": False,
        "backup_creation_allowed": False,
        "backup_binding_active": False,
        "backup_delete_allowed": False,
        "backup_overwrite_allowed": False,
        "unrestricted_shell_allowed": False,
        "direct_filesystem_mutation_allowed": False,
        "direct_admin_write_allowed": False,
        "direct_service_restart_allowed": False,
        "direct_network_mutation_allowed": False
    },
    "result": {
        "ok": True,
        "blocked": True,
        "reason": "codex_governed_as_proposal_only_client_no_direct_mutation"
    }
}
out.write_text(json.dumps(artifact, indent=2) + "\n")
PY

  cmd_verify "$out" >/dev/null
  echo "$out"
}

cmd_verify() {
  need_cmd python3
  local file
  file="$(resolve_file "${1:-}")"

  python3 - "$file" <<'PY'
import json, sys
from pathlib import Path

file = Path(sys.argv[1])
data = json.loads(file.read_text())

required = [
    "schema", "phase", "created_utc", "client", "target_worker",
    "worker_role", "mode", "contract_status", "authority",
    "hard_gates", "result",
]
for key in required:
    if key not in data:
        raise SystemExit(f"ERROR: missing required field: {key}")

expected = {
    "schema": "spot.codex_proposal_contract.v1",
    "client": "codex",
    "target_worker": "spot-worker-03",
    "worker_role": "coding",
    "mode": "proposal_only",
    "contract_status": "active_non_mutating_governance",
}
for key, value in expected.items():
    if data.get(key) != value:
        raise SystemExit(f"ERROR: {key}: expected {value}, got {data.get(key)!r}")

authority_true = [
    "may_read_repo_context",
    "may_generate_proposals",
    "may_generate_patch_artifacts",
    "may_request_validation",
    "may_request_spot_core_apply",
    "spot_core_is_apply_authority",
    "operator_approval_required_for_apply",
]
authority = data.get("authority", {})
for key in authority_true:
    if authority.get(key) is not True:
        raise SystemExit(f"ERROR: authority.{key} must be true")

hard_gates = data.get("hard_gates", {})
for key, value in hard_gates.items():
    if value is not False:
        raise SystemExit(f"ERROR: hard_gates.{key} must be false")

result = data.get("result", {})
if result.get("ok") is not True:
    raise SystemExit("ERROR: result.ok must be true")
if result.get("blocked") is not True:
    raise SystemExit("ERROR: result.blocked must be true")

print(json.dumps({
    "ok": True,
    "verified": True,
    "file": str(file),
    "schema": data["schema"],
    "client": data["client"],
    "mode": data["mode"],
    "mutation_performed": False,
    "execution_performed": False
}, indent=2))
PY
}

cmd_show() {
  local file
  file="$(resolve_file "${1:-}")"
  cat "$file"
}

cmd_list() {
  local count="${1:-20}"
  mkdir -p "$CONTRACT_DIR"
  find "$CONTRACT_DIR" -maxdepth 1 -type f -name 'CODEX-PROPOSAL-CONTRACT-*.json' -printf '%T@ %p\n' \
    | sort -nr \
    | head -n "$count" \
    | cut -d' ' -f2-
}

cmd_summary() {
  need_cmd python3
  mkdir -p "$CONTRACT_DIR" "$STATE_DIR"

  python3 - "$CONTRACT_DIR" "$SUMMARY_FILE" <<'PY'
import json, sys
from pathlib import Path
from datetime import datetime, UTC
contract_dir = Path(sys.argv[1])
summary_file = Path(sys.argv[2])

items = []
invalid = []
for file in sorted(contract_dir.glob("CODEX-PROPOSAL-CONTRACT-*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
    try:
        data = json.loads(file.read_text())
        clean = (
            data.get("schema") == "spot.codex_proposal_contract.v1"
            and data.get("client") == "codex"
            and data.get("mode") == "proposal_only"
            and data.get("result", {}).get("ok") is True
            and data.get("result", {}).get("blocked") is True
            and all(v is False for v in data.get("hard_gates", {}).values())
        )
        row = {
            "file": str(file),
            "name": file.name,
            "schema": data.get("schema"),
            "client": data.get("client"),
            "target_worker": data.get("target_worker"),
            "mode": data.get("mode"),
            "contract_status": data.get("contract_status"),
            "ok": data.get("result", {}).get("ok"),
            "blocked": data.get("result", {}).get("blocked"),
            "clean": clean,
        }
        items.append(row)
        if not clean:
            invalid.append(row)
    except Exception as exc:
        invalid.append({"file": str(file), "error": repr(exc)})

artifact = {
    "schema": "spot.codex_proposal_contract_summary.v1",
    "created_utc": datetime.now(UTC).strftime("%Y%m%d-%H%M%S"),
    "contract_dir": str(contract_dir),
    "summary_file": str(summary_file),
    "count": len(items),
    "verified_count": len(items) - len(invalid),
    "invalid_count": len(invalid),
    "all_known_codex_proposal_contracts_blocked_and_non_mutating": len(invalid) == 0,
    "items": items,
    "invalid": invalid,
}
summary_file.write_text(json.dumps(artifact, indent=2) + "\n")
print(json.dumps(artifact, indent=2))
PY
}

main() {
  local cmd="${1:-}"
  shift || true

  case "$cmd" in
    create) cmd_create "$@" ;;
    verify) cmd_verify "$@" ;;
    show) cmd_show "$@" ;;
    list) cmd_list "$@" ;;
    summary) cmd_summary "$@" ;;
    -h|--help|help|"") usage ;;
    *) echo "ERROR: unknown command: $cmd" >&2; usage >&2; exit 2 ;;
  esac
}

main "$@"
