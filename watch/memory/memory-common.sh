#!/usr/bin/env bash

MEMORY_ROOT="${SPOT_MEMORY_ROOT:-/mnt/collective/memory/spot}"

require_memory_root() {
  if [[ ! -d /mnt/collective ]]; then
    echo "ERROR: /mnt/collective is unavailable" >&2
    return 1
  fi

  mkdir -p "$MEMORY_ROOT"

  if [[ ! -w "$MEMORY_ROOT" ]]; then
    echo "ERROR: memory root is not writable: $MEMORY_ROOT" >&2
    return 1
  fi
}

memory_id() {
  local category="$1"

  printf '%s-%s-%s-%s\n' \
    "$category" \
    "$(hostname -s)" \
    "$(date -u +%Y%m%dT%H%M%SZ)" \
    "$$"
}

append_json_line() {
  local index="$1"
  local record="$2"
  local lock="${index}.lock"

  mkdir -p "$(dirname "$index")"

  exec 9>>"$lock"
  flock -x 9
  printf '%s\n' "$record" >>"$index"
  flock -u 9
  exec 9>&-
}

write_checksum() {
  local artifact="$1"
  local checksum="${artifact}.sha256"

  set -o noclobber
  sha256sum "$artifact" >"$checksum"
  set +o noclobber

  printf '%s\n' "$checksum"
}
