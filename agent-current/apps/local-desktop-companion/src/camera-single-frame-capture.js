import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import childProcess from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const INDICATOR = path.join(STATE, 'camera_perception_indicator.json');
const OUT = path.join(STATE, 'desktop_wrapper_camera_single_frame_capture_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_camera_single_frame_capture_audit.jsonl');
const SEMANTICS = path.join(STATE, 'camera_single_frame_semantics.json');
const RAW = path.join(STATE, 'camera_single_frame_capture_tmp.jpg');
const CAMERA_IO = path.join(WORKSPACE, 'skills', 'camera-io', 'scripts', 'camera_io.py');
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

function indicatorDoc(state, reason, extra = {}) {
  return {
    timestamp: new Date().toISOString(),
    state,
    reason,
    captureNow: state !== 'idle',
    continuousCameraEnabled: false,
    storesRawImages: false,
    visibleIndicatorRequiredBeforeCapture: true,
    ...extra,
  };
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

function runCapture(device = 0) {
  const started = Date.now();
  const result = childProcess.spawnSync('python', [CAMERA_IO, 'capture', RAW, '--device', String(device)], {
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

function selectedMode() {
  const args = new Set(process.argv.slice(2));
  if (args.has('--capture')) return 'capture';
  return 'status';
}

function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const mode = selectedMode();
  const clearance = mode === 'capture' ? runClearance('camera-capture') : null;
  const resource = readJson('core/resource-state.json', {});
  const appControl = readJson('state/app_control_state.json', {});
  const bodyIndicators = readJson('state/desktop_wrapper_body_indicator_status.json', {});
  const dryRun = readJson('state/desktop_wrapper_camera_single_frame_dry_run_status.json', {});
  const existingIndicator = readJson(INDICATOR, indicatorDoc('idle', 'indicator initialized by capture status'));
  const resourceOk = resource.resourcePressure?.level === 'ok';
  const pauseAll = Boolean(appControl.pauseAll);
  const cameraAlreadyActive = Boolean(existingIndicator.captureNow || existingIndicator.continuousCameraEnabled);
  const gates = [
    { id: 'resource-clearance-camera-capture', status: mode !== 'capture' ? 'ready' : clearance?.parsed?.allowedNow === true ? 'ready' : 'blocked', evidence: mode !== 'capture' ? 'not-capture-mode' : clearance?.parsed?.requestedClass ?? 'missing-clearance' },
    { id: 'resource-ok', status: resourceOk ? 'ready' : 'blocked', evidence: resource.resourcePressure?.level ?? 'unknown' },
    { id: 'pause-all-off', status: !pauseAll ? 'ready' : 'blocked', evidence: pauseAll },
    { id: 'camera-not-already-active', status: !cameraAlreadyActive ? 'ready' : 'blocked', evidence: cameraAlreadyActive },
    { id: 'body-indicators-ready', status: bodyIndicators.status === 'ready' ? 'ready' : 'warn', evidence: bodyIndicators.status ?? 'missing' },
    { id: 'single-frame-dry-run-ready', status: dryRun.status === 'ready' ? 'ready' : 'warn', evidence: dryRun.status ?? 'missing' },
    { id: 'camera-io-script-present', status: fs.existsSync(CAMERA_IO) ? 'ready' : 'blocked', evidence: path.relative(WORKSPACE, CAMERA_IO) },
  ];
  const blocked = gates.filter((gate) => gate.status === 'blocked');
  let capture = null;
  let semantics = null;
  let rawDeleted = false;
  let indicatorRestored = false;
  let status = blocked.length === 0 ? 'ready' : 'blocked';

  try {
    if (mode === 'capture' && blocked.length === 0) {
      fs.rmSync(RAW, { force: true });
      writeJson(INDICATOR, indicatorDoc('single-frame-capturing', 'bounded single-frame camera capture in progress; raw image will be deleted by default', { deviceIndex: 0 }));
      appendAudit({ timestamp: new Date().toISOString(), event: 'capture-start', deviceIndex: 0, bounded: true, maxFrames: 1 });
      capture = runCapture(0);
      if (capture.rc !== 0 || !capture.parsed || !fs.existsSync(RAW)) {
        status = 'failed';
      } else {
        const stat = fs.statSync(RAW);
        semantics = {
          timestamp: new Date().toISOString(),
          source: 'camera-single-frame-capture',
          device: capture.parsed.device,
          width: capture.parsed.width,
          height: capture.parsed.height,
          rawBytesBeforeDeletion: stat.size,
          rawSha256BeforeDeletion: sha256(RAW),
          semanticSummary: 'single frame captured successfully; no visual content description retained by this connector',
          retention: {
            rawImageDefaultRetention: 'delete-after-local-analysis',
            rawImageDeleted: false,
            storedRawImagePath: null,
            networkUpload: false,
            paidApi: false,
          },
        };
        fs.rmSync(RAW, { force: true });
        rawDeleted = !fs.existsSync(RAW);
        semantics.retention.rawImageDeleted = rawDeleted;
        writeJson(SEMANTICS, semantics);
        status = rawDeleted ? 'captured-and-deleted' : 'warn-raw-not-deleted';
      }
    }
  } finally {
    writeJson(INDICATOR, indicatorDoc('idle', 'camera single-frame capture complete or inactive; camera idle', { lastCaptureMode: mode }));
    indicatorRestored = true;
  }

  const doc = {
    timestamp: new Date().toISOString(),
    status,
    mode: `camera-single-frame-${mode}`,
    gates,
    resourceClearance: clearance,
    selectedDevice: { index: 0, source: 'skills/camera-io previous probe' },
    capture,
    semanticsPath: semantics ? path.relative(WORKSPACE, SEMANTICS) : null,
    rawPathDeleted: rawDeleted || !fs.existsSync(RAW),
    indicatorRestored,
    finalIndicator: readJson(INDICATOR, {}),
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      boundedSingleFrame: mode === 'capture',
      maxFrames: mode === 'capture' ? 1 : 0,
      continuousCameraEnabled: false,
      startsPersistentProcess: false,
      externalNetworkWrites: false,
      storesRawImages: false,
      rawImageDeleted: rawDeleted || !fs.existsSync(RAW),
      storesRawAudio: false,
      realPhysicalActuation: false,
    },
  };
  writeJson(OUT, doc);
  appendAudit({ timestamp: doc.timestamp, event: 'capture-finish', mode, status, rawDeleted: doc.safety.rawImageDeleted, indicatorRestored, width: capture?.parsed?.width, height: capture?.parsed?.height });
  console.log(JSON.stringify({ ok: ['ready', 'captured-and-deleted'].includes(doc.status), out: OUT, status: doc.status, mode, captured: status === 'captured-and-deleted', rawImageDeleted: doc.safety.rawImageDeleted, indicatorRestored, startsCamera: status === 'captured-and-deleted', capturesFrame: status === 'captured-and-deleted', clearanceAllowed: clearance?.parsed?.allowedNow ?? null, width: capture?.parsed?.width ?? null, height: capture?.parsed?.height ?? null }, null, 2));
}

main();
