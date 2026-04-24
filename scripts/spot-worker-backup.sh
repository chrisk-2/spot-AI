#!/usr/bin/env bash
set -euo pipefail

HOST="$(hostname)"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
ROOT="/mnt/collective/backups/${HOST}/worker-config/${TS}"
LATEST="/mnt/collective/backups/${HOST}/worker-config/latest"

mkdir -p "$ROOT"

write_cmd() {
  local name="$1"
  shift
  {
    echo "# command: $*"
    echo "# timestamp_utc: $TS"
    echo
    "$@" || true
  } > "$ROOT/$name"
}

copy_if_exists() {
  local src="$1"
  local dest="$2"
  if [ -e "$src" ]; then
    mkdir -p "$(dirname "$ROOT/$dest")"
    cp -R "$src" "$ROOT/$dest"
  fi
}

write_cmd hostname.txt hostname
write_cmd hostnamectl.txt hostnamectl
write_cmd uname.txt uname -a
write_cmd os-release.txt cat /etc/os-release
write_cmd mounts.txt findmnt
write_cmd df.txt df -h
write_cmd lsblk.txt lsblk -f
write_cmd fstab.txt cat /etc/fstab
write_cmd systemd-ollama-cat.txt systemctl cat ollama
write_cmd systemd-ollama-show.txt systemctl show ollama
write_cmd systemd-timers.txt systemctl list-timers --all
write_cmd crontab-ogre.txt bash -lc "crontab -l 2>/dev/null || true"
write_cmd nvidia-smi.txt nvidia-smi
write_cmd nvidia-smi-query.csv nvidia-smi --query-gpu=index,name,uuid,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu --format=csv,noheader,nounits
write_cmd ollama-list.txt ollama list
write_cmd packages-apt.txt bash -lc "dpkg-query -W 2>/dev/null || true"
write_cmd home-ogre-top.txt bash -lc "find /home/ogre -maxdepth 2 -mindepth 1 -printf '%M %u %g %s %TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null | sort"

copy_if_exists /etc/systemd/system/ollama.service etc/systemd/system/ollama.service
copy_if_exists /etc/systemd/system/ollama.service.d etc/systemd/system/ollama.service.d
copy_if_exists /home/ogre/codex_spot.sh home/ogre/codex_spot.sh
copy_if_exists /home/ogre/codex_worker03_install.sh home/ogre/codex_worker03_install.sh
copy_if_exists /home/ogre/backup-spot-repo.sh home/ogre/backup-spot-repo.sh
copy_if_exists /home/ogre/install_fleet_models.sh home/ogre/install_fleet_models.sh
copy_if_exists /home/ogre/codex-workspace home/ogre/codex-workspace
copy_if_exists /home/ogre/.starfleet-stage/fleet-docs home/ogre/.starfleet-stage/fleet-docs

{
  echo "{"
  echo "  \"host\": \"$HOST\","
  echo "  \"timestamp_utc\": \"$TS\","
  echo "  \"backup_root\": \"$ROOT\","
  echo "  \"policy\": \"worker config snapshot only; model blobs not included\","
  echo "  \"status\": \"complete\""
  echo "}"
} > "$ROOT/metadata.json"

sha256sum $(find "$ROOT" -type f | sort) > "$ROOT/SHA256SUMS"

rm -f "$LATEST"
ln -s "$ROOT" "$LATEST"

echo "$ROOT"
