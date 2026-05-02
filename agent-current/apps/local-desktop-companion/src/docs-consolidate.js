import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT_MD = path.join(APP_ROOT, 'OPERATIONS.md');
const OUT_STATUS = path.join(STATE, 'desktop_wrapper_docs_status.json');

function readJson(rel, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8')); } catch { return fallback; }
}

function bool(value) { return value ? 'true' : 'false'; }

function main() {
  const pkg = readJson('apps/local-desktop-companion/package.json', {});
  const app = readJson('state/app_shell_status.json', {});
  const matrix = readJson('state/desktop_wrapper_test_matrix_status.json', {});
  const preflight = readJson('state/desktop_wrapper_packaging_preflight_status.json', {});
  const readiness = readJson('state/desktop_wrapper_tray_readiness_status.json', {});
  const electron = readJson('state/desktop_wrapper_electron_fallback_status.json', {});
  const scripts = pkg.scripts ?? {};
  const lines = [];
  lines.push('# Local Evolution Agent Desktop Companion Operations');
  lines.push('');
  lines.push('Generated local operations guide for the dependency-free preview wrapper.');
  lines.push('');
  lines.push('## Current state');
  lines.push('');
  lines.push(`- App shell status: ${app.status ?? 'unknown'}`);
  lines.push(`- App shell card count: ${Array.isArray(app.cards) ? app.cards.length : 'n/a'}`);
  lines.push(`- Test matrix: ${matrix.status ?? 'missing'} (${matrix.passedCount ?? 0}/${matrix.totalCount ?? 0})`);
  lines.push(`- Tray readiness: ${readiness.status ?? 'missing'} (${readiness.passedCount ?? 0}/${readiness.totalCount ?? 0})`);
  lines.push(`- Packaging recommendation: ${preflight.recommendation ?? 'unknown'}`);
  lines.push(`- Electron fallback: ${electron.status ?? 'missing'}, install=${bool(electron.packageInstallPerformedNow)}, scaffold=${bool(electron.scaffoldCreatedNow)}`);
  lines.push('');
  lines.push('## Commands');
  lines.push('');
  lines.push('Run from `apps/local-desktop-companion`:');
  lines.push('');
  lines.push('```powershell');
  for (const key of Object.keys(scripts).sort()) lines.push(`npm run ${key}`);
  lines.push('```');
  lines.push('');
  lines.push('## Safety invariants');
  lines.push('');
  lines.push('- No dependency install unless Lee explicitly approves a scaffold/install step.');
  lines.push('- No persistent wrapper/tray process unless explicitly installed later.');
  lines.push('- No always-on microphone. Manual 3s calibration requires explicit token/click flow.');
  lines.push('- No camera capture.');
  lines.push('- No real physical actuation; simulator/allowlist only.');
  lines.push('- External sends remain approval/context gated.');
  lines.push('- Pause/resume may only mutate `state/app_control_state.json` `pauseAll`.');
  lines.push('');
  lines.push('## Packaging decision');
  lines.push('');
  lines.push('- Tauri remains preferred long-term if Rust/Cargo become available.');
  lines.push('- Current preflight recommends Electron fallback because Node/npm are available and Rust/Cargo are unavailable.');
  lines.push('- Electron plan is planning-only: no install/scaffold has been performed.');
  lines.push('');
  lines.push('## Recovery / rollback');
  lines.push('');
  lines.push('- Dependency-free wrapper can be kept as the fallback even if Electron/Tauri is scaffolded later.');
  lines.push('- If a future Electron scaffold is created, rollback is deleting `apps/local-desktop-electron-shell` and its local `node_modules`/lockfile only.');
  lines.push('- Gateway/watchdog rollback is tracked in service health/control state.');
  lines.push('');
  fs.writeFileSync(OUT_MD, `${lines.join('\n')}\n`, 'utf8');
  const status = {
    timestamp: new Date().toISOString(),
    status: 'ok',
    mode: 'operations-docs-consolidated',
    operationsPath: OUT_MD,
    commandCount: Object.keys(scripts).length,
    appShellStatus: app.status ?? null,
    appCardCount: Array.isArray(app.cards) ? app.cards.length : null,
    testMatrixStatus: matrix.status ?? null,
    trayReadinessStatus: readiness.status ?? null,
    packagingRecommendation: preflight.recommendation ?? null,
    safety: {
      dependencyInstall: false,
      scaffoldCreated: false,
      persistentInstall: false,
      persistentProcessStarted: false,
      externalNetworkWrites: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
    }
  };
  fs.writeFileSync(OUT_STATUS, `${JSON.stringify(status, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: true, out: OUT_STATUS, operations: OUT_MD, commandCount: status.commandCount }, null, 2));
}

main();
