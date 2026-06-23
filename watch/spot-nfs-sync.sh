#!/usr/bin/env bash
# spot-nfs-sync.sh — sync W-01 buffer back to /mnt/collective when NFS returns
# Called by fleet-watch.sh on unimatrix6 ping recovery, or manually via nfs_sync operator command.
set -uo pipefail

BUFFER_HOST="192.168.10.10"
BUFFER_ROOT="/home/ogre/spot-buffer"
NFS_ROOT="/mnt/collective"
SSH_KEY="$HOME/.ssh/spot_fleet"
LOG_FILE="/home/ogre/spot-stack/watch/logs/nfs-sync.log"
STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

log() { echo "[$STAMP] $*" | tee -a "$LOG_FILE"; }

# Check NFS is actually mounted and writable
if ! touch "$NFS_ROOT/.spot-nfs-sync-check" 2>/dev/null; then
    log "ERROR nfs_not_available mount=$NFS_ROOT — aborting sync"
    exit 1
fi
rm -f "$NFS_ROOT/.spot-nfs-sync-check"

# Check W-01 is reachable
if ! ssh -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=5 "ogre@$BUFFER_HOST" "test -d $BUFFER_ROOT" 2>/dev/null; then
    log "INFO w01_buffer_empty_or_unreachable host=$BUFFER_HOST — nothing to sync"
    exit 0
fi

# Check buffer has anything in it
BUFFER_COUNT=$(ssh -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=5 "ogre@$BUFFER_HOST" \
    "find $BUFFER_ROOT -type f 2>/dev/null | wc -l" 2>/dev/null || echo "0")

if [[ "$BUFFER_COUNT" -eq 0 ]]; then
    log "INFO w01_buffer_empty — nothing to sync"
    exit 0
fi

log "INFO starting_sync buffer_host=$BUFFER_HOST buffer_root=$BUFFER_ROOT nfs_root=$NFS_ROOT files=$BUFFER_COUNT"

# rsync buffer → NFS (archive mode, preserve structure, don't delete NFS-only files)
if rsync -av --no-delete \
    -e "ssh -i $SSH_KEY -o BatchMode=yes -o ConnectTimeout=10" \
    "ogre@${BUFFER_HOST}:${BUFFER_ROOT}/" \
    "${NFS_ROOT}/" \
    >> "$LOG_FILE" 2>&1; then

    log "INFO sync_complete files=$BUFFER_COUNT"

    # Clear the buffer on W-01 after successful sync
    ssh -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=5 "ogre@$BUFFER_HOST" \
        "rm -rf ${BUFFER_ROOT:?}/* && echo cleared" >> "$LOG_FILE" 2>&1 && \
        log "INFO w01_buffer_cleared" || \
        log "WARN w01_buffer_clear_failed — manual cleanup needed"
else
    log "ERROR rsync_failed — buffer preserved on W-01"
    exit 1
fi
