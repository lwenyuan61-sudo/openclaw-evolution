import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const LOG = path.join(STATE, 'resource_monitor_log.jsonl');
const OUT = path.join(STATE, 'desktop_wrapper_resource_trend_gate_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_resource_trend_gate_audit.jsonl');

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

function pressureOf(entry, key) {
  if (key === 'memory') return typeof entry.memory?.pressure === 'number' ? entry.memory.pressure : null;
  if (key === 'gpu') return typeof entry.gpus?.[0]?.memoryPressure === 'number' ? entry.gpus[0].memoryPressure : null;
  if (key === 'disk') {
    const disks = Array.isArray(entry.disks) ? entry.disks : [];
    const workspaceDisk = disks.find((item) => item?.isWorkspaceDrive) ?? disks[0];
    return typeof workspaceDisk?.pressure === 'number' ? workspaceDisk.pressure : null;
  }
  return null;
}

function trend(entries, key) {
  const points = entries.map((entry) => ({ timestamp: entry.timestamp, value: pressureOf(entry, key) })).filter((p) => typeof p.value === 'number');
  const recent = points.slice(-8);
  if (recent.length < 2) return { sampleCount: recent.length, latest: recent.at(-1)?.value ?? null, delta: null, direction: 'unknown' };
  const first = recent[0].value;
  const latest = recent.at(-1).value;
  const delta = Number((latest - first).toFixed(4));
  const direction = delta > 0.01 ? 'rising' : delta < -0.01 ? 'falling' : 'flat';
  return { sampleCount: recent.length, first, latest, delta, direction };
}

function consecutiveLevels(entries, level) {
  let count = 0;
  for (let i = entries.length - 1; i >= 0; i -= 1) {
    if (entries[i]?.resourcePressure?.level === level) count += 1;
    else break;
  }
  return count;
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const current = readJson('core/resource-state.json', {});
  const budget = readJson('state/desktop_wrapper_resource_budget_gate_status.json', {});
  const entries = readJsonlTail(LOG).filter((entry) => entry?.timestamp).slice(-32);
  const warnMemory = current.policy?.warnMemoryPressure ?? 0.82;
  const criticalMemory = current.policy?.criticalMemoryPressure ?? 0.92;
  const memoryTrend = trend(entries, 'memory');
  const gpuTrend = trend(entries, 'gpu');
  const diskTrend = trend(entries, 'disk');
  const currentLevel = current.resourcePressure?.level ?? 'unknown';
  const warningStreak = consecutiveLevels(entries, 'warning');
  const criticalStreak = consecutiveLevels(entries, 'critical');
  const latestMemory = current.memory?.pressure ?? memoryTrend.latest;
  const warnings = [];
  const blocked = [];
  if (currentLevel === 'critical' || criticalStreak > 0) blocked.push('resource-critical');
  if (currentLevel === 'warning') warnings.push('resource-warning');
  if (typeof latestMemory === 'number' && latestMemory >= warnMemory) warnings.push('memory-over-warning');
  if (typeof latestMemory === 'number' && latestMemory >= criticalMemory) blocked.push('memory-over-critical');
  if (memoryTrend.direction === 'rising' && typeof latestMemory === 'number' && latestMemory > warnMemory - 0.03) warnings.push('memory-rising-near-warning');
  const status = blocked.length ? 'blocked' : warnings.length ? 'warning' : 'ready';
  const doc = {
    timestamp,
    status,
    mode: 'resource-trend-gate-read-only',
    window: { maxEntries: 32, parsedEntries: entries.length, trendSamples: 8 },
    current: {
      resourceLevel: currentLevel,
      memoryPressure: latestMemory,
      memoryUsedMiB: current.memory?.usedMiB ?? null,
      memoryTotalMiB: current.memory?.totalMiB ?? null,
      gpuVramUsedMiB: current.gpus?.[0]?.memoryUsedMiB ?? null,
      workspaceDiskFreeMiB: (current.disks ?? []).find((item) => item?.isWorkspaceDrive)?.freeMiB ?? null,
    },
    trends: { memory: memoryTrend, gpu: gpuTrend, workspaceDisk: diskTrend },
    streaks: { warning: warningStreak, critical: criticalStreak },
    budgetGate: { status: budget.status ?? null, recommendedMode: budget.recommendedMode ?? null, allowedWorkModes: budget.allowedWorkModes ?? {} },
    warnings: [...new Set(warnings)],
    blocked: [...new Set(blocked)],
    recommendedMode: blocked.length ? 'pause-heavy-work-and-free-resources' : warnings.length ? 'small-local-cpu-only-until-memory-drops' : 'normal-local-cpu-first',
    policyEffect: {
      suppressGpuHeavy: blocked.length > 0 || warnings.length > 0,
      suppressMemoryHeavy: blocked.length > 0 || warnings.includes('memory-over-warning') || warnings.includes('memory-rising-near-warning'),
      suppressLargeDiskWrites: blocked.length > 0,
      keepPaidApiOff: true,
    },
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      readOnly: true,
      startsGpuWork: false,
      allocatesLargeMemory: false,
      writesLargeFiles: false,
      externalNetworkWrites: false,
      paidApi: false,
      persistentProcessStarted: false,
    },
  };
  writeJson(OUT, doc);
  appendAudit({ timestamp, status, currentLevel, warnings: doc.warnings, blocked: doc.blocked, memoryTrend, recommendedMode: doc.recommendedMode });
  console.log(JSON.stringify({ ok: status !== 'blocked', out: OUT, status, currentLevel, warnings: doc.warnings, blocked: doc.blocked, recommendedMode: doc.recommendedMode, suppressGpuHeavy: doc.policyEffect.suppressGpuHeavy, suppressMemoryHeavy: doc.policyEffect.suppressMemoryHeavy }, null, 2));
}

main();
