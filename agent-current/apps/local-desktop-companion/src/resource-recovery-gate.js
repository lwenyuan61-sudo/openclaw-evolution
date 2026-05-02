import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const LOG = path.join(STATE, 'resource_monitor_log.jsonl');
const OUT = path.join(STATE, 'desktop_wrapper_resource_recovery_gate_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_resource_recovery_gate_audit.jsonl');

function readJson(rel, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8')); }
  catch (error) { return { ...fallback, _error: `${error.name}: ${error.message}` }; }
}

function readJsonlTail(file, maxBytes = 256 * 1024) {
  try {
    const stat = fs.statSync(file);
    const start = Math.max(0, stat.size - maxBytes);
    const fd = fs.openSync(file, 'r');
    const buffer = Buffer.alloc(stat.size - start);
    fs.readSync(fd, buffer, 0, buffer.length, start);
    fs.closeSync(fd);
    return buffer.toString('utf8').split(/\r?\n/).filter(Boolean).map((line) => {
      try { return JSON.parse(line); } catch { return null; }
    }).filter(Boolean);
  } catch { return []; }
}

function writeJson(file, doc) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
}

function appendAudit(event) {
  fs.mkdirSync(path.dirname(AUDIT), { recursive: true });
  fs.appendFileSync(AUDIT, `${JSON.stringify(event)}\n`, 'utf8');
}

function memoryPressure(entry) {
  return typeof entry.memory?.pressure === 'number' ? entry.memory.pressure : null;
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const resource = readJson('core/resource-state.json', {});
  const response = readJson('state/desktop_wrapper_resource_pressure_response_status.json', {});
  const entries = readJsonlTail(LOG).filter((entry) => entry?.timestamp).slice(-12);
  const warn = resource.policy?.warnMemoryPressure ?? 0.82;
  const recoverBelow = Math.max(0, warn - 0.02);
  const currentPressure = memoryPressure(resource);
  const recent = entries.slice(-5).map((entry) => ({ timestamp: entry.timestamp, level: entry.resourcePressure?.level ?? 'unknown', memoryPressure: memoryPressure(entry) }));
  const okStreak = (() => {
    let count = 0;
    for (let i = entries.length - 1; i >= 0; i -= 1) {
      const level = entries[i].resourcePressure?.level;
      const mem = memoryPressure(entries[i]);
      if (level === 'ok' && typeof mem === 'number' && mem < recoverBelow) count += 1;
      else break;
    }
    return count;
  })();
  const recentWarning = entries.slice(-5).some((entry) => ['warning', 'critical'].includes(entry.resourcePressure?.level) || (typeof memoryPressure(entry) === 'number' && memoryPressure(entry) >= warn));
  const recovered = currentPressure !== null && currentPressure < recoverBelow && okStreak >= 1;
  const stableRecovered = currentPressure !== null && currentPressure < recoverBelow && okStreak >= 3 && !recentWarning;
  const recommendedProfile = stableRecovered ? 'normal-local-first' : recovered ? 'recovery-cooldown' : (resource.resourcePressure?.level === 'warning' ? 'low-memory-safe-mode' : 'normal-local-first-watch-memory');
  const allowed = stableRecovered
    ? ['small-local-cpu', 'read-only-probes', 'bounded-verifiers', 'normal-connector-queue-with-fresh-check']
    : ['small-local-cpu', 'read-only-probes', 'state-summarization', 'policy/connectors-that-do-not-start-organs'];
  const suppressed = stableRecovered
    ? ['paid-api-by-default']
    : ['gpu-heavy', 'memory-heavy', 'camera-capture', 'microphone-recording', 'model-loads', 'dependency-install', 'persistent-new-processes', 'paid-api'];
  const doc = {
    timestamp,
    status: 'ready',
    mode: 'resource-recovery-gate-read-only',
    resourceLevel: resource.resourcePressure?.level ?? 'unknown',
    previousProfile: response.profile ?? 'unknown',
    recommendedProfile,
    thresholds: { warnMemoryPressure: warn, recoverBelow },
    current: {
      memoryPressure: currentPressure,
      memoryUsedMiB: resource.memory?.usedMiB ?? null,
      memoryTotalMiB: resource.memory?.totalMiB ?? null,
      gpuVramUsedMiB: resource.gpus?.[0]?.memoryUsedMiB ?? null,
      workspaceDiskFreeMiB: (resource.disks ?? []).find((item) => item?.isWorkspaceDrive)?.freeMiB ?? null,
    },
    recovery: {
      okStreak,
      recentWarning,
      recovered,
      stableRecovered,
      reason: stableRecovered ? 'hysteresis-clear' : recovered ? 'single-ok-sample-recovery-cooldown' : 'watch-memory',
    },
    recent,
    allowed,
    suppressed,
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
  appendAudit({ timestamp, resourceLevel: doc.resourceLevel, previousProfile: doc.previousProfile, recommendedProfile, okStreak, recentWarning, memoryPressure: currentPressure });
  console.log(JSON.stringify({ ok: true, out: OUT, status: doc.status, recommendedProfile, memoryPressure: currentPressure, okStreak, stableRecovered, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, persistentProcessStarted: false }, null, 2));
}

main();
