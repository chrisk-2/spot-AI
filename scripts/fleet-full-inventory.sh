#!/usr/bin/env bash
set -euo pipefail

BASE="$HOME/spot-stack"
OUT="$BASE/fleet-inventory"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$OUT/runs/$STAMP"
LATEST="$OUT/latest"

mkdir -p "$RUN_DIR"/{raw,json}
mkdir -p "$OUT"

HOSTS=(
  "spot-worker-01|192.168.10.10|ENGINEERING|5|Worker node"
  "spot-worker-02|192.168.10.11|ENGINEERING|4|Worker node"
  "spot-ui-01|192.168.10.12|ENGINEERING|7|Interface / dashboard"
  "spot-worker-03|192.168.10.13|ENGINEERING|6|Worker node"
  "spot-worker-04|192.168.10.14|ENGINEERING|8|Worker node"
  "spot-worker-05|192.168.10.15|ENGINEERING||Visual / render node"
  "spot-worker-06|192.168.10.16|ENGINEERING||Utility prime candidate"
  "spot-worker-07|192.168.10.17|ENGINEERING||Heavy secondary candidate"
)

STATIC_CSV="$RUN_DIR/starfleet-network-map.csv"

cat > "$STATIC_CSV" <<'CSV'
Category,VLAN/Network,IP Address,Hostname,Switch Port,Description,GPU0,GPU1
CORE,192.168.1.x,192.168.1.1,OPNsense,1,Router / Firewall / Gateway / VPN,,
INFRASTRUCTURE,192.168.60.x,192.168.60.10,dns-core,22,Primary DNS / AdGuard,,
INFRASTRUCTURE,192.168.60.x,192.168.60.20,starfleet-core,21,NPM + UniFi + Secondary DNS + NTP,,
INFRASTRUCTURE,192.168.60.x,192.168.60.30,spot-core,24,Primary orchestrator,,
ENGINEERING,192.168.10.x,192.168.10.10,spot-worker-01,5,Worker node,w01-gpu0-rtx3060 (12g),
ENGINEERING,192.168.10.x,192.168.10.11,spot-worker-02,4,Worker node,w02-gpu0-m4000 (8g),w02-gpu1-gtx1060 (6g)
ENGINEERING,192.168.10.x,192.168.10.12,spot-ui-01,7,Interface / dashboard,,
ENGINEERING,192.168.10.x,192.168.10.13,spot-worker-03,6,Worker node,w03-gpu0-gtx1070 (8g),w03-gpu1-rtx3060 (12g)
ENGINEERING,192.168.10.x,192.168.10.14,spot-worker-04,8,Worker node,w04-gpu0-p6000 (24g),
ENGINEERING,192.168.10.x,192.168.10.15,spot-worker-05,,Visual / render node,w05-gpu0-titan-xp (12g),
ENGINEERING,192.168.10.x,192.168.10.16,spot-worker-06,,Utility prime candidate,pending,
ENGINEERING,192.168.10.x,192.168.10.17,spot-worker-07,,Heavy secondary candidate,w07-gpu0-p6000 (24g),
SECTION 31,192.168.30.x,192.168.30.5,starfleet-tower,13,Homarr / Portainer / Uptime Kuma / Glances / Netdata,,
UNIMATRIX,192.168.50.x,192.168.50.10,unimatrix6,,NAS / Storage,,
HOUSE,192.168.1.x,192.168.1.131,UniFi Switch,,Network switch,,
HOUSE,192.168.1.x,192.168.1.2,sentinel iDRAC,,Server management,,
HOUSE,192.168.1.x,192.168.1.3,sentinel-core,,Proxmox host,,
COMMAND,192.168.99.x,192.168.99.150,Ogre PC,,Primary workstation,,
VPN,10.6.0.x,10.6.0.1,WireGuard,,VPN endpoint,,
DNS,,192.168.60.10,Primary DNS,,,,
DNS,,192.168.60.20,Secondary DNS,,,,
NTP,,192.168.60.20,Primary NTP,,,,
NTP,,192.168.60.10,Backup NTP,,,,
REVERSE PROXY,,192.168.60.20:8443,unifi.starfleet.local,,,,
REVERSE PROXY,,192.168.60.10:80,adguard1.starfleet.local,,,,
REVERSE PROXY,,192.168.60.20:80,adguard2.starfleet.local,,,,
REVERSE PROXY,,192.168.30.5:7575,dashboard.starfleet.local,,,,
HOLODECK,192.168.20.x,,,Reserved / future use,,,
DEEP SPACE 9,192.168.40.x,,,Cameras & smart devices,,,
CSV

