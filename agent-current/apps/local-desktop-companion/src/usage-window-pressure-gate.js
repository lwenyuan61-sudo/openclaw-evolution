import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const WORKSPACE = path.resolve(__dirname, '..', '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_usage_window_pressure_gate_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_usage_window_pressure_gate_audit.jsonl');

function readJson(rel, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8')); }
  catch { return fallback; }
}
function writeJson(file, doc) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
}
function appendAudit(event) {
  fs.mkdirSync(path.dirname(AUDIT), { recursive: true });
  fs.appendFileSync(AUDIT, `${JSON.stringify(event)}\n`, 'utf8');
}
function decide(quota, resource) {
  const weekly = Number(quota.weeklyLeftPercent ?? 0);
  const reserve = Number(quota.weeklyReserveFloorPercent ?? 10);
  const minutes = Number(quota.currentWindowLeftMinutesApprox ?? 999);
  const context = Number(quota.contextUsedPercentApprox ?? 0);
  const profile = resource.final?.effectiveProfile ?? 'unknown';
  const resourceLevel = resource.final?.resourceLevel ?? 'unknown';
  if (weekly <= reserve) return { mode: 'reserve-lock', allowAutonomy: false, reason: 'weekly reserve floor reached' };
  if (minutes <= 30 || context >= 90) return { mode: 'window-context-conserve', allowAutonomy: true, reason: 'current window/context pressure high' };
  if (resourceLevel === 'warning' || String(profile).includes('recovery') || String(profile).includes('low-memory')) return { mode: 'resource-conserve', allowAutonomy: true, reason: 'resource recovery or warning profile active' };
  if (weekly < 35) return { mode: 'measured', allowAutonomy: true, reason: 'weekly quota below fast-normal band' };
  return { mode: 'fast-normal', allowAutonomy: true, reason: 'quota/resource window acceptable' };
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const quota = readJson('state/codex_usage_governor_status.json', {});
  const resource = readJson('state/desktop_wrapper_resource_gate_serialized_refresh_status.json', {});
  const decision = decide(quota, resource);
  const doc = {
    timestamp,
    status: 'ready',
    mode: 'usage-window-pressure-gate-local-only',
    decision,
    quota: {
      weeklyLeftPercent: quota.weeklyLeftPercent ?? null,
      reserveFloor: quota.weeklyReserveFloorPercent ?? 10,
      currentWindowLeftMinutesApprox: quota.currentWindowLeftMinutesApprox ?? null,
      contextUsedPercentApprox: quota.contextUsedPercentApprox ?? null,
    },
    resource: {
      level: resource.final?.resourceLevel ?? null,
      memoryPressure: resource.final?.memoryPressure ?? null,
      effectiveProfile: resource.final?.effectiveProfile ?? null,
    },
    allowedWork: decision.mode === 'reserve-lock' ? [] : [
      'direct Lee request',
      'urgent recovery',
      'tiny local state writeback',
      'single targeted syntax/run check',
      'quiet read-only status verification',
    ],
    deniedWork: [
      'full regression matrix unless Lee asks or window resets',
      'subagents/acp sessions',
      'browser research loops',
      'large file reads or high-token summarization',
      'GPU-heavy or model-load work',
      'real mic/camera/organ calibration',
      'paid API or external/public actions',
    ],
    safety: {
      localPolicyOnly: true,
      startsMicrophone: false,
      startsCamera: false,
      startsGpuWork: false,
      dependencyInstall: false,
      externalNetworkWrites: false,
      sendsMessages: false,
      publicPosting: false,
      financialCommitment: false,
      paidApi: false,
      persistentProcessStarted: false,
      realPhysicalActuation: false,
    },
    auditPath: path.relative(WORKSPACE, AUDIT),
  };
  writeJson(OUT, doc);
  appendAudit({ timestamp, status: doc.status, mode: decision.mode, weekly: doc.quota.weeklyLeftPercent, minutes: doc.quota.currentWindowLeftMinutesApprox, context: doc.quota.contextUsedPercentApprox });
  console.log(JSON.stringify({ ok: true, out: OUT, status: doc.status, decisionMode: decision.mode, allowAutonomy: decision.allowAutonomy, weeklyLeftPercent: doc.quota.weeklyLeftPercent, currentWindowLeftMinutesApprox: doc.quota.currentWindowLeftMinutesApprox, contextUsedPercentApprox: doc.quota.contextUsedPercentApprox, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, externalNetworkWrites: false, sendsMessages: false, publicPosting: false, financialCommitment: false, paidApi: false, persistentProcessStarted: false }, null, 2));
}

main();
