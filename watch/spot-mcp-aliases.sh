spotctl() {
  python3 /home/ogre/spot-stack/watch/spot-mcp-tool.py "$@"
}

spot_health() {
  spotctl health
}

spot_route() {
  spotctl routing
}

spot_fleet() {
  spotctl fleet-ping
}

spot_audit() {
  spotctl routing-audit --limit "${1:-20}"
}

spot_validate() {
  local worker="$1"
  shift
  spotctl validate --worker "$worker" "$@"
}

spot_read() {
  local worker="$1"
  local path="$2"
  spotctl read-file --worker "$worker" --path "$path"
}

spot_restart() {
  local worker="$1"
  local service="$2"
  spotctl restart-service --worker "$worker" --service "$service"
}

spot_quarantine() {
  local worker="$1"
  local seconds="${2:-1800}"
  local reason="${3:-manual_quarantine}"
  spotctl quarantine --worker "$worker" --seconds "$seconds" --reason "$reason"
}

spot_release() {
  local worker="$1"
  spotctl release --worker "$worker"
}
