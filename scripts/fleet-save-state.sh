#!/usr/bin/env bash
set -euo pipefail

TS="$(date +%F_%H%M%S)"
OUT="$HOME/spot-AI/fleet-docs/snapshots/$TS"

echo "[*] Saving fleet state to $OUT"
mkdir -p "$OUT"/{systemd,configs,status,apps,meta}

# --- Copy configs ---
cp -r "$HOME/spot-AI/configs" "$OUT/" 2>/dev/null || true

# --- Copy scripts ---
cp -r "$HOME/spot-AI/scripts" "$OUT/" 2>/dev/null || true

# --- Copy Spot node app ---
cp -r "$HOME/spot-AI/nodes/spot" "$OUT/apps/" 2>/dev/null || true

# --- Systemd units ---
sudo cp /etc/systemd/system/spot-gateway.service "$OUT/systemd/" 2>/dev/null || true
sudo cp /etc/systemd/system/spot-worker.service "$OUT/systemd/" 2>/dev/null || true
sudo cp /etc/systemd/system/spot-worker0.service "$OUT/systemd/" 2>/dev/null || true

# --- Service states ---
systemctl status spot-gateway --no-pager > "$OUT/status/spot-gateway.status.txt"
systemctl status spot-worker --no-pager > "$OUT/status/spot-worker.status.txt"
systemctl status spot-worker0 --no-pager > "$OUT/status/spot-worker0.status.txt"

# --- Journals (recent) ---
journalctl -u spot-gateway -n 200 --no-pager > "$OUT/status/spot-gateway.journal.txt"
journalctl -u spot-worker -n 200 --no-pager > "$OUT/status/spot-worker.journal.txt"
journalctl -u spot-worker0 -n 200 --no-pager > "$OUT/status/spot-worker0.journal.txt"

# --- Fleet + health ---
fleet > "$OUT/status/fleet.txt" || true
curl -s http://127.0.0.1:8798/health > "$OUT/status/gateway-health.json" 2>/dev/null || true
curl -s http://127.0.0.1:8798/cluster/gpu_status > "$OUT/status/gpu-status.json" 2>/dev/null || true

# --- Ollama models ---
curl -s http://127.0.0.1:11434/api/tags > "$OUT/status/ollama-tags.json" 2>/dev/null || true

# --- Package baseline (manual installs only) ---
apt-mark showmanual | sort > "$OUT/meta/packages-manual.txt" || true

# --- Git state ---
cd "$HOME/spot-AI"
git rev-parse HEAD > "$OUT/meta/git-commit.txt"
git status > "$OUT/meta/git-status.txt"

# --- Archive ---
tar -czf "$HOME/spot-AI/fleet-docs/snapshots/$TS.tar.gz" -C "$OUT" .

echo "[OK] Snapshot saved:"
echo "    $OUT"
echo "    $HOME/spot-AI/fleet-docs/snapshots/$TS.tar.gz"
