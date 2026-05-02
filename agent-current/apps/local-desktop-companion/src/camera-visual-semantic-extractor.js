import fs from 'node:fs';
import path from 'node:path';
import childProcess from 'node:child_process';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const INDICATOR = path.join(STATE, 'camera_perception_indicator.json');
const OUT = path.join(STATE, 'desktop_wrapper_camera_visual_semantic_extractor_status.json');
const SEMANTICS = path.join(STATE, 'camera_one_shot_visual_semantics.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_camera_visual_semantic_extractor_audit.jsonl');
const RAW = path.join(STATE, 'camera_single_frame_capture_tmp.jpg');
const CAMERA_IO = path.join(WORKSPACE, 'skills', 'camera-io', 'scripts', 'camera_io.py');
const PRIVACY_VERIFIER = path.join(WORKSPACE, 'apps', 'local-desktop-companion', 'src', 'camera-privacy-verifier.js');

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
    captureNow: state !== 'idle',
    continuousCameraEnabled: false,
    storesRawImages: false,
    visibleIndicatorRequiredBeforeCapture: true,
    ...extra,
  };
}

function spawn(cmd, args, timeout = 10000) {
  const started = Date.now();
  const result = childProcess.spawnSync(cmd, args, {
    cwd: WORKSPACE,
    encoding: 'utf8',
    windowsHide: true,
    timeout,
  });
  return {
    rc: result.status,
    durationMs: Date.now() - started,
    parsed: parseJson(result.stdout),
    stdoutTail: (result.stdout ?? '').slice(-1600),
    stderrTail: (result.stderr ?? '').slice(-1600),
    error: result.error ? `${result.error.name}: ${result.error.message}` : null,
  };
}

function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function selectedMode() {
  return new Set(process.argv.slice(2)).has('--capture') ? 'capture' : 'status';
}

function runCapture(device = 0) {
  return spawn('python', [CAMERA_IO, 'capture', RAW, '--device', String(device)], 10000);
}

function runLocalVisualAnalysis() {
  const code = String.raw`
import json, sys
try:
    import cv2
    import numpy as np
except Exception as exc:
    print(json.dumps({'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}))
    sys.exit(2)
path = sys.argv[1]
img = cv2.imread(path, cv2.IMREAD_COLOR)
if img is None:
    print(json.dumps({'ok': False, 'error': 'cv2.imread returned None'}))
    sys.exit(3)
h, w = img.shape[:2]
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
mean_bgr = img.mean(axis=(0, 1))
mean_rgb = [round(float(mean_bgr[2]), 2), round(float(mean_bgr[1]), 2), round(float(mean_bgr[0]), 2)]
brightness = round(float(gray.mean()), 2)
contrast = round(float(gray.std()), 2)
sharpness = round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 2)
dominant = max(enumerate(mean_rgb), key=lambda item: item[1])[0]
color_name = ['red-channel', 'green-channel', 'blue-channel'][dominant]
if brightness < 55:
    exposure = 'dark'
elif brightness > 205:
    exposure = 'bright'
else:
    exposure = 'normal'
if sharpness < 25:
    focus = 'low-detail-or-blurry'
elif sharpness < 120:
    focus = 'moderate-detail'
else:
    focus = 'sharp/high-detail'
summary = f'local low-level visual features only: {w}x{h}, exposure={exposure}, focus={focus}, dominant={color_name}; no object/person recognition retained'
print(json.dumps({'ok': True, 'width': int(w), 'height': int(h), 'brightness': brightness, 'contrast': contrast, 'sharpnessLaplacianVar': sharpness, 'meanRgb': mean_rgb, 'dominantColorChannel': color_name, 'exposure': exposure, 'focus': focus, 'semanticSummary': summary}, ensure_ascii=False))
`;
  return spawn('python', ['-c', code, RAW], 10000);
}

