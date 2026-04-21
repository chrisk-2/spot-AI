#!/usr/bin/env bash
set -euo pipefail

host="${1:?host required}"

GOOD_DNS_1="192.168.60.10"
GOOD_DNS_2="192.168.60.20"

declare -A HOST_IPS=(
  ["spot-worker-01"]="192.168.10.10"
  ["spot-worker-02"]="192.168.10.11"
  ["spot-worker-03"]="192.168.10.13"
  ["spot-worker-04"]="192.168.10.14"
  ["spot-ui-01"]="192.168.10.12"
  ["starfleet-tower"]="192.168.30.5"
  ["unimatrix6"]="192.168.50.10"
  ["starfleet-core"]="192.168.60.20"
  ["dns-core"]="192.168.60.10"
)

target_ip="${HOST_IPS[$host]:-}"
if [[ -z "$target_ip" ]]; then
  echo "[ERROR] unknown host: $host" >&2
  exit 1
fi

ssh_target="ogre@${target_ip}"

case "$host" in
  dns-core)
    echo "[SKIP] dns-core uses local resolver by design"
    exit 0
    ;;
  unimatrix6)
    echo "[SKIP] unimatrix6 should be corrected in DSM GUI, not by shell rewrite"
    exit 0
    ;;
esac

dns_raw="$(ssh -o BatchMode=yes -o ConnectTimeout=5 "$ssh_target" "cat /etc/resolv.conf 2>/dev/null || true")"

if echo "$dns_raw" | grep -q "127.0.0.53"; then
  echo "[INFO] $host uses systemd-resolved; attempting resolved.conf fix"

  ssh -o BatchMode=yes -o ConnectTimeout=5 "$ssh_target" "sudo bash -c 'cat > /etc/systemd/resolved.conf.d/99-starfleet-dns.conf <<CFG
[Resolve]
DNS=${GOOD_DNS_1} ${GOOD_DNS_2}
FallbackDNS=
Domains=starfleet.local
CFG
mkdir -p /etc/systemd/resolved.conf.d
systemctl restart systemd-resolved
'" || {
    echo "[ERROR] failed to update systemd-resolved on $host" >&2
    exit 1
  }

  exit 0
fi

echo "[INFO] $host uses static resolv.conf; applying static Starfleet DNS"

ssh -o BatchMode=yes -o ConnectTimeout=5 "$ssh_target" "sudo bash -c 'cat > /etc/resolv.conf <<CFG
nameserver ${GOOD_DNS_1}
nameserver ${GOOD_DNS_2}
search starfleet.local
CFG
'" || {
  echo "[ERROR] failed to write resolv.conf on $host" >&2
  exit 1
}
