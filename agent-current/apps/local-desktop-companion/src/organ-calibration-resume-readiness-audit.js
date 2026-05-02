import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_organ_calibration_resume_readiness_audit_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_organ_calibration_resume_readiness_audit_audit.jsonl');

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
function hashSubset(value) {
  return crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const mode = readJson('core/session-mode.json', {});
  const ticketStatus = readJson('state/desktop_wrapper_resource_action_clearance_ticket_status.json', {});
  const ticket = readJson('state/resource_action_clearance_ticket.json', {});
  const queue = readJson('state/desktop_wrapper_deferred_organ_calibration_queue_status.json', {});
  const packet = readJson('state/desktop_wrapper_organ_calibration_resume_packet_status.json', {});
  const voiceE2E = readJson('state/desktop_wrapper_voice_wake_end_to_end_gate_status.json', {});
  const voiceRunner = readJson('state/desktop_wrapper_voice_spoken_wake_calibration_runner_status.json', {});
  const cameraCapture = readJson('state/desktop_wrapper_camera_single_frame_capture_status.json', {});
  const bodyIndicators = readJson('state/desktop_wrapper_body_indicator_status.json', {});
  const ticketAge = ageSeconds(ticket.issuedAt ?? ticketStatus.timestamp);
  const packetAge = ageSeconds(packet.timestamp);
  const queueAge = ageSeconds(queue.timestamp);
  const quietHours = mode.mode === 'quiet-hours';
  const checks = [
    { id: 'quiet-hours-block-active', ok: quietHours === true, evidence: mode.mode ?? 'unknown' },
    { id: 'ticket-fresh-now-but-expires-before-real-execution', ok: ticketAge !== null && ticketAge <= 120 && ticket.expiresAt !== undefined, evidence: { ticketAge, expiresAt: ticket.expiresAt ?? null } },
    { id: 'resume-packet-present', ok: packet.status === 'ready', evidence: { status: packet.status, ageSeconds: packetAge } },
    { id: 'deferred-queue-present', ok: queue.status === 'ready' && queue.deferredCount >= 2, evidence: { status: queue.status, deferredCount: queue.deferredCount, ageSeconds: queueAge } },
    { id: 'voice-first-selected', ok: packet.readiness?.selectedDeferredItem === 'voice-spoken-wake-armed-calibration' && queue.selectedWhenAllowed === 'voice-spoken-wake-armed-calibration', evidence: { packet: packet.readiness?.selectedDeferredItem, queue: queue.selectedWhenAllowed } },
    { id: 'voice-e2e-ready', ok: voiceE2E.status === 'ready-for-armed-calibration' || voiceE2E.readyFor?.armedSpokenWakeCalibration === true, evidence: { status: voiceE2E.status, ready: voiceE2E.readyFor?.armedSpokenWakeCalibration ?? null } },
    { id: 'organ-indicators-ready', ok: bodyIndicators.status === 'ready', evidence: bodyIndicators.status ?? 'unknown' },
    { id: 'no-organ-active-now', ok: cameraCapture.safety?.startsCamera !== true && voiceRunner.safety?.startsMicrophone !== true, evidence: { cameraStarts: cameraCapture.safety?.startsCamera ?? false, micStarts: voiceRunner.safety?.startsMicrophone ?? false } },
  ];
  const failed = checks.filter((check) => !check.ok).map((check) => check.id);
  const resumeFingerprint = hashSubset({
    selected: packet.readiness?.selectedDeferredItem,
    steps: (packet.steps ?? []).map((step) => step.id),
    queue: (queue.items ?? []).map((item) => ({ id: item.id, deferredBy: item.deferredBy })),
  });
  const doc = {
    timestamp,
    status: failed.length === 0 ? 'ready' : 'needs-attention',
    mode: 'organ-calibration-resume-readiness-audit-read-only',
    quietHours,
    executableNow: packet.executableNow === true && !quietHours,
    resumeFingerprint,
    checks,
    failed,
    recommendation: quietHours ? 'do-not-start-organs; keep packet queued' : 'refresh-ticket-and-review-before-execution',
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
  appendAudit({ timestamp, status: doc.status, failed, resumeFingerprint, quietHours });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, quietHours, executableNow: doc.executableNow, failed, recommendation: doc.recommendation, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, externalNetworkWrites: false, paidApi: false, persistentProcessStarted: false }, null, 2));
}

main();