collect_host() {
  local host="$1" ip="$2" category="$3" switch_port="$4" description="$5"
  local raw="$RUN_DIR/raw/$host.txt"
  local json="$RUN_DIR/json/$host.json"

  echo "=== Collecting $host ($ip) ==="

  if ! ssh -o BatchMode=yes -o ConnectTimeout=8 "$host" "true" >/dev/null 2>&1; then
    cat > "$json" <<EOF
{
  "hostname": "$host",
  "ip": "$ip",
  "category": "$category",
  "switch_port": "$switch_port",
  "description": "$description",
  "reachable": false,
  "collected_at": "$(date -Is)"
}
EOF
    echo "WARN: $host unreachable"
    return 0
  fi

  ssh -o BatchMode=yes -o ConnectTimeout=8 "$host" 'bash -s' > "$raw" <<'REMOTE'
echo "COLLECTED_AT=$(date -Is)"
echo "HOSTNAME=$(hostname)"
echo "KERNEL=$(uname -r)"
echo "OS=$(awk -F= "/^PRETTY_NAME=/{gsub(/\"/,\"\",\$2); print \$2}" /etc/os-release)"
echo "CPU=$(lscpu | awk -F: "/Model name/{gsub(/^[ \t]+/,\"\",\$2); print \$2; exit}")"
echo "CPU_CORES=$(lscpu | awk -F: "/^CPU\\(s\\)/{gsub(/^[ \t]+/,\"\",\$2); print \$2; exit}")"
echo "RAM_TOTAL=$(free -h | awk "/^Mem:/{print \$2}")"
echo "RAM_AVAILABLE=$(free -h | awk "/^Mem:/{print \$7}")"
echo "PRIMARY_IP=$(hostname -I | awk "{print \$1}")"
echo "DEFAULT_ROUTE=$(ip route | awk "/default/{print \$3\" via \"\$5; exit}")"
echo "DISKS=$(lsblk -dn -o NAME,SIZE,MODEL | sed "s/[[:space:]]\+/ /g" | paste -sd "; " -)"
echo "MOUNTS=$(df -h --output=source,target,size,used,avail,pcent | tail -n +2 | sed "s/[[:space:]]\+/ /g" | paste -sd "; " -)"
echo "FAILED_SERVICES=$(systemctl --failed --no-legend 2>/dev/null | wc -l)"
echo "SSH_ACTIVE=$(systemctl is-active ssh 2>/dev/null || systemctl is-active sshd 2>/dev/null || true)"
echo "OLLAMA_ACTIVE=$(systemctl is-active ollama 2>/dev/null || true)"
echo "OLLAMA_VERSION=$(ollama --version 2>/dev/null || true)"
echo "OLLAMA_MODELS=$(ollama list 2>/dev/null | tail -n +2 | awk "{print \$1\" \"\$3\" \"\$4}" | paste -sd "; " -)"
echo "DOCKER_VERSION=$(docker --version 2>/dev/null || true)"
echo "DOCKER_RUNNING=$(docker ps --format "{{.Names}}" 2>/dev/null | paste -sd "," -)"
echo "GPU_SUMMARY=$(nvidia-smi --query-gpu=index,name,uuid,pci.bus_id,memory.total,driver_version,temperature.gpu,power.draw,power.limit --format=csv,noheader,nounits 2>/dev/null | paste -sd "; " -)"
echo "NVIDIA_PERSISTENCED=$(systemctl is-active nvidia-persistenced 2>/dev/null || true)"
REMOTE

  python3 - "$raw" "$json" "$host" "$ip" "$category" "$switch_port" "$description" <<'PY'
import json, sys
raw_path, json_path, host, ip, category, switch_port, description = sys.argv[1:]
data = {}
with open(raw_path, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.rstrip("\n")
        if "=" in line:
            k, v = line.split("=", 1)
            data[k] = v

out = {
    "hostname": host,
    "ip": ip,
    "category": category,
    "switch_port": switch_port,
    "description": description,
    "reachable": True,
    "collected_at": data.get("COLLECTED_AT"),
    "reported_hostname": data.get("HOSTNAME"),
    "os": data.get("OS"),
    "kernel": data.get("KERNEL"),
    "cpu": data.get("CPU"),
    "cpu_threads": data.get("CPU_CORES"),
    "ram_total": data.get("RAM_TOTAL"),
    "ram_available": data.get("RAM_AVAILABLE"),
    "primary_ip": data.get("PRIMARY_IP"),
    "default_route": data.get("DEFAULT_ROUTE"),
    "disks": data.get("DISKS"),
    "mounts": data.get("MOUNTS"),
    "failed_services": data.get("FAILED_SERVICES"),
    "ssh_active": data.get("SSH_ACTIVE"),
    "ollama_active": data.get("OLLAMA_ACTIVE"),
    "ollama_version": data.get("OLLAMA_VERSION"),
    "ollama_models": data.get("OLLAMA_MODELS"),
    "docker_version": data.get("DOCKER_VERSION"),
    "docker_running": data.get("DOCKER_RUNNING"),
    "gpu_summary": data.get("GPU_SUMMARY"),
    "nvidia_persistenced": data.get("NVIDIA_PERSISTENCED"),
}
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
PY
}

for row in "${HOSTS[@]}"; do
  IFS='|' read -r host ip category switch_port description <<< "$row"
  collect_host "$host" "$ip" "$category" "$switch_port" "$description"
done

SUMMARY_MD="$RUN_DIR/FLEET-INVENTORY-$STAMP.md"
SUMMARY_CSV="$RUN_DIR/fleet-inventory-$STAMP.csv"

python3 - "$RUN_DIR/json" "$SUMMARY_MD" "$SUMMARY_CSV" "$STAMP" <<'PY'
import csv, json, sys
from pathlib import Path

json_dir, md_path, csv_path, stamp = sys.argv[1:]
items = []
for p in sorted(Path(json_dir).glob("*.json")):
    with open(p, "r", encoding="utf-8") as f:
        items.append(json.load(f))

cols = [
    "hostname","ip","category","switch_port","description","reachable",
    "os","kernel","cpu","cpu_threads","ram_total","primary_ip",
    "gpu_summary","nvidia_persistenced","ollama_active","ollama_models","failed_services"
]

with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for item in items:
        w.writerow({c: item.get(c, "") for c in cols})

lines = []
lines.append(f"# Starfleet Fleet Inventory — {stamp}")
lines.append("")
lines.append("| Host | IP | Reachable | CPU | RAM | GPU | Ollama | Models |")
lines.append("|---|---:|---:|---|---:|---|---:|---|")
for i in items:
    lines.append(
        f"| {i.get('hostname','')} | {i.get('ip','')} | {i.get('reachable')} | "
        f"{i.get('cpu','')} | {i.get('ram_total','')} | {i.get('gpu_summary','')} | "
        f"{i.get('ollama_active','')} | {i.get('ollama_models','')} |"
    )

lines.append("")
lines.append("## Notes")
lines.append("- Collection is read-only.")
lines.append("- Unreachable hosts are recorded instead of blocking the run.")
lines.append("- Raw SSH output is stored under `raw/`.")
lines.append("- Per-host JSON is stored under `json/`.")

Path(md_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

rm -f "$LATEST"
ln -s "$RUN_DIR" "$LATEST"

cp "$SUMMARY_MD" "$OUT/FLEET-INVENTORY-latest.md"
cp "$SUMMARY_CSV" "$OUT/fleet-inventory-latest.csv"
cp "$STATIC_CSV" "$OUT/starfleet-network-map-latest.csv"

echo
echo "DONE"
echo "Run dir: $RUN_DIR"
echo "Latest markdown: $OUT/FLEET-INVENTORY-latest.md"
echo "Latest CSV: $OUT/fleet-inventory-latest.csv"
echo "Static map CSV: $OUT/starfleet-network-map-latest.csv"
