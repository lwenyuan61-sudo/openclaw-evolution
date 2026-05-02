import fs from 'node:fs';
import path from 'node:path';
import childProcess from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const INDICATOR = path.join(STATE, 'voice_listening_indicator.json');
const OUT = path.join(STATE, 'desktop_wrapper_voice_vad_measurement_runner_status.json');
const METRICS = path.join(STATE, 'voice_vad_measurement_metrics.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_voice_vad_measurement_runner_audit.jsonl');
const CLEARANCE_VERIFIER = path.join(WORKSPACE, 'apps', 'local-desktop-companion', 'src', 'resource-action-clearance-verifier.js');

function readJson(relOrAbs, fallback = {}) {
  const file = path.isAbsolute(relOrAbs) ? relOrAbs : path.join(WORKSPACE, relOrAbs);
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); }
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

function indicatorDoc(state, reason, extra = {}) {
  return {
    timestamp: new Date().toISOString(),
    state,
    reason,
    recordingNow: state !== 'idle',
    alwaysOnMicEnabled: false,
    storesRawAudio: false,
    visibleIndicatorRequiredBeforeCapture: true,
    ...extra,
  };
}

function selectedMode() {
  return new Set(process.argv.slice(2)).has('--measure') ? 'measure' : 'status';
}

function runMeasurement({ seconds, deviceIndex, sampleRate }) {
  const code = String.raw`
import json, sys, time
try:
    import sounddevice as sd
    import numpy as np
except Exception as exc:
    print(json.dumps({'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}))
    sys.exit(2)
seconds = float(sys.argv[1])
device = None if sys.argv[2] == 'auto' else int(sys.argv[2])
sample_rate = int(float(sys.argv[3]))
window_ms = 30
hop_ms = 15
channels = 1
started = time.time()
try:
    data = sd.rec(int(seconds * sample_rate), samplerate=sample_rate, channels=channels, dtype='float32', device=device)
    sd.wait()
except Exception as exc:
    print(json.dumps({'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}))
    sys.exit(3)
x = data.reshape(-1).astype('float64')
if x.size == 0:
    print(json.dumps({'ok': False, 'error': 'empty audio buffer'}))
    sys.exit(4)
win = max(1, int(sample_rate * window_ms / 1000.0))
hop = max(1, int(sample_rate * hop_ms / 1000.0))
rms = []
peaks = []
for start in range(0, max(1, x.size - win + 1), hop):
    chunk = x[start:start+win]
    if chunk.size == 0:
        continue
    rms.append(float(np.sqrt(np.mean(np.square(chunk)))))
    peaks.append(float(np.max(np.abs(chunk))))
r = np.array(rms or [0.0], dtype='float64')
p = np.array(peaks or [0.0], dtype='float64')
noise_floor = float(np.percentile(r, 20))
threshold = max(noise_floor * 3.0, 0.01)
active = r > threshold
candidate_count = 0
run = 0
for flag in active:
    if flag:
        run += 1
        if run == 4:
            candidate_count += 1
    else:
        run = 0
metrics = {
    'ok': True,
    'durationSeconds': round(float(seconds), 3),
    'sampleRate': sample_rate,
    'deviceIndex': None if device is None else device,
    'windowMs': window_ms,
    'hopMs': hop_ms,
    'sampleCount': int(x.size),
    'windowCount': int(len(r)),
    'rms': {
        'min': round(float(np.min(r)), 6),
        'p20': round(float(np.percentile(r, 20)), 6),
        'median': round(float(np.median(r)), 6),
        'p95': round(float(np.percentile(r, 95)), 6),
        'max': round(float(np.max(r)), 6),
    },
    'peak': {
        'min': round(float(np.min(p)), 6),
        'median': round(float(np.median(p)), 6),
        'p95': round(float(np.percentile(p, 95)), 6),
        'max': round(float(np.max(p)), 6),
    },
    'thresholdBootstrap': {
        'noiseFloorRmsP20': round(noise_floor, 6),
        'initialThresholdRms': round(threshold, 6),
        'initialRmsMultiplier': 3.0,
        'minConsecutiveActiveWindows': 4,
    },
    'candidateWakeCount': int(candidate_count),
    'falsePositiveEstimate': 'needs repeated quiet-baseline runs; single bounded run only',
    'rawAudioRetained': False,
    'transcriptGenerated': False,
    'elapsedMs': int((time.time() - started) * 1000),
}
print(json.dumps(metrics, ensure_ascii=False))
`;
  const result = childProcess.spawnSync('python', ['-c', code, String(seconds), deviceIndex == null ? 'auto' : String(deviceIndex), String(sampleRate)], {
    cwd: WORKSPACE,
    encoding: 'utf8',
    windowsHide: true,
    timeout: Math.max(10000, (seconds + 5) * 1000),
  });
  return {
    rc: result.status,
    parsed: parseJson(result.stdout),
    stdoutTail: (result.stdout ?? '').slice(-1600),
    stderrTail: (result.stderr ?? '').slice(-1600),
    error: result.error ? `${result.error.name}: ${result.error.message}` : null,
  };
}

