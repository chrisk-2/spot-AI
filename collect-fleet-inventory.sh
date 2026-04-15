#!/usr/bin/env bash
set -u

OUT_DIR="${HOME}/spot-stack/fleet-inventory-$(date +%Y%m%d-%H%M%S)"
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
hostnamectl 2>/dev/null || true
echo

echo "===== HOSTNAME ====="
hostname || true
echo

echo "===== OS ====="
cat /etc/os-release 2>/dev/null || true
echo

echo "===== KERNEL ====="
uname -a || true
echo

echo "===== UPTIME ====="
uptime || true
echo

echo "===== CPU ====="
lscpu 2>/dev/null | sed -n '1,40p' || cat /proc/cpuinfo 2>/dev/null || true
echo

echo "===== RAM ====="
free -h || true
echo
grep -E "MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree" /proc/meminfo 2>/dev/null || true
echo

echo "===== STORAGE ====="
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,MODEL 2>/dev/null || true
echo
df -h 2>/dev/null || true
echo

echo "===== PCI GPU DEVICES ====="
lspci | grep -Ei "vga|3d|display|nvidia" || true
echo

echo "===== NVIDIA-SMI GPU SUMMARY ====="
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi || true
else
  echo "nvidia-smi not found"
fi
echo

echo "===== NVIDIA-SMI DETAILED ====="
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=index,name,uuid,memory.total,memory.used,memory.free,temperature.gpu,power.draw,utilization.gpu,pcie.link.gen.current,pcie.link.width.current --format=csv,noheader,nounits || true
else
  echo "nvidia-smi not found"
fi
echo

echo "===== GPU PROCESSES ====="
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi pmon -c 1 || true
else
  echo "nvidia-smi not found"
fi
echo

echo "===== NETWORK ADDRESSES ====="
ip -br addr 2>/dev/null || true
echo

echo "===== ROUTES ====="
ip route 2>/dev/null || true
echo

echo "===== DNS ====="
resolvectl status 2>/dev/null || cat /etc/resolv.conf 2>/dev/null || true
echo

echo "===== OLLAMA VERSION ====="
ollama --version 2>/dev/null || true
echo

echo "===== OLLAMA MODELS ====="
ollama list 2>/dev/null || true
echo

echo "===== DOCKER ====="
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null || true
echo

echo "===== IMPORTANT SERVICES ====="
systemctl --no-pager --type=service --state=running 2>/dev/null | grep -Ei "ollama|docker|nvidia|ssh|sshd" || true
echo

echo "===== MOUNTS ====="
mount | grep -E "/mnt|nfs|cifs" || true
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

echo "Inventory saved in: ${OUT_DIR}"
