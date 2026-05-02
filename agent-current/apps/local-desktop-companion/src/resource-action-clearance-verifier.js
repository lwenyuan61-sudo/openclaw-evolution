import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const TICKET = path.join(STATE, 'resource_action_clearance_ticket.json');
const OUT = path.join(STATE, 'desktop_wrapper_resource_action_clearance_verifier_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_resource_action_clearance_verifier_audit.jsonl');

function readJson(file, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); }
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

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function argValue(name, fallback) {
  const idx = process.argv.indexOf(name);
  if (idx >= 0 && process.argv[idx + 1]) return process.argv[idx + 1];
  return fallback;
}

function classify(requested) {
  const aliases = {
    'read-only': 'read-only-probes',
    'read-only-probe': 'read-only-probes',
    'small-cpu': 'small-local-cpu',
    verifier: 'bounded-verifiers',
    'camera': 'camera-capture',
    'mic': 'microphone-recording',
    'microphone': 'microphone-recording',
    'dependency': 'dependency-install',
    'persistent': 'persistent-new-process',
    'paid': 'paid-api',
  };
  return aliases[requested] ?? requested;
}

function validateHash(ticket) {
  if (!ticket || typeof ticket !== 'object') return { ok: false, expected: null, actual: null };
  const { ticketHash, ...payload } = ticket;
  const expected = sha256(JSON.stringify(payload));
  return { ok: ticketHash === expected, expected, actual: ticketHash ?? null };
}

function decisionFor(ticket, requestedClass) {
  const now = Date.now();
  const expiresAtMs = Date.parse(ticket.expiresAt ?? '');
  const expired = !Number.isFinite(expiresAtMs) || expiresAtMs <= now;
  const hash = validateHash(ticket);
  const allowed = new Set(ticket.allowedWorkClasses ?? []);
  const denied = new Set(ticket.deniedWorkClasses ?? []);
  const reasons = [];
  if (!ticket.valid) reasons.push('ticket-not-valid');
  if (expired) reasons.push('ticket-expired');
  if (!hash.ok) reasons.push('ticket-hash-mismatch');
  if (denied.has(requestedClass)) reasons.push(`class-denied:${requestedClass}`);
  if (!allowed.has(requestedClass)) reasons.push(`class-not-allowed:${requestedClass}`);
  return {
    requestedClass,
    allowedNow: reasons.length === 0,
    decision: reasons.length === 0 ? 'allowed-by-fresh-ticket' : 'blocked-by-clearance-ticket',
    reasons,
    expiresInSeconds: Number.isFinite(expiresAtMs) ? Math.max(0, Math.round((expiresAtMs - now) / 1000)) : null,
    hash,
  };
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const requestedClass = classify(argValue('--class', 'read-only-probes'));
  const ticket = readJson(TICKET, {});
  const requested = decisionFor(ticket, requestedClass);
  const selfTestAllowed = decisionFor(ticket, 'read-only-probes');
  const selfTestCamera = decisionFor(ticket, 'camera-capture');
  const selfTestPaidApi = decisionFor(ticket, 'paid-api');
  const doc = {
    timestamp,
    status: requested.hash.ok && !requested.reasons.includes('ticket-expired') && ticket.valid ? 'ready' : 'blocked',
    mode: 'resource-action-clearance-verifier-read-only',
    ticketPath: path.relative(WORKSPACE, TICKET),
    ticketHash: ticket.ticketHash ?? null,
    profile: ticket.profile ?? 'unknown',
    resourceLevel: ticket.resourceLevel ?? 'unknown',
    requested,
    selfTest: {
      readOnlyAllowed: selfTestAllowed.allowedNow,
      cameraDenied: !selfTestCamera.allowedNow,
      cameraDeniedReason: selfTestCamera.reasons,
      paidApiDenied: !selfTestPaidApi.allowedNow && selfTestPaidApi.reasons.includes('class-denied:paid-api'),
      paidApiDeniedReason: selfTestPaidApi.reasons,
    },
    policy: {
      mustVerifyHash: true,
      mustBeUnexpired: true,
      allowListOnly: true,
      deniesSensitiveClassesFromTicket: true,
      doesNotExecuteRequestedAction: true,
    },
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      readOnly: true,
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
  appendAudit({ timestamp, status: doc.status, requestedClass, allowedNow: requested.allowedNow, profile: doc.profile, expiresInSeconds: requested.expiresInSeconds });
  console.log(JSON.stringify({ ok: doc.status === 'ready' && requested.allowedNow && doc.selfTest.readOnlyAllowed && doc.selfTest.paidApiDenied, out: OUT, status: doc.status, requestedClass, allowedNow: requested.allowedNow, readOnlyAllowed: doc.selfTest.readOnlyAllowed, cameraDenied: doc.selfTest.cameraDenied, paidApiDenied: doc.selfTest.paidApiDenied, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, persistentProcessStarted: false }, null, 2));
}

main();
