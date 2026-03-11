# Start NaoChao (BrainFlow) + ensure OpenClaw gateway is running (manual)
# Usage: Right-click -> Run with PowerShell

$ErrorActionPreference = "Stop"

$base = "C:\Users\15305\.openclaw\workspace\brainflow"
Set-Location $base

# relax execution policy for this process
try { Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force } catch {}

# Ensure venv exists
if (!(Test-Path "$base\.venv\Scripts\python.exe")) {
  python -m venv .venv
}

# Install deps if missing (best-effort)
& "$base\.venv\Scripts\python.exe" -m pip install -r "$base\requirements.txt" | Out-Host

Write-Host "Starting BrainFlow daemon (NaoChao)..." -ForegroundColor Cyan
Write-Host "Tip: stop with Ctrl+C" -ForegroundColor DarkGray

# Continuous thinking; no push rate limit (you will tell it)
& "$base\.venv\Scripts\python.exe" "$base\daemon.py" --interval 0 --workflow auto --push-min-interval 0
