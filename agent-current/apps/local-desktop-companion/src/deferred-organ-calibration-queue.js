import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_deferred_organ_calibration_queue_status.json');
const QUEUE = path.join(STATE, 'deferred_organ_calibration_queue.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_deferred_organ_calibration_queue_audit.jsonl');

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
  const quietGate = readJson('state/desktop_wrapper_quiet_hours_action_gate_status.json', {});
  const ticket = readJson('state/resource_action_clearance_ticket.json', {});
  const voiceE2E = readJson('state/desktop_wrapper_voice_wake_end_to_end_gate_status.json', {});
  const cameraDryRun = readJson('state/desktop_wrapper_camera_single_frame_dry_run_status.json', {});
  const cameraCapture = readJson('state/desktop_wrapper_camera_single_frame_capture_status.json', {});
  const voiceVad = readJson('state/desktop_wrapper_voice_vad_measurement_runner_status.json', {});
  const bodyIndicators = readJson('state/desktop_wrapper_body_indicator_status.json', {});
  const readyAfterQuietHours = quietGate.quietHours === true && ticket.resourceLevel === 'ok' && ticket.profile === 'normal-local-first';
  const items = [
    {
      id: 'voice-spoken-wake-armed-calibration',
      target: 'microphone',
      priority: 90,
      preconditions: [
        'not quiet-hours or Lee explicitly active',
        'fresh normal-local-first resource ticket',
        'LOCAL_AGENT_SPOKEN_WAKE_ARM=1',
        'visible listening indicator',
        'bounded 5s in-memory audio',
        'raw audio delete-by-default',
      ],
      currentEvidence: {
        voiceWakeE2EStatus: voiceE2E.status ?? 'unknown',
        readyForArmedCalibration: voiceE2E.readyFor?.armedSpokenWakeCalibration ?? null,
        voiceVadStatus: voiceVad.status ?? 'unknown',
        startsMicrophoneNow: voiceVad.safety?.startsMicrophone ?? false,
      },
      deferredBy: quietGate.quietHours ? ['quiet-hours'] : [],
    },
    {
      id: 'camera-single-frame-calibration',
      target: 'camera',
      priority: 70,
      preconditions: [
        'not quiet-hours or Lee explicitly active',
        'fresh normal-local-first resource ticket',
        'visible camera indicator',
        'single frame only',
        'raw image delete-by-default',
      ],
      currentEvidence: {
        dryRunStatus: cameraDryRun.status ?? 'unknown',
        captureStatus: cameraCapture.status ?? 'unknown',
        startsCameraNow: cameraCapture.safety?.startsCamera ?? false,
        bodyIndicatorStatus: bodyIndicators.status ?? 'unknown',
      },
      deferredBy: quietGate.quietHours ? ['quiet-hours'] : [],
    },
  ].sort((a, b) => b.priority - a.priority);
  const executableNow = items.filter((item) => item.deferredBy.length === 0);
  const doc = {
    timestamp,
    status: 'ready',
    mode: 'deferred-organ-calibration-queue-read-only',
    readyAfterQuietHours,
    selectedWhenAllowed: items[0]?.id ?? null,
    executableNowCount: executableNow.length,
    deferredCount: items.length - executableNow.length,
    items,
    policy: {
      noOrganStartDuringQueueBuild: true,
      queueDoesNotOverrideQuietHours: true,
      requiresFreshResourceTicketAtExecutionTime: true,
      requiresVisibleIndicatorAtExecutionTime: true,
    },
    queuePath: path.relative(WORKSPACE, QUEUE),
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
  writeJson(QUEUE, { timestamp, items, policy: doc.policy });
  writeJson(OUT, doc);
  appendAudit({ timestamp, status: doc.status, selectedWhenAllowed: doc.selectedWhenAllowed, deferredCount: doc.deferredCount, readyAfterQuietHours });
  console.log(JSON.stringify({ ok: true, out: OUT, status: doc.status, selectedWhenAllowed: doc.selectedWhenAllowed, deferredCount: doc.deferredCount, executableNowCount: doc.executableNowCount, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, externalNetworkWrites: false, paidApi: false, persistentProcessStarted: false }, null, 2));
}

main();
