# Local Evolution Agent Desktop Companion Operations

Generated local operations guide for the dependency-free preview wrapper.

## Current state

- App shell status: ok
- App shell card count: 40
- Test matrix: passed (54/54)
- Tray readiness: ready-for-native-scaffold-decision (9/9)
- Packaging recommendation: electron-fallback
- Electron fallback: planned-no-install, install=false, scaffold=false

## Commands

Run from `apps/local-desktop-companion`:

```powershell
npm run approval:gates
npm run audit:view
npm run check
npm run controls
npm run decision:packet
npm run diagnostics
npm run digest:morning
npm run docs:ops
npm run electron:plan
npm run electron:scaffold-status
npm run endpoint
npm run endpoint:self-test
npm run execute:pause
npm run execute:resume
npm run home:routes-test
npm run home:summary
npm run multi-agent:board
npm run multi-agent:handoff-rules
npm run next:connector-queue
npm run packaging:preflight
npm run physical:scenario-matrix
npm run preview:pause
npm run preview:resume
npm run release:readiness
npm run serve
npm run service:recovery-drill
npm run status
npm run test:matrix
npm run tray:contract
npm run tray:readiness
npm run voice:body-readiness
```

## Safety invariants

- No dependency install unless Lee explicitly approves a scaffold/install step.
- No persistent wrapper/tray process unless explicitly installed later.
- No always-on microphone. Manual 3s calibration requires explicit token/click flow.
- No camera capture.
- No real physical actuation; simulator/allowlist only.
- External sends remain approval/context gated.
- Pause/resume may only mutate `state/app_control_state.json` `pauseAll`.

## Packaging decision

- Tauri remains preferred long-term if Rust/Cargo become available.
- Current preflight recommends Electron fallback because Node/npm are available and Rust/Cargo are unavailable.
- Electron plan is planning-only: no install/scaffold has been performed.

## Recovery / rollback

- Dependency-free wrapper can be kept as the fallback even if Electron/Tauri is scaffolded later.
- If a future Electron scaffold is created, rollback is deleting `apps/local-desktop-electron-shell` and its local `node_modules`/lockfile only.
- Gateway/watchdog rollback is tracked in service health/control state.

