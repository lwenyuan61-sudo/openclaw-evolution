import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_voice_body_readiness_status.json');

function readJson(rel, fallback = {}) {
  try {
    return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8'));
  } catch (error) {
    return { ...fallback, _error: `${error.name}: ${error.message}` };
  }
}

function capability(matrix, id) {
  return (matrix.capabilities || []).find((item) => item.id === id) || null;
}

function gate(id, status, evidence, nextStep = null) {
  return { id, status, evidence, nextStep };
}

function main() {
  const timestamp = new Date().toISOString();
  const voicePlan = readJson('state/voice_wake_plan.json', { enabled: false });
  const calibration = readJson('state/voice_calibration_status.json', {});
  const runner = readJson('state/voice_manual_calibration_runner_status.json', {});
  const indicator = readJson('state/voice_listening_indicator.json', {});
  const permissions = readJson('state/app_permission_matrix.json', { capabilities: [] });
  const resource = readJson('core/resource-state.json', {});
  const queue = readJson('state/desktop_wrapper_next_connector_queue_status.json', {});

  const micPermission = capability(permissions, 'microphone-always-on');
  const cameraPermission = capability(permissions, 'camera-perception');
  const desktopActuation = capability(permissions, 'desktop-actuation');
  const physicalActuation = capability(permissions, 'physical-actuation');

  const inputs = calibration.deviceEnumeration || {};
  const recommendedInput = inputs.recommendedInput || null;
  const availableAudio = String(voicePlan.availableAudio || '');
  const hasLocalWhisper = availableAudio.includes('faster_whisper');
  const hasSoundDevice = availableAudio.includes('sounddevice');

  const gates = [
    gate('audio-device-enumeration', inputs.ok === true ? 'ready' : 'blocked', { inputCount: inputs.inputCount ?? 0, outputCount: inputs.outputCount ?? 0, recommendedInput }, 'Run device-state/audio probe if missing.'),
    gate('manual-calibration-path', calibration.status === 'ready' && calibration.mode === 'manual-calibration-only' ? 'ready' : 'blocked', { status: calibration.status, mode: calibration.mode, durationSeconds: calibration.manualCalibrationPlan?.durationSeconds ?? null }, 'Keep manual 3-second calibration path only.'),
    gate('visible-listening-indicator', indicator.state === 'idle' && indicator.recordingNow === false ? 'ready' : 'attention', { state: indicator.state, recordingNow: indicator.recordingNow, alwaysOnMicEnabled: indicator.alwaysOnMicEnabled }, 'Indicator must be visible before any manual recording.'),
    gate('always-on-mic-approval', micPermission?.allowedNow === true && voicePlan.enabled === false ? 'ready' : (micPermission?.allowedNow === false && voicePlan.enabled === false ? 'gated-as-expected' : 'attention'), { permissionMode: micPermission?.currentMode ?? 'unknown', voicePlanEnabled: voicePlan.enabled, reason: micPermission?.reason ?? voicePlan.reason }, 'Approved, but listener remains not started until an explicit run path starts it with indicator/logging.'),
    gate('local-transcription-baseline', hasSoundDevice && hasLocalWhisper ? 'ready' : 'partial', { availableAudio, hasSoundDevice, hasLocalWhisper }, 'Use CPU/local tiny model only for approved manual calibration.'),
    gate('privacy-retention', calibration.privacyLedger?.recordsRawAudio === false && calibration.manualCalibrationPlan?.networkUpload === false ? 'ready' : 'attention', { recordsRawAudio: calibration.privacyLedger?.recordsRawAudio, rawAudioDefaultRetention: calibration.manualCalibrationPlan?.rawAudioDefaultRetention, networkUpload: calibration.manualCalibrationPlan?.networkUpload }, 'Raw audio should be deleted by default; no external upload.'),
    gate('last-runner-safety', runner.recordingStarted === false && runner.rawAudioCreated === false ? 'ready' : 'attention', { event: runner.event, status: runner.status, reason: runner.reason, recordingStarted: runner.recordingStarted, rawAudioCreated: runner.rawAudioCreated }, 'Blocked missing-token run is expected and safe.'),
    gate('camera-body-gate', cameraPermission?.allowedNow === true ? 'ready' : 'gated-as-expected', { mode: cameraPermission?.currentMode ?? 'unknown', reason: cameraPermission?.reason ?? null }, 'Camera is approved but not started; visible indicator/audit still required when used.'),
    gate('desktop-body-gate', desktopActuation?.allowedNow === true ? 'ready' : 'attention', { mode: desktopActuation?.currentMode ?? 'unknown', constraints: desktopActuation?.constraints ?? [] }, 'Digital reversible desktop actions remain allowed through existing gates.'),
    gate('physical-body-gate', physicalActuation?.allowedNow === true ? 'ready' : 'attention', { mode: physicalActuation?.currentMode ?? 'unknown', constraints: physicalActuation?.constraints ?? [] }, 'Physical control is approved; concrete device/action allowlist and T3 block still apply.'),
    gate('resource-fit', resource.resourcePressure?.level === 'ok' ? 'ready' : 'blocked', { resourcePressure: resource.resourcePressure?.level ?? 'unknown' }, 'Avoid GPU-heavy voice work if resource pressure rises.'),
  ];

  const blocked = gates.filter((item) => item.status === 'blocked');
  const attention = gates.filter((item) => item.status === 'attention');
  const ready = gates.filter((item) => item.status === 'ready' || item.status === 'gated-as-expected');
  const doc = {
    timestamp,
    status: blocked.length === 0 && attention.length === 0 ? 'ready' : 'needs-attention',
    mode: 'voice-body-readiness-matrix-no-recording',
    selectedByQueue: queue.selected?.id === 'voice-body-readiness-matrix',
    readiness: {
      readyCount: ready.length,
      gateCount: gates.length,
      blockedIds: blocked.map((item) => item.id),
      attentionIds: attention.map((item) => item.id),
    },
    summary: {
      manualCalibrationReady: calibration.status === 'ready',
      recommendedInput,
      alwaysOnMicEnabled: Boolean(voicePlan.enabled || calibration.alwaysOnMicEnabled || indicator.alwaysOnMicEnabled),
      recordingNow: Boolean(calibration.recordingNow || indicator.recordingNow),
      localTranscriptionBaseline: hasLocalWhisper ? 'available-cpu-fallback' : 'missing',
      wakeListenerQuality: voicePlan.mode ?? 'unknown',
    },
    gates,
    nextSafeStep: 'Keep voice/body path in manual-calibration-only mode unless Lee explicitly approves 3-second calibration or always-on listening.',
    blockedUntilApproval: [
      'always-on microphone listener',
      'background capture',
      'external transcription/upload',
      'camera continuous perception',
    ],
    safety: {
      noRecordingStarted: true,
      microphoneAccessed: false,
      cameraAccessed: false,
      externalNetworkWrites: false,
      paidApi: false,
      dependencyInstall: false,
      persistentProcessStarted: false,
      realPhysicalActuation: false,
    },
  };
  fs.writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, readyCount: doc.readiness.readyCount, gateCount: doc.readiness.gateCount, blockedIds: doc.readiness.blockedIds, attentionIds: doc.readiness.attentionIds }, null, 2));
}

main();
