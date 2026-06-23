#!/usr/bin/env bash
set -euo pipefail
cd /home/ogre/spot-stack
npm --prefix starfleet-ui run build >> /home/ogre/spot-stack/watch/logs/ui-build.log 2>&1
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) ui-build complete" >> /home/ogre/spot-stack/watch/logs/ui-build.log
