#!/usr/bin/env bash
set -euo pipefail

CAP_DIR="${CAP_DIR:-/home/ogre/spot-stack/watch/capabilities}"

usage() {
  cat <<USAGE
Usage:
  spot-capabilities.sh list
  spot-capabilities.sh show <worker>
  spot-capabilities.sh find <capability>
USAGE
}

need_jq() {
  command -v jq >/dev/null 2>&1 || {
    echo "ERROR: jq required" >&2
    exit 2
  }
}

cmd_list() {
  need_jq
  find "$CAP_DIR" -maxdepth 1 -type f -name '*.json' -print0 \
    | sort -z \
    | xargs -0 jq -r '[.worker,.primary_role,.status,(.capabilities|join(","))] | @tsv' \
    | column -t -s $'\t'
}

cmd_show() {
  need_jq
  local worker="${1:-}"
  [[ -n "$worker" ]] || { echo "ERROR: worker required" >&2; exit 2; }
  jq . "$CAP_DIR/${worker}.json"
}

cmd_find() {
  need_jq
  local capability="${1:-}"
  [[ -n "$capability" ]] || { echo "ERROR: capability required" >&2; exit 2; }

  find "$CAP_DIR" -maxdepth 1 -type f -name '*.json' -print0 \
    | sort -z \
    | xargs -0 jq -r --arg cap "$capability" '
      select(.capabilities | index($cap)) |
      [.worker,.primary_role,.status] | @tsv
    ' \
    | column -t -s $'\t'
}

case "${1:-}" in
  list) shift; cmd_list "$@" ;;
  show) shift; cmd_show "$@" ;;
  find) shift; cmd_find "$@" ;;
  -h|--help|help|"") usage ;;
  *) echo "ERROR: unknown command: $1" >&2; usage >&2; exit 2 ;;
esac
