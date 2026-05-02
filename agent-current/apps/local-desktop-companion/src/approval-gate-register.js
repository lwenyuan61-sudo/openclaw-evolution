import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_approval_gate_register_status.json');

function readJson(rel, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8')); }
  catch (error) { return { ...fallback, _error: `${error.name}: ${error.message}` }; }
}

function capability(matrix, id) {
  return (matrix.capabilities || []).find((item) => item.id === id) || null;
}

function makeGate(id, title, source, currentMode, allowedNow, note, requirements, auditState = null) {
  return {
    id,
    title,
    source,
    currentMode,
    allowedNow: Boolean(allowedNow),
    status: allowedNow ? 'allowed' : 'approval-gated',
    whyBlocked: allowedNow ? null : note,
    approvalNote: allowedNow ? note : null,
    unblockRequirements: allowedNow ? [] : requirements,
    remainingExecutionRequirements: allowedNow ? requirements : [],
    auditState,
  };
}

function main() {
  const timestamp = new Date().toISOString();
  const permission = readJson('state/app_permission_matrix.json', { capabilities: [] });
  const voice = readJson('state/desktop_wrapper_voice_body_readiness_status.json', {});
  const packaging = readJson('state/desktop_wrapper_packaging_preflight_status.json', {});
  const queue = readJson('state/desktop_wrapper_next_connector_queue_status.json', {});
  const broad = readJson('state/lee_broad_approval_state.json', { scope: {} });
  const scope = broad.scope || {};

  const mic = capability(permission, 'microphone-always-on');
  const camera = capability(permission, 'camera-perception');
  const physicalActuation = capability(permission, 'physical-actuation');
  const externalSend = capability(permission, 'external-send');
  const paidHeavy = capability(permission, 'paid-or-gpu-heavy-work');

  const gates = [
    makeGate('always-on-microphone', 'Always-on microphone / wake listener', 'app_permission_matrix + Lee broad approval', mic?.currentMode ?? 'unknown', mic?.allowedNow === true || scope.alwaysOnVoiceWake === true || scope.microphone === true, 'Lee broadly approved microphone/always-on capability; execution still needs visible indicator, audit, and stop/pause path.', ['Visible listening indicator', 'App-shell toggle/control', 'Local-only retention policy', 'Stop/pause path verified', 'Action log'], mic?.auditState ?? 'state/voice_wake_plan.json'),
    makeGate('manual-voice-calibration-record', '3-second manual voice calibration record', 'voice_manual_calibration_runner + Lee broad approval', 'approved-token-no-longer-required-by-policy', scope.manualVoiceCalibration === true || scope.microphone === true, 'Lee broadly approved manual voice calibration recording; execution still must show indicator and delete raw audio by default.', ['Show indicator before capture', 'Delete raw audio by default', 'Write metadata ledger'], 'state/voice_manual_calibration_runner_status.json'),
    makeGate('camera-continuous-perception', 'Continuous camera perception', 'app_permission_matrix + Lee broad approval', camera?.currentMode ?? 'unknown', camera?.allowedNow === true || scope.camera === true, 'Lee broadly approved camera perception; execution still needs visible state and retention/audit policy.', ['Clear indicator', 'Retention policy', 'Post-capture audit state'], camera?.auditState ?? 'state/device_state_snapshot.json'),
    makeGate('real-physical-device-action', 'Real physical device actuation', 'physical policy + Lee broad approval', physicalActuation?.currentMode ?? 'unknown', scope.realPhysicalControl === true, 'Lee broadly approved real physical control; execution still needs concrete device/action, allowlist, risk tier, kill switch, and verification.', ['Concrete target/action', 'Device allowlist', 'Risk tier <= T2 and not T3', 'Kill switch present', 'Visible UI state', 'Post-action verification'], physicalActuation?.auditState ?? 'state/physical_actuation_simulator_status.json'),
    makeGate('external-send-or-post', 'External sends/posts', 'app_permission_matrix + Lee broad approval', externalSend?.currentMode ?? 'unknown', externalSend?.allowedNow === true || scope.externalSend === true, 'Lee broadly approved external sends/posts; execution still needs concrete recipient/channel and content/intent.', ['Clear recipient/channel', 'Exact message or intent', 'Audit/log if applicable'], externalSend?.auditState ?? null),
    makeGate('dependency-install-or-scaffold', 'Electron/Tauri scaffold or dependency install', 'packaging preflight + Lee broad approval', packaging.recommendation ?? 'unknown', scope.dependencyInstall === true || scope.scaffoldCreation === true, 'Lee broadly approved dependency install/scaffold capability.', ['Target stack selected', 'Rollback path documented', 'No persistent process unless separately needed/logged'], 'state/desktop_wrapper_packaging_preflight_status.json'),
    makeGate('service-rollback-or-safe-mode-execute', 'Gateway rollback / safe-mode execution', 'service_control_schema + Lee broad approval', 'approved-system-change', scope.serviceRollbackOrSafeMode === true || scope.permissionChanges === true, 'Lee broadly approved permission/system changes; execution still should show exact commands and log result.', ['Show exact rollback/safe-mode commands', 'Record audit result'], 'state/service_control_schema.json'),
    makeGate('paid-or-gpu-heavy-work', 'Paid API or GPU-heavy local model work', 'app_permission_matrix + resource guard + Lee broad approval', paidHeavy?.currentMode ?? 'unknown', paidHeavy?.allowedNow === true || scope.paidOrGpuHeavyWork === true, 'Lee broadly approved paid/GPU-heavy work; resource guard and value checks remain active.', ['Resource pressure ok', 'Budget/time bound', 'Fallback/queue/degrade path'], paidHeavy?.auditState ?? 'core/resource-state.json'),
  ];

  const allowed = gates.filter((gate) => gate.allowedNow);
  const gated = gates.filter((gate) => !gate.allowedNow);
  const blockedQueueIds = (queue.blockedImportant || []).map((item) => item.id);
  const doc = {
    timestamp,
    status: 'ready',
    mode: 'approval-gate-register',
    gateCount: gates.length,
    approvalGatedCount: gated.length,
    allowedCount: allowed.length,
    queueBlockedImportant: blockedQueueIds,
    leeBroadApproval: { status: broad.status ?? 'missing', scope },
    voiceBodyReadiness: {
      status: voice.status ?? 'unknown',
      recordingNow: voice.summary?.recordingNow ?? false,
      alwaysOnMicEnabled: voice.summary?.alwaysOnMicEnabled ?? false,
    },
    gates,
    safety: {
      registerOnly: true,
      changedPermissionState: true,
      dependencyInstall: false,
      scaffoldCreated: false,
      persistentProcessStarted: false,
      externalNetworkWrites: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
    },
  };
  fs.writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, gateCount: doc.gateCount, approvalGatedCount: doc.approvalGatedCount, allowedCount: doc.allowedCount, queueBlockedImportant: blockedQueueIds.length }, null, 2));
}

main();
