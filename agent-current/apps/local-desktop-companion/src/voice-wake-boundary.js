import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_voice_wake_boundary_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_voice_wake_boundary_audit.jsonl');

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

function includes(text, needle) {
  return String(text ?? '').toLowerCase().includes(needle);
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const resource = readJson('core/resource-state.json', {});
  const appControl = readJson('state/app_control_state.json', {});
  const voicePlan = readJson('state/voice_wake_plan.json', {});
  const voiceIndicator = readJson('state/voice_listening_indicator.json', {});
  const calibration = readJson('state/voice_calibration_status.json', {});
  const readiness = readJson('state/desktop_wrapper_voice_body_readiness_status.json', {});
  const availableAudio = String(voicePlan.availableAudio ?? readiness.summary?.wakeListenerQuality ?? '');
  const resourceOk = resource.resourcePressure?.level === 'ok';
  const pauseAll = Boolean(appControl.pauseAll);
  const indicatorIdle = voiceIndicator.state === 'idle' && voiceIndicator.recordingNow === false && voiceIndicator.alwaysOnMicEnabled === false;
  const approved = voicePlan.approvedByLee === true || voicePlan.status === 'approved-not-started';
  const localWhisperAvailable = includes(availableAudio, 'faster_whisper') || readiness.summary?.localTranscriptionBaseline === 'available-cpu-fallback';
  const soundDeviceAvailable = includes(availableAudio, 'sounddevice') || readiness.gates?.some?.((gate) => gate.id === 'local-transcription-baseline' && gate.evidence?.hasSoundDevice === true);
  const dedicatedWakeDepsMissing = ['webrtcvad', 'pvporcupine', 'openwakeword'].filter((dep) => !includes(availableAudio, dep) || includes(availableAudio, `${dep} absent`));
  const gates = [
    { id: 'resource-ok', status: resourceOk ? 'ready' : 'blocked', evidence: resource.resourcePressure?.level ?? 'unknown' },
    { id: 'pause-all-off', status: !pauseAll ? 'ready' : 'blocked', evidence: pauseAll },
    { id: 'voice-approved-not-started', status: approved && voicePlan.enabled === false ? 'ready' : 'blocked', evidence: { approvedByLee: voicePlan.approvedByLee, enabled: voicePlan.enabled, status: voicePlan.status } },
    { id: 'listening-indicator-idle', status: indicatorIdle ? 'ready' : 'blocked', evidence: { state: voiceIndicator.state, recordingNow: voiceIndicator.recordingNow, alwaysOnMicEnabled: voiceIndicator.alwaysOnMicEnabled } },
    { id: 'manual-calibration-ready', status: calibration.status === 'ready' ? 'ready' : 'warn', evidence: { status: calibration.status, recommendedInput: calibration.deviceEnumeration?.recommendedInput ?? null } },
    { id: 'local-cpu-transcription-baseline', status: localWhisperAvailable && soundDeviceAvailable ? 'ready' : 'warn', evidence: { localWhisperAvailable, soundDeviceAvailable, availableAudio } },
    { id: 'dedicated-wake-word-engine', status: dedicatedWakeDepsMissing.length ? 'warn' : 'ready', evidence: { missing: dedicatedWakeDepsMissing, fallback: 'CPU whisper phrase-loop only; not phone-grade always-on wake word' } },
  ];
  const blocked = gates.filter((gate) => gate.status === 'blocked');
  const warnings = gates.filter((gate) => gate.status === 'warn');
  const doc = {
    timestamp,
    status: blocked.length === 0 ? 'ready' : 'blocked',
    mode: 'voice-wake-boundary-no-recording',
    recommendedInput: calibration.deviceEnumeration?.recommendedInput ?? readiness.summary?.recommendedInput ?? null,
    startContract: {
      defaultState: 'not-started',
      explicitStartRequired: true,
      sequence: [
        'resource/pause gates pass',
        'set visible mic indicator to listening-or-calibrating before capture',
        'run CPU-first VAD/wake loop in bounded measured mode',
        'discard non-hit audio windows immediately',
        'log activation counts and false-positive estimate without retaining raw audio',
        'stop on pauseAll, app stop button, process exit, or resource warning',
        'restore indicator to idle and write audit/status',
      ],
      baselineBackend: localWhisperAvailable ? 'local faster-whisper tiny CPU fallback' : 'unavailable-until-local-transcription-baseline-restored',
      missingBetterWakeDeps: dedicatedWakeDepsMissing,
      qualityLimit: 'approved path exists, but current backend is not phone-grade wake-word DSP',
    },
    retentionPolicy: {
      rawAudioDefaultRetention: 'delete-after-local-analysis',
      storeRawAudio: false,
      storeTranscriptOnlyOnWakeHit: true,
      networkUpload: false,
      paidApi: false,
      gpuRequired: false,
    },
    stopAndRollback: {
      pauseAllStops: true,
      visibleIndicatorMustReturnIdle: true,
      killSwitchStatePath: 'state/app_control_state.json:pauseAll',
      auditPath: path.relative(WORKSPACE, AUDIT),
    },
    gates,
    blocked: blocked.map((gate) => gate.id),
    warnings: warnings.map((gate) => gate.id),
    safety: {
      boundaryOnly: true,
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
  appendAudit({ timestamp, status: doc.status, blocked: doc.blocked, warnings: doc.warnings, startsMicrophone: false, recordsAudio: false });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, boundaryOnly: true, startsMicrophone: false, recordsAudio: false, warningCount: doc.warnings.length, blocked: doc.blocked }, null, 2));
}

main();
