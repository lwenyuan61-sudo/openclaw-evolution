#!/usr/bin/env bash
set -euo pipefail

echo "[OpenClaw Evolution] Installing dependencies..."

# Check Node.js
if ! command -v node >/dev/null 2>&1; then
  echo "Node.js 18+ is required. Please install Node.js first." >&2
  exit 1
fi

# Install OpenClaw CLI if missing
if ! command -v openclaw >/dev/null 2>&1; then
  npm i -g openclaw
fi

# Initialize workspace
openclaw setup

# Config directory
CFG_DIR="$HOME/.openclaw-evolution/config"
mkdir -p "$CFG_DIR"

# Unique seed
SEED="$(date +%s)-$RANDOM"

# Mode (no prompts; configurable via env)
MODE="${OPENCLAW_EVOLUTION_MODE:-conservative}"
if [ "$MODE" != "fast" ]; then MODE="conservative"; fi

# Tick (no prompts; configurable via env)
TICK="${OPENCLAW_EVOLUTION_TICK:-60}"
if [ "$TICK" != "120" ] && [ "$TICK" != "300" ]; then TICK="60"; fi

cat > "$CFG_DIR/seed.json" <<EOF
{ "seed": "$SEED", "note": "Each install gets a unique seed." }
EOF

cat > "$CFG_DIR/evolution_mode.json" <<EOF
{ "mode": "$MODE", "allowed": ["conservative", "fast"] }
EOF

cat > "$CFG_DIR/tick.json" <<EOF
{ "tick_seconds": $TICK, "allowed": [60, 120, 300] }
EOF

# Start gateway (best effort)
openclaw gateway start || true

echo "[OpenClaw Evolution] Done."
echo "Note: This system can be token‑intensive during evolution loops."
echo "Next: run the loop with:"
echo "powershell -ExecutionPolicy Bypass -File .\\brainflow\\run_daemon.ps1 -IntervalSec $TICK -PushMinIntervalSec 600 -Workflow auto"
