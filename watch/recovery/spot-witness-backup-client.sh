#!/usr/bin/env bash
set -euo pipefail

REQUEST="${SSH_ORIGINAL_COMMAND:-status}"

case "$REQUEST" in
    status)
        exec sudo -n \
            /usr/local/sbin/spot-witness-authority \
            status
        ;;

    renew-backup)
        exec sudo -n \
            /usr/local/sbin/spot-witness-authority \
            renew-backup
        ;;

    *)
        echo "permitted commands: status, renew-backup" >&2
        exit 2
        ;;
esac
