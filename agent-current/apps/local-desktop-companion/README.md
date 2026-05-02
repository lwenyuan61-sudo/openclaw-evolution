# Local Evolution Agent Desktop Companion Shell

This is the first local desktop-app wrapper skeleton for the agent.

Current mode: **dependency-free Node preview**.

It does not install Electron/Tauri, does not add startup hooks, and does not request microphone/camera/device permissions. It only reads the generated dashboard/status files from `state/`.

## Commands

```powershell
npm run check
npm run status
npm run serve
```

- `status` prints a JSON readiness snapshot and exits.
- `serve` starts a local HTTP preview server on `127.0.0.1:18790`.
- `check` verifies JavaScript syntax.

## Safety

- No external network writes.
- No persistent install.
- No always-on microphone.
- No camera capture.
- No real physical device action.

Future packaging target: Tauri/Electron/native tray once controls and permission gates are stable.
