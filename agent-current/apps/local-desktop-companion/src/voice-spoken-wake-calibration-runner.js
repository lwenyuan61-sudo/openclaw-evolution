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
const OUT = path.join(STATE, 'desktop_wrapper_voice_spoken_wake_calibration_runner_status.json');
const RESULT = path.join(STATE, 'voice_spoken_wake_calibration_result.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_voice_spoken_wake_calibration_runner_audit.jsonl');

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
  return new Set(process.argv.slice(2)).has('--calibrate') ? 'calibrate' : 'status';
}

function armedForCalibration() {
  return process.env.LOCAL_AGENT_SPOKEN_WAKE_ARM === '1';
}

function runInMemoryCalibration({ seconds, deviceIndex, sampleRate, threshold, phrase }) {
  const code = String.raw`
import json, sys, time
try:
    import sounddevice as sd
    import numpy as np
except Exception as exc:
    print(json.dumps({'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}))
    sys.exit(2)
seconds = float(sys.argv[1])
device = int(sys.argv[2])
sample_rate = int(float(sys.argv[3]))
threshold = float(sys.argv[4])
phrase = sys.argv[5]
window_ms = 30
hop_ms = 15
started = time.time()
try:
    data = sd.rec(int(seconds * sample_rate), samplerate=sample_rate, channels=1, dtype='float32', device=device)
    sd.wait()
except Exception as exc:
    print(json.dumps({'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}))
    sys.exit(3)
x = data.reshape(-1).astype('float64')
win = max(1, int(sample_rate * window_ms / 1000.0))
hop = max(1, int(sample_rate * hop_ms / 1000.0))
rms = []
for start in range(0, max(1, x.size - win + 1), hop):
    chunk = x[start:start+win]
    if chunk.size:
        rms.append(float(np.sqrt(np.mean(np.square(chunk)))))
r = np.array(rms or [0.0], dtype='float64')
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
print(json.dumps({
    'ok': True,
    'phraseExpected': phrase,
    'phraseConfirmationBackend': 'not-run-in-this-minimal-runner-without-raw-audio-disk-path',
    'durationSeconds': round(float(seconds), 3),
    'deviceIndex': device,
    'sampleRate': sample_rate,
    'windowMs': window_ms,
    'hopMs': hop_ms,
    'windowCount': int(len(r)),
    'candidateWakeCount': int(candidate_count),
    'rms': {
        'median': round(float(np.median(r)), 6),
        'p95': round(float(np.percentile(r, 95)), 6),
        'max': round(float(np.max(r)), 6),
    },
    'thresholdRms': threshold,
    'rawAudioWrittenToDisk': False,
    'rawAudioRetained': False,
    'transcriptGenerated': False,
    'phraseMatched': False,
    'needsPhraseConfirmationBackend': True,
    'elapsedMs': int((time.time() - started) * 1000),
}, ensure_ascii=False))
`;
  const result = childProcess.spawnSync('python', ['-c', code, String(seconds), String(deviceIndex), String(sampleRate), String(threshold), phrase], {
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

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const mode = selectedMode();
  const timestamp = new Date().toISOString();
  const resource = readJson('core/resource-state.json', {});
  const appControl = readJson('state/app_control_state.json', {});
  const boundary = readJson('state/desktop_wrapper_voice_spoken_wake_boundary_status.json', {});
  const engine = readJson('state/desktop_wrapper_voice_wake_engine_readiness_status.json', {});
  const indicator = readJson(INDICATOR, indicatorDoc('idle', 'indicator initialized by spoken wake calibration runner'));
  const resourceOk = resource.resourcePressure?.level === 'ok';
  const pauseAll = Boolean(appControl.pauseAll);
  const indicatorIdle = indicator.state === 'idle' && indicator.recordingNow === false && indicator.alwaysOnMicEnabled === false;
  const contract = boundary.calibrationContract ?? {};
  const bounded = contract.boundedRun ?? {};
  const phrase = contract.recommendedPhrase ?? 'the agent';
  const seconds = Number(bounded.durationSeconds ?? 5);
  const deviceIndex = Number(bounded.selectedDevice ?? 1);
  const sampleRate = Number(bounded.sampleRate ?? 44100);
  const threshold = Number(bounded.vadThresholdRms ?? 0.01);
  const gates = [
    { id: 'resource-ok', status: resourceOk ? 'ready' : 'blocked', evidence: resource.resourcePressure?.level ?? 'unknown' },
    { id: 'pause-all-off', status: !pauseAll ? 'ready' : 'blocked', evidence: pauseAll },
    { id: 'spoken-boundary-ready', status: boundary.status === 'ready' ? 'ready' : 'blocked', evidence: boundary.status ?? 'missing' },
    { id: 'wake-engine-current-path-ready', status: engine.currentPath?.ready === true ? 'ready' : 'blocked', evidence: engine.currentPath ?? null },
    { id: 'indicator-idle', status: indicatorIdle ? 'ready' : 'blocked', evidence: { state: indicator.state, recordingNow: indicator.recordingNow, alwaysOnMicEnabled: indicator.alwaysOnMicEnabled } },
  ];
  const blocked = gates.filter((gate) => gate.status === 'blocked');
  let calibration = null;
  let indicatorRestored = false;
  let status = blocked.length === 0 ? 'ready' : 'blocked';
  try {
    if (mode === 'calibrate') {
      if (!armedForCalibration()) {
        status = 'blocked-not-armed';
      } else if (blocked.length === 0) {
        writeJson(INDICATOR, indicatorDoc('spoken-wake-calibrating', 'bounded spoken wake calibration in progress; raw audio stays in memory and will not be written to disk', { durationSeconds: seconds, deviceIndex, phraseExpected: phrase }));
        appendAudit({ timestamp: new Date().toISOString(), event: 'calibration-start', seconds, deviceIndex, phraseExpected: phrase, storesRawAudio: false });
        calibration = runInMemoryCalibration({ seconds, deviceIndex, sampleRate, threshold, phrase });
        if (calibration.rc === 0 && calibration.parsed?.ok === true) {
          const resultDoc = {
            timestamp: new Date().toISOString(),
            source: 'voice-spoken-wake-calibration-runner',
            phraseExpected: phrase,
            result: calibration.parsed,
            retention: {
              rawAudioWrittenToDisk: false,
              rawAudioRetained: false,
              transcriptGenerated: false,
              networkUpload: false,
              paidApi: false,
            },
            note: 'Minimal runner intentionally does not write raw audio to disk; full phrase confirmation requires a local backend that accepts in-memory audio or a temporary-delete verifier path.',
          };
          writeJson(RESULT, resultDoc);
          status = 'measured-needs-phrase-confirmation-backend';
        } else {
          status = 'failed-calibration-measurement';
        }
      }
    }
  } finally {
    writeJson(INDICATOR, indicatorDoc('idle', 'spoken wake calibration complete or inactive; microphone idle', { lastCalibrationMode: mode }));
    indicatorRestored = true;
  }
  const doc = {
    timestamp: new Date().toISOString(),
    status,
    mode: `spoken-wake-calibration-${mode}`,
    gates,
    calibration,
    resultPath: fs.existsSync(RESULT) ? path.relative(WORKSPACE, RESULT) : null,
    indicatorRestored,
    finalIndicator: readJson(INDICATOR, {}),
    arming: {
      requiredForCalibration: true,
      env: 'LOCAL_AGENT_SPOKEN_WAKE_ARM=1',
      armedThisRun: armedForCalibration(),
      reason: 'Prevents accidental microphone start on routine status/test-matrix runs.',
    },
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      runnerReady: status === 'ready' || status === 'measured-needs-phrase-confirmation-backend',
      boundedCalibration: mode === 'calibrate' && armedForCalibration(),
      startsMicrophone: mode === 'calibrate' && armedForCalibration(),
      recordsAudioToMemoryOnly: mode === 'calibrate' && armedForCalibration(),
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
  appendAudit({ timestamp: doc.timestamp, event: 'calibration-finish', mode, status, armed: armedForCalibration(), indicatorRestored, storesRawAudio: false, transcriptGenerated: false });
  console.log(JSON.stringify({ ok: ['ready', 'measured-needs-phrase-confirmation-backend'].includes(doc.status), out: OUT, status: doc.status, mode, runnerReady: doc.safety.runnerReady, startsMicrophone: doc.safety.startsMicrophone, storesRawAudio: false, indicatorRestored, armed: armedForCalibration() }, null, 2));
}

main();
