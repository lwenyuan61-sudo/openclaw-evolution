import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_organ_calibration_resume_packet_status.json');
const PACKET = path.join(STATE, 'organ_calibration_resume_packet.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_organ_calibration_resume_packet_audit.jsonl');

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
  const quietGate = readJson('state/desktop_wrapper_quiet_hours_action_gate_status.json', {});
  const queue = readJson('state/desktop_wrapper_deferred_organ_calibration_queue_status.json', {});
  const voiceBoundary = readJson('state/desktop_wrapper_voice_spoken_wake_boundary_status.json', {});
  const voiceE2E = readJson('state/desktop_wrapper_voice_wake_end_to_end_gate_status.json', {});
  const voiceRunner = readJson('state/desktop_wrapper_voice_spoken_wake_calibration_runner_status.json', {});
  const bodyIndicators = readJson('state/desktop_wrapper_body_indicator_status.json', {});
  const cameraDryRun = readJson('state/desktop_wrapper_camera_single_frame_dry_run_status.json', {});
  const cameraCapture = readJson('state/desktop_wrapper_camera_single_frame_capture_status.json', {});
  const quietHours = mode.mode === 'quiet-hours' || quietGate.quietHours === true;
  const resourcesReady = ticket.valid === true && ticket.resourceLevel === 'ok' && ticket.profile === 'normal-local-first';
  const resumeWhen = quietHours ? 'after-quiet-hours-or-Lee-explicitly-active' : 'now-if-Lee-active-and-fresh-ticket';
  const steps = [
    {
      order: 1,
      id: 'refresh-resource-ticket',
      command: 'node apps/local-desktop-companion/src/resource-gate-serialized-refresh.js && node apps/local-desktop-companion/src/resource-action-clearance-ticket.js',
      required: true,
      reason: 'ticket expires quickly; execution must use fresh profile',
    },
    {
      order: 2,
      id: 'voice-spoken-wake-armed-calibration',
      command: 'LOCAL_AGENT_SPOKEN_WAKE_ARM=1 node apps/local-desktop-companion/src/voice-spoken-wake-calibration-runner.js',
      required: false,
      blockedNow: quietHours,
      reason: 'first queued organ calibration; requires Lee available to say the agent and visible indicator',
      safety: ['bounded 5s', 'in-memory audio', 'raw delete-by-default', 'no persistent listener'],
    },
    {
      order: 3,
      id: 'camera-single-frame-calibration',
      command: 'node apps/local-desktop-companion/src/camera-single-frame-capture.js --capture',
      required: false,
      blockedNow: quietHours,
      reason: 'second queued calibration; single frame only after indicator and fresh clearance',
      safety: ['single frame', 'raw delete-by-default', 'no continuous camera'],
    },
    {
      order: 4,
      id: 'post-calibration-regression',
      command: 'node apps/local-desktop-companion/src/test-matrix.js && python core/scripts/consistency_check.py',
      required: true,
      reason: 'verify no guard regressions after any real organ calibration',
    },
  ];
  const readiness = {
    resourcesReady,
    quietHours,
    selectedDeferredItem: queue.selectedWhenAllowed ?? null,
    voiceReadyForArmedCalibration: voiceE2E.readyFor?.armedSpokenWakeCalibration === true || voiceE2E.status === 'ready-for-armed-calibration',
    voiceRunnerStatus: voiceRunner.status ?? 'unknown',
    voiceBoundaryStatus: voiceBoundary.status ?? 'unknown',
    bodyIndicatorStatus: bodyIndicators.status ?? 'unknown',
    cameraDryRunStatus: cameraDryRun.status ?? 'unknown',
    cameraCaptureStatus: cameraCapture.status ?? 'unknown',
  };
  const executableNow = resourcesReady && !quietHours && readiness.voiceReadyForArmedCalibration;
  const doc = {
    timestamp,
    status: 'ready',
    mode: 'organ-calibration-resume-packet-read-only',
    resumeWhen,
    executableNow,
    readiness,
    steps,
    packetPath: path.relative(WORKSPACE, PACKET),
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
  writeJson(PACKET, doc);
  writeJson(OUT, doc);
  appendAudit({ timestamp, status: doc.status, resumeWhen, executableNow, resourcesReady, quietHours, selected: readiness.selectedDeferredItem });
  console.log(JSON.stringify({ ok: true, out: OUT, status: doc.status, resumeWhen, executableNow, selectedDeferredItem: readiness.selectedDeferredItem, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, externalNetworkWrites: false, paidApi: false, persistentProcessStarted: false }, null, 2));
}

main();
