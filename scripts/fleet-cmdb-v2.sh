#!/usr/bin/env bash
set -euo pipefail

BASE="$HOME/spot-stack"
OUT="$BASE/fleet-inventory"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$OUT/runs/cmdb-$STAMP"
LATEST="$OUT/latest-cmdb"

mkdir -p "$RUN_DIR"/{raw,json}
mkdir -p "$OUT"

HOSTS=(
  "spot-ui-01|192.168.10.12|ENGINEERING|7|Interface / dashboard"
  "spot-worker-01|192.168.10.10|ENGINEERING|5|Worker node"
  "spot-worker-02|192.168.10.11|ENGINEERING|4|Worker node"
  "spot-worker-03|192.168.10.13|ENGINEERING|6|Worker node"
  "spot-worker-04|192.168.10.14|ENGINEERING|8|Worker node"
  "spot-worker-05|192.168.10.15|ENGINEERING||Worker node"
  "spot-core|192.168.60.30|INFRASTRUCTURE|24|Primary orchestrator"
  "dns-core|192.168.60.10|INFRASTRUCTURE|22|Primary DNS / AdGuard"
  "starfleet-core|192.168.60.20|INFRASTRUCTURE|21|NPM + UniFi + Secondary DNS + NTP"
  "starfleet-tower|192.168.30.5|SECTION 31|13|Homarr / Portainer / Uptime Kuma / Glances / Netdata"
  "sentinel-core|192.168.1.3|HOUSE||Proxmox host"
)

collect_host() {
  local host="$1" ip="$2" category="$3" switch_port="$4" description="$5"
  local raw="$RUN_DIR/raw/$host.txt"
  local json="$RUN_DIR/json/$host.json"

  echo "=== Collecting $host ($ip) ==="

  if ! ssh -o BatchMode=yes -o ConnectTimeout=8 "$host" "true" >/dev/null 2>&1; then
    cat > "$json" <<EOF
{
  "identity": {
    "hostname": "$host",
    "reported_hostname": "$host",
    "ip": "$ip",
    "category": "$category",
    "switch_port": "$switch_port",
    "description": "$description",
    "reachable": false,
    "collected_at": "$(date -Is)"
  },
  "system": {},
  "cpu": {},
  "memory": {},
  "network": {},
  "storage": {},
  "gpu": {
    "summary": [],
    "topology": []
  },
  "services": {},
  "ollama": {
    "models": []
  },
  "thermal": {}
}
EOF

    echo "WARN: $host unreachable"
    return 0
  fi

  ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" 'bash -s' > "$raw" <<'REMOTE'
safe() { "$@" 2>/dev/null || true; }

echo "COLLECTED_AT=$(date -Is)"
echo "HOSTNAME=$(hostname)"
echo "HOSTNAMECTL=$(hostnamectl --static 2>/dev/null || hostname)"
echo "OS=$(awk -F= '/^PRETTY_NAME=/{gsub(/"/,"",$2); print $2}' /etc/os-release)"
echo "KERNEL=$(uname -r)"
echo "UPTIME=$(uptime -p)"

echo "CPU_MODEL=$(lscpu | awk -F: '/Model name/{gsub(/^[ \t]+/,"",$2); print $2; exit}')"
echo "CPU_THREADS=$(lscpu | awk -F: '/^CPU\(s\)/{gsub(/^[ \t]+/,"",$2); print $2; exit}')"
echo "CPU_CORES=$(lscpu | awk -F: '/Core\(s\) per socket/{gsub(/^[ \t]+/,"",$2); print $2; exit}')"
echo "CPU_SOCKETS=$(lscpu | awk -F: '/Socket\(s\)/{gsub(/^[ \t]+/,"",$2); print $2; exit}')"

echo "RAM_TOTAL=$(free -h | awk '/^Mem:/{print $2}')"
echo "RAM_USED=$(free -h | awk '/^Mem:/{print $3}')"
echo "RAM_AVAILABLE=$(free -h | awk '/^Mem:/{print $7}')"
echo "SWAP_TOTAL=$(free -h | awk '/^Swap:/{print $2}')"
echo "SWAP_USED=$(free -h | awk '/^Swap:/{print $3}')"

