# Cluster recovery notes - 2026-03-17

## spot-gateway
- Restored working gateway app with cluster routes.
- Known-good file saved at:
  - /opt/spot-gateway/app.py.known-good.20260317-035908

## fleet probes
- fleet-dispatch-probes updated and known-good copy saved at:
  - /usr/local/bin/fleet-dispatch-probes.known-good.20260317-035908

## M-5
- Ollama caused stale GPU handles / phantom 100% GPU util on Quadro M4000.
- Ollama disabled on M-5:
  - sudo systemctl disable --now ollama
- M-5 should run worker services only.

## Verified desired routing
- light -> spot_exec
- coder -> daystrom_exec
- 14b -> spot_exec
- tiny/heartbeat -> m5_watch
