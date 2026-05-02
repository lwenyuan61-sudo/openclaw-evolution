import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import childProcess from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_packaging_preflight_status.json');
const DECISION = path.join(STATE, 'native_packaging_decision_memo.json');

function run(command, args) {
  try {
    const useShell = process.platform === 'win32' && command.toLowerCase().endsWith('.cmd');
    const result = childProcess.spawnSync(command, args, {
      cwd: WORKSPACE,
      encoding: 'utf8',
      windowsHide: true,
      shell: useShell,
      timeout: 15000,
    });
    return {
      ok: result.status === 0,
      status: result.status,
      stdoutTail: (result.stdout ?? '').slice(-2000),
      stderrTail: (result.stderr ?? '').slice(-2000),
      error: result.error ? `${result.error.name}: ${result.error.message}` : null,
    };
  } catch (error) {
    return { ok: false, status: null, stdoutTail: '', stderrTail: '', error: `${error.name}: ${error.message}` };
  }
}

function candidateCommands(command) {
  if (process.platform !== 'win32') return [command];
  const nodeDir = path.dirname(process.execPath);
  const appData = process.env.APPDATA ? path.join(process.env.APPDATA, 'npm') : null;
  const bases = [command];
  if (!command.endsWith('.cmd')) bases.push(`${command}.cmd`);
  if (!command.endsWith('.exe')) bases.push(`${command}.exe`);
  const candidates = [...bases];
  for (const base of bases) {
    candidates.push(path.join(nodeDir, base));
    if (appData) candidates.push(path.join(appData, base));
  }
  return [...new Set(candidates)];
}

function runFirstAvailable(command, args) {
  const attempts = [];
  for (const candidate of candidateCommands(command)) {
    const result = run(candidate, args);
    attempts.push({ candidate, ok: result.ok, status: result.status, error: result.error });
    if (result.ok) return { command: candidate, result, attempts };
  }
  return { command, result: run(command, args), attempts };
}

function commandVersion(command, args = ['--version']) {
  const resolved = runFirstAvailable(command, args);
  const result = resolved.result;
  const text = `${result.stdoutTail || ''}${result.stderrTail ? `\n${result.stderrTail}` : ''}`.trim();
  return {
    command: [resolved.command, ...args].join(' '),
    requestedCommand: [command, ...args].join(' '),
    available: result.ok,
    versionText: text.split(/\r?\n/)[0] ?? '',
    error: result.error,
    status: result.status,
    attempts: resolved.attempts,
  };
}

function readJson(rel, fallback = {}) {
  try {
    return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8'));
  } catch {
    return fallback;
  }
}

function main() {
  const node = commandVersion('node');
  const npm = commandVersion('npm');
  const rustc = commandVersion('rustc');
  const cargo = commandVersion('cargo');
  const readiness = readJson('state/desktop_wrapper_tray_readiness_status.json', {});
  const app = readJson('state/app_shell_status.json', {});
  const packageJson = readJson('apps/local-desktop-companion/package.json', {});
  const tauriReady = Boolean(node.available && npm.available && rustc.available && cargo.available && readiness.status === 'ready-for-native-scaffold-decision');
  const electronReady = Boolean(node.available && npm.available && readiness.status === 'ready-for-native-scaffold-decision');
  const memo = {
    timestamp: new Date().toISOString(),
    status: 'preflight-complete',
    mode: 'packaging-preflight-no-install',
    recommendation: tauriReady ? 'tauri' : electronReady ? 'electron-fallback' : 'stay-dependency-free-preview',
    rationale: tauriReady
      ? 'Tauri prerequisites appear available and all tray readiness gates passed.'
      : electronReady
        ? 'Node/npm are available and readiness gates passed, but Rust/Cargo are not both available for Tauri.'
        : 'Packaging prerequisites or readiness gates are incomplete; keep dependency-free wrapper. Windows .cmd/.exe fallbacks were probed without installing anything.',
    prerequisites: { node, npm, rustc, cargo },
    readiness: {
      status: readiness.status ?? 'missing',
      passedCount: readiness.passedCount ?? null,
      totalCount: readiness.totalCount ?? null,
      failedGateIds: readiness.failedGateIds ?? [],
    },
    currentWrapper: {
      packageName: packageJson.name,
      version: packageJson.version,
      appCardCount: Array.isArray(app.cards) ? app.cards.length : null,
      appStatus: app.status ?? null,
    },
    nextIfApprovedLater: [
      'Scaffold Tauri shell in a separate directory or branch.',
      'Keep dependency-free wrapper as fallback.',
      'Map tray menu to existing safe commands only.',
      'Do not enable microphone, camera, real physical actuation, or external sends by default.',
      'Run diagnostics export and consistency_check after scaffold.'
    ],
    safety: {
      dependencyInstall: false,
      scaffoldCreated: false,
      persistentInstall: false,
      persistentProcessStarted: false,
      externalNetworkWrites: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
    },
  };
  fs.writeFileSync(OUT, `${JSON.stringify(memo, null, 2)}\n`, 'utf8');
  fs.writeFileSync(DECISION, `${JSON.stringify(memo, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: true, out: OUT, decision: DECISION, recommendation: memo.recommendation, tauriReady, electronReady }, null, 2));
}

main();