echo "DMI_SYSTEM_VENDOR=$(safe sudo dmidecode -s system-manufacturer)"
echo "DMI_SYSTEM_PRODUCT=$(safe sudo dmidecode -s system-product-name)"
echo "DMI_BOARD_VENDOR=$(safe sudo dmidecode -s baseboard-manufacturer)"
echo "DMI_BOARD_PRODUCT=$(safe sudo dmidecode -s baseboard-product-name)"
echo "DMI_BIOS_VERSION=$(safe sudo dmidecode -s bios-version)"
echo "DMI_BIOS_DATE=$(safe sudo dmidecode -s bios-release-date)"

echo "MEMORY_DEVICES=$(safe sudo dmidecode -t memory | awk '
/Memory Device$/ {slot=""; size=""; type=""; speed=""; part=""}
/Locator:/ && slot=="" {slot=$2}
/Size:/ && size=="" {$1=""; sub(/^ /,""); size=$0}
/Type:/ && type=="" && $2!="Detail:" {type=$2}
/Configured Memory Speed:/ {$1=$2=$3=""; sub(/^   /,""); speed=$0}
/Part Number:/ {$1=$2=""; sub(/^  /,""); part=$0}
part!="" && size!="" && slot!="" {print slot "|" size "|" type "|" speed "|" part; part=""; size=""; slot=""}
' | paste -sd ';' -)"

echo "PRIMARY_IP=$(hostname -I | awk '{print $1}')"
echo "ALL_IPS=$(hostname -I | xargs)"
echo "DEFAULT_ROUTE=$(ip route | awk '/default/{print $3" via "$5; exit}')"
echo "NIC_BRIEF=$(ip -br link | sed 's/[[:space:]]\+/ /g' | paste -sd ';' -)"
echo "NIC_SPEEDS=$(for n in $(ls /sys/class/net | grep -v lo); do printf "%s=" "$n"; cat /sys/class/net/$n/speed 2>/dev/null || printf "unknown"; printf ";"; done)"
echo "DNS=$(resolvectl dns 2>/dev/null | sed 's/[[:space:]]\+/ /g' | paste -sd ';' -)"

echo "DISKS=$(lsblk -dn -o NAME,SIZE,TYPE,MODEL,SERIAL | sed 's/[[:space:]]\+/ /g' | paste -sd ';' -)"
echo "FILESYSTEMS=$(df -h --output=source,target,size,used,avail,pcent | tail -n +2 | sed 's/[[:space:]]\+/ /g' | paste -sd ';' -)"
echo "NVME_HEALTH=$(for d in /dev/nvme*n1; do [ -e "$d" ] || continue; printf "%s|" "$d"; safe sudo nvme smart-log "$d" | awk -F: '/temperature|percentage_used|data_units_written|critical_warning/{gsub(/^[ \t]+/,"",$2); printf "%s=%s,", $1, $2}'; printf ";"; done)"

echo "GPU_QUERY=$(nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,driver_version,temperature.gpu,power.draw,power.limit,pcie.link.gen.current,pcie.link.width.current,vbios_version --format=csv,noheader,nounits 2>/dev/null | paste -sd ';' -)"
echo "GPU_TOPO=$(nvidia-smi topo -m 2>/dev/null | head -n 20 | sed 's/[[:space:]]\+/ /g' | paste -sd ';' -)"

echo "FAILED_SERVICES=$(systemctl --failed --no-legend 2>/dev/null | wc -l)"
echo "FAILED_SERVICE_NAMES=$(systemctl --failed --no-legend 2>/dev/null | awk '{print $1}' | paste -sd ',' -)"
echo "SSH_ACTIVE=$(systemctl is-active ssh 2>/dev/null || systemctl is-active sshd 2>/dev/null || true)"
echo "OLLAMA_ACTIVE=$(systemctl is-active ollama 2>/dev/null || true)"
echo "OLLAMA_VERSION=$(ollama --version 2>/dev/null || true)"
echo "OLLAMA_MODELS=$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1" "$3" "$4}' | paste -sd ';' -)"

