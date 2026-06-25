#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<USAGE
Usage:
  provision/provision-spot-core.sh [--apply]

Runs ON spot-core.

Default: dry-run.

With --apply it will:
  - install base packages
  - install docker.io / compose support when available
  - install cloudflared when available from apt
  - ensure /mnt/collective exists in fstab
  - enable docker
  - validate compose/cloudflared/mount state

It does not create Cloudflare tunnels or inject secrets.
USAGE
}

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
SUDO=""
if [[ "${EUID}" -ne 0 ]]; then
  SUDO="sudo"
fi

NFS_SOURCE="${NFS_SOURCE:-192.168.50.10:/volume1/docker}"
NFS_MOUNT="${NFS_MOUNT:-/mnt/collective}"
SPOT_MCP_DIR="${SPOT_MCP_DIR:-/home/ogre/spot-mcp}"

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

echo "spot-core-root=$ROOT"
echo "apply=$APPLY"
echo "nfs=${NFS_SOURCE} -> ${NFS_MOUNT}"
echo "spot-mcp-dir=$SPOT_MCP_DIR"

if (( APPLY == 0 )); then
  echo "DRY-RUN: no changes will be made"
fi

echo "===== package plan ====="
APT_PKGS=(
  ca-certificates
  curl
  gnupg
  jq
  git
  nfs-common
  python3
  python3-venv
  docker.io
)

if apt-cache show docker-compose-v2 >/dev/null 2>&1; then
  APT_PKGS+=(docker-compose-v2)
elif apt-cache show docker-compose-plugin >/dev/null 2>&1; then
  APT_PKGS+=(docker-compose-plugin)
elif apt-cache show docker-compose >/dev/null 2>&1; then
  APT_PKGS+=(docker-compose)
fi

if apt-cache show cloudflared >/dev/null 2>&1; then
  APT_PKGS+=(cloudflared)
fi

printf 'pkg=%s\n' "${APT_PKGS[@]}"

run $SUDO apt-get update
run $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y "${APT_PKGS[@]}"

echo "===== NFS mount config ====="
run $SUDO install -d -m 0755 "$NFS_MOUNT"

if grep -q " ${NFS_MOUNT} " /etc/fstab 2>/dev/null; then
  echo "fstab already has $NFS_MOUNT"
else
  runs "printf '%s\n' '${NFS_SOURCE} ${NFS_MOUNT} nfs4 defaults,_netdev,noatime,nofail 0 0' | $SUDO tee -a /etc/fstab >/dev/null"
fi

echo "===== docker service ====="
run $SUDO systemctl enable --now docker

echo "===== compose config check ====="
COMPOSE_FILE=""
for f in docker-compose.yml compose.yml compose.yaml; do
  if [[ -f "$ROOT/$f" ]]; then
    COMPOSE_FILE="$ROOT/$f"
    break
  fi
done

if [[ -n "$COMPOSE_FILE" ]]; then
  echo "compose_file=$COMPOSE_FILE"
  if (( APPLY == 1 )); then
    if docker compose version >/dev/null 2>&1; then
      docker compose -f "$COMPOSE_FILE" config >/dev/null
    elif command -v docker-compose >/dev/null 2>&1; then
      docker-compose -f "$COMPOSE_FILE" config >/dev/null
    else
      echo "WARN: compose command not found"
    fi
  else
    echo "DRY-RUN: would validate compose config"
  fi
else
  echo "WARN: no compose file found at repo root"
fi

echo "===== spot-mcp check ====="
if [[ -d "$SPOT_MCP_DIR" ]]; then
  echo "found $SPOT_MCP_DIR"
  find "$SPOT_MCP_DIR" -maxdepth 1 -type f -printf '%f\n' | sort
else
  echo "WARN: $SPOT_MCP_DIR not found"
fi

echo "===== validation ====="
if (( APPLY == 1 )); then
  $SUDO mount "$NFS_MOUNT" || true
fi

systemctl is-active docker || true
if command -v cloudflared >/dev/null 2>&1; then
  cloudflared --version
else
  echo "WARN: cloudflared not installed/found"
fi
findmnt "$NFS_MOUNT" || echo "WARN: $NFS_MOUNT not mounted"

echo "RESULT: provision-spot-core complete"
