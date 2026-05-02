import fs from 'node:fs';
import path from 'node:path';
import childProcess from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_voice_wake_engine_readiness_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_voice_wake_engine_readiness_audit.jsonl');

function readJson(rel, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8')); }
  catch (error) { return { ...fallback, _error: `${error.name}: ${error.message}` }; }
}

function writeJson(file, doc) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
}

function appendAudit(event) {
  fs.mkdirSync(path.dirname(AUDIT), { recursive: true });
  fs.appendFileSync(AUDIT, `${JSON.stringify(event)}\n`, 'utf8');
}

function parseJson(text) {
  const trimmed = String(text ?? '').trim();
  if (!trimmed) return null;
  try { return JSON.parse(trimmed); } catch {}
  const start = trimmed.lastIndexOf('\n{');
  if (start >= 0) {
    try { return JSON.parse(trimmed.slice(start + 1)); } catch {}
  }
  return null;
}

function probePythonModules() {
  const code = String.raw`
import json, importlib.util, sys
names = ['sounddevice', 'numpy', 'faster_whisper', 'webrtcvad', 'pvporcupine', 'openwakeword']
mods = {name: importlib.util.find_spec(name) is not None for name in names}
print(json.dumps({'ok': True, 'python': sys.version.split()[0], 'modules': mods}, ensure_ascii=False))
`;
  const result = childProcess.spawnSync('python', ['-c', code], {
    cwd: WORKSPACE,
    encoding: 'utf8',
    windowsHide: true,
    timeout: 10000,
  });
  return {
    rc: result.status,
    parsed: parseJson(result.stdout),
    stdoutTail: (result.stdout ?? '').slice(-1200),
    stderrTail: (result.stderr ?? '').slice(-1200),
    error: result.error ? `${result.error.name}: ${result.error.message}` : null,
  };
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const resource = readJson('core/resource-state.json', {});
  const spokenBoundary = readJson('state/desktop_wrapper_voice_spoken_wake_boundary_status.json', {});
  const baseline = readJson('state/desktop_wrapper_voice_vad_baseline_evaluator_status.json', {});
  const voicePlan = readJson('state/voice_wake_plan.json', {});
  const moduleProbe = probePythonModules();
  const modules = moduleProbe.parsed?.modules ?? {};
  const resourceOk = resource.resourcePressure?.level === 'ok';
  const baselineOk = baseline.status === 'ready' && (baseline.warnings?.length ?? 0) === 0;
  const boundaryOk = spokenBoundary.status === 'ready';
  const currentFallbackReady = modules.sounddevice === true && modules.numpy === true && modules.faster_whisper === true && baselineOk && boundaryOk;
  const dedicated = {
    webrtcvad: modules.webrtcvad === true,
    pvporcupine: modules.pvporcupine === true,
    openwakeword: modules.openwakeword === true,
  };
  const anyDedicatedReady = dedicated.webrtcvad || dedicated.pvporcupine || dedicated.openwakeword;
  const candidates = [
    {
      id: 'current-energy-plus-whisper-fallback',
      status: currentFallbackReady ? 'ready' : 'blocked',
      priority: 1,
      installRequired: false,
      externalAccountRequired: false,
      gpuRequired: false,
      paidApi: false,
      quality: 'baseline prototype; not phone-grade wake word',
      reason: 'Already available: sounddevice/numpy/faster_whisper with measured quiet baseline and spoken wake boundary.',
      nextStep: 'Implement bounded spoken wake calibration runner before any continuous listener.',
    },
    {
      id: 'webrtcvad-local-vad',
      status: dedicated.webrtcvad ? 'ready' : 'install-candidate',
      priority: 2,
      installRequired: !dedicated.webrtcvad,
      externalAccountRequired: false,
      gpuRequired: false,
      paidApi: false,
      quality: 'lightweight local VAD; still needs phrase confirmation backend',
      reason: dedicated.webrtcvad ? 'Python module present.' : 'Missing but likely the smallest local CPU dependency for better VAD gating.',
      proposedCommand: 'python -m pip install webrtcvad',
      reversibleCheck: 'python -c "import webrtcvad; print(webrtcvad.__version__ if hasattr(webrtcvad, \'__version__\') else \'ok\')"',
    },
    {
      id: 'openwakeword-local-wake-word',
      status: dedicated.openwakeword ? 'ready' : 'later-candidate',
      priority: 3,
      installRequired: !dedicated.openwakeword,
      externalAccountRequired: false,
      gpuRequired: false,
      paidApi: false,
      quality: 'closer to real wake-word engine but heavier dependency/model path',
      reason: dedicated.openwakeword ? 'Python module present.' : 'Missing; evaluate only after lightweight VAD path because dependencies/models may be heavier.',
    },
    {
      id: 'pvporcupine-commercial-wake-word',
      status: dedicated.pvporcupine ? 'ready' : 'defer',
      priority: 4,
      installRequired: !dedicated.pvporcupine,
      externalAccountRequired: true,
      gpuRequired: false,
      paidApi: true,
      quality: 'strong wake-word engine but account/key/licensing likely required',
      reason: dedicated.pvporcupine ? 'Python module present.' : 'Defer to avoid paid/external-key path during local-first autonomous wake.',
    },
  ];
  const recommended = candidates.find((item) => item.status === 'ready') ?? candidates[0];
  const gates = [
    { id: 'resource-ok', status: resourceOk ? 'ready' : 'blocked', evidence: resource.resourcePressure?.level ?? 'unknown' },
    { id: 'python-module-probe', status: moduleProbe.rc === 0 && moduleProbe.parsed?.ok === true ? 'ready' : 'blocked', evidence: { rc: moduleProbe.rc, error: moduleProbe.error ?? moduleProbe.stderrTail } },
    { id: 'quiet-baseline-ready', status: baselineOk ? 'ready' : 'blocked', evidence: { status: baseline.status, warnings: baseline.warnings ?? [] } },
    { id: 'spoken-wake-boundary-ready', status: boundaryOk ? 'ready' : 'blocked', evidence: spokenBoundary.status ?? 'missing' },
    { id: 'dedicated-engine-present', status: anyDedicatedReady ? 'ready' : 'warn', evidence: dedicated },
  ];
  const blocked = gates.filter((gate) => gate.status === 'blocked');
  const warnings = gates.filter((gate) => gate.status === 'warn');
  const doc = {
    timestamp,
    status: blocked.length === 0 ? 'ready' : 'blocked',
    mode: 'voice-wake-engine-readiness-no-install-no-recording',
    moduleProbe: moduleProbe.parsed ?? { error: moduleProbe.error, stderrTail: moduleProbe.stderrTail },
    currentPath: {
      ready: currentFallbackReady,
      backend: 'energy/noise-floor VAD + local faster_whisper phrase confirmation',
      approvedByLee: voicePlan.approvedByLee === true,
      startsListenerNow: false,
      qualityLimit: 'not phone-grade; suitable for bounded calibration and local prototype only',
    },
    candidates,
    recommendedNext: recommended,
    installDecision: {
      installPerformedNow: false,
      recommendedIfInstallingLater: dedicated.webrtcvad ? null : 'webrtcvad-local-vad',
      rationale: 'Prefer smallest local CPU-only VAD dependency before heavier openwakeword or paid/keyed pvporcupine paths.',
    },
    gates,
    blocked: blocked.map((gate) => gate.id),
    warnings: warnings.map((gate) => gate.id),
    safety: {
      readinessOnly: true,
      dependencyInstall: false,
      startsMicrophone: false,
      recordsAudio: false,
      storesRawAudio: false,
      startsPersistentProcess: false,
      externalNetworkWrites: false,
      paidApi: false,
      gpuHeavy: false,
      realPhysicalActuation: false,
    },
  };
  writeJson(OUT, doc);
  appendAudit({ timestamp, status: doc.status, warnings: doc.warnings, blocked: doc.blocked, recommendedNext: recommended.id, installPerformedNow: false });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, readinessOnly: true, startsMicrophone: false, recordsAudio: false, installPerformedNow: false, recommendedNext: recommended.id, warningCount: doc.warnings.length }, null, 2));
}

main();
