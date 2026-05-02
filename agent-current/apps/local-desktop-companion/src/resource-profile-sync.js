import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_resource_profile_sync_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_resource_profile_sync_audit.jsonl');

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

function unique(items) { return [...new Set(items.filter(Boolean))]; }

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const resource = readJson('core/resource-state.json', {});
  const budget = readJson('state/desktop_wrapper_resource_budget_gate_status.json', {});
  const trend = readJson('state/desktop_wrapper_resource_trend_gate_status.json', {});
  const response = readJson('state/desktop_wrapper_resource_pressure_response_status.json', {});
  const recovery = readJson('state/desktop_wrapper_resource_recovery_gate_status.json', {});
  const pressureLevel = resource.resourcePressure?.level ?? 'unknown';
  const recoveryProfile = recovery.recommendedProfile ?? 'unknown';
  const responseProfile = response.profile ?? 'unknown';
  const warnings = unique([...(budget.warnings ?? []), ...(trend.warnings ?? []), ...(response.warnings ?? [])]);
  const blocked = unique([...(budget.blocked ?? []), ...(trend.blocked ?? []), ...(response.blocked ?? []), ...(recovery.blocked ?? [])]);
  let effectiveProfile = responseProfile;
  let reason = 'pressure-response-profile';
  if (blocked.length) {
    effectiveProfile = 'protective-stop';
    reason = 'blocked-gates-present';
  } else if (pressureLevel === 'warning' || responseProfile === 'low-memory-safe-mode') {
    effectiveProfile = 'low-memory-safe-mode';
    reason = 'active-warning';
  } else if (recoveryProfile === 'recovery-cooldown' || recoveryProfile === 'normal-local-first-watch-memory') {
    effectiveProfile = recoveryProfile;
    reason = 'recovery-hysteresis';
  }
  const allowHeavy = effectiveProfile === 'normal-local-first' && pressureLevel === 'ok' && warnings.length === 0;
  const watchMemory = effectiveProfile === 'normal-local-first-watch-memory' || effectiveProfile === 'recovery-cooldown';
  const allowed = allowHeavy
    ? ['small-local-cpu', 'read-only-probes', 'bounded-verifiers', 'normal-connector-queue-with-fresh-check']
    : watchMemory
      ? ['small-local-cpu', 'read-only-probes', 'bounded-verifiers', 'app/product hardening without organs', 'normal queue only after fresh resource recheck']
      : ['small-local-cpu', 'read-only-probes', 'state-summarization', 'policy/connectors-that-do-not-start-organs'];
  const suppressed = allowHeavy
    ? ['paid-api-by-default']
    : watchMemory
      ? ['gpu-heavy-without-fresh-check', 'memory-heavy-without-fresh-check', 'camera/microphone without explicit fresh recovery', 'dependency-install', 'persistent-new-processes', 'paid-api']
      : ['gpu-heavy', 'memory-heavy', 'camera-capture', 'microphone-recording', 'model-loads', 'dependency-install', 'persistent-new-processes', 'paid-api'];
  const doc = {
    timestamp,
    status: blocked.length ? 'blocked' : 'ready',
    mode: 'resource-profile-sync-read-only',
    pressureLevel,
    effectiveProfile,
    reason,
    inputs: {
      budget: { status: budget.status ?? null, warnings: budget.warnings ?? [], blocked: budget.blocked ?? [] },
      trend: { status: trend.status ?? null, warnings: trend.warnings ?? [], blocked: trend.blocked ?? [], recommendedMode: trend.recommendedMode ?? null },
      response: { status: response.status ?? null, profile: responseProfile, warnings: response.warnings ?? [], blocked: response.blocked ?? [] },
      recovery: { status: recovery.status ?? null, recommendedProfile: recoveryProfile, recovery: recovery.recovery ?? {} },
    },
    current: {
      memoryPressure: resource.memory?.pressure ?? null,
      memoryUsedMiB: resource.memory?.usedMiB ?? null,
      memoryTotalMiB: resource.memory?.totalMiB ?? null,
      gpuVramUsedMiB: resource.gpus?.[0]?.memoryUsedMiB ?? null,
      workspaceDiskFreeMiB: (resource.disks ?? []).find((item) => item?.isWorkspaceDrive)?.freeMiB ?? null,
    },
    warnings,
    blocked,
    policy: {
      allowed,
      suppressed,
      requireFreshResourceCheckBefore: ['camera-capture', 'microphone-recording', 'model-loads', 'dependency-install', 'persistent-new-processes', 'gpu-heavy', 'memory-heavy'],
      doesNotMutateControlState: true,
    },
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
  appendAudit({ timestamp, status: doc.status, pressureLevel, effectiveProfile, reason, warnings, blocked });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, effectiveProfile, reason, warnings, blocked, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, persistentProcessStarted: false }, null, 2));
}

main();
