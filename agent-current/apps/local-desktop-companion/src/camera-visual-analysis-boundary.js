import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_camera_visual_analysis_boundary_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_camera_visual_analysis_boundary_audit.jsonl');

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

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const resource = readJson('core/resource-state.json', {});
  const capture = readJson('state/desktop_wrapper_camera_single_frame_capture_status.json', {});
  const privacy = readJson('state/desktop_wrapper_camera_privacy_verifier_status.json', {});
  const semantics = readJson('state/camera_single_frame_semantics.json', {});
  const indicator = readJson('state/camera_perception_indicator.json', {});
  const appControl = readJson('state/app_control_state.json', {});
  const resourceOk = resource.resourcePressure?.level === 'ok';
  const pauseAll = Boolean(appControl.pauseAll);
  const rawAvailable = Boolean(semantics.retention?.storedRawImagePath);
  const rawDeleted = semantics.retention?.rawImageDeleted === true && privacy.status === 'passed';
  const indicatorIdle = indicator.state === 'idle' && indicator.captureNow === false && indicator.continuousCameraEnabled === false;
  const canAnalyzeCurrentFrame = rawAvailable === true;
  const gates = [
    { id: 'resource-ok', status: resourceOk ? 'ready' : 'blocked', evidence: resource.resourcePressure?.level ?? 'unknown' },
    { id: 'pause-all-off', status: !pauseAll ? 'ready' : 'blocked', evidence: pauseAll },
    { id: 'capture-metadata-present', status: capture.status ? 'ready' : 'warn', evidence: capture.status ?? 'missing' },
    { id: 'privacy-verifier-passed', status: privacy.status === 'passed' ? 'ready' : 'blocked', evidence: privacy.status ?? 'missing' },
    { id: 'indicator-idle-before-boundary', status: indicatorIdle ? 'ready' : 'blocked', evidence: { state: indicator.state, captureNow: indicator.captureNow, continuousCameraEnabled: indicator.continuousCameraEnabled } },
    { id: 'raw-image-not-retained', status: rawDeleted ? 'ready' : 'blocked', evidence: { rawDeleted, storedRawImagePath: semantics.retention?.storedRawImagePath ?? null } },
    { id: 'analysis-current-frame-blocked-without-raw', status: canAnalyzeCurrentFrame ? 'blocked' : 'ready', evidence: { rawAvailable, reason: canAnalyzeCurrentFrame ? 'unexpected raw image retained' : 'privacy-first path deleted raw image; analyze only during a future bounded capture window' } },
  ];
  const blocked = gates.filter((gate) => gate.status === 'blocked');
  const doc = {
    timestamp,
    status: blocked.length === 0 ? 'ready' : 'blocked',
    mode: 'camera-visual-analysis-boundary-no-image-analysis',
    currentFrameAnalysis: {
      possibleNow: false,
      reason: 'raw frame was intentionally deleted after metadata extraction; current connector must not reconstruct or analyze absent private image data',
      metadataOnlyAvailable: true,
      metadata: {
        device: semantics.device ?? capture.capture?.parsed?.device ?? null,
        width: semantics.width ?? capture.capture?.parsed?.width ?? null,
        height: semantics.height ?? capture.capture?.parsed?.height ?? null,
        rawBytesBeforeDeletion: semantics.rawBytesBeforeDeletion ?? null,
        hasRawHashOnly: Boolean(semantics.rawSha256BeforeDeletion),
      },
    },
    futureOneShotAnalysisContract: {
      sequence: [
        'resource/pause/body gates pass',
        'set visible camera indicator to analyzing-single-frame',
        'capture exactly one frame',
        'run local analysis while raw frame exists only in the bounded step',
        'write minimal semantic summary, confidence, and safety metadata',
        'delete raw image immediately',
        'run camera privacy verifier',
        'restore indicator to idle and append audit',
      ],
      allowedAnalysisBackends: ['local lightweight cv2/metadata first', 'configured image model only if explicitly selected by main persona and retention remains delete-by-default'],
      defaultRetention: { rawImage: 'delete-after-analysis', storedRawImagePath: null, semanticOnly: true },
      stopPath: 'restore indicator idle, verify no raw temp files, append audit, do not start continuous loop',
    },
    gates,
    blocked: blocked.map((gate) => gate.id),
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      boundaryOnly: true,
      analyzesImageNow: false,
      startsCamera: false,
      capturesFrame: false,
      startsPersistentProcess: false,
      externalNetworkWrites: false,
      storesRawImages: false,
      realPhysicalActuation: false,
    },
  };
  writeJson(OUT, doc);
  appendAudit({ timestamp, status: doc.status, blocked: doc.blocked, analyzesImageNow: false, rawDeleted, indicatorIdle });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, boundaryOnly: true, analyzesImageNow: false, blocked: doc.blocked }, null, 2));
}

main();
