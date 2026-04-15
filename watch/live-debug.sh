#!/bin/bash

echo "=== SPOT LIVE DEBUG ==="

# Scheduler logs
echo "[1] spot-core logs"
docker compose -f /home/ogre/spot-stack/spot-core/docker-compose.yml logs -f spot-core &
PID1=$!

# Decision history
echo "[2] decision history"
tail -f /mnt/collective/fleet/spot-core/shared_memory/decision-history.jsonl | jq -c '{worker, model, role, status}' &
PID2=$!

# Exec history
echo "[3] exec history"
tail -f /mnt/collective/fleet/spot-core/shared_memory/exec-history.jsonl | jq -c '{worker, duration, status}' &
PID3=$!

# Wait
trap "kill $PID1 $PID2 $PID3" EXIT
wait
