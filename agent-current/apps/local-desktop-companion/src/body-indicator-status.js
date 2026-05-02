import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_body_indicator_status.json');
const CAMERA_INDICATOR = path.join(STATE, 'camera_perception_indicator.json');

function readJson(relOrAbs, fallback = {}) {
  const file = path.isAbsolute(relOrAbs) ? relOrAbs : path.join(WORKSPACE, relOrAbs);
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch (error) { return { ...fallback, _error: `${error.name}: ${error.message}` }; }
}

function writeJson(file, doc) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
}

function ensureCameraIndicator() {
  const current = readJson(CAMERA_INDICATOR, null);
  if (current && !current._error) return { indicator: current, created: false };
  const doc = {
    timestamp: new Date().toISOString(),
    state: 'idle',
    reason: 'no-capture body indicator initialized; camera approved but not started',
    captureNow: false,
    continuousCameraEnabled: false,
    storesRawImages: false,
    visibleIndicatorRequiredBeforeCapture: true,
  };
  writeJson(CAMERA_INDICATOR, doc);
  return { indicator: doc, created: true };
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const voiceIndicator = readJson('state/voice_listening_indicator.json', {
    state: 'idle',
    recordingNow: false,
    alwaysOnMicEnabled: false,
  });
  const voicePlan = readJson('state/voice_wake_plan.json', {});
  const voiceCalibration = readJson('state/voice_calibration_status.json', {});
  const voiceBody = readJson('state/desktop_wrapper_voice_body_readiness_status.json', {});
  const appControl = readJson('state/app_control_state.json', {});
  const camera = ensureCameraIndicator();
  const resource = readJson('core/resource-state.json', {});

  const microphoneActive = Boolean(voiceIndicator.recordingNow || voiceIndicator.alwaysOnMicEnabled || voiceCalibration.recordingNow || voiceCalibration.alwaysOnMicEnabled);
  const cameraActive = Boolean(camera.indicator.captureNow || camera.indicator.continuousCameraEnabled);
  const pauseAll = Boolean(appControl.pauseAll);
  const gates = [
    {
      id: 'microphone-indicator-present',
      status: voiceIndicator._error ? 'warn' : 'ready',
      evidence: { state: voiceIndicator.state ?? 'unknown', recordingNow: Boolean(voiceIndicator.recordingNow), alwaysOnMicEnabled: Boolean(voiceIndicator.alwaysOnMicEnabled) },
    },
    {
      id: 'camera-indicator-present',
      status: camera.indicator._error ? 'warn' : 'ready',
      evidence: { state: camera.indicator.state ?? 'unknown', captureNow: Boolean(camera.indicator.captureNow), continuousCameraEnabled: Boolean(camera.indicator.continuousCameraEnabled), created: camera.created },
    },
    {
      id: 'no-capture-now',
      status: !microphoneActive && !cameraActive ? 'ready' : 'warn',
      evidence: { microphoneActive, cameraActive },
    },
    {
      id: 'pause-all-visible',
      status: 'ready',
      evidence: { pauseAll },
    },
    {
      id: 'resource-fit',
      status: resource.resourcePressure?.level === 'ok' ? 'ready' : 'warn',
      evidence: { resourcePressure: resource.resourcePressure?.level ?? 'unknown' },
    },
  ];
  const readyCount = gates.filter((gate) => gate.status === 'ready').length;
  const doc = {
    timestamp: new Date().toISOString(),
    status: readyCount === gates.length ? 'ready' : 'warn',
    mode: 'body-indicator-status-no-capture',
    summary: {
      microphoneIndicatorState: voiceIndicator.state ?? 'unknown',
      microphoneActive,
      alwaysOnMicApproved: voicePlan.approvedByLee === true || voicePlan.status === 'approved-not-started',
      manualCalibrationReady: voiceCalibration.status === 'ready',
      cameraIndicatorState: camera.indicator.state ?? 'unknown',
      cameraActive,
      pauseAll,
      voiceBodyReady: voiceBody.status === 'ready',
    },
    gates,
    controlsPreview: {
      microphoneStartRequires: ['visible indicator', 'audit ledger', 'pauseAll=false', 'local-only path', 'explicit bounded runner'],
      microphoneStopPath: ['set voice_listening_indicator state=idle', 'stop/kill listener process if present', 'write audit'],
      cameraStartRequires: ['visible indicator', 'audit ledger', 'pauseAll=false', 'retention policy', 'single-frame or bounded loop first'],
      cameraStopPath: ['set camera_perception_indicator state=idle', 'stop capture loop if present', 'write audit'],
    },
    safety: {
      noCapture: true,
      startsMicrophone: false,
      startsCamera: false,
      startsPersistentProcess: false,
      externalNetworkWrites: false,
      storesRawAudio: false,
      storesRawImages: false,
      realPhysicalActuation: false,
      writesOnlyStatusIndicators: true,
    },
  };
  writeJson(OUT, doc);
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, readyCount, gateCount: gates.length, microphoneActive, cameraActive }, null, 2));
}

main();
