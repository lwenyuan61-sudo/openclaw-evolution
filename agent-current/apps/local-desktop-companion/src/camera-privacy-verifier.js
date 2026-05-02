import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_camera_privacy_verifier_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_camera_privacy_verifier_audit.jsonl');

const RAW_CANDIDATES = [
  'state/camera_single_frame_capture_tmp.jpg',
  'state/camera_single_frame_capture_tmp.png',
  'state/camera_single_frame_preview.jpg',
  'state/camera_single_frame_preview.png',
];

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

function existsWithSize(rel) {
  const abs = path.join(WORKSPACE, rel);
  if (!fs.existsSync(abs)) return { rel, exists: false, bytes: 0 };
  const stat = fs.statSync(abs);
  return { rel, exists: true, bytes: stat.size };
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const capture = readJson('state/desktop_wrapper_camera_single_frame_capture_status.json', {});
  const semantics = readJson('state/camera_single_frame_semantics.json', {});
  const indicator = readJson('state/camera_perception_indicator.json', {});
  const resource = readJson('core/resource-state.json', {});
  const rawCandidates = RAW_CANDIDATES.map(existsWithSize);
  const rawLeftovers = rawCandidates.filter((item) => item.exists);
  const semanticsRetention = semantics.retention || {};
  const gates = [
    { id: 'resource-ok', status: resource.resourcePressure?.level === 'ok' ? 'ready' : 'warn', evidence: resource.resourcePressure?.level ?? 'unknown' },
    { id: 'capture-status-safe', status: ['captured-and-deleted', 'ready'].includes(capture.status) ? 'ready' : 'warn', evidence: capture.status ?? 'missing' },
    { id: 'raw-temp-files-absent', status: rawLeftovers.length === 0 ? 'ready' : 'blocked', evidence: rawCandidates },
    { id: 'semantics-retention-no-raw-path', status: semanticsRetention.storedRawImagePath == null ? 'ready' : 'blocked', evidence: semanticsRetention.storedRawImagePath ?? null },
    { id: 'semantics-says-raw-deleted', status: semanticsRetention.rawImageDeleted === true ? 'ready' : 'warn', evidence: semanticsRetention.rawImageDeleted },
    { id: 'indicator-idle', status: indicator.state === 'idle' && indicator.captureNow === false && indicator.continuousCameraEnabled === false ? 'ready' : 'blocked', evidence: { state: indicator.state, captureNow: indicator.captureNow, continuousCameraEnabled: indicator.continuousCameraEnabled } },
    { id: 'no-network-or-paid-api', status: semanticsRetention.networkUpload === false && semanticsRetention.paidApi === false ? 'ready' : 'warn', evidence: { networkUpload: semanticsRetention.networkUpload, paidApi: semanticsRetention.paidApi } },
  ];
  const blocked = gates.filter((gate) => gate.status === 'blocked');
  const warnings = gates.filter((gate) => gate.status === 'warn');
  const doc = {
    timestamp,
    status: blocked.length === 0 ? 'passed' : 'failed',
    mode: 'camera-capture-privacy-retention-verifier',
    captureSummary: {
      status: capture.status ?? 'missing',
      width: capture.capture?.parsed?.width ?? semantics.width ?? null,
      height: capture.capture?.parsed?.height ?? semantics.height ?? null,
      rawPathDeleted: capture.rawPathDeleted ?? null,
      indicatorRestored: capture.indicatorRestored ?? null,
    },
    semanticsSummary: {
      exists: !semantics._error,
      path: 'state/camera_single_frame_semantics.json',
      rawBytesBeforeDeletion: semantics.rawBytesBeforeDeletion ?? null,
      hasHashOnly: Boolean(semantics.rawSha256BeforeDeletion) && semanticsRetention.storedRawImagePath == null,
      retainedFields: Object.keys(semantics).sort(),
    },
    rawCandidates,
    gates,
    warnings: warnings.map((gate) => gate.id),
    blocked: blocked.map((gate) => gate.id),
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      verifierOnly: true,
      deletesFiles: false,
      startsCamera: false,
      capturesFrame: false,
      startsPersistentProcess: false,
      externalNetworkWrites: false,
      storesRawImages: false,
      realPhysicalActuation: false,
    },
  };
  writeJson(OUT, doc);
  appendAudit({ timestamp, status: doc.status, rawLeftoverCount: rawLeftovers.length, warnings: doc.warnings, captureStatus: doc.captureSummary.status, indicatorState: indicator.state ?? 'unknown' });
  console.log(JSON.stringify({ ok: doc.status === 'passed', out: OUT, status: doc.status, rawLeftoverCount: rawLeftovers.length, warningCount: warnings.length, verifierOnly: true }, null, 2));
}

main();
