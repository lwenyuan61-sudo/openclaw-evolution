import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_voice_vad_baseline_evaluator_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_voice_vad_baseline_evaluator_audit.jsonl');

function readJson(rel, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8')); }
  catch (error) { return { ...fallback, _error: `${error.name}: ${error.message}` }; }
}

function readJsonl(rel) {
  const file = path.join(WORKSPACE, rel);
  if (!fs.existsSync(file)) return [];
  return fs.readFileSync(file, 'utf8').split(/\r?\n/).filter(Boolean).map((line) => {
    try { return JSON.parse(line); } catch { return null; }
  }).filter(Boolean);
}

function writeJson(file, doc) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
}

function appendAudit(event) {
  fs.mkdirSync(path.dirname(AUDIT), { recursive: true });
  fs.appendFileSync(AUDIT, `${JSON.stringify(event)}\n`, 'utf8');
}

function median(values) {
  const xs = values.filter((v) => Number.isFinite(v)).sort((a, b) => a - b);
  if (!xs.length) return null;
  const mid = Math.floor(xs.length / 2);
  return xs.length % 2 ? xs[mid] : (xs[mid - 1] + xs[mid]) / 2;
}

function round(value, digits = 6) {
  return Number.isFinite(value) ? Number(value.toFixed(digits)) : null;
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const resource = readJson('core/resource-state.json', {});
  const runner = readJson('state/desktop_wrapper_voice_vad_measurement_runner_status.json', {});
  const metricsDoc = readJson('state/voice_vad_measurement_metrics.json', {});
  const indicator = readJson('state/voice_listening_indicator.json', {});
  const auditEvents = readJsonl('state/desktop_wrapper_voice_vad_measurement_runner_audit.jsonl');
  const measurementEvents = auditEvents.filter((event) => event.event === 'measurement-finish' && event.status === 'measured-metrics-only');
  const latest = metricsDoc.metrics ?? runner.measurement?.parsed ?? {};
  const resourceOk = resource.resourcePressure?.level === 'ok';
  const indicatorIdle = indicator.state === 'idle' && indicator.recordingNow === false && indicator.alwaysOnMicEnabled === false;
  const retentionSafe = metricsDoc.retention?.rawAudioWrittenToDisk === false && metricsDoc.retention?.rawAudioRetained === false && metricsDoc.retention?.networkUpload === false;
  const latestUsable = latest.ok === true && Number.isFinite(latest.windowCount) && latest.windowCount > 0;
  const samples = latestUsable ? [latest] : [];
  const noiseFloors = samples.map((sample) => sample.thresholdBootstrap?.noiseFloorRmsP20).filter(Number.isFinite);
  const rmsP95s = samples.map((sample) => sample.rms?.p95).filter(Number.isFinite);
  const maxRms = samples.map((sample) => sample.rms?.max).filter(Number.isFinite);
  const candidateCounts = samples.map((sample) => sample.candidateWakeCount).filter(Number.isFinite);
  const totalDuration = samples.reduce((sum, sample) => sum + (Number(sample.durationSeconds) || 0), 0);
  const totalCandidates = candidateCounts.reduce((sum, n) => sum + n, 0);
  const candidateRatePerHour = totalDuration > 0 ? totalCandidates / totalDuration * 3600 : null;
  const gates = [
    { id: 'resource-ok', status: resourceOk ? 'ready' : 'blocked', evidence: resource.resourcePressure?.level ?? 'unknown' },
    { id: 'metrics-present', status: latestUsable ? 'ready' : 'blocked', evidence: { runnerStatus: runner.status, latestUsable, metricsTimestamp: metricsDoc.timestamp ?? null } },
    { id: 'indicator-idle', status: indicatorIdle ? 'ready' : 'blocked', evidence: { state: indicator.state, recordingNow: indicator.recordingNow, alwaysOnMicEnabled: indicator.alwaysOnMicEnabled } },
    { id: 'retention-safe', status: retentionSafe ? 'ready' : 'blocked', evidence: metricsDoc.retention ?? null },
    { id: 'enough-baseline-samples', status: measurementEvents.length >= 3 ? 'ready' : 'warn', evidence: { measurementFinishEvents: measurementEvents.length, target: 3 } },
  ];
  const blocked = gates.filter((gate) => gate.status === 'blocked');
  const warnings = gates.filter((gate) => gate.status === 'warn');
  const evaluator = {
    sampleCount: samples.length,
    auditMeasurementFinishEvents: measurementEvents.length,
    totalDurationSeconds: round(totalDuration, 3),
    aggregate: {
      noiseFloorRmsP20Median: round(median(noiseFloors)),
      rmsP95Median: round(median(rmsP95s)),
      maxRmsMax: round(Math.max(...maxRms), 6),
      totalCandidateWakeCount: totalCandidates,
      candidateRatePerHour: round(candidateRatePerHour, 3),
    },
    recommendation: {
      currentThresholdRms: latest.thresholdBootstrap?.initialThresholdRms ?? null,
      candidateThresholdAdequateForQuietBaseline: latest.candidateWakeCount === 0 && latest.rms?.max < latest.thresholdBootstrap?.initialThresholdRms,
      nextMeasurementNeed: measurementEvents.length >= 3 ? 'enough-short-baselines-for-initial-threshold; next test can be spoken wake phrase' : 'collect at least 3 short quiet-baseline runs before tuning false-positive estimate',
      qualityLimit: 'without dedicated VAD/wake-word engine, this remains an energy/noise-floor bootstrap plus CPU phrase-confirmation path',
    },
  };
  const doc = {
    timestamp,
    status: blocked.length === 0 ? 'ready' : 'blocked',
    mode: 'voice-vad-baseline-evaluator-no-recording',
    evaluator,
    latestMetricsPath: 'state/voice_vad_measurement_metrics.json',
    gates,
    blocked: blocked.map((gate) => gate.id),
    warnings: warnings.map((gate) => gate.id),
    safety: {
      evaluatorOnly: true,
      startsMicrophone: false,
      recordsAudio: false,
      readsRawAudio: false,
      storesRawAudio: false,
      startsPersistentProcess: false,
      externalNetworkWrites: false,
      paidApi: false,
      gpuHeavy: false,
      realPhysicalActuation: false,
    },
  };
  writeJson(OUT, doc);
  appendAudit({ timestamp, status: doc.status, warnings: doc.warnings, blocked: doc.blocked, totalCandidateWakeCount: totalCandidates, startsMicrophone: false });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, evaluatorOnly: true, startsMicrophone: false, recordsAudio: false, totalCandidateWakeCount: totalCandidates, warningCount: doc.warnings.length }, null, 2));
}

main();
