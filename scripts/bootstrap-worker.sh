#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  sudo scripts/bootstrap-worker.sh --hostname spot-worker-06
  sudo scripts/bootstrap-worker.sh --hostname spot-worker-07 --install-nvidia-driver

Purpose:
  Bootstrap a Starfleet/Spot worker after fresh Ubuntu install.

What it does:
  - verifies root/sudo execution
  - sets hostname when requested
  - installs base packages
  - installs Ollama when missing
  - enables SSH and Ollama
  - configures Ollama to listen on 0.0.0.0:11434
  - creates /mnt/collective
  - adds optional /mnt/collective NFS fstab entry
  - optionally installs recommended NVIDIA driver
  - writes a local bootstrap report

Flags:
  --hostname NAME              Required. Expected worker hostname.
  --install-nvidia-driver      Optional. Install ubuntu-drivers recommended NVIDIA driver.
  --nfs-source SRC             Optional. Default: 192.168.50.10:/volume1/docker
  --skip-nfs                   Optional. Do not add/mount /mnt/collective.
  --skip-ollama                Optional. Do not install/configure Ollama.
  --no-reboot                  Optional. Do not prompt/recommend reboot text at end.
  -h, --help                   Show help.
USAGE
}

TARGET_HOSTNAME=""
INSTALL_NVIDIA_DRIVER=0
NFS_SOURCE="192.168.50.10:/volume1/docker"
SKIP_NFS=0
SKIP_OLLAMA=0
NO_REBOOT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --hostname)
      TARGET_HOSTNAME="${2:-}"
      shift 2
      ;;
    --install-nvidia-driver)
      INSTALL_NVIDIA_DRIVER=1
      shift
      ;;
    --nfs-source)
      NFS_SOURCE="${2:-}"
      shift 2
      ;;
    --skip-nfs)
      SKIP_NFS=1
      shift
      ;;
    --skip-ollama)
      SKIP_OLLAMA=1
      shift
      ;;
    --no-reboot)
      NO_REBOOT=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$TARGET_HOSTNAME" ]]; then
  echo "ERROR: --hostname is required" >&2
  usage >&2
  exit 2
fi

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run with sudo/root" >&2
  exit 1
fi

log() { printf '\n=== %s ===\n' "$*"; }
need_cmd() { command -v "$1" >/dev/null 2>&1; }

BOOTSTRAP_DIR="/var/log/starfleet-bootstrap"
BOOTSTRAP_LOG="$BOOTSTRAP_DIR/${TARGET_HOSTNAME}-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$BOOTSTRAP_DIR"
exec > >(tee -a "$BOOTSTRAP_LOG") 2>&1

log "Starfleet worker bootstrap"
echo "target_hostname=$TARGET_HOSTNAME"
echo "bootstrap_log=$BOOTSTRAP_LOG"
echo "started_at=$(date -Is)"

log "Set hostname"
current_hostname="$(hostname)"
echo "current_hostname=$current_hostname"
if [[ "$current_hostname" != "$TARGET_HOSTNAME" ]]; then
  hostnamectl set-hostname "$TARGET_HOSTNAME"
  echo "hostname_changed_to=$TARGET_HOSTNAME"
else
  echo "hostname_already_correct=true"
fi

log "APT base packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
  ca-certificates \
  curl \
  git \
  jq \
  htop \
  btop \
  pciutils \
  usbutils \
  lshw \
  dmidecode \
  net-tools \
  iproute2 \
  dnsutils \
  nfs-common \
  openssh-server \
  python3 \
  python3-venv \
  python3-pip \
  unzip \
  rsync \
  tmux

log "Enable SSH"
systemctl enable --now ssh || systemctl enable --now sshd
systemctl is-active ssh 2>/dev/null || systemctl is-active sshd 2>/dev/null || true

if [[ "$INSTALL_NVIDIA_DRIVER" -eq 1 ]]; then
  log "Install recommended NVIDIA driver"
  apt-get install -y ubuntu-drivers-common
  ubuntu-drivers devices || true
  ubuntu-drivers install || true
else
  log "Skip NVIDIA driver install"
  echo "install_nvidia_driver=false"
fi

if [[ "$SKIP_NFS" -eq 0 ]]; then
  log "Configure /mnt/collective"
  mkdir -p /mnt/collective
  if ! grep -qE '^[^#]+[[:space:]]+/mnt/collective[[:space:]]+' /etc/fstab; then
    echo "$NFS_SOURCE /mnt/collective nfs4 rw,noatime,vers=4.0,rsize=131072,wsize=131072,hard,_netdev,auto 0 0" >> /etc/fstab
    echo "fstab_added=true"
  else
    echo "fstab_entry_exists=true"
  fi
  mount /mnt/collective || true
  findmnt /mnt/collective || true
else
  log "Skip NFS mount"
fi

if [[ "$SKIP_OLLAMA" -eq 0 ]]; then
  log "Install/configure Ollama"
  if ! need_cmd ollama; then
    curl -fsSL https://ollama.com/install.sh | sh
  else
    ollama --version || true
  fi

  mkdir -p /etc/systemd/system/ollama.service.d
  cat > /etc/systemd/system/ollama.service.d/starfleet.conf <<'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF

  systemctl daemon-reload
  systemctl enable --now ollama
  systemctl restart ollama
  sleep 2
  systemctl is-active ollama || true
  curl -s http://127.0.0.1:11434/api/tags || true
else
  log "Skip Ollama"
fi

log "Hardware snapshot"
echo "hostname=$(hostname)"
echo "kernel=$(uname -r)"
if [[ -f /etc/os-release ]]; then
  awk -F= '/^PRETTY_NAME=/{gsub(/\"/,"",$2); print "os="$2}' /etc/os-release
fi
lscpu | awk -F: '/Model name|^CPU\(s\)/{gsub(/^[ \t]+/,"",$2); print $1"="$2}' || true
free -h || true
lsblk -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINT,MODEL || true
lspci | grep -Ei 'nvidia|vga|3d|display' || true
if need_cmd nvidia-smi; then
  nvidia-smi || true
  nvidia-smi --query-gpu=index,name,uuid,pci.bus_id,memory.total,driver_version,temperature.gpu,power.draw,power.limit --format=csv,noheader,nounits || true
else
  echo "nvidia_smi=missing"
fi

log "Network snapshot"
ip -br a || true
ip route || true
resolvectl status 2>/dev/null || cat /etc/resolv.conf || true

log "Service snapshot"
systemctl --failed --no-pager || true
systemctl is-active ssh 2>/dev/null || systemctl is-active sshd 2>/dev/null || true
systemctl is-active ollama 2>/dev/null || true
systemctl is-active nvidia-persistenced 2>/dev/null || true

log "Complete"
echo "completed_at=$(date -Is)"
echo "bootstrap_log=$BOOTSTRAP_LOG"

if [[ "$NO_REBOOT" -eq 0 ]]; then
  echo
  echo "Recommended next step if NVIDIA driver/kernel changed: sudo reboot"
fi
