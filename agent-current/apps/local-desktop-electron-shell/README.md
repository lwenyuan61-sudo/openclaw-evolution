# Local Evolution Agent Desktop Electron Shell

Approved scaffold for a future packaged desktop companion.

Current state:

- Scaffold files exist.
- Dependencies are declared but not installed yet.
- No persistent process is started by this scaffold.
- The shell loads the generated local dashboard: `state/app_shell_dashboard.html`.
- Electron runtime requires a future `npm install` or equivalent dependency resolution before `npm start` can run.

Safety defaults:

- `contextIsolation: true`
- `nodeIntegration: false`
- `sandbox: true`
- External links open through the OS shell and are denied as new Electron windows.

Rollback:

- Remove `apps/local-desktop-electron-shell/` if the scaffold is abandoned.
- No Gateway/service rollback is needed for this scaffold alone.
