import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_voice_spoken_wake_boundary_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_voice_spoken_wake_boundary_audit.jsonl');

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
  const appControl = readJson('state/app_control_state.json', {});
  const baseline = readJson('state/desktop_wrapper_voice_vad_baseline_evaluator_status.json', {});
  const metrics = readJson('state/voice_vad_measurement_metrics.json', {});
  const wakePlan = readJson('state/voice_wake_plan.json', {});
  const indicator = readJson('state/voice_listening_indicator.json', {});
  const resourceOk = resource.resourcePressure?.level === 'ok';
  const pauseAll = Boolean(appControl.pauseAll);
  const indicatorIdle = indicator.state === 'idle' && indicator.recordingNow === false && indicator.alwaysOnMicEnabled === false;
  const baselineReady = baseline.status === 'ready' && (baseline.warnings?.length ?? 0) === 0;
  const metricValues = metrics.metrics ?? {};
  const threshold = metricValues.thresholdBootstrap?.initialThresholdRms ?? baseline.evaluator?.recommendation?.currentThresholdRms ?? 0.01;
  const gates = [
    { id: 'resource-ok', status: resourceOk ? 'ready' : 'blocked', evidence: resource.resourcePressure?.level ?? 'unknown' },
    { id: 'pause-all-off', status: !pauseAll ? 'ready' : 'blocked', evidence: pauseAll },
    { id: 'baseline-ready-no-warnings', status: baselineReady ? 'ready' : 'blocked', evidence: { status: baseline.status, warnings: baseline.warnings ?? [] } },
    { id: 'indicator-idle', status: indicatorIdle ? 'ready' : 'blocked', evidence: { state: indicator.state, recordingNow: indicator.recordingNow, alwaysOnMicEnabled: indicator.alwaysOnMicEnabled } },
    { id: 'wake-approved-not-started', status: wakePlan.approvedByLee === true && wakePlan.enabled === false ? 'ready' : 'blocked', evidence: { approvedByLee: wakePlan.approvedByLee, enabled: wakePlan.enabled, status: wakePlan.status } },
    { id: 'local-baseline-threshold-adequate', status: baseline.evaluator?.recommendation?.candidateThresholdAdequateForQuietBaseline === true ? 'ready' : 'warn', evidence: baseline.evaluator?.recommendation ?? null },
  ];
  const blocked = gates.filter((gate) => gate.status === 'blocked');
  const warnings = gates.filter((gate) => gate.status === 'warn');
  const candidateWakeWords = ['the agent', 'hey local-evolution-agent'];
  const doc = {
    timestamp,
    status: blocked.length === 0 ? 'ready' : 'blocked',
    mode: 'spoken-wake-phrase-calibration-boundary-no-recording',
    calibrationContract: {
      defaultState: 'not-started',
      explicitRunRequired: true,
      recommendedWakeWords: candidateWakeWords,
      recommendedPhrase: 'the agent',
      boundedRun: {
        durationSeconds: 5,
        expectedHumanAction: 'speak the selected wake phrase once near the start of the window',
        selectedDevice: metrics.deviceIndex ?? 1,
        sampleRate: metricValues.sampleRate ?? 44100,
        vadThresholdRms: threshold,
        candidateRule: {
          initialThresholdRms: threshold,
          minConsecutiveActiveWindows: metricValues.thresholdBootstrap?.minConsecutiveActiveWindows ?? 4,
          candidateCooldownMs: 2000,
        },
      },
      sequence: [
        'resource/pause/baseline/indicator gates pass',
        'set visible mic indicator to spoken-wake-calibrating before capture',
        'record only bounded in-memory audio for the short calibration window',
        'detect candidate windows with existing VAD threshold',
        'run local CPU whisper phrase confirmation only on candidate window or bounded sample',
        'write phrase match/confidence/metrics only',
        'delete all raw audio buffers and do not write raw audio to disk',
        'restore indicator idle and append audit/status',
      ],
      acceptanceCriteria: {
        rawAudioWrittenToDisk: false,
        candidateWakeCountAtLeast: 1,
        transcriptMustContainOneOf: candidateWakeWords,
        indicatorRestored: true,
        noPersistentProcess: true,
      },
      rollback: {
        onFailure: 'restore idle indicator; retain metrics/failure reason only; no retry loop',
        killSwitch: 'state/app_control_state.json:pauseAll',
      },
    },
    baselineSummary: {
      measurementFinishEvents: baseline.evaluator?.auditMeasurementFinishEvents ?? null,
      candidateRatePerHour: baseline.evaluator?.aggregate?.candidateRatePerHour ?? null,
      latestNoiseFloorRmsP20: metricValues.thresholdBootstrap?.noiseFloorRmsP20 ?? null,
      latestRmsP95: metricValues.rms?.p95 ?? null,
      latestMaxRms: metricValues.rms?.max ?? null,
    },
    gates,
    blocked: blocked.map((gate) => gate.id),
    warnings: warnings.map((gate) => gate.id),
    safety: {
      boundaryOnly: true,
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
  appendAudit({ timestamp, status: doc.status, warnings: doc.warnings, blocked: doc.blocked, startsMicrophone: false, recordsAudio: false });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, boundaryOnly: true, startsMicrophone: false, recordsAudio: false, warningCount: doc.warnings.length, blocked: doc.blocked }, null, 2));
}

main();
