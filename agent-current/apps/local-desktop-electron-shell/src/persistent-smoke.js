import fs from 'node:fs';
import path from 'node:path';
import childProcess from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SHELL_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(SHELL_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_electron_persistent_smoke_status.json');
const SMOKE_OUT = path.join(STATE, 'desktop_electron_persistent_launch_inner_status.json');
const ELECTRON = process.platform === 'win32'
  ? path.join(SHELL_ROOT, 'node_modules', 'electron', 'dist', 'electron.exe')
  : path.join(SHELL_ROOT, 'node_modules', '.bin', 'electron');

function readJson(file, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch (error) { return { ...fallback, _error: `${error.name}: ${error.message}` }; }
}

function main() {
  const started = Date.now();
  fs.mkdirSync(STATE, { recursive: true });
  fs.rmSync(SMOKE_OUT, { force: true });
  const child = childProcess.spawn(ELECTRON, ['.'], {
    cwd: SHELL_ROOT,
    windowsHide: false,
    env: { ...process.env, LOCAL_AGENT_ELECTRON_SMOKE_OUT: SMOKE_OUT, LOCAL_AGENT_ELECTRON_PERSISTENT_SMOKE: '1', ELECTRON_ENABLE_LOGGING: '0' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let stdout = '';
  let stderr = '';
  child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
  child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });

  const checks = [];
  let killed = false;
  const interval = setInterval(() => {
    const inner = readJson(SMOKE_OUT, { status: 'missing' });
    checks.push({ tMs: Date.now() - started, childAlive: !child.killed && child.exitCode === null, innerStatus: inner.status, trayItemCount: inner.trayItemCount ?? null, menuItemCount: inner.menuItemCount ?? null });
  }, 1000);

  setTimeout(() => {
    if (child.exitCode === null) {
      killed = child.kill();
    }
  }, 10000);

  child.on('exit', (code, signal) => {
    clearInterval(interval);
    const inner = readJson(SMOKE_OUT, { status: 'missing' });
    const doc = {
      timestamp: new Date().toISOString(),
      status: inner.status === 'loaded' && checks.some((c) => c.childAlive) ? 'passed' : 'failed',
      mode: 'bounded-persistent-electron-tray-lifecycle-smoke',
      durationMs: Date.now() - started,
      processExitCode: code,
      processSignal: signal,
      killRequested: killed,
      inner,
      checks,
      stdoutTail: stdout.slice(-800),
      stderrTail: stderr.slice(-1200),
      safety: {
        boundedLaunch: true,
        persistentProcessStarted: false,
        killedAfterMs: 10000,
        externalNetworkWrites: false,
        microphone: false,
        camera: false,
        realPhysicalActuation: false,
      },
    };
    fs.writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
    console.log(JSON.stringify({ ok: doc.status === 'passed', out: OUT, status: doc.status, durationMs: doc.durationMs, checks: checks.length }, null, 2));
  });
}

main();