function runPrivacyVerifier() {
  if (!fs.existsSync(PRIVACY_VERIFIER)) return { rc: 127, parsed: null, error: 'privacy verifier missing', stdoutTail: '', stderrTail: '' };
  return spawn(process.execPath, [PRIVACY_VERIFIER], 10000);
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const mode = selectedMode();
  const resource = readJson('core/resource-state.json', {});
  const appControl = readJson('state/app_control_state.json', {});
  const bodyIndicators = readJson('state/desktop_wrapper_body_indicator_status.json', {});
  const boundary = readJson('state/desktop_wrapper_camera_visual_analysis_boundary_status.json', {});
  const existingIndicator = readJson(INDICATOR, indicatorDoc('idle', 'indicator initialized by visual semantic extractor'));
  const resourceOk = resource.resourcePressure?.level === 'ok';
  const pauseAll = Boolean(appControl.pauseAll);
  const cameraAlreadyActive = Boolean(existingIndicator.captureNow || existingIndicator.continuousCameraEnabled);
  const gates = [
    { id: 'resource-ok', status: resourceOk ? 'ready' : 'blocked', evidence: resource.resourcePressure?.level ?? 'unknown' },
    { id: 'pause-all-off', status: !pauseAll ? 'ready' : 'blocked', evidence: pauseAll },
    { id: 'camera-not-already-active', status: !cameraAlreadyActive ? 'ready' : 'blocked', evidence: cameraAlreadyActive },
    { id: 'body-indicators-ready', status: bodyIndicators.status === 'ready' ? 'ready' : 'warn', evidence: bodyIndicators.status ?? 'missing' },
    { id: 'visual-analysis-boundary-ready', status: boundary.status === 'ready' ? 'ready' : 'blocked', evidence: boundary.status ?? 'missing' },
    { id: 'camera-io-script-present', status: fs.existsSync(CAMERA_IO) ? 'ready' : 'blocked', evidence: path.relative(WORKSPACE, CAMERA_IO) },
  ];
  const blocked = gates.filter((gate) => gate.status === 'blocked');
  let capture = null;
  let analysis = null;
  let privacyVerifier = null;
  let rawHash = null;
  let rawBytes = null;
  let rawDeleted = !fs.existsSync(RAW);
  let indicatorRestored = false;
  let status = blocked.length === 0 ? 'ready' : 'blocked';

  try {
    if (mode === 'capture' && blocked.length === 0) {
      fs.rmSync(RAW, { force: true });
      writeJson(INDICATOR, indicatorDoc('analyzing-single-frame', 'bounded local visual semantics extraction in progress; raw image is temporary and will be deleted', { deviceIndex: 0 }));
      appendAudit({ timestamp: new Date().toISOString(), event: 'analysis-start', deviceIndex: 0, bounded: true, maxFrames: 1, localOnly: true });
      capture = runCapture(0);
      if (capture.rc !== 0 || !capture.parsed || !fs.existsSync(RAW)) {
        status = 'failed-capture';
      } else {
        rawBytes = fs.statSync(RAW).size;
        rawHash = sha256(RAW);
        analysis = runLocalVisualAnalysis();
        if (analysis.rc !== 0 || analysis.parsed?.ok !== true) {
          status = 'failed-analysis';
        } else {
          const semanticDoc = {
            timestamp: new Date().toISOString(),
            source: 'camera-visual-semantic-extractor',
            device: capture.parsed.device,
            width: analysis.parsed.width,
            height: analysis.parsed.height,
            semanticSummary: analysis.parsed.semanticSummary,
            lowLevelVisualFeatures: {
              brightness: analysis.parsed.brightness,
              contrast: analysis.parsed.contrast,
              sharpnessLaplacianVar: analysis.parsed.sharpnessLaplacianVar,
              meanRgb: analysis.parsed.meanRgb,
              dominantColorChannel: analysis.parsed.dominantColorChannel,
              exposure: analysis.parsed.exposure,
              focus: analysis.parsed.focus,
            },
            rawBytesBeforeDeletion: rawBytes,
            rawSha256BeforeDeletion: rawHash,
            recognitionScope: {
              objectRecognition: false,
              personRecognition: false,
              faceRecognition: false,
              ocr: false,
              modelInference: false,
              backend: 'local-cv2-low-level-features-only',
            },
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
          semanticDoc.retention.rawImageDeleted = rawDeleted;
          writeJson(SEMANTICS, semanticDoc);
          status = rawDeleted ? 'awaiting-privacy-verification' : 'warn-raw-not-deleted';
        }
      }
    }
  } finally {
    fs.rmSync(RAW, { force: true });
    rawDeleted = !fs.existsSync(RAW);
    writeJson(INDICATOR, indicatorDoc('idle', 'camera visual semantic extraction complete or inactive; camera idle', { lastAnalysisMode: mode }));
    indicatorRestored = true;
  }

  if (status === 'awaiting-privacy-verification') {
    privacyVerifier = runPrivacyVerifier();
    status = rawDeleted && privacyVerifier.parsed?.ok === true ? 'captured-analyzed-and-deleted' : 'warn-privacy-verification';
  }

  const doc = {
    timestamp: new Date().toISOString(),
    status,
    mode: `camera-visual-semantic-${mode}`,
    gates,
    selectedDevice: { index: 0, source: 'skills/camera-io previous probe' },
    capture,
    analysis: analysis ? { rc: analysis.rc, durationMs: analysis.durationMs, parsed: analysis.parsed, error: analysis.error, stderrTail: analysis.stderrTail } : null,
    semanticsPath: fs.existsSync(SEMANTICS) ? path.relative(WORKSPACE, SEMANTICS) : null,
    rawPathDeleted: rawDeleted,
    indicatorRestored,
    privacyVerifier: privacyVerifier ? { rc: privacyVerifier.rc, parsed: privacyVerifier.parsed, error: privacyVerifier.error } : null,
    finalIndicator: readJson(INDICATOR, {}),
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      boundedSingleFrame: mode === 'capture',
      maxFrames: mode === 'capture' ? 1 : 0,
      continuousCameraEnabled: false,
      startsPersistentProcess: false,
      externalNetworkWrites: false,
      storesRawImages: false,
      rawImageDeleted: rawDeleted,
      storesRawAudio: false,
      objectRecognition: false,
      personRecognition: false,
      faceRecognition: false,
      ocr: false,
      paidApi: false,
      modelInference: false,
      realPhysicalActuation: false,
    },
  };
  writeJson(OUT, doc);
  appendAudit({ timestamp: doc.timestamp, event: 'analysis-finish', mode, status, rawDeleted, indicatorRestored, width: analysis?.parsed?.width ?? capture?.parsed?.width, height: analysis?.parsed?.height ?? capture?.parsed?.height });
  console.log(JSON.stringify({ ok: ['ready', 'captured-analyzed-and-deleted'].includes(doc.status), out: OUT, status: doc.status, mode, captured: status === 'captured-analyzed-and-deleted', analyzedImageNow: status === 'captured-analyzed-and-deleted', rawImageDeleted: rawDeleted, indicatorRestored, width: analysis?.parsed?.width ?? null, height: analysis?.parsed?.height ?? null, summary: analysis?.parsed?.semanticSummary ?? null }, null, 2));
}

main();