echo "DOCKER_VERSION=$(docker --version 2>/dev/null || true)"
echo "DOCKER_RUNNING=$(docker ps --format '{{.Names}}' 2>/dev/null | paste -sd ',' -)"
echo "PYTHON_VERSION=$(python3 --version 2>/dev/null || true)"
echo "TOOLS=$(for t in curl jq git docker nvidia-smi ollama sensors nvme; do command -v $t >/dev/null && printf "$t=yes;" || printf "$t=no;"; done)"
echo "TEMPS=$(sensors 2>/dev/null | awk '/Package id|Core [0-9]+|Composite|temp1/ {gsub(/^[ \t]+/,""); print}' | paste -sd ';' -)"
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

def split_semicolon(value):
    return [x for x in (value or "").split(";") if x]

out = {
    "identity": {
        "hostname": host,
        "reported_hostname": data.get("HOSTNAME"),
        "ip": ip,
        "category": category,
        "switch_port": switch_port,
        "description": description,
        "reachable": True,
        "collected_at": data.get("COLLECTED_AT"),
    },
    "system": {
        "os": data.get("OS"),
        "kernel": data.get("KERNEL"),
        "uptime": data.get("UPTIME"),
        "vendor": data.get("DMI_SYSTEM_VENDOR"),
        "product": data.get("DMI_SYSTEM_PRODUCT"),
        "board_vendor": data.get("DMI_BOARD_VENDOR"),
        "board_product": data.get("DMI_BOARD_PRODUCT"),
        "bios_version": data.get("DMI_BIOS_VERSION"),
        "bios_date": data.get("DMI_BIOS_DATE"),
    },
    "cpu": {
        "model": data.get("CPU_MODEL"),
        "threads": data.get("CPU_THREADS"),
        "cores_per_socket": data.get("CPU_CORES"),
        "sockets": data.get("CPU_SOCKETS"),
    },
    "memory": {
        "total": data.get("RAM_TOTAL"),
        "used": data.get("RAM_USED"),
        "available": data.get("RAM_AVAILABLE"),
        "swap_total": data.get("SWAP_TOTAL"),
        "swap_used": data.get("SWAP_USED"),
        "devices": split_semicolon(data.get("MEMORY_DEVICES")),
    },
    "network": {
        "primary_ip": data.get("PRIMARY_IP"),
        "all_ips": data.get("ALL_IPS"),
        "default_route": data.get("DEFAULT_ROUTE"),
        "nic_brief": split_semicolon(data.get("NIC_BRIEF")),
        "nic_speeds": split_semicolon(data.get("NIC_SPEEDS")),
        "dns": split_semicolon(data.get("DNS")),
    },
    "storage": {
        "disks": split_semicolon(data.get("DISKS")),
        "filesystems": split_semicolon(data.get("FILESYSTEMS")),
        "nvme_health": split_semicolon(data.get("NVME_HEALTH")),
    },
    "gpu": {
        "summary": split_semicolon(data.get("GPU_QUERY")),
        "topology": split_semicolon(data.get("GPU_TOPO")),
    },
    "services": {
        "failed_count": data.get("FAILED_SERVICES"),
        "failed_names": data.get("FAILED_SERVICE_NAMES"),
        "ssh_active": data.get("SSH_ACTIVE"),
        "ollama_active": data.get("OLLAMA_ACTIVE"),
        "docker_version": data.get("DOCKER_VERSION"),
        "docker_running": data.get("DOCKER_RUNNING"),
        "python_version": data.get("PYTHON_VERSION"),
        "tools": split_semicolon(data.get("TOOLS")),
    },
    "ollama": {
        "version": data.get("OLLAMA_VERSION"),
        "models": split_semicolon(data.get("OLLAMA_MODELS")),
    },
    "thermal": {
        "temps": split_semicolon(data.get("TEMPS")),
    },
}

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
PY
}

