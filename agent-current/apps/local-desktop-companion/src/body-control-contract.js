import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_body_control_contract_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_body_control_contract_audit.jsonl');

function readJson(rel, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8')); }
  catch (error) { return { ...fallback, _error: `${error.name}: ${error.message}` }; }
}

function writeJson(file, doc) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
}

function audit(event) {
  fs.mkdirSync(path.dirname(AUDIT), { recursive: true });
  fs.appendFileSync(AUDIT, `${JSON.stringify(event)}\n`, 'utf8');
}

function selectedMode() {
  const args = new Set(process.argv.slice(2));
  if (args.has('--preview-start-microphone')) return 'preview-start-microphone';
  if (args.has('--preview-stop-microphone')) return 'preview-stop-microphone';
  if (args.has('--preview-start-camera')) return 'preview-start-camera';
  if (args.has('--preview-stop-camera')) return 'preview-stop-camera';
  return 'status';
}

function actionSpec(mode) {
  const common = {
    previewOnly: true,
    startsMicrophone: false,
    startsCamera: false,
    startsPersistentProcess: false,
    externalNetworkWrites: false,
    storesRawAudio: false,
    storesRawImages: false,
    realPhysicalActuation: false,
  };
  const specs = {
    status: {
      target: 'none',
      transition: 'observe-current-body-indicator-state',
      indicatorWritePreview: null,
      stopPathPreview: null,
      ...common,
    },
    'preview-start-microphone': {
      target: 'microphone',
      transition: 'idle -> armed-visible-listening-indicator -> bounded-runner-required',
      indicatorWritePreview: { path: 'state/voice_listening_indicator.json', state: 'manual-recording-preview', recordingNow: false, alwaysOnMicEnabled: false },
      stopPathPreview: { path: 'state/voice_listening_indicator.json', state: 'idle', recordingNow: false, alwaysOnMicEnabled: false },
      requiredBeforeRealStart: ['pauseAll=false', 'visible indicator already rendered', 'audit ledger opened', 'bounded duration or explicit stop path', 'local-only transcription if any', 'raw audio delete-by-default'],
      ...common,
    },
    'preview-stop-microphone': {
      target: 'microphone',
      transition: 'any microphone indicator state -> idle/off',
      indicatorWritePreview: { path: 'state/voice_listening_indicator.json', state: 'idle', recordingNow: false, alwaysOnMicEnabled: false },
      stopPathPreview: { killProcessFamilyIfPresent: 'voice_wake_listener.py / calibration runner', writeIndicatorIdle: true, appendAudit: true },
      ...common,
    },
    'preview-start-camera': {
      target: 'camera',
      transition: 'idle -> armed-visible-camera-indicator -> single-frame-or-bounded-loop-required',
      indicatorWritePreview: { path: 'state/camera_perception_indicator.json', state: 'manual-capture-preview', captureNow: false, continuousCameraEnabled: false, storesRawImages: false },
      stopPathPreview: { path: 'state/camera_perception_indicator.json', state: 'idle', captureNow: false, continuousCameraEnabled: false, storesRawImages: false },
      requiredBeforeRealStart: ['pauseAll=false', 'visible indicator already rendered', 'audit ledger opened', 'single-frame or bounded loop first', 'processed semantics retention by default', 'raw image delete-by-default unless explicitly needed'],
      ...common,
    },
    'preview-stop-camera': {
      target: 'camera',
      transition: 'any camera indicator state -> idle/off',
      indicatorWritePreview: { path: 'state/camera_perception_indicator.json', state: 'idle', captureNow: false, continuousCameraEnabled: false, storesRawImages: false },
      stopPathPreview: { killProcessFamilyIfPresent: 'camera capture/perception loop', writeIndicatorIdle: true, appendAudit: true },
      ...common,
    },
  };
  return specs[mode] ?? specs.status;
}

function main() {
  const timestamp = new Date().toISOString();
  const mode = selectedMode();
  const voiceIndicator = readJson('state/voice_listening_indicator.json', { state: 'missing' });
  const cameraIndicator = readJson('state/camera_perception_indicator.json', { state: 'missing' });
  const bodyIndicators = readJson('state/desktop_wrapper_body_indicator_status.json', {});
  const appControl = readJson('state/app_control_state.json', {});
  const resource = readJson('core/resource-state.json', {});
  const spec = actionSpec(mode);
  const pauseAll = Boolean(appControl.pauseAll);
  const resourceOk = resource.resourcePressure?.level === 'ok';
  const activeNow = Boolean(voiceIndicator.recordingNow || voiceIndicator.alwaysOnMicEnabled || cameraIndicator.captureNow || cameraIndicator.continuousCameraEnabled);
  const gates = [
    { id: 'resource-ok', status: resourceOk ? 'ready' : 'blocked', evidence: resource.resourcePressure?.level ?? 'unknown' },
    { id: 'pause-all-off', status: !pauseAll ? 'ready' : 'blocked', evidence: pauseAll },
    { id: 'body-indicators-ready', status: bodyIndicators.status === 'ready' ? 'ready' : 'warn', evidence: bodyIndicators.status ?? 'missing' },
    { id: 'preview-only-no-capture', status: 'ready', evidence: { startsMicrophone: false, startsCamera: false } },
    { id: 'stop-path-defined', status: spec.stopPathPreview !== undefined ? 'ready' : 'warn', evidence: spec.stopPathPreview },
  ];
  const blocked = gates.filter((gate) => gate.status === 'blocked');
  const doc = {
    timestamp,
    status: blocked.length === 0 ? 'ready' : 'blocked',
    mode: `body-control-contract-${mode}`,
    selectedAction: mode,
    currentState: {
      voiceIndicator: { state: voiceIndicator.state ?? 'unknown', recordingNow: Boolean(voiceIndicator.recordingNow), alwaysOnMicEnabled: Boolean(voiceIndicator.alwaysOnMicEnabled) },
      cameraIndicator: { state: cameraIndicator.state ?? 'unknown', captureNow: Boolean(cameraIndicator.captureNow), continuousCameraEnabled: Boolean(cameraIndicator.continuousCameraEnabled) },
      activeNow,
      pauseAll,
      resourcePressure: resource.resourcePressure?.level ?? 'unknown',
    },
    gates,
    actionPreview: spec,
    supportedPreviewActions: ['preview-start-microphone', 'preview-stop-microphone', 'preview-start-camera', 'preview-stop-camera'],
    realExecutionBoundary: {
      microphone: 'Not implemented in this connector; future real start must be bounded, visible, audited, local-only, and stopped by indicator/process guard.',
      camera: 'Not implemented in this connector; future real start must be single-frame or bounded loop first, visible, audited, and delete raw images by default.',
    },
    safety: {
      previewOnly: true,
      mutatesIndicators: false,
      startsMicrophone: false,
      startsCamera: false,
      startsPersistentProcess: false,
      externalNetworkWrites: false,
      storesRawAudio: false,
      storesRawImages: false,
      realPhysicalActuation: false,
    },
  };
  writeJson(OUT, doc);
  audit({ timestamp, mode, status: doc.status, target: spec.target, previewOnly: true, pauseAll, resourcePressure: doc.currentState.resourcePressure, activeNow });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, mode, target: spec.target, previewOnly: true, activeNow }, null, 2));
}

main();
