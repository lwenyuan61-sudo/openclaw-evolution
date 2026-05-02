import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_voice_wake_end_to_end_gate_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_voice_wake_end_to_end_gate_audit.jsonl');

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

function gate(id, status, evidence, nextStep = null) {
  return { id, status, evidence, ...(nextStep ? { nextStep } : {}) };
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const resource = readJson('core/resource-state.json', {});
  const body = readJson('state/desktop_wrapper_voice_body_readiness_status.json', {});
  const boundary = readJson('state/desktop_wrapper_voice_wake_boundary_status.json', {});
  const vadDry = readJson('state/desktop_wrapper_voice_vad_measurement_dry_run_status.json', {});
  const vadRunner = readJson('state/desktop_wrapper_voice_vad_measurement_runner_status.json', {});
  const vadBaseline = readJson('state/desktop_wrapper_voice_vad_baseline_evaluator_status.json', {});
  const spokenBoundary = readJson('state/desktop_wrapper_voice_spoken_wake_boundary_status.json', {});
  const engine = readJson('state/desktop_wrapper_voice_wake_engine_readiness_status.json', {});
  const spokenRunner = readJson('state/desktop_wrapper_voice_spoken_wake_calibration_runner_status.json', {});
  const retention = readJson('state/desktop_wrapper_voice_phrase_retention_verifier_status.json', {});
  const match = readJson('state/desktop_wrapper_voice_phrase_match_verifier_status.json', {});
  const indicator = readJson('state/voice_listening_indicator.json', {});
  const indicatorIdle = indicator.state === 'idle' && indicator.recordingNow === false && indicator.alwaysOnMicEnabled === false;
  const matchSelfTest = (match.normalizer?.examples ?? []).length > 0 && match.normalizer.examples.every((item) => item.passed === true);
  const gates = [
    gate('resource-ok', resource.resourcePressure?.level === 'ok' ? 'ready' : 'blocked', resource.resourcePressure?.level ?? 'unknown'),
    gate('body-readiness', body.status === 'ready' ? 'ready' : 'blocked', { status: body.status, readiness: body.readiness ?? null }),
    gate('voice-boundary', boundary.status === 'ready' ? 'ready' : 'blocked', boundary.status ?? 'missing'),
    gate('vad-dry-run', vadDry.status === 'ready' ? 'ready' : 'blocked', { status: vadDry.status, warnings: vadDry.warnings ?? [] }),
    gate('vad-runner', ['ready', 'measured-metrics-only'].includes(vadRunner.status) ? 'ready' : 'blocked', vadRunner.status ?? 'missing'),
    gate('vad-baseline', vadBaseline.status === 'ready' && (vadBaseline.warnings?.length ?? 0) === 0 ? 'ready' : 'blocked', { status: vadBaseline.status, warnings: vadBaseline.warnings ?? [] }),
    gate('spoken-wake-boundary', spokenBoundary.status === 'ready' ? 'ready' : 'blocked', spokenBoundary.status ?? 'missing'),
    gate('wake-engine-readiness', engine.status === 'ready' && engine.currentPath?.ready === true ? 'ready' : 'blocked', { status: engine.status, recommended: engine.recommendedNext?.id ?? null }),
    gate('spoken-runner-safe-status', spokenRunner.status === 'ready' && spokenRunner.safety?.startsMicrophone === false ? 'ready' : 'blocked', { status: spokenRunner.status, armed: spokenRunner.arming?.armedThisRun, startsMicrophone: spokenRunner.safety?.startsMicrophone }),
    gate('phrase-retention', retention.status === 'ready' && (retention.blocked?.length ?? 0) === 0 ? 'ready' : 'blocked', { status: retention.status, rawLeftovers: (retention.rawCandidates ?? []).filter((item) => item.exists).length }),
    gate('phrase-match', match.status === 'ready' && matchSelfTest ? 'ready' : 'blocked', { status: match.status, selfTest: matchSelfTest }),
    gate('indicator-idle', indicatorIdle ? 'ready' : 'blocked', { state: indicator.state, recordingNow: indicator.recordingNow, alwaysOnMicEnabled: indicator.alwaysOnMicEnabled }),
  ];
  const blocked = gates.filter((item) => item.status === 'blocked');
  const chain = [
    'approval/body readiness',
    'visible mic indicator boundary',
    'VAD dry-run/module probe',
    'bounded VAD metrics runner',
    '3/3 quiet baseline evaluator',
    'spoken wake calibration boundary',
    'wake engine readiness selection',
    'armed spoken calibration runner status gate',
    'phrase retention verifier',
    'phrase match verifier',
  ];
  const doc = {
    timestamp,
    status: blocked.length === 0 ? 'ready-for-armed-calibration' : 'blocked',
    mode: 'voice-wake-end-to-end-gate-no-recording',
    chain,
    readyFor: {
      armedSpokenWakeCalibration: blocked.length === 0,
      continuousAlwaysOnListener: false,
      reasonContinuousStillFalse: 'bounded spoken calibration must succeed before any continuous listener; dedicated VAD/wake engine still absent',
      recommendedNext: blocked.length === 0 ? 'armed-spoken-wake-calibration-when-Lee-is-ready-to-say-the agent' : 'clear-blocked-gates-first',
    },
    gates,
    blocked: blocked.map((item) => item.id),
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      gateOnly: true,
      startsMicrophone: false,
      recordsAudio: false,
      readsRawAudio: false,
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
  appendAudit({ timestamp, status: doc.status, blocked: doc.blocked, readyForArmedCalibration: doc.readyFor.armedSpokenWakeCalibration, startsMicrophone: false });
  console.log(JSON.stringify({ ok: doc.status === 'ready-for-armed-calibration', out: OUT, status: doc.status, gateOnly: true, startsMicrophone: false, recordsAudio: false, readyForArmedCalibration: doc.readyFor.armedSpokenWakeCalibration, blocked: doc.blocked }, null, 2));
}

main();
