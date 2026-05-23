#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ogre/spot-stack"
cd "$ROOT"

cmd="${1:-help}"
shift || true

status() {
  git status --short
  git log --oneline -6
}

precheck() {
  git diff --check

  if git diff --cached --name-only | grep -E '\.md$' >/dev/null; then
    if git diff --cached --name-only | grep -E '\.md$' | xargs grep -n '^```' >/tmp/spot-module-md-fences.out 2>/dev/null; then
      echo "[FAIL] staged markdown contains fenced code blocks"
      cat /tmp/spot-module-md-fences.out
      echo "[INFO] use plain indented text in shell-created markdown"
      exit 2
    fi
  fi

  find watch spot-core scripts -type f \
    \( -name '*.sh' -o -name '*.py' \) 2>/dev/null \
  | while read -r f; do
      case "$f" in
        *.sh)
          bash -n "$f"
          ;;
        *.py)
          python3 -m py_compile "$f"
          ;;
      esac
    done
}

validate() {
  spot validate
}

operator_cmd() {
  exec watch/operator/spot-operator.sh "$@"
}

logs_cmd() {
  journalctl -u spot-core -n "${1:-50}" --no-pager
}

restart_cmd() {
  docker compose down
  docker compose up -d
}


commit_cmd() {
  msg="${1:-}"

  if [ -z "$msg" ]; then
    echo "[FAIL] commit message required"
    exit 2
  fi

  if git diff --cached --quiet; then
    echo "[FAIL] nothing staged"
    exit 2
  fi

  git commit -m "$msg"
}

module_cmd() {
  msg="${1:-}"

  precheck
  validate
  status
  commit_cmd "$msg"
  status
}

case "$cmd" in
  help|-h|--help)
    cat <<'EOF'
spot-module.sh commands:

  status
  precheck
  validate
  commit "message"
  module "message"

  operator ...
  logs [N]
  restart

  operator ...
  logs [N]
  restart
EOF
    ;;

  status)
    status
    ;;

  precheck)
    precheck
    ;;

  validate)
    validate
    ;;

  commit)
    commit_cmd "${1:-}"
    ;;

  module)
    module_cmd "${1:-}"
    ;;

  operator)
    shift || true
    operator_cmd "$@"
    ;;

  logs)
    logs_cmd "${1:-50}"
    ;;

  restart)
    restart_cmd
    ;;

  *)
    echo "[FAIL] unknown command: $cmd"
    exit 2
    ;;
esac
