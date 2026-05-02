import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_resource_budget_gate_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_resource_budget_gate_audit.jsonl');

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

function ageSeconds(iso) {
  const t = Date.parse(iso ?? '');
  if (!Number.isFinite(t)) return null;
  return Math.max(0, Math.round((Date.now() - t) / 1000));
}

function gate(id, status, evidence, action = null) {
  return { id, status, evidence, ...(action ? { action } : {}) };
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const resource = readJson('core/resource-state.json', {});
  const policy = resource.policy ?? {};
  const pressure = resource.resourcePressure ?? {};
  const gpu = Array.isArray(resource.gpus) ? resource.gpus[0] : null;
  const memory = resource.memory ?? {};
  const disks = Array.isArray(resource.disks) ? resource.disks : [];
  const workspaceDisk = disks.find((item) => item?.isWorkspaceDrive) ?? disks[0] ?? null;
  const freshnessAgeSeconds = ageSeconds(resource.timestamp);
  const memoryPressure = typeof memory.pressure === 'number' ? memory.pressure : null;
  const diskFreeMiB = typeof workspaceDisk?.freeMiB === 'number' ? workspaceDisk.freeMiB : null;
  const diskPressure = typeof workspaceDisk?.pressure === 'number' ? workspaceDisk.pressure : null;
  const gpuPressure = typeof gpu?.memoryPressure === 'number' ? gpu.memoryPressure : null;
  const warnMemory = policy.warnMemoryPressure ?? 0.82;
  const criticalMemory = policy.criticalMemoryPressure ?? 0.92;
  const warnDiskPressure = policy.warnDiskPressure ?? 0.90;
  const criticalDiskPressure = policy.criticalDiskPressure ?? 0.95;
  const warnDiskFreeMiB = policy.warnDiskFreeMiB ?? 20480;
  const criticalDiskFreeMiB = policy.criticalDiskFreeMiB ?? 10240;
  const gates = [
    gate('resource-snapshot-fresh', freshnessAgeSeconds !== null && freshnessAgeSeconds <= 15 * 60 ? 'ready' : 'warning', { timestamp: resource.timestamp ?? null, ageSeconds: freshnessAgeSeconds }, 'refresh resource_monitor before heavy work'),
    gate('gpu-vram-headroom', pressure.components?.gpu?.level === 'ok' ? 'ready' : pressure.components?.gpu?.level === 'warning' ? 'warning' : 'blocked', { name: gpu?.name ?? null, usedMiB: gpu?.memoryUsedMiB ?? null, totalMiB: gpu?.memoryTotalMiB ?? null, freeMiB: gpu?.memoryFreeMiB ?? null, pressure: gpuPressure }),
    gate('ram-headroom', memoryPressure !== null && memoryPressure < criticalMemory ? (memoryPressure >= warnMemory ? 'warning' : 'ready') : 'blocked', { usedMiB: memory.usedMiB ?? null, totalMiB: memory.totalMiB ?? null, availableMiB: memory.availableMiB ?? null, pressure: memoryPressure, warnAt: warnMemory, criticalAt: criticalMemory }, 'avoid spawning memory-heavy jobs when warning'),
    gate('workspace-disk-headroom', diskFreeMiB !== null && diskPressure !== null && diskFreeMiB >= criticalDiskFreeMiB && diskPressure < criticalDiskPressure ? (diskFreeMiB < warnDiskFreeMiB || diskPressure >= warnDiskPressure ? 'warning' : 'ready') : 'blocked', { root: workspaceDisk?.root ?? null, freeMiB: diskFreeMiB, usedPercent: workspaceDisk?.usedPercent ?? null, pressure: diskPressure, warnFreeMiB: warnDiskFreeMiB, criticalFreeMiB: criticalDiskFreeMiB }, 'clean/compress artifacts before large writes'),
  ];
  const blocked = gates.filter((item) => item.status === 'blocked');
  const warnings = gates.filter((item) => item.status === 'warning');
  const level = blocked.length ? 'blocked' : warnings.length ? 'warning' : 'ready';
  const doc = {
    timestamp,
    status: level,
    mode: 'resource-budget-gate-read-only',
    resourceLevel: pressure.level ?? 'unknown',
    gates,
    blocked: blocked.map((item) => item.id),
    warnings: warnings.map((item) => item.id),
    allowedWorkModes: {
      smallLocalCpu: blocked.length === 0,
      gpuHeavy: blocked.length === 0 && warnings.length === 0 && pressure.gpuAccelerationAllowed === true,
      memoryHeavy: blocked.length === 0 && !warnings.some((item) => item.id === 'ram-headroom'),
      largeDiskWrites: blocked.length === 0 && !warnings.some((item) => item.id === 'workspace-disk-headroom'),
      paidApi: false,
    },
    recommendedMode: blocked.length ? 'stop-heavy-work-and-free-resources' : warnings.length ? 'small-local-cpu-only-and-avoid-heavy-jobs' : 'small-local-cpu-first-heavy-jobs-allowed-with-fresh-check',
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
  appendAudit({ timestamp, status: doc.status, resourceLevel: doc.resourceLevel, blocked: doc.blocked, warnings: doc.warnings, allowedWorkModes: doc.allowedWorkModes });
  console.log(JSON.stringify({ ok: doc.status !== 'blocked', out: OUT, status: doc.status, resourceLevel: doc.resourceLevel, warnings: doc.warnings, blocked: doc.blocked, gpuHeavyAllowed: doc.allowedWorkModes.gpuHeavy, memoryHeavyAllowed: doc.allowedWorkModes.memoryHeavy, largeDiskWritesAllowed: doc.allowedWorkModes.largeDiskWrites }, null, 2));
}

main();
