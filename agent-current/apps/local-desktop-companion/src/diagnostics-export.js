import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const CORE = path.join(WORKSPACE, 'core');
const OUT_DIR = path.join(STATE, 'diagnostics_export');
const LATEST = path.join(OUT_DIR, 'latest.json');
const SUMMARY = path.join(STATE, 'desktop_wrapper_diagnostics_status.json');

const FILES = [
  'state/app_shell_status.json',
  'state/app_control_schema.json',
  'state/app_control_state.json',
  'state/service_health_status.json',
  'state/service_control_schema.json',
  'state/physical_actuation_allowlist.json',
  'state/physical_actuation_simulator_status.json',
  'state/voice_calibration_status.json',
  'state/voice_manual_calibration_runner_status.json',
  'state/desktop_app_wrapper_status.json',
  'state/desktop_wrapper_control_preview_status.json',
  'state/desktop_wrapper_control_endpoint_status.json',
  'state/consistency_report.json',
  'core/resource-state.json',
  'core/multi-agent-mode.json',
  'apps/local-desktop-companion/wrapper-manifest.json',
  'apps/local-desktop-companion/package.json',
];

const REDACT_KEYS = new Set(['token', 'secret', 'password', 'apiKey', 'api_key', 'authorization', 'cookie']);

function nowIso() {
  return new Date().toISOString();
}

function sha256(text) {
  return crypto.createHash('sha256').update(text).digest('hex');
}

function exists(file) {
  try { return fs.existsSync(file); } catch { return false; }
}

function readText(abs) {
  return fs.readFileSync(abs, 'utf8');
}

function readJson(abs) {
  return JSON.parse(readText(abs));
}

function redact(value) {
  if (Array.isArray(value)) return value.map(redact);
  if (!value || typeof value !== 'object') return value;
  const out = {};
  for (const [key, val] of Object.entries(value)) {
    const normalized = key.toLowerCase();
    if ([...REDACT_KEYS].some((needle) => normalized.includes(needle))) {
      out[key] = '[REDACTED]';
    } else {
      out[key] = redact(val);
    }
  }
  return out;
}

function collectFile(rel) {
  const abs = path.join(WORKSPACE, rel);
  if (!exists(abs)) {
    return { path: rel, exists: false, status: 'missing' };
  }
  const text = readText(abs);
  const stat = fs.statSync(abs);
  let json = null;
  let parseError = null;
  try {
    json = redact(JSON.parse(text));
  } catch (error) {
    parseError = `${error.name}: ${error.message}`;
  }
  return {
    path: rel,
    exists: true,
    status: parseError ? 'non-json-or-invalid' : 'ok',
    bytes: Buffer.byteLength(text, 'utf8'),
    mtime: stat.mtime.toISOString(),
    sha256: sha256(text),
    parseError,
    json,
  };
}

function buildDiagnostics() {
  const collected = FILES.map(collectFile);
  const byPath = Object.fromEntries(collected.map((item) => [item.path, item]));
  const app = byPath['state/app_shell_status.json']?.json ?? {};
  const resource = byPath['core/resource-state.json']?.json ?? {};
  const consistency = byPath['state/consistency_report.json']?.json ?? {};
  const cards = Array.isArray(app.cards) ? app.cards : [];
  const warnings = [];
  const errors = [];
  if (consistency.status && consistency.status !== 'ok') warnings.push('consistency-not-ok');
  for (const item of collected) {
    if (!item.exists) warnings.push(`missing:${item.path}`);
    if (item.parseError && item.path.endsWith('.json')) warnings.push(`invalid-json:${item.path}`);
  }
  return {
    timestamp: nowIso(),
    status: errors.length ? 'error' : warnings.length ? 'warn' : 'ok',
    mode: 'local-redacted-diagnostics-export',
    workspace: WORKSPACE,
    summary: {
      fileCount: collected.length,
      presentCount: collected.filter((item) => item.exists).length,
      appCardCount: cards.length,
      appStatus: app.status ?? null,
      resourcePressure: resource.resourcePressure ?? null,
      consistencyStatus: consistency.status ?? null,
      warningCount: warnings.length,
      errorCount: errors.length,
    },
    warnings,
    errors,
    files: collected,
    privacy: {
      redactedKeys: Array.from(REDACT_KEYS),
      rawAudioIncluded: false,
      screenshotsIncluded: false,
      browserCookiesIncluded: false,
      externalNetworkWrites: false,
      localOnly: true,
    },
    safety: {
      externalNetworkWrites: false,
      persistentInstall: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
      mutatesRuntimeControlState: false,
    },
  };
}

function main() {
  const doc = buildDiagnostics();
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(LATEST, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
  const summary = {
    timestamp: doc.timestamp,
    status: doc.status,
    mode: doc.mode,
    latestPath: LATEST,
    fileCount: doc.summary.fileCount,
    presentCount: doc.summary.presentCount,
    warningCount: doc.summary.warningCount,
    errorCount: doc.summary.errorCount,
    appCardCount: doc.summary.appCardCount,
    privacy: doc.privacy,
    safety: doc.safety,
  };
  fs.writeFileSync(SUMMARY, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: doc.status !== 'error', summary, latestPath: LATEST }, null, 2));
}

main();
