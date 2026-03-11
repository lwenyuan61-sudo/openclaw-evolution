@echo off
set BASE=C:\Users\15305\.openclaw\workspace\brainflow
cd /d %BASE%

REM Ensure venv exists
if not exist "%BASE%\.venv\Scripts\python.exe" (
  python -m venv .venv
)

REM NOTE: Dependency installation is intentionally NOT done on every start.
REM Run this manually when needed:
REM   "%BASE%\.venv\Scripts\python.exe" -m pip install -r "%BASE%\requirements.txt"

echo Starting NaoChao BrainFlow supervisor (single-instance + auto-restart)...

REM Start supervisor in the background (no console).
start "NaoChao Supervisor" /min powershell -NoProfile -ExecutionPolicy Bypass -File "%BASE%\supervisor.ps1" -IntervalSec 30 -PushMinIntervalSec 120 -Workflow auto

echo Done. You can close this window.
