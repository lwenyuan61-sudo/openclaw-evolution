import fs from 'node:fs';
import path from 'node:path';
import childProcess from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_voice_vad_measurement_dry_run_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_voice_vad_measurement_dry_run_audit.jsonl');

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

function probeAudioModules() {
  const code = String.raw`
import json, importlib.util
mods = {name: importlib.util.find_spec(name) is not None for name in ['sounddevice', 'numpy', 'faster_whisper', 'webrtcvad', 'pvporcupine', 'openwakeword']}
summary = {'modules': mods}
try:
    import sounddevice as sd
    summary['defaultDevice'] = list(sd.default.device) if hasattr(sd.default, 'device') else None
    devices = sd.query_devices()
    summary['deviceCount'] = len(devices)
    inputs = []
    for idx, dev in enumerate(devices):
        if int(dev.get('max_input_channels', 0)) > 0:
            inputs.append({'index': idx, 'name': str(dev.get('name')), 'maxInputChannels': int(dev.get('max_input_channels', 0)), 'defaultSamplerate': float(dev.get('default_samplerate', 0.0))})
    summary['inputCount'] = len(inputs)
    summary['recommendedInput'] = inputs[0] if inputs else None
except Exception as exc:
    summary['audioProbeError'] = type(exc).__name__ + ': ' + str(exc)
print(json.dumps(summary, ensure_ascii=False))
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
  const appControl = readJson('state/app_control_state.json', {});
  const boundary = readJson('state/desktop_wrapper_voice_wake_boundary_status.json', {});
  const voiceIndicator = readJson('state/voice_listening_indicator.json', {});
  const calibration = readJson('state/voice_calibration_status.json', {});
  const moduleProbe = probeAudioModules();
  const modules = moduleProbe.parsed?.modules ?? {};
  const resourceOk = resource.resourcePressure?.level === 'ok';
  const pauseAll = Boolean(appControl.pauseAll);
  const indicatorIdle = voiceIndicator.state === 'idle' && voiceIndicator.recordingNow === false && voiceIndicator.alwaysOnMicEnabled === false;
  const hasSoundDevice = modules.sounddevice === true;
  const hasNumpy = modules.numpy === true;
  const hasWhisper = modules.faster_whisper === true;
  const hasDedicatedVad = modules.webrtcvad === true || modules.pvporcupine === true || modules.openwakeword === true;
  const gates = [
    { id: 'resource-ok', status: resourceOk ? 'ready' : 'blocked', evidence: resource.resourcePressure?.level ?? 'unknown' },
    { id: 'pause-all-off', status: !pauseAll ? 'ready' : 'blocked', evidence: pauseAll },
    { id: 'voice-boundary-ready', status: boundary.status === 'ready' ? 'ready' : 'blocked', evidence: boundary.status ?? 'missing' },
    { id: 'listening-indicator-idle', status: indicatorIdle ? 'ready' : 'blocked', evidence: { state: voiceIndicator.state, recordingNow: voiceIndicator.recordingNow, alwaysOnMicEnabled: voiceIndicator.alwaysOnMicEnabled } },
    { id: 'audio-module-probe', status: moduleProbe.rc === 0 && hasSoundDevice && hasNumpy ? 'ready' : 'warn', evidence: { rc: moduleProbe.rc, hasSoundDevice, hasNumpy, error: moduleProbe.error ?? moduleProbe.parsed?.audioProbeError ?? null } },
    { id: 'cpu-transcription-fallback', status: hasWhisper ? 'ready' : 'warn', evidence: { hasWhisper } },
    { id: 'dedicated-vad-or-wake-engine', status: hasDedicatedVad ? 'ready' : 'warn', evidence: { webrtcvad: modules.webrtcvad === true, pvporcupine: modules.pvporcupine === true, openwakeword: modules.openwakeword === true, fallback: 'energy + CPU whisper phrase confirmation only' } },
  ];
  const blocked = gates.filter((gate) => gate.status === 'blocked');
  const warnings = gates.filter((gate) => gate.status === 'warn');
  const dryRunPlan = {
    defaultMode: 'measurement-dry-run-no-recording',
    windowMs: 30,
    hopMs: 15,
    sampleRate: calibration.deviceEnumeration?.recommendedInput?.defaultSamplerate ?? 44100,
    recommendedInput: calibration.deviceEnumeration?.recommendedInput ?? boundary.recommendedInput ?? moduleProbe.parsed?.recommendedInput ?? null,
    boundedMeasurementWhenEnabled: {
      maxDurationSeconds: 20,
      recordRawAudio: false,
      storeRawAudio: false,
      storeRollingBuffers: false,
      storeMetricsOnly: ['windowCount', 'rmsDistribution', 'peakDistribution', 'candidateWakeCount', 'falsePositiveEstimate'],
      stopConditions: ['pauseAll=true', 'indicator failure', 'resourcePressure!=ok', 'duration limit', 'app stop button'],
    },
    thresholdBootstrap: {
      method: 'noise-floor bootstrap from short local windows, then wake phrase confirmation by CPU whisper only on candidate windows',
      initialRmsMultiplier: 3.0,
      minConsecutiveActiveWindows: 4,
      candidateCooldownMs: 2000,
    },
  };
  const doc = {
    timestamp,
    status: blocked.length === 0 ? 'ready' : 'blocked',
    mode: 'voice-vad-measurement-dry-run-no-recording',
    moduleProbe: moduleProbe.parsed ?? { error: moduleProbe.error, stderrTail: moduleProbe.stderrTail },
    dryRunPlan,
    gates,
    blocked: blocked.map((gate) => gate.id),
    warnings: warnings.map((gate) => gate.id),
    safety: {
      dryRunOnly: true,
      startsMicrophone: false,
      recordsAudio: false,
      startsPersistentProcess: false,
      externalNetworkWrites: false,
      storesRawAudio: false,
      paidApi: false,
      gpuHeavy: false,
      realPhysicalActuation: false,
    },
  };
  writeJson(OUT, doc);
  appendAudit({ timestamp, status: doc.status, warnings: doc.warnings, blocked: doc.blocked, startsMicrophone: false, recordsAudio: false });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, dryRunOnly: true, startsMicrophone: false, recordsAudio: false, warningCount: doc.warnings.length, blocked: doc.blocked }, null, 2));
}

main();
