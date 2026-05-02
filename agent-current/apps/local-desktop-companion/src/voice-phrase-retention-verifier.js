import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_voice_phrase_retention_verifier_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_voice_phrase_retention_verifier_audit.jsonl');

const RAW_CANDIDATES = [
  'state/voice_spoken_wake_calibration_tmp.wav',
  'state/voice_spoken_wake_candidate_tmp.wav',
  'state/voice_spoken_wake_phrase_tmp.wav',
  'state/voice_calibration_sample.wav',
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
  return { rel, exists: true, bytes: fs.statSync(abs).size };
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const resource = readJson('core/resource-state.json', {});
  const runner = readJson('state/desktop_wrapper_voice_spoken_wake_calibration_runner_status.json', {});
  const boundary = readJson('state/desktop_wrapper_voice_spoken_wake_boundary_status.json', {});
  const indicator = readJson('state/voice_listening_indicator.json', {});
  const result = readJson('state/voice_spoken_wake_calibration_result.json', {});
  const rawCandidates = RAW_CANDIDATES.map(existsWithSize);
  const rawLeftovers = rawCandidates.filter((item) => item.exists);
  const retention = result.retention ?? {};
  const indicatorIdle = indicator.state === 'idle' && indicator.recordingNow === false && indicator.alwaysOnMicEnabled === false;
  const gates = [
    { id: 'resource-ok', status: resource.resourcePressure?.level === 'ok' ? 'ready' : 'blocked', evidence: resource.resourcePressure?.level ?? 'unknown' },
    { id: 'spoken-runner-ready', status: ['ready', 'measured-needs-phrase-confirmation-backend'].includes(runner.status) ? 'ready' : 'blocked', evidence: runner.status ?? 'missing' },
    { id: 'spoken-boundary-ready', status: boundary.status === 'ready' ? 'ready' : 'blocked', evidence: boundary.status ?? 'missing' },
    { id: 'indicator-idle', status: indicatorIdle ? 'ready' : 'blocked', evidence: { state: indicator.state, recordingNow: indicator.recordingNow, alwaysOnMicEnabled: indicator.alwaysOnMicEnabled } },
    { id: 'raw-temp-files-absent', status: rawLeftovers.length === 0 ? 'ready' : 'blocked', evidence: rawCandidates },
    { id: 'result-retention-safe-or-absent', status: (!result.source || (retention.rawAudioWrittenToDisk === false && retention.rawAudioRetained === false && retention.networkUpload === false && retention.paidApi === false)) ? 'ready' : 'blocked', evidence: result.source ? retention : 'no calibration result yet' },
  ];
  const blocked = gates.filter((gate) => gate.status === 'blocked');
  const doc = {
    timestamp,
    status: blocked.length === 0 ? 'ready' : 'blocked',
    mode: 'voice-phrase-retention-verifier-no-recording',
    rawCandidates,
    phraseConfirmationRetentionContract: {
      allowedTemporaryPath: 'state/voice_spoken_wake_candidate_tmp.wav',
      defaultPreferredPath: 'in-memory audio only',
      ifTemporaryFileRequired: [
        'write bounded candidate audio only after visible mic indicator is active',
        'run local CPU phrase confirmation immediately',
        'write transcript/match/confidence/metrics only',
        'delete temporary wav in finally block',
        'run this verifier and require rawLeftoverCount=0',
      ],
      storedResultPath: 'state/voice_spoken_wake_calibration_result.json',
      storedResultAllowedFields: ['timestamp', 'phraseExpected', 'phraseMatched', 'confidence', 'candidateWakeCount', 'rms metrics', 'retention'],
      forbiddenRetention: ['raw audio path', 'raw audio bytes', 'external upload', 'paid API transcript', 'persistent listener side effects'],
    },
    gates,
    blocked: blocked.map((gate) => gate.id),
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      verifierOnly: true,
      startsMicrophone: false,
      recordsAudio: false,
      readsRawAudio: false,
      deletesFiles: false,
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
  appendAudit({ timestamp, status: doc.status, rawLeftoverCount: rawLeftovers.length, blocked: doc.blocked, startsMicrophone: false, recordsAudio: false });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, verifierOnly: true, startsMicrophone: false, recordsAudio: false, rawLeftoverCount: rawLeftovers.length, blocked: doc.blocked }, null, 2));
}

main();
