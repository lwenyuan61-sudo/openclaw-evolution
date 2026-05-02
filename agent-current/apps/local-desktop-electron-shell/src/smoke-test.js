import fs from 'node:fs';
import path from 'node:path';
import childProcess from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SHELL_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(SHELL_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_electron_launch_smoke_status.json');
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
  fs.rmSync(OUT, { force: true });
  const result = childProcess.spawnSync(ELECTRON, ['.'], {
    cwd: SHELL_ROOT,
    encoding: 'utf8',
    timeout: 25000,
    windowsHide: false,
    env: {
      ...process.env,
      LOCAL_AGENT_ELECTRON_SMOKE_OUT: OUT,
      ELECTRON_ENABLE_LOGGING: '0',
    },
  });
  const smoke = readJson(OUT, { status: 'missing' });
  const passed = result.status === 0 && smoke.status === 'loaded' && smoke.fileExists === true;
  const doc = {
    ...smoke,
    timestamp: new Date().toISOString(),
    status: passed ? 'passed' : 'failed',
    mode: 'bounded-electron-launch-smoke-test',
    electronPath: ELECTRON,
    processStatus: result.status,
    signal: result.signal,
    durationMs: Date.now() - started,
    stdoutTail: String(result.stdout || '').slice(-800),
    stderrTail: String(result.stderr || '').slice(-1200),
    error: result.error ? `${result.error.name}: ${result.error.message}` : null,
    safety: {
      boundedLaunch: true,
      persistentProcessStarted: false,
      externalNetworkWrites: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
    },
  };
  fs.writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: passed, out: OUT, status: doc.status, processStatus: result.status, durationMs: doc.durationMs }, null, 2));
}

main();
