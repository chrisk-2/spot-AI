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

commit_cmd() {
  msg="${1:-}"

  if [ -z "$msg" ]; then
    echo "[FAIL] commit message required"
    exit 2
  fi

  git status --short

  if git diff --cached --quiet; then
    echo
    echo "[FAIL] nothing staged"
    echo "[INFO] stage files manually first"
    exit 2
  fi

  git commit -m "$msg"

  git status --short
  git log --oneline -6
}

case "$cmd" in
  help|-h|--help)
    cat <<'EOF'
spot-module.sh commands:

  status
  precheck
  validate
  commit "message"
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

  *)
    echo "[FAIL] unknown command: $cmd"
    exit 2
    ;;
esac
