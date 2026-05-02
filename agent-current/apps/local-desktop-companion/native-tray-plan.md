# Local Evolution Agent Native Tray Packaging Plan

Current status: **contract ready, no install**.

This document defines the first native tray surface without installing Tauri/Electron or starting a persistent tray process.

## Recommended path

1. Keep dependency-free Node preview as the control-plane prototype.
2. Add native tray wrapper only after the following are stable:
   - dashboard status
   - permission controls
   - pause/resume
   - diagnostics export
   - voice calibration preview
3. Prefer **Tauri** for first real packaging because it is lighter than Electron and can host the existing local dashboard.

## First tray menu

- Open Local Evolution Agent Dashboard
- Show Status
- Pause All
- Resume All
- Export Diagnostics
- Voice Calibration Preview
- Record 3s Calibration — gated
- Real Physical Action — blocked until per-device allowlist approval

## Safety

- No dependency install in this planning step.
- No persistent tray process started.
- No microphone/camera access.
- No real physical actuation.
- No external network writes.
