#!/usr/bin/env bash
set -euo pipefail

HOST="${1:?usage: $0 <worker-host>}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
ROOT="/mnt/collective/backups/${HOST}/worker-config/${TS}"

mkdir -p "$ROOT"

run_remote() {
  local name="$1"
  shift
  {
    echo "# host: $HOST"
    echo "# command: $*"
    echo "# timestamp_utc: $TS"
    echo
    timeout 20s ssh -o BatchMode=yes -o ConnectTimeout=8 "$HOST" "$@" 2>&1 || true
  } > "$ROOT/$name"
}

copy_remote_if_exists() {
  local src="$1"
  local dest="$2"

  if timeout 15s ssh -o BatchMode=yes -o ConnectTimeout=8 "$HOST" "test -e '$src'" 2>/dev/null; then
    mkdir -p "$(dirname "$ROOT/$dest")"
    timeout 60s ssh -o BatchMode=yes -o ConnectTimeout=8 "$HOST" "tar -C / -czf - '${src#/}' 2>/dev/null" > "$ROOT/$dest.tar.gz" || true
  fi
}

run_remote hostname.txt hostname
run_remote hostnamectl.txt hostnamectl
run_remote uname.txt uname -a
run_remote os-release.txt cat /etc/os-release
run_remote mounts.txt findmnt
run_remote df.txt df -h
run_remote lsblk.txt lsblk -f
run_remote fstab.txt cat /etc/fstab
run_remote systemd-ollama-cat.txt systemctl cat ollama
run_remote systemd-ollama-show.txt systemctl show ollama
run_remote systemd-timers.txt systemctl list-timers --all
run_remote crontab-ogre.txt "crontab -l 2>/dev/null || true"
run_remote nvidia-smi.txt "command -v nvidia-smi >/dev/null && nvidia-smi || true"
run_remote nvidia-smi-query.csv "command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=index,name,uuid,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu --format=csv,noheader,nounits || true"
run_remote ollama-list.txt "command -v ollama >/dev/null && ollama list || true"
run_remote packages-apt.txt "dpkg-query -W 2>/dev/null || true"
run_remote home-ogre-top.txt "find /home/ogre -maxdepth 2 -mindepth 1 -printf '%M %u %g %s %TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null | sort"

copy_remote_if_exists /etc/systemd/system/ollama.service etc/systemd/system/ollama.service
copy_remote_if_exists /etc/systemd/system/ollama.service.d etc/systemd/system/ollama.service.d
copy_remote_if_exists /etc/hostname etc/hostname
copy_remote_if_exists /etc/hosts etc/hosts
copy_remote_if_exists /etc/fstab etc/fstab
copy_remote_if_exists /home/ogre/.ssh home/ogre/.ssh

cat > "$ROOT/metadata.json" <<META
{
  "host": "$HOST",
  "timestamp_utc": "$TS",
  "backup_root": "$ROOT",
  "policy": "remote worker config snapshot only; model blobs not included",
  "status": "complete"
}
META

find "$ROOT" -type f -print0 | sort -z | xargs -0 sha256sum > "$ROOT/SHA256SUMS"

# CIFS mount may reject symlinks; use marker file instead.
printf '%s\n' "$ROOT" > "/mnt/collective/backups/${HOST}/worker-config/LATEST_PATH.txt"

echo "$ROOT"
