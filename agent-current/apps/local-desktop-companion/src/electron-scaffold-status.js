import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const SHELL = path.join(WORKSPACE, 'apps', 'local-desktop-electron-shell');
const OUT = path.join(STATE, 'desktop_electron_scaffold_status.json');
const SMOKE = path.join(STATE, 'desktop_electron_launch_smoke_status.json');
const MENU_STATUS = path.join(STATE, 'desktop_electron_menu_status.json');
const MENU_ACTION_TEST = path.join(STATE, 'desktop_electron_menu_action_test_status.json');
const TRAY_STATUS = path.join(STATE, 'desktop_electron_tray_status.json');
const PERSISTENT_SMOKE = path.join(STATE, 'desktop_electron_persistent_smoke_status.json');

const REQUIRED = [
  'package.json',
  'README.md',
  'src/main.js',
  'src/preload.js',
  'src/smoke-test.js',
  'src/menu-status.js',
  'src/menu-actions.js',
  'src/menu-action-test.js',
  'src/tray-status.js',
  'src/persistent-smoke.js',
  'assets/tray-ok.png',
  'assets/tray-paused.png',
  'assets/tray-alert.png',
];

function exists(rel) {
  return fs.existsSync(path.join(SHELL, rel));
}

function readJson(abs, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(abs, 'utf8')); }
  catch (error) { return { ...fallback, _error: `${error.name}: ${error.message}` }; }
}

function main() {
  const timestamp = new Date().toISOString();
  const pkg = readJson(path.join(SHELL, 'package.json'));
  const files = REQUIRED.map((rel) => ({ rel, exists: exists(rel) }));
  const nodeModulesExists = fs.existsSync(path.join(SHELL, 'node_modules'));
  const packageLockExists = fs.existsSync(path.join(SHELL, 'package-lock.json'));
  const smoke = readJson(SMOKE, { status: 'missing' });
  const menu = readJson(MENU_STATUS, { status: 'missing' });
  const menuActionTest = readJson(MENU_ACTION_TEST, { status: 'missing' });
  const trayStatus = readJson(TRAY_STATUS, { status: 'missing' });
  const persistentSmoke = readJson(PERSISTENT_SMOKE, { status: 'missing' });
  const missing = files.filter((item) => !item.exists).map((item) => item.rel);
  const canRunNow = missing.length === 0 && nodeModulesExists && Boolean(pkg.dependencies?.electron);
  const doc = {
    timestamp,
    status: missing.length === 0 ? 'scaffold-ready' : 'missing-files',
    mode: 'approved-electron-scaffold-status',
    shellPath: SHELL,
    approvalSource: pkg.local-evolution-agent?.approvalSource ?? 'unknown',
    packageName: pkg.name ?? null,
    electronDependencyDeclared: Boolean(pkg.dependencies?.electron),
    startScriptDeclared: Boolean(pkg.scripts?.start),
    checkScriptDeclared: Boolean(pkg.scripts?.check),
    smokeScriptDeclared: Boolean(pkg.scripts?.smoke),
    menuStatusScriptDeclared: Boolean(pkg.scripts?.['menu:status']),
    files,
    missing,
    dependencyInstallPerformed: nodeModulesExists || packageLockExists,
    nodeModulesExists,
    packageLockExists,
    canRunNow,
    runBlocker: canRunNow ? null : 'electron dependency not installed yet',
    launchSmoke: {
      status: smoke.status,
      durationMs: smoke.durationMs ?? null,
      lastTimestamp: smoke.timestamp ?? null,
      menuItemCount: smoke.menuItemCount ?? null,
    },
    menu: {
      status: menu.status,
      menuItemCount: menu.menuItemCount ?? null,
      wiredInMainProcess: menu.wiredInMainProcess ?? null,
      pauseResumeActionTest: menuActionTest.status ?? 'missing',
      finalPauseAll: menuActionTest.finalPauseAll ?? null,
    },
    tray: {
      status: trayStatus.status,
      trayItemCount: trayStatus.trayItemCount ?? null,
      dynamicStates: trayStatus.dynamicStates ?? [],
      wiredInMainProcess: trayStatus.wiredInMainProcess ?? null,
      persistentSmoke: persistentSmoke.status ?? 'missing',
      persistentSmokeChecks: persistentSmoke.checks?.length ?? null,
    },
    nextStep: canRunNow && smoke.status !== 'passed' ? 'Run npm run smoke for bounded Electron launch validation.' : (canRunNow ? 'Electron shell is dependency-ready and has a bounded smoke validation path.' : 'If Lee wants the packaged shell to run, perform bounded npm install in this scaffold and then run npm run check/start validation.'),
    rollback: 'Delete apps/local-desktop-electron-shell; no Gateway rollback required.',
    safety: {
      scaffoldCreated: true,
      dependencyInstall: nodeModulesExists || packageLockExists,
      persistentProcessStarted: false,
      externalNetworkWrites: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
    },
  };
  fs.writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: doc.status === 'scaffold-ready', out: OUT, status: doc.status, missing, dependencyInstallPerformed: doc.dependencyInstallPerformed }, null, 2));
}

main();
