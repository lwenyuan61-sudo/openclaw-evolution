import fs from 'node:fs';
import path from 'node:path';
import childProcess from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SHELL_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(SHELL_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_electron_autostart_readiness_status.json');
const TASK_NAME = 'Local Evolution Agent Desktop Companion Tray';
const STARTUP_DIR = process.platform === 'win32' && process.env.APPDATA
  ? path.join(process.env.APPDATA, 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
  : null;
const STARTUP_CMD = STARTUP_DIR ? path.join(STARTUP_DIR, `${TASK_NAME}.cmd`) : null;
const ELECTRON_EXE = process.platform === 'win32'
  ? path.join(SHELL_ROOT, 'node_modules', 'electron', 'dist', 'electron.exe')
  : path.join(SHELL_ROOT, 'node_modules', '.bin', 'electron');
const DASHBOARD = path.join(STATE, 'app_shell_dashboard.html');
const APP_MAIN = path.join(SHELL_ROOT, 'src', 'main.js');

function quote(value) {
  return `"${String(value).replaceAll('"', '\\"')}"`;
}

function queryScheduledTask() {
  if (process.platform !== 'win32') {
    return { supported: false, installed: false, status: 'unsupported-platform', stdoutTail: '', stderrTail: '' };
  }
  const result = childProcess.spawnSync('schtasks.exe', ['/Query', '/TN', TASK_NAME, '/FO', 'LIST'], {
    encoding: 'utf8',
    windowsHide: true,
    timeout: 10000,
  });
  const stdout = result.stdout ?? '';
  const stderr = result.stderr ?? '';
  return {
    supported: true,
    installed: result.status === 0,
    status: result.status === 0 ? 'installed' : 'not-installed',
    rc: result.status,
    error: result.error ? `${result.error.name}: ${result.error.message}` : null,
    stdoutTail: stdout.slice(-1200),
    stderrTail: stderr.slice(-1200),
  };
}

function queryStartupCmd() {
  const exists = Boolean(STARTUP_CMD && fs.existsSync(STARTUP_CMD));
  let contentMatches = false;
  let contentPreview = '';
  if (exists) {
    try {
      contentPreview = fs.readFileSync(STARTUP_CMD, 'utf8').slice(0, 500);
      contentMatches = contentPreview.includes(ELECTRON_EXE) && contentPreview.includes(SHELL_ROOT);
    } catch {}
  }
  return { supported: Boolean(STARTUP_CMD), installed: exists && contentMatches, exists, contentMatches, path: STARTUP_CMD, contentPreview };
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const task = queryScheduledTask();
  const startupCmd = queryStartupCmd();
  const launchTarget = `${quote(ELECTRON_EXE)} ${quote(SHELL_ROOT)}`;
  const installed = task.installed || startupCmd.installed;
  const gates = [
    { id: 'electron-exe-present', passed: fs.existsSync(ELECTRON_EXE), evidence: ELECTRON_EXE },
    { id: 'electron-app-main-present', passed: fs.existsSync(APP_MAIN), evidence: APP_MAIN },
    { id: 'dashboard-present', passed: fs.existsSync(DASHBOARD), evidence: DASHBOARD },
    { id: 'scheduled-task-query-supported', passed: task.supported, evidence: process.platform },
    { id: 'startup-folder-supported', passed: startupCmd.supported, evidence: STARTUP_CMD },
    { id: 'autostart-state-known', passed: ['installed', 'not-installed'].includes(task.status), evidence: task.status },
  ];
  const prerequisitesReady = gates.every((gate) => gate.passed);
  const readyToInstall = prerequisitesReady && !installed;
  const doc = {
    timestamp: new Date().toISOString(),
    status: prerequisitesReady ? 'ready' : 'blocked',
    mode: 'electron-autostart-readiness-preview',
    taskName: TASK_NAME,
    launchTarget,
    scheduledTask: task,
    startupCmd,
    installed,
    gates,
    prerequisitesReady,
    readyToInstall,
    alreadyInstalled: installed,
    installPreview: process.platform === 'win32'
      ? `schtasks /Create /TN ${quote(TASK_NAME)} /TR ${quote(launchTarget)} /SC ONLOGON /RL LIMITED /F`
      : null,
    uninstallPreview: process.platform === 'win32'
      ? `schtasks /Delete /TN ${quote(TASK_NAME)} /F`
      : null,
    safety: {
      previewOnly: true,
      installsScheduledTask: false,
      startsPersistentProcess: false,
      mutatesSystemAutostart: false,
      externalNetworkWrites: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
      rollbackPreviewIncluded: true,
    },
    nextStep: installed
      ? 'Autostart task is installed; next verify rollback path and bounded launch smoke without leaving duplicate processes.'
      : readyToInstall
      ? 'If Lee wants the real tray to persist across logins, execute the installPreview command from a visible main-persona action and verify with a bounded launch smoke plus task query.'
      : 'Resolve blocked gates before installing any autostart task.',
  };
  fs.writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, readyToInstall: doc.readyToInstall, taskInstalled: task.installed }, null, 2));
}

main();
