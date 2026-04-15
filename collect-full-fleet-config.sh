#!/usr/bin/env bash
set -u

OUT_DIR="${HOME}/spot-stack/full-fleet-config-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT_DIR"

declare -A HOSTS=(
  ["spot-worker-01"]="192.168.10.10"
  ["spot-worker-02"]="192.168.10.11"
  ["spot-worker-03"]="192.168.10.13"
  ["spot-worker-04"]="192.168.10.14"
)

for NAME in "${!HOSTS[@]}"; do
  IP="${HOSTS[$NAME]}"
  OUT_FILE="${OUT_DIR}/${NAME}.txt"

  echo "=== Collecting from ${NAME} (${IP}) ==="

  ssh \
    -o ConnectTimeout=8 \
    -o StrictHostKeyChecking=accept-new \
    "ogre@${IP}" 'bash -s' > "${OUT_FILE}" 2>&1 <<'REMOTE'
set -u

echo "===== BASIC ====="
date
echo

echo "===== HOSTNAMECTL ====="
hostnamectl 2>/dev/null || true
echo

echo "===== HOSTNAME ====="
hostname || true
echo

echo "===== OS RELEASE ====="
cat /etc/os-release 2>/dev/null || true
echo

echo "===== KERNEL ====="
uname -a || true
echo

echo "===== UPTIME ====="
uptime || true
echo

echo "===== CPU LSCU ====="
lscpu 2>/dev/null || true
echo

echo "===== CPUINFO TOP ====="
sed -n '1,80p' /proc/cpuinfo 2>/dev/null || true
echo

echo "===== RAM ====="
free -h || true
echo
grep -E 'MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree' /proc/meminfo 2>/dev/null || true
echo

echo "===== MAINBOARD / BIOS ====="
sudo dmidecode -t baseboard -t bios -t system 2>/dev/null || dmidecode -t baseboard -t bios -t system 2>/dev/null || true
echo

echo "===== STORAGE LSBLK ====="
lsblk -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINT,MODEL,SERIAL 2>/dev/null || true
echo

echo "===== STORAGE DF ====="
df -h 2>/dev/null || true
echo

echo "===== FSTAB ====="
cat /etc/fstab 2>/dev/null || true
echo

echo "===== MOUNTS OF INTEREST ====="
mount | grep -E '/mnt|nfs|cifs|collective|shared|docker' || true
echo

echo "===== NETWORK BRIEF ====="
ip -br addr 2>/dev/null || true
echo

echo "===== ROUTES ====="
ip route 2>/dev/null || true
echo

echo "===== DNS ====="
resolvectl status 2>/dev/null || cat /etc/resolv.conf 2>/dev/null || true
echo

echo "===== LISTENING PORTS ====="
ss -tulpn 2>/dev/null || true
echo

echo "===== IMPORTANT SERVICES ====="
systemctl --no-pager --type=service --all 2>/dev/null | grep -Ei 'ollama|docker|nvidia|ssh|sshd|cron|systemd-resolved' || true
echo

echo "===== OLLAMA VERSION ====="
ollama --version 2>/dev/null || true
echo

echo "===== OLLAMA MODELS ====="
ollama list 2>/dev/null || true
echo

echo "===== DOCKER PS ====="
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || true
echo

echo "===== PCI ALL RELEVANT ====="
lspci | grep -Ei 'vga|3d|display|nvidia|ethernet|network|raid|sata|nvme' || true
echo

echo "===== NVIDIA-SMI SUMMARY ====="
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi || true
else
  echo "nvidia-smi not found"
fi
echo

echo "===== NVIDIA-SMI DETAILED ====="
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=index,name,uuid,memory.total,memory.used,memory.free,temperature.gpu,power.draw,utilization.gpu,pcie.link.gen.current,pcie.link.width.current,driver_version --format=csv,noheader,nounits || true
else
  echo "nvidia-smi not found"
fi
echo

echo "===== NVIDIA GPU PROCESSES ====="
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi pmon -c 1 || true
else
  echo "nvidia-smi not found"
fi
echo

echo "===== NVIDIA TOPO ====="
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi topo -m 2>/dev/null || true
else
  echo "nvidia-smi not found"
fi
echo

echo "===== ENV HINTS ====="
env | grep -Ei 'ollama|cuda|nvidia' || true
echo
REMOTE

  RC=$?
  if [ $RC -ne 0 ]; then
    echo "[FAIL] ${NAME} (${IP}) rc=${RC} -- see ${OUT_FILE}"
  else
    echo "[OK]   ${NAME} (${IP}) -> ${OUT_FILE}"
  fi
  echo
done

echo "Saved in: ${OUT_DIR}"

