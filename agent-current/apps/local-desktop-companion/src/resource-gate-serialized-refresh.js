import fs from 'node:fs';
import path from 'node:path';
import childProcess from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_resource_gate_serialized_refresh_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_resource_gate_serialized_refresh_audit.jsonl');
const NODE = process.execPath;
const PYTHON = process.platform === 'win32' ? 'python' : 'python3';

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

function parseLastJson(text) {
  const trimmed = String(text ?? '').trim();
  if (!trimmed) return null;
  try { return JSON.parse(trimmed); } catch {}
  const start = trimmed.lastIndexOf('\n{');
  if (start >= 0) {
    try { return JSON.parse(trimmed.slice(start + 1)); } catch {}
  }
  return null;
}

function runStep(step) {
  const started = Date.now();
  const result = childProcess.spawnSync(step.command, step.args, {
    cwd: WORKSPACE,
    encoding: 'utf8',
    windowsHide: true,
    timeout: step.timeoutMs ?? 30000,
  });
  const parsed = parseLastJson(result.stdout);
  return {
    id: step.id,
    status: result.status,
    signal: result.signal,
    durationMs: Date.now() - started,
    ok: result.status === 0,
    parsed,
    stderrTail: (result.stderr ?? '').slice(-500),
  };
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const steps = [
    { id: 'resource-monitor', command: PYTHON, args: ['core\\scripts\\resource_monitor.py'], timeoutMs: 30000 },
    { id: 'budget-gate', command: NODE, args: ['apps/local-desktop-companion/src/resource-budget-gate.js'] },
    { id: 'trend-gate', command: NODE, args: ['apps/local-desktop-companion/src/resource-trend-gate.js'] },
    { id: 'recovery-gate', command: NODE, args: ['apps/local-desktop-companion/src/resource-recovery-gate.js'] },
    { id: 'profile-sync', command: NODE, args: ['apps/local-desktop-companion/src/resource-profile-sync.js'] },
    { id: 'sensitive-preflight', command: NODE, args: ['apps/local-desktop-companion/src/sensitive-action-resource-preflight.js'] },
    { id: 'consistency-audit', command: NODE, args: ['apps/local-desktop-companion/src/resource-gate-consistency-audit.js'] },
  ];
  const results = [];
  for (const step of steps) {
    const result = runStep(step);
    results.push(result);
    if (!result.ok) break;
  }
  const finalAudit = readJson('state/desktop_wrapper_resource_gate_consistency_audit_status.json', {});
  const profile = readJson('state/desktop_wrapper_resource_profile_sync_status.json', {});
  const resource = readJson('core/resource-state.json', {});
  const failed = results.filter((item) => !item.ok);
  const inconsistencies = finalAudit.inconsistencies ?? [];
  const doc = {
    timestamp,
    status: failed.length === 0 && inconsistencies.length === 0 ? 'ready' : 'needs-attention',
    mode: 'resource-gate-serialized-refresh-local-cpu',
    steps: results,
    final: {
      resourceLevel: resource.resourcePressure?.level ?? 'unknown',
      memoryPressure: resource.memory?.pressure ?? null,
      effectiveProfile: profile.effectiveProfile ?? null,
      consistencyRecommendation: finalAudit.recommendation ?? null,
      inconsistencies,
      requiresRerunOrder: finalAudit.requiresRerunOrder ?? null,
    },
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      localCpuOnly: true,
      mutatesOnlyResourceState: true,
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
  appendAudit({ timestamp, status: doc.status, stepCount: results.length, failedIds: failed.map((item) => item.id), final: doc.final });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, stepCount: results.length, final: doc.final, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, persistentProcessStarted: false }, null, 2));
}

main();
