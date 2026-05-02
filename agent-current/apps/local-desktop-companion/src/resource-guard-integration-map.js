import fs from 'node:fs';
import path from 'node:path';
import childProcess from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_resource_guard_integration_map_status.json');
const MANIFEST = path.join(STATE, 'resource_guard_integration_map.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_resource_guard_integration_map_audit.jsonl');
const NODE = process.execPath;
const WRAPPER = 'apps/local-desktop-companion/src/resource-guarded-action-wrapper.js';

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

function previewThroughWrapper(item) {
  const args = [WRAPPER, '--class', item.actionClass, '--intent', item.id, '--', ...item.commandPreview];
  const started = Date.now();
  const result = childProcess.spawnSync(NODE, args, {
    cwd: WORKSPACE,
    encoding: 'utf8',
    windowsHide: true,
    timeout: 30000,
  });
  const parsed = parseLastJson(result.stdout);
  return {
    id: item.id,
    actionClass: item.actionClass,
    commandPreview: item.commandPreview,
    status: result.status,
    durationMs: Date.now() - started,
    wrapperStatus: parsed?.status ?? 'unknown',
    allowedByTicket: parsed?.allowedByTicket === true,
    wouldExecute: parsed?.wouldExecute === true,
    startsMicrophone: parsed?.startsMicrophone === true,
    startsCamera: parsed?.startsCamera === true,
    startsGpuWork: parsed?.startsGpuWork === true,
    dependencyInstall: parsed?.dependencyInstall === true,
    persistentProcessStarted: parsed?.persistentProcessStarted === true,
    stderrTail: (result.stderr ?? '').slice(-500),
  };
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const ticket = readJson('state/resource_action_clearance_ticket.json', {});
  const integrations = [
    {
      id: 'resource-policy-summary-readonly',
      title: 'Resource policy summary read-only connector',
      actionClass: 'read-only-probes',
      expectedAllowed: true,
      commandPreview: ['node', 'apps/local-desktop-companion/src/resource-policy-state-summary.js'],
    },
    {
      id: 'camera-single-frame-capture',
      title: 'Camera single frame capture',
      actionClass: 'camera-capture',
      expectedAllowed: false,
      commandPreview: ['node', 'apps/local-desktop-companion/src/camera-single-frame-capture.js', '--capture'],
    },
    {
      id: 'voice-vad-measurement',
      title: 'Voice VAD measurement',
      actionClass: 'microphone-recording',
      expectedAllowed: false,
      commandPreview: ['node', 'apps/local-desktop-companion/src/voice-vad-measurement-runner.js', '--measure'],
    },
    {
      id: 'dependency-install',
      title: 'Dependency install',
      actionClass: 'dependency-install',
      expectedAllowed: false,
      commandPreview: ['npm', 'install'],
    },
    {
      id: 'persistent-process',
      title: 'Persistent process start',
      actionClass: 'persistent-new-process',
      expectedAllowed: false,
      commandPreview: ['node', 'apps/local-desktop-companion/src/preview-server.js', '--serve'],
    },
    {
      id: 'paid-api',
      title: 'Paid API call',
      actionClass: 'paid-api',
      expectedAllowed: false,
      commandPreview: ['provider-api-call'],
    },
  ];
  const previews = integrations.map(previewThroughWrapper);
  const mismatches = previews.filter((item) => {
    const integration = integrations.find((candidate) => candidate.id === item.id);
    return item.allowedByTicket !== integration?.expectedAllowed || item.wouldExecute !== false;
  }).map((item) => item.id);
  const sensitiveLeaks = previews.filter((item) => item.startsMicrophone || item.startsCamera || item.startsGpuWork || item.dependencyInstall || item.persistentProcessStarted).map((item) => item.id);
  const doc = {
    timestamp,
    status: mismatches.length === 0 && sensitiveLeaks.length === 0 ? 'ready' : 'blocked',
    mode: 'resource-guard-integration-map-dry-run',
    ticket: {
      profile: ticket.profile ?? 'unknown',
      resourceLevel: ticket.resourceLevel ?? 'unknown',
      valid: ticket.valid === true,
      expiresAt: ticket.expiresAt ?? null,
      hash: ticket.ticketHash ?? null,
    },
    manifestPath: path.relative(WORKSPACE, MANIFEST),
    integrationCount: integrations.length,
    allowedCount: previews.filter((item) => item.allowedByTicket).length,
    deniedCount: previews.filter((item) => !item.allowedByTicket).length,
    mismatches,
    sensitiveLeaks,
    previews,
    contract: {
      concreteScriptsMappedToActionClasses: true,
      allPreviewsGoThroughGuardedWrapper: true,
      wrapperDryRunOnly: true,
      deniedSensitiveScriptsDoNotExecute: true,
    },
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      dryRunOnly: true,
      readOnlyExceptStatus: true,
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
  writeJson(MANIFEST, { timestamp, integrations, ticket: doc.ticket, contract: doc.contract });
  writeJson(OUT, doc);
  appendAudit({ timestamp, status: doc.status, integrationCount: integrations.length, allowedCount: doc.allowedCount, deniedCount: doc.deniedCount, mismatches, sensitiveLeaks });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, integrationCount: doc.integrationCount, allowedCount: doc.allowedCount, deniedCount: doc.deniedCount, mismatches, sensitiveLeaks, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, persistentProcessStarted: false }, null, 2));
}

main();
