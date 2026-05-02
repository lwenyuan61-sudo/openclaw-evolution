import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_camera_single_frame_dry_run_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_camera_single_frame_dry_run_audit.jsonl');
const INDICATOR = path.join(STATE, 'camera_perception_indicator.json');

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

function ensureIndicator() {
  const indicator = readJson(INDICATOR, null);
  if (indicator && !indicator._error) return indicator;
  const doc = {
    timestamp: new Date().toISOString(),
    state: 'idle',
    reason: 'camera single-frame dry-run initialized indicator; no capture performed',
    captureNow: false,
    continuousCameraEnabled: false,
    storesRawImages: false,
    visibleIndicatorRequiredBeforeCapture: true,
  };
  writeJson(INDICATOR, doc);
  return doc;
}

function main() {
  const timestamp = new Date().toISOString();
  fs.mkdirSync(STATE, { recursive: true });
  const appControl = readJson('state/app_control_state.json', {});
  const resource = readJson('core/resource-state.json', {});
  const bodyIndicators = readJson('state/desktop_wrapper_body_indicator_status.json', {});
  const bodyContract = readJson('state/desktop_wrapper_body_control_contract_status.json', {});
  const currentIndicator = ensureIndicator();
  const pauseAll = Boolean(appControl.pauseAll);
  const resourceOk = resource.resourcePressure?.level === 'ok';
  const cameraAlreadyActive = Boolean(currentIndicator.captureNow || currentIndicator.continuousCameraEnabled);
  const dryRunSequence = [
    {
      step: 'preflight',
      indicatorState: currentIndicator.state ?? 'unknown',
      verifies: ['resource-ok', 'pauseAll=false', 'indicator-present', 'stop-path-present'],
    },
    {
      step: 'would-arm-visible-indicator',
      writePreview: { path: 'state/camera_perception_indicator.json', state: 'single-frame-preview', captureNow: false, continuousCameraEnabled: false, storesRawImages: false },
    },
    {
      step: 'would-capture-one-frame',
      capturePreview: { deviceIndex: 0, maxFrames: 1, timeoutSeconds: 5, rawImagePath: 'state/camera_single_frame_preview.jpg' },
      dryRunOnly: true,
    },
    {
      step: 'would-extract-semantics-and-delete-raw',
      retentionPreview: { processedSemanticsPath: 'state/camera_single_frame_semantics.json', rawImageDefaultRetention: 'delete-after-local-analysis', storesRawImagesByDefault: false },
    },
    {
      step: 'would-restore-idle-indicator',
      writePreview: { path: 'state/camera_perception_indicator.json', state: 'idle', captureNow: false, continuousCameraEnabled: false, storesRawImages: false },
    },
  ];
  const gates = [
    { id: 'resource-ok', status: resourceOk ? 'ready' : 'blocked', evidence: resource.resourcePressure?.level ?? 'unknown' },
    { id: 'pause-all-off', status: !pauseAll ? 'ready' : 'blocked', evidence: pauseAll },
    { id: 'camera-not-already-active', status: !cameraAlreadyActive ? 'ready' : 'blocked', evidence: cameraAlreadyActive },
    { id: 'body-indicators-ready', status: bodyIndicators.status === 'ready' ? 'ready' : 'warn', evidence: bodyIndicators.status ?? 'missing' },
    { id: 'camera-contract-ready', status: bodyContract.status === 'ready' ? 'ready' : 'warn', evidence: bodyContract.status ?? 'missing' },
    { id: 'dry-run-only', status: 'ready', evidence: { startsCamera: false, writesIndicator: false, capturesFrame: false } },
    { id: 'retention-delete-by-default', status: 'ready', evidence: { storesRawImages: false, rawImageDefaultRetention: 'delete-after-local-analysis' } },
  ];
  const blocked = gates.filter((gate) => gate.status === 'blocked');
  const doc = {
    timestamp,
    status: blocked.length === 0 ? 'ready' : 'blocked',
    mode: 'camera-single-frame-dry-run-no-capture',
    selectedDevice: { index: 0, source: 'previous camera probe detected index 0 opens at 640x480' },
    currentIndicator: {
      state: currentIndicator.state ?? 'unknown',
      captureNow: Boolean(currentIndicator.captureNow),
      continuousCameraEnabled: Boolean(currentIndicator.continuousCameraEnabled),
      storesRawImages: Boolean(currentIndicator.storesRawImages),
    },
    gates,
    dryRunSequence,
    auditPath: path.relative(WORKSPACE, AUDIT),
    futureRealRunBoundary: {
      requireVisibleIndicatorBeforeCapture: true,
      maxFramesFirstRun: 1,
      timeoutSeconds: 5,
      rawImageDefaultRetention: 'delete-after-local-analysis',
      networkUpload: false,
      paidApi: false,
      continuousLoop: false,
      stopPath: 'restore idle indicator, stop capture process, append audit, verify no camera process remains',
    },
    safety: {
      dryRunOnly: true,
      writesIndicator: false,
      startsCamera: false,
      capturesFrame: false,
      startsPersistentProcess: false,
      externalNetworkWrites: false,
      storesRawImages: false,
      storesRawAudio: false,
      realPhysicalActuation: false,
    },
  };
  writeJson(OUT, doc);
  appendAudit({ timestamp, status: doc.status, mode: doc.mode, dryRunOnly: true, selectedDevice: doc.selectedDevice, cameraAlreadyActive, pauseAll, resourcePressure: resource.resourcePressure?.level ?? 'unknown' });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, dryRunOnly: true, startsCamera: false, capturesFrame: false, gateCount: gates.length, blocked: blocked.map((gate) => gate.id) }, null, 2));
}

main();
