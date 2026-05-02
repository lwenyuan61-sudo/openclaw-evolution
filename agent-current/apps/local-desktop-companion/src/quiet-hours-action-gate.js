import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_quiet_hours_action_gate_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_quiet_hours_action_gate_audit.jsonl');

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

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const mode = readJson('core/session-mode.json', {});
  const ticket = readJson('state/resource_action_clearance_ticket.json', {});
  const safeQueue = readJson('state/desktop_wrapper_resource_safe_connector_queue_status.json', {});
  const guardScore = readJson('state/desktop_wrapper_resource_guard_enforcement_scorecard_status.json', {});
  const externalGuard = readJson('state/desktop_wrapper_external_action_guard_status.json', {});
  const quietHours = mode.mode === 'quiet-hours';
  const resourcesStable = ticket.resourceLevel === 'ok' && ticket.profile === 'normal-local-first';
  const candidates = [
    {
      id: 'organ-calibration-camera-or-voice',
      class: 'organ-sensitive',
      baseAllowedByResource: resourcesStable,
      quietHoursAllowed: false,
      reason: 'resource may allow later, but quiet-hours suppresses real mic/camera calibration unless Lee is active',
    },
    {
      id: 'guard-consolidation-read-only',
      class: 'read-only-probes',
      baseAllowedByResource: true,
      quietHoursAllowed: true,
      reason: 'low-noise local verification / documentation is safe during quiet-hours',
    },
    {
      id: 'external-paid-action',
      class: 'external-or-paid',
      baseAllowedByResource: false,
      quietHoursAllowed: false,
      reason: 'external/paid remains blocked by policy and is never implied by resource stability',
    },
    {
      id: 'persistent-process-start',
      class: 'persistent-new-process',
      baseAllowedByResource: resourcesStable,
      quietHoursAllowed: false,
      reason: 'persistent process changes should not start during quiet-hours unless explicitly necessary',
    },
  ];
  const decisions = candidates.map((candidate) => {
    const allowedNow = candidate.baseAllowedByResource && (!quietHours || candidate.quietHoursAllowed);
    const blockers = [];
    if (!candidate.baseAllowedByResource) blockers.push('resource-or-policy-denied');
    if (quietHours && !candidate.quietHoursAllowed) blockers.push('quiet-hours-suppression');
    return { ...candidate, allowedNow, blockers };
  });
  const selected = decisions.find((item) => item.allowedNow)?.id ?? null;
  const doc = {
    timestamp,
    status: 'ready',
    mode: 'quiet-hours-action-gate-read-only',
    currentMode: mode.mode ?? 'unknown',
    quietHours,
    resources: {
      profile: ticket.profile ?? 'unknown',
      resourceLevel: ticket.resourceLevel ?? 'unknown',
      stableEnoughForNormalWork: resourcesStable,
      ticketValid: ticket.valid === true,
    },
    decisions,
    selected,
    suppressions: decisions.filter((item) => !item.allowedNow).map((item) => ({ id: item.id, blockers: item.blockers })),
    evidence: {
      safeQueueSelected: safeQueue.selected?.id ?? null,
      guardCoverageScore: guardScore.score ?? null,
      externalGuardStatus: externalGuard.status ?? null,
      externalBlockedCount: externalGuard.blockedExternalCount ?? null,
    },
    contract: {
      quietHoursSuppressesOrganCalibration: true,
      quietHoursSuppressesPersistentStarts: true,
      externalPaidNeverAllowedByResourceAlone: true,
      readOnlyGuardConsolidationAllowed: true,
    },
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      readOnly: true,
      startsMicrophone: false,
      startsCamera: false,
      startsGpuWork: false,
      dependencyInstall: false,
      externalNetworkWrites: false,
      paidApi: false,
      persistentProcessStarted: false,
      realPhysicalActuation: false,
    },
  };
  writeJson(OUT, doc);
  appendAudit({ timestamp, status: doc.status, quietHours, selected, suppressedCount: doc.suppressions.length, profile: doc.resources.profile });
  console.log(JSON.stringify({ ok: true, out: OUT, status: doc.status, quietHours, selected, suppressedCount: doc.suppressions.length, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, externalNetworkWrites: false, paidApi: false, persistentProcessStarted: false }, null, 2));
}

main();
