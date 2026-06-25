#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<USAGE
Usage:
  sudo provision/bootstrap-worker.sh <spot-worker-NN> [--apply]

Runs ON THE WORKER after bare Ubuntu install.

Default: dry-run.

With --apply it will:
  - set hostname
  - install base packages
  - install NVIDIA driver via ubuntu-drivers
  - install Ollama if missing
  - enable ssh + ollama
  - add /mnt/collective NFS mount if missing
  - validate SSH, Ollama, NVIDIA, and mount state
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

if [[ "$NODE" =~ ^worker-([0-9])$ ]]; then
  NODE="spot-worker-0${BASH_REMATCH[1]}"
elif [[ "$NODE" =~ ^W-([0-9])$ ]]; then
  NODE="spot-worker-0${BASH_REMATCH[1]}"
elif [[ ! "$NODE" =~ ^spot-worker-0[1-6]$ ]]; then
  echo "FAIL: invalid worker name: $NODE"
  exit 2
fi

SUDO=""
if [[ "${EUID}" -ne 0 ]]; then
  SUDO="sudo"
fi

NFS_SOURCE="${NFS_SOURCE:-192.168.50.10:/volume1/docker}"
NFS_MOUNT="${NFS_MOUNT:-/mnt/collective}"

run() {
  echo "+ $*"
  if (( APPLY == 1 )); then
    "$@"
  fi
}

runs() {
  echo "+ $*"
  if (( APPLY == 1 )); then
    bash -c "$*"
  fi
}

echo "node=$NODE"
echo "apply=$APPLY"
echo "nfs=${NFS_SOURCE} -> ${NFS_MOUNT}"

if (( APPLY == 0 )); then
  echo "DRY-RUN: no changes will be made"
fi

echo "===== hostname ====="
run $SUDO hostnamectl set-hostname "$NODE"

echo "===== packages ====="
run $SUDO apt-get update
run $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates \
  curl \
  gnupg \
  jq \
  git \
  openssh-server \
  nfs-common \
  python3 \
  python3-venv \
  pciutils \
  ubuntu-drivers-common

echo "===== NVIDIA driver ====="
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
  echo "nvidia already working"
elif command -v ubuntu-drivers >/dev/null 2>&1; then
  run $SUDO ubuntu-drivers autoinstall || echo "WARN: ubuntu-drivers autoinstall failed; validate nvidia-smi after reboot"
else
  echo "WARN: ubuntu-drivers command missing"
fi

echo "===== Ollama install ====="
if command -v ollama >/dev/null 2>&1; then
  echo "ollama already installed: $(command -v ollama)"
else
  runs "curl -fsSL https://ollama.com/install.sh | sh"
fi

echo "===== NFS mount config ====="
if findmnt "$NFS_MOUNT" >/dev/null 2>&1; then
  echo "mount already active: $NFS_MOUNT"
elif [[ -d "$NFS_MOUNT" ]]; then
  echo "mountpoint directory already exists: $NFS_MOUNT"
else
  run $SUDO install -d -m 0755 "$NFS_MOUNT"
fi

if grep -q " ${NFS_MOUNT} " /etc/fstab 2>/dev/null; then
  echo "fstab already has $NFS_MOUNT"
else
  runs "printf '%s\n' '${NFS_SOURCE} ${NFS_MOUNT} nfs4 defaults,_netdev,noatime,nofail 0 0' | $SUDO tee -a /etc/fstab >/dev/null"
fi

echo "===== services ====="
run $SUDO systemctl enable --now ssh
run $SUDO systemctl enable --now ollama

echo "===== validation ====="
if (( APPLY == 1 )); then
  $SUDO mount "$NFS_MOUNT" || true

  echo "hostname=$(hostname)"
  echo "ssh=$(systemctl is-active ssh)"
  echo "ollama=$(systemctl is-active ollama)"

  command -v ollama

  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
  else
    echo "WARN: nvidia-smi missing after bootstrap"
  fi

  findmnt "$NFS_MOUNT" || echo "WARN: $NFS_MOUNT not mounted"
else
  echo "DRY-RUN: would validate hostname, ssh, ollama, nvidia-smi, and $NFS_MOUNT"
fi

echo "RESULT: bootstrap-worker complete for $NODE"
