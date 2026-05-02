import fs from 'node:fs';
import path from 'node:path';
import childProcess from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SHELL_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(SHELL_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const CONTROL = path.join(__dirname, 'autostart-control.js');
const STATUS_OUT = path.join(STATE, 'desktop_electron_autostart_rollback_drill_status.json');
const AUDIT_OUT = path.join(STATE, 'desktop_electron_autostart_rollback_drill_audit.jsonl');
const CONTROL_STATUS = path.join(STATE, 'desktop_electron_autostart_control_status.json');

function runControl(mode) {
  const started = Date.now();
  const result = childProcess.spawnSync(process.execPath, [CONTROL, `--${mode}`], {
    cwd: SHELL_ROOT,
    encoding: 'utf8',
    windowsHide: true,
    timeout: 30000,
  });
  const parsed = parseLastJson(result.stdout);
  const statusDoc = readJson(CONTROL_STATUS, {});
  return {
    mode,
    rc: result.status,
    durationMs: Date.now() - started,
    ok: result.status === 0 && parsed?.ok === true,
    parsed,
    statusDoc,
    stdoutTail: (result.stdout ?? '').slice(-1000),
    stderrTail: (result.stderr ?? '').slice(-1000),
    error: result.error ? `${result.error.name}: ${result.error.message}` : null,
  };
}

function parseLastJson(text) {
  const trimmed = String(text ?? '').trim();
  if (!trimmed) return null;
  try { return JSON.parse(trimmed); } catch {}
  const start = trimmed.lastIndexOf('\n{');
  if (start >= 0) {
    try { return JSON.parse(trimmed.slice(start + 1)); } catch {}
  }
  return null;
}

function readJson(file, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return fallback; }
}

function installedFrom(run) {
  return Boolean(run?.statusDoc?.installed ?? run?.parsed?.installed);
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const before = runControl('status');
  const initiallyInstalled = installedFrom(before);
  const steps = [before];
  let uninstall = null;
  let afterUninstall = null;
  let reinstall = null;
  let finalStatus = before;

  if (initiallyInstalled) {
    uninstall = runControl('uninstall');
    steps.push(uninstall);
    afterUninstall = runControl('status');
    steps.push(afterUninstall);
    reinstall = runControl('install');
    steps.push(reinstall);
    finalStatus = runControl('status');
    steps.push(finalStatus);
  }

  const rollbackVerified = initiallyInstalled
    ? uninstall?.ok === true && installedFrom(afterUninstall) === false
    : true;
  const restoreVerified = initiallyInstalled
    ? reinstall?.ok === true && installedFrom(finalStatus) === true
    : installedFrom(finalStatus) === false;

  const doc = {
    timestamp: new Date().toISOString(),
    status: rollbackVerified && restoreVerified ? 'passed' : 'failed',
    mode: 'electron-autostart-rollback-drill',
    initiallyInstalled,
    rollbackVerified,
    restoreVerified,
    finalInstalled: installedFrom(finalStatus),
    finalMechanism: finalStatus.statusDoc?.startupCmd?.installed ? 'startup-folder-cmd' : (finalStatus.statusDoc?.task?.installed ? 'scheduled-task' : 'none'),
    steps: steps.map((step) => ({
      mode: step.mode,
      rc: step.rc,
      ok: step.ok,
      installed: installedFrom(step),
      taskInstalled: Boolean(step.statusDoc?.task?.installed),
      startupCmdInstalled: Boolean(step.statusDoc?.startupCmd?.installed),
      actionAttempted: step.statusDoc?.action?.attempted ?? null,
      reason: step.statusDoc?.action?.reason ?? null,
      durationMs: step.durationMs,
    })),
    safety: {
      reversible: true,
      finalStateRestored: initiallyInstalled ? installedFrom(finalStatus) === true : installedFrom(finalStatus) === false,
      startsPersistentProcessNow: false,
      externalNetworkWrites: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
      mutationScope: 'temporarily removes and restores current-user Electron tray autostart only',
    },
  };
  fs.writeFileSync(STATUS_OUT, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
  fs.appendFileSync(AUDIT_OUT, `${JSON.stringify({ timestamp: doc.timestamp, status: doc.status, initiallyInstalled, rollbackVerified, restoreVerified, finalInstalled: doc.finalInstalled, finalMechanism: doc.finalMechanism })}\n`, 'utf8');
  console.log(JSON.stringify({ ok: doc.status === 'passed', out: STATUS_OUT, status: doc.status, rollbackVerified, restoreVerified, finalInstalled: doc.finalInstalled, finalMechanism: doc.finalMechanism }, null, 2));
}

main();
