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

# Start gateway (best effort)
openclaw gateway start || true

echo "[OpenClaw Evolution] Done."
echo "Next: run the loop with:"
echo "powershell -ExecutionPolicy Bypass -File .\brainflow\run_daemon.ps1 -IntervalSec 60 -PushMinIntervalSec 600 -Workflow auto"
