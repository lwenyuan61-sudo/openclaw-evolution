import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'electron_fallback_scaffold_plan.json');
const STATUS = path.join(STATE, 'desktop_wrapper_electron_fallback_status.json');

function readJson(rel, fallback = {}) {
  try {
    return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8'));
  } catch {
    return fallback;
  }
}

function main() {
  const preflight = readJson('state/desktop_wrapper_packaging_preflight_status.json', {});
  const readiness = readJson('state/desktop_wrapper_tray_readiness_status.json', {});
  const app = readJson('state/app_shell_status.json', {});
  const plan = {
    timestamp: new Date().toISOString(),
    status: 'planned-no-install',
    mode: 'electron-fallback-scaffold-plan',
    whyElectronFallback: preflight.recommendation === 'electron-fallback'
      ? 'Node/npm are available and tray readiness passed, but Rust/Cargo are unavailable for Tauri.'
      : `Current preflight recommendation is ${preflight.recommendation ?? 'unknown'}; keep this as fallback planning only.`,
    intendedDirectoryIfApprovedLater: 'apps/local-desktop-electron-shell',
    sourceWrapper: 'apps/local-desktop-companion',
    packageInstallRequiredLater: true,
    packageInstallPerformedNow: false,
    scaffoldCreatedNow: false,
    persistentProcessStartedNow: false,
    minimalFilesIfApprovedLater: [
      'package.json with electron dev dependency',
      'src/main.js: create BrowserWindow pointed at local dashboard or wrapper server',
      'src/preload.js: expose read-only status bridge first',
      'assets/tray.ico or placeholder icon',
      'README.md with rollback/delete instructions'
    ],
    trayMenuMapping: [
      { item: 'Open Dashboard', mapsTo: 'state/app_shell_dashboard.html or http://127.0.0.1:18790/' },
      { item: 'Show Status', mapsTo: 'state/app_shell_status.json' },
      { item: 'Pause All', mapsTo: 'npm run execute:pause', reversible: true },
      { item: 'Resume All', mapsTo: 'npm run execute:resume', reversible: true },
      { item: 'Export Diagnostics', mapsTo: 'npm run diagnostics', localOnly: true },
      { item: 'Voice Calibration Preview', mapsTo: 'python core/scripts/voice_manual_calibration_runner.py', noRecording: true },
      { item: 'Record 3s Calibration', mapsTo: 'blocked until explicit user click/token', gated: true },
      { item: 'Real Physical Action', mapsTo: 'blocked until per-device allowlist approval', gated: true }
    ],
    verificationBeforeRealScaffold: [
      'Lee explicitly approves dependency install/scaffold step',
      'npm remains available',
      'tray readiness remains 9/9',
      'diagnostics export status is ok',
      'consistency_check is ok',
      'pause/resume still scoped to app_control_state.pauseAll',
      'no microphone/camera/real physical action enabled by default'
    ],
    rollbackIfScaffoldedLater: [
      'delete apps/local-desktop-electron-shell directory',
      'remove any generated package-lock/node_modules inside that directory',
      'do not touch apps/local-desktop-companion or state files unless explicitly requested'
    ],
    currentEvidence: {
      preflightRecommendation: preflight.recommendation ?? null,
      npmAvailable: preflight.prerequisites?.npm?.available ?? null,
      rustcAvailable: preflight.prerequisites?.rustc?.available ?? null,
      cargoAvailable: preflight.prerequisites?.cargo?.available ?? null,
      trayReadiness: readiness.status ?? null,
      trayReadinessPassed: readiness.passedCount ?? null,
      trayReadinessTotal: readiness.totalCount ?? null,
      appShellStatus: app.status ?? null,
      appCardCount: Array.isArray(app.cards) ? app.cards.length : null,
    },
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
  fs.writeFileSync(OUT, `${JSON.stringify(plan, null, 2)}\n`, 'utf8');
  fs.writeFileSync(STATUS, `${JSON.stringify({
    timestamp: plan.timestamp,
    status: plan.status,
    mode: plan.mode,
    recommendation: 'electron-fallback-if-Lee-approves-install-later',
    intendedDirectoryIfApprovedLater: plan.intendedDirectoryIfApprovedLater,
    packageInstallPerformedNow: false,
    scaffoldCreatedNow: false,
    persistentProcessStartedNow: false,
    safety: plan.safety,
  }, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: true, out: OUT, status: STATUS, mode: plan.mode, scaffoldCreatedNow: false, packageInstallPerformedNow: false }, null, 2));
}

main();