function runClearance(actionClass) {
  const started = Date.now();
  const result = childProcess.spawnSync(process.execPath, [CLEARANCE_VERIFIER, '--class', actionClass], {
    cwd: WORKSPACE,
    encoding: 'utf8',
    windowsHide: true,
    timeout: 10000,
  });
  return {
    rc: result.status,
    durationMs: Date.now() - started,
    parsed: parseJson(result.stdout),
    stdoutTail: (result.stdout ?? '').slice(-1000),
    stderrTail: (result.stderr ?? '').slice(-1000),
    error: result.error ? `${result.error.name}: ${result.error.message}` : null,
  };
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const mode = selectedMode();
  const timestamp = new Date().toISOString();
  const clearance = mode === 'measure' ? runClearance('microphone-recording') : null;
  const resource = readJson('core/resource-state.json', {});
  const appControl = readJson('state/app_control_state.json', {});
  const dryRun = readJson('state/desktop_wrapper_voice_vad_measurement_dry_run_status.json', {});
  const voiceIndicator = readJson(INDICATOR, indicatorDoc('idle', 'indicator initialized by voice VAD runner'));
  const plan = dryRun.dryRunPlan ?? {};
  const recommended = plan.recommendedInput ?? {};
  const resourceOk = resource.resourcePressure?.level === 'ok';
  const pauseAll = Boolean(appControl.pauseAll);
  const indicatorIdle = voiceIndicator.state === 'idle' && voiceIndicator.recordingNow === false && voiceIndicator.alwaysOnMicEnabled === false;
  const gates = [
    { id: 'resource-clearance-microphone-recording', status: mode !== 'measure' ? 'ready' : clearance?.parsed?.allowedNow === true ? 'ready' : 'blocked', evidence: mode !== 'measure' ? 'not-measure-mode' : clearance?.parsed?.requestedClass ?? 'missing-clearance' },
    { id: 'resource-ok', status: resourceOk ? 'ready' : 'blocked', evidence: resource.resourcePressure?.level ?? 'unknown' },
    { id: 'pause-all-off', status: !pauseAll ? 'ready' : 'blocked', evidence: pauseAll },
    { id: 'vad-dry-run-ready', status: dryRun.status === 'ready' ? 'ready' : 'blocked', evidence: dryRun.status ?? 'missing' },
    { id: 'listening-indicator-idle', status: indicatorIdle ? 'ready' : 'blocked', evidence: { state: voiceIndicator.state, recordingNow: voiceIndicator.recordingNow, alwaysOnMicEnabled: voiceIndicator.alwaysOnMicEnabled } },
  ];
  const blocked = gates.filter((gate) => gate.status === 'blocked');
  const seconds = 5;
  const sampleRate = Number(recommended.defaultSamplerate ?? plan.sampleRate ?? 44100);
  const deviceIndex = Number.isFinite(Number(recommended.index)) ? Number(recommended.index) : null;
  let measurement = null;
  let indicatorRestored = false;
  let status = blocked.length === 0 ? 'ready' : 'blocked';
  try {
    if (mode === 'measure' && blocked.length === 0) {
      writeJson(INDICATOR, indicatorDoc('vad-measuring', 'bounded VAD metrics measurement in progress; raw audio is not written to disk', { durationSeconds: seconds, deviceIndex }));
      appendAudit({ timestamp: new Date().toISOString(), event: 'measurement-start', seconds, deviceIndex, storesRawAudio: false });
      measurement = runMeasurement({ seconds, deviceIndex, sampleRate });
      if (measurement.rc === 0 && measurement.parsed?.ok === true) {
        const metricsDoc = {
          timestamp: new Date().toISOString(),
          source: 'voice-vad-measurement-runner',
          deviceIndex,
          deviceName: recommended.name ?? null,
          metrics: measurement.parsed,
          retention: {
            rawAudioWrittenToDisk: false,
            rawAudioRetained: false,
            transcriptGenerated: false,
            networkUpload: false,
            paidApi: false,
          },
        };
        writeJson(METRICS, metricsDoc);
        status = 'measured-metrics-only';
      } else {
        status = 'failed-measurement';
      }
    }
  } finally {
    writeJson(INDICATOR, indicatorDoc('idle', 'bounded VAD measurement complete or inactive; microphone idle', { lastMeasurementMode: mode }));
    indicatorRestored = true;
  }

  const doc = {
    timestamp: new Date().toISOString(),
    status,
    mode: `voice-vad-measurement-${mode}`,
    gates,
    resourceClearance: clearance,
    measurement: measurement ? { rc: measurement.rc, parsed: measurement.parsed, error: measurement.error, stderrTail: measurement.stderrTail } : null,
    metricsPath: fs.existsSync(METRICS) ? path.relative(WORKSPACE, METRICS) : null,
    indicatorRestored,
    finalIndicator: readJson(INDICATOR, {}),
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      boundedMeasurement: mode === 'measure',
      durationSeconds: mode === 'measure' ? seconds : 0,
      startsMicrophone: status === 'measured-metrics-only',
      recordsAudioToMemoryOnly: status === 'measured-metrics-only',
      writesRawAudioToDisk: false,
      storesRawAudio: false,
      transcriptGenerated: false,
      startsPersistentProcess: false,
      externalNetworkWrites: false,
      paidApi: false,
      gpuHeavy: false,
      realPhysicalActuation: false,
    },
  };
  writeJson(OUT, doc);
  appendAudit({ timestamp: doc.timestamp, event: 'measurement-finish', mode, status, indicatorRestored, storesRawAudio: false, transcriptGenerated: false });
  console.log(JSON.stringify({ ok: ['ready', 'measured-metrics-only'].includes(doc.status), out: OUT, status: doc.status, mode, measured: status === 'measured-metrics-only', startsMicrophone: doc.safety.startsMicrophone, recordsAudio: doc.safety.recordsAudioToMemoryOnly, clearanceAllowed: clearance?.parsed?.allowedNow ?? null, storesRawAudio: false, indicatorRestored, metricsPath: doc.metricsPath, candidateWakeCount: measurement?.parsed?.candidateWakeCount ?? null }, null, 2));
}

main();
