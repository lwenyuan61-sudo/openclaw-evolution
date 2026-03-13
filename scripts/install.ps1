$ErrorActionPreference = 'Stop'

Write-Host "[OpenClaw Evolution] Installing dependencies..."

# Check Node.js
try { node -v | Out-Null } catch { Write-Error "Node.js is required. Install Node.js 18+ first."; exit 1 }

# Install OpenClaw CLI if missing
try { openclaw --version | Out-Null } catch { npm i -g openclaw }

# Initialize workspace
openclaw setup

# Create config directory
$cfg = Join-Path $HOME ".openclaw-evolution\config"
New-Item -ItemType Directory -Force -Path $cfg | Out-Null

# Generate unique seed
$seed = [guid]::NewGuid().ToString()

# Evolution mode (no prompts; configurable via env)
$mode = $env:OPENCLAW_EVOLUTION_MODE
if ([string]::IsNullOrWhiteSpace($mode)) { $mode = "conservative" }
if ($mode -ne "fast") { $mode = "conservative" }

# Tick seconds (no prompts; configurable via env)
$tick = $env:OPENCLAW_EVOLUTION_TICK
if ([string]::IsNullOrWhiteSpace($tick)) { $tick = "60" }
if ($tick -ne "120" -and $tick -ne "300") { $tick = "60" }

@"{" | Set-Content (Join-Path $cfg "seed.json")
"  \"seed\": \"$seed\"," | Add-Content (Join-Path $cfg "seed.json")
"  \"note\": \"Each install gets a unique seed.\"" | Add-Content (Join-Path $cfg "seed.json")
"}" | Add-Content (Join-Path $cfg "seed.json")

@"{" | Set-Content (Join-Path $cfg "evolution_mode.json")
"  \"mode\": \"$mode\"," | Add-Content (Join-Path $cfg "evolution_mode.json")
"  \"allowed\": [\"conservative\", \"fast\"]" | Add-Content (Join-Path $cfg "evolution_mode.json")
"}" | Add-Content (Join-Path $cfg "evolution_mode.json")

@"{" | Set-Content (Join-Path $cfg "tick.json")
"  \"tick_seconds\": $tick," | Add-Content (Join-Path $cfg "tick.json")
"  \"allowed\": [60, 120, 300]" | Add-Content (Join-Path $cfg "tick.json")
"}" | Add-Content (Join-Path $cfg "tick.json")

# Start gateway (best effort)
try { openclaw gateway start } catch { }

Write-Host "[OpenClaw Evolution] Done."
Write-Host "Note: This system can be token‑intensive during evolution loops."
Write-Host "Next: run the loop with:"
Write-Host "powershell -ExecutionPolicy Bypass -File .\brainflow\run_daemon.ps1 -IntervalSec $tick -PushMinIntervalSec 600 -Workflow auto"
