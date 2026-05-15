#!/usr/bin/env bash
set -Eeuo pipefail

BASE="/mnt/collective/backups"
LOG_DIR="/home/ogre/spot-stack/watch/logs"
LOG="${LOG_DIR}/fleet-worker-config-backup.log"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$LOG_DIR"

workers=(
  spot-worker-01
  spot-worker-02
  spot-worker-03
  spot-worker-04
  spot-worker-05
  spot-worker-06
)

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$LOG"
}

backup_worker() {
  local worker="$1"
  local root="${BASE}/${worker}/worker-config"
  local dest="${root}/${TS}"
  local tmp="${dest}.tmp"

  mkdir -p "$root"
  rm -rf "$tmp"
  mkdir -p "$tmp"

  log "START worker=${worker} dest=${dest}"

  if ! timeout 15s ssh -o BatchMode=yes -o ConnectTimeout=8 "$worker" 'hostname' >/dev/null 2>&1; then
    cat > "${tmp}/metadata.json" <<META
{
  "timestamp_utc": "${TS}",
  "worker": "${worker}",
  "type": "worker-config",
  "status": "failed",
  "error": "ssh_unreachable",
  "source": "fleet-worker-config-backup"
}
META
    mv "$tmp" "$dest"
    rm -rf "${root}/latest"
    ln -s "$dest" "${root}/latest"
    log "WARN worker=${worker} ssh_unreachable metadata=${dest}/metadata.json"
    return 0
  fi

    if timeout 45s ssh -o BatchMode=yes -o ConnectTimeout=8 "$worker" '
          tar czf - \
            /etc/hostname \
            /etc/hosts \
            /etc/ollama \
            /etc/systemd/system \
            2>/dev/null || true
        ' > "${tmp}/config.tar.gz"; then
    status="ok"
    error=""
  else
    status="failed"
    error="tar_failed"
    rm -f "${tmp}/config.tar.gz"
  fi

  cat > "${tmp}/metadata.json" <<META
{
  "timestamp_utc": "${TS}",
  "worker": "${worker}",
  "type": "worker-config",
  "status": "${status}",
  "error": "${error}",
  "source": "fleet-worker-config-backup"
}
META

  mv "$tmp" "$dest"

  if [[ "$status" == "ok" ]]; then
    log "OK worker=${worker} metadata=${dest}/metadata.json"
  else
    log "WARN worker=${worker} error=${error} metadata=${dest}/metadata.json"
  fi
}

    if [[ $# -gt 0 ]]; then
      backup_worker "$1"
    else
      for worker in "${workers[@]}"; do
        backup_worker "$worker"
      done
    fi

log "DONE timestamp=${TS}"
