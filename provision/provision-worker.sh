#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<USAGE
Usage:
  provision/provision-worker.sh <spot-worker-NN|worker-NN|W-NN> [--apply]

Default: dry-run.
Reads:
  - spot-core/config/cluster_config.json
  - watch/fleet-policy.json

Behavior:
  - skips node when provision_enabled=false
  - validates SSH/Ollama/NVIDIA
  - pulls required Ollama models only with --apply
USAGE
}

NODE="${1:-}"
[[ -n "$NODE" ]] || { usage; exit 2; }
shift || true

APPLY=0
for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=1 ;;
    --dry-run) APPLY=0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "FAIL: unknown arg: $arg" >&2; usage; exit 2 ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CFG="$ROOT/spot-core/config/cluster_config.json"
POLICY="$ROOT/watch/fleet-policy.json"
SSH_USER="${SSH_USER:-ogre}"

[[ -f "$CFG" ]] || { echo "FAIL: missing $CFG"; exit 1; }
[[ -f "$POLICY" ]] || { echo "FAIL: missing $POLICY"; exit 1; }

mapfile -t META < <(python3 - "$CFG" "$POLICY" "$NODE" <<'PY'
import json
import re
import sys
from pathlib import Path

cfg_path, policy_path, raw_node = sys.argv[1:4]

def canon(text):
    text = str(text).lower()
    m = re.search(r"(?:spot-)?worker[-_ ]?0?([1-6])\b", text)
    if not m:
        m = re.search(r"\bw[-_ ]?0?([1-6])\b", text)
    if not m:
        raise SystemExit(f"FAIL: cannot parse worker from {raw_node!r}")
    return f"spot-worker-{int(m.group(1)):02d}"

host = canon(raw_node)
cfg = json.loads(Path(cfg_path).read_text())
policy = json.loads(Path(policy_path).read_text())

workers = cfg.get("workers", {})
if host not in workers:
    raise SystemExit(f"FAIL: {host} missing from cluster_config workers")

worker = workers[host]
enabled = worker.get("provision_enabled", True)
role = worker.get("primary_role") or worker.get("role") or "unknown"
gpu = worker.get("gpu_summary") or worker.get("gpu") or "unknown"

models = policy.get("required_models", {}).get(host)
if models is None:
    models = worker.get("models", [])
if isinstance(models, dict):
    models = list(models.keys())
elif isinstance(models, str):
    models = [x for x in models.replace(",", " ").split() if x]
elif not isinstance(models, list):
    models = []

print(host)
print("true" if enabled else "false")
print(role)
print(gpu)
for model in models:
    print(str(model))
PY
)

HOST="${META[0]}"
ENABLED="${META[1]}"
ROLE="${META[2]}"
GPU="${META[3]}"
MODELS=("${META[@]:4}")

echo "target=$HOST"
echo "role=$ROLE"
echo "gpu=$GPU"
echo "provision_enabled=$ENABLED"
echo "apply=$APPLY"

if [[ "$ENABLED" != "true" ]]; then
  echo "SKIP: $HOST provision_enabled=false"
  exit 0
fi

SSH_TARGET="${SSH_TARGET:-$SSH_USER@$HOST}"
SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=8)

echo "===== remote base check ====="
ssh "${SSH_OPTS[@]}" "$SSH_TARGET" '
set -euo pipefail
echo "host=$(hostname)"
echo "ssh=$(systemctl is-active ssh)"
echo "ollama=$(systemctl is-active ollama)"
command -v ollama
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
  echo "WARN: nvidia-smi missing"
fi
'

echo "===== model plan ====="
if ((${#MODELS[@]} == 0)); then
  echo "WARN: no required models listed for $HOST"
fi

for model in "${MODELS[@]}"; do
  echo "model=$model"
  if (( APPLY == 1 )); then
    ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "ollama list | awk 'NR>1 {print \$1}' | grep -Fxq '$model' || ollama pull '$model'"
  else
    echo "DRY-RUN: would ensure model on $HOST: $model"
  fi
done

if (( APPLY == 1 )); then
  echo "===== enforce ollama listen + service state ====="
  ssh "${SSH_OPTS[@]}" "$SSH_TARGET" '
set -euo pipefail
if sudo -n true 2>/dev/null; then
  sudo install -d -m 0755 /etc/systemd/system/ollama.service.d
  printf "%s\n" "[Service]" "Environment=\"OLLAMA_HOST=0.0.0.0:11434\"" | sudo tee /etc/systemd/system/ollama.service.d/starfleet.conf >/dev/null
  sudo systemctl daemon-reload
  sudo systemctl enable --now ssh ollama
  sudo systemctl restart ollama
else
  echo "WARN: remote sudo requires password/tty; skipping service override"
fi
systemctl is-active ssh
systemctl is-active ollama
'
else
  echo "DRY-RUN: would enforce ollama systemd override"
fi

echo "RESULT: provision-worker dry-run/apply complete for $HOST"