for row in "${HOSTS[@]}"; do
  IFS='|' read -r host ip category switch_port description <<< "$row"
  collect_host "$host" "$ip" "$category" "$switch_port" "$description"
done

python3 - "$RUN_DIR/json" "$RUN_DIR" "$STAMP" "$OUT" <<'PY'
import csv, json, sys
from pathlib import Path

json_dir = Path(sys.argv[1])
run_dir = Path(sys.argv[2])
stamp = sys.argv[3]
out_dir = Path(sys.argv[4])

items = []
for p in sorted(json_dir.glob("*.json")):
    items.append(json.loads(p.read_text(encoding="utf-8")))

cmdb = {
    "generated_at": stamp,
    "node_count": len(items),
    "nodes": items,
}

(run_dir / f"fleet-cmdb-{stamp}.json").write_text(json.dumps(cmdb, indent=2), encoding="utf-8")
(out_dir / "fleet-cmdb-latest.json").write_text(json.dumps(cmdb, indent=2), encoding="utf-8")

rows = []
for n in items:
    ident = n["identity"]
    rows.append({
        "hostname": ident.get("hostname"),
        "ip": ident.get("ip"),
        "category": ident.get("category"),
        "switch_port": ident.get("switch_port"),
        "reachable": ident.get("reachable"),
        "os": n["system"].get("os"),
        "kernel": n["system"].get("kernel"),
        "cpu": n["cpu"].get("model"),
        "ram": n["memory"].get("total"),
        "board": f"{n['system'].get('board_vendor','')} {n['system'].get('board_product','')}".strip(),
        "gpu": " | ".join(n["gpu"].get("summary", [])),
        "ollama": n["services"].get("ollama_active"),
        "models": " | ".join(n["ollama"].get("models", [])),
        "failed_services": n["services"].get("failed_count"),
    })

csv_path = run_dir / f"fleet-cmdb-{stamp}.csv"
with csv_path.open("w", newline="", encoding="utf-8") as f:
    fields = list(rows[0].keys()) if rows else []
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

md = []
md.append(f"# Starfleet CMDB Inventory — {stamp}")
md.append("")
md.append("| Host | IP | CPU | RAM | Board | GPU | Ollama | Failed |")
md.append("|---|---:|---|---:|---|---|---:|---:|")
for r in rows:
    md.append(f"| {r['hostname']} | {r['ip']} | {r['cpu']} | {r['ram']} | {r['board']} | {r['gpu']} | {r['ollama']} | {r['failed_services']} |")

md.append("")
md.append("## Artifacts")
md.append(f"- JSON: `fleet-cmdb-{stamp}.json`")
md.append(f"- CSV: `fleet-cmdb-{stamp}.csv`")
md.append("- Raw per-host captures: `raw/`")
md.append("- Per-host normalized JSON: `json/`")
md.append("")
md.append("## Safety")
md.append("- Read-only inventory collection.")
md.append("- No file writes on workers.")
md.append("- No service restarts.")
md.append("- No package installs.")

md_text = "\n".join(md) + "\n"
(run_dir / f"FLEET-CMDB-{stamp}.md").write_text(md_text, encoding="utf-8")
(out_dir / "FLEET-CMDB-latest.md").write_text(md_text, encoding="utf-8")
(out_dir / "fleet-cmdb-latest.csv").write_text(csv_path.read_text(encoding="utf-8"), encoding="utf-8")
PY

rm -f "$LATEST"
ln -s "$RUN_DIR" "$LATEST"

echo
echo "DONE"
echo "Run dir: $RUN_DIR"
echo "Latest CMDB markdown: $OUT/FLEET-CMDB-latest.md"
echo "Latest CMDB JSON: $OUT/fleet-cmdb-latest.json"
echo "Latest CMDB CSV: $OUT/fleet-cmdb-latest.csv"
