import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_resource_action_clearance_ticket_status.json');
const TICKET = path.join(STATE, 'resource_action_clearance_ticket.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_resource_action_clearance_ticket_audit.jsonl');
const MAX_PREFLIGHT_AGE_SECONDS = 5 * 60;
const TTL_SECONDS = 2 * 60;

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
  const parsed = Date.parse(iso ?? '');
  if (!Number.isFinite(parsed)) return null;
  return Math.max(0, Math.round((Date.now() - parsed) / 1000));
}

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const issuedAtMs = Date.parse(timestamp);
  const expiresAt = new Date(issuedAtMs + TTL_SECONDS * 1000).toISOString();
  const serialized = readJson('state/desktop_wrapper_resource_gate_serialized_refresh_status.json', {});
  const safeQueue = readJson('state/desktop_wrapper_resource_safe_connector_queue_status.json', {});
  const sensitive = readJson('state/desktop_wrapper_sensitive_action_resource_preflight_status.json', {});
  const resource = readJson('core/resource-state.json', {});
  const final = serialized.final ?? {};
  const serializedAge = ageSeconds(serialized.timestamp);
  const sensitiveAge = ageSeconds(sensitive.timestamp);
  const serializedFresh = serialized.status === 'ready' && serializedAge !== null && serializedAge <= MAX_PREFLIGHT_AGE_SECONDS;
  const sensitiveFresh = sensitive.status === 'ready' && sensitiveAge !== null && sensitiveAge <= MAX_PREFLIGHT_AGE_SECONDS;
  const inconsistencies = final.inconsistencies ?? [];
  const consistent = inconsistencies.length === 0 && final.requiresRerunOrder !== true;
  const resourceLevel = final.resourceLevel ?? resource.resourcePressure?.level ?? 'unknown';
  const profile = final.effectiveProfile ?? safeQueue.profile ?? sensitive.effectiveProfile ?? 'unknown';
  const sensitiveDecisions = sensitive.decisions ?? [];
  const sensitiveAllowed = sensitiveDecisions.filter((item) => item?.allowedNow).map((item) => item.id);
  const sensitiveBlocked = sensitiveDecisions.filter((item) => item && !item.allowedNow).map((item) => ({ id: item.id, reasons: item.reasons ?? [] }));
  const allowHeavy = profile === 'normal-local-first' && resourceLevel === 'ok' && serializedFresh && sensitiveFresh && consistent;
  const allowedWorkClasses = [
    'read-only-probes',
    'small-local-cpu',
    'bounded-verifiers',
  ];
  if (allowHeavy) allowedWorkClasses.push('fresh-checked-normal-local-work');
  const deniedWorkClasses = [
    'gpu-heavy',
    'memory-heavy',
    'camera-capture',
    'microphone-recording',
    'model-load',
    'dependency-install',
    'persistent-new-process',
    'paid-api',
  ].filter((id) => !sensitiveAllowed.includes(id));
  const valid = serializedFresh && sensitiveFresh && consistent;
  const ticketPayload = {
    kind: 'local-evolution-agent.resource-action-clearance-ticket.v1',
    issuedAt: timestamp,
    expiresAt,
    ttlSeconds: TTL_SECONDS,
    valid,
    profile,
    resourceLevel,
    memoryPressure: resource.memory?.pressure ?? null,
    gpuVramUsedMiB: resource.gpus?.[0]?.memoryUsedMiB ?? null,
    allowedWorkClasses,
    deniedWorkClasses,
    sensitiveAllowed,
    sensitiveBlocked,
    selectedSafeConnector: safeQueue.selected?.id ?? null,
    evidence: {
      serializedPreflight: {
        timestamp: serialized.timestamp ?? null,
        ageSeconds: serializedAge,
        fresh: serializedFresh,
        consistencyRecommendation: final.consistencyRecommendation ?? null,
        inconsistencies,
        requiresRerunOrder: final.requiresRerunOrder ?? null,
      },
      sensitivePreflight: {
        timestamp: sensitive.timestamp ?? null,
        ageSeconds: sensitiveAge,
        fresh: sensitiveFresh,
        blockedCount: sensitive.summary?.blockedCount ?? sensitive.blockedCount ?? null,
      },
    },
    policy: {
      expiresBeforeExecution: true,
      doesNotExecuteActions: true,
      paidApiDefaultOff: true,
      organsRequireFreshStableProfile: true,
    },
  };
  const ticketHash = sha256(JSON.stringify(ticketPayload));
  const ticket = { ...ticketPayload, ticketHash };
  writeJson(TICKET, ticket);
  const doc = {
    timestamp,
    status: valid ? 'ready' : 'needs-refresh',
    mode: 'resource-action-clearance-ticket-read-only',
    ticketPath: path.relative(WORKSPACE, TICKET),
    ticketHash,
    expiresAt,
    valid,
    profile,
    resourceLevel,
    allowedWorkClasses,
    deniedWorkClassCount: deniedWorkClasses.length,
    sensitiveAllowedCount: sensitiveAllowed.length,
    selectedSafeConnector: safeQueue.selected?.id ?? null,
    evidence: ticketPayload.evidence,
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      readOnlyExceptTicketState: true,
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
  appendAudit({ timestamp, status: doc.status, ticketHash, profile, resourceLevel, valid, allowedWorkClasses, deniedWorkClassCount: deniedWorkClasses.length });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, ticket: TICKET, valid, profile, resourceLevel, allowedWorkClasses, deniedWorkClassCount: deniedWorkClasses.length, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, persistentProcessStarted: false }, null, 2));
}

main();
