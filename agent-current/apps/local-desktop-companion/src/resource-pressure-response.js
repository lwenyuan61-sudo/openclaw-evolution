import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_resource_pressure_response_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_resource_pressure_response_audit.jsonl');

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

function chooseProfile(resourceLevel, memoryPressure) {
  if (resourceLevel === 'critical' || memoryPressure >= 0.92) return 'protective-stop';
  if (resourceLevel === 'warning' || memoryPressure >= 0.82) return 'low-memory-safe-mode';
  return 'normal-local-first';
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const resource = readJson('core/resource-state.json', {});
  const budget = readJson('state/desktop_wrapper_resource_budget_gate_status.json', {});
  const trend = readJson('state/desktop_wrapper_resource_trend_gate_status.json', {});
  const control = readJson('state/app_control_state.json', {});
  const indicator = readJson('state/voice_listening_indicator.json', {});
  const cameraIndicator = readJson('state/camera_perception_indicator.json', {});
  const resourceLevel = resource.resourcePressure?.level ?? 'unknown';
  const memoryPressure = typeof resource.memory?.pressure === 'number' ? resource.memory.pressure : null;
  const profile = chooseProfile(resourceLevel, memoryPressure ?? 0);
  const recommendations = {
    'normal-local-first': {
      allowed: ['small-local-cpu', 'read-only-probes', 'bounded-verifiers', 'large-disk-writes-with-fresh-check'],
      suppressed: ['paid-api-by-default'],
      cadence: 'normal-autonomy-cadence',
    },
    'low-memory-safe-mode': {
      allowed: ['small-local-cpu', 'read-only-probes', 'state-summarization', 'policy/connectors-that-do-not-start-organs'],
      suppressed: ['gpu-heavy', 'memory-heavy', 'camera-capture', 'microphone-recording', 'model-loads', 'dependency-install', 'persistent-new-processes', 'paid-api'],
      cadence: 'continue-wakes-but-only-lightweight-actions',
    },
    'protective-stop': {
      allowed: ['read-only-resource-checks', 'cleanup-proposals', 'state-compression-proposals'],
      suppressed: ['all-heavy-work', 'camera-capture', 'microphone-recording', 'model-loads', 'dependency-install', 'persistent-new-processes', 'large-disk-writes', 'paid-api'],
      cadence: 'pause-autonomous-upgrades-until-resource-recovery',
    },
  }[profile];
  const unsafeActive = [];
  if (indicator.recordingNow === true || indicator.alwaysOnMicEnabled === true) unsafeActive.push('microphone-active');
  if (cameraIndicator.capturingNow === true || cameraIndicator.cameraActive === true) unsafeActive.push('camera-active');
  if (control.pauseAll === true) unsafeActive.push('pause-all-active');
  const blocked = [];
  if (unsafeActive.includes('microphone-active') || unsafeActive.includes('camera-active')) blocked.push('organ-active-during-resource-pressure');
  if (profile === 'protective-stop') blocked.push('resource-critical');
  const warnings = [];
  if (profile === 'low-memory-safe-mode') warnings.push('low-memory-safe-mode-active');
  if (trend.trends?.memory?.direction === 'rising') warnings.push('memory-trend-rising');
  const doc = {
    timestamp,
    status: blocked.length ? 'blocked' : warnings.length ? 'warning' : 'ready',
    mode: 'resource-pressure-response-read-only',
    profile,
    current: {
      resourceLevel,
      memoryPressure,
      memoryUsedMiB: resource.memory?.usedMiB ?? null,
      memoryTotalMiB: resource.memory?.totalMiB ?? null,
      gpuVramUsedMiB: resource.gpus?.[0]?.memoryUsedMiB ?? null,
      workspaceDiskFreeMiB: (resource.disks ?? []).find((item) => item?.isWorkspaceDrive)?.freeMiB ?? null,
    },
    recommendations,
    budget: {
      status: budget.status ?? null,
      warnings: budget.warnings ?? [],
      blocked: budget.blocked ?? [],
      allowedWorkModes: budget.allowedWorkModes ?? {},
    },
    trend: {
      status: trend.status ?? null,
      warnings: trend.warnings ?? [],
      blocked: trend.blocked ?? [],
      memoryDirection: trend.trends?.memory?.direction ?? null,
      memoryDelta: trend.trends?.memory?.delta ?? null,
    },
    unsafeActive,
    warnings: [...new Set(warnings)],
    blocked,
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      readOnly: true,
      mutatesControlState: false,
      startsMicrophone: false,
      startsCamera: false,
      startsGpuWork: false,
      allocatesLargeMemory: false,
      writesLargeFiles: false,
      dependencyInstall: false,
      externalNetworkWrites: false,
      paidApi: false,
      persistentProcessStarted: false,
      realPhysicalActuation: false,
    },
  };
  writeJson(OUT, doc);
  appendAudit({ timestamp, status: doc.status, profile, resourceLevel, memoryPressure, warnings: doc.warnings, blocked: doc.blocked });
  console.log(JSON.stringify({ ok: doc.status !== 'blocked', out: OUT, status: doc.status, profile, warnings: doc.warnings, blocked: doc.blocked, startsMicrophone: false, startsCamera: false, startsGpuWork: false, persistentProcessStarted: false }, null, 2));
}

main();
