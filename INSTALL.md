# Installation Guide (One‑click + Manual)

This project is an **advanced evolution of OpenClaw** (independent, not endorsed by OpenClaw). It is designed to be **human‑centered, verifiable, and easy to run**.

---

## 0) Prerequisites
- **Node.js 18+**
- **Git**
- Windows / macOS / Linux

---

## 1) One‑click install (recommended)
> Choose the script for your OS.

### Windows (PowerShell)
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
irm https://raw.githubusercontent.com/lwenyuan61-sudo/openclaw-evolution/main/scripts/install.ps1 | iex
```

### macOS / Linux (bash)
```bash
curl -fsSL https://raw.githubusercontent.com/lwenyuan61-sudo/openclaw-evolution/main/scripts/install.sh | bash
```

---

## 2) Manual install (if you prefer control)
```bash
# 1) Install OpenClaw CLI
yarn global add openclaw
# or
npm i -g openclaw

# 2) Initialize workspace
openclaw setup

# 3) Start gateway
openclaw gateway start
```

---

## 3) Start the evolution loop
```powershell
# from your OpenClaw workspace
powershell -ExecutionPolicy Bypass -File .\brainflow\run_daemon.ps1 -IntervalSec 60 -PushMinIntervalSec 600 -Workflow auto
```

---

## 4) Verify it works (acceptance check)
- You should see new trace logs under `brainflow/runs/`
- `scorecard_latest.json` should update after each cycle
- The system should self‑report when a high‑value result or failure occurs

---

## Notes
- This repository contains **no personal data**.
- All behavior is auditable via logs and scorecards.

If you hit issues, open an Issue with your logs.
