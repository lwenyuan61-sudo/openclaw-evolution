$ErrorActionPreference = 'Stop'

Write-Host "[OpenClaw Evolution] Installing dependencies..."

# Check Node.js
try { node -v | Out-Null } catch { Write-Error "Node.js is required. Install Node.js 18+ first."; exit 1 }

# Install OpenClaw CLI if missing
try { openclaw --version | Out-Null } catch { npm i -g openclaw }

# Initialize workspace
openclaw setup

# Start gateway (best effort)
try { openclaw gateway start } catch { }

Write-Host "[OpenClaw Evolution] Done."
Write-Host "Next: run the loop with:"
Write-Host "powershell -ExecutionPolicy Bypass -File .\brainflow\run_daemon.ps1 -IntervalSec 60 -PushMinIntervalSec 600 -Workflow auto"
