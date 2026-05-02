import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_resource_gate_consistency_audit_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_resource_gate_consistency_audit_audit.jsonl');
const MAX_SKEW_SECONDS = 300;

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

function ts(rel, doc) {
  const parsed = Date.parse(doc.timestamp ?? '');
  return Number.isFinite(parsed) ? { rel, timestamp: doc.timestamp, epoch: parsed } : { rel, timestamp: doc.timestamp ?? null, epoch: null };
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const docs = {
    resource: readJson('core/resource-state.json', {}),
    budget: readJson('state/desktop_wrapper_resource_budget_gate_status.json', {}),
    trend: readJson('state/desktop_wrapper_resource_trend_gate_status.json', {}),
    recovery: readJson('state/desktop_wrapper_resource_recovery_gate_status.json', {}),
    profile: readJson('state/desktop_wrapper_resource_profile_sync_status.json', {}),
    sensitive: readJson('state/desktop_wrapper_sensitive_action_resource_preflight_status.json', {}),
  };
  const timestamps = Object.entries(docs).map(([rel, doc]) => ts(rel, doc));
  const validEpochs = timestamps.map((item) => item.epoch).filter((item) => typeof item === 'number');
  const skewSeconds = validEpochs.length ? Math.round((Math.max(...validEpochs) - Math.min(...validEpochs)) / 1000) : null;
  const resourceLevel = docs.resource.resourcePressure?.level ?? 'unknown';
  const profileLevel = docs.profile.pressureLevel ?? 'unknown';
  const sensitiveLevel = docs.sensitive.pressureLevel ?? 'unknown';
  const profileName = docs.profile.effectiveProfile ?? 'unknown';
  const sensitiveProfile = docs.sensitive.effectiveProfile ?? 'unknown';
  const inconsistencies = [];
  if (profileLevel !== 'unknown' && profileLevel !== resourceLevel) inconsistencies.push('profile-pressure-level-mismatch');
  if (sensitiveLevel !== 'unknown' && sensitiveLevel !== resourceLevel) inconsistencies.push('sensitive-pressure-level-mismatch');
  if (sensitiveProfile !== 'unknown' && sensitiveProfile !== profileName) inconsistencies.push('sensitive-profile-stale');
  if (skewSeconds !== null && skewSeconds > MAX_SKEW_SECONDS) inconsistencies.push('timestamp-skew-too-large');
  const requiresRerunOrder = inconsistencies.length > 0;
  const rerunOrder = [
    'python core\\scripts\\resource_monitor.py',
    'node apps\\local-desktop-companion\\src\\resource-budget-gate.js',
    'node apps\\local-desktop-companion\\src\\resource-trend-gate.js',
    'node apps\\local-desktop-companion\\src\\resource-recovery-gate.js',
    'node apps\\local-desktop-companion\\src\\resource-profile-sync.js',
    'node apps\\local-desktop-companion\\src\\sensitive-action-resource-preflight.js',
  ];
  const doc = {
    timestamp,
    status: 'ready',
    mode: 'resource-gate-consistency-audit-read-only',
    resourceLevel,
    profileName,
    sensitiveProfile,
    timestampSkewSeconds: skewSeconds,
    maxSkewSeconds: MAX_SKEW_SECONDS,
    timestamps,
    inconsistencies,
    requiresRerunOrder,
    rerunOrder,
    recommendation: requiresRerunOrder ? 'serialize-resource-gates-before-sensitive-preflight' : 'resource-gates-consistent',
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
  appendAudit({ timestamp, status: doc.status, inconsistencies, requiresRerunOrder, resourceLevel, profileName, sensitiveProfile, timestampSkewSeconds: skewSeconds });
  console.log(JSON.stringify({ ok: true, out: OUT, status: doc.status, inconsistencies, requiresRerunOrder, resourceLevel, profileName, sensitiveProfile, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, persistentProcessStarted: false }, null, 2));
}

main();
